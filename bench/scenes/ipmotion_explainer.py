"""The product explaining itself: how a visitor gets from a block diagram to an .mp4 on their own machine.

Hand-written against ipmotion_lib, the same library the generator writes against, and checked by the same
linter that checks generated scripts:

    python -m ipmotion.lint bench/scenes/ipmotion_explainer.py IPMotionExplainer
    python -m manim render -ql bench/scenes/ipmotion_explainer.py IPMotionExplainer
"""
from manim import DOWN, LEFT, RIGHT, UP, Arrow, Scene, VGroup

from ipmotion_lib import Banner, IPBlock, Packet, Theme, ui_text

ACTIVE = "#FFD700"
FLOW = "#00FFF0"
DONE = "#34D399"
STEP_Y = 0.75
BOX_W, BOX_H = 2.25, 1.15


class IPMotionExplainer(Scene):
    def construct(self):
        theme = Theme()

        banner = Banner("IPMotion: from a block diagram to an animation", theme)
        banner.move_to([0, 3.45, 0])
        self.add(banner)

        names = [
            "Your diagram\n+ your story",
            "IPMotion\nwebsite",
            "Your LLM\n(your key)",
            "script.py",
            "manim\non your PC",
        ]
        xs = [-5.45, -2.75, 0.0, 2.75, 5.45]
        blocks = []
        for name, x in zip(names, xs):
            b = IPBlock(name, theme, width=BOX_W, height=BOX_H, line_spacing=0.3)
            b.move_to([x, STEP_Y, 0])
            blocks.append(b)
            self.add(b)

        arrows = []
        for a, b in zip(blocks, blocks[1:]):
            ar = Arrow(a.get_right(), b.get_left(), buff=0.06, color="#9CA3AF",
                       stroke_width=4, max_tip_length_to_length_ratio=0.22)
            arrows.append(ar)
            self.add(ar)

        out = IPBlock("your-animation.mp4", theme, width=3.1, height=0.95)
        out.move_to([5.25, -1.75, 0])
        self.add(out)
        down = Arrow(blocks[-1].get_bottom(), out.get_top(), buff=0.06, color="#9CA3AF",
                     stroke_width=4, max_tip_length_to_length_ratio=0.3)
        self.add(down)

        cmd = ui_text("manim -pql script.py YourSceneName", 20, theme.text)
        cmd.move_to([-1.5, -1.75, 0])
        note = ui_text("Runs on your machine. We host nothing and store nothing.", 16, theme.muted)
        note.move_to([-1.5, -2.6, 0])

        caption = ui_text("Step 1 of 6", 24, theme.active)
        caption.move_to([0, -3.4, 0])
        self.add(caption)

        steps = [
            ("You bring a block diagram and a short story", 0),
            ("Paste them into the IPMotion website", 0),
            ("Your own API key, kept in your browser", 1),
            ("The model writes one complete Manim script", 2),
            ("Download the script", 3),
            ("Run one command on your own machine", 4),
        ]
        self.wait(0.6)
        for n, (text, lit) in enumerate(steps, 1):
            new_cap = ui_text(f"Step {n} of 6: {text}", 24, theme.active)
            new_cap.move_to([0, -3.4, 0])
            self.play(banner.update_text(text, theme, ACTIVE), run_time=0.5)
            caption.become(new_cap)
            self.play(blocks[lit].bg.animate.set_color(ACTIVE), run_time=0.4)
            if lit < len(arrows):
                self.play(arrows[lit].animate.set_color(FLOW), run_time=0.3)
                pkt = Packet("your work", FLOW, theme, width=1.05, height=0.3, font_size=13)
                pkt.move_to(blocks[lit].get_right() + RIGHT * 0.1 + UP * 0.0)
                self.play(pkt.animate.move_to(blocks[lit + 1].get_left() + LEFT * 0.1), run_time=0.55)
                self.remove(pkt)
            self.play(blocks[lit].bg.animate.set_color(DONE), run_time=0.3)
            self.wait(0.35)

        self.play(banner.update_text("One command, and the .mp4 is yours", theme, DONE), run_time=0.5)
        self.add(cmd, note)
        self.play(down.animate.set_color(DONE), out.bg.animate.set_color(DONE), run_time=0.6)
        final = ui_text("Bring your own key. Nothing is uploaded, nothing is stored.", 24, DONE)
        final.move_to([0, -3.4, 0])
        caption.become(final)
        self.wait(2.0)
