"""Build bench/report.html from the newest runs/<ts>_<spec>_<pipeline>/final.json per (spec, pipeline).
Frames are embedded (base64) so the report is one self-contained file. python bench/make_report.py
"""
from __future__ import annotations

import base64
import glob
import html
import json
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_ORDER = ["axi_write", "fifo_backpressure", "darjeeling_periph_read", "earlgrey_read", "peppermint_main"]


def latest():
    best = {}
    for f in glob.glob(os.path.join(ROOT, "runs", "*", "final.json")):
        r = json.load(open(f, encoding="utf-8"))
        key = (r["spec"], r["pipeline"])
        if key not in best or f > best[key][0]:
            best[key] = (f, r)
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
    body = []
    for s in specs:
        cols = []
        for p in ("v2", "v3"):
            if (s, p) in best:
                f, r = best[(s, p)]
                cols.append(f"<div class='col'><h3>{p}</h3>{card(os.path.dirname(f), r)}</div>")
            else:
                cols.append(f"<div class='col'><h3>{p}</h3><p>not run</p></div>")
        body.append(f"<section><h2>{html.escape(s)}</h2><div class='row'>{''.join(cols)}</div></section>")
    page = f"""<!doctype html><meta charset="utf-8"><title>IPMotion benchmark report</title>
<style>body{{font:14px system-ui;margin:24px;background:#0b0f14;color:#dbe4ee}}h1,h2,h3{{font-weight:600}}
.row{{display:flex;gap:20px;flex-wrap:wrap}}.col{{flex:1 1 540px;min-width:0}}.card{{background:#121a24;border-radius:8px;padding:12px}}
table{{border-collapse:collapse;width:100%}}th{{text-align:left;color:#8aa0b6;padding:3px 10px 3px 0;font-weight:500;white-space:nowrap}}
.ok{{color:#39ff14}}.warn{{color:#ffd700}}.bad{{color:#ff5c7a}}figure{{margin:8px 0}}img{{width:100%;border-radius:4px}}
figcaption{{color:#8aa0b6;font-size:12px}}code{{color:#9ad}}details{{margin:8px 0}}</style>
<h1>IPMotion benchmark: v2 vs v3</h1>
<p>Generated {datetime.now():%Y-%m-%d %H:%M}. Same model, same clean (manifest-only) index and same prompt text for both pipelines;
v3 additionally lints each attempt and feeds back runtime errors first, then lint errors. v2 only sees tracebacks
(its final script is linted afterwards for measurement). Nothing was tuned per spec.</p>{''.join(body)}"""
    out = os.path.join(ROOT, "bench", "report.html")
    open(out, "w", encoding="utf-8").write(page)
    print("wrote", out, f"({os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    main()
