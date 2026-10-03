"""Turn a live Manim Scene into a plain-data geometry snapshot.

The snapshot is JSON-serialisable so the checks (checks.py) never touch Manim
objects and can be unit-tested with hand-written data.

Unit kinds
  text       a Text/MarkupText (glyphs are collapsed into one unit)
  block      IPBlock, HWComponent, GlowBox, or a filled raw Rectangle
  container  Banner, DomainGroup (own their title text)
  connector  Line/Arrow or a Wire/Route/Connection group; carries its segments
  shape      any other drawn VMobject (Circle, Polygon, ...)
Ports and fully transparent objects are not units.
"""
from __future__ import annotations

import numpy as np
from manim import (
    DashedVMobject, Line, Mobject, MarkupText, Rectangle, Text, VMobject,
)
from manim.utils.family import extract_mobject_family_members

try:  # the library is optional so snapshot code stays testable without it
    import ipmotion_lib as _lib
except Exception:  # pragma: no cover
    _lib = None


def _types(*names):
    return tuple(c for c in (getattr(_lib, n, None) for n in names) if c is not None)


STRONG_TYPES = _types("IPBlock", "HWComponent")        # blocks (outermost wins)
CONTAINER_TYPES = _types("Banner", "DomainGroup")      # own their title text
GLOW_TYPES = _types("GlowBox")                         # standalone packets etc.
ROUTE_TYPES = _types("Wire", "DirectRoute", "ManhattanRoute")  # Connection subclasses ManhattanRoute

PACKET_MAX_W, PACKET_MAX_H = 2.2, 1.1   # standalone GlowBoxes up to this size count as packets
VISIBLE = 0.02          # opacity below this counts as invisible
GLOW_MAX_OPACITY = 0.3  # connector strokes at or below this are glow copies
FILL_RECORD_MIN = 0.3   # leaves with fill >= this are kept as possible occluders

_cap_cache: dict[str, float] = {}


def cap_height_per_pt(font: str = "Consolas") -> float:
    """Scene units of cap height per point of font size (measured once)."""
    if font not in _cap_cache:
        ref = Text("H", font=font, font_size=100)
        _cap_cache[font] = float(ref.height) / 100.0
    return _cap_cache[font]


# ---------------------------------------------------------------- naming
def build_names(local_maps: list[dict]) -> dict[int, str]:
    """id(mobject) -> readable name, from construct()'s local variables.

    Priority: direct variable > attribute path (banner.txt) > index path (grp[3]).
    """
    names: dict[int, str] = {}
    roots: list[tuple[str, Mobject]] = []

    def take(name, value):
        if isinstance(value, Mobject):
            if id(value) not in names:
                names[id(value)] = name
                roots.append((name, value))
        elif isinstance(value, (list, tuple)) and len(value) <= 300:
            for i, v in enumerate(value):
                take(f"{name}[{i}]", v)
        elif isinstance(value, dict) and len(value) <= 300:
            for k, v in value.items():
                take(f"{name}[{k!r}]", v)

    for locs in local_maps:                      # innermost frame first
        for name, value in locs.items():
            if name.startswith("__") or name in ("self", "theme"):
                continue
            take(name, value)

    def attr_pass(name, mob, depth):
        if depth > 2:
            return
        for k, v in vars(mob).items():
            if isinstance(v, Mobject) and id(v) not in names and not k.startswith("_"):
                names[id(v)] = f"{name}.{k}"
                attr_pass(f"{name}.{k}", v, depth + 1)

    for name, mob in list(roots):
        attr_pass(name, mob, 0)

    def index_pass(name, mob, depth):
        if depth > 3:
            return
        for i, s in enumerate(mob.submobjects):
            if id(s) not in names:
                names[id(s)] = f"{name}[{i}]"
            index_pass(names[id(s)], s, depth + 1)

    for name, mob in list(roots):
        index_pass(name, mob, 0)
    return names


