"""Draw a whole reference diagram from its truth file (what is connected to what) + layout file (where it is).

The positions come from the reference image itself (pixels), scaled to fit the frame, so blocks cannot overlap and
the picture keeps the reference's arrangement. Colors/scale are ours. Items the truth file marks `unclear` are drawn
in an amber dashed "unconfirmed" style instead of being dropped or drawn as if certain.

    d = Diagram("opentitan_darjeeling")      # reads bench/truth/<name>.yaml and <name>.layout.yaml
    d.blocks["ibex_core"], d.conns["c01"], d.panel (step panel on the right)
"""
from __future__ import annotations

import os
import textwrap

import numpy as np
import yaml
from manim import (BOLD, DOWN, LEFT, RIGHT, UP, Arrow, Circle, DashedLine, Line, Polygon, RoundedRectangle, Square, Text,
                   VGroup, config)

from ipmotion_lib import (DomainGroup, GlowBox, IPBlock, Packet, TextTransform, Theme, ui_text)
from manim import AnimationGroup, DashedVMobject, Wait

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRUTH_DIR = os.path.join(ROOT, "bench", "truth")

FILL = {   # legend label -> (stroke, fill)  (colors are ours; only the grouping follows the reference legend)
    "~1 Ghz": ("#22D3EE", "#0E2A33"), "~250 MHz": ("#A78BFA", "#1E1736"), "Logic Only": ("#9CA3AF", "#22262C"),
    # earlgrey / others
    "~150 MHz (target)": ("#60A5FA", "#0F2238"), "96 MHz": ("#3B82F6", "#0B1B33"), "48 MHz": ("#F472B6", "#33121F"),
    "24 MHz": ("#34D399", "#0F2A22"), "200 kHz": ("#FDBA74", "#33220F"), "Logic only": ("#9CA3AF", "#22262C"),
}
MARKER = {"orange": "#F59E0B", "purple": "#A78BFA", "peach": "#FDBA74", "blue": "#3B82F6", "pink": "#F472B6"}
UNCONFIRMED = "#F59E0B"
LINE_GRAY = "#9CA3AF"
BLUE_OUTLINE = "#3B82F6"


def load(name: str):
    with open(os.path.join(TRUTH_DIR, f"{name}.yaml"), encoding="utf-8") as fh:
        truth = yaml.safe_load(fh)
    with open(os.path.join(TRUTH_DIR, f"{name}.layout.yaml"), encoding="utf-8") as fh:
        layout = yaml.safe_load(fh)
    return truth, layout


def _partitions(words, k):
    """All ways to cut `words` into exactly k consecutive non-empty groups."""
    if k == 1:
        yield [" ".join(words)]
        return
    for i in range(1, len(words) - k + 2):
        for rest in _partitions(words[i:], k - 1):
            yield [" ".join(words[:i])] + rest


def wrap_label(label: str, w_px: float, h_px: float) -> str:
    """Pick the line breaks that let the text be biggest inside the box (estimated from character counts)."""
    words = label.split()
    best, best_score = label, -1.0
    for k in range(1, min(len(words), 4) + 1):
        for lines in _partitions(words, k):
            longest = max(len(l) for l in lines)
            score = min(w_px / (longest * 0.55), h_px / (len(lines) * 1.25))
            if score > best_score + 1e-9:
                best, best_score = "\n".join(lines), score
    return best


class StepPanel(VGroup):
    """Right-hand panel: title, the current step text, and room for a legend."""
    lint_container = True          # a panel background is a container, not a block of the diagram

    def __init__(self, theme, x0, x1, y0, y1, title):
        super().__init__()
        self.theme = theme
        self.frame = RoundedRectangle(width=x1 - x0, height=y1 - y0, corner_radius=0.12, stroke_color=theme.stroke,
                                      stroke_width=2, fill_color=theme.panel, fill_opacity=0.9)
        self.frame.move_to([(x0 + x1) / 2, (y0 + y1) / 2, 0])
        self.anchor = np.array([x0 + 0.3, y1 - 1.35, 0.0])
        self.max_chars = 30
        self.title_txt = Text(title, font="Consolas", font_size=22, color=theme.active, weight=BOLD)
        self.title_txt.move_to([x0 + 0.3, y1 - 0.5, 0], aligned_edge=LEFT)
        if self.title_txt.width > (x1 - x0) - 0.6:
            self.title_txt.scale(((x1 - x0) - 0.6) / self.title_txt.width)
        self.txt = self._make("")
        self.add(self.frame, self.title_txt, self.txt)

    def _make(self, text):
        wrapped = "\n".join(textwrap.wrap(text, self.max_chars)) or " "
        t = Text(wrapped, font="Consolas", font_size=26, color=self.theme.text, weight=BOLD, line_spacing=0.9)
        t.move_to(self.anchor, aligned_edge=UP + LEFT)
        return t

    def update_text(self, text, color=None):
        new = self._make(text)
        if color:
            new.set_color(color)
        return AnimationGroup(TextTransform(self.txt, new), group=self)

    def set_text_now(self, text):
        new = self._make(text)
        self.txt.become(new)
        self.txt.text = new.text
        return self


