"""Port API: positions, sides, transforms, error messages, Connection routing, and
backward compatibility with the pre-v3 library (golden data recorded from the M0 commit)."""
import json
import os

import numpy as np
import pytest
from manim import DOWN, LEFT, RIGHT, UP, Arrow, Line, Scene, Succession, VGroup

import ipmotion_lib as L
from ipmotion_lib import (Connection, IPBlock, Port, SHAPE_REGISTRY, Theme, normalize_side,
                          route_points)

TH = Theme()
HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = json.load(open(os.path.join(HERE, "fixtures", "lib_v2_golden.json")))


def xy(v):
    return [round(float(x), 6) for x in v[:2]]


def close(a, b, tol=1e-4):
    return np.allclose(a[:2], b[:2], atol=tol)


# ------------------------------------------------------------ IPBlock ports
def test_ipblock_declared_ports_sit_on_their_edge_with_outward_side():
    b = IPBlock("M", TH, width=2.6, height=1.6, ports=[
        {"label": "ARVALID", "edge": "RIGHT"}, {"label": "CLK", "edge": "UP"},
        {"label": "RST", "edge": "LEFT"}, {"label": "IRQ", "edge": "DOWN"}])
    box = b.bg.box
    expected = {"ARVALID": (box.get_right()[0], "RIGHT"), "CLK": (box.get_top()[1], "UP"),
                "RST": (box.get_left()[0], "LEFT"), "IRQ": (box.get_bottom()[1], "DOWN")}
    for name, (coord, side) in expected.items():
        p = b.port(name)
        assert isinstance(p, Port) and p.side_name() == side and p.name == name and p.owner is b
        axis = 0 if side in ("LEFT", "RIGHT") else 1
        assert p.get_center()[axis] == pytest.approx(coord, abs=1e-4)


def test_multiple_ports_on_one_edge_are_spread_evenly():
    b = IPBlock("M", TH, width=2.6, height=1.5,
                ports=[{"label": f"P{i}", "edge": "RIGHT"} for i in range(3)])
    ys = [b.port(f"P{i}").get_center()[1] for i in range(3)]
    top, bottom = b.bg.box.get_top()[1], b.bg.box.get_bottom()[1]
    assert ys == pytest.approx([top - (bottom * -1 + top) * f for f in (0.25, 0.5, 0.75)], abs=1e-4)


def test_port_name_defaults_to_label_and_can_be_overridden():
    b = IPBlock("M", TH, ports=[{"label": "ARVALID", "edge": "RIGHT"},
                                {"label": "AR valid", "edge": "LEFT", "name": "ARV"}])
    assert b.port_names == ["ARVALID", "ARV"]


def test_edge_aliases_and_vectors_are_accepted():
    for edge in ("TOP", "top", UP, "UP"):
        assert normalize_side(edge).tolist() == [0, 1, 0]
    for edge in ("BOTTOM", DOWN):
        assert normalize_side(edge).tolist() == [0, -1, 0]
    with pytest.raises(ValueError):
        normalize_side("DIAGONAL")
    with pytest.raises(ValueError):
        normalize_side(UP + RIGHT)


def test_implicit_ports_exist_at_edge_centres_and_are_reserved():
    b = IPBlock("M", TH, width=2.6, height=1.6)
    box = b.bg.box
    assert sorted(b.implicit_ports()) == ["_bottom", "_left", "_right", "_top"]
    assert b.ports() == {}                                  # declared only
    assert close(b.port("_left").get_center(), box.get_left())
    assert close(b.port("_top").get_center(), box.get_top())
    assert b.port("_right").side_name() == "RIGHT"
    with pytest.raises(ValueError, match="reserved"):
        IPBlock("M", TH, ports=[{"label": "_left", "edge": "LEFT"}])


def test_duplicate_port_names_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        IPBlock("M", TH, ports=[{"label": "X", "edge": "LEFT"}, {"label": "X", "edge": "RIGHT"}])


def test_missing_port_error_lists_declared_and_implicit_separately():
    b = IPBlock("Master", TH, ports=[{"label": "ARVALID", "edge": "RIGHT"}])
    with pytest.raises(KeyError) as e:
        b.port("ARVALD")
    msg = str(e.value)
    assert "Declared ports: ['ARVALID']" in msg
    assert "Implicit ports: ['_bottom', '_left', '_right', '_top']" in msg
    assert "Master" in msg and "ARVALD" in msg


# --------------------------------------------------- ports follow transforms
def test_ports_follow_move_scale_and_arrange():
    a = IPBlock("A", TH, width=2, height=1, ports=[{"label": "OUT", "edge": "RIGHT"}])
    b = IPBlock("B", TH, width=2, height=1, ports=[{"label": "IN", "edge": "LEFT"}])
    g = VGroup(a, b).arrange(RIGHT, buff=3)
    g.scale(0.5).move_to(UP * 2 + LEFT)
    assert close(a.port("OUT").get_center(), a.bg.box.get_right())
    assert close(b.port("IN").get_center(), b.bg.box.get_left())
    assert a.port("OUT").get_center()[0] < b.port("IN").get_center()[0]
    assert b.port("IN").get_center()[0] - a.port("OUT").get_center()[0] == pytest.approx(1.5, abs=1e-3)


