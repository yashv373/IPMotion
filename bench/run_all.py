"""Resumable benchmark driver.

python bench/run_all.py darjeeling_periph_read --reps 3
Jobs run in the order v2#1, v3#1, v2#2, v3#2, ... State is saved to runs/bench_state.json after every job.
On a daily-quota error the current job is marked `interrupted` (its partial run dir is kept but ignored by the
report), the state is saved and the driver exits with code 3. Re-running the same command resumes with the
remaining jobs; finished jobs are never repeated. State from a different model is refused (never mixed).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

STATE = os.path.join(C.ROOT, "runs", "bench_state.json")


def load_state() -> dict:
    if os.path.exists(STATE):
        st = json.load(open(STATE, encoding="utf-8"))
        if st.get("model") != C.MODEL:
            raise SystemExit(f"state file was written for model {st.get('model')!r}, current model is {C.MODEL!r}. "
                             "Runs on different models are never mixed; move runs/bench_state.json away to start fresh.")
        return st
    return {"model": C.MODEL, "jobs": {}}


def save_state(st: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--reps", type=int, default=3)
    a = ap.parse_args()
    spec_path = os.path.join(C.ROOT, "bench", "specs", f"{a.spec}.yaml")
    import run_v2, run_v3
    runners = {"v2": run_v2.run, "v3": run_v3.run}
    st = load_state()
    for rep in range(1, a.reps + 1):
        for pipe in ("v2", "v3"):
            key = f"{a.spec}|{pipe}|{rep}"
            if st["jobs"].get(key, {}).get("status") == "done":
                print(f"skip {key} (done)")
                continue
            print(f"=== {key} ({C.MODEL})")
            st["jobs"][key] = {"status": "running"}
            save_state(st)
            try:
                r = runners[pipe](spec_path, rep)
            except C.DailyQuotaError as e:
                st["jobs"][key] = {"status": "interrupted", "reason": "daily quota", "detail": str(e)[:200]}
                save_state(st)
                print(f"DAILY QUOTA reached during {key}. State saved; re-run this command to resume.")
                return 3
            st["jobs"][key] = {"status": "done", "result": r["status"], "attempts": r["attempts_used"]}
            save_state(st)
    print("all jobs done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
