"""MESI cache-coherence state machine: one cache line moving between Modified, Exclusive, Shared and Invalid.

Protocol follows M.S. Papamarcos and J.H. Patel, "A Low-Overhead Coherence Solution for Multiprocessors with
Private Cache Memories", ISCA 1984, and the MESI description in Hennessy & Patterson, "Computer Architecture:
A Quantitative Approach", chapter on multiprocessor cache coherence. See docs/SOURCES.md.

Why this is a gold example: not every hardware diagram is a floorplan. RTL designers spend as much time
explaining state machines, and this is the only example that shows how to draw one --
  * NODES ARE CIRCLES AND THEY CARRY THEIR OWN LABEL. The letter and the full word both sit INSIDE the circle,
    so nothing can collide with a label parked outside it.
  * ARROWS CURVE BETWEEN NODES, AND TWO DIRECTIONS NEVER SHARE A PATH. Each transition is an arc with a signed
    bend; the pair between Modified and Shared bends opposite ways so both stay readable.
  * EVERY LABEL IS PLACED BY THE ARC, NOT BY HAND. The label is pushed along the arc's own perpendicular, so
    moving a state moves its labels correctly and no offset has to be re-tuned by eye.
  * AN ARROW CAN RETURN TO ITS OWN NODE. A read hit that leaves the line in Shared is a self-loop, which no
    block-diagram example contains.
  * THE DIAGRAM DOES NOT MOVE; THE HIGHLIGHT DOES. Nothing travels along a wire. The live state lights up and
    the taken transition flashes, which is how a state machine should be animated.
"""
import numpy as np
from manim import DOWN, LEFT, Arc, ArcBetweenPoints, Circle, Scene, VGroup

from ipmotion_lib import Banner, Theme, ui_text

R = 0.74
IDLE_FILL = "#141D28"
IDLE_LINE = "#64748B"
LIVE = "#FFD700"
EDGE = "#9CA3AF"
HOT = "#00FFF0"

POS = {                                  # four corners, so every edge of the square is a usable path
    "Modified":  np.array([-2.75,  1.30, 0.0]),
    "Exclusive": np.array([ 2.75,  1.30, 0.0]),
    "Shared":    np.array([-2.75, -1.30, 0.0]),
    "Invalid":   np.array([ 2.75, -1.30, 0.0]),
}


class MesiCacheFsm(Scene):
    def construct(self):
        theme = Theme()

        banner = Banner("MESI: how one cache line changes state", theme)
        banner.move_to([0, 3.5, 0])
        self.add(banner)

        node = {}
        for name, p in POS.items():
            c = Circle(radius=R, stroke_color=IDLE_LINE, stroke_width=3,
                       fill_color=IDLE_FILL, fill_opacity=1).move_to(p)
            letter = ui_text(name[0], 30, theme.text).move_to(p + np.array([0, 0.16, 0]))
            word = ui_text(name, 13, theme.muted).move_to(p + np.array([0, -0.28, 0]))
            g = VGroup(c, letter, word)
            g.circle = c
            node[name] = g
            self.add(g)

        def arc(a, b, bend, label, pad=0.30):
            """A transition arc from circle edge to circle edge. The label is pushed along the arc's own
            perpendicular, on the outside of the bend, so it never lands on the line it belongs to."""
            pa, pb = POS[a], POS[b]
            d = (pb - pa) / np.linalg.norm(pb - pa)
            line = ArcBetweenPoints(pa + d * R, pb - d * R, angle=bend,
                                    stroke_color=EDGE, stroke_width=3)
            line.add_tip(tip_length=0.18, tip_width=0.16)
            mid = line.point_from_proportion(0.5)
            perp = np.array([-d[1], d[0], 0.0]) * (1 if bend >= 0 else -1)
            lab = ui_text(label, 13, theme.muted)
            # clear the arc by the label's extent ALONG the perpendicular: half its width when pushed
            # sideways, half its height when pushed up or down. Using the height either way left the long
            # labels on a vertical arc still sitting on the line.
            reach = abs(perp[0]) * lab.width / 2 + abs(perp[1]) * lab.height / 2
            lab.move_to(mid + perp * (pad + reach))
            self.add(line, lab)
            return line

        edges = {
            ("Exclusive", "Modified"): arc("Exclusive", "Modified", 0.0, "write hit"),
            ("Invalid", "Exclusive"): arc("Invalid", "Exclusive", 0.0, "read miss, no sharer"),
            ("Invalid", "Shared"): arc("Invalid", "Shared", 0.0, "read miss, shared"),
            ("Shared", "Modified"): arc("Shared", "Modified", 0.55, "write hit, invalidate"),
            ("Modified", "Shared"): arc("Modified", "Shared", 0.55, "snoop read, write back"),
            ("Modified", "Invalid"): arc("Modified", "Invalid", 0.45, "snoop write"),
        }

        # a transition that ends where it started: a read hit leaves Shared in Shared
        anchor = POS["Shared"] + np.array([-R - 0.42, 0.0, 0.0])
        loop = Arc(radius=0.42, start_angle=np.deg2rad(-60), angle=np.deg2rad(260),
                   stroke_color=EDGE, stroke_width=3).move_to(anchor)
        loop.add_tip(tip_length=0.16, tip_width=0.14)
        loop_lab = ui_text("read hit", 13, theme.muted).move_to(anchor + np.array([-1.18, 0.0, 0.0]))
        self.add(loop, loop_lab)

        key = ui_text("the line is in exactly one of these four states at any moment", 16, theme.muted)
        key.move_to([0, -3.15, 0])
        self.add(key)

        def light(name, edge=None, text=""):
            anims = [node[n].circle.animate.set_stroke(LIVE if n == name else IDLE_LINE, 5 if n == name else 3)
                     for n in POS]
            anims.append(banner.update_text(text, theme, LIVE))
            if edge is not None:
                anims.append(edge.animate.set_color(HOT))
            self.play(*anims, run_time=0.8)
            self.wait(1.2)
            if edge is not None:
                self.play(edge.animate.set_color(EDGE), run_time=0.4)

        self.wait(0.8)
        light("Invalid", None, "The line starts Invalid: this cache does not have it")
        light("Exclusive", edges[("Invalid", "Exclusive")], "Read miss, nobody else has it: Exclusive")
        light("Modified", edges[("Exclusive", "Modified")], "A write hit makes it Modified: dirty and private")
        light("Shared", edges[("Modified", "Shared")], "Another core reads it: write back, drop to Shared")
        light("Shared", None, "A read hit keeps it Shared, with no bus traffic")
        light("Modified", edges[("Shared", "Modified")], "A write here invalidates the other copies: Modified")
        light("Invalid", edges[("Modified", "Invalid")], "Another core writes: this copy becomes Invalid")

        self.play(banner.update_text("Four states, and every bus event moves between them", theme, HOT),
                  run_time=0.8)
        self.wait(2.5)
