# IPMotion v3: Progress

| Milestone | Scope | Status |
|---|---|---|
| M0 | Housekeeping: git, .gitignore, scipy mock removal, MANIFEST, pytest, docs | Done (2026-10-03) |
| M1 | A (port API) + C (geometric lint) + tests | **Done** (2026-10-03) |
| M2 | B (STYLE.md + style.toml layout conventions) | Next |
| M3 | F (LLM layer) + G (run logging) | Pending |
| M4 | E (ordered repair loop) | Pending |
| M5 | D (vision critique, behind a flag) | Pending |
| M6 | H (approve CLI + incremental indexing; indexer must read MANIFEST.toml) | Pending |

## M1 summary
**Port API** (`ipmotion_lib.py`, additive):
- `Port` is an invisible Dot with `.name`, `.side` (outward LEFT/RIGHT/UP/DOWN vector) and `.owner`.
- `PortMixin` gives `port(name)`, `ports()` (declared only), `implicit_ports()` and `port_names`.
- `IPBlock(ports=[{label, edge, name?}])` creates real ports, spread evenly along the edge. With one port per edge, label positions are unchanged from v2.
- Every `IPBlock` also has reserved implicit ports `_left/_right/_top/_bottom`. Declared names starting with `_` or duplicated are rejected. `port()` errors list declared and implicit ports separately.
- `HWComponent` pins are now `Port`s with inferred sides. `.pins` and `get_pin()` are unchanged. `BusBar` and `CustomMacro` pass explicit sides.
- `Connection(src_port, dst_port, style="manhattan"|"direct")` routes orthogonally: straight, Z, around, U-turn and corner cases. It subclasses `ManhattanRoute`, so `.transfer()` still works.
- Backward compat is verified against golden geometry recorded from the M0 library (`tests/fixtures/lib_v2_golden.json`): all 41 symbol/block bounding boxes and every pin position are identical to 1e-6.
- **Bug fixed:** `Banner.update_text` drew the banner background over its new text (dim text in every gold example that uses it).

**Lint** (`python -m ipmotion.lint <script> [Scene] [--json out.json]`; package `ipmotion/lint/`):
- `worker.py` runs the scene in a subprocess without rendering and snapshots after every `play()`/`wait()` (plus a final snapshot). Objects are named from `construct()` locals. Each issue records scene time and source line.
- `snapshot.py` extracts plain data, `checks.py` holds the checks, `report.py` dedupes across snapshots and builds JSON.
- Checks: `text_overlap`, `text_occluded`, `dangling_endpoint`, `out_of_frame`, `min_spacing`, `min_text_size`. Thresholds live in `ipmotion/style.toml [lint]`.
- Opt-out: `mob.lint_ignore = ["text_overlap"]` (or `"all"`) on the object or any ancestor. The issue is reported as severity `info`, `ignored: true`.
- A script crash is reported as a `runtime_error` issue, with the snapshots taken before it.

**Baselines and fixtures**
- `axi_read_handshake` lints with 0 errors. Accepted warnings: blocks sit 0.08 from the frame edge, and the banner is wider than the frame (full-bleed bar).
- 6 broken AXI copies in `tests/fixtures/broken/`, each caught by its intended check: label_overlap, dangling_wire, off_frame, tiny_text, block_overlap, banner_occluded (the last uses a frozen copy of the legacy Banner).
- `symbol_showcase` reports the off-frame banner and about 40 tiny labels. `darjeeling_full` reports block overlaps and hidden text.

**Regression frames (before/after the library changes):** `symbol_showcase` is pixel-identical. `axi_read_handshake` and `darjeeling_full` changed only inside the banner text strip (the Banner fix). The three broken gold examples fail exactly as before (NameError for missing classes).

## Known limits
- **Lint snapshots end states only.** Mid-animation overlaps (a packet crossing a label during a move) aren't checked yet.
- Lint speed, wall clock including process start: AXI about 5s, Darjeeling (60 blocks) about 8s. Manim import is 1.7s per process. Scene construction (Text to SVG paths) dominates the rest, and `take_snapshot` is only 0.4–0.8s. A persistent worker would remove the import cost for the M4 repair loop.
- Manhattan `Connection` routes are geometric only; they don't avoid blocks in between. Connections are static (built at construction time).
- Many identical findings (e.g. 40 tiny labels) are separate issues; consider grouping before sending to the LLM (M4).
- `indexer.py` doesn't read `MANIFEST.toml` yet (M6). Don't re-run the v2 indexer until then.
- Threshold calibration: `min_text_cap_px_error=9`, `_warn=12` (cap height at 1080p, about 12.5px and 17px font) are chosen from legibility conventions, not tuned on AXI. AXI's smallest text measures well above them.
