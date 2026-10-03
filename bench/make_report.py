"""Build bench/report.html from the newest runs/<ts>_<spec>_<pipeline>/final.json per (spec, pipeline).
Frames are embedded (base64) so the report is one self-contained file. python bench/make_report.py
"""
from __future__ import annotations

import base64
import glob
import html
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_ORDER = ["axi_write", "fifo_backpressure", "darjeeling_periph_read", "earlgrey_read", "peppermint_main"]


def latest():
    """All completed runs on the pinned model, newest per (spec, pipeline, rep). Other models are excluded."""
    sys.path.insert(0, os.path.join(ROOT, "bench"))
    from common import MODEL
    best, skipped = {}, 0
    for f in sorted(glob.glob(os.path.join(ROOT, "runs", "*", "final.json"))):
        r = json.load(open(f, encoding="utf-8"))
        if r.get("model") != MODEL:
            skipped += 1
            continue
        best[(r["spec"], r["pipeline"], r.get("rep", 1))] = (f, r)     # later file (newer timestamp) wins
    latest.skipped, latest.model = skipped, MODEL
    return best


def img(run_dir, rel, label):
    p = os.path.join(run_dir, rel)
    if not os.path.exists(p):
        return ""
    b = base64.b64encode(open(p, "rb").read()).decode()
    return f'<figure><img src="data:image/png;base64,{b}" alt="{label}"><figcaption>{label}</figcaption></figure>'


def card(run_dir, r):
    ok = r["status"].startswith(("pass", "renders"))
    cls = "ok" if r["status"].startswith("pass") else ("warn" if ok else "bad")
    lint = r.get("final_lint_errors")
    lint_txt = "n/a (crashed, no lint result)" if lint is None else f"{lint} error(s)"
    rows = [("pipeline", f"<b>{r['pipeline']}</b> ({html.escape(r['model'])})"),
            ("status", f"<span class='{cls}'>{html.escape(r['status'])}</span>"),
            ("attempts used", f"{r['attempts_used']} / 8"),
            ("crashed at the end", "yes" if r["crashed"] else "no"),
            ("final lint errors", lint_txt), ("wall time", f"{r['seconds']} s"),
            ("leak check", html.escape(r["leak_check"]))]
    t = "".join(f"<tr><th>{a}</th><td>{b}</td></tr>" for a, b in rows)
    errs = "".join(f"<li><code>{html.escape(e['check'])}</code> {html.escape(e['detail'][:220])}</li>" for e in r["final_errors"][:8])
    more = f"<li>... {len(r['final_errors']) - 8} more</li>" if len(r["final_errors"]) > 8 else ""
    trail = "".join(
        f"<li>attempt {a['n']}: " + html.escape(a.get("kind", "render ok" if a.get("render_ok") else "render FAILED")) + "</li>"
        for a in r["attempts"])
    fr = r.get("final_frames") or {}
    imgs = "".join(img(run_dir, fr[k], lbl) for k, lbl in (("key_25", "keyframe 25%"), ("key_50", "keyframe 50%"),
                                                           ("key_75", "keyframe 75%"), ("last", "last frame")) if k in fr)
    return (f"<div class='card'><table>{t}</table>"
            f"<details><summary>attempt trail</summary><ul>{trail}</ul></details>"
            f"<details {'open' if errs else ''}><summary>final errors</summary><ul>{errs}{more or ''}</ul></details>"
            f"<div class='frames'>{imgs or '<p class=bad>no frames (script did not render)</p>'}</div></div>")


def main():
    best = latest()
    specs = [s for s in SPEC_ORDER if any(k[0] == s for k in best)] + sorted({k[0] for k in best} - set(SPEC_ORDER))
    summary = []
    body = []
    for s in specs:
        cols = []
        for p in ("v2", "v3"):
            reps = sorted(k[2] for k in best if k[0] == s and k[1] == p)
            if reps:
                cards = "".join(f"<h4>run {rp}</h4>" + card(os.path.dirname(best[(s, p, rp)][0]), best[(s, p, rp)][1]) for rp in reps)
                rs = [best[(s, p, rp)][1] for rp in reps]
                okc = sum(1 for r in rs if r["status"].startswith("pass"))
                rn = sum(1 for r in rs if r["status"].startswith(("pass", "renders")))
                summary.append(f"<tr><td>{html.escape(s)}</td><td>{p}</td><td>{len(rs)}</td><td>{rn}</td><td>{okc}</td>"
                               f"<td>{', '.join(str(r['attempts_used']) for r in rs)}</td>"
                               f"<td>{', '.join('crash' if r['final_lint_errors'] is None else str(r['final_lint_errors']) for r in rs)}</td></tr>")
                cols.append(f"<div class='col'><h3>{p} ({len(reps)} run{'s' if len(reps) > 1 else ''})</h3>{cards}</div>")
            else:
                cols.append(f"<div class='col'><h3>{p}</h3><p>not run</p></div>")
        body.append(f"<section><h2>{html.escape(s)}</h2><div class='row'>{''.join(cols)}</div></section>")
    table = ("<table class='sum'><tr><th>spec</th><th>pipeline</th><th>runs</th><th>rendered</th><th>pass (0 lint errors)</th>"
             "<th>attempts per run</th><th>final lint errors per run</th></tr>" + "".join(summary) + "</table>")
    page = f"""<!doctype html><meta charset="utf-8"><title>IPMotion benchmark report</title>
<style>body{{font:14px system-ui;margin:24px;background:#0b0f14;color:#dbe4ee}}h1,h2,h3{{font-weight:600}}
.row{{display:flex;gap:20px;flex-wrap:wrap}}.col{{flex:1 1 540px;min-width:0}}.card{{background:#121a24;border-radius:8px;padding:12px}}
table{{border-collapse:collapse;width:100%}}th{{text-align:left;color:#8aa0b6;padding:3px 10px 3px 0;font-weight:500;white-space:nowrap}}
.ok{{color:#39ff14}}.warn{{color:#ffd700}}.bad{{color:#ff5c7a}}figure{{margin:8px 0}}img{{width:100%;border-radius:4px}}
figcaption{{color:#8aa0b6;font-size:12px}}code{{color:#9ad}}details{{margin:8px 0}}.sum td,.sum th{{padding:4px 14px 4px 0;border-bottom:1px solid #223}}h4{{margin:14px 0 4px;color:#8aa0b6}}</style>
<h1>IPMotion benchmark: v2 vs v3</h1>
<p><b>Model: <code>{latest.model}</code></b> for every run shown ({latest.skipped} run(s) on other models excluded, never mixed).
Generated {datetime.now():%Y-%m-%d %H:%M}. Same model, same clean (manifest-only) index and same prompt text for both pipelines;
v3 additionally lints each attempt and feeds back runtime errors first, then lint errors. v2 only sees tracebacks
(its final script is linted afterwards for measurement). Nothing was tuned per spec.</p>{table}{''.join(body)}"""
    out = os.path.join(ROOT, "bench", "report.html")
    open(out, "w", encoding="utf-8").write(page)
    print("wrote", out, f"({os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    main()