# --------------------------------------------------------------- helpers
def _opacity(m: VMobject) -> tuple[float, float]:
    fill = float(m.get_fill_opacity())
    stroke = float(m.get_stroke_opacity()) if float(np.max(m.get_stroke_width())) > 0 else 0.0
    return fill, stroke


def _bbox_of_points(pts: np.ndarray) -> list[float]:
    return [float(pts[:, 0].min()), float(pts[:, 1].min()),
            float(pts[:, 0].max()), float(pts[:, 1].max())]


def _merge(a: list[float] | None, b: list[float]) -> list[float]:
    if a is None:
        return list(b)
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def _r(v, n=4):
    return round(float(v), n)


def _rbox(b):
    return [_r(x) for x in b]


class _Unit:
    __slots__ = ("kind", "root", "bbox", "order_min", "order_max", "fill", "stroke",
                 "segs", "owner_root", "extra")

    def __init__(self, kind, root):
        self.kind, self.root = kind, root
        self.bbox = None
        self.order_min = 10 ** 9
        self.order_max = -1
        self.fill = 0.0
        self.stroke = 0.0
        self.segs: list[list[float]] = []
        self.owner_root = None
        self.extra: dict = {}

    def touch(self, order):
        self.order_min = min(self.order_min, order)
        self.order_max = max(self.order_max, order)


def _chain(leaf: Mobject, parent: dict) -> list[Mobject]:
    out, cur, guard = [], leaf, 0
    while cur is not None and guard < 64:
        out.append(cur)
        cur = parent.get(id(cur))
        guard += 1
    return out


def _classify(chain: list[Mobject]):
    """-> (kind, root) for a leaf, given its ancestor chain (leaf first)."""
    for a in chain:
        if getattr(a, "is_port", False):
            return "port", a
    for a in chain:
        if isinstance(a, (Text, MarkupText)):
            return "text", a
    strong = [a for a in chain if isinstance(a, STRONG_TYPES)]
    if strong:
        return "block", strong[-1]                        # outermost
    cont = [a for a in chain if isinstance(a, CONTAINER_TYPES)]
    if cont:
        return "container", cont[-1]
    for a in chain:
        if isinstance(a, GLOW_TYPES):
            return "block", a
    for a in chain:
        if isinstance(a, ROUTE_TYPES):
            return "connector", a
    for a in chain:
        if isinstance(a, Line):
            return "connector", a
    for a in chain:
        if isinstance(a, DashedVMobject):        # its dashes are one outline, not dozens of shapes
            return "shape", a
    return "shape", chain[0]


def _transient(chain: list[Mobject]) -> bool:
    return any(getattr(a, "lint_transient", False) for a in chain)


def _ignores(chain: list[Mobject]) -> list[str]:
    out: list[str] = []
    for a in chain:
        v = getattr(a, "lint_ignore", None)
        if v:
            out.extend([v] if isinstance(v, str) else list(v))
    return sorted(set(out))


