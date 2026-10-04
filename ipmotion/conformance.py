"""Spec conformance: does the generated script draw what the spec says, and only that?

labels_and_banners(spec) / preamble(spec)   the LABELS and BANNERS block the generated script must start with
check_static(script_text, spec)             the script text: LABELS/BANNERS intact, no hand-typed strings, no lint_ignore
check_dynamic(result, spec)                 the lint worker's snapshots: blocks, domains, connections (with arrowheads),
                                            banners, packet/state text, and nothing extra
check(...)                                  both, as a list of issues {check, severity, detail}

Not checked yet (known limit): which blocks/connections are highlighted in which step, and packet paths.
"""
from __future__ import annotations

import ast
import math

TOL_END = 0.6          # a connection end must be within this of its block
TOL_JOIN = 0.06        # segments that touch within this form one wire
TOL_IN = 0.03          # containment slack
REGION_CLASSES = ("DomainGroup", "Rectangle", "RoundedRectangle", "Square", "DashedVMobject", "Polygon", "VMobject")


def _norm(s) -> str:
    """Compare text ignoring all whitespace: Manim's Text.text drops spaces ('AXI Master' -> 'AXIMaster')."""
    return "".join(str(s).split())


# ----------------------------------------------------------- the dicts
def labels_and_banners(spec: dict) -> tuple[dict, list]:
    labels: dict[str, str] = {}
    if spec.get("title"):
        labels["title"] = spec["title"]
    for b in spec.get("blocks") or []:
        labels[b["id"]] = b["label"]
    for d in spec.get("domains") or []:
        labels[f"domain_{d['id']}"] = d["label"]
    for c in spec.get("connections") or []:
        if c.get("label"):
            labels[f"conn_{c['id']}"] = c["label"]
    banners = []
    for n, s in enumerate(spec.get("sequence") or [], 1):
        banners.append(s["banner"])
        for k, p in enumerate(s.get("packets") or []):
            if p.get("label"):
                labels[f"packet_{n}_{k}"] = p["label"]
        for k, st in enumerate(s.get("state") or []):
            if st.get("value") is not None:
                labels[f"state_{n}_{k}"] = str(st["value"])
    return labels, banners


def preamble(spec: dict) -> str:
    labels, banners = labels_and_banners(spec)
    lines = ["LABELS = {"] + [f"    {k!r}: {v!r}," for k, v in labels.items()] + ["}", "BANNERS = ["]
    lines += [f"    {b!r}," for b in banners] + ["]"]
    return "\n".join(lines)


def _issue(check, detail):
    return {"check": check, "severity": "error", "detail": detail}


# ------------------------------------------------------------- static
def check_static(script_text: str, spec: dict) -> list[dict]:
    issues = []
    labels, banners = labels_and_banners(spec)
    try:
        tree = ast.parse(script_text)
    except SyntaxError as e:
        return [_issue("conformance_static", f"script does not parse: {e}")]

    defs, def_nodes = {}, set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id in ("LABELS", "BANNERS"):
            try:
                defs[node.targets[0].id] = ast.literal_eval(node.value)
            except Exception:
                defs[node.targets[0].id] = None
            def_nodes.update(id(n) for n in ast.walk(node))
    for name, want in (("LABELS", labels), ("BANNERS", banners)):
        if name not in defs:
            issues.append(_issue("conformance_static", f"{name} is missing: start the script with the LABELS and BANNERS block exactly as given"))
        elif defs[name] != want:
            got = defs[name]
            if isinstance(want, dict) and isinstance(got, dict):
                bad = sorted(k for k in set(want) | set(got) if want.get(k) != got.get(k))
                issues.append(_issue("conformance_static", f"{name} was changed (keys differing from the given block: {bad[:8]}); copy it exactly"))
            else:
                issues.append(_issue("conformance_static", f"{name} was changed; copy it exactly as given"))

    expected = {_norm(v): f"LABELS[{k!r}]" for k, v in labels.items()}
    expected.update({_norm(b): f"BANNERS[{i}]" for i, b in enumerate(banners)})
    uses = {"LABELS": 0, "BANNERS": 0}
    flagged = set()
    for node in ast.walk(tree):
        if id(node) in def_nodes:
            continue
        if isinstance(node, ast.Name) and node.id in uses and isinstance(node.ctx, ast.Load):
            uses[node.id] += 1
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            c = _norm(node.value)
            if "lint_ignore" in c:
                issues.append(_issue("conformance_static", f"line {node.lineno}: lint_ignore is not allowed in generated scripts"))
            for text, use in expected.items():
                if c == text or (len(text) >= 4 and text in c):
                    if (node.lineno, text) not in flagged:
                        flagged.add((node.lineno, text))
                        issues.append(_issue("conformance_static",
                                             f"line {node.lineno}: hand-typed text {text[:60]!r}; use {use}"))
        if (isinstance(node, ast.Attribute) and node.attr == "lint_ignore") or (isinstance(node, ast.Name) and node.id == "lint_ignore"):
            issues.append(_issue("conformance_static", f"line {node.lineno}: lint_ignore is not allowed in generated scripts"))
    for name, n in uses.items():
        if n == 0 and isinstance(defs.get(name), (dict, list)):
            issues.append(_issue("conformance_static", f"{name} is defined but never used; every label/banner must come from it"))
    return issues


