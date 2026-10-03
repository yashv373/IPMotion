"""Re-score existing v2 runs with the current lint rules + the dynamic spec-conformance checks. No LLM calls.

v2 never saw the LABELS/BANNERS rule, so the static conformance checks (LABELS block present, no hand-typed text)
are NOT applied to it; only the dynamic ones (blocks, domains, connections incl. arrowheads, banners, extras).
Result is stored under final.json["rescore"]; the original fields are left untouched.

python bench/rescore_v2.py
"""
from __future__ import annotations

import collections
import glob
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ipmotion.lint.harness import lint_script  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    for f in sorted(glob.glob(os.path.join(ROOT, "runs", "*_v2", "final.json"))):
        d = os.path.dirname(f)
        r = json.load(open(f, encoding="utf-8"))
        atts = sorted(glob.glob(os.path.join(d, "attempt_*", "script.py")), key=lambda p: int(p.split("attempt_")[1].split(os.sep)[0]))
        if not atts:
            continue
        spec = yaml.safe_load(open(os.path.join(ROOT, "bench", "specs", f"{r['spec']}.yaml"), encoding="utf-8"))
        rep = lint_script(atts[-1], spec=spec)
        runtime = [i for i in rep["issues"] if i["check"] == "runtime_error"]
        lint = [i for i in rep["issues"] if i["severity"] == "error" and i["check"] != "runtime_error"]
        conf = [c for c in rep.get("conformance", []) if c["check"] != "conformance_static"]
        r["rescore"] = {
            "script": os.path.relpath(atts[-1], d), "runtime_error": bool(runtime),
            "lint_errors": len(lint), "lint_by_check": dict(collections.Counter(i["check"] for i in lint)),
            "conformance_errors": len(conf), "conformance_by_check": dict(collections.Counter(c["check"] for c in conf)),
            "conformance_details": [c["detail"] for c in conf][:12],
            "note": "dynamic conformance only (v2 never saw the LABELS/BANNERS rule); lint with transient-packet rules",
        }
        json.dump(r, open(f, "w", encoding="utf-8"), indent=2)
        print(f"v2 rep{r.get('rep')}: lint {len(lint)} {r['rescore']['lint_by_check']} | conformance {len(conf)} {r['rescore']['conformance_by_check']}")


if __name__ == "__main__":
    main()
