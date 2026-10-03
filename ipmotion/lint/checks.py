"""Geometric lint checks over plain-data snapshots (see snapshot.py).

Each check takes (snapshot, frame, thresholds) and returns raw issue dicts:
  {check, severity, objects:[{name,kind,bbox}], detail, key, involved:[unit ids]}
"""
from __future__ import annotations

import math
import os
import tomllib

import numpy as np

_STYLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "style.toml")
RECT_SHAPES = ("Rectangle", "RoundedRectangle", "Square", "DashedVMobject")


def load_thresholds(path: str | None = None) -> dict:
    with open(path or _STYLE, "rb") as fh:
        return tomllib.load(fh)["lint"]


# ------------------------------------------------------------- geometry
def _area(b):
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _shrink(b, p):
    return [b[0] + p, b[1] + p, b[2] - p, b[3] - p]


def _inter(a, b):
    return [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]


def _inter_area(a, b):
    return _area(_inter(a, b))


def _contains(outer, inner, tol=1e-3):
    return (outer[0] - tol <= inner[0] and outer[1] - tol <= inner[1]
            and outer[2] + tol >= inner[2] and outer[3] + tol >= inner[3])


def _gap(a, b):
    dx = max(0.0, b[0] - a[2], a[0] - b[2])
    dy = max(0.0, b[1] - a[3], a[1] - b[3])
    return math.hypot(dx, dy)


def _point_box(p, b):
    """(outside_distance, inside_depth); one of them is 0."""
    dx = max(b[0] - p[0], 0.0, p[0] - b[2])
    dy = max(b[1] - p[1], 0.0, p[1] - b[3])
    out = math.hypot(dx, dy)
    if out > 0:
        return out, 0.0
    return 0.0, min(p[0] - b[0], b[2] - p[0], p[1] - b[1], b[3] - p[1])


def _point_seg(p, s):
    ax, ay, bx, by = s
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * vx + (p[1] - ay) * vy) / L2))
    return math.hypot(p[0] - (ax + t * vx), p[1] - (ay + t * vy))


def _seg_hits_box(s, b):
    """Liang-Barsky segment/AABB intersection."""
    ax, ay, bx, by = s
    dx, dy = bx - ax, by - ay
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, ax - b[0]), (dx, b[2] - ax), (-dy, ay - b[1]), (dy, b[3] - ay)):
        if p == 0:
            if q < 0:
                return False
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return False
                t0 = max(t0, r)
            else:
                if r < t0:
                    return False
                t1 = min(t1, r)
    return True


