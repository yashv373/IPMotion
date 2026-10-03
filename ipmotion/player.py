"""Play a story on a drawn reference diagram, deterministically (no AI in the loop).

    class DarjeelingStory(FullDiagramScene):
        STORY = "bench/stories/darjeeling_ibex_uart_read.yaml"

Each story step: reset the look, show the step text in the right-hand panel, light up the blocks/wires it names,
then move the labelled packets along the wires. A packet with kind: response is orange and travels the wire
backwards, so a response going against a one-way arrow does not look like a wrong arrow.
"""
from __future__ import annotations

import numpy as np
from manim import FadeIn, FadeOut, Scene

from ipmotion.diagram import Diagram
from ipmotion.fullspec import load_story, make_full_spec
from ipmotion_lib import Packet, Theme

YELLOW = "#FFD700"
REQUEST = "#00FFF0"
RESPONSE = "#FF7A00"


class FullDiagramScene(Scene):
    STORY: str = ""

    def construct(self):
        spec = make_full_spec(load_story(self.STORY))
        theme = Theme()
        d = Diagram(spec["source"], theme, title=spec["title"])
        self.diagram, self.spec = d, spec
        self.add(d)
        self.wait(0.5)
        for step in spec["sequence"]:
            self.play_step(d, step, theme)

    def play_step(self, d, step, theme):
        d.reset_now()
        anims = [d.panel.update_text(step["banner"])]
        anims += [d.blocks[b].bg.animate.set_color(YELLOW) for b in step.get("highlight", [])]
        anims += [d.conns[c].animate.set_color(YELLOW) for c in step.get("activate", [])]
        self.play(*anims, run_time=0.6)
        for pk in step.get("packets", []):
            self.run_packet(d, pk, theme)
        self.wait(step.get("hold", 0.5))

    def run_packet(self, d, pk, theme):
        response = pk.get("kind", "request") == "response"
        pts = list(d.conn_pts[pk["conn"]][0])
        if response:
            pts.reverse()
        pkt = Packet(pk["label"], RESPONSE if response else REQUEST, theme, width=0.62, height=0.2, font_size=9)
        pkt.move_to(pts[0])
        self.play(FadeIn(pkt, run_time=0.15))
        for p in pts[1:]:
            self.play(pkt.animate.move_to(p), run_time=max(0.35, float(np.linalg.norm(p - pkt.get_center())) * 0.5))
        self.play(FadeOut(pkt, run_time=0.15))
