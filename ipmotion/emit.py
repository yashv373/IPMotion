"""Turn a drawn reference diagram into a FLAT, standalone Manim script -- a worked example for the prompt.

The website's model had one example to learn from: a two-block AXI handshake that uses `arrange()` and contains
no DomainGroup at all. Measured result on a 24-block diagram: 0 of 3 regions drawn and half the wires missing.
This writes out what a finished, correct, many-block diagram actually looks like in code, so the model has a
blueprint instead of guessing.

It only READS a built Diagram -- no drawing logic is duplicated and nothing in diagram.py changes behaviour, so
whatever the engine draws is exactly what the example teaches.

    python -m ipmotion.emit bench/stories/darjeeling_ibex_uart_read.yaml out.py

Peppermint is deliberately NOT emitted: it is the held-out exam (CLAUDE.md).
"""
from __future__ import annotations

import os
import sys

import textwrap

from manim import DashedLine, config

from ipmotion.diagram import Diagram
from ipmotion.fullspec import load_story, make_full_spec

HEADER = '''# GOLD EXAMPLE: a whole reference block diagram, drawn from a picture (renders with 0 lint errors).
# Habits to copy for a diagram of this size:
#   1. REGIONS FIRST. Every power/clock domain in the picture is a DomainGroup, added before the blocks so the
#      blocks sit on top of it. A diagram with domains and no DomainGroup is wrong.
#   2. EXACT NAMES. Every block title is the picture's own text, character for character. Never shorten
#      "Timer Block (32-bit)" to "Timer", and never invent a word the picture does not have.
#   3. ABSOLUTE POSITIONS. Blocks are placed with move_to([x, y, 0]) at measured coordinates, not arrange() or
#      next_to(). That is the only way a 40-block picture comes out without overlaps.
#   4. EVERY WIRE. One Line per connection in the source diagram, with explicit points. If the picture has 53
#      connections, the script draws 53. Missing wires are the most common failure.
#   5. One font size for the block titles, set after move_to, so the drawing reads as one piece.
from manim import *
from ipmotion_lib import *
'''


def _c(v) -> str:
    """A manim colour as a plain hex string."""
    return f'"{str(v).upper()}"'


def _cap(text: str, width_u: float) -> str:
    """Break a step caption to the gutter it has to live in (Consolas at 22pt is ~0.164 units a character)."""
    return chr(10).join(textwrap.wrap(text, max(12, int(width_u / 0.164))))


def _pt(p) -> str:
    return f"[{p[0]:.3f}, {p[1]:.3f}, 0]"


def _on_edge(d, c, pts):
    """A reference wire that points AT something inside a block (Darjeeling's SoC Proxy trapezoid) is drawn
    ending inside it. In a flat script every block is a named object, so the linter can see that and calls it a
    dangling end. Pull such an end back onto the block's edge: same wire to the eye, honest to the checker."""
    for idx, end in ((0, str(c["from"])), (-1, str(c["to"]))):
        box = d.layout["blocks"].get(end.split(".")[0])
        if not box:
            continue
        cx, cy, w, h = d._box(box)
        x, y = pts[idx][0], pts[idx][1]
        if not (cx - w / 2 < x < cx + w / 2 and cy - h / 2 < y < cy + h / 2):
            continue
        # push out along whichever edge is nearest
        dists = {"l": x - (cx - w / 2), "r": (cx + w / 2) - x, "b": y - (cy - h / 2), "t": (cy + h / 2) - y}
        side = min(dists, key=dists.get)
        p = list(pts[idx])
        p[0] = cx - w / 2 if side == "l" else cx + w / 2 if side == "r" else p[0]
        p[1] = cy - h / 2 if side == "b" else cy + h / 2 if side == "t" else p[1]
        pts[idx] = p
    return pts


