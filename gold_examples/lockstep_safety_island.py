"""Dual-core lockstep safety island: two identical cores, one comparator, one fault flag.

Structure follows the dual-core lockstep (DCLS) arrangement described for ARM Cortex-R class processors in
ARM's "Cortex-R5 Technical Reference Manual" (redundant core comparison and the delay used to decorrelate
common-cause faults), and the ASIL-D safety-island partitioning in ISO 26262-5 and Infineon's AURIX TriCore
safety documentation. See docs/SOURCES.md.

Why this is a gold example: it is the only one built on strict mirror symmetry --
  * POSITIONS ARE MIRRORED, NOT TYPED TWICE. Every block on the right is the left one's position with the sign
    of x flipped, so the two halves cannot drift apart as the layout is tuned.
  * TWO DATAPATHS MEET AT ONE BLOCK WITHOUT CROSSING. The two cores feed a single comparator from opposite
    sides, each entering its own half of the block, so neither wire has to pass over the other.
  * A SAFETY DOMAIN IS A REGION INSIDE A REGION. The ASIL-D island is drawn as its own box within the chip, so
    what is and is not inside the safety boundary is visible rather than implied.
  * A FAULT IS A STATE CHANGE, NOT A PACKET. The mismatch case recolours the comparator and raises a flag,
    which is how an error should be shown.
"""
from manim import DOWN, LEFT, RIGHT, UP, Arrow, Scene

from ipmotion_lib import Banner, DomainGroup, IPBlock, Theme, ui_text

CORE_W, CORE_H = 2.95, 1.20
CORE_X, CORE_Y = 2.55, 1.45          # the RIGHT core; the left one is the mirror of it
CMP_Y = -0.75
OK = "#34D399"
BAD = "#F87171"
LIVE = "#FFD700"
WIRE = "#9CA3AF"


class LockstepSafetyIsland(Scene):
    def construct(self):
        theme = Theme()

        banner = Banner("Dual-core lockstep: two cores, one answer, or a fault", theme)
        banner.move_to([0, 3.5, 0])
        self.add(banner)

        island = DomainGroup("Safety island (ASIL-D)", 0, 0.30, 9.4, 4.85, "#141D28", stroke="#64748B")
        self.add(island)

        # ---- the two cores: one definition, mirrored ----
        core, delay = {}, {}
        for side, name, sub in ((-1, "Core A", "primary"), (+1, "Core B", "redundant, 2-cycle delay")):
            b = IPBlock(f"{name}\n({sub})", theme, width=CORE_W, height=CORE_H, line_spacing=0.3)
            b.move_to([side * CORE_X, CORE_Y, 0])
            core[side] = b
            self.add(b)

        cmp_blk = IPBlock("Comparator", theme, width=3.1, height=1.0)
        cmp_blk.move_to([0, CMP_Y, 0])
        self.add(cmp_blk)

        # ---- each core enters its own half of the comparator, so the two wires never cross ----
        for side in (-1, +1):
            a = Arrow(core[side].get_bottom(),
                      cmp_blk.get_top() + RIGHT * (side * 0.95),
                      buff=0.06, color=WIRE, stroke_width=4, max_tip_length_to_length_ratio=0.22)
            delay[side] = a
            self.add(a)

        # ---- the same instruction stream reaches both cores ----
        feed = ui_text("instruction\nand data in", 15, theme.text)
        feed.move_to([-6.25, CORE_Y, 0])
        self.add(feed)
        self.add(Arrow(feed.get_right(), core[-1].get_left(), buff=0.08, color=WIRE, stroke_width=4,
                       max_tip_length_to_length_ratio=0.3))
        self.add(Arrow(core[-1].get_right(), core[+1].get_left(), buff=0.08, color=WIRE, stroke_width=4,
                       max_tip_length_to_length_ratio=0.12))

        flag = IPBlock("Fault flag", theme, width=2.5, height=0.85)
        flag.move_to([0, -2.75, 0])
        self.add(flag)
        self.add(Arrow(cmp_blk.get_bottom(), flag.get_top(), buff=0.06, color=WIRE, stroke_width=4,
                       max_tip_length_to_length_ratio=0.4))

        out = ui_text("to the safety manager", 15, theme.muted)
        out.move_to([4.15, -2.75, 0])
        self.add(out)
        self.add(Arrow(flag.get_right(), out.get_left(), buff=0.08, color=WIRE, stroke_width=3,
                       max_tip_length_to_length_ratio=0.22))

        note = ui_text("both cores run the same instruction; only the comparator decides whether they agree",
                       16, theme.muted)
        note.move_to([0, -3.55, 0])
        self.add(note)

        def step(text, colour, lit=(), cmp_colour=None, flag_colour=None):
            anims = [banner.update_text(text, theme, colour)]
            anims += [core[s].bg.animate.set_color(colour) for s in lit]
            if cmp_colour:
                anims.append(cmp_blk.bg.animate.set_color(cmp_colour))
            if flag_colour:
                anims.append(flag.bg.animate.set_color(flag_colour))
            self.play(*anims, run_time=0.8)
            self.wait(1.2)

        self.wait(0.8)
        step("The same instruction is issued to both cores", LIVE, lit=(-1, +1))
        step("Core B runs it two cycles later, so one glitch cannot hit both", LIVE, lit=(+1,))
        step("Both results arrive at the comparator", LIVE, lit=(-1, +1), cmp_colour=LIVE)
        step("They agree: the core pair is healthy, nothing is raised", OK, lit=(-1, +1), cmp_colour=OK)
        self.play(banner.update_text("Now a bit flips inside Core B", theme, BAD),
                  core[+1].bg.animate.set_color(BAD), run_time=0.8)
        self.wait(1.2)
        step("The results differ, so the comparator rejects them", BAD, cmp_colour=BAD)
        step("The fault flag reaches the safety manager in time to act", BAD,
             cmp_colour=BAD, flag_colour=BAD)
        self.wait(2.5)
