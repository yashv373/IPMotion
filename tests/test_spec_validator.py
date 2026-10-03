import copy
import glob
import os
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))
from spec_validator import validate  # noqa: E402

SPECS = sorted(glob.glob(os.path.join(ROOT, "bench", "specs", "*.yaml")))


def load(name):
    with open(os.path.join(ROOT, "bench", "specs", name), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.mark.parametrize("path", SPECS)
def test_committed_specs_are_valid(path):
    with open(path, encoding="utf-8") as fh:
        assert validate(yaml.safe_load(fh)) == []


def mutated(fn):
    s = copy.deepcopy(load("darjeeling_periph_read.yaml"))
    fn(s)
    return validate(s)


def test_unclear_block_rejected():
    errs = mutated(lambda s: s["blocks"].append({"id": "soc_proxy", "label": "SoC Proxy", "role": "logic"}))
    assert any("marked unclear" in e for e in errs)


def test_unclear_connection_rejected():
    def add(s):
        s["blocks"] += [{"id": "jtag_mailbox", "label": "JTAG Mailbox", "role": "peripheral"},
                        {"id": "debug_module", "label": "Debug Module", "role": "peripheral"}]
        s["connections"].append({"id": "x", "truth": "c14", "from": "jtag_mailbox", "to": "debug_module", "bus": "tl_ul"})
    assert any("c14 which is marked unclear" in e for e in mutated(add))


def test_label_must_match_truth_exactly():
    assert any("!= truth label" in e for e in mutated(lambda s: s["blocks"][0].update(label="Ibex Core")))


def test_block_not_in_truth_rejected():
    errs = mutated(lambda s: s["blocks"].append({"id": "made_up", "label": "Made Up", "role": "logic"}))
    assert any("not in truth file" in e for e in errs)


def test_invented_connection_and_direction_rejected():
    assert any("does not match truth" in e for e in mutated(
        lambda s: s["connections"].append({"id": "y", "truth": "c01", "from": "ibex_core", "to": "main_sram", "bus": "tl_ul"})))
    assert any("heads=to" in e for e in mutated(lambda s: s["connections"][0].update(direction="both")))
    assert any("needs `truth:" in e for e in mutated(lambda s: s["connections"][0].pop("truth")))


def test_domain_membership_must_match_truth_region():
    errs = mutated(lambda s: s["domains"][0]["contains"].append("uart_i2c"))
    assert any("truth region" in e for e in errs)


def test_generic_rules():
    s = load("axi_write.yaml")
    s["connections"][0]["bus"] = "wifi"
    s["sequence"][0]["activate"] = ["nope"]
    s["blocks"].append(dict(s["blocks"][0]))
    errs = validate(s)
    assert any("bus" in e for e in errs) and any("unknown connection" in e for e in errs) and any("duplicate block" in e for e in errs)
