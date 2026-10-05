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
    # peppermint has no legend at all: the truth file records the fill as drawn
    "light green": ("#34D399", "#0F2A22"), "dark green": ("#22D3EE", "#0E2A33"),
}
MARKER = {"orange": "#F59E0B", "purple": "#A78BFA", "peach": "#FDBA74", "blue": "#3B82F6", "pink": "#F472B6"}
UNCONFIRMED = "#F59E0B"
TEXT_PAD_W, TEXT_PAD_H = 0.88, 0.80      # share of a block's box its title may use
MAX_BLOCK_FONT = 14.0                     # a big block does not get huge text; everything reads as one size
MARGIN_LABEL_FONT = 12.0                  # free labels in the left margin ("DMA System Egress")
MARGIN_LABEL_CHARS = 11                   # ...broken to about this many characters a line
MARGIN_LABEL_MIN = 9.0                    # ...and never smaller than this, however tight the reference box is
LINE_SPACING = 0.25                       # block titles: tight lines, so a 3-line title stays readable
FRAME_MARGIN = 0.16                       # nothing is drawn closer than this to the edge of the frame
                                          # (over the linter's 0.15 safe margin)
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


def _wrap_to_lines(label: str, n: int) -> str:
    """The label broken over at most n lines, with the lines as long as that allows."""
    longest = max((len(w) for w in label.split()), default=1)
    for budget in range(longest, len(label) + 1):
        lines = textwrap.wrap(label, budget)
        if len(lines) <= n:
            return "\n".join(lines)
    return label


_METRICS: dict = {}


def text_metrics():
    """Measured once: how wide one Consolas character is, how far apart two lines sit, and how tall a line's
    glyphs get, per point of font size, in the exact Text style the blocks use. Consolas is monospace, so a
    line's width is just its character count."""
    if not _METRICS:
        F = 100.0
        kw = dict(font="Consolas", font_size=F, weight=BOLD, line_spacing=LINE_SPACING)
        one = Text("MMMMMMMMMM", **kw)
        two = Text("MMMMMMMMMM\nMMMMMMMMMM", **kw)
        deep = Text("Mg", **kw)
        _METRICS["char_w"] = one.width / 10 / F
        _METRICS["line_pitch"] = (two.height - one.height) / F
        _METRICS["glyph_h"] = deep.height / F          # cap height plus descender: the tallest one line gets
    return _METRICS["char_w"], _METRICS["line_pitch"], _METRICS["glyph_h"]


def fit_size(lines, w_u: float, h_u: float, top_inset: float = 0.0, bot_inset: float = 0.0) -> float:
    """The biggest font size at which these lines fit a w_u x h_u box (scene units). The insets are width the
    first/last line must give up, for the legend swatches that sit in the block's corners."""
    cw, pitch, gh = text_metrics()
    n = len(lines)
    budget = [w_u - (top_inset if i == 0 else 0.0) - (bot_inset if i == n - 1 else 0.0) for i in range(n)]
    by_w = min(budget[i] / max(len(l) * cw, 1e-9) for i, l in enumerate(lines))
    return min(by_w, h_u / max((n - 1) * pitch + gh, 1e-9))


