"""Rules the website's prompt has to keep, checked cheaply (no model calls, no rendering).

The measurement in bench/run_web.py is only meaningful while two things hold: the harness sends exactly what
the browser sends, and Peppermint -- the held-out exam -- never appears in the context. Both are easy to break
by editing one file and forgetting the other, and neither failure is visible by eye.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTX_DIR = os.path.join(ROOT, "web", "rag_context")


def _ctx_list(path, pattern):
    src = open(os.path.join(ROOT, path), encoding="utf-8").read()
    m = re.search(pattern, src, re.M)
    assert m, f"could not find the context list in {path}"
    return re.findall(r'"([^"]+)"', m.group(1))


def test_the_harness_sends_exactly_what_the_browser_sends():
    """If these drift, bench/run_web.py stops measuring the product and nobody notices."""
    browser = _ctx_list("web/app.js", r"const CTX = \[(.*?)\]")
    harness = _ctx_list("bench/run_web.py", r"^CTX = \[(.*?)\]")
    assert browser == harness, f"web/app.js sends {browser}, bench/run_web.py sends {harness}"


def test_every_context_file_the_prompt_lists_exists():
    for name in _ctx_list("web/app.js", r"const CTX = \[(.*?)\]"):
        assert os.path.exists(os.path.join(CTX_DIR, f"{name}.txt")), name


def test_peppermint_never_reaches_the_prompt():
    """Peppermint is the held-out exam (CLAUDE.md). The moment it is in the context, every score against it is
    worthless, so this is checked rather than remembered."""
    for f in os.listdir(CTX_DIR):
        body = open(os.path.join(CTX_DIR, f), encoding="utf-8").read().lower()
        assert "peppermint" not in body, f"{f} mentions Peppermint"
        for held_out in ("retention sram", "aon tl-ul"):
            assert held_out not in body, f"{f} leaks held-out content: {held_out!r}"


def test_the_worked_examples_teach_regions_and_absolute_positions():
    """The two habits the measurement showed were missing. A worked example that lost them would quietly undo
    the gain, so assert they are actually in there."""
    for name in ("25_example_earlgrey", "26_example_darjeeling"):
        body = open(os.path.join(CTX_DIR, f"{name}.txt"), encoding="utf-8").read()
        assert body.count("DomainGroup(") >= 3, f"{name}: too few regions to teach from"
        assert body.count("move_to([") >= 30, f"{name}: should place blocks absolutely"
        code = [l for l in body.splitlines() if not l.lstrip().startswith("#")]
        assert not any(".arrange(" in l for l in code), f"{name}: must not teach arrange() on a big diagram"


def test_the_rules_tell_the_model_to_draw_domains_and_keep_exact_names():
    rules = open(os.path.join(CTX_DIR, "00_rules.txt"), encoding="utf-8").read()
    assert "DomainGroup" in rules
    assert "paraphrase" in rules.lower()