def emit(story_path: str) -> str:
    story = load_story(story_path)
    spec = make_full_spec(story)
    d = Diagram(spec["source"], panel=False)
    cls = "".join(w.capitalize() for w in os.path.basename(story_path).split(".")[0].split("_")) + "Scene"

    L: list[str] = [HEADER, "", f"class {cls}(Scene):", "    def construct(self):",
                    "        theme = Theme()", "",
                    "        ACTIVE = \"#FFD700\"", "        REQUEST = \"#00FFF0\"", "        RESPONSE = \"#FF7A00\"", ""]
    a = L.append

    a("        # ---- 1. the regions of the picture, drawn first so blocks sit on top of them ----")
    for r in d.truth["regions"]:
        g = d.regions[r["id"]]
        cx, cy, w, h = d._box(d.layout["regions"][r["id"]])
        var = "rg_" + r["id"]
        a(f"        {var} = DomainGroup({g.label_wrapped!r}, {cx:.3f}, {cy:.3f}, {w:.3f}, {h:.3f}, "
          f"{_c(g.bg.get_fill_color())}, stroke={_c(g.bg.get_stroke_color())})")
        a(f"        {var}.bg.set_stroke({_c(g.bg.get_stroke_color())}, {g.bg.get_stroke_width():.1f})")
        a(f"        {var}.txt.font_size = {g.txt.font_size:.2f}")
        a(f"        {var}.txt.move_to({_pt(g.txt.get_corner([-1, 1, 0]))}, aligned_edge=UP + LEFT)")
        a(f"        self.add({var})")
    a("")

    a("        # ---- 2. every block, with the picture's exact words and a measured position ----")
    names = {}
    for b in d.truth["blocks"] + [dict(e, external=True) for e in d.truth.get("externals", [])]:
        blk = d.blocks.get(b["id"])
        if blk is None:
            continue
        # read the box as DRAWN, not as written in the notes: the engine grows a sliver block so its title
        # fits, and the example has to carry that or its own text overflows
        box = blk.bg.box
        cx, cy = box.get_center()[0], box.get_center()[1]
        w, h = box.width, box.height
        var = "b_" + b["id"]
        names[b["id"]] = var
        title = blk.title or ""
        a(f"        {var} = IPBlock({title!r}, theme, width={w:.3f}, height={h:.3f}, "
          f"fill={_c(blk.bg.box.get_fill_color())}, stroke={_c(blk.bg.box.get_stroke_color())}, line_spacing=0.25)")
        a(f"        {var}.move_to([{cx:.3f}, {cy:.3f}, 0])")
        if title.strip():
            a(f"        {var}.txt.font_size = {blk.txt.font_size:.2f}")
            a(f"        {var}.txt.move_to({_pt(blk.txt.get_center())})")
        a(f"        self.add({var})")
    a("")

    if d._margin_wraps:
        a("        # ---- 3. text labels printed outside the drawing, as the picture has them ----")
        for lid, wrapped in d._margin_wraps.items():
            t = d.labels[lid]
            a(f"        lb_{lid} = Text({wrapped!r}, font=\"Consolas\", font_size={t.font_size:.2f}, "
              f"color={_c(t.get_color())}, line_spacing=0.25)")
            a(f"        lb_{lid}.move_to({_pt(t.get_center())})")
            a(f"        self.add(lb_{lid})")
        a("")

    a(f"        # ---- 4. all {len(d.truth['connections'])} connections of the picture, one wire each ----")
    for c in d.truth["connections"]:
        routes = d.conn_pts.get(c["id"])
        if not routes:
            continue
        grp = d.conns[c["id"]]
        seg0 = grp.submobjects[0]
        dashed = isinstance(seg0, DashedLine)
        col, sw = _c(seg0.get_color()), seg0.get_stroke_width()
        heads = d.conn_heads[c["id"]]
        var = "w_" + c["id"]
        parts = []
        for ri, pts in enumerate(routes):
            pts = _on_edge(d, c, list(pts))
            for i in range(len(pts) - 1):
                nm = f"{var}_{ri}_{i}"
                kind = "DashedLine" if dashed else "Line"
                extra = ", dash_length=0.05, dashed_ratio=0.6" if dashed else ""
                a(f"        {nm} = {kind}({_pt(pts[i])}, {_pt(pts[i + 1])}, color={col}, "
                  f"stroke_width={sw:.0f}{extra})")
                if i == len(pts) - 2 and heads in ("to", "both"):
                    a(f"        {nm}.add_tip(tip_length=0.11, tip_width=0.11)")
                if i == 0 and heads == "both":
                    a(f"        {nm}.add_tip(tip_length=0.11, tip_width=0.11, at_start=True)")
                parts.append(nm)
        a(f"        {var} = VGroup({', '.join(parts)})")
        a(f"        self.add({var})")
        ct = d.labels.get("conn_" + c["id"])
        if ct is not None:
            a(f"        {var}_lb = Text({c['printed_label']!r}, font=\"Consolas\", font_size={ct.font_size:.2f}, "
              f"color={_c(ct.get_color())})")
            a(f"        {var}_lb.move_to({_pt(ct.get_center())})")
            a(f"        self.add({var}_lb)")
    a("")

    # A Banner is 14 units wide and 0.8 tall. A portrait reference fills the frame height, so there is no free
    # strip for one: its step text goes in the gutter beside the drawing instead, which is also the honest
    # lesson -- put the caption where the drawing is not.
    top = max(d.P(0, y)[1] for y in (0, d.layout["image_size"][1]))
    room_above = config.frame_height / 2 - 0.16 - top
    gutter_x0, gutter_x1 = d._panel_x0, config.frame_width / 2 - 0.16
    use_banner = room_above >= 0.9

    a("        # ---- 5. the story: one step caption at a time, lighting up what it names ----")
    if use_banner:
        a(f"        caption = Banner({spec['title']!r}, theme)")
        a(f"        caption.move_to([0, {top + room_above / 2:.3f}, 0])")
    else:
        a("        # the drawing fills the height, so the caption goes beside it, never on top of it")
        a(f"        CAP = [{(gutter_x0 + gutter_x1) / 2:.3f}, 2.2, 0]")
        a(f"        caption = Text({_cap(spec['title'], gutter_x1 - gutter_x0)!r}, font=\"Consolas\", "
          f"font_size=22, color=\"#E5E7EB\", weight=BOLD, line_spacing=0.9)")
        a("        caption.move_to(CAP)")
    a("        self.add(caption)")
    a("        self.wait(0.5)")
    for step in spec["sequence"]:
        a("")
        if use_banner:
            a(f"        self.play(caption.update_text({step['banner']!r}, theme, ACTIVE))")
        else:
            a(f"        self.play(Transform(caption, Text({_cap(step['banner'], gutter_x1 - gutter_x0)!r}, "
              f"font=\"Consolas\", font_size=22, color=ACTIVE, weight=BOLD, line_spacing=0.9).move_to(CAP)))")
        lit = [f"{names[b]}.bg.animate.set_color(ACTIVE)" for b in step.get("highlight", []) if b in names]
        lit += [f"w_{c}.animate.set_color(ACTIVE)" for c in step.get("activate", []) if "w_" + c]
        if lit:
            a(f"        self.play({', '.join(lit)}, run_time=0.6)")
        for pk in step.get("packets", []):
            pts = d.conn_pts.get(pk["conn"], [[]])[0]
            if len(pts) < 2:
                continue
            resp = pk.get("kind", "request") == "response"
            seq = list(reversed(pts)) if resp else list(pts)
            a(f"        pkt = Packet({pk['label']!r}, {'RESPONSE' if resp else 'REQUEST'}, theme, "
              f"width=0.62, height=0.2, font_size=9)")
            a(f"        pkt.move_to({_pt(seq[0])})")
            a("        self.play(FadeIn(pkt, run_time=0.15))")
            for p in seq[1:]:
                a(f"        self.play(pkt.animate.move_to({_pt(p)}), run_time=0.4)")
            a("        self.play(FadeOut(pkt, run_time=0.15))")
        a(f"        self.wait({step.get('hold', 0.5)})")
    a("")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    out = emit(sys.argv[1])
    if len(sys.argv) > 2:
        open(sys.argv[2], "w", encoding="utf-8").write(out)
        print(f"wrote {sys.argv[2]} ({out.count(chr(10))} lines)")
    else:
        print(out)
