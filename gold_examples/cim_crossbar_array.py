"""Compute-in-memory crossbar: a wordline opens a row, every cell drives its bitline, sense amps read the column.

Structure follows the resistive crossbar accelerators described in A. Shafiee et al., "ISAAC: A Convolutional
Neural Network Accelerator with In-Situ Analog Arithmetic in Crossbars", ISCA 2016, and P. Chi et al., "PRIME:
A Novel Processing-in-Memory Architecture for Neural Network Computation in ReRAM-Based Main Memory", ISCA 2016.
The row-decoder / array / sense-amplifier partitioning is the standard memory macro organisation. See
docs/SOURCES.md.

Why this is a gold example: here the interesting parts are not boxes at all --
  * THE BLOCKS ARE THE INTERSECTIONS. Wordlines and bitlines are full-length lines, and a cell is a small square
    placed where two of them cross, at a computed coordinate. No diagram we had drawn a matrix before.
  * A CELL CHANGES IN PLACE INSTEAD OF A PACKET MOVING. Reading is shown by recolouring the cells on the live
    row, because nothing physically travels along a wordline that a viewer could follow.
  * ANALOG AND DIGITAL ARE VISUALLY SEPARATED. The array and the sense amplifiers are grouped apart from the
    digital output, so where the signal stops being a current and becomes a bit is visible.
  * ONE ROW LIGHTS AT A TIME, ALL OF ITS COLUMNS AT ONCE. Every cell on the row is animated in a single play()
    call, which is what "the whole row is read in one cycle" means.
"""
from manim import DOWN, LEFT, RIGHT, UP, Line, Scene, Square

from ipmotion_lib import Banner, IPBlock, Theme, ui_text

ROWS, COLS = 4, 6
PX, PY = 0.92, 0.72                     # bitline and wordline pitch
X0, Y0 = -1.05, 1.18                    # the (0,0) crossing
CELL = 0.30

WL_IDLE, WL_LIVE = "#475569", "#FFD700"
BL_IDLE, BL_LIVE = "#475569", "#00FFF0"
CELL_0, CELL_1 = "#1B1F26", "#34D399"

# which cells hold a 1: a fixed pattern so the read result is something the viewer can check
PATTERN = [[1, 0, 1, 1, 0, 0],
           [0, 1, 1, 0, 1, 0],
           [1, 1, 0, 0, 0, 1],
           [0, 0, 1, 0, 1, 1]]


class CimCrossbarArray(Scene):
    def construct(self):
        theme = Theme()

        banner = Banner("Compute in memory: one wordline, every column at once", theme)
        banner.move_to([0, 3.5, 0])
        self.add(banner)

        last_x = X0 + (COLS - 1) * PX
        bottom = Y0 - (ROWS - 1) * PY

        # the decoder and the sense amps are built FIRST, so every line can end ON one of them instead of
        # stopping in empty space -- which is what the linter calls a dangling endpoint, and it is right to.
        decoder = IPBlock("Row decoder", theme, width=1.40, height=2.35, line_spacing=0.3)
        decoder.move_to([X0 - 1.70, Y0 - (ROWS - 1) * PY / 2, 0])
        self.add(decoder)

        amps = []
        for c in range(COLS):
            a = IPBlock("SA", theme, width=0.70, height=0.52)
            a.move_to([X0 + c * PX, bottom - 0.74, 0])
            amps.append(a)
            self.add(a)

        wl, bl, cell = {}, {}, {}
        for r in range(ROWS):
            y = Y0 - r * PY
            wl[r] = Line([decoder.get_right()[0], y, 0], [last_x, y, 0],
                         color=WL_IDLE, stroke_width=3)
            self.add(wl[r])
            lab = ui_text(f"WL{r}", 14, theme.muted)
            lab.move_to([decoder.get_left()[0] - 0.42, y, 0])
            self.add(lab)
        for c in range(COLS):
            x = X0 + c * PX
            bl[c] = Line([x, Y0, 0], amps[c].get_top(), color=BL_IDLE, stroke_width=3)
            self.add(bl[c])
            lab = ui_text(f"BL{c}", 14, theme.muted)
            lab.move_to([x, Y0 + 0.44, 0])
            self.add(lab)

        # a cell sits where a wordline crosses a bitline
        for r in range(ROWS):
            for c in range(COLS):
                sq = Square(side_length=CELL, fill_opacity=1, stroke_width=2,
                            fill_color=CELL_1 if PATTERN[r][c] else CELL_0, stroke_color="#64748B")
                sq.move_to([X0 + c * PX, Y0 - r * PY, 0])
                cell[(r, c)] = sq
                self.add(sq)

        out = IPBlock("Digital output register", theme, width=5.2, height=0.68)
        out.move_to([X0 + (COLS - 1) * PX / 2, bottom - 1.78, 0])
        self.add(out)
        for c in range(COLS):
            self.add(Line(amps[c].get_bottom(), [X0 + c * PX, out.get_top()[1], 0],
                          color=BL_IDLE, stroke_width=2))

        key = ui_text("SA = sense amplifier, where the analog current becomes a bit.   "
                      "A green cell holds a 1, and one row is read per cycle.", 15, theme.muted)
        key.move_to([0, bottom - 2.48, 0])
        self.add(key)

        self.wait(0.8)
        for r in range(ROWS):
            bits = "".join(str(b) for b in PATTERN[r])
            self.play(banner.update_text(f"Row {r} selected: the decoder drives WL{r} high", theme, WL_LIVE),
                      wl[r].animate.set_color(WL_LIVE),
                      decoder.bg.animate.set_color(WL_LIVE), run_time=0.8)
            self.wait(1.2)
            self.play(*[cell[(r, c)].animate.set_stroke(WL_LIVE, 3) for c in range(COLS)],
                      *[bl[c].animate.set_color(BL_LIVE) for c in range(COLS)], run_time=0.8)
            self.wait(1.2)
            self.play(banner.update_text(f"Sense amps resolve row {r} to {bits}", theme, BL_LIVE),
                      *[a.bg.animate.set_color(BL_LIVE) for a in amps], run_time=0.8)
            self.wait(1.2)
            self.play(wl[r].animate.set_color(WL_IDLE),
                      decoder.bg.animate.set_color(theme.panel),
                      *[cell[(r, c)].animate.set_stroke("#64748B", 2) for c in range(COLS)],
                      *[bl[c].animate.set_color(BL_IDLE) for c in range(COLS)],
                      *[a.bg.animate.set_color(theme.panel) for a in amps], run_time=0.6)

        self.play(banner.update_text("Four rows, four cycles, and the array never moved its data", theme,
                                     CELL_1), run_time=0.8)
        self.wait(2.5)