def test_ports_are_invisible_and_do_not_change_block_extents():
    plain = IPBlock("A", TH, width=2, height=1)
    for p in plain.implicit_ports().values():
        assert p.get_fill_opacity() == 0 and p.get_stroke_width() == 0
    assert plain.get_right()[0] == pytest.approx(plain.bg.box.get_right()[0], abs=1e-4)
    assert plain.width == pytest.approx(plain.bg.box.width, abs=1e-4)


# ------------------------------------------------------ HWComponent symbols
def test_symbol_sides_follow_the_drawn_geometry():
    and_ = L.ANDGate()
    assert {k: and_.port(k).side_name() for k in ("a", "b", "out")} == {"a": "LEFT", "b": "LEFT", "out": "RIGHT"}
    mux = L.MuxSymbol()
    assert mux.port("sel").side_name() == "DOWN" and mux.port("in_0").side_name() == "LEFT"
    nmos = L.NMOSTransistor()
    assert [nmos.port(k).side_name() for k in ("gate", "drain", "source")] == ["LEFT", "UP", "DOWN"]
    dff = L.DFlipFlop()
    assert dff.port("d").side_name() == "LEFT" and dff.port("q").side_name() == "RIGHT"
    macro = L.CustomMacro(custom_pins={"A": "LEFT", "B": "RIGHT", "C": "TOP", "D": "BOTTOM"})
    assert [macro.port(k).side_name() for k in "ABCD"] == ["LEFT", "RIGHT", "UP", "DOWN"]
    assert L.BusBar(taps=2).port("tap_0").side_name() == "UP"
    assert L.BusBar(taps=2, vertical=True).port("tap_0").side_name() == "RIGHT"


@pytest.mark.parametrize("key", sorted(k for k, c in SHAPE_REGISTRY.items() if c is not None))
def test_every_registered_symbol_has_valid_ports_matching_get_pin(key):
    kwargs = {"custom_pins": {"A": "LEFT", "B": "RIGHT"}} if key == "custom" else {}
    comp = SHAPE_REGISTRY[key](**kwargs)
    assert comp.pins is comp._ports and set(comp.port_names) == set(comp.pins)
    c = comp.body.get_center() if hasattr(comp, "body") else comp.get_center()
    for name in comp.port_names:
        p = comp.port(name)
        assert p.side_name() in ("LEFT", "RIGHT", "UP", "DOWN")
        assert close(comp.get_pin(name), p.get_center(), 1e-9)
        assert float((p.get_center() - c)[:2] @ p.side[:2]) >= -1e-6, f"{key}.{name} points into the body"


def test_get_pin_still_raises_keyerror_listing_available_pins():
    with pytest.raises(KeyError, match="Available"):
        L.ANDGate().get_pin("nope")


# --------------------------------------------- backward compat (golden data)
@pytest.mark.parametrize("entry", sorted(k for k in GOLDEN if "IPBlock" not in k))
def test_symbol_geometry_and_pins_unchanged_from_v2(entry):
    key, _, scale = entry.partition("@scale")
    kwargs = {"label": "X"}
    if scale:
        kwargs = {"scale": float(scale)}
    if key == "custom":
        kwargs["custom_pins"] = {"A": "LEFT", "B": "LEFT", "C": "RIGHT", "D": "TOP", "E": "BOTTOM"}
    comp = SHAPE_REGISTRY[key](**kwargs)
    want = GOLDEN[entry]
    for side in ("left", "right", "top", "bottom"):
        assert xy(getattr(comp, f"get_{side}")()) == pytest.approx(want[side], abs=1e-6), f"{entry} {side}"
    for pin, pos in want.get("pins", {}).items():
        assert xy(comp.get_pin(pin)) == pytest.approx(pos, abs=1e-6), f"{entry}.{pin}"
    assert set(comp.pins) == set(want.get("pins", {}))


def test_ipblock_extents_and_single_port_labels_unchanged_from_v2():
    plain = IPBlock("Master", TH, width=2.6, height=1.6)
    for side in ("left", "right", "top", "bottom"):
        assert xy(getattr(plain, f"get_{side}")()) == pytest.approx(GOLDEN["IPBlock:plain"][side], abs=1e-4)
    # one port per edge: labels must sit exactly where v2 drew them
    b = IPBlock("M", TH, width=2.6, height=1.6, ports=[
        {"label": "SEC_IN", "edge": "LEFT"}, {"label": "TL_OUT", "edge": "DOWN"},
        {"label": "R1", "edge": "RIGHT"}, {"label": "U1", "edge": "UP"}])
    labels = {t.text: xy(t.get_center()) for t in b.submobjects if hasattr(t, "text") and t.text in ("SEC_IN", "TL_OUT", "R1", "U1")}
    for name, pos in GOLDEN["IPBlock:ports"]["labels"].items():
        assert labels[name] == pytest.approx(pos, abs=1e-4), name


