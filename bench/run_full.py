"""Full-diagram pipeline (no AI in the loop): story -> full spec -> deterministic drawing + player -> lint + checks
-> render -> closeness-to-reference numbers -> runs/<time>_<story>_v4/final.json.

python bench/run_full.py bench/stories/darjeeling_ibex_uart_read.yaml
"""
from __future__ import annotations

import collections
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402  (also pins the index dir; no model is used here)
import yaml  # noqa: E402

from ipmotion import fidelity  # noqa: E402
from ipmotion.fullspec import load_story, write_spec  # noqa: E402
from ipmotion.lint.harness import lint_script  # noqa: E402

sys.path.insert(0, os.path.join(C.ROOT, "bench"))
from spec_validator import validate  # noqa: E402


def run(story_path: str, rep_no: int = 1) -> dict:
    name = os.path.splitext(os.path.basename(story_path))[0]
    run_dir = C.make_run_dir(name, "v4")
    t0 = time.time()
    spec_path = os.path.join(run_dir, "spec.yaml")
    spec = write_spec(story_path, spec_path)
    errs = validate(spec)
    if errs:
        raise SystemExit("generated spec invalid:\n" + "\n".join(errs[:10]))
    story = load_story(story_path)
    with open(os.path.join(C.ROOT, "bench", "truth", f"{story['source']}.layout.yaml"), encoding="utf-8") as fh:
        layout = yaml.safe_load(fh)

    adir = os.path.join(run_dir, "attempt_1")
    os.makedirs(adir)
    script = os.path.join(adir, "script.py")
    abs_story = os.path.abspath(os.path.join(C.ROOT, story_path) if not os.path.isabs(story_path) else story_path)
    open(script, "w", encoding="utf-8").write(
        '"""Deterministic scene: drawn from the reference notes, no AI-written code."""\n'
        "from ipmotion.player import FullDiagramScene\n\n\n"
        f"class FullStory(FullDiagramScene):\n    STORY = {abs_story!r}\n")
    rep = lint_script(script, "FullStory", spec=spec, layout=layout)
    C.write_json(os.path.join(adir, "lint.json"), rep)
    runtime = [i for i in rep["issues"] if i["check"] == "runtime_error"]
    lint_errs = [i for i in rep["issues"] if i["severity"] == "error" and i["check"] != "runtime_error"]
    conf = [c for c in rep.get("conformance", []) if c["check"] != "conformance_static"]   # static check: AI-written scripts only
    frames, crashed = {}, bool(runtime)
    if not runtime:
        ok, log, frames = C.render_and_frames(script, "FullStory", adir)
        crashed = not ok
    # closeness numbers need the snapshots again: re-run the worker through the harness result file is not kept, so
    # lint_script keeps them in the report only as counts; recompute from a fresh worker run
    from ipmotion.lint.worker import load_scene, run_scene
    sys.path.insert(0, adir)
    res = run_scene(load_scene(script, "FullStory"), script) if not runtime else {"snapshots": []}
    fid = fidelity.score(res, spec, layout) if res.get("snapshots") else None
    final_errors = ([{"check": i["check"], "detail": i["detail"]} for i in runtime] +
                    [{"check": c["check"], "detail": c["detail"]} for c in conf] +
                    [{"check": i["check"], "detail": i["detail"]} for i in lint_errs])
    result = {"spec": name, "pipeline": "v4", "rep": rep_no, "model": "none (deterministic, no AI used)",
              "status": "pass" if not final_errors and not crashed else "has problems", "attempts_used": 1,
              "attempts": [{"n": 1, "kind": "pass" if not final_errors and not crashed else "has problems"}],
              "crashed": crashed, "final_errors": final_errors,
              "final_lint_errors": None if crashed else len(lint_errs), "final_conformance_errors": None if crashed else len(conf),
              "lint_by_check": dict(collections.Counter(i["check"] for i in rep["issues"] if i["severity"] == "error")),
              "lint_warnings": rep["summary"]["warning"], "seconds": round(time.time() - t0),
              "fidelity": fid, "final_frames": {k: f"attempt_1/{v}" for k, v in frames.items()},
              "reference": layout["source_image"], "source": story["source"],
              "leak_check": "not applicable: no retrieval, no prompt"}
    C.write_json(os.path.join(run_dir, "final.json"), result)
    if fid:
        print(f"[v4] blocks {fid['blocks_ok']}/{fid['blocks_total']}, regions {fid['regions_ok']}/{fid['regions_total']}, "
              f"wires {fid['wires_ok']}/{fid['wires_total']}, extras {fid['extras']}, layout {fid['layout_percent']}%, "
              f"unconfirmed {len(fid['unconfirmed'])}")
    print(f"[v4] lint errors {len(lint_errs)}, conformance errors {len(conf)}, crashed {crashed}, {result['seconds']}s")
    return result


if __name__ == "__main__":
    run(sys.argv[1])
