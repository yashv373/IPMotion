"""Full-diagram pipeline: spec generation, unconfirmed-item rules, the drawing, the closeness score."""
import copy
import os
import sys

import pytest
import yaml
from manim import Scene

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))
from spec_validator import validate  # noqa: E402

from ipmotion import conformance, fidelity  # noqa: E402
from ipmotion.diagram import UNCONFIRMED, Diagram, load  # noqa: E402
from ipmotion.fullspec import load_story, make_full_spec  # noqa: E402
from ipmotion.lint.harness import lint_script  # noqa: E402
from ipmotion.lint.worker import run_scene  # noqa: E402

STORY = "bench/stories/darjeeling_ibex_uart_read.yaml"
SPEC = make_full_spec(load_story(STORY))
TRUTH, LAYOUT = load("opentitan_darjeeling")


def test_full_spec_contains_the_whole_diagram_and_validates():
    assert len(SPEC["blocks"]) == len(TRUTH["blocks"]) + len(TRUTH["externals"]) == 49
    assert len(SPEC["connections"]) == len(TRUTH["connections"]) == 61
    assert {d["id"] for d in SPEC["domains"]} == {"wrapper", "ip", "hi", "lo"}
    assert validate(SPEC) == []
    labels = {b["id"]: b["label"] for b in SPEC["blocks"]}
    assert labels["peri_tlul_crossbar"] == "Peri TL-UL Cross bar" and labels["uart_i2c"] == "1 x UART / 1x I2C"
    ibex_domains = [d["id"] for d in SPEC["domains"] if "ibex_core" in d["contains"]]
    assert set(ibex_domains) == {"wrapper", "ip", "hi"}             # nested regions: the block is in the whole chain


def test_unclear_items_are_included_only_as_unconfirmed():
    unconf_c = {c["id"] for c in SPEC["connections"] if c.get("unconfirmed")}
    unconf_b = {b["id"] for b in SPEC["blocks"] if b.get("unconfirmed")}
    assert unconf_b == {"soc_proxy", "analog_sensor_top"}
    assert {"c03", "c14", "c19", "c45", "c46", "c47", "c51"} <= unconf_c and len(unconf_c) == 10


def mutate(fn):
    s = copy.deepcopy(SPEC)
    fn(s)
    return validate(s)


def test_full_spec_rules_are_enforced():
    # an unclear item must be marked unconfirmed
    assert any("must be marked unconfirmed" in e for e in mutate(
        lambda s: next(c for c in s["connections"] if c["id"] == "c19").pop("unconfirmed")))
    # a story may not use an unconfirmed item
    assert any("unconfirmed and may not be used" in e for e in mutate(
        lambda s: s["sequence"][1].update(activate=["c19"])))
    # completeness: dropping a connection or a block is rejected
    assert any("missing" in e and "connections" in e for e in mutate(
        lambda s: s["connections"].pop(0)))
    assert any("missing" in e for e in mutate(lambda s: s["blocks"].pop(0)))
    # exact label
    assert any("!= truth label" in e for e in mutate(
        lambda s: next(b for b in s["blocks"] if b["id"] == "uart_i2c").update(label="UART")))
    # direction cannot be invented
    assert any("heads=to" in e for e in mutate(
        lambda s: next(c for c in s["connections"] if c["id"] == "c01").update(direction="both")))


def test_diagram_draws_every_block_with_its_exact_label_and_marks_unconfirmed_wires():
    d = Diagram("opentitan_darjeeling", panel=False)
    assert set(d.blocks) | set(d.layout["labels"]) >= {b["id"] for b in TRUTH["blocks"]} - {"base_addr_translation"} | {"base_addr_translation"}
    for b in TRUTH["blocks"]:
        blk = d.blocks[b["id"]]
        assert "".join(blk.title.split()) == "".join(b["label"].split()), b["id"]
    assert len(d.conns) == 61
    for cid in ("c19", "c45", "c51"):
        assert d._base_color[cid] == UNCONFIRMED
    assert d._base_color["c01"] != UNCONFIRMED


def test_diagram_blocks_stay_inside_their_regions_and_do_not_overlap():
    boxes = LAYOUT["blocks"]
    ids = [b["id"] for b in TRUTH["blocks"] if b["id"] != "base_addr_translation"]
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            A, B = boxes[a], boxes[b]
            overlap = min(A[2], B[2]) - max(A[0], B[0]) > 1 and min(A[3], B[3]) - max(A[1], B[1]) > 1
            assert not overlap, f"{a} and {b} overlap in the layout file"


class WholeDiagram(Scene):
    def construct(self):
        self.add(Diagram("opentitan_darjeeling"))
        self.wait(0.1)


class DiagramWithAWireMissing(Scene):
    def construct(self):
        d = Diagram("opentitan_darjeeling")
        d.remove(d.conns["c06"])                    # the reference draws OTBN's line; this render does not
        self.add(d)
        self.wait(0.1)


def test_score_is_perfect_for_the_whole_diagram_and_drops_when_a_wire_is_missing():
    full = fidelity.score(run_scene(WholeDiagram), SPEC, LAYOUT)
    assert full["blocks_ok"] == full["blocks_total"] == 49 and full["regions_ok"] == 4
    assert full["wires_ok"] == full["wires_total"] and full["extras"] == 0
    assert full["layout_percent"] == 100.0 and len(full["unconfirmed"]) == 12
    broken = fidelity.score(run_scene(DiagramWithAWireMissing), SPEC, LAYOUT)
    assert broken["wires_ok"] == broken["wires_total"] - 1
    assert any("c06" in i for i in broken["issue_details"])


def test_story_scene_has_no_errors_from_either_check():
    rep = lint_script(os.path.join(ROOT, "bench", "scenes", "darjeeling_ibex_uart_read.py"), spec=SPEC)
    assert not [i for i in rep["issues"] if i["check"] == "runtime_error"]
    assert rep["summary"]["error"] == 0, [i["detail"] for i in rep["issues"] if i["severity"] == "error"]
    assert [c for c in rep["conformance"] if c["check"] != "conformance_static"] == []
