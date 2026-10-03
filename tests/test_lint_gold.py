"""Lint the real gold examples and the broken AXI fixtures through the subprocess harness."""
import os

import pytest

from ipmotion.lint.harness import lint_script

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = os.path.join(ROOT, "gold_examples")
BROKEN = os.path.join(ROOT, "tests", "fixtures", "broken")

_cache: dict[str, dict] = {}


def lint_file(path):
    if path not in _cache:
        _cache[path] = lint_script(path, timeout=120)
    return _cache[path]


def error_checks(rep):
    return {i["check"] for i in rep["issues"] if i["severity"] == "error"}


# ---------------------------------------------------------------- baseline
def test_axi_is_a_zero_error_baseline():
    rep = lint_file(os.path.join(GOLD, "axi_read_handshake.py"))
    errors = [i["detail"] for i in rep["issues"] if i["severity"] == "error"]
    assert errors == []
    assert rep["ok"]
    # known, accepted warnings: edge-hugging blocks and a full-bleed banner
    assert {i["check"] for i in rep["issues"]} <= {"out_of_frame"}


# ---------------------------------------------------------- broken fixtures
# fixture -> (intended check, error-level checks that are legitimate consequences)
FIXTURES = {
    "axi_label_overlap": ("text_overlap", set()),
    "axi_dangling_wire": ("dangling_endpoint", set()),
    "axi_off_frame": ("out_of_frame", set()),
    "axi_tiny_text": ("min_text_size", set()),
    "axi_block_overlap": ("min_spacing", {"text_overlap", "text_occluded"}),
    "axi_banner_occluded": ("text_occluded", {"text_overlap", "out_of_frame"}),   # legacy banner leaves a stray block
}


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_broken_fixture_is_caught_by_its_check(name):
    intended, consequences = FIXTURES[name]
    rep = lint_file(os.path.join(BROKEN, f"{name}.py"))
    errs = error_checks(rep)
    assert intended in errs, f"{name}: expected {intended}, got {errs}"
    assert errs <= {intended} | consequences, f"{name}: unexpected extra errors {errs - {intended} - consequences}"


def test_dangling_fixture_points_at_the_right_arrow():
    rep = lint_file(os.path.join(BROKEN, "axi_dangling_wire.py"))
    d = [i for i in rep["issues"] if i["check"] == "dangling_endpoint"]
    assert len(d) == 1 and "ar_fwd" in d[0]["detail"] and "end of" in d[0]["detail"]
    assert d[0]["first_t"] == 1.0 and d[0]["source_line"] > 0


# ----------------------------------------------------- known-bad gold files
def test_symbol_showcase_reports_offframe_banner_and_tiny_labels():
    rep = lint_file(os.path.join(GOLD, "symbol_showcase.py"))
    oof = [i for i in rep["issues"] if i["check"] == "out_of_frame" and i["severity"] == "error"]
    assert any("entirely outside" in i["detail"] and "IPMotionV5SymbolLibraryShowcase" in i["detail"] for i in oof)
    tiny = [i for i in rep["issues"] if i["check"] == "min_text_size" and i["severity"] == "error"]
    assert len(tiny) >= 20


def test_darjeeling_full_reports_block_overlap_and_occlusion():
    rep = lint_file(os.path.join(GOLD, "darjeeling_full.py"))
    errs = [i for i in rep["issues"] if i["severity"] == "error"]
    assert any(i["check"] == "min_spacing" and "overlap" in i["detail"] for i in errs)
    occ = [i for i in errs if i["check"] == "text_occluded"]
    named = " ".join(i["detail"] for i in occ)
    assert "CSRNG" in named and "DebugModule" in named           # Low-Speed blocks cover Hi-Speed ones


@pytest.mark.parametrize("name", ["axi_read_handshake", "symbol_showcase", "darjeeling_full"])
def test_previously_rendering_gold_examples_still_run(name):
    rep = lint_file(os.path.join(GOLD, f"{name}.py"))
    assert not [i for i in rep["issues"] if i["check"] == "runtime_error"]
