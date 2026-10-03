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
ROLES = {"master", "slave", "interconnect", "memory", "peripheral", "logic", "fifo"}
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
        if not b.get("label"):
            errs.append(f"block {b.get('id')!r}: label is required")

    seen_dom: dict[str, str] = {}
    dids = [d.get("id") for d in spec.get("domains") or []]
    for d in spec.get("domains") or []:
        for m in d.get("contains") or []:
            if m not in ports:
                errs.append(f"domain {d.get('id')!r} contains unknown block {m!r}")
            elif m in seen_dom:
                errs.append(f"block {m!r} is in two domains ({seen_dom[m]!r}, {d.get('id')!r})")
            seen_dom[m] = d.get("id")
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

    for b in blocks:
        t = tb.get(b.get("id"))
        if t is None:
            errs.append(f"block {b.get('id')!r} is not in truth file {name} (ids must equal truth ids)")
            continue
        if b.get("label") != t["label"]:
            errs.append(f"block {b['id']!r}: label {b.get('label')!r} != truth label {t['label']!r}")
        if "unclear" in t:
            errs.append(f"block {b['id']!r} is marked unclear in the truth file: {t['unclear']}")
    for d in spec.get("domains") or []:
        regions = {r["id"]: r["label"] for r in truth["regions"]}
        if d.get("id") not in regions:
            errs.append(f"domain {d.get('id')!r} is not a region in the truth file")
        elif d.get("label") != regions[d["id"]]:
            errs.append(f"domain {d['id']!r}: label {d.get('label')!r} != truth label {regions[d['id']]!r}")
        else:
            for m in d.get("contains") or []:
                real = tb.get(m, {}).get("region")
                # a block belongs to the domain if its truth region is that domain
                if real != d["id"]:
                    errs.append(f"domain {d['id']!r} contains {m!r} but the truth region of {m!r} is {real!r}")
    for c in conns:
        tid = c.get("truth")
        t = tc.get(tid)
        if t is None:
            errs.append(f"connection {c.get('id')!r}: needs `truth: <connection id from {name}.yaml>` (got {tid!r})")
            continue
        if "unclear" in t:
            errs.append(f"connection {c['id']!r} uses truth {tid} which is marked unclear: {t['unclear']}")
        a, b = _ref(str(c["from"]))[0], _ref(str(c["to"]))[0]
        directed = t.get("directed", True) and t.get("heads") != "none"
        if (a, b) != (t["from"], t["to"]) and not ((b, a) == (t["from"], t["to"]) and not directed):
            errs.append(f"connection {c['id']!r}: {a}->{b} does not match truth {tid} ({t['from']}->{t['to']})")
        want = {"to": "forward", "both": "both", "none": "none"}[t["heads"]]
        if c.get("direction", "forward") != want:
            errs.append(f"connection {c['id']!r}: direction {c.get('direction', 'forward')!r} but truth {tid} has heads={t['heads']} (expected {want!r})")
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
