"""Build bench/report.html: the reference diagram next to the animation the computer made, in plain words.

Reads the newest runs/<time>_<spec>_<pipeline>/final.json per (spec, pipeline, run number). Only runs made with the
pinned model are shown (v3 also needs the current prompt version). Everything is embedded, so the file is standalone.
python bench/make_report.py
"""
from __future__ import annotations

import base64
import collections
import glob
import html
import io
import json
import os
import sys
from datetime import datetime

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))
SPEC_ORDER = ["axi_write", "fifo_backpressure", "darjeeling_periph_read", "earlgrey_read", "peppermint_main"]

# The reference ("golden") picture for a test, and where its blocks are on that picture (pixels), used only to
# draw yellow boxes around the parts the test is about.
REFS = {
    "darjeeling_periph_read": {
        "image": "opentitan_archs/top_darjeeling_block_diagram.png",
        "name": "OpenTitan Darjeeling block diagram",
        "boxes": {"ibex_core": (60, 137, 237, 222), "main_tlul_crossbar": (55, 264, 463, 327),
                  "main_sram": (265, 200, 358, 248), "otbn": (57, 345, 152, 375),
                  "peri_tlul_crossbar": (625, 137, 695, 583), "timers": (512, 137, 608, 183),
                  "gpio_32bit": (712, 137, 808, 183), "spi_host": (712, 283, 808, 328),
                  "uart_i2c": (712, 345, 808, 392)},
    },
}

PLAIN = {   # check name -> how to say it in plain words
    "out_of_frame": "parts of the drawing are cut off by the edge of the picture",
    "text_overlap": "text overlaps other text, a line, or a block",
    "text_occluded": "text is hidden behind a shape",
    "min_spacing": "blocks are too close together, overlap, or stick out of their region",
    "dangling_endpoint": "a line ends in empty space",
    "min_text_size": "text is too small to read",
    "conformance_block": "a block from the spec is missing (or its name is different)",
    "conformance_domain": "a region (domain) label or its contents don't match the spec",
    "conformance_connection": "a line from the spec is missing, or its arrow is wrong",
    "conformance_banner": "a step title (banner) is different from the spec or never shown",
    "conformance_sequence": "a label that should travel along a line (like 'Read req') is never shown",
    "conformance_extra": "something was drawn that is not in the spec",
    "conformance_static": "the script typed a name by hand instead of copying it from the spec",
    "runtime_error": "the script crashed",
}


def b64(path_or_bytes):
    data = path_or_bytes if isinstance(path_or_bytes, bytes) else open(path_or_bytes, "rb").read()
    return base64.b64encode(data).decode()


def reference_png(spec: str):
    """Reference picture with yellow boxes around the blocks this test uses -> (png bytes, w, h) or None."""
    ref = REFS.get(spec)
    if not ref:
        return None
    im = Image.open(os.path.join(ROOT, ref["image"])).convert("RGB")
    d = ImageDraw.Draw(im)
    for b in ref["boxes"].values():
        d.rectangle(b, outline=(255, 200, 0), width=4)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue(), im.width, im.height


def load_runs():
    from common import MODEL, PROMPT_VERSION
    runs, skipped = {}, 0
    for f in sorted(glob.glob(os.path.join(ROOT, "runs", "*", "final.json"))):
        r = json.load(open(f, encoding="utf-8"))
        if r["pipeline"] == "v4":                       # drawn by code, no AI model involved
            runs[(r["spec"], "v4", r.get("rep", 1))] = (os.path.dirname(f), r)
            continue
        if r.get("model") != MODEL or (r["pipeline"] == "v3" and r.get("prompt_version") != PROMPT_VERSION):
            skipped += 1
            continue
        runs[(r["spec"], r["pipeline"], r.get("rep", 1))] = (os.path.dirname(f), r)
    return runs, skipped, MODEL


def problems(r) -> collections.Counter:
    if "rescore" in r:
        c = collections.Counter(r["rescore"]["lint_by_check"])
        c.update(r["rescore"]["conformance_by_check"])
        return c
    return collections.Counter(e["check"] for e in r["final_errors"])