# ------------------------------------------------------------- Connection
def blocks(dx=6.0, dy=0.0):
    a = IPBlock("A", TH, width=2, height=1, ports=[{"label": "OUT", "edge": "RIGHT"}, {"label": "UP_P", "edge": "UP"}])
    b = IPBlock("B", TH, width=2, height=1, ports=[{"label": "IN", "edge": "LEFT"}, {"label": "DOWN_P", "edge": "DOWN"},
                                                   {"label": "TOP_P", "edge": "UP"}, {"label": "OUT2", "edge": "RIGHT"}])
    b.move_to(RIGHT * dx + UP * dy)
    return a, b


def orthogonal(pts):
    return all(abs(p[0] - q[0]) < 1e-9 or abs(p[1] - q[1]) < 1e-9 for p, q in zip(pts, pts[1:]))


def test_connection_straight_when_ports_are_aligned():
    a, b = blocks()
    c = Connection(a.port("OUT"), b.port("IN"))
    assert len(c.pts) == 2
    assert close(c.pts[0], a.port("OUT").get_center()) and close(c.pts[-1], b.port("IN").get_center())
    assert c.src is a.port("OUT") and c.dst is b.port("IN")


def test_connection_z_route_when_offset():
    a, b = blocks(dy=2.0)
    c = Connection(a.port("OUT"), b.port("IN"))
    assert len(c.pts) == 4 and orthogonal(c.pts)
    assert close(c.pts[0], a.port("OUT").get_center()) and close(c.pts[-1], b.port("IN").get_center())
    assert c.pts[1][0] == pytest.approx(c.pts[2][0])               # one vertical run in the gap


def test_connection_leaves_and_enters_along_port_sides():
    a, b = blocks(dy=2.0)
    for other in ("IN", "DOWN_P", "TOP_P"):
        c = Connection(a.port("OUT"), b.port(other))
        assert orthogonal(c.pts)
        first = c.pts[1] - c.pts[0]
        assert first[0] > 0 and abs(first[1]) < 1e-9                # leaves rightwards
        dst = b.port(other)
        last = c.pts[-1] - c.pts[-2]
        assert float(last[:2] @ dst.side[:2]) < 0                   # arrives against the port's outward side


def test_connection_goes_around_when_destination_is_behind():
    a, b = blocks(dx=-6.0)                                          # b is to the LEFT of a
    c = Connection(a.port("OUT"), b.port("IN"))
    assert orthogonal(c.pts) and len(c.pts) >= 5
    assert close(c.pts[-1], b.port("IN").get_center())
    last = c.pts[-1] - c.pts[-2]
    assert last[0] > 0                                              # still enters IN from its left side


def test_connection_u_turn_for_same_side_ports():
    a, b = blocks(dy=3.0)
    c = Connection(a.port("OUT"), b.port("OUT2"))
    assert orthogonal(c.pts)
    assert max(p[0] for p in c.pts) > max(a.port("OUT").get_center()[0], b.port("OUT2").get_center()[0])


def test_direct_style_is_one_straight_arrow():
    a, b = blocks(dy=2.0)
    c = Connection(a.port("OUT"), b.port("IN"), style="direct")
    assert len(c.pts) == 2


def test_connection_rejects_non_ports_and_bad_style():
    a, b = blocks()
    with pytest.raises(TypeError):
        Connection(a, b)
    with pytest.raises(ValueError):
        Connection(a.port("OUT"), b.port("IN"), style="spline")


def test_connection_to_implicit_ports_and_transfer_animation():
    a = IPBlock("A", TH, width=2, height=1)
    b = IPBlock("B", TH, width=2, height=1).shift(RIGHT * 6)
    c = Connection(a.port("_right"), b.port("_left"), color="#00FFF0")
    assert isinstance(c.transfer("REQ", "#00FFF0", TH), Succession)


def test_route_points_helper_is_pure_and_returns_3d_points():
    pts = route_points(np.array([0, 0, 0]), RIGHT, np.array([4, 2, 0]), LEFT)
    assert all(len(p) == 3 for p in pts) and pts[0].tolist() == [0, 0, 0] and pts[-1].tolist() == [4, 2, 0]


def test_block_with_ports_deep_copies_and_copy_ports_belong_to_the_copy():
    from ipmotion.lint.worker import _fast_deepcopy
    b = IPBlock("A", TH, ports=[{"label": "OUT", "edge": "RIGHT"}])
    for dup in (b.copy(), _fast_deepcopy(b, {})):          # Manim's deepcopy and the lint fast path
        assert dup is not b and dup.port("OUT").owner is dup
        assert dup.port("OUT") is not b.port("OUT")
        assert close(dup.port("OUT").get_center(), b.port("OUT").get_center())
