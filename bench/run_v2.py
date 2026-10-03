"""v2 pipeline (runner.py unchanged: RAG -> Gemini -> manim render -> feed back tracebacks only).
Same model, same clean index, same prompt text as v3. Afterwards the final script is measured with the lint
(v2 never sees it) and rendered with the same frame extraction.

python bench/run_v2.py bench/specs/darjeeling_periph_read.yaml
"""
from __future__ import annotations

import glob
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import yaml  # noqa: E402

from ipmotion.lint.harness import lint_script  # noqa: E402
import rag_pipeline  # noqa: E402
import runner  # noqa: E402

sys.path.insert(0, os.path.join(C.ROOT, "bench"))
from spec_validator import validate  # noqa: E402


def run(spec_path: str) -> dict:
    name = os.path.splitext(os.path.basename(spec_path))[0]
    with open(spec_path, encoding="utf-8") as fh:
        errs = validate(yaml.safe_load(fh))
    if errs:
        raise SystemExit("spec invalid:\n" + "\n".join(errs))
    run_dir = C.make_run_dir(name, "v2")
    rec = C.Recorder()
    guarded = rec.guarded_retrieve(rag_pipeline.retrieve_context)
    rag_pipeline.retrieve_context = guarded
    runner.retrieve_context = guarded
    before = set(glob.glob(os.path.join(runner.OUTPUT_DIR, "ipmotion_*")))
    t0 = time.time()
    print(f"[v2] {name}: run dir {run_dir}")
    final_path = runner.run_pipeline(C.user_request(spec_path), model=C.MODEL)
    seconds = round(time.time() - t0)

    new = sorted(set(glob.glob(os.path.join(runner.OUTPUT_DIR, "ipmotion_*"))) - before)
    gen_dir = new[-1] if new else None
    attempts = []
    last_script = None
    if gen_dir:
        for f in sorted(glob.glob(os.path.join(gen_dir, "attempt_*.py")), key=lambda p: int(p.rsplit("_", 1)[1][:-3])):
            n = int(f.rsplit("_", 1)[1][:-3])
            adir = os.path.join(run_dir, f"attempt_{n}")
            os.makedirs(adir, exist_ok=True)
            shutil.copy(f, os.path.join(adir, "script.py"))
            err = os.path.join(gen_dir, f"error_{n}.txt")
            if os.path.exists(err):
                shutil.copy(err, os.path.join(adir, "traceback.txt"))
            attempts.append({"n": n, "render_ok": not os.path.exists(err)})
            last_script = os.path.join(adir, "script.py")
    crashed = final_path is None
    lint_summary, final_errors, frames, status = None, [], {}, "fail"
    if last_script:
        sc = C.scene_name(open(last_script, encoding="utf-8").read()) or "Scene"
        rep = lint_script(last_script, None)
        rt = [i for i in rep["issues"] if i["check"] == "runtime_error"]
        lint_summary = rep["summary"]
        final_errors = [{"check": i["check"], "detail": i["detail"]} for i in rep["issues"] if i["severity"] == "error"]
        C.write_json(os.path.join(run_dir, "final_lint.json"), rep)
        if not crashed:
            status = "renders (v2 success criterion)"
            ok, log, frames = C.render_and_frames(last_script, rep["scene"] or sc, os.path.dirname(last_script))
            frames = {k: f"{os.path.basename(os.path.dirname(last_script))}/{v}" for k, v in frames.items()}
            crashed = not ok
        elif rt:
            pass
    result = {"spec": name, "pipeline": "v2", "model": C.MODEL, "status": status, "attempts_used": len(attempts),
              "attempts": attempts, "crashed": crashed, "final_errors": final_errors,
              "final_lint_errors": None if (crashed and not frames) else len(final_errors),
              "final_lint_summary": lint_summary, "seconds": seconds, "contexts": rec.contexts,
              "leak_check": "passed (assert on every retrieved context)", "final_frames": frames,
              "note": "v2 never sees lint; lint measured afterwards on the final/last script"}
    C.write_json(os.path.join(run_dir, "final.json"), result)
    print(f"[v2] {status}, attempts {len(attempts)}, lint errors {result['final_lint_errors']}")
    return result


if __name__ == "__main__":
    run(sys.argv[1])