def totals(r):
    if "rescore" in r:
        return r["rescore"]["lint_errors"], r["rescore"]["conformance_errors"]
    return r.get("final_lint_errors"), r.get("final_conformance_errors")


def is_clean(r):
    l, c = totals(r)
    return not r["crashed"] and l == 0 and c == 0


def verdict(r):
    if r["crashed"]:
        return "bad", "The script crashed, so there is no animation."
    if is_clean(r):
        return "ok", "Passed both checks: the layout is clean and it matches the spec."
    n = sum(problems(r).values())
    return "warn", f"It draws an animation, but {n} problem{'s' if n != 1 else ''} remain."


def img_tag(run_dir, rel, cap, cls="shot"):
    p = os.path.join(run_dir, rel) if rel else ""
    if not rel or not os.path.exists(p):
        return ""
    return f'<figure class="{cls}"><img src="data:image/png;base64,{b64(p)}" alt="{html.escape(cap)}"><figcaption>{cap}</figcaption></figure>'


def trail_word(a):
    if "kind" in a:
        return {"pass": "passed both checks", "runtime error": "the script crashed",
                "spec conformance errors": "did not match the spec", "lint errors": "layout problems"}.get(a["kind"], a["kind"])
    return "drew an animation" if a.get("render_ok") else "crashed while rendering (the old pipeline then tried again)"


def run_card(spec, run_dir, r, has_ref):
    kind, line = verdict(r)
    fr = r.get("final_frames") or {}
    last = img_tag(run_dir, fr.get("last", ""), "What the computer drew (last moment of the animation)", "big")
    if not last:
        last = '<div class="nopic big">No picture: the script did not produce an animation.</div>'
    ref = (f'<figure class="ref"><div class="refpic r_{spec}"></div><figcaption>REFERENCE (the real diagram). '
           f'Yellow boxes = the parts this test draws.</figcaption></figure>') if has_ref else \
          '<figure class="ref"><div class="nopic">No reference picture for this test yet.</div></figure>'
    p = problems(r)
    lis = "".join(f"<li><b>{n}</b> &times; {html.escape(PLAIN.get(k, k))}</li>" for k, n in p.most_common())
    details = ""
    if "rescore" in r:
        det = r["rescore"].get("conformance_details", [])
        if det:
            details = "<details><summary>Exact spec mismatches</summary><ul>" + "".join(
                f"<li>{html.escape(d[:240])}</li>" for d in det) + "</ul></details>"
    elif r.get("final_errors"):
        details = "<details><summary>Exact problems</summary><ul>" + "".join(
            f"<li>{html.escape(e['detail'][:240])}</li>" for e in r["final_errors"][:10]) + "</ul></details>"
    trail = "".join(f"<li>try {a['n']}: {html.escape(trail_word(a))}</li>" for a in r["attempts"])
    keys = "".join(img_tag(run_dir, fr[k], cap, "small") for k, cap in
                   (("key_25", "about 25% through"), ("key_50", "about half way"), ("key_75", "about 75% through")) if k in fr)
    wrong = ('<p class="lbl">What is still wrong, in plain words:</p><ul>' + lis + '</ul>') if lis else ''
    more = ('<p class="lbl">Other moments of the same animation:</p><div class="row">' + keys + '</div>') if keys else ''
    return f"""<div class="card">
<div class="verdict {kind}">{html.escape(line)}</div>
<div class="pair">{ref}{last}</div>
{wrong}{details}
<p class="facts">Tries used: <b>{r['attempts_used']}</b> of 8 &middot; crashed at the end: <b>{'yes' if r['crashed'] else 'no'}</b> &middot; time: {r['seconds']} s</p>
<details><summary>What happened on each try</summary><ul>{trail}</ul></details>
{more}
</div>"""


def full_reference(source_png: str):
    im = Image.open(os.path.join(ROOT, source_png)).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue(), im.width, im.height


