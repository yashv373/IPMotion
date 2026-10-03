"""Spec conformance: a good script passes; each kind of departure from the spec is caught."""
import os

import pytest
import yaml

from ipmotion import conformance
from ipmotion.lint.harness import lint_script

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = yaml.safe_load(open(os.path.join(ROOT, "bench", "specs", "axi_write.yaml"), encoding="utf-8"))

BODY = '''
from manim import *
from ipmotion_lib import *


class AxiWriteScene(Scene):
    def construct(self):
        theme = Theme()
        banner = Banner(BANNERS[0], theme).move_to([0, 3.4, 0])
        master = IPBlock(LABELS["master"], theme, width=2.6, height=1.6)
        slave = IPBlock(LABELS["slave"], theme, width=2.6, height=1.6)
        VGroup(master, slave).arrange(RIGHT, buff=4.5).move_to([0, -0.3, 0])
        aw = Arrow(master.get_right() + UP * 0.8, slave.get_left() + UP * 0.8, buff=0.1, color=GREEN)
        w = Arrow(master.get_right(), slave.get_left(), buff=0.1, color=BLUE)
        b = Arrow(slave.get_left() + DOWN * 0.8, master.get_right() + DOWN * 0.8, buff=0.1, color=BLUE)
        l_aw = Text(LABELS["conn_aw"], font="Consolas", font_size=16).next_to(aw, UP, buff=0.1)
        l_w = Text(LABELS["conn_w"], font="Consolas", font_size=16).next_to(w, UP, buff=0.05)
        l_b = Text(LABELS["conn_b"], font="Consolas", font_size=16).next_to(b, DOWN, buff=0.1)
        self.play(FadeIn(VGroup(banner, master, slave, aw, w, b, l_aw, l_w, l_b)))
        for i in range(6):
            self.play(banner.update_text(BANNERS[i], theme))
            if i in (0, 2, 4):
                key = {0: "packet_1_0", 2: "packet_3_0", 4: "packet_5_0"}[i]
                pkt = Packet(LABELS[key], YELLOW, theme).move_to(DOWN * 2.6)
                self.play(FadeIn(pkt))
                self.play(FadeOut(pkt))
        self.wait(0.5)
'''


def build(tmp_path, body=BODY, name="s.py"):
    path = tmp_path / name
    path.write_text(conformance.preamble(SPEC) + "\n" + body, encoding="utf-8")
    return str(path)


def run(tmp_path, body=BODY, replace=None):
    for old, new in (replace or []):
        assert old in body, old
        body = body.replace(old, new)
    p = build(tmp_path, body)
    rep = lint_script(p, spec=SPEC)
    return rep, [(i["check"], i["detail"]) for i in rep["conformance"]]


def kinds(issues):
    return {c for c, _ in issues}


def test_good_script_conforms(tmp_path):
    rep, issues = run(tmp_path)
    assert issues == [] and rep["conformance_ok"]
    assert not [i for i in rep["issues"] if i["check"] == "runtime_error"]


def test_hand_typed_label_is_rejected(tmp_path):
    _, issues = run(tmp_path, replace=[('IPBlock(LABELS["master"]', 'IPBlock("AXI Master"')])
    assert any(c == "conformance_static" and "hand-typed" in d and "LABELS['master']" in d for c, d in issues)


def test_hand_typed_banner_is_rejected(tmp_path):
    _, issues = run(tmp_path, replace=[("Banner(BANNERS[0], theme)", 'Banner("Cycle 1: Master asserts AWVALID with AWADDR=0x1000", theme)')])
    assert any("hand-typed" in d and "BANNERS[0]" in d for _, d in issues)


def test_label_with_a_line_break_is_still_hand_typed(tmp_path):
    _, issues = run(tmp_path, replace=[('IPBlock(LABELS["slave"]', 'IPBlock("AXI\\nSlave"')])
    assert any("hand-typed" in d for _, d in issues)


def test_lint_ignore_is_rejected(tmp_path):
    _, issues = run(tmp_path, replace=[("        self.wait(0.5)\n", '        master.lint_ignore = ["text_overlap"]\n        self.wait(0.5)\n')])
    assert any("lint_ignore is not allowed" in d for _, d in issues)


