"""Two library guarantees that stop a generated diagram looking broken, whatever the model writes.

Both faults were visible in the generator's own output on 2026-10-05: the AON crossbar's title shrunk to roughly
6pt and unreadable, and one block hanging outside its own power domain. Neither can be fixed by asking the model
nicely, so the library makes them impossible instead.
"""
import numpy as np

from ipmotion_lib import MIN_TITLE_FONT, DomainGroup, IPBlock, Theme, domain_around

TH = Theme()


def test_a_long_title_in_a_normal_block_still_shrinks_to_fit():
    b = IPBlock("Key Manager DPE", TH, width=2.0, height=0.6)
    assert b.txt.width <= 2.0


def test_a_title_never_shrinks_below_readable():
    # 23 characters in a 1.2-wide box: fitting it across would need roughly 4pt.
    b = IPBlock("Entropy Source, CSRNG, EDN", TH, width=1.2, height=0.5)
    assert b.txt.font_size >= MIN_TITLE_FONT - 1e-6


def test_a_tall_narrow_bar_writes_its_title_along_the_bar():
    b = IPBlock("AON TL-UL Cross bar", TH, width=0.4, height=5.0)
    assert b.txt.height > b.txt.width, "a bus bar's title should run vertically"
    assert b.txt.font_size >= MIN_TITLE_FONT - 1e-6
    assert b.txt.height <= 5.0


def test_a_short_title_in_a_tall_bar_is_left_alone():
    b = IPBlock("AON", TH, width=1.0, height=3.0)
    assert b.txt.width > b.txt.height
    assert b.txt.font_size == 16


def test_domain_around_contains_every_block_it_was_given():
    blocks = [IPBlock("A", TH, width=1.2, height=0.6).move_to([-2, 1.5, 0]),
              IPBlock("B", TH, width=1.2, height=0.6).move_to([2, -1.5, 0]),
              IPBlock("C", TH, width=2.0, height=0.6).move_to([0, 0, 0])]
    d = domain_around("Main power and clock domain", blocks, "#0F172A")
    assert isinstance(d, DomainGroup)
    lo, hi = d.bg.get_corner([-1, -1, 0]), d.bg.get_corner([1, 1, 0])
    for b in blocks:
        bl, br = b.get_corner([-1, -1, 0]), b.get_corner([1, 1, 0])
        assert lo[0] <= bl[0] and lo[1] <= bl[1], f"{b.title} escapes bottom-left"
        assert hi[0] >= br[0] and hi[1] >= br[1], f"{b.title} escapes top-right"


def test_domain_around_leaves_the_padding_it_was_asked_for():
    b = IPBlock("A", TH, width=1.0, height=1.0)
    d = domain_around("R", [b], "#0F172A", pad=0.5)
    assert np.isclose(d.bg.width, 2.0, atol=0.01)
    assert np.isclose(d.bg.height, 2.0, atol=0.01)


def test_a_long_title_is_wrapped_before_it_is_shrunk():
    # manim's Text.text drops the whitespace, so the wrap is checked by what it buys: the title sits inside the
    # box AND keeps a readable size, which a single line of this length in 1.8 units cannot do.
    wide = IPBlock("Mailboxes (inbound & outbound)", TH, width=1.8, height=0.7)
    assert wide.txt.width <= 1.6 + 1e-6, "the title must sit inside the box"
    assert wide.txt.font_size > 12, "and must not have been shrunk to get there"


def test_a_one_word_title_too_wide_is_still_handled():
    b = IPBlock("Supercalifragilistic", TH, width=0.9, height=0.6)
    assert b.txt.font_size >= MIN_TITLE_FONT - 1e-6     # nothing to wrap on, so the floor is what protects it
