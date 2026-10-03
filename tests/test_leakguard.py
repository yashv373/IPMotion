import os

import pytest

from ipmotion.leakguard import LeakError, assert_no_truth_leak, find_leaks, is_denied, truth_labels

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_denied_paths():
    for rel in ("bench/truth/opentitan_darjeeling.yaml", "opentitan_archs/peppermint.png",
                "openPulp_arch/pulp_story.png", "bench\\truth\\x.yaml"):
        assert is_denied(os.path.join(ROOT, rel)), rel
    for rel in ("gold_examples/axi_read_handshake.py", "ipmotion_lib.py", "bench/specs/axi_write.yaml"):
        assert not is_denied(os.path.join(ROOT, rel)), rel


def test_truth_labels_are_loaded_and_distinctive():
    labels = truth_labels()
    assert "main tl-ul crossbar" in labels and "padring" in labels
    assert all(len(l) >= 6 for l in labels)


def test_context_with_truth_content_is_rejected():
    leaky = "blocks: Main TL-UL Crossbar, Peri TL-UL Cross bar, Life Cycle Controller"
    assert find_leaks(leaky)
    with pytest.raises(LeakError):
        assert_no_truth_leak(["harmless", leaky], where="test")
    with pytest.raises(LeakError):
        assert_no_truth_leak([{"text": "x", "metadata": {"source": "bench/truth/opentitan_darjeeling.yaml"}}])
    with pytest.raises(LeakError):
        assert_no_truth_leak(["see opentitan_archs/top_darjeeling_block_diagram.png"])


def test_normal_library_and_gold_context_passes():
    lib = open(os.path.join(ROOT, "ipmotion_lib.py"), encoding="utf-8").read()
    axi = open(os.path.join(ROOT, "gold_examples", "axi_read_handshake.py"), encoding="utf-8").read()
    assert_no_truth_leak([lib, axi, "class IPBlock(VGroup): ..."], where="test")


def test_indexer_input_chunks_are_clean():
    import indexer
    chunks = indexer.chunk_library(indexer.LIB_PATH) + indexer.chunk_example_scripts() + indexer.chunk_manim_api_basics()
    assert_no_truth_leak(chunks, where="indexer chunks")
    assert not any(indexer.is_denied(c["metadata"].get("source", "")) for c in chunks)
