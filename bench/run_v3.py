"""v3 loop: spec -> RAG prompt -> Gemini -> lint -> feedback (runtime errors first, then lint errors). Max 8 attempts.

python bench/run_v3.py bench/specs/darjeeling_periph_read.yaml
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import yaml  # noqa: E402

from ipmotion.lint.harness import lint_script  # noqa: E402
import rag_pipeline  # noqa: E402
import runner  # noqa: E402   (only for extract_error / the fix-prompt wording, reused from v2)

sys.path.insert(0, os.path.join(C.ROOT, "bench"))
from spec_validator import validate  # noqa: E402

FIX_PROMPT = """The following Manim script was checked and has problems of ONE kind. Fix them.

## PROBLEMS ({kind})
{errors}

## THE CURRENT SCRIPT
```python
{script}
```

## SPEC (unchanged; the script must still realise all of it, and nothing else)
```yaml
{spec}```

## RELEVANT CONTEXT FROM THE IPMOTION LIBRARY
{context}

## RULES
1. Return ONLY the complete fixed Python script. No explanations.
2. Fix only the listed problems; keep everything else.
3. Do NOT use any Manim API that is not shown in the context above.
4. NEVER set config.pixel_width, config.pixel_height, or config.frame_width.
"""


def format_lint_errors(issues, limit=15) -> str:
    lines = []
    for i in issues[:limit]:
        objs = "; ".join(f"{o['name']} bbox={o['bbox']}" for o in i["objects"][:3])
        lines.append(f"- [{i['check']}] line {i['source_line']}, t={i['first_t']}s: {i['detail']}  ({objs})")
    if len(issues) > limit:
        lines.append(f"- ... and {len(issues) - limit} more errors of the same kinds")
    return "\n".join(lines)


def run(spec_path: str) -> dict:
    name = os.path.splitext(os.path.basename(spec_path))[0]
    with open(spec_path, encoding="utf-8") as fh:
        errs = validate(yaml.safe_load(fh))
    if errs:
        raise SystemExit("spec invalid:\n" + "\n".join(errs))
    run_dir = C.make_run_dir(name, "v3")
    rec = C.Recorder()
    rag_pipeline.retrieve_context = rec.guarded_retrieve(rag_pipeline.retrieve_context)
    request = C.user_request(spec_path)
    t0 = time.time()
    print(f"[v3] {name}: run dir {run_dir}")

    context = rag_pipeline.retrieve_context(request)
    script = C.call_llm(rag_pipeline.build_prompt(request, context))
    attempts, last_sig, same, frames, status, final_errors, crashed = [], None, 0, {}, "fail", [], True

    for n in range(1, C.MAX_ATTEMPTS + 1):
        adir = os.path.join(run_dir, f"attempt_{n}")
        os.makedirs(adir)
        spath = os.path.join(adir, "script.py")
        open(spath, "w", encoding="utf-8").write(script)
        scene = C.scene_name(script)
        rep = lint_script(spath, scene)
        C.write_json(os.path.join(adir, "lint.json"), rep)
        runtime = [i for i in rep["issues"] if i["check"] == "runtime_error"]
        lint_errs = [i for i in rep["issues"] if i["severity"] == "error" and i["check"] != "runtime_error"]
        kind, text = "pass", ""
        if runtime:
            kind, text = "runtime error", runtime[0]["traceback"][-2500:]
        elif lint_errs:
            kind, text = "lint errors", format_lint_errors(lint_errs)
        else:
            ok, log, frames = C.render_and_frames(spath, rep["scene"] or "Scene", adir)
            if not ok:
                kind, text = "runtime error", runner.extract_error(log)
        open(os.path.join(adir, "feedback.txt"), "w", encoding="utf-8").write(f"{kind}\n{text}")
        sig = (kind, text[:300])
        same = same + 1 if sig == last_sig else 0
        last_sig = sig
        attempts.append({"n": n, "kind": kind, "lint_errors": len(lint_errs), "runtime": bool(runtime or kind == "runtime error"),
                         "lint_warnings": rep["summary"]["warning"], "frames": {k: f"attempt_{n}/{v}" for k, v in frames.items()}})
        print(f"[v3] attempt {n}: {kind}" + (f" ({len(lint_errs)} lint errors)" if lint_errs else ""))
        if kind == "pass":
            status, final_errors, crashed = "pass", [], False
            break
        final_errors = [{"check": i["check"], "detail": i["detail"]} for i in (runtime or lint_errs)]
        crashed = kind == "runtime error"
        if n == C.MAX_ATTEMPTS or same >= 2:
            if same >= 2:
                status = "fail (same error repeated 3 times)"
            break
        fix_ctx = rag_pipeline.retrieve_context(f"Manim error: {text[:200]}", top_k=5)
        script = C.call_llm(FIX_PROMPT.format(kind=kind, errors=text, script=script,
                                              spec=C.prompt_spec(spec_path), context=fix_ctx))

    if not frames and not crashed:      # failed on lint only: still render the last attempt for the report
        ok, _, frames = C.render_and_frames(spath, rep["scene"] or "Scene", adir)
        attempts[-1]["frames"] = {k: f"attempt_{n}/{v}" for k, v in frames.items()}
    result = {"spec": name, "pipeline": "v3", "model": C.MODEL, "status": status, "attempts_used": len(attempts),
              "attempts": attempts, "crashed": crashed, "final_errors": final_errors,
              "final_lint_errors": len(final_errors) if not crashed else None, "seconds": round(time.time() - t0),
              "contexts": rec.contexts, "leak_check": "passed (assert on every retrieved context)",
              "final_frames": attempts[-1]["frames"]}
    C.write_json(os.path.join(run_dir, "final.json"), result)
    print(f"[v3] {status} after {len(attempts)} attempts in {result['seconds']}s")
    return result


if __name__ == "__main__":
    run(sys.argv[1])
