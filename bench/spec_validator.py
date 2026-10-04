"""Validate a benchmark spec (docs/SPEC.md). python bench/spec_validator.py bench/specs/*.yaml

Generic rules, plus: a spec with `source: <truth name>` may only use blocks, labels and connections that
exist in bench/truth/<truth name>.yaml, must not use anything marked `unclear`, and must not invent arrow
directions.  Block ids must equal truth block ids; every connection names its truth connection via `truth:`.
"""
from __future__ import annotations

import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ID = re.compile(r"^[a-z0-9_]+$")
ROLES = {"master", "slave", "interconnect", "memory", "peripheral", "logic", "fifo", "external"}
BUSES = {"control", "address", "data", "response", "clock", "reset", "irq", "tl_ul"}
HINTS = {"left_to_right", "top_down", "hub_and_spoke", "hierarchical"}
DIRECTIONS = {"forward", "both", "none"}


def _ref(r):
    return r.split(".", 1)[0], (r.split(".", 1)[1] if "." in r else None)


def validate(spec: dict) -> list[str]:
    errs: list[str] = []
    blocks = spec.get("blocks") or []
    conns = spec.get("connections") or []
    seq = spec.get("sequence") or []
    if not spec.get("title"):
        errs.append("title is required")
    if spec.get("layout_hint") and spec["layout_hint"] not in HINTS:
        errs.append(f"layout_hint {spec['layout_hint']!r} not in {sorted(HINTS)}")
    if not blocks:
        errs.append("at least one block is required")
    if not seq:
        errs.append("at least one sequence step is required")

    bids = [b.get("id") for b in blocks]
    cids = [c.get("id") for c in conns]
    for kind, ids in (("block", bids), ("connection", cids)):
        for i in ids:
            if not isinstance(i, str) or not ID.match(i):
                errs.append(f"{kind} id {i!r} must match [a-z0-9_]+")
        for i in {x for x in ids if ids.count(x) > 1}:
            errs.append(f"duplicate {kind} id {i!r}")
    ports = {b["id"]: set(b.get("ports") or []) for b in blocks if "id" in b}
    for b in blocks:
        if b.get("role") not in ROLES:
            errs.append(f"block {b.get('id')!r}: role {b.get('role')!r} not in {sorted(ROLES)}")
        if not b.get("label") and "label" not in b:
            # a full-diagram spec may carry label: null for a box the reference draws with no text
            errs.append(f"block {b.get('id')!r}: label is required")

    dom_parent = {d.get("id"): d.get("parent") for d in spec.get("domains") or []}

    def ancestors(did):
        out, p = set(), dom_parent.get(did)
        while p and p not in out:
            out.add(p)
            p = dom_parent.get(p)
        return out

    seen_dom: dict[str, list[str]] = {}
    dids = [d.get("id") for d in spec.get("domains") or []]
    for d in spec.get("domains") or []:
        if d.get("parent") and d["parent"] not in dids:
            errs.append(f"domain {d.get('id')!r}: unknown parent {d['parent']!r}")
        for m in d.get("contains") or []:
            if m not in ports:
                errs.append(f"domain {d.get('id')!r} contains unknown block {m!r}")
            else:
                for other in seen_dom.get(m, []):
                    if other not in ancestors(d.get("id")) and d.get("id") not in ancestors(other):
                        errs.append(f"block {m!r} is in two domains that are not nested ({other!r}, {d.get('id')!r})")
                seen_dom.setdefault(m, []).append(d.get("id"))
    for i in {x for x in dids if dids.count(x) > 1}:
        errs.append(f"duplicate domain id {i!r}")

    for c in conns:
        for end in ("from", "to"):
            blk, port = _ref(str(c.get(end, "")))
            if blk not in ports:
                errs.append(f"connection {c.get('id')!r}: unknown block {blk!r} in {end}")
            elif port and port not in ports[blk]:
                errs.append(f"connection {c.get('id')!r}: block {blk!r} has no port {port!r}")
        if c.get("bus") not in BUSES:
            errs.append(f"connection {c.get('id')!r}: bus {c.get('bus')!r} not in {sorted(BUSES)}")
        if c.get("direction", "forward") not in DIRECTIONS:
            errs.append(f"connection {c.get('id')!r}: direction must be one of {sorted(DIRECTIONS)}")

    for n, s in enumerate(seq, 1):
        if not str(s.get("banner", "")).strip():
            errs.append(f"sequence step {n}: banner is required")
        for x in s.get("activate") or []:
            if x not in cids:
                errs.append(f"sequence step {n}: unknown connection {x!r}")
        for x in s.get("highlight") or []:
            if x not in ports:
                errs.append(f"sequence step {n}: unknown block {x!r}")
        for p in s.get("packets") or []:
            if p.get("conn") not in cids:
                errs.append(f"sequence step {n}: packet on unknown connection {p.get('on')!r}")
        for st in s.get("state") or []:
            if st.get("block") not in ports:
                errs.append(f"sequence step {n}: state on unknown block {st.get('block')!r}")

    if spec.get("source"):
        errs += _check_against_truth(spec, blocks, conns)
    return errs


