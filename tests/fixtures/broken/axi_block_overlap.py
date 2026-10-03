"""BROKEN FIXTURE (derived from gold_examples/axi_read_handshake.py).
Injected defect: master and slave are arranged with a negative gap so the blocks overlap (min_spacing).
Do not "fix" this file; tests expect the defect.
"""
from manim import *
from ipmotion_lib import *


class AxiBrokenBlockOverlap(Scene):
    def construct(self):
        theme = Theme()

        COLOR_DATA = BLUE
        COLOR_CTRL = GREEN
        COLOR_ACTIVE = YELLOW
        COLOR_INACTIVE = GRAY

        banner = Banner("AXI4 Read Handshake Protocol", theme)
        banner.move_to([0, 3.6, 0])

        master = IPBlock("AXI Master", theme, width=2.6, height=1.6)
        slave = IPBlock("AXI Slave", theme, width=2.6, height=1.6)
        cores = VGroup(master, slave).arrange(RIGHT, buff=-1.0)
        cores.move_to(ORIGIN)

        # Draw arrows for buses
        ar_fwd = Arrow(master.get_right() + UP*0.5, slave.get_left() + UP*0.5, color=COLOR_CTRL, buff=0.1)
        ar_bwd = Arrow(slave.get_left() + UP*0.2, master.get_right() + UP*0.2, color=COLOR_CTRL, buff=0.1)

        r_fwd = Arrow(slave.get_left() + DOWN*0.2, master.get_right() + DOWN*0.2, color=COLOR_DATA, buff=0.1)
        r_bwd = Arrow(master.get_right() + DOWN*0.5, slave.get_left() + DOWN*0.5, color=COLOR_CTRL, buff=0.1)

        ar_label = Text("Read Address Channel (AR)", font="Consolas", font_size=15, color=COLOR_CTRL)
        ar_label.next_to(ar_fwd, UP, buff=0.1)

        r_label = Text("Read Data Channel (R)", font="Consolas", font_size=15, color=COLOR_DATA)
        r_label.next_to(r_bwd, DOWN, buff=0.1)

        all_elements = VGroup(banner, ar_label, r_label, master, slave, ar_fwd, ar_bwd, r_fwd, r_bwd)
        all_elements.scale_to_fit_height(config.frame_height * 0.9)
        all_elements.move_to(ORIGIN)

        self.play(FadeIn(all_elements))
        self.wait(0.5)

        self.play(banner.update_text("Cycle 1: Master asserts ARVALID=1 & ARADDR=0x1000", theme, COLOR_ACTIVE))
        self.play(master.animate.set_stroke(COLOR_ACTIVE))
        self.play(ar_fwd.animate.set_color(COLOR_ACTIVE))
        self.play(slave.animate.set_stroke(COLOR_ACTIVE))
        self.wait(0.5)

        self.play(banner.update_text("Cycle 2: Slave asserts ARREADY=1. AR Handshake completes.", theme, COLOR_CTRL))
        self.play(slave.animate.set_stroke(COLOR_CTRL))
        self.play(ar_bwd.animate.set_color(COLOR_ACTIVE))
        self.play(master.animate.set_stroke(COLOR_CTRL))
        self.wait(0.5)

        self.play(banner.update_text("Cycle 3: Internal memory read latency. ARVALID deasserted.", theme, COLOR_INACTIVE))
        self.play(
            master.animate.set_stroke(COLOR_INACTIVE),
            slave.animate.set_stroke(COLOR_ACTIVE),
            ar_fwd.animate.set_color(COLOR_CTRL),
            ar_bwd.animate.set_color(COLOR_CTRL)
        )
        self.wait(0.6)

        self.play(banner.update_text("Cycle 4: Slave drives RDATA=0xCAFE, RVALID=1, RLAST=1", theme, COLOR_DATA))
        self.play(slave.animate.set_stroke(COLOR_DATA))
        self.play(r_fwd.animate.set_color(COLOR_ACTIVE))
        self.play(master.animate.set_stroke(COLOR_ACTIVE))
        self.wait(0.5)

        self.play(banner.update_text("Cycle 5: Master asserts RREADY=1. Read Data Handshake completes!", theme, COLOR_CTRL))
        self.play(master.animate.set_stroke(COLOR_CTRL))
        self.play(r_bwd.animate.set_color(COLOR_ACTIVE))
        self.play(
            master.animate.set_stroke(COLOR_DATA),
            slave.animate.set_stroke(COLOR_DATA)
        )
        self.wait(0.5)

        self.play(banner.update_text("Transaction Complete: Read data 0xCAFE received successfully.", theme, COLOR_CTRL))
        self.wait(1.5)
