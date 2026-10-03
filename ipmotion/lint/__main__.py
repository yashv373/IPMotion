"""python -m ipmotion.lint <script.py> [Scene] [--json out.json] [--max-lines N]"""
import argparse
import json
import sys

from ipmotion.lint.harness import lint_script
from ipmotion.lint.report import format_summary


def main():
    ap = argparse.ArgumentParser(prog="ipmotion.lint")
    ap.add_argument("script")
    ap.add_argument("scene", nargs="?")
    ap.add_argument("--json", help="write the full report here")
    ap.add_argument("--max-lines", type=int, default=40)
    a = ap.parse_args()
    report = lint_script(a.script, a.scene)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    print(format_summary(report, a.max_lines))
    sys.exit(0 if report["ok"] else 1)


main()
