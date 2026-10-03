"""Build a FULL-diagram spec from a truth file + a short story.

The story only says what should happen (title, steps using truth ids). Every block, region and connection of the
reference diagram is added automatically, with its exact label and arrow direction. Items the truth file marks
`unclear` are included as `unconfirmed: true` (drawn in a marked style, never used by the story).

    story = load_story("bench/stories/darjeeling_ibex_uart_read.yaml")
    spec  = make_full_spec(story)
"""
from __future__ import annotations

import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_story(path: str) -> dict:
    with open(path if os.path.isabs(path) else os.path.join(ROOT, path), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _descendants(regions: list[dict]) -> dict[str, set[str]]:
    kids: dict[str, set[str]] = {r["id"]: {r["id"]} for r in regions}
    parent = {r["id"]: r.get("parent") for r in regions}
    for r in regions:
        p = parent[r["id"]]
        while p:
            kids[p].add(r["id"])
            p = parent[p]
    return kids


def make_full_spec(story: dict) -> dict:
    with open(os.path.join(ROOT, "bench", "truth", f"{story['source']}.yaml"), encoding="utf-8") as fh:
        truth = yaml.safe_load(fh)
    with open(os.path.join(ROOT, "bench", "truth", f"{story['source']}.layout.yaml"), encoding="utf-8") as fh:
        layout = yaml.safe_load(fh)

    ports: dict[str, list[str]] = {}
    for c in truth["connections"]:
        for end in (c["from"], c["to"]):
            if "." in str(end):
                b, p = str(end).split(".", 1)
                ports.setdefault(b, [])
                if p not in ports[b]:
                    ports[b].append(p)

    blocks = []
    for b in truth["blocks"]:
        d = {"id": b["id"], "label": b["label"], "role": "logic"}
        if b["id"] in ports:
            d["ports"] = ports[b["id"]]
        if "unclear" in b:
            d["unconfirmed"] = True
        blocks.append(d)
    for e in truth.get("externals", []):
        blocks.append({"id": e["id"], "label": e["label"], "role": "external"})

    sub = _descendants(truth["regions"])
    domains = []
    for r in truth["regions"]:
        members = [b["id"] for b in truth["blocks"] if b.get("region") in sub[r["id"]] or b.get("inside") and
                   next((x.get("region") for x in truth["blocks"] if x["id"] == b["inside"]), None) in sub[r["id"]]]
        d = {"id": r["id"], "label": r["label"], "contains": members}
        if r.get("parent"):
            d["parent"] = r["parent"]
        domains.append(d)

    conns = []
    for c in truth["connections"]:
        d = {"id": c["id"], "truth": c["id"], "from": c["from"], "to": c["to"], "bus": "tl_ul",
             "direction": {"to": "forward", "both": "both", "none": "none"}[c["heads"]]}
        multi = layout["routes"].get(c["id"], {}).get("multi")
        if multi:
            d["count"] = len(multi)
        if "printed_label" in c and c["printed_label"] != "...":
            d["label"] = c["printed_label"]
        if "unclear" in c:
            d["unconfirmed"] = True
        conns.append(d)

    return {"source": story["source"], "scope": "full", "title": story["title"],
            "layout_hint": "hierarchical", "description": story.get("description", ""),
            "domains": domains, "blocks": blocks, "connections": conns, "sequence": story["sequence"]}


def write_spec(story_path: str, out_path: str) -> dict:
    spec = make_full_spec(load_story(story_path))
    with open(out_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(spec, fh, sort_keys=False, allow_unicode=True, width=120)
    return spec
