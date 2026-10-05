"""Score what the WEBSITE actually produces: one shot, no lint, no repair.

This is the only measurement that matches the promise on the site -- a stranger pastes a block diagram and a
story, hits Generate, downloads the .py and runs it. Every other benchmark here gives the model feedback and
several tries; this one gives it exactly what web/app.js gives it, once.

The prompt is assembled byte-for-byte the way web/app.js assembles it. If that file changes, change this too,
or the number stops meaning anything.

    python bench/run_web.py bench/web_inputs/peppermint.txt bench/web_inputs/peppermint.story.txt --reps 3

Held out on purpose: Peppermint is never put in web/rag_context, so scoring against it is an honest exam.
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

from ipmotion import fidelity  # noqa: E402
from ipmotion.fullspec import load_story, make_full_spec  # noqa: E402
from ipmotion.lint.harness import lint_script  # noqa: E402

CTX = ["00_rules", "10_library_api", "20_example_axi", "25_example_earlgrey", "27_example_wired", "30_user_input_notes"]
WEB = os.path.join(C.ROOT, "web", "rag_context")


def build_prompt(story: str, diagram: str) -> str:
    """Identical to buildPrompt() in web/app.js: the four context files joined with '=====', then the user's
    two inputs, then the output instruction."""
    parts = [open(os.path.join(WEB, f"{n}.txt"), encoding="utf-8").read() for n in CTX]
    return ("\n\n=====\n\n".join(parts) +
            "\n\n=====\n\n## USER BLOCK DIAGRAM\n" + (diagram.strip() or "(none given)") +
            "\n\n## USER STORY\n" + story.strip() +
            "\n\n## OUTPUT\nReturn ONLY the complete Python script.")


def clean_response(t: str) -> str:
    """Identical to cleanResponse() in web/app.js."""
    m = re.search(r"```(?:python)?\s*\n([\s\S]*?)```", t)
    return ((m.group(1) if m else t).strip() + "\n")


def run_once(diagram_path: str, story_path: str, spec: dict | None, rep: int) -> dict:
    name = os.path.splitext(os.path.basename(diagram_path))[0]
    run_dir = C.make_run_dir(name, "web")
    t0 = time.time()
    diagram = open(diagram_path, encoding="utf-8").read()
    story = open(story_path, encoding="utf-8").read()
    prompt = build_prompt(story, diagram)

    adir = os.path.join(run_dir, "attempt_1")
    os.makedirs(adir, exist_ok=True)
    open(os.path.join(run_dir, "prompt.txt"), "w", encoding="utf-8").write(prompt)

    script = os.path.join(adir, "script.py")
    try:
        code = clean_response(C.call_llm(prompt))
    except Exception as exc:                       # quota, rate limit, network: a real visitor sees this too
        result = {"spec": name, "pipeline": "web", "rep": rep, "model": C.MODEL, "status": "no answer",
                  "error": str(exc)[:500], "seconds": round(time.time() - t0)}
        C.write_json(os.path.join(run_dir, "final.json"), result)
        print(f"[web] rep {rep}: no answer from the model -- {str(exc)[:160]}")
        return result
    open(script, "w", encoding="utf-8").write(code)

    scene = C.scene_name(code)                     # scene_name reads the source text, not the path
    if not scene:
        result = {"spec": name, "pipeline": "web", "rep": rep, "model": C.MODEL, "status": "no scene",
                  "lines": code.count("\n"), "seconds": round(time.time() - t0)}
        C.write_json(os.path.join(run_dir, "final.json"), result)
        print(f"[web] rep {rep}: the file has no Scene class")
        return result

    # exactly the checks the website does NOT do -- that is the point: they tell us what the visitor would get.
    # With no spec (a shape we have no reference answer for) only the geometry is judged: does it run, does it
    # render, and is the picture clean. That still answers "did this change make the output tidier".
    rep_json = lint_script(script, scene, spec=spec) if spec else lint_script(script, scene)
    runtime = [i for i in rep_json["issues"] if i["check"] == "runtime_error"]
    lint_errs = [i for i in rep_json["issues"] if i["severity"] == "error" and i["check"] != "runtime_error"]
    conf = [c for c in rep_json.get("conformance", []) if c["check"] != "conformance_static"]

    frames, crashed = {}, bool(runtime)
    if not runtime:
        ok, _log, frames = C.render_and_frames(script, scene, adir)
        crashed = not ok

    fid = None
    if not runtime and spec:
        from ipmotion.lint.worker import load_scene, run_scene
        sys.path.insert(0, adir)
        try:
            res = run_scene(load_scene(script, scene), script)
            fid = fidelity.score(res, spec, {"blocks": {}}) if res.get("snapshots") else None
        except Exception:
            fid = None

    result = {
        "spec": name, "pipeline": "web", "rep": rep, "model": C.MODEL,
        "status": "runs clean" if not (crashed or lint_errs or conf) else "has problems",
        "crashed": crashed, "lines": code.count("\n"),
        "final_lint_errors": None if crashed else len(lint_errs),
        "final_conformance_errors": None if crashed else len(conf),
        "lint_by_check": dict(collections.Counter(i["check"] for i in rep_json["issues"] if i["severity"] == "error")),
        "final_errors": ([{"check": i["check"], "detail": i["detail"]} for i in runtime] +
                         [{"check": c["check"], "detail": c["detail"]} for c in conf][:10] +
                         [{"check": i["check"], "detail": i["detail"]} for i in lint_errs][:10]),
        "fidelity": fid, "final_frames": {k: f"attempt_1/{v}" for k, v in frames.items()},
        "seconds": round(time.time() - t0),
        "note": "one shot, exactly what web/app.js sends; no lint, no conformance and no repair in the browser",
    }
    C.write_json(os.path.join(run_dir, "final.json"), result)
    blocks = f"{fid['blocks_ok']}/{fid['blocks_total']}" if fid else "n/a"
    print(f"[web] rep {rep}: {result['status']}, crashed {crashed}, lint errors "
          f"{result['final_lint_errors']}, spec errors {result['final_conformance_errors']}, blocks {blocks}, "
          f"{result['seconds']}s")
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("diagram")
    ap.add_argument("story")
    ap.add_argument("--spec-story", default="bench/stories/peppermint_ibex_retention_read.yaml",
                    help="the story YAML whose full spec is the yardstick (the exam answer; never sent to the model)")
    ap.add_argument("--no-spec", action="store_true",
                    help="score geometry only. For a shape we have no reference answer for, where the question "
                         "is whether the drawing comes out clean rather than whether it matches a known diagram.")
    ap.add_argument("--reps", type=int, default=1)
    a = ap.parse_args()
    spec = None if a.no_spec else make_full_spec(load_story(a.spec_story))
    results = []
    for r in range(1, a.reps + 1):
        try:
            results.append(run_once(a.diagram, a.story, spec, r))
        except C.DailyQuotaError as exc:
            # DailyQuotaError is a BaseException on purpose, so `except Exception` cannot swallow it. Stop
            # cleanly and still report the reps that did finish, instead of losing them all to a traceback.
            print(f"[web] rep {r}: daily quota exhausted, stopping here -- {str(exc)[:150]}")
            break
    if not results:
        print("[web] no runs completed.")
        return
    clean = sum(1 for x in results if x.get("status") == "runs clean")
    print(f"\n[web] BASELINE over {len(results)} run(s): {clean} came out clean with no human help.")


if __name__ == "__main__":
    main()