class Diagram(VGroup):
    def __init__(self, name: str, theme=None, height_units: float = 7.6, center_x: float = -3.45, panel=True, title=None):
        super().__init__()
        self.theme = theme or Theme()
        self.truth, self.layout = load(name)
        w_px, h_px = self.layout["image_size"]
        self.u = height_units / h_px
        self.ox, self.oy = w_px / 2, h_px / 2
        self.cx = center_x
        self.blocks: dict = {}
        self.conns: dict = {}
        self.regions: dict = {}
        self.labels: dict = {}
        self.unconfirmed: set = set()
        self.conn_pts: dict = {}
        self.conn_heads: dict = {}
        self._base_stroke: dict = {}
        self._base_color: dict = {}
        self._pending_fit: list = []
        self._build()
        self._size_texts()
        if panel:
            self.panel = StepPanel(self.theme, 0.35, 6.95, -3.9, 3.9, title or self.truth.get("diagram_title") or "")
            self.legend = self._legend()
            self.panel.add(self.legend)
            self.add(self.panel)

    # ---------------------------------------------------------------- geometry
    def P(self, x, y):
        return np.array([(x - self.ox) * self.u + self.cx, -(y - self.oy) * self.u, 0.0])

    def _box(self, b):
        (x0, y0), (x1, y1) = self.P(b[0], b[1])[:2], self.P(b[2], b[3])[:2]
        return (x0 + x1) / 2, (y0 + y1) / 2, abs(x1 - x0), abs(y1 - y0)

    # ------------------------------------------------------------------- build
    def _build(self):
        T, L, th = self.truth, self.layout, self.theme
        region_style = {0: ("#0B0F14", "#E5E7EB", 3), 1: ("#10161D", "#475569", 1), 2: ("#141D28", "#64748B", 1.5)}
        depth = {"wrapper": 0, "ip": 1}
        for r in T["regions"]:
            box = L["regions"][r["id"]]
            cx, cy, w, h = self._box(box)
            fill, stroke, sw = region_style[depth.get(r["id"], 2)]
            dg = DomainGroup(r["label"], cx, cy, w, h, fill, stroke=stroke)
            dg.bg.set_stroke(stroke, sw)
            # smaller title, kept inside the top-left corner
            dg.txt.scale(11 / 24 if r["id"] not in ("wrapper",) else 0.5)
            dg.txt.move_to(dg.bg.get_corner(UP + LEFT) + RIGHT * 0.12 + DOWN * 0.13, aligned_edge=LEFT)
            self.regions[r["id"]] = dg
            self.add(dg)

        # connections first (so blocks hide lines that pass behind them); the few that end INSIDE a block
        # (a port reference like soc_proxy.trapezoid) are drawn after the blocks so they stay visible
        inside = [c for c in T["connections"] if "." in str(c["from"]) or "." in str(c["to"])]
        for c in T["connections"]:
            if c not in inside:
                self._add_connection(c)

        for b in T["blocks"]:
            if b["id"] not in L["blocks"]:
                continue
            self._add_block(b)
        for c in inside:
            self._add_connection(c)
        for e in T["externals"]:
            if e["id"] in L["blocks"]:
                self._add_block({"id": e["id"], "label": e["label"], "fill_legend": None, "attributes": ["dashed_outline"],
                                 "external": True})
            elif e["id"] in L["labels"]:
                self._add_label(e)

    def _add_block(self, b):
        L, th = self.layout, self.theme
        cx, cy, w, h = self._box(L["blocks"][b["id"]])
        if h < 0.2:                       # a nested sliver (Base Addr Translation): a little taller so the text can be read
            cy += (0.26 - h) / 2           # grow upward so the box stays inside its parent
            h = 0.26
        legend = b.get("fill_legend")
        stroke, fill = FILL.get(legend, ("#9CA3AF", "#1B1F26"))
        attrs = b.get("attributes", [])
        if "blue_outline" in attrs:
            stroke = BLUE_OUTLINE
        wrapped = wrap_label(b["label"], w / self.u, h / self.u)
        blk = IPBlock(wrapped, th, width=w, height=h, fill=fill, stroke=stroke, text_color=th.text)
        blk.move_to([cx, cy, 0])
        if "dashed_outline" in attrs:
            blk.bg.glow1.set_opacity(0)
            blk.bg.glow2.set_opacity(0)
            outline = DashedVMobject(RoundedRectangle(width=w, height=h, corner_radius=0.15, stroke_color=stroke, stroke_width=2,
                                                      fill_opacity=0).move_to([cx, cy, 0]), num_dashes=36)
            blk.bg.box.set_stroke(width=0)
            blk.add(outline)
        if "blue_outline" in attrs:
            blk.bg.box.set_stroke(BLUE_OUTLINE, 3)
        self._pending_fit.append((blk, w, h))
        blk.has_markers = bool(b.get("markers"))
        for i, m in enumerate(b.get("markers", [])):
            sq = Square(side_length=min(0.08, h * 0.2), fill_color=MARKER.get(m["color"], "#FFFFFF"), fill_opacity=1, stroke_width=0)
            sq.move_to(blk.bg.box.get_corner(UP + LEFT) + RIGHT * (0.07 + 0.11 * i) + DOWN * 0.07)
            blk.add(sq)
        blk.lint_unconfirmed = bool(b.get("unclear"))
        if b["id"] == "ibex_core":
            sh = self.layout["extras"]["dual_lockstep_shadow"]
            scx, scy, sw_, sh_ = self._box(sh)
            shadow = RoundedRectangle(width=sw_, height=sh_, corner_radius=0.1, fill_color="#0B4F5E", fill_opacity=1,
                                      stroke_color=stroke, stroke_width=1).move_to([scx, scy, 0])
            tag = Text("DUAL LOCKSTEP", font="Consolas", font_size=8, color=th.text).move_to(shadow.get_bottom() + UP * 0.07)
            blk.submobjects.insert(0, shadow)
            blk.submobjects.append(tag)
        if b["id"] == "soc_proxy":
            tcx, tcy, tw, thh = self._box(self.layout["extras"]["soc_proxy_trapezoid"])
            ptsx = [[-tw / 2, thh / 2], [tw / 2, thh / 2], [tw * 0.3, -thh / 2], [-tw * 0.3, -thh / 2]]
            trap = Polygon(*[[x + tcx, y + tcy, 0] for x, y in ptsx], stroke_color=BLUE_OUTLINE, stroke_width=2, fill_opacity=0)
            blk.add(trap)
        self.blocks[b["id"]] = blk
        self._base_stroke[b["id"]] = stroke
        self.add(blk)

    def _size_texts(self):
        """One common font size for all block titles (the library only ever shrinks text); a block whose box is
        too small for that size gets the largest size that fits."""
        fits = []
        for blk, w, h in self._pending_fit:
            t = blk.txt
            pad_w, pad_h = (0.80, 0.66) if getattr(blk, "has_markers", False) else (0.84, 0.74)
            k = min((w * pad_w) / max(t.width, 1e-6), (h * pad_h) / max(t.height, 1e-6))
            fits.append(t.font_size * k)
        common = min(float(np.median(fits)) * 0.95, 14.0)
        for (blk, w, h), fit in zip(self._pending_fit, fits):
            t = blk.txt
            t.scale(min(common, fit) / t.font_size)
            t.move_to(blk.bg.box.get_center() + (DOWN * h * 0.08 if getattr(blk, "has_markers", False) else 0 * DOWN))
            if blk is self.blocks.get("soc_proxy"):
                t.move_to(blk.bg.box.get_top() + DOWN * 0.16)
        self.common_font = common

    def _add_label(self, e):
        cx, cy, w, h = self._box(self.layout["labels"][e["id"]])
        t = Text(wrap_label(e["label"], w / self.u, h / self.u), font="Consolas", font_size=12, color=self.theme.text)
        k = min(w * 0.95 / max(t.width, 1e-6), h * 0.95 / max(t.height, 1e-6))
        t.scale(min(k, 1.2)).move_to([cx, cy, 0])
        self.labels[e["id"]] = t
        self.add(t)

    # -------------------------------------------------------------- connections
    def _route(self, c):
        """-> list of px points, or list of such lists (multi)."""
        L = self.layout
        spec = L["routes"].get(c["id"], {})
        if "route" in spec:
            return [spec["route"]]
        if "multi" in spec:
            return [[[a, b], [cc, d]] for a, b, cc, d in spec["multi"]]
        fb = L["blocks"].get(c["from"].split(".")[0]) or L["labels"].get(c["from"])
        tb = L["blocks"].get(c["to"].split(".")[0]) or L["labels"].get(c["to"])
        ox = min(fb[2], tb[2]) - max(fb[0], tb[0])      # x-overlap
        oy = min(fb[3], tb[3]) - max(fb[1], tb[1])
        at = spec.get("at")
        if ox >= oy:                                    # stacked vertically -> vertical stem
            x = at if at is not None else (max(fb[0], tb[0]) + min(fb[2], tb[2])) / 2
            if fb[3] <= tb[1]:
                return [[[x, fb[3]], [x, tb[1]]]]
            return [[[x, fb[1]], [x, tb[3]]]]
        y = at if at is not None else (max(fb[1], tb[1]) + min(fb[3], tb[3])) / 2
        if fb[2] <= tb[0]:
            return [[[fb[2], y], [tb[0], y]]]
        return [[[fb[0], y], [tb[2], y]]]

    def _add_connection(self, c):
        th = self.theme
        unconfirmed = "unclear" in c
        line = c.get("line", "thick")
        thick = line == "thick" or line == "hollow_block"
        dashed = line in ("dashed_thin", "dashed_block") or unconfirmed
        color = UNCONFIRMED if unconfirmed else LINE_GRAY
        sw = 5 if thick else 2
        heads = c.get("heads", "to")
        routes = self._route(c)
        grp = VGroup()
        self.conn_pts[c["id"]] = []
        for pts_px in routes:
            pts = [self.P(x, y) for x, y in pts_px]
            self.conn_pts[c["id"]].append(pts)
            segs = []
            for i in range(len(pts) - 1):
                last = i == len(pts) - 2
                first = i == 0
                a, b = pts[i], pts[i + 1]
                want_end = last and heads in ("to", "both")
                want_start = first and heads == "both"
                tl = min(0.11 if thick else 0.08, np.linalg.norm(b - a) * 0.8)
                if dashed:
                    seg = DashedLine(a, b, color=color, stroke_width=sw, dash_length=0.05, dashed_ratio=0.6)
                else:
                    seg = Line(a, b, color=color, stroke_width=sw)
                if want_end:
                    seg.add_tip(tip_length=tl, tip_width=tl * (1.0 if thick else 0.8))
                if want_start:
                    seg.add_tip(tip_length=tl, tip_width=tl * (1.0 if thick else 0.8), at_start=True)
                segs.append(seg)
            grp.add(*segs)
        lab = self.layout["routes"].get(c["id"], {}).get("label_at")
        if lab and c.get("printed_label"):
            t = Text(c["printed_label"], font="Consolas", font_size=9, color=self.theme.text)
            t.move_to(self.P(*lab), aligned_edge=LEFT)
            self.labels["conn_" + c["id"]] = t
            self.add(t)
        self.conns[c["id"]] = grp
        self.conn_heads[c["id"]] = heads
        self._base_color[c["id"]] = color
        if unconfirmed:
            self.unconfirmed.add(c["id"])
        self.add(grp)

    # ------------------------------------------------------------------ legend
    def _legend(self):
        th = self.theme
        items = VGroup()
        y = -0.85
        lines = [("Clock speed (fill color):", None)]
        for e in self.truth.get("legend", []):
            if e["swatch"].endswith("fill"):
                word = e["swatch"].split()[0]
                lines.append((e["label"], FILL[e["label"]][0] if e["label"] in FILL and word in ("cyan", "purple", "gray") or
                              e["label"] in ("~1 Ghz", "~250 MHz", "Logic Only") else MARKER.get(word, "#9CA3AF")))
        lines += [("dashed box: not fully implemented yet", "#9CA3AF"), ("blue outline: new in rev2", BLUE_OUTLINE),
                  ("amber dashed line: not sure (see report)", UNCONFIRMED)]
        head = ui_text(lines[0][0], 13, th.muted)
        head.move_to([0.65, y, 0], aligned_edge=LEFT)
        items.add(head)
        for txt, col in lines[1:]:
            y -= 0.33
            sw = Circle(radius=0.08, fill_color=col, fill_opacity=0.9, stroke_width=0).move_to([0.72, y, 0])
            t = ui_text(txt, 12, th.text).move_to([0.95, y, 0], aligned_edge=LEFT)
            items.add(sw, t)
        return items

    # ----------------------------------------------------------------- helpers
    def reset_now(self):
        """Put every block outline and wire back to its base look immediately (no animation)."""
        for k, blk in self.blocks.items():
            blk.bg.set_color(self._base_stroke[k])
        for k, g in self.conns.items():
            g.set_color(self._base_color[k])

    def reset_style(self):
        """Animations that put every block outline and wire back to its base look."""
        anims = []
        for k, blk in self.blocks.items():
            anims.append(blk.bg.box.animate.set_stroke(self._base_stroke[k]))
        for k, g in self.conns.items():
            anims.append(g.animate.set_color(self._base_color[k]))
        return anims
