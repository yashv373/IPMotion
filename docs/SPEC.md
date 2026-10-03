# IPMotion animation spec (YAML)

A spec states **intent**: what exists, how it connects, and what happens in which order.
It deliberately contains **no coordinates, sizes, or colors**. Placement, routing, fonts and pacing are the
generator's job (guided by `docs/STYLE.md` and the gold examples) and are what the linter checks.

## Top level

```yaml
title: "AXI4 Write Transaction"        # required; shown in the opening banner
layout_hint: left_to_right             # optional, see below
description: >                         # optional: one or two sentences of context for the generator
  ...
domains:      [...]                    # optional
blocks:       [...]                    # required, at least one
connections:  [...]                    # optional
sequence:     [...]                    # required, at least one step
```

### `layout_hint` (advisory, never mandatory)
| value | meaning |
|---|---|
| `left_to_right` | signal flow runs left to right; initiator/master left, target/slave right (default) |
| `top_down` | flow runs top to bottom |
| `hub_and_spoke` | one interconnect block in the middle, others around it |
| `hierarchical` | hosts on top, interconnect(s) in the middle, targets below; domains drawn as enclosing regions |

## `domains` (optional): enclosing regions such as clock or power domains
```yaml
- id: lo                       # unique, [a-z0-9_]+
  label: "Low-Speed Domain"
  contains: [peri_xbar, uart]  # block ids
```
A block belongs to at most one domain. Blocks not listed in any domain are drawn outside all domains.

## `blocks`
```yaml
- id: master                   # unique, [a-z0-9_]+, referenced everywhere else
  label: "AXI Master"          # text shown on the block (keep it short)
  role: master                 # master | slave | interconnect | memory | peripheral | logic | fifo
  ports: [AWVALID, AWREADY]    # optional named ports; a connection may attach to "master.AWVALID"
  notes: "optional free text for the generator; not drawn"
```
`role` carries meaning for layout: masters/initiators go on the flow's start side, slaves/targets on the end side,
interconnects between them. `fifo` asks for the library FIFO symbol, `logic` for a gate/small-symbol if one fits.

## `connections`
```yaml
- id: aw                       # unique; referenced by the sequence
  from: master                 # "block" or "block.PORT"
  to: slave                    # "block" or "block.PORT"
  bus: address                 # see bus types
  label: "AW (write address)"  # optional label drawn beside the wire
  direction: forward           # forward (from->to, default) | both | none
```
### `bus` types (the color/meaning vocabulary)
| bus | meaning | conventional color |
|---|---|---|
| `control` | handshake/valid/ready/enable/flags | green |
| `address` | address / request channel | green |
| `data` | data / payload / response data | blue |
| `response` | status / acknowledge / completion | blue |
| `clock` / `reset` | clocking / reset | muted gray |
| `irq` | interrupts / alerts | red |
| `tl_ul` | TileLink-UL bus segments (request on A, response on D) | cyan |
The active/highlighted state is yellow, inactive is gray (these are *sequence* states, not bus types).

## `sequence`: the story, one `step` per banner
```yaml
- banner: "Cycle 1: Master asserts AWVALID with AWADDR=0x1000"   # required, shown in the banner
  activate: [aw]                # connection ids lit up (active color) during this step
  highlight: [master]           # block ids highlighted during this step
  packets:                      # optional: labelled tokens that travel along a connection
    - {conn: aw, label: "AWADDR=0x1000"}            # kind defaults to request
    - {conn: aw, label: "response", kind: response}  # response packets are drawn in a distinct color
  state:                        # optional: text/state changes inside blocks (e.g. FIFO contents, FSM state)
    - {block: fifo, value: "A B - -"}
  hold: 0.5                     # optional seconds to pause after the step (default 0.5)
```
`kind` is `request` (default) or `response`. Response packets must be visually distinct from requests (different color, label printed on the packet), so a response travelling against a one-way arrow does not look like a wrong arrow.
Steps run in order. Anything not mentioned returns to the inactive state at the start of each step
(a step describes the *whole* highlighted picture, not a delta).

## Validation rules (a spec that breaks these is rejected before generation)
- `direction` is forward | both | none (none = no arrowhead)
- a spec with `source: <truth name>` (bench/truth/<name>.yaml) may only use truth block ids with their exact labels; every connection needs `truth: <connection id>`, matching its from/to and arrow direction; blocks or connections marked `unclear` in the truth file are rejected
- ids unique and `[a-z0-9_]+`; every reference (domain `contains`, connection `from`/`to`, sequence ids) resolves
- `block.PORT` references must name a port declared on that block
- `bus` must be one of the listed types; `role` and `layout_hint` likewise
- every sequence step has a non-empty `banner`
- a block may be in several domains only if they are nested (`parent:` chain); `scope: full` specs must contain every truth block/connection (items the truth file marks `unclear` must say `unconfirmed: true` and may not be used in the story)

## What a spec does NOT say (on purpose)
Coordinates, sizes, colors, font sizes, run times, wire routing, z-order. If a spec needs these to come out right,
that is a generator or linter gap to measure, not something to paper over in the spec.
