"""How close is a render to the reference picture? Numbers in plain terms, from the lint snapshots.

  blocks     how many reference blocks are drawn with their exact label
  regions    how many regions are drawn with the right label and the right members
  wires      how many CONFIRMED reference connections are drawn between the right blocks with the right arrowheads
  extras     things drawn that the reference does not have
  layout     how often a pair of blocks keeps the reference's left/right and above/below order
  unconfirmed  items the reference notes are not sure about (drawn in a marked style, listed for review)
"""
from __future__ import annotations

import collections

from ipmotion import conformance as C


def _locate(snaps, spec, layout=None):
    """block id -> bbox of the box that holds its label (same mapping the conformance check uses, so blocks
    that share a name are told apart the same way)."""
    return C.locate_blocks(snaps, spec, layout)[0]


def score(result: dict, spec: dict, layout: dict) -> dict:
    snaps = result.get("snapshots") or []
    issues = C.check_dynamic(result, spec, layout) if snaps else []
    by = collections.Counter(i["check"] for i in issues)
    blocks = spec.get("blocks") or []
    conns = spec.get("connections") or []
    conf_conns = [c for c in conns if not c.get("unconfirmed")]
    wires_total = sum(int(c.get("count", 1)) for c in conf_conns)
    bad_conf_ids = set()
    for i in issues:
        if i["check"] == "conformance_connection":
            # detail starts with "connection 'cNN'"
            try:
                bad_conf_ids.add(i["detail"].split("'")[1])
            except IndexError:
                pass
    wires_bad = sum(int(c.get("count", 1)) for c in conf_conns if c["id"] in bad_conf_ids)
    domains = spec.get("domains") or []
    bad_dom = {i["detail"].split("'")[1] for i in issues if i["check"] == "conformance_domain" and "'" in i["detail"]}
    located = _locate(snaps, spec, layout) if snaps else {}

    # layout agreement: left/right and above/below order of every pair of drawn blocks, vs the reference pixels
    px = {k: ((v[0] + v[2]) / 2, (v[1] + v[3]) / 2) for k, v in layout["blocks"].items()}
    ids = [b["id"] for b in blocks if b["id"] in located and b["id"] in px and b.get("role") != "external"]
    agree = total = 0
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            (xa, ya), (xb, yb) = px[ids[a]], px[ids[b]]
            ra, rb = located[ids[a]], located[ids[b]]
            cxa, cya, cxb, cyb = (ra[0] + ra[2]) / 2, (ra[1] + ra[3]) / 2, (rb[0] + rb[2]) / 2, (rb[1] + rb[3]) / 2
            for ref_d, got_d, dead_ref, dead_got in ((xb - xa, cxb - cxa, 10, 0.08), (yb - ya, -(cyb - cya), 10, 0.08)):
                if abs(ref_d) < dead_ref:
                    continue
                total += 1
                if abs(got_d) < dead_got or (ref_d > 0) == (got_d > 0):
                    agree += 1
    unconf = [{"kind": "wire", "id": c["id"], "from": c["from"], "to": c["to"], "count": c.get("count", 1)}
              for c in conns if c.get("unconfirmed")] + \
             [{"kind": "block", "id": b["id"], "label": b["label"]} for b in blocks if b.get("unconfirmed")]
    return {
        "blocks_total": len(blocks), "blocks_ok": len(blocks) - by.get("conformance_block", 0),
        "regions_total": len(domains), "regions_ok": len(domains) - len(bad_dom),
        "wires_total": wires_total, "wires_ok": wires_total - wires_bad,
        "extras": by.get("conformance_extra", 0),
        "layout_pairs": total, "layout_agree": agree,
        "layout_percent": round(100.0 * agree / total, 1) if total else None,
        "unconfirmed": unconf,
        "issues_by_check": dict(by), "issue_details": [i["detail"] for i in issues][:20],
    }