def crop_png(source_png: str, box, pad=28, max_w=420):
    im = Image.open(os.path.join(ROOT, source_png)).convert("RGB")
    x0, y0, x1, y1 = max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad)
    c = im.crop((x0, y0, x1, y1))
    k = max(1, min(4, max_w // max(c.width, 1)))
    c = c.resize((c.width * k, c.height * k), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    d.rectangle(((box[0] - x0) * k, (box[1] - y0) * k, (box[2] - x0) * k, (box[3] - y0) * k), outline=(255, 160, 0), width=2)
    buf = io.BytesIO()
    c.save(buf, "PNG")
    return buf.getvalue()


def v4_cards(run_dir, r):
    """Full-diagram result: reference | render, closeness in plain words, and the 'please check these' panel."""
    sys.path.insert(0, ROOT)
    from ipmotion.diagram import load
    truth, layout = load(r["source"])
    f = r.get("fidelity") or {}
    fr = r.get("final_frames") or {}
    last = img_tag(run_dir, fr.get("last", ""), "What the computer drew (last moment of the animation)", "big")
    ref_png = full_reference(r["reference"])
    ref = (f'<figure class="ref"><div class="refpic r_full_{r["source"]}"></div>'
           f'<figcaption>REFERENCE: the real diagram, the only truth.</figcaption></figure>')
    kind, line = verdict(r)
    rows = [
        ("Blocks drawn with the exact name", f"{f.get('blocks_ok', '?')} of {f.get('blocks_total', '?')}"),
        ("Regions with the right name and the right blocks inside", f"{f.get('regions_ok', '?')} of {f.get('regions_total', '?')}"),
        ("Sure lines drawn between the right blocks, arrows the right way", f"{f.get('wires_ok', '?')} of {f.get('wires_total', '?')}"),
        ("Extra things drawn that are not in the picture", f"{f.get('extras', '?')}"),
        ("Blocks keep the picture's left/right and above/below order", f"{f.get('layout_percent', '?')}% of block pairs"),
        ("Not sure about (drawn in amber dashes, see below)", f"{len(f.get('unconfirmed', []))} items"),
        ("Layout check problems / spec check problems", f"{r.get('final_lint_errors', '?')} / {r.get('final_conformance_errors', '?')}"),
    ]
    table = "".join(f"<tr><td>{html.escape(a)}</td><td><b>{html.escape(b)}</b></td></tr>" for a, b in rows)
    honest = ('<div class="status"><b>Be careful with these numbers.</b> They compare the drawing with my written notes of the '
              'picture, not with the picture itself. You are the judge: look at the reference on the left and the drawing on the right.</div>')
    keys = "".join(img_tag(run_dir, fr[k], cap, "small") for k, cap in
                   (("key_25", "about 25% through"), ("key_50", "about half way"), ("key_75", "about 75% through")) if k in fr)
    items = []
    unclear = {c["id"]: c.get("unclear", "") for c in truth["connections"] if "unclear" in c}
    unclear.update({b["id"]: b.get("unclear", "") for b in truth["blocks"] if "unclear" in b})
    for u in f.get("unconfirmed", []):
        L = layout["blocks"]
        if u["kind"] == "wire":
            route = layout["routes"].get(u["id"], {})
            if "route" in route:
                xs = [pt[0] for pt in route["route"]]
                ys = [pt[1] for pt in route["route"]]
                box = (min(xs), min(ys), max(xs), max(ys))
            else:
                a = L.get(str(u["from"]).split(".")[0]) or [0, 0, 1, 1]
                b = L.get(str(u["to"]).split(".")[0]) or a
                box = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
            what = f"Line {u['id']}: {u['from']} to {u['to']}"
        else:
            box = tuple(L[u["id"]])
            what = f"Block: {u['label']}"
        png = crop_png(r["reference"], box)
        items.append(f'<div class="conf"><img src="data:image/png;base64,{b64(png)}"><div><b>{html.escape(what)}</b>'
                     f'<p>Why I am unsure: {html.escape(unclear.get(u["id"], ""))}</p>'
                     f'<p class="ask">Please look at the picture: is this there, and does it go where I drew it?</p></div></div>')
    confirm = ('<h4>Please check these (what I am not sure about)</h4><p class="blurb">Each one is drawn in amber dashes in the animation so it '
               'is never mistaken for a sure line. The orange box on the crop shows where to look in the reference.</p>' + "".join(items)) if items else ""
    css = (f".r_full_{r['source']}{{background:url(data:image/png;base64,{b64(ref_png[0])}) center/contain no-repeat;"
           f"aspect-ratio:{ref_png[1]}/{ref_png[2]};width:100%}}")
    body = (f'<div class="card"><div class="verdict {kind}">{html.escape(line)}</div>{honest}'
            f'<div class="pair">{ref}{last}</div><table class="sum">{table}</table>'
            f'{("<p class=lbl>Other moments of the same animation:</p><div class=row>" + keys + "</div>") if keys else ""}'
            f'{confirm}</div>')
    return css, body


def main():
    runs, skipped, model = load_runs()
    specs = [s for s in SPEC_ORDER if any(k[0] == s for k in runs)] + sorted({k[0] for k in runs} - set(SPEC_ORDER))
    css_refs, body, rows = [], [], []
    full_html = ""
    for k in sorted(k for k in runs if k[1] == "v4"):
        d_, r_ = runs[k]
        css_, card_ = v4_cards(d_, r_)
        css_refs.append(css_)
        full_html += (f"<section><h2>Full diagram test: {html.escape(k[0])}</h2>"
                      f"<p class='blurb'>The whole reference diagram is drawn by code from my notes of the picture (positions taken from the picture itself), "
                      f"then a short story is played on it. No AI wrote any of this code.</p>{card_})</section>")
        l_, c_ = r_.get("final_lint_errors"), r_.get("final_conformance_errors")
        rows.append(f"<tr><td>{html.escape(k[0])}</td><td>full diagram (code)</td><td>1</td><td>{l_}</td><td>{c_}</td>"
                    f"<td class='{'ok' if is_clean(r_) else 'bad'}'>{'yes' if is_clean(r_) else 'no'}</td></tr>")
    specs = [x for x in specs if not any(k[0] == x and k[1] == "v4" and not any(kk[0] == x and kk[1] != "v4" for kk in runs) for k in runs)]
    for s in specs:
        ref = reference_png(s)
        if ref:
            css_refs.append(f".r_{s}{{background:url(data:image/png;base64,{b64(ref[0])}) center/contain no-repeat;"
                            f"aspect-ratio:{ref[1]}/{ref[2]};width:100%}}")
        sections = []
        for p, title, blurb in (
                ("v2", "Old pipeline (v2)", "Asks the AI once, then only fixes crashes. It never looks at the picture."),
                ("v3", "New pipeline (v3)", "After every try it checks the layout and the spec, and sends the problems back to the AI.")):
            reps = sorted(k[2] for k in runs if k[0] == s and k[1] == p)
            if not reps:
                note = ("Not run yet with the new checks: the daily limit of the AI service was reached. "
                        "It will run when the limit resets." if p == "v3" else "Not run.")
                sections.append(f"<h3>{title}</h3><p class='blurb'>{blurb}</p><p class='pending'>{note}</p>")
                continue
            cards = []
            for rp in reps:
                d, r = runs[(s, p, rp)]
                l, c = totals(r)
                rows.append(f"<tr><td>{html.escape(s)}</td><td>{p} run {rp}</td><td>{r['attempts_used']}</td>"
                            f"<td>{'crash' if l is None else l}</td><td>{'n/a' if c is None else c}</td>"
                            f"<td class='{'ok' if is_clean(r) else 'bad'}'>{'yes' if is_clean(r) else 'no'}</td></tr>")
                cards.append(f"<h4>{title}: run {rp}</h4>" + run_card(s, d, r, bool(ref)))
            sections.append(f"<h3>{title}</h3><p class='blurb'>{blurb}</p>" + "".join(cards))
        body.append(f"<section><h2>Test: {html.escape(s)}</h2>{''.join(sections)}</section>")

    table = ("<table class='sum'><tr><th>Test</th><th>Run</th><th>Tries used</th><th>Layout problems</th>"
             "<th>Spec mismatches</th><th>All clean?</th></tr>" + "".join(rows) + "</table>") if rows else ""
    status = "" if any(k[1] == "v3" for k in runs) else (
        '<div class="status"><b>Where things stand:</b> the new pipeline (v3) has not been run yet with the newest checks. '
        'The AI service has a daily limit that is used up. It will run when the limit resets, and this page will fill in.</div>')
    page = f"""<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="60"><title>IPMotion test report</title>
<style>
body{{font:15px/1.45 system-ui,Segoe UI,sans-serif;margin:24px auto;max-width:1280px;padding:0 16px;background:#0b0f14;color:#dbe4ee}}
h1{{margin:0 0 4px}}h2{{margin-top:36px;border-top:1px solid #223;padding-top:18px}}h3{{margin:22px 0 2px}}h4{{margin:18px 0 8px;color:#8aa0b6}}
.how,.status{{background:#121a24;border-radius:8px;padding:12px 16px;margin:14px 0}}.status{{border-left:4px solid #ffd700}}
.blurb{{color:#8aa0b6;margin:0 0 6px}}.pending{{background:#1a1a10;border-radius:6px;padding:10px 14px;color:#ffd700}}
.card{{background:#121a24;border-radius:8px;padding:14px;margin:8px 0 18px}}
.verdict{{font-weight:600;padding:8px 12px;border-radius:6px;margin-bottom:12px}}
.verdict.ok{{background:#10301a;color:#39ff14}}.verdict.warn{{background:#33290a;color:#ffd700}}.verdict.bad{{background:#3a1220;color:#ff5c7a}}
.pair{{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-start}}.ref{{flex:0 1 38%;min-width:280px;margin:0}}.big{{flex:1 1 55%;min-width:320px;margin:0}}
.big img,.small img{{width:100%;border-radius:4px;display:block}}figcaption{{color:#8aa0b6;font-size:12px;margin-top:4px}}
.row{{display:flex;gap:10px;flex-wrap:wrap}}.small{{flex:1 1 30%;min-width:200px;margin:0}}
.nopic{{background:#1a2330;border-radius:6px;padding:40px 16px;text-align:center;color:#8aa0b6}}
.lbl{{margin:14px 0 4px;color:#8aa0b6}}.facts{{color:#8aa0b6}}ul{{margin:4px 0 4px 18px;padding:0}}details{{margin:8px 0}}summary{{cursor:pointer;color:#9ad}}
.conf{{display:flex;gap:14px;align-items:flex-start;background:#0f1620;border-radius:6px;padding:10px;margin:8px 0}}.conf img{{max-width:46%;border-radius:4px}}.conf p{{margin:4px 0}}.ask{{color:#ffd700}}
.sum{{border-collapse:collapse;width:100%}}.sum th,.sum td{{padding:6px 12px 6px 0;border-bottom:1px solid #223;text-align:left}}.ok{{color:#39ff14}}.bad{{color:#ff5c7a}}
{''.join(css_refs)}
</style>
<h1>IPMotion test report</h1>
<p><b>Last updated: {datetime.now():%Y-%m-%d %H:%M:%S}</b> (this page reloads itself every minute) &middot; AI model used for every run: <code>{model}</code></p>
<div class="how"><b>How to read this page</b><ul>
<li>Each test gives the computer a short description (a "spec") of a few blocks and one story, and asks it to make an animation.</li>
<li><b>Left: the REFERENCE</b>, the real architecture diagram. It is the only truth. The yellow boxes show the few blocks this test draws (the test is a small piece of the whole chip, so the animation will not show everything).</li>
<li><b>Right: what the computer drew.</b> Compare the two: are the same blocks there, with the same names, in the same regions, with arrows going the same way?</li>
<li>The <b>Full diagram test</b> (at the top) is the real goal: the whole reference diagram, redrawn by code, with a short story played on it. Everything below it is the older test with the AI writing the code.</li>
<li>Two pipelines are compared. <b>v2</b> is the old way; <b>v3</b> is the new way with automatic checks. Each is run several times, because the AI gives a different answer each time.</li>
<li>Two automatic checks: the <b>layout check</b> (text overlapping, things cut off, things too small) and the <b>spec check</b> (right names, right blocks, right arrows, right step titles).</li>
</ul></div>
{status}
{('<h2>All runs at a glance</h2>' + table) if table else ''}
{full_html}
{''.join(body)}
<p class="facts">{skipped} older run(s) are hidden because they used a different AI model or an older prompt.</p>"""
    out = os.path.join(ROOT, "bench", "report.html")
    open(out, "w", encoding="utf-8").write(page)
    print("wrote", out, f"({os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    main()
