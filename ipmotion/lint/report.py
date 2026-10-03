"""Run all checks over a worker result and build the structured report."""
from __future__ import annotations

import os

from ipmotion.lint.checks import CHECKS, load_thresholds

SEV_ORDER = {"error": 0, "warning": 1, "info": 2}


def build_report(result: dict, script: str, thresholds: dict | None = None,
                 only: list[str] | None = None) -> dict:
    th = thresholds or load_thresholds()
    frame = result["frame"]
    merged: dict[tuple, dict] = {}

    def add(issue, snap_index, snap):
        key = (issue["check"], issue["severity"], issue["key"])
        cur = merged.get(key)
        if cur is None:
            issue = dict(issue)
            issue.update({"first_t": snap["t"], "last_t": snap["t"], "count": 1,
                          "first_snapshot": snap_index, "source_line": snap["line"],
                          "call": snap["call"]})
            merged[key] = issue
        else:
            cur["last_t"] = snap["t"]
            cur["count"] += 1

    for si, snap in enumerate(result["snapshots"]):
        by_id = {u["id"]: u for u in snap["units"]}
        for name, fn in CHECKS.items():
            if only and name not in only:
                continue
            for issue in fn(snap, frame, th):
                ignored_by = None
                for uid in issue["involved"]:
                    ign = by_id[uid].get("ignore", [])
                    if issue["check"] in ign or "all" in ign:
                        ignored_by = by_id[uid]["name"]
                        break
                if ignored_by:
                    issue = dict(issue, severity="info", ignored=True, ignored_by=ignored_by)
                add(issue, si, snap)

    issues = list(merged.values())
    if result.get("runtime_error"):
        e = result["runtime_error"]
        issues.append({"check": "runtime_error", "severity": "error", "objects": [],
                       "detail": e["traceback"].strip().splitlines()[-1] if e["traceback"].strip() else "error",
                       "traceback": e["traceback"], "first_t": None, "last_t": None, "count": 1,
                       "source_line": e.get("line", 0), "key": ("rt",), "involved": []})
    for i in issues:
        i.pop("key", None)
        i.pop("involved", None)
    issues.sort(key=lambda i: (SEV_ORDER[i["severity"]], i["check"], i.get("first_t") or 0))
    counts = {s: sum(1 for i in issues if i["severity"] == s) for s in SEV_ORDER}
    return {"file": script, "scene": result.get("scene"), "ok": counts["error"] == 0,
            "summary": counts, "snapshots": len(result["snapshots"]),
            "duration_s": result.get("seconds"), "frame": frame, "issues": issues}


def format_summary(report: dict, max_lines: int = 40) -> str:
    s = report["summary"]
    try:
        shown = os.path.relpath(report["file"])
    except ValueError:
        shown = report["file"]
    head = (f"{'PASS' if report['ok'] else 'FAIL'}  {shown}::{report['scene']}  "
            f"errors={s['error']} warnings={s['warning']} info={s['info']}  "
            f"({report['snapshots']} snapshots, {report['duration_s']}s)")
    lines = [head]
    by_check: dict[tuple, int] = {}
    for i in report["issues"]:
        by_check[(i["severity"], i["check"])] = by_check.get((i["severity"], i["check"]), 0) + 1
    if by_check:
        lines.append("  " + ", ".join(f"{sev}:{chk}x{n}" for (sev, chk), n in by_check.items()))
    for i in report["issues"][:max_lines]:
        t = "" if i["first_t"] is None else f" t={i['first_t']}"
        lines.append(f"  [{i['severity'][:4]}] {i['check']} L{i['source_line']}{t}: {i['detail']}")
    if len(report["issues"]) > max_lines:
        lines.append(f"  ... {len(report['issues']) - max_lines} more (use --json)")
    return "\n".join(lines)
