"""Split the wires a web run got wrong into buckets, so "wires 19/32" stops hiding its own cause.

    python bench/wire_buckets.py                 # the last few peppermint web runs
    python bench/wire_buckets.py runs/2026...    # specific run dirs

Three buckets, because they need three different fixes:
  unscorable  an end block's exact label is not in the input at all, so the wire can never score (fix the input)
  arrowhead   the right pair is joined, only the heads are wrong      (fix the notation the model is taught)
  wrong/miss  genuinely absent, or joined to the wrong block          (the real quality problem)
"""
from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bucket(run_dir: str) -> dict:
    j = json.load(open(os.path.join(run_dir, "final.json"), encoding="utf-8"))
    f = j["fidelity"]
    counts = {"unscorable": 0, "arrowhead": 0, "wrong_or_missing": 0}
    for d in f.get("issue_details", []):
        if not d.startswith("connection "):
            continue
        if "an end block is not drawn" in d:
            counts["unscorable"] += 1
        elif "wrong arrowheads" in d:
            counts["arrowhead"] += 1
        else:
            counts["wrong_or_missing"] += 1
    return {"run": os.path.basename(run_dir), "rep": j.get("rep"),
            "wires_ok": f["wires_ok"], "wires_total": f["wires_total"],
            "lint": j["final_lint_errors"], "extras": f["extras"],
            "blocks": f"{f['blocks_ok']}/{f['blocks_total']}",
            "regions": f"{f['regions_ok']}/{f['regions_total']}", **counts}


def main(dirs: list[str]) -> None:
    dirs = dirs or sorted(glob.glob(os.path.join(ROOT, "runs", "*_peppermint_web")))[-3:]
    rows = [bucket(d) for d in dirs if os.path.exists(os.path.join(d, "final.json"))]
    if not rows:
        sys.exit("no finished runs found")
    cols = ["rep", "wires_ok", "lint", "extras", "blocks", "regions", "unscorable", "arrowhead", "wrong_or_missing"]
    print(" | ".join(f"{c:>16}" for c in cols))
    for r in rows:
        print(" | ".join(f"{str(r[c]):>16}" for c in cols))
    n = len(rows)
    print(" | ".join(f"{v:>16}" for v in ["mean"] + [f"{sum(r[c] for r in rows) / n:.1f}" for c in
                                          ("wires_ok", "lint", "extras")] + ["", ""] +
                    [f"{sum(r[c] for r in rows) / n:.1f}" for c in ("unscorable", "arrowhead", "wrong_or_missing")]))


if __name__ == "__main__":
    main(sys.argv[1:])
