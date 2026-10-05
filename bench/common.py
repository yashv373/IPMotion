"""Shared pieces for the v2 / v3 benchmark runs. Nothing here is tuned per spec."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
CLEAN_INDEX = os.path.join(ROOT, ".chroma_db_clean")
os.environ["IPMOTION_CHROMA_DIR"] = CLEAN_INDEX          # BOTH pipelines use the clean manifest-only index
MODEL = os.environ.get("IPMOTION_MODEL", "gemini-3.5-flash")   # ONE model for every run in a comparison.
# Set IPMOTION_MODEL to an OpenRouter slug (it has a "/") and OPENROUTER_API_KEY to measure that provider
# instead -- the same endpoint the website calls. Never mix providers inside one comparison table.
MAX_ATTEMPTS = 8

import rag_pipeline  # noqa: E402  (reads IPMOTION_CHROMA_DIR at import)
import runner  # noqa: E402
from ipmotion.leakguard import LeakError, assert_no_truth_leak  # noqa: E402

SPEC_INSTRUCTIONS = """## SPEC FORMAT (how to read the spec below)
The spec states intent only; you decide placement, sizes, routing and pacing.
- blocks: each is a labelled block (use the exact `label`). `role` guides layout: masters/initiators first,
  interconnects between, slaves/targets/peripherals last. `fifo` may use the library FIFO symbol.
- domains: enclosing regions (clock/power domains) drawn around the blocks they `contains`; use the exact `label`.
- connections: wires between blocks. `from -> to` is the arrow direction when `direction` is forward;
  `both` = arrowheads at both ends; `none` = a plain line with no arrowhead. Use the exact `label` if given.
  `bus` colors: control/address green, data/response blue, clock/reset gray, irq red, tl_ul cyan.
- sequence: one banner per step (use the exact `banner` text). `highlight` lights blocks, `activate` lights
  connections for that step (everything else returns to the inactive look). `packets` are labelled tokens that
  travel along a connection. A packet with `kind: response` must be drawn in a clearly different color from
  request packets and carry the text "response", because it travels back over a connection whose arrow points
  the other way. `state` changes text inside a block. `hold` is seconds to pause after the step.
- Draw ONLY the blocks, domains and connections in the spec. Do not add, rename or rewire anything.
"""


def prompt_spec(spec_path: str) -> str:
    """The spec as shown to the model: provenance keys (source/truth) and comments removed."""
    with open(spec_path, encoding="utf-8") as fh:
        d = yaml.safe_load(fh)
    d.pop("source", None)
    for c in d.get("connections") or []:
        c.pop("truth", None)
    return yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=110)


PROMPT_VERSION = 2          # v3 prompts with the LABELS/BANNERS block at the top (v2 runs use the old prompt)

LABELS_RULES = """## READ THIS FIRST: LABELS AND BANNERS
Start your script with this block EXACTLY as given (copy it, do not edit it):

{block}

Rules (a script that breaks them is rejected before it is even looked at):
- Every block title, domain title, wire label, packet text, state text and step banner must come from LABELS or BANNERS
  (for example IPBlock(LABELS["ibex_core"], ...), banner.update_text(BANNERS[2], theme)).
- NEVER type any of these texts yourself, in any form. Do not rewrite, shorten, re-wrap or retype them.
- NEVER use lint_ignore.
"""


def labels_block(spec_path: str) -> str:
    from ipmotion import conformance
    with open(spec_path, encoding="utf-8") as fh:
        return LABELS_RULES.format(block=conformance.preamble(yaml.safe_load(fh)))


def user_request(spec_path: str) -> str:
    return (SPEC_INSTRUCTIONS + "\n## SPEC\n```yaml\n" + prompt_spec(spec_path) + "```\n\n"
            "Generate the complete Manim animation script for this spec.")


class Recorder:
    """Records every retrieved context and enforces the leakage assertion on it."""
    def __init__(self):
        self.contexts: list[dict] = []

    def guarded_retrieve(self, original):
        original = getattr(original, "__wrapped__", original)      # never stack guards from earlier runs
        def wrapped(query, top_k=rag_pipeline.TOP_K):
            ctx = original(query, top_k=top_k)
            assert_no_truth_leak([ctx], where="retrieved context")      # raises LeakError -> run aborts
            sources = re.findall(r"^# --- \[(\w+)\] ([^\s:]+)(?: :: (\w+))? ---", ctx, flags=re.M)
            self.contexts.append({"query_chars": len(query), "chars": len(ctx), "chunks": [list(s) for s in sources]})
            return ctx
        wrapped.__wrapped__ = original
        return wrapped


class DailyQuotaError(BaseException):
    """Daily API quota exhausted. BaseException so v2's `except Exception` around its fix call cannot swallow it."""


