"""The library's wire router: a wire must go AROUND blocks it does not belong to.

A straight line between two blocks runs over whatever sits between them, which was the most visible fault in
generated diagrams -- a wire hiding the name of a block it has nothing to do with. The engine solved this years
ago inside diagram.py, where a generated script can never reach it. These tests pin the library version.
"""
import pytest

from ipmotion_lib import IPBlock, Theme, _box_of, _hits, wire, wire_points

TH = Theme()


def block(x, y, w=1.2, h=0.6, label="B"):
    b = IPBlock(label, TH, width=w, height=h)
    b.move_to([x, y, 0])
    return b


def crosses(pts, box):
    return any(_hits(pts[i], pts[i + 1], box) for i in range(len(pts) - 1))


def test_a_straight_run_is_kept_when_nothing_is_in_the_way():
    a, b = block(-3, 0), block(3, 0)
    pts = wire_points(a, b, avoid=[a, b])
    assert len(pts) == 2, "two clear blocks should get the short route, not a detour"


def test_a_block_in_the_way_is_routed_around():
    a, mid, b = block(-4, 0), block(0, 0), block(4, 0)
    pts = wire_points(a, b, avoid=[a, mid, b])
    assert not crosses(pts, _box_of(mid, 0.1)), "the wire still runs through the middle block"
    assert len(pts) > 2, "going around needs more than a straight line"


def test_a_block_stacked_between_two_others_is_routed_around():
    a, mid, b = block(0, 3), block(0, 0), block(0, -3)
    pts = wire_points(a, b, avoid=[a, mid, b])
    assert not crosses(pts, _box_of(mid, 0.1))


def test_several_obstacles_are_all_avoided():
    a, b = block(-5.5, 0), block(5.5, 0)
    mids = [block(x, 0) for x in (-2, 0, 2)]
    pts = wire_points(a, b, avoid=[a, b] + mids)
    for m in mids:
        assert not crosses(pts, _box_of(m, 0.1)), "one of the blocks in between is still crossed"


def test_the_wire_sits_behind_the_blocks():
    """Even a perfectly routed wire must not be drawn on top of a block's name."""
    a, b = block(-3, 0), block(3, 0)
    w = wire(a, b, avoid=[a, b])
    assert w.z_index < 0


def test_the_endpoints_stay_on_the_two_blocks():
    a, b = block(-4, 0), block(4, 0)
    pts = wire_points(a, b, avoid=[a, b])
    start, end = pts[0], pts[-1]
    ab, bb = _box_of(a, 0.06), _box_of(b, 0.06)
    on = lambda p, box: box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]
    assert on(start, ab), "the wire does not start on the source block"
    assert on(end, bb), "the wire does not end on the target block"


@pytest.mark.parametrize("heads,tips", [("to", 1), ("both", 2), ("none", 0)])
def test_arrowheads_follow_the_heads_argument(heads, tips):
    a, b = block(-3, 0), block(3, 0)
    w = wire(a, b, avoid=[a, b], heads=heads)
    assert sum(len(s.get_tips()) for s in w.submobjects) == tips