def _points_in_poly(pts: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """Even-odd ray casting; pts (N,2), poly (M,2)."""
    x, y = pts[:, 0], pts[:, 1]
    inside = np.zeros(len(pts), dtype=bool)
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        cond = (yi > y) != (yj > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            xcross = (xj - xi) * (y - yi) / (yj - yi) + xi
        inside ^= cond & (x < xcross)
        j = i
    return inside


def _obj(u):
    return {"name": u["name"], "kind": u["kind"], "bbox": u["bbox"]}


def _issue(check, severity, units, detail, key, extra=None):
    d = {"check": check, "severity": severity, "objects": [_obj(u) for u in units],
         "detail": detail, "key": key, "involved": [u["id"] for u in units]}
    if extra:
        d.update(extra)
    return d


def _fmt(v):
    return f"{v:.2f}"


# ---------------------------------------------------------------- checks
def _hidden_under_owner(conn, text, snap, th):
    """True if an opaque fill of the text's own block is drawn after the connector over the text."""
    owner = text.get("owner")
    if owner is None:
        return False
    cx, cy = (text["bbox"][0] + text["bbox"][2]) / 2, (text["bbox"][1] + text["bbox"][3]) / 2
    for f in snap["fills"]:
        b = f["bbox"]
        if (f["unit"] == owner and f["order"] > conn["order"] and f["fill"] >= th["occlusion_min_fill"]
                and b[0] <= cx <= b[2] and b[1] <= cy <= b[3]):
            return True
    return False


def check_text_overlap(snap, frame, th):
    out = []
    pad = th["text_overlap_pad"]
    units = snap["units"]
    by_id = {u["id"]: u for u in units}
    texts = [u for u in units if u["kind"] == "text" and not u.get("transient")]
    blocks = [u for u in units if u["kind"] == "block" and not u.get("transient")]
    conns = [u for u in units if u["kind"] == "connector" and not u.get("transient")]

    for i, a in enumerate(texts):
        ba = _shrink(a["bbox"], pad)
        for b in texts[i + 1:]:
            ov = _inter(ba, _shrink(b["bbox"], pad))
            if ov[2] > ov[0] and ov[3] > ov[1]:
                frac = _area(ov) / max(1e-9, min(_area(a["bbox"]), _area(b["bbox"])))
                out.append(_issue("text_overlap", "error", [a, b],
                                  f"text {a['text']!r} overlaps {b['text']!r} "
                                  f"({_fmt(ov[2] - ov[0])}x{_fmt(ov[3] - ov[1])} units, {frac:.0%} of the smaller)",
                                  ("tt", *sorted([a["name"], b["name"]]))))
        for c in conns:
            if _hidden_under_owner(c, a, snap, th):
                continue
            for s in c.get("segs", []):
                if _seg_hits_box(s, ba):
                    out.append(_issue("text_overlap", "error", [a, c],
                                      f"connector {c['name']!r} runs through text {a['text']!r}",
                                      ("tc", a["name"], c["name"])))
                    break
        owner = by_id.get(a.get("owner"))
        for blk in blocks:
            if blk["id"] == a.get("owner"):
                continue
            if owner and owner["kind"] == "block" and _contains(blk["bbox"], owner["bbox"]):
                continue                                    # nested block's own text
            ov = _inter(ba, _shrink(blk["bbox"], pad))
            if ov[2] > ov[0] and ov[3] > ov[1]:
                out.append(_issue("text_overlap", "error", [a, blk],
                                  f"text {a['text']!r} sits on top of block {blk['name']!r} "
                                  f"({_fmt(ov[2] - ov[0])}x{_fmt(ov[3] - ov[1])} units)",
                                  ("tb", a["name"], blk["name"])))
        if owner and owner["cls"] in ("IPBlock", "Banner"):
            ob, tb = owner["bbox"], a["bbox"]
            over = max(ob[0] - tb[0], tb[2] - ob[2], ob[1] - tb[1], tb[3] - ob[3])
            if over > 0.02:
                out.append(_issue("text_overlap", "error", [a, owner],
                                  f"text {a['text']!r} overflows its block {owner['name']!r} by {_fmt(over)} units",
                                  ("to", a["name"], owner["name"])))
    return out


def check_text_occluded(snap, frame, th, grid=(12, 5)):
    out = []
    fills = [f for f in snap["fills"] if f["fill"] >= th["occlusion_min_fill"] and not f.get("transient")]
    by_id = {u["id"]: u for u in snap["units"]}
    for t in snap["units"]:
        if t["kind"] != "text" or _area(t["bbox"]) <= 0 or t.get("transient"):
            continue
        x0, y0, x1, y1 = t["bbox"]
        gx = np.linspace(x0, x1, grid[0] + 2)[1:-1]
        gy = np.linspace(y0, y1, grid[1] + 2)[1:-1]
        pts = np.array([(x, y) for x in gx for y in gy])
        covered = np.zeros(len(pts), dtype=bool)
        culprits = []
        for f in fills:
            if f["order"] <= t["order"] or _inter_area(f["bbox"], t["bbox"]) <= 0:
                continue
            if len(f["poly"]) >= 3:
                hit = _points_in_poly(pts, np.array(f["poly"]))
            else:
                b = f["bbox"]
                hit = (pts[:, 0] >= b[0]) & (pts[:, 0] <= b[2]) & (pts[:, 1] >= b[1]) & (pts[:, 1] <= b[3])
            new = hit & ~covered
            if new.any():
                culprits.append((int(new.sum()), f))
            covered |= hit
        cov = float(covered.mean())
        if cov >= th["occlusion_min_coverage"]:
            culprits.sort(key=lambda c: -c[0])
            top = culprits[0][1]
            occ_unit = by_id.get(top["unit"])
            units = [t] + ([occ_unit] if occ_unit else [])
            out.append(_issue("text_occluded", "error", units,
                              f"text {t['text']!r} is {cov:.0%} covered by {top['leaf']!r} "
                              f"(fill {top['fill']}) drawn after it",
                              ("occ", t["name"], top["leaf"])))
    return out


def check_dangling_endpoint(snap, frame, th):
    out = []
    tol, jtol = th["endpoint_tolerance"], th["junction_tolerance"]
    units = snap["units"]
    blocks = [u for u in units if u["kind"] == "block" and not u.get("transient")]
    conns = [u for u in units if u["kind"] == "connector" and u.get("segs") and not u.get("transient")]
    fills = snap["fills"]
    for c in conns:
        for label, pt in (("start", c["segs"][0][:2]), ("end", c["segs"][-1][2:])):
            if any(math.hypot(pt[0] - p["xy"][0], pt[1] - p["xy"][1]) <= tol for p in snap["ports"]):
                continue
            nearest, inside_in = None, None
            ok = False
            for b in blocks:
                outside, depth = _point_box(pt, b["bbox"])
                if outside > 0:
                    if nearest is None or outside < nearest[0]:
                        nearest = (outside, b)
                    if outside <= tol:
                        ok = True
                        break
                else:
                    if depth <= tol:
                        ok = True
                        break
                    hidden = any(f["unit"] == b["id"] and f["order"] > c["order"]
                                 and f["fill"] >= th["occlusion_min_fill"] for f in fills)
                    if hidden:
                        ok = True
                        break
                    inside_in = (depth, b)
            if ok:
                continue
            if any(o is not c and any(_point_seg(pt, s) <= jtol for s in o.get("segs", []))
                   for o in conns):
                continue
            if inside_in:
                depth, b = inside_in
                out.append(_issue("dangling_endpoint", "error", [c, b],
                                  f"{label} of {c['name']!r} at ({_fmt(pt[0])},{_fmt(pt[1])}) ends "
                                  f"{_fmt(depth)} units inside block {b['name']!r}, not on its edge or a port",
                                  ("dang", c["name"], label)))
            else:
                where = (f"nearest block {nearest[1]['name']!r} edge is {_fmt(nearest[0])} away"
                         if nearest else "no block nearby")
                objs = [c] + ([nearest[1]] if nearest else [])
                out.append(_issue("dangling_endpoint", "error", objs,
                                  f"{label} of {c['name']!r} at ({_fmt(pt[0])},{_fmt(pt[1])}) ends in "
                                  f"empty space; {where}",
                                  ("dang", c["name"], label), {"point": [pt[0], pt[1]]}))
    return out


def check_out_of_frame(snap, frame, th):
    out = []
    hw, hh = frame["width"] / 2, frame["height"] / 2
    safe = th["frame_safe_margin"]
    for u in snap["units"]:
        x0, y0, x1, y1 = u["bbox"]
        sides = {"left": -hw - x0, "right": x1 - hw, "bottom": -hh - y0, "top": y1 - hh}
        over = {k: v for k, v in sides.items() if v > 1e-3}
        full = x1 < -hw or x0 > hw or y1 < -hh or y0 > hh
        if over:
            backdrop = u["kind"] == "container" or (
                u["kind"] == "shape" and u["cls"] in RECT_SHAPES and u["fill"] < 0.5)
            sev = "warning" if backdrop else "error"
            desc = ", ".join(f"{k} by {_fmt(v)}" for k, v in over.items())
            what = "entirely outside the frame" if full else f"extends beyond the frame ({desc})"
            label = u.get("text") and f"text {u['text']!r}" or f"{u['kind']} {u['name']!r}"
            out.append(_issue("out_of_frame", sev, [u], f"{label} {what}", ("oof", u["name"])))
        elif u["kind"] in ("text", "block", "connector"):
            m = min(x0 + hw, hw - x1, y0 + hh, hh - y1)
            if m < safe:
                label = u.get("text") and f"text {u['text']!r}" or f"{u['kind']} {u['name']!r}"
                out.append(_issue("out_of_frame", "warning", [u],
                                  f"{label} is only {_fmt(m)} units from the frame edge (safe margin {safe})",
                                  ("margin", u["name"])))
    return out


def check_min_spacing(snap, frame, th):
    out = []
    units = snap["units"]
    blocks = [u for u in units if u["kind"] == "block" and not u.get("transient")]
    for i, a in enumerate(blocks):
        for b in blocks[i + 1:]:
            ov = _inter(_shrink(a["bbox"], 1e-3), _shrink(b["bbox"], 1e-3))
            if ov[2] > ov[0] and ov[3] > ov[1]:
                if _contains(a["bbox"], b["bbox"]) or _contains(b["bbox"], a["bbox"]):
                    continue                                   # intentional nesting
                out.append(_issue("min_spacing", "error", [a, b],
                                  f"blocks {a['name']!r} and {b['name']!r} overlap "
                                  f"({_fmt(ov[2] - ov[0])}x{_fmt(ov[3] - ov[1])} units)",
                                  ("bb", *sorted([a["name"], b["name"]]))))
            else:
                g = _gap(a["bbox"], b["bbox"])
                if g < th["min_block_gap"]:
                    out.append(_issue("min_spacing", "warning", [a, b],
                                      f"gap between {a['name']!r} and {b['name']!r} is {_fmt(g)} "
                                      f"(< {th['min_block_gap']})", ("bg", *sorted([a["name"], b["name"]]))))
    containers = [u for u in units if u["cls"] == "DomainGroup"
                  or (u["kind"] == "shape" and u["cls"] in RECT_SHAPES and u["fill"] < 0.5)]
    for c in containers:
        inside = [b for b in blocks if _contains(c["bbox"], b["bbox"], 0.02)]
        if not inside:
            continue
        for b in blocks:
            if b in inside:
                continue
            if _inter_area(_shrink(c["bbox"], 1e-3), _shrink(b["bbox"], 1e-3)) > 1e-4 \
                    and not _contains(b["bbox"], c["bbox"]):
                out.append(_issue("min_spacing", "error", [b, c],
                                  f"block {b['name']!r} straddles the border of container {c['name']!r}",
                                  ("strad", b["name"], c["name"])))
    for t in (u for u in units if u["kind"] == "text" and u.get("owner") is None and not u.get("transient")):
        for b in blocks:
            g = _gap(t["bbox"], b["bbox"])
            if 0 < g < th["min_label_gap"] and _inter_area(t["bbox"], b["bbox"]) == 0:
                out.append(_issue("min_spacing", "warning", [t, b],
                                  f"label {t['text']!r} is {_fmt(g)} from block {b['name']!r}",
                                  ("lg", t["name"], b["name"])))
    return out


def check_min_text_size(snap, frame, th):
    out = []
    for u in snap["units"]:
        if u["kind"] != "text" or not u.get("text", "").strip():
            continue
        cap = u["cap_px"]
        if cap < th["min_text_cap_px_error"]:
            sev = "error"
        elif cap < th["min_text_cap_px_warn"]:
            sev = "warning"
        else:
            continue
        out.append(_issue("min_text_size", sev, [u],
                          f"text {u['text']!r} renders with ~{cap:.1f}px cap height at "
                          f"{th['reference_height_px']}p (font_size {u['font_size']:.1f}); "
                          f"minimum {th['min_text_cap_px_warn']}px",
                          ("size", u["name"])))
    return out


CHECKS = {
    "text_overlap": check_text_overlap,
    "text_occluded": check_text_occluded,
    "dangling_endpoint": check_dangling_endpoint,
    "out_of_frame": check_out_of_frame,
    "min_spacing": check_min_spacing,
    "min_text_size": check_min_text_size,
}
