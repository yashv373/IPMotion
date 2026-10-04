"""The whole-diagram engine on a third chip (Peppermint), plus the three rules it exposed: a picture may have
no legend at all, may draw a box it never labels, and may print its free labels along the bottom and right
edges instead of only down the left."""
import os
import sys

import pytest
from manim import Scene

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))
from spec_validator import validate  # noqa: E402

from ipmotion import conformance, fidelity  # noqa: E402
from ipmotion.diagram import MARGIN_LABEL_MIN, Diagram, load  # noqa: E402
from ipmotion.fullspec import load_story, make_full_spec  # noqa: E402
from ipmotion.lint.harness import lint_script  # noqa: E402
from ipmotion.lint.worker import run_scene  # noqa: E402

STORY = "bench/stories/peppermint_ibex_retention_read.yaml"
SPEC = make_full_spec(load_story(STORY))
TRUTH, LAYOUT = load("opentitan_peppermint")
CHIPS = ["opentitan_darjeeling", "opentitan_earlgrey", "opentitan_peppermint"]


class WholePeppermint(Scene):
    """Drawn without the step panel: Peppermint's outer region is labelled with the diagram title, so a panel
    carrying the same title would give the checker two texts to choose from. The story scene gives the panel
    the story's own title, which is why it does not hit this."""
    def construct(self):
        self.add(Diagram("opentitan_peppermint", panel=False))
        self.wait(0.1)


def test_peppermint_spec_is_the_whole_diagram_and_validates():
    assert len(TRUTH["blocks"]) == 24 and len(TRUTH["externals"]) == 9
    assert len(SPEC["blocks"]) == 33                      # blocks + the nine edge labels
    assert len(SPEC["connections"]) == len(TRUTH["connections"]) == 34
    assert {d["id"] for d in SPEC["domains"]} == {"outer", "main", "aon"}
    assert validate(SPEC) == []


def test_every_block_region_and_edge_label_of_the_truth_file_has_a_box():
    for b in TRUTH["blocks"]:
        assert b["id"] in LAYOUT["blocks"], b["id"]
    for r in TRUTH["regions"]:
        assert r["id"] in LAYOUT["regions"], r["id"]
    for e in TRUTH["externals"]:
        assert e["id"] in LAYOUT["labels"], e["id"]


@pytest.mark.parametrize("name", CHIPS)
def test_the_step_panel_is_never_narrower_than_its_minimum(name):
    """The gutter the margin labels need depends on the scale and the scale on the gutter. Sizing the panel
    from one and placing it from the other left Peppermint's panel at 4.26 units and clipped its legend."""
    d = Diagram(name)
    assert d._panel_x1 - d._panel_x0 >= Diagram.MIN_PANEL_W - 1e-6


def test_edge_labels_are_told_apart_by_side_and_keep_darjeeling_in_its_gutter():
    """Peppermint prints free labels on three sides; Darjeeling's all sit in the left gutter, and its boxes
    overlap the drawing's own left edge, so the side test must default to left."""
    p = Diagram("opentitan_peppermint", panel=False)
    sides = {lid: p._label_side(box) for lid, box in p._label_boxes0.items()}
    assert sides["memory_bus_egress"] == sides["noise_source_bits"] == "left"
    assert sides["alerts_from_soc"] == sides["life_cycle_function_control"] == "right"
    assert sides["memory_bus_ingress"] == sides["outbound_message_irq"] == "bottom"
    d = Diagram("opentitan_darjeeling", panel=False)
    assert all(d._label_side(box) == "left" for box in d._label_boxes0.values())
    # ...and still get the full-size text the gutter was made for (d.labels also holds wire labels: only the
    # margin labels, the ones with a box, are meant here)
    assert all(round(d.labels[lid].font_size, 1) == 12.0 for lid in d._label_boxes0)


def test_no_edge_label_runs_into_another_one():
    d = Diagram("opentitan_peppermint", panel=False)
    ts = [d.labels[lid] for lid in d._label_boxes0]
    for i, a in enumerate(ts):
        for b in ts[i + 1:]:
            apart = (a.get_right()[0] < b.get_left()[0] or b.get_right()[0] < a.get_left()[0] or
                     a.get_bottom()[1] > b.get_top()[1] or b.get_bottom()[1] > a.get_top()[1])
            assert apart, (a.text, b.text)
    assert all(t.font_size >= MARGIN_LABEL_MIN - 1e-6 for t in ts)


def test_a_box_the_picture_never_labels_is_still_found_and_is_not_an_extra():
    """Peppermint's AON domain holds a small symbol with no text. It has to get a position anyway, or its two
    wires read as both missing and extra."""
    d = Diagram("opentitan_peppermint", panel=False)
    assert d.blocks["unlabeled_symbol"].txt not in d.blocks["unlabeled_symbol"].submobjects
    res = run_scene(WholePeppermint)
    boxes, issues, _ = conformance.locate_blocks(res["snapshots"], SPEC, LAYOUT)
    assert issues == []
    assert "unlabeled_symbol" in boxes
    assert not [i for i in conformance.check_dynamic(res, SPEC, LAYOUT) if i["check"] == "conformance_extra"]


def test_peppermint_score_is_perfect():
    f = fidelity.score(run_scene(WholePeppermint), SPEC, LAYOUT)
    assert f["blocks_ok"] == f["blocks_total"] == 33
    assert f["regions_ok"] == f["regions_total"] == 3
    assert f["wires_ok"] == f["wires_total"] and f["extras"] == 0
    assert f["layout_percent"] == 100.0


def test_peppermint_story_scene_has_no_errors_from_either_check():
    rep = lint_script(os.path.join(ROOT, "bench", "scenes", "peppermint_ibex_retention_read.py"),
                      spec=SPEC, layout=LAYOUT)
    assert not [i for i in rep["issues"] if i["check"] == "runtime_error"]
    assert rep["summary"]["error"] == 0, [i["detail"] for i in rep["issues"] if i["severity"] == "error"]
    assert [c for c in rep["conformance"] if c["check"] != "conformance_static"] == []