def _check_against_truth(spec, blocks, conns) -> list[str]:
    errs: list[str] = []
    name = spec["source"]
    path = os.path.join(ROOT, "bench", "truth", f"{name}.yaml")
    if not os.path.exists(path):
        return [f"source {name!r}: no such truth file bench/truth/{name}.yaml"]
    with open(path, encoding="utf-8") as fh:
        truth = yaml.safe_load(fh)
    tb = {b["id"]: b for b in truth["blocks"]}
    tb.update({e["id"]: e for e in truth.get("externals", [])})
    tc = {c["id"]: c for c in truth["connections"]}
    full = spec.get("scope") == "full"
    if spec.get("scope") not in (None, "subset", "full"):
        errs.append("scope must be 'subset' (default) or 'full'")
    parent = {r["id"]: r.get("parent") for r in truth["regions"]}

    def in_region(block_id, region_id):
        b = tb.get(block_id, {})
        reg = b.get("region")
        if reg is None and b.get("inside"):
            reg = tb.get(b["inside"], {}).get("region")
        while reg:
            if reg == region_id:
                return True
            reg = parent.get(reg)
        return False

    for b in blocks:
        t = tb.get(b.get("id"))
        if t is None:
            errs.append(f"block {b.get('id')!r} is not in truth file {name} (ids must equal truth ids)")
            continue
        if b.get("label") != t["label"]:
            errs.append(f"block {b['id']!r}: label {b.get('label')!r} != truth label {t['label']!r}")
        if "unclear" in t and not (full and b.get("unconfirmed")):
            errs.append(f"block {b['id']!r} is marked unclear in the truth file: {t['unclear']}"
                        + ("" if not full else " (in a full spec it must be marked unconfirmed: true)"))
        if full and b.get("unconfirmed") and "unclear" not in t:
            errs.append(f"block {b['id']!r} is marked unconfirmed but the truth file does not mark it unclear")
    for d in spec.get("domains") or []:
        regions = {r["id"]: r["label"] for r in truth["regions"]}
        if d.get("id") not in regions:
            errs.append(f"domain {d.get('id')!r} is not a region in the truth file")
        elif d.get("label") != regions[d["id"]]:
            errs.append(f"domain {d['id']!r}: label {d.get('label')!r} != truth label {regions[d['id']]!r}")
        else:
            for m in d.get("contains") or []:
                if not in_region(m, d["id"]):
                    errs.append(f"domain {d['id']!r} contains {m!r} but the truth region of {m!r} is {tb.get(m, {}).get('region')!r}")
            if full:
                want = {b["id"] for b in truth["blocks"] if in_region(b["id"], d["id"])}
                missing = sorted(want - set(d.get("contains") or []))
                if missing:
                    errs.append(f"domain {d['id']!r} is missing members {missing[:6]}")
    for c in conns:
        tid = c.get("truth")
        t = tc.get(tid)
        if t is None:
            errs.append(f"connection {c.get('id')!r}: needs `truth: <connection id from {name}.yaml>` (got {tid!r})")
            continue
        if "unclear" in t and not (full and c.get("unconfirmed")):
            errs.append(f"connection {c['id']!r} uses truth {tid} which is marked unclear: {t['unclear']}"
                        + ("" if not full else " (in a full spec it must be marked unconfirmed: true)"))
        a, b = str(c["from"]), str(c["to"])
        directed = t.get("directed", True) and t.get("heads") != "none"
        if (a, b) != (str(t["from"]), str(t["to"])) and not ((b, a) == (str(t["from"]), str(t["to"])) and not directed):
            errs.append(f"connection {c['id']!r}: {a}->{b} does not match truth {tid} ({t['from']}->{t['to']})")
        want = {"to": "forward", "both": "both", "none": "none"}[t["heads"]]
        if c.get("direction", "forward") != want:
            errs.append(f"connection {c['id']!r}: direction {c.get('direction', 'forward')!r} but truth {tid} has heads={t['heads']} (expected {want!r})")
    if full:
        have_b = {b.get("id") for b in blocks}
        have_c = {c.get("truth") for c in conns}
        miss_b = sorted((set(tb) - have_b))
        miss_c = sorted(set(tc) - have_c)
        if miss_b:
            errs.append(f"full spec is missing {len(miss_b)} truth blocks/externals, e.g. {miss_b[:5]}")
        if miss_c:
            errs.append(f"full spec is missing {len(miss_c)} truth connections, e.g. {miss_c[:5]}")
        unconf_b = {b["id"] for b in blocks if b.get("unconfirmed")}
        unconf_c = {c["id"] for c in conns if c.get("unconfirmed")}
        for n, st in enumerate(spec.get("sequence") or [], 1):
            for x in (st.get("highlight") or []):
                if x in unconf_b:
                    errs.append(f"sequence step {n}: block {x!r} is unconfirmed and may not be used in a story")
            for x in (st.get("activate") or []):
                if x in unconf_c:
                    errs.append(f"sequence step {n}: connection {x!r} is unconfirmed and may not be used in a story")
            for pk in (st.get("packets") or []):
                if pk.get("conn") in unconf_c:
                    errs.append(f"sequence step {n}: packet on unconfirmed connection {pk.get('conn')!r}")
    return errs


if __name__ == "__main__":
    bad = 0
    for f in sys.argv[1:]:
        with open(f, encoding="utf-8") as fh:
            e = validate(yaml.safe_load(fh))
        print(("OK   " if not e else "FAIL ") + f)
        for x in e:
            print("   -", x)
        bad += bool(e)
    sys.exit(1 if bad else 0)