# -------------------------------------------------------------- snapshot
def take_snapshot(scene, names: dict[int, str]) -> dict:
    from manim import config

    parent: dict[int, Mobject] = {}
    stack = list(scene.mobjects)
    while stack:
        m = stack.pop()
        for s in m.submobjects:
            if id(s) not in parent:
                parent[id(s)] = m
            stack.append(s)

    drawn = extract_mobject_family_members(
        scene.mobjects, use_z_index=True, only_those_with_points=True)

    units: dict[int, _Unit] = {}
    fills: list[dict] = []
    ports: list[dict] = []
    port_owner: dict[int, int] = {}

    for order, leaf in enumerate(drawn):
        if not isinstance(leaf, VMobject):
            continue
        chain = _chain(leaf, parent)
        kind, root = _classify(chain)
        pts = leaf.points
        if len(pts) == 0:
            continue
        xy = pts[:, :2]

        if kind == "port":
            ports.append({"name": getattr(root, "name", ""), "xy": [_r(xy[0, 0]), _r(xy[0, 1])],
                          "owner_root": id(getattr(root, "owner", None)) if getattr(root, "owner", None) is not None else None})
            continue

        fill, stroke = _opacity(leaf)
        visible = max(fill, stroke)
        if kind == "text":
            u = units.get(id(root))
            if u is None:
                u = units[id(root)] = _Unit("text", root)
                u.extra["ignore"] = _ignores(chain)
                u.extra["transient"] = _transient(chain)
            if visible >= VISIBLE:
                u.bbox = _merge(u.bbox, _bbox_of_points(xy))
                u.touch(order)
                u.fill = max(u.fill, fill)
            continue

        if visible < VISIBLE:
            continue

        if kind == "connector":
            u = units.get(id(root))
            if u is None:
                u = units[id(root)] = _Unit("connector", root)
                u.extra["ignore"] = _ignores(chain)
                u.extra["transient"] = _transient(chain)
            if isinstance(leaf, Line) and stroke > GLOW_MAX_OPACITY:
                s, e = leaf.get_start(), leaf.get_end()
                u.segs.append([_r(s[0]), _r(s[1]), _r(e[0]), _r(e[1])])
                u.extra.setdefault("seg_tips", []).append(
                    [bool(leaf.has_start_tip()), bool(leaf.has_tip())])
                seg_pts = np.array([s[:2], e[:2]])
                u.bbox = _merge(u.bbox, _bbox_of_points(seg_pts))
                u.bbox = _merge(u.bbox, _bbox_of_points(xy))
                u.touch(order)
                u.stroke = max(u.stroke, stroke)
            elif stroke > GLOW_MAX_OPACITY or fill > GLOW_MAX_OPACITY:   # arrow tip
                u.bbox = _merge(u.bbox, _bbox_of_points(xy))
                u.touch(order)
            continue

        # block / container / shape
        key = id(root) if (kind in ("block", "container") or root is not leaf) else id(leaf)
        u = units.get(key)
        if u is None:
            real_kind = kind
            if kind == "shape" and isinstance(leaf, Rectangle) and fill >= 0.5:
                real_kind = "block"
            u = units[key] = _Unit(real_kind, root)
            u.extra["ignore"] = _ignores(chain)
            # standalone GlowBox (not part of an IPBlock) is a packet/glow token
            u.extra["transient"] = _transient(chain)
            u.extra["glow_root"] = isinstance(root, GLOW_TYPES)      # packet-sized ones are made transient below
        u.bbox = _merge(u.bbox, _bbox_of_points(xy))
        u.touch(order)
        u.fill = max(u.fill, fill)
        u.stroke = max(u.stroke, stroke)
        if fill >= FILL_RECORD_MIN:
            fills.append({"unit_key": key, "leaf": names.get(id(leaf), type(leaf).__name__),
                          "order": order, "fill": _r(fill),
                          "bbox": _rbox(_bbox_of_points(xy)),
                          "poly": [[_r(a[0]), _r(a[1])] for a in np.asarray(leaf.get_anchors())[:64]]})

    # text ownership: strong/container ancestor, else a rectangle sibling that contains it
    rect_units = [(k, u) for k, u in units.items() if u.kind == "block" and u.root is not None
                  and isinstance(u.root, Rectangle)]
    for key, u in units.items():
        if u.kind != "text" or u.bbox is None:
            continue
        chain = _chain(u.root, parent)
        for a in chain[1:]:
            if isinstance(a, STRONG_TYPES + CONTAINER_TYPES):
                u.owner_root = id(a)
        if u.owner_root is None:
            for a in chain[1:]:
                if isinstance(a, GLOW_TYPES):
                    u.owner_root = id(a)
                    break
        if u.owner_root is None:
            cx, cy = (u.bbox[0] + u.bbox[2]) / 2, (u.bbox[1] + u.bbox[3]) / 2
            par = parent.get(id(u.root))
            best = None
            for k2, ru in rect_units:
                if parent.get(id(ru.root)) is par and par is not None:
                    b = ru.bbox
                    if b[0] <= cx <= b[2] and b[1] <= cy <= b[3]:
                        area = (b[2] - b[0]) * (b[3] - b[1])
                        if best is None or area < best[0]:
                            best = (area, k2)
            if best:
                u.owner_root = best[1]

    for u in units.values():
        if u.extra.get("glow_root") and u.bbox is not None:
            if (u.bbox[2] - u.bbox[0]) <= PACKET_MAX_W and (u.bbox[3] - u.bbox[1]) <= PACKET_MAX_H:
                u.extra["transient"] = True          # a standalone packet-sized GlowBox is a travelling token
    transient_blocks = [(k, u) for k, u in units.items()
                        if u.kind == "block" and u.extra.get("transient") and u.bbox is not None]
    for key, u in units.items():
        if u.kind == "text" and u.bbox is not None and u.owner_root is None and not u.extra.get("transient"):
            cx, cy = (u.bbox[0] + u.bbox[2]) / 2, (u.bbox[1] + u.bbox[3]) / 2
            for k2, tb in transient_blocks:
                b = tb.bbox
                if b[0] <= cx <= b[2] and b[1] <= cy <= b[3]:
                    u.extra["transient"] = True
                    u.owner_root = id(tb.root)
                    break

    # assign sequential ids, then translate owner roots / unit keys into ids
    ordered = [(k, u) for k, u in units.items() if u.bbox is not None]
    ids = {k: i for i, (k, _) in enumerate(ordered)}
    root_to_id = {id(u.root): ids[k] for k, u in ordered if u.root is not None}
    cap = cap_height_per_pt()
    px_per_unit = 1080.0 / float(config.frame_height)

    out_units = []
    for k, u in ordered:
        name = names.get(id(u.root))
        d = {"id": ids[k], "kind": u.kind, "cls": type(u.root).__name__,
             "bbox": _rbox(u.bbox), "order": u.order_max, "order_min": u.order_min,
             "fill": _r(u.fill), "stroke": _r(u.stroke), "ignore": u.extra.get("ignore", []),
             "transient": bool(u.extra.get("transient"))}
        if u.kind == "text":
            font = getattr(u.root, "font", "Consolas") or "Consolas"
            try:
                fs = float(u.root.font_size)
            except Exception:
                fs = 0.0
            d["text"] = getattr(u.root, "text", "")
            d["font_size"] = _r(fs, 2)
            d["cap_px"] = _r(fs * cap_height_per_pt(font if isinstance(font, str) else "Consolas") * px_per_unit, 2)
            d["owner"] = root_to_id.get(u.owner_root) if u.owner_root is not None else None
            if name is None:
                name = f"Text({d['text'][:24]!r})"
        elif u.kind == "connector":
            d["segs"] = u.segs
            tips = u.extra.get("seg_tips") or []
            d["tips"] = [bool(tips[0][0]), bool(tips[-1][1])] if tips else [False, False]
            if not u.segs and u.bbox is None:
                continue
        if name is None:
            name = f"{d['cls']}@({(u.bbox[0] + u.bbox[2]) / 2:.2f},{(u.bbox[1] + u.bbox[3]) / 2:.2f})"
        d["name"] = name
        out_units.append(d)

    transient_ids = {ids[k] for k, u in ordered if u.extra.get("transient")}
    for f in fills:
        f["unit"] = ids.get(f.pop("unit_key"))
        f["transient"] = f["unit"] in transient_ids
    for p in ports:
        orr = p.pop("owner_root")
        p["owner"] = root_to_id.get(orr) if orr is not None else None

    return {"units": out_units, "fills": fills, "ports": ports}