def wrap_label(label: str, w_u: float, h_u: float, top_inset: float = 0.0, bot_inset: float = 0.0) -> str:
    """Pick the line breaks that let the text be biggest inside a w_u x h_u box (scene units). Uses the real
    font metrics, so the choice agrees with the size the text is actually given later. Ties go to fewer lines."""
    words = label.split()
    if not words:
        return label
    best, best_score = label, -1.0
    for k in range(1, min(len(words), 4) + 1):
        for lines in _partitions(words, k):
            score = fit_size(lines, w_u, h_u, top_inset, bot_inset)
            if score > best_score + 1e-6:
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
        cw = text_metrics()[0]                       # characters that fit one line at font size 26
        self.max_chars = max(16, int((x1 - x0 - 0.6) / (cw * 26)))
        self.title_txt = Text(title, font="Consolas", font_size=22, color=theme.active, weight=BOLD)
        if self.title_txt.width > (x1 - x0) - 0.6:          # shrink first, then place: scaling moves the centre
            self.title_txt.scale(((x1 - x0) - 0.6) / self.title_txt.width)
        self.title_txt.move_to([x0 + 0.3, y1 - 0.5, 0], aligned_edge=LEFT)
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
    PANEL_GAP = 0.25
    MIN_PANEL_W = 4.8        # the step panel never gets narrower than this

    def __init__(self, name: str, theme=None, height_units: float = None, center_x: float = None, panel=True, title=None):
        super().__init__()
        self.theme = theme or Theme()
        self.truth, self.layout = load(name)
        w_px, h_px = self.layout["image_size"]
        half_w, half_h = config.frame_width / 2, config.frame_height / 2
        self.ox, self.oy = w_px / 2, h_px / 2
        self._margin_wraps = self._wrap_margin_labels()
        if height_units is None:
            # fit the reference in the frame height AND in the width left over once the panel has its share,
            # so a landscape reference (Earlgrey) is not pushed out past the panel. The gutter the margin labels
            # need depends on the scale, and the scale on the gutter, so settle the two together: sizing the
            # panel from one scale and placing it from another leaves it narrower than MIN_PANEL_W.
            fit_h = (config.frame_height - 2 * FRAME_MARGIN) / h_px
            self.u = fit_h
            for _ in range(5):
                gutter = self._margin_boxes()
                u = min(fit_h, (config.frame_width - 2 * FRAME_MARGIN - self.PANEL_GAP - self.MIN_PANEL_W
                                - gutter) / w_px)
                if abs(u - self.u) < 1e-9:
                    break
                self.u = u
        else:
            self.u = height_units / h_px
            gutter = self._margin_boxes()
        if center_x is None:                      # left-align the drawing, leaving a gutter for the margin labels
            center_x = -half_w + FRAME_MARGIN + gutter + w_px * self.u / 2
        self.cx = center_x
        self._panel_x0 = center_x + w_px * self.u / 2 + self.PANEL_GAP
        self._panel_x1 = half_w - FRAME_MARGIN
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
        self._pending_labels: list = []
        self._wire_starts: list = []          # where wires already start and end: a detour must not begin
        self._wire_ends: list = []            # where another one ends (they would be read as a single long wire)
        self._build()
        self._size_texts()
        self._place_labels()
        if panel:
            self.panel = StepPanel(self.theme, self._panel_x0, self._panel_x1, -half_h + FRAME_MARGIN,
                                   half_h - FRAME_MARGIN, title or self.truth.get("diagram_title") or "")
            self.legend = self._legend()
            self.panel.add(self.legend)
            self.add(self.panel)

    # ------------------------------------------------------------ margin labels
    def _wrap_margin_labels(self) -> dict:
        """Margin labels ("DMA System Egress") sit in the strip left of the drawing. Break them to a readable
        line length up front, so the strip can be made exactly as wide as they need."""
        out = {}
        chars = self.layout.get("label_chars", {})
        for e in self.truth.get("externals", []):
            if e["id"] in self.layout.get("labels", {}):
                limit = chars.get(e["id"], MARGIN_LABEL_CHARS)      # per label: the reference's own line breaks
                words, lines, cur = e["label"].split(), [], ""
                for word in words:
                    cand = (cur + " " + word).strip()
                    if cur and len(cand) > limit:
                        lines.append(cur)
                        cur = word
                    else:
                        cur = cand
                lines.append(cur)
                out[e["id"]] = "\n".join(lines)
        return out

    def _drawing_left(self) -> float:
        """Leftmost pixel of anything drawn from the reference (the outer region border, normally)."""
        return min([b[0] for b in self.layout["blocks"].values()] +
                   [r[0] for r in self.layout["regions"].values()])

    def _drawing_right(self) -> float:
        """Rightmost pixel of anything drawn from the reference."""
        return max([b[2] for b in self.layout["blocks"].values()] +
                   [r[2] for r in self.layout["regions"].values()])

    def _drawing_bottom(self) -> float:
        """Lowest pixel of anything drawn from the reference."""
        return max([b[3] for b in self.layout["blocks"].values()] +
                   [r[3] for r in self.layout["regions"].values()])

    def _label_side(self, box) -> str:
        """Which margin a free label lives in. Left is the default: that is where Darjeeling prints all of
        its, and its boxes overlap the drawing's own left edge, so left cannot be told from position alone --
        only the other two sides can."""
        if box[0] >= self._drawing_right():
            return "right"
        if box[1] >= self._drawing_bottom():
            return "bottom"
        return "left"

    def _margin_boxes(self) -> float:
        """Give each margin label the pixel box its text really needs. A left label is pulled out into the
        gutter, keeping the right edge the reference gave it (that is where its wire arrives); a label at the
        bottom or right edge (Peppermint prints them there) keeps its place and grows about it. -> how far the
        widest left one reaches past the drawing, in scene units: the gutter the drawing has to be inset by."""
        cw, pitch, gh = text_metrics()
        overhang = 0.0
        if not hasattr(self, "_label_boxes0"):                      # keep the originals: this may run twice
            self._label_boxes0 = {k: list(v) for k, v in self.layout.get("labels", {}).items()}
        for lid, wrapped in self._margin_wraps.items():
            box = self._label_boxes0[lid]
            side = self._label_side(box)
            # a gutter label is given all the room it needs; the other two sides only have what the picture
            # left around the drawing, so they are sized for the floor instead
            font = MARGIN_LABEL_FONT if side == "left" else MARGIN_LABEL_MIN
            lines = wrapped.split("\n")
            w = max(len(l) for l in lines) * cw * font / self.u                       # in image pixels
            h = ((len(lines) - 1) * pitch + gh) * font / self.u
            cy = (box[1] + box[3]) / 2
            if side == "left":
                # keep the label out of the drawing: its right edge stops short of the outermost border, so its
                # arrow leaves the drawing to reach it, exactly as the reference shows
                right = min(box[2], self._drawing_left()) - 0.12 / self.u      # 0.12 scene units of air
                self.layout["labels"][lid] = [right - w, cy - h / 2, right, cy + h / 2]
                overhang = max(overhang, -(right - w) * self.u)
            elif side == "right":
                left = max(box[0], self._drawing_right() + 0.12 / self.u)
                self.layout["labels"][lid] = [left, cy - h / 2, left + w, cy + h / 2]
            else:                                   # bottom: keep its place, grow about its own centre
                cx = (box[0] + box[2]) / 2
                self.layout["labels"][lid] = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
        return overhang + 0.06 if self._margin_wraps else 0.15

    # ---------------------------------------------------------------- geometry
    def P(self, x, y):
        return np.array([(x - self.ox) * self.u + self.cx, -(y - self.oy) * self.u, 0.0])

    def _box(self, b):
        (x0, y0), (x1, y1) = self.P(b[0], b[1])[:2], self.P(b[2], b[3])[:2]
        return (x0 + x1) / 2, (y0 + y1) / 2, abs(x1 - x0), abs(y1 - y0)

    def _header_height(self, region_box, h: float) -> float:
        """How tall the strip above a region's own blocks is, in scene units: all the room its title has before
        it starts sitting on them."""
        inside = [b for b in self.layout["blocks"].values()
                  if region_box[0] <= b[0] and b[2] <= region_box[2] and region_box[1] <= b[1] and b[3] <= region_box[3]]
        if not inside:
            return h - 0.12
        return max(0.1, (min(b[1] for b in inside) - region_box[1]) * self.u - 0.10)

    # ------------------------------------------------------------------- build
    def _build(self):
        T, L, th = self.truth, self.layout, self.theme
        region_style = {0: ("#0B0F14", "#E5E7EB", 3), 1: ("#10161D", "#475569", 1), 2: ("#141D28", "#64748B", 1.5)}
        parent = {r["id"]: r.get("parent") for r in T["regions"]}

        def depth_of(rid):                        # how deeply nested: 0 is the outermost box
            d, p = 0, parent.get(rid)
            while p:
                d, p = d + 1, parent.get(p)
            return d
        for r in T["regions"]:
            box = L["regions"][r["id"]]
            cx, cy, w, h = self._box(box)
            d = depth_of(r["id"])
            fill, stroke, sw = region_style[min(d, 2)]
            dg = DomainGroup(r["label"], cx, cy, w, h, fill, stroke=stroke, fit=False)
            scale, label = 0.5 if d == 0 else 11 / 24, r["label"]
            room_w = w - 0.16
            room_h = self._header_height(box, h)
            if d > 0 and (dg.txt.width * scale > room_w or dg.txt.height * scale > room_h):
                # A nested title that does not fit the strip above the region's own blocks (Peppermint's AON
                # domain). Break it over lines, as the reference does, rather than shrink it until it cannot be
                # read: try one, two and three lines and keep whichever ends up biggest. The outermost title
                # spans the whole drawing, so it is only shrunk, which keeps it on one line as the reference has.
                best = None
                for n in (1, 2, 3):
                    cand = _wrap_to_lines(label, n)
                    probe = DomainGroup(cand, cx, cy, w, h, fill, stroke=stroke, fit=False)
                    got = scale * min(room_w / max(probe.txt.width, 1e-9), room_h / max(probe.txt.height, 1e-9), 1.0)
                    if best is None or got > best[0] + 1e-6:
                        best = (got, cand, probe)
                _got, label, dg = best
            dg.bg.set_stroke(stroke, sw)
            # smaller title, kept inside the top-left corner
            dg.txt.scale(scale)
            fits = min(room_w / max(dg.txt.width, 1e-9), room_h / max(dg.txt.height, 1e-9), 1.0)
            if fits < 1.0:                              # still too big: shrink it the rest of the way
                dg.txt.scale(fits)
            n_lines = label.count("\n") + 1
            dg.txt.move_to(dg.bg.get_corner(UP + LEFT) + RIGHT * 0.12 + DOWN * (0.13 if n_lines == 1 else 0.06),
                           aligned_edge=LEFT if n_lines == 1 else UP + LEFT)
            dg.label_wrapped = label          # the text as drawn, spaces intact (Text.text drops them)
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
        legend = b.get("fill_legend") or b.get("fill")      # no legend in the picture -> the fill as drawn
        stroke, fill = FILL.get(legend, ("#9CA3AF", "#1B1F26"))
        attrs = b.get("attributes", [])
        if "blue_outline" in attrs:
            stroke = BLUE_OUTLINE
        # The text area is the box minus padding, minus the strip the legend swatches sit in, so a swatch never
        # lands on a letter. Swatches go into free corners (top-left first, then bottom-right, as the reference
        # does); the title block is centred and its lines are left-aligned, so it gives up the strip on both sides.
        marks = b.get("markers", [])
        side = min(0.07, h * 0.18)
        corners = [(UP + LEFT, RIGHT, DOWN), (DOWN + RIGHT, LEFT, UP), (UP + RIGHT, LEFT, DOWN), (DOWN + LEFT, RIGHT, UP)]
        strip = 0.04 + side + 0.025
        left_strip = strip if any(corners[i % 4][1] is RIGHT for i in range(len(marks))) else 0.0
        right_strip = strip if any(corners[i % 4][1] is LEFT for i in range(len(marks))) else 0.0
        tw, thh = w * TEXT_PAD_W - left_strip - right_strip, h * TEXT_PAD_H
        text_dx = (left_strip - right_strip) / 2
        wrapped = wrap_label(b["label"] or "", tw, thh)
        blk = IPBlock(wrapped, th, width=w, height=h, fill=fill, stroke=stroke, text_color=th.text,
                      line_spacing=LINE_SPACING, min_font_size=0)   # dense whole-chip mode: labels are wrapped above
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
        if wrapped.strip():
            self._pending_fit.append((blk, tw, thh, text_dx))
        else:
            blk.remove(blk.txt)      # a box the reference draws with no text: drop the empty Text entirely,
                                     # so it is neither drawn nor measured (an empty Text has no font size)
        blk.has_markers = bool(marks)
        for i, m in enumerate(marks):
            corner, inx, iny = corners[i % 4]
            sq = Square(side_length=side, fill_color=MARKER.get(m["color"], "#FFFFFF"), fill_opacity=1, stroke_width=0)
            sq.move_to(blk.bg.box.get_corner(corner) + inx * (0.04 + side / 2) + iny * (0.04 + side / 2))
            sq.is_marker = True
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
        """One common font size for all block titles (the library only ever shrinks text); a block whose text
        area is too small for that size gets the largest size that fits there."""
        fits = []
        for blk, tw, thh, _dx in self._pending_fit:
            t = blk.txt
            fits.append(t.font_size * min(tw / max(t.width, 1e-6), thh / max(t.height, 1e-6)))
        common = min(float(np.median(fits)) * 0.95, MAX_BLOCK_FONT)
        for (blk, tw, thh, dx), fit in zip(self._pending_fit, fits):
            t = blk.txt
            t.scale(min(common, fit) / t.font_size)
            t.move_to(blk.bg.box.get_center() + RIGHT * dx)
            if blk is self.blocks.get("soc_proxy"):
                t.move_to(blk.bg.box.get_top() + DOWN * 0.16)
            self._clear_markers(blk)
        self.common_font = common
        self._smallest_font = min(fits) if fits else common

    @staticmethod
    def _clear_markers(blk, gap=0.02):
        """Last word on the legend swatches: measure the letters that were actually drawn and shrink the title
        until no glyph touches a swatch. The estimate above is close, so this rarely does anything."""
        marks = [m for m in blk.submobjects if getattr(m, "is_marker", False)]
        if not marks:
            return
        cw, pitch, gh = text_metrics()
        lines = blk.title.split("\n")
        for _ in range(12):
            t = blk.txt
            f, cx, top = t.font_size, t.get_center()[0], t.get_top()[1]
            hit = False
            left = t.get_left()[0]                            # Text draws its lines left-aligned
            for i, line in enumerate(lines):                  # one box per line: Consolas is monospace
                x0, x1 = left, left + len(line) * cw * f
                y1, y0 = top - i * pitch * f, top - i * pitch * f - gh * f
                hit = hit or any(x0 - gap < m.get_right()[0] and x1 + gap > m.get_left()[0] and
                                 y0 - gap < m.get_top()[1] and y1 + gap > m.get_bottom()[1] for m in marks)
            if not hit:
                return
            t.scale(0.94, about_point=t.get_center())

    def _add_label(self, e):
        self._pending_labels.append(e)

    def _place_labels(self):
        """Free labels in the margin (e.g. "DMA System Egress"). They grow leftwards out of the drawing, into
        the gutter kept for them, and are then nudged back inside the frame if they still stick out."""
        half_w, half_h = config.frame_width / 2, config.frame_height / 2
        # One size for all of them, as the block titles do. A gutter label was given a box that fits
        # MARGIN_LABEL_FONT; a label that keeps the reference's own box (Peppermint prints them along the bottom
        # and right edges too) only has the room the picture gave it, so the tightest box sets the size for all.
        size = min([MARGIN_LABEL_FONT] + [fit_size(self._margin_wraps[e["id"]].splitlines(),
                                                   *self._box(self.layout["labels"][e["id"]])[2:])
                                          for e in self._pending_labels])
        size = max(size, MARGIN_LABEL_MIN)       # readability floor; the linter reports it if they then collide
        for e in self._pending_labels:
            cx, cy, w, h = self._box(self.layout["labels"][e["id"]])
            wrapped = self._margin_wraps[e["id"]]
            t = Text(wrapped, font="Consolas", font_size=size, color=self.theme.text, line_spacing=LINE_SPACING)
            t.move_to([cx, cy, 0])
            # sit against the edge of the box that faces the drawing, so the label meets its own arrow instead
            # of floating in the middle of the room reserved for it
            side = self._label_side(self._label_boxes0[e["id"]])
            if side == "left":
                t.align_to([cx + w / 2, cy, 0], RIGHT)
            elif side == "right":
                t.align_to([cx - w / 2, cy, 0], LEFT)
            right_edge = min(half_w - FRAME_MARGIN, self._panel_x0 - 0.1)      # never under the step panel
            dx = max(0.0, (-half_w + FRAME_MARGIN) - t.get_left()[0])
            dx -= max(0.0, t.get_right()[0] - right_edge)
            dy = max(0.0, (-half_h + FRAME_MARGIN) - t.get_bottom()[1])
            dy -= max(0.0, t.get_top()[1] - (half_h - FRAME_MARGIN))
            t.shift(RIGHT * dx + UP * dy)
            self.labels[e["id"]] = t
            self.add(t)

    # -------------------------------------------------------------- connections
    def _route(self, c):
        """-> list of px points, or list of such lists (multi)."""
        L = self.layout
        spec = L["routes"].get(c["id"], {})
        fb = L["blocks"].get(c["from"].split(".")[0]) or L["labels"].get(c["from"])
        tb = L["blocks"].get(c["to"].split(".")[0]) or L["labels"].get(c["to"])
        ends = {str(c["from"]).split(".")[0], str(c["to"]).split(".")[0]}
        if "route" in spec:
            r = spec["route"]
            # a hand-read route is kept as it is, unless it would be drawn straight over a block
            if len(r) == 2 and fb and tb:
                return [self._avoid(r, fb, tb, ends, vertical=r[0][0] == r[1][0])]
            return [r]
        if "multi" in spec:
            return [[[a, b], [cc, d]] for a, b, cc, d in spec["multi"]]
        ox = min(fb[2], tb[2]) - max(fb[0], tb[0])      # x-overlap
        oy = min(fb[3], tb[3]) - max(fb[1], tb[1])
        at = spec.get("at")
        if ox >= oy:                                    # stacked vertically -> vertical stem
            x = at if at is not None else (max(fb[0], tb[0]) + min(fb[2], tb[2])) / 2
            straight = [[x, fb[3]], [x, tb[1]]] if fb[3] <= tb[1] else [[x, fb[1]], [x, tb[3]]]
            return [self._avoid(straight, fb, tb, ends, vertical=True)]
        y = at if at is not None else (max(fb[1], tb[1]) + min(fb[3], tb[3])) / 2
        straight = [[fb[2], y], [tb[0], y]] if fb[2] <= tb[0] else [[fb[0], y], [tb[2], y]]
        return [self._avoid(straight, fb, tb, ends, vertical=False)]

    # ---- block avoidance -------------------------------------------------
    AVOID_PAD = 3.0          # image pixels of clearance a wire keeps from a block it passes

    def _obstacles(self, ends):
        """Every block except the wire's own two ends and anything nested in (or around) them -- a wire into a
        block drawn inside another block has to cross the outer one."""
        all_boxes = dict(self.layout["blocks"], **self.layout.get("labels", {}))
        boxes = [all_boxes[e] for e in ends if e in all_boxes]

        def nested(b):
            return any((b[0] >= e[0] and b[1] >= e[1] and b[2] <= e[2] and b[3] <= e[3]) or
                       (e[0] >= b[0] and e[1] >= b[1] and e[2] <= b[2] and e[3] <= b[3]) for e in boxes)
        return [b for bid, b in all_boxes.items() if bid not in ends and not nested(b)]

    @staticmethod
    def _crosses(p, q, box, pad):
        x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
        if p[0] == q[0]:
            a, b = sorted((p[1], q[1]))
            return x0 < p[0] < x1 and not (b <= y0 or a >= y1)
        a, b = sorted((p[0], q[0]))
        return y0 < p[1] < y1 and not (b <= x0 or a >= x1)

    def _clear(self, pts, obstacles, pad):
        return all(not self._crosses(pts[i], pts[i + 1], o, pad)
                   for i in range(len(pts) - 1) for o in obstacles)

    def _avoid(self, straight, fb, tb, ends, vertical):
        """If the straight wire would run over a block that is not one of its own ends, take it out of the
        source's side, along the nearest free channel, and back into the target's side. The reference's own
        routes are kept whenever they are already clear."""
        obstacles = self._obstacles(ends)
        pad = self.AVOID_PAD
        if self._clear(straight, obstacles, pad):
            return straight
        # work in a canonical frame where the wire's long run is horizontal and the free channel varies in y
        swap_box = (lambda b: [b[1], b[0], b[3], b[2]]) if vertical else (lambda b: b)
        unswap_pt = (lambda p: [p[1], p[0]]) if vertical else (lambda p: p)
        f, t = swap_box(fb), swap_box(tb)
        obs = [swap_box(o) for o in obstacles]
        fcx, fcy = (f[0] + f[2]) / 2, (f[1] + f[3]) / 2
        tcx, tcy = (t[0] + t[2]) / 2, (t[1] + t[3]) / 2
        forward = f[2] <= t[0]                                     # target lies the +x way in canonical space
        fx_near, tx_near = (f[2], t[0]) if forward else (f[0], t[2])
        gap = pad + 2.0
        # stay as close as possible to the channel the reference used, so a detour does not wander across the
        # drawing and land on an edge another wire already leaves from
        base = straight[0][0] if vertical else straight[0][1]
        fallback = None
        for yc in sorted({round(v, 1) for o in obs for v in (o[1] - gap, o[3] + gap)}, key=lambda v: abs(v - base)):
            pts = []
            if f[1] < yc < f[3]:            # the channel passes the source: leave by the edge facing the target
                pts.append([fx_near, yc])
            else:                           # otherwise leave sideways, then turn onto the channel
                pts += [[fcx, f[3] if yc > fcy else f[1]], [fcx, yc]]
            if t[1] < yc < t[3]:
                pts.append([tx_near, yc])
            else:
                pts += [[tcx, yc], [tcx, t[3] if yc > tcy else t[1]]]
            pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
            if len(pts) < 2 or any(p[0] != q[0] and p[1] != q[1] for p, q in zip(pts, pts[1:])):
                continue
            real = [unswap_pt(p) for p in pts]
            if self._clear(real, obstacles, pad):
                # a detour that leaves from a point another wire already uses would merge with it into one
                # long wire, so keep looking for a free one
                touch = (any(abs(e[0] - real[0][0]) < 2 and abs(e[1] - real[0][1]) < 2 for e in self._wire_ends) or
                         any(e[0] == real[-1][0] and e[1] == real[-1][1] for e in self._wire_starts))
                if touch:
                    fallback = fallback or real
                    continue
                return real
        return fallback or straight

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
        for pts_px in routes:
            self._wire_starts.append(pts_px[0])
            self._wire_ends.append(pts_px[-1])
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
        fills = []
        for e in self.truth.get("legend", []):
            if e["swatch"].endswith("fill"):
                word = e["swatch"].split()[0]
                fills.append((e["label"], FILL[e["label"]][0] if e["label"] in FILL else MARKER.get(word, "#9CA3AF")))
        # a picture with no legend (Peppermint) explains nothing about its colours: don't invent a meaning
        lines = [("Clock speed (fill color):", None)] + fills if fills else [("Drawing notes:", None)]
        attrs = {a for b in self.truth["blocks"] for a in b.get("attributes", [])}
        if "dashed_outline" in attrs or any(e.get("id") for e in self.truth.get("externals", [])):
            lines.append(("dashed box: not fully implemented yet" if fills else
                          "dashed box: the picture does not say", "#9CA3AF"))
        if "blue_outline" in attrs:
            lines.append(("blue outline: new in rev2", BLUE_OUTLINE))
        if self.unconfirmed or any("unclear" in b for b in self.truth["blocks"]):
            lines.append(("amber dashed line: not sure (see report)", UNCONFIRMED))
        x0 = self._panel_x0
        head = ui_text(lines[0][0], 13, th.muted)
        head.move_to([x0 + 0.30, y, 0], aligned_edge=LEFT)
        items.add(head)
        for txt, col in lines[1:]:
            y -= 0.33
            sw = Circle(radius=0.08, fill_color=col, fill_opacity=0.9, stroke_width=0).move_to([x0 + 0.37, y, 0])
            t = ui_text(txt, 12, th.text).move_to([x0 + 0.60, y, 0], aligned_edge=LEFT)
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
