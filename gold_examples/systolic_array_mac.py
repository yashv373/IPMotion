"""4x4 output-stationary systolic array doing a matrix multiply, wavefront by wavefront.

Structure follows the classic systolic array of H.T. Kung and C.E. Leiserson, "Systolic Arrays (for VLSI)",
Sparse Matrix Proceedings, 1978, and the output-stationary MAC array described in Jouppi et al., "In-Datacenter
Performance Analysis of a Tensor Processing Unit", ISCA 2017. See docs/SOURCES.md.

Why this is a gold example: it is the first one that is not a floorplan. It teaches patterns the chip examples
cannot --
  * REPEATED BLOCKS COME FROM A LOOP. Sixteen processing elements are four lines of Python, not sixteen block
    definitions. A long script is a script that runs out of room and breaks; a loop is short and cannot drift.
  * GRID COORDINATES ARE COMPUTED. Row and column positions come from arithmetic on an origin and a pitch, so
    the grid is exact and no two cells can overlap.
  * THINGS HAPPEN AT THE SAME TIME. A wavefront lights a whole diagonal in ONE self.play(*anims) call, which is
    how parallel hardware should be drawn. Strictly sequential steps would misrepresent the machine.
"""
from manim import DOWN, LEFT, RIGHT, UP, Arrow, Scene, VGroup

from ipmotion_lib import Banner, IPBlock, Theme, ui_text

ROWS, COLS = 4, 4
PITCH_X, PITCH_Y = 1.18, 0.95          # centre-to-centre spacing, bigger than the block so cells cannot touch
CELL_W, CELL_H = 0.95, 0.72
ORIGIN_X, ORIGIN_Y = -0.58, 1.05       # centre of cell (0,0)

IDLE = "#1B1F26"
ACTIVE = "#FFD700"
WEIGHT = "#A78BFA"
ACT = "#00FFF0"
DONE = "#34D399"


class SystolicArrayMac(Scene):
    def construct(self):
        theme = Theme()

        banner = Banner("4x4 systolic array: a matrix multiply, one wavefront at a time", theme)
        banner.move_to([0, 3.5, 0])
        self.add(banner)

        # ---- the 16 processing elements, from a loop, at computed positions ----
        pe = {}
        for r in range(ROWS):
            for c in range(COLS):
                b = IPBlock(f"PE{r}{c}", theme, width=CELL_W, height=CELL_H, fill=IDLE, stroke="#64748B")
                b.move_to([ORIGIN_X + c * PITCH_X, ORIGIN_Y - r * PITCH_Y, 0])
                pe[(r, c)] = b
                self.add(b)

        # ---- activations enter from the left, one label per row ----
        act_lbl = []
        for r in range(ROWS):
            t = ui_text(f"a{r}0 a{r}1 a{r}2", 15, ACT)
            t.move_to([ORIGIN_X - PITCH_X - 0.95, ORIGIN_Y - r * PITCH_Y, 0])
            act_lbl.append(t)
            self.add(t)
            ar = Arrow(t.get_right() + RIGHT * 0.06, pe[(r, 0)].get_left(), buff=0.05,
                       color="#9CA3AF", stroke_width=3, max_tip_length_to_length_ratio=0.3)
            self.add(ar)

        # ---- weights are pushed down each column ----
        wt_lbl = []
        for c in range(COLS):
            t = ui_text(f"w{c}", 15, WEIGHT)
            t.move_to([ORIGIN_X + c * PITCH_X, ORIGIN_Y + PITCH_Y - 0.3, 0])
            wt_lbl.append(t)
            self.add(t)
            ar = Arrow(t.get_bottom() + DOWN * 0.04, pe[(0, c)].get_top(), buff=0.05,
                       color="#9CA3AF", stroke_width=3, max_tip_length_to_length_ratio=0.45)
            self.add(ar)

        # ---- partial sums leave the bottom of each column ----
        for c in range(COLS):
            t = ui_text(f"y{c}", 15, DONE)
            t.move_to([ORIGIN_X + c * PITCH_X, ORIGIN_Y - (ROWS - 1) * PITCH_Y - PITCH_Y + 0.26, 0])
            self.add(t)
            ar = Arrow(pe[(ROWS - 1, c)].get_bottom(), t.get_top() + UP * 0.04, buff=0.05,
                       color="#9CA3AF", stroke_width=3, max_tip_length_to_length_ratio=0.45)
            self.add(ar)

        legend = ui_text("activations flow right   weights flow down   each PE does one multiply-accumulate",
                         16, theme.muted)
        legend.move_to([0, -3.1, 0])
        self.add(legend)

        self.wait(1.0)

        # ---- the wavefront: every PE on a diagonal fires in the SAME play() call ----
        for step in range(ROWS + COLS - 1):
            cells = [(r, c) for r in range(ROWS) for c in range(COLS) if r + c == step]
            self.play(banner.update_text(f"Cycle {step + 1}: PEs on diagonal {step} multiply and accumulate",
                                         theme, ACTIVE), run_time=0.8)
            self.play(*[pe[k].bg.animate.set_color(ACTIVE) for k in cells], run_time=0.8)
            self.wait(1.2)
            self.play(*[pe[k].bg.animate.set_color(DONE) for k in cells], run_time=0.6)

        self.play(banner.update_text("All 16 partial sums complete: C = A x B", theme, DONE), run_time=0.8)
        self.wait(2.5)