_DAILY = re.compile(r"PerDay|per.?day|GenerateRequestsPerDay", re.I)
_TRANSIENT = re.compile(r"429|ResourceExhausted|503|504|500|unavailable|timed? ?out|deadline|overloaded", re.I)


def wrap_llm(original, sleep=time.sleep, tries: int = 4):
    """Identical error policy for v2 and v3: daily quota -> stop at once; transient errors -> backoff retries."""
    def wrapped(prompt, api_key=None, model=None):
        last = None
        for i in range(tries):
            try:
                return original(prompt, api_key=api_key, model=model or MODEL)
            except Exception as e:
                msg = str(e)
                if _DAILY.search(msg):
                    raise DailyQuotaError(msg[:400])
                if not _TRANSIENT.search(msg):
                    raise
                last = e
                sleep(20 * (i + 1))
        raise RuntimeError(f"LLM call still failing after {tries} tries: {str(last)[:300]}")
    wrapped.__wrapped__ = original
    return wrapped


def install_llm_wrapper():
    if not hasattr(rag_pipeline.call_llm, "__wrapped__"):
        rag_pipeline.call_llm = wrap_llm(rag_pipeline.call_llm)
    runner.call_llm = rag_pipeline.call_llm


install_llm_wrapper()


def call_llm(prompt: str) -> str:
    return rag_pipeline.call_llm(prompt, model=MODEL)


def scene_name(script: str) -> str | None:
    m = re.search(r"class (\w+)\(\s*\w*Scene\s*\)", script)
    return m.group(1) if m else None


def make_run_dir(spec_name: str, pipeline: str) -> str:
    base = os.environ.get("IPMOTION_RUNS_DIR") or os.path.join(ROOT, "runs")      # tests redirect this
    d = os.path.join(base, f"{datetime.now():%Y%m%d_%H%M%S}_{spec_name}_{pipeline}")
    os.makedirs(d)
    return d


def render_and_frames(script_path: str, scene: str, out_dir: str, timeout: int = 900):
    """Render at 1920x1080 (the standard landscape video size) into out_dir, extract the last frame + 3
    mid-sequence keyframes. -> (ok, log, {name: path})."""
    media = os.path.join(out_dir, "media")
    env = dict(os.environ, PYTHONPATH=ROOT)
    cmd = [sys.executable, "-m", "manim", "render", "--resolution", "1920,1080", "--fps", "30",
           "--progress_bar", "none", "-v", "WARNING", "--media_dir", media, script_path, scene]
    try:
        p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT: render exceeded {timeout}s", {}
    log = (p.stdout + "\n" + p.stderr)[-3000:]
    vids = [os.path.join(dp, f) for dp, _, fs in os.walk(media) for f in fs
            if f.endswith(".mp4") and "partial_movie_files" not in dp]
    if p.returncode or not vids:
        return False, log, {}
    video = vids[0]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True).stdout.strip() or 0)
    frames = {}
    os.makedirs(os.path.join(out_dir, "frames"), exist_ok=True)
    for name, frac in (("key_25", 0.25), ("key_50", 0.5), ("key_75", 0.75), ("last", 0.985)):
        dst = os.path.join(out_dir, "frames", f"{name}.png")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{dur * frac:.2f}", "-i", video,
                        "-frames:v", "1", dst], capture_output=True)
        if os.path.exists(dst):
            frames[name] = os.path.relpath(dst, out_dir)
    shutil.copy(video, os.path.join(out_dir, "video.mp4"))
    shutil.rmtree(media, ignore_errors=True)
    return True, log, frames


def write_json(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)