# ------------------------------------------------------------ dynamic
def _bbox_dist(p, b):
    dx = max(b[0] - p[0], 0.0, p[0] - b[2])
    dy = max(b[1] - p[1], 0.0, p[1] - b[3])
    return math.hypot(dx, dy)


def _inside(outer, inner, tol=TOL_IN):
    return (outer[0] - tol <= inner[0] and outer[1] - tol <= inner[1]
            and outer[2] + tol >= inner[2] and outer[3] + tol >= inner[3])


def _chains(units):
    """Join touching connector segments into wires: [{s, e, tip_s, tip_e, names}]."""
    segs = []
    for u in units:
        tips = u.get("tips", [False, False])
        n = len(u.get("segs", []))
        for i, s in enumerate(u.get("segs", [])):
            segs.append({"s": s[:2], "e": s[2:], "tip_s": bool(tips[0]) if i == 0 else False,
                         "tip_e": bool(tips[1]) if i == n - 1 else False, "names": [u["name"]]})
    changed = True
    while changed:
        changed = False
        for a in segs:
            for b in segs:
                if a is not b and math.dist(a["e"], b["s"]) <= TOL_JOIN:
                    a.update({"e": b["e"], "tip_e": b["tip_e"], "names": a["names"] + b["names"]})
                    segs.remove(b)
                    changed = True
                    break
            if changed:
                break
    return segs


def _richest(snaps):
    return max(range(len(snaps)), key=lambda i: (sum(1 for u in snaps[i]["units"] if not u.get("transient")), i))


def locate_blocks(snaps: list, spec: dict, layout: dict | None = None):
    """Map every spec block id to the box of the thing drawn with its label.

    A real diagram can repeat a name (Earlgrey draws 'Pinmux' once per power domain), and Manim's Text.text
    drops spaces, so 'TL-UL Crossbar' and 'TL-UL Cross bar' read the same here as well. When several spec
    blocks share a drawn name, they are told apart by position: the reference boxes (layout) are in the same
    left-to-right / top-to-bottom order as the drawing. -> (block_box, issues, seen)
    """
    issues: list[dict] = []
    seen: dict[str, tuple[int, dict]] = {}          # normalized text -> (latest snapshot index, text unit)
    for si, snap in enumerate(snaps):
        for u in snap["units"]:
            if u["kind"] == "text":
                seen[_norm(u.get("text", ""))] = (si, u)

    def owner_box(si, t):
        """The block (or region) a piece of text belongs to."""
        snap = snaps[si]
        by_id = {u["id"]: u for u in snap["units"]}
        owner = by_id.get(t.get("owner"))
        if owner and owner["kind"] in ("block", "container"):
            return owner["bbox"], owner
        cx, cy = (t["bbox"][0] + t["bbox"][2]) / 2, (t["bbox"][1] + t["bbox"][3]) / 2
        for u in snap["units"]:
            if u["kind"] in ("block", "container", "shape") and u["bbox"][0] <= cx <= u["bbox"][2]                     and u["bbox"][1] <= cy <= u["bbox"][3]:
                return u["bbox"], u
        return t["bbox"], None

    def candidates(label):
        hit = seen.get(_norm(label))
        if not hit:
            return []
        si = hit[0]
        out, boxes = [], set()
        for u in snaps[si]["units"]:
            if u["kind"] == "text" and _norm(u.get("text", "")) == _norm(label):
                box, _unit = owner_box(si, u)
                if tuple(box) not in boxes:
                    boxes.add(tuple(box))
                    out.append(box)
        return out

    block_box: dict[str, list] = {}
    by_label: dict[str, list] = {}
    for b in spec.get("blocks") or []:
        by_label.setdefault(_norm(b["label"]), []).append(b)
    for _norm_label, group in by_label.items():
        found = candidates(group[0]["label"])
        if not found:
            for b in group:
                issues.append(_issue("conformance_block",
                                     f"block {b['id']!r}: no text with the exact label {b['label']!r} is drawn"))
            continue
        if len(group) == 1 or len(found) < len(group) or not layout:
            for b in group:
                block_box[b["id"]] = found[0]
            if len(group) > 1 and len(found) < len(group):
                issues.append(_issue("conformance_block", f"{len(group)} blocks are named {group[0]['label']!r} "
                                                          f"but only {len(found)} are drawn"))
            continue
        ref = layout.get("blocks", {})
        order = sorted(group, key=lambda b: (ref.get(b["id"], [0, 0])[0], ref.get(b["id"], [0, 0])[1]))
        drawn = sorted(found, key=lambda bb: (bb[0], -bb[3]))      # scene y grows upwards, image y downwards
        for b, bb in zip(order, drawn):
            block_box[b["id"]] = bb
    return block_box, issues, seen


