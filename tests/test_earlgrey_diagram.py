"""The same whole-diagram engine on a second chip (Earlgrey), plus the rules the second chip exposed:
wires must not run over blocks, and two blocks may legitimately carry the same printed name."""
import os
import sys

import pytest
from manim import Scene

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))
from spec_validator import validate  # noqa: E402

from ipmotion import conformance, fidelity  # noqa: E402
from ipmotion.diagram import Diagram, load  # noqa: E402
from ipmotion.fullspec import load_story, make_full_spec  # noqa: E402
from ipmotion.lint.harness import lint_script  # noqa: E402
from ipmotion.lint.worker import run_scene  # noqa: E402

STORY = "bench/stories/earlgrey_ibex_uart_read.yaml"
SPEC = make_full_spec(load_story(STORY))
TRUTH, LAYOUT = load("opentitan_earlgrey")
BOTH = ["opentitan_darjeeling", "opentitan_earlgrey"]
CHIPS = BOTH + ["opentitan_peppermint"]        # the swatch test needs a chip that has swatches; the rest do not


def test_earlgrey_spec_is_the_whole_diagram_and_validates():
    assert len(SPEC["blocks"]) == len(TRUTH["blocks"]) == 40
    assert len(SPEC["connections"]) == len(TRUTH["connections"]) == 40
    assert {d["id"] for d in SPEC["domains"]} == {"chip", "top", "pd_main", "pd_aon"}
    assert validate(SPEC) == []


def test_every_block_and_region_of_the_truth_file_has_a_box():
    for b in TRUTH["blocks"]:
        assert b["id"] in LAYOUT["blocks"], b["id"]
    for r in TRUTH["regions"]:
        assert r["id"] in LAYOUT["regions"], r["id"]


@pytest.mark.parametrize("name", CHIPS)
def test_no_wire_is_drawn_over_a_block_it_does_not_belong_to(name):
    d = Diagram(name, panel=False)
    bad = []
    for c in d.truth["connections"]:
        ends = {str(c["from"]).split(".")[0], str(c["to"]).split(".")[0]}
        obstacles = d._obstacles(ends)
        for pts in d._route(c):
            for a, b in zip(pts, pts[1:]):
                if any(Diagram._crosses(a, b, o, 2.0) for o in obstacles):
                    bad.append(c["id"])
    assert bad == []


@pytest.mark.parametrize("name", BOTH)
def test_no_block_title_runs_into_its_legend_swatches(name):
    d = Diagram(name, panel=False)
    marked = [bid for bid, blk in d.blocks.items()
              if any(getattr(m, "is_marker", False) for m in blk.submobjects)]
    assert marked, "this reference has blocks with legend swatches"
    for bid in marked:                       # running the clearance pass again must find nothing left to fix
        blk = d.blocks[bid]
        before = blk.txt.font_size
        Diagram._clear_markers(blk)
        assert blk.txt.font_size == pytest.approx(before), bid


@pytest.mark.parametrize("name", CHIPS)
def test_the_drawing_stays_inside_the_frame_and_clear_of_the_panel(name):
    from manim import config
    d = Diagram(name)
    half_w, half_h = config.frame_width / 2, config.frame_height / 2
    for part in list(d.blocks.values()) + list(d.regions.values()) + list(d.labels.values()):
        assert part.get_left()[0] > -half_w and part.get_right()[0] < half_w, part
        assert part.get_bottom()[1] > -half_h and part.get_top()[1] < half_h, part
        assert part.get_right()[0] < d._panel_x0 + 1e-6, part


def test_two_blocks_may_share_a_printed_name_and_are_still_told_apart():
    """Earlgrey prints 'Pinmux', 'Clk/Rst Managers' and 'Analog Sensor Top' once per power domain, and Manim's
    Text.text drops spaces, so 'TL-UL Crossbar' and 'TL-UL Cross bar' read the same as well."""
    d = Diagram("opentitan_earlgrey", panel=False)
    assert d.blocks["pinmux_main"].txt.text == d.blocks["pinmux_aon"].txt.text
    res = run_scene(WholeEarlgrey)
    boxes, issues, _ = conformance.locate_blocks(res["snapshots"], SPEC, LAYOUT)
    assert issues == []
    for a, b in (("pinmux_main", "pinmux_aon"), ("clk_rst_managers_main", "clk_rst_managers_aon"),
                 ("analog_sensor_top_main", "analog_sensor_top_aon"), ("tlul_crossbar", "peri_tlul_crossbar")):
        assert boxes[a] != boxes[b], (a, b)
        assert boxes[a][0] < boxes[b][0], (a, b)        # the _main one is the left one in both references
    # without the reference positions the names cannot be separated: everything falls back to one box
    blind, _, _ = conformance.locate_blocks(res["snapshots"], SPEC, None)
    assert blind["pinmux_main"] == blind["pinmux_aon"]


class WholeEarlgrey(Scene):
    def construct(self):
        self.add(Diagram("opentitan_earlgrey"))
        self.wait(0.1)


def test_earlgrey_score_is_perfect():
    f = fidelity.score(run_scene(WholeEarlgrey), SPEC, LAYOUT)
    assert f["blocks_ok"] == f["blocks_total"] == 40
    assert f["regions_ok"] == f["regions_total"] == 4
    assert f["wires_ok"] == f["wires_total"] and f["extras"] == 0
    assert f["layout_percent"] == 100.0


def test_earlgrey_story_scene_has_no_errors_from_either_check():
    rep = lint_script(os.path.join(ROOT, "bench", "scenes", "earlgrey_ibex_uart_read.py"), spec=SPEC, layout=LAYOUT)
    assert not [i for i in rep["issues"] if i["check"] == "runtime_error"]
    assert rep["summary"]["error"] == 0, [i["detail"] for i in rep["issues"] if i["severity"] == "error"]
    assert [c for c in rep["conformance"] if c["check"] != "conformance_static"] == []
