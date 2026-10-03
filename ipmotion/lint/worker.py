"""Run one Scene without rendering and snapshot its geometry after every play()/wait().

Animations are completed in a single step (begin -> finish) instead of being
stepped frame by frame, so only END STATES are observed; mid-animation
overlaps are a known limit.

Subprocess entry point:  python -m ipmotion.lint.worker <script.py> [Scene] <out.json>
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import traceback

import copy

import manim
import numpy as np
from manim import Mobject, Scene, Transform, config, tempconfig
from manim.utils.color import ManimColor
from manim.constants import DEFAULT_WAIT_TIME

from ipmotion.lint.snapshot import build_names, take_snapshot

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_MANIM_DIR = os.path.dirname(os.path.abspath(manim.__file__))


_ATOMIC = (int, float, str, bool, type(None), ManimColor)


def _copy_attr(v, memo):
    t = type(v)
    if t in _ATOMIC or isinstance(v, ManimColor):
        return v
    if t is np.ndarray:
        return v.copy()
    if isinstance(v, Mobject):
        hit = memo.get(id(v))            # explicit None test: truthiness of a half-copied mobject calls __len__
        return hit if hit is not None else v.__deepcopy__(memo)
    if t is list:
        return [_copy_attr(x, memo) for x in v]
    if t is dict:
        return {k: _copy_attr(x, memo) for k, x in v.items()}
    if type(v).__module__.startswith("svgelements"):
        return v                      # glyph path data: read-only after construction
    return copy.deepcopy(v, memo)


def _fast_deepcopy(self, memo):
    """Structural copy that skips copy.deepcopy's per-attribute dispatch (3-5x faster on Text)."""
    result = self.__class__.__new__(self.__class__)
    memo[id(self)] = result
    for k, v in self.__dict__.items():
        setattr(result, k, _copy_attr(v, memo))
    result.original_id = str(id(self))
    return result


def _sync_text(target, source):
    """After a Transform the glyphs show the new string but .text is stale; copy it (pairwise over equal-length groups)."""
    if isinstance(getattr(target, "text", None), str) and isinstance(getattr(source, "text", None), str):
        target.text = source.text
    elif len(target.submobjects) == len(source.submobjects):
        for a, b in zip(target.submobjects, source.submobjects):
            _sync_text(a, b)


def _user_frames(skip: int):
    """Frames from the caller of play()/wait() outward, up to and including construct()."""
    frames, f = [], sys._getframe(skip)
    while f is not None:
        fn = os.path.abspath(f.f_code.co_filename)
        if not fn.startswith(_MANIM_DIR) and not fn.startswith(_THIS_DIR):
            frames.append(f)
            if f.f_code.co_name == "construct":
                break
        f = f.f_back
    return frames


class _Recorder:
    def __init__(self):
        self.snaps: list[dict] = []
        self.last_line = 0
        self.names: dict[int, str] = {}      # survives past construct() for the final snapshot
        self.last_locals: list[dict] = []    # construct()'s locals as of the latest user-level add()

    def remember(self, frames):
        self.last_locals = [dict(f.f_locals) for f in frames]

    def record(self, scene, call: str, skip: int = 3):
        frames = _user_frames(skip)
        line = frames[0].f_lineno if frames else self.last_line
        self.last_line = line
        fresh = build_names([f.f_locals for f in frames] or self.last_locals)
        self.names = {**self.names, **fresh}
        snap = take_snapshot(scene, self.names)
        snap.update({"call": call, "line": line, "t": round(float(scene.time), 3)})
        self.snaps.append(snap)


def run_scene(scene_cls, script_path: str | None = None, fast_copy: bool = True) -> dict:
    """Run scene_cls in this process. Returns {'snapshots', 'frame', 'runtime_error', 'seconds'}."""
    rec = _Recorder()
    orig_play, orig_wait, orig_copy, orig_add = Scene.play, Scene.wait, Mobject.__deepcopy__, Scene.add
    orig_finish = Transform.finish

    def synced_finish(self):
        orig_finish(self)
        tgt = getattr(self, "target_mobject", None)
        if tgt is not None and self.mobject is not None:
            _sync_text(self.mobject, tgt)

    def fast_play(self, *args, subcaption=None, subcaption_duration=None,
                  subcaption_offset=0, **kwargs):
        self.compile_animation_data(*args, **kwargs)
        if not getattr(self.animations[0], "is_static_wait", False) or len(self.animations) > 1:
            self.begin_animations()
            self.update_to_time(self.duration)
            for a in self.animations:
                a.finish()
                a.clean_up_from_scene(self)
            self.update_mobjects(0)
        self.renderer.time += self.duration
        rec.record(self, "play")

    def fast_wait(self, duration=DEFAULT_WAIT_TIME, stop_condition=None, frozen_frame=None):
        duration = float(duration)
        if self.always_update_mobjects or any(
                m.has_time_based_updater() for m in self.get_mobject_family_members()):
            self.update_mobjects(dt=duration)
        self.renderer.time += duration
        rec.record(self, "wait")

    def lint_add(self, *mobjects):
        frames = _user_frames(2)
        if frames:
            rec.remember(frames)
        return orig_add(self, *mobjects)

    err = None
    t0 = time.time()
    media = os.path.join(tempfile.gettempdir(), "ipmotion_lint_media")   # shared: caches Text SVGs
    with tempconfig({"dry_run": True, "progress_bar": "none", "verbosity": "ERROR",
                     "disable_caching": True, "media_dir": media}):
        Scene.play, Scene.wait, Scene.add = fast_play, fast_wait, lint_add
        Transform.finish = synced_finish
        if fast_copy:
            Mobject.__deepcopy__ = _fast_deepcopy
        try:
            scene = scene_cls()
            scene.render()
            rec.record(scene, "end", skip=1)
        except Exception:
            tb = traceback.format_exc()
            err = {"traceback": tb[-3000:], "line": rec.last_line}
        finally:
            Scene.play, Scene.wait, Scene.add = orig_play, orig_wait, orig_add
            Transform.finish = orig_finish
            Mobject.__deepcopy__ = orig_copy
        frame = {"width": float(config.frame_width), "height": float(config.frame_height)}
    return {"snapshots": rec.snaps, "frame": frame, "runtime_error": err,
            "seconds": round(time.time() - t0, 2)}


def load_scene(script: str, scene_name: str | None):
    script = os.path.abspath(script)
    sys.path[:0] = [os.path.dirname(script)]
    spec = importlib.util.spec_from_file_location("_lint_target", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if scene_name:
        return getattr(mod, scene_name)
    cands = [c for c in vars(mod).values()
             if isinstance(c, type) and issubclass(c, Scene) and c is not Scene
             and c.__module__ == mod.__name__]
    if not cands:
        raise RuntimeError("no Scene subclass found in script")
    return cands[0]


def main(argv):
    script, out = argv[0], argv[-1]
    scene_name = argv[1] if len(argv) == 3 else None
    try:
        cls = load_scene(script, scene_name)
        result = run_scene(cls, script)
        result["scene"] = cls.__name__
    except Exception:
        result = {"snapshots": [], "frame": {"width": 14.2222, "height": 8.0}, "scene": scene_name,
                  "runtime_error": {"traceback": traceback.format_exc()[-3000:], "line": 0}, "seconds": 0}
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh)


if __name__ == "__main__":
    main(sys.argv[1:])