def check_dynamic(result: dict, spec: dict, layout: dict | None = None) -> list[dict]:
    snaps = result.get("snapshots") or []
    if not snaps:
        return []
    labels, banners = labels_and_banners(spec)
    rich = snaps[_richest(snaps)]
    block_box, issues, seen = locate_blocks(snaps, spec, layout)

    # blocks drawn that the spec does not have
    want = {_norm(v) for v in labels.values()} | {_norm(b) for b in banners}
    for u in rich["units"]:
        if u["kind"] == "block" and not u.get("transient"):
            own = [t for t in rich["units"] if t["kind"] == "text" and t.get("owner") == u["id"]]
            if not any(_norm(t.get("text", "")) in want for t in own):
                issues.append(_issue("conformance_extra", f"block {u['name']!r} at {u['bbox']} is not in the spec"
                                     + (f" (text: {own[0]['text']!r})" if own else "")))

    def find_region(label):
        """Smallest region-like shape (not a banner/block) that holds the label, allowing a label just above its top edge."""
        hit = seen.get(_norm(label))
        if not hit:
            return None
        si, t = hit
        by_id = {u["id"]: u for u in snaps[si]["units"]}
        owner = by_id.get(t.get("owner"))
        if owner and owner["kind"] == "container":        # the title belongs to its region box: use that box
            return owner["bbox"]
        cx, cy = (t["bbox"][0] + t["bbox"][2]) / 2, (t["bbox"][1] + t["bbox"][3]) / 2
        tarea = max((t["bbox"][2] - t["bbox"][0]) * (t["bbox"][3] - t["bbox"][1]), 1e-6)
        best = None
        for u in snaps[si]["units"]:
            if u["kind"] in ("container", "shape") and u["cls"] in REGION_CLASSES:
                b = u["bbox"]
                area = (b[2] - b[0]) * (b[3] - b[1])
                if area > 4 * tarea and b[0] - 0.6 <= cx <= b[2] + 0.6 and b[1] - 0.6 <= cy <= b[3] + 0.6:
                    if best is None or area < best[0]:
                        best = (area, b)
        return best[1] if best else None

    # domains
    for d in spec.get("domains") or []:
        lab = labels[f"domain_{d['id']}"]
        box = find_region(lab)
        if box is None:
            issues.append(_issue("conformance_domain", f"domain {d['id']!r}: label {lab!r} is not drawn on or just above a region"))
            continue
        members = set(d.get("contains") or [])
        external = {b["id"] for b in spec.get("blocks") or [] if b.get("role") == "external"}
        for m in members:
            if m in block_box and not _inside(box, block_box[m]):
                issues.append(_issue("conformance_domain", f"domain {d['id']!r} ({lab}) does not fully contain block {m!r}"))
        for bid, bb in block_box.items():
            if bid not in members and bid not in external and _inside(box, bb):
                issues.append(_issue("conformance_domain", f"block {bid!r} is drawn inside domain {d['id']!r} but is not a member"))

    # connections: assign wires to spec connections all at once (minimum total distance), so close-together wires
    # cannot be taken by the wrong connection
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    chains = _chains([u for u in rich["units"] if u["kind"] == "connector" and not u.get("transient")])
    used: set[int] = set()
    slots = []                                              # (connection, copy number)
    for c in spec.get("connections") or []:
        a, b = c["from"].split(".")[0], c["to"].split(".")[0]
        if a not in block_box or b not in block_box:
            issues.append(_issue("conformance_connection", f"connection {c['id']!r} ({a} -> {b}): an end block is not drawn"))
            continue
        for k in range(int(c.get("count", 1))):
            slots.append(c)
    BIG = 1e6
    cost = np.full((len(slots), max(len(chains), 1)), BIG)
    detail = {}
    for si, c in enumerate(slots):
        a, b = c["from"].split(".")[0], c["to"].split(".")[0]
        want_dir, unconf = c.get("direction", "forward"), bool(c.get("unconfirmed"))
        for i, ch in enumerate(chains):
            for flip in (False, True):
                p, q = (ch["s"], ch["e"]) if not flip else (ch["e"], ch["s"])
                head_a, head_b = (ch["tip_s"], ch["tip_e"]) if not flip else (ch["tip_e"], ch["tip_s"])
                da, db = _bbox_dist(p, block_box[a]), _bbox_dist(q, block_box[b])
                if da <= TOL_END and db <= TOL_END:
                    right = unconf or {"forward": head_b and not head_a, "both": head_a and head_b,
                                       "none": not head_a and not head_b}[want_dir]
                    cst = da + db + (0 if right else 0.05)      # wrong arrowheads still match, at a small penalty
                    if cst < cost[si, i]:
                        cost[si, i] = cst
                        detail[(si, i)] = (right, head_a, head_b)
    if slots and chains:
        rows, cols = linear_sum_assignment(cost)
        matched = {r: cc for r, cc in zip(rows, cols) if cost[r, cc] < BIG / 2}
    else:
        matched = {}
    for si, c in enumerate(slots):
        a, b = c["from"].split(".")[0], c["to"].split(".")[0]
        if si not in matched:
            if not any(x is c for x in slots[:si]) or True:
                issues.append(_issue("conformance_connection", f"connection {c['id']!r}: no wire is drawn from {a} to {b}"))
            continue
        i = matched[si]
        used.add(i)
        right, head_a, head_b = detail[(si, i)]
        if not right:
            want_dir = c.get("direction", "forward")
            expect = {"forward": "a head at the end only", "both": "heads at both ends", "none": "no arrowheads"}[want_dir]
            issues.append(_issue("conformance_connection",
                                 f"connection {c['id']!r} ({a} -> {b}): wrong arrowheads; expected {expect}; "
                                 f"drawn: head at {a} = {head_a}, head at {b} = {head_b}"))
    for c in spec.get("connections") or []:
        if c.get("label") and _norm(labels[f"conn_{c['id']}"]) not in seen:
            issues.append(_issue("conformance_connection", f"connection {c['id']!r}: label {c['label']!r} is not drawn"))
    for i, ch in enumerate(chains):
        if i not in used:
            def near(pt):
                return min(block_box, key=lambda k: _bbox_dist(pt, block_box[k])) if block_box else "?"
            issues.append(_issue("conformance_extra", f"wire from near {near(ch['s'])!r} to near {near(ch['e'])!r} is not in the spec"))

    # banners (all, in order) and packet/state text
    last = -1
    for k, bn in enumerate(banners):
        hit = None
        for si, snap in enumerate(snaps):
            if any(u["kind"] == "text" and _norm(u.get("text", "")) == _norm(bn) for u in snap["units"]):
                hit = si
                break
        if hit is None:
            issues.append(_issue("conformance_banner", f"step {k + 1}: banner {bn[:60]!r} is never shown"))
        else:
            if hit < last:
                issues.append(_issue("conformance_banner", f"step {k + 1}: banner appears before the previous step's banner"))
            last = max(last, hit)
    for key, val in labels.items():
        if key.startswith(("packet_", "state_")) and _norm(val) not in seen:
            issues.append(_issue("conformance_sequence", f"{key.split('_')[0]} text {val!r} (step {key.split('_')[1]}) is never shown"))
    return issues


def check(script_text: str, result: dict, spec: dict, layout: dict | None = None) -> list[dict]:
    return check_static(script_text, spec) + check_dynamic(result, spec, layout)
