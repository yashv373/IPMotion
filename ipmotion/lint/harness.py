"""Lint a scene script in an isolated subprocess and return the JSON-able report."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

from ipmotion.lint.report import build_report

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def lint_script(script: str, scene: str | None = None, timeout: int = 90,
                thresholds: dict | None = None, only: list[str] | None = None, spec: dict | None = None) -> dict:
    """With spec=..., the report also carries report['conformance'] (list of error issues) and conformance_ok."""
    script = os.path.abspath(script)
    if thresholds is None and spec is not None and spec.get("scope") == "full":
        from ipmotion.lint.checks import load_thresholds
        thresholds = load_thresholds(full=True)
    work = tempfile.mkdtemp(prefix="ipm_lintrun_")
    out = os.path.join(work, "snapshots.json")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([PROJECT_ROOT, os.path.dirname(script), env.get("PYTHONPATH", "")])
    cmd = [sys.executable, "-m", "ipmotion.lint.worker", script] + ([scene] if scene else []) + [out]
    try:
        proc = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        result = {"snapshots": [], "frame": {"width": 14.2222, "height": 8.0}, "scene": scene,
                  "runtime_error": {"traceback": f"TimeoutError: lint exceeded {timeout}s", "line": 0},
                  "seconds": timeout}
        return _finish(build_report(result, script, thresholds, only), result, script, spec)
    if not os.path.exists(out):
        result = {"snapshots": [], "frame": {"width": 14.2222, "height": 8.0}, "scene": scene,
                  "runtime_error": {"traceback": (proc.stderr or "worker crashed")[-3000:], "line": 0},
                  "seconds": 0}
    else:
        with open(out, encoding="utf-8") as fh:
            result = json.load(fh)
    return _finish(build_report(result, script, thresholds, only), result, script, spec)


def _finish(report: dict, result: dict, script: str, spec: dict | None) -> dict:
    if spec is not None:
        from ipmotion import conformance
        with open(script, encoding="utf-8") as fh:
            text = fh.read()
        report["conformance"] = conformance.check(text, result, spec)
        report["conformance_ok"] = not report["conformance"]
    return report