def test_changed_labels_block_is_rejected(tmp_path):
    p = tmp_path / "s.py"
    text = conformance.preamble(SPEC).replace("'AXI Slave'", "'AXI Peripheral'") + "\n" + BODY
    p.write_text(text, encoding="utf-8")
    issues = lint_script(str(p), spec=SPEC)["conformance"]
    assert any("LABELS was changed" in i["detail"] for i in issues)


def test_missing_labels_block_is_rejected(tmp_path):
    p = tmp_path / "s.py"
    p.write_text(BODY.replace("LABELS[", "{}.get(").replace("BANNERS[", "[].__getitem__(") if False else "from manim import *\nclass S(Scene):\n    def construct(self):\n        self.add(Text('x'))\n", encoding="utf-8")
    issues = lint_script(str(p), spec=SPEC)["conformance"]
    assert any("LABELS is missing" in i["detail"] for i in issues) and any("BANNERS is missing" in i["detail"] for i in issues)


def test_missing_connection_is_reported(tmp_path):
    _, issues = run(tmp_path, replace=[("VGroup(banner, master, slave, aw, w, b, l_aw, l_w, l_b)", "VGroup(banner, master, slave, aw, w, l_aw, l_w, l_b)")])
    assert any(c == "conformance_connection" and "'b'" in d and "no wire" in d for c, d in issues)


def test_wrong_arrow_direction_is_reported(tmp_path):
    _, issues = run(tmp_path, replace=[("b = Arrow(slave.get_left() + DOWN * 0.8, master.get_right() + DOWN * 0.8,", "b = Arrow(master.get_right() + DOWN * 0.8, slave.get_left() + DOWN * 0.8,")])
    assert any(c == "conformance_connection" and "wrong arrowheads" in d for c, d in issues)


def test_missing_banner_step_is_reported(tmp_path):
    _, issues = run(tmp_path, replace=[("for i in range(6):", "for i in range(5):")])
    assert any(c == "conformance_banner" and "step 6" in d for c, d in issues)


def test_extra_block_is_reported(tmp_path):
    _, issues = run(tmp_path, replace=[("        self.wait(0.5)\n", '        extra = IPBlock("DMA", theme, width=2, height=1).move_to(UP * 2.2)\n        self.add(extra)\n        self.wait(0.5)\n')])
    assert any(c == "conformance_extra" and "not in the spec" in d for c, d in issues)


def test_missing_packet_text_is_reported(tmp_path):
    _, issues = run(tmp_path, replace=[("if i in (0, 2, 4):", "if i in (0, 2):")])
    assert any(c == "conformance_sequence" and "BRESP=OKAY" in d for c, d in issues)


def test_domain_membership_is_checked(tmp_path):
    spec = dict(SPEC, domains=[{"id": "d", "label": "Domain D", "contains": ["master"]}])
    body = BODY.replace("        self.wait(0.5)\n", '        dom = RoundedRectangle(width=4, height=3, corner_radius=0.1, stroke_width=1, fill_opacity=0).move_to(master.get_center())\n        lab = Text(LABELS["domain_d"], font="Consolas", font_size=14).move_to(dom.get_top() + DOWN * 0.2)\n        self.add(dom, lab)\n        self.wait(0.5)\n')
    p = tmp_path / "d.py"
    p.write_text(conformance.preamble(spec) + "\n" + body, encoding="utf-8")
    ok = lint_script(str(p), spec=spec)["conformance"]
    assert not any(i["check"] == "conformance_domain" for i in ok)
    bad_body = body.replace("move_to(master.get_center())", "move_to(UP * 3 + LEFT * 5)")
    p.write_text(conformance.preamble(spec) + "\n" + bad_body, encoding="utf-8")
    bad = lint_script(str(p), spec=spec)["conformance"]
    assert any(i["check"] == "conformance_domain" and "does not fully contain" in i["detail"] for i in bad)


def test_preamble_covers_blocks_domains_connections_banners_packets_and_state():
    spec = yaml.safe_load(open(os.path.join(ROOT, "bench", "specs", "fifo_backpressure.yaml"), encoding="utf-8"))
    labels, banners = conformance.labels_and_banners(spec)
    assert labels["fifo"] == "FIFO (depth 4)" and labels["conn_full"] == "FULL (backpressure)"
    assert labels["state_3_0"] == "A B C D" and labels["packet_2_0"] == "B"
    assert len(banners) == len(spec["sequence"])
    assert ast_ok(conformance.preamble(spec))


def ast_ok(src):
    import ast
    ast.parse(src)
    return True
