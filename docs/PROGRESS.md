# IPMotion v3: Progress

| Milestone | Scope | Status |
|---|---|---|
| M0 | Housekeeping: git, .gitignore, scipy mock removal, MANIFEST, pytest, docs | Done (2026-10-03) |
| M1 | A (port API) + C (geometric lint) + tests | **Done** (2026-10-03) |
| M1.5 | End-to-end benchmark (spec -> animation), v2 vs v3 | **In progress**: Darjeeling run done, others pending |
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

## M1.5 benchmark status (2026-10-03)
Model for every run: `gemini-3.5-flash` (3.8-flash daily free quota was exhausted; no runs were done on it).
Truth: bench/truth/{opentitan_darjeeling,opentitan_earlgrey,opentitan_peppermint}.yaml (Peppermint awaits the user's own review). PULP is out until a block diagram exists.
Resume after a daily-quota stop: `python bench/run_all.py <spec> --reps 3` (state in runs/bench_state.json; an interrupted job restarts from scratch).
Report: `python bench/make_report.py` -> bench/report.html.

Darjeeling (darjeeling_periph_read), v2 x3 complete, v3 x2 complete (v3 run 3 interrupted by the daily quota, excluded):
- v2: all 3 rendered (own criterion) after 3/1/3 attempts; final lint errors 4 / 40 / 39; content clipped at the frame edges in all three.
- v3: run 1 passed lint at attempt 2 (0 errors); run 2 failed after 8 attempts (1 error left).
Findings: see the conversation summary; main ones below.
- Lint passing does NOT mean the animation matches the spec: no check for label/banner/connection fidelity (v3 run 2 changed 'Peri TL-UL Cross bar' and '1 x UART / 1x I2C'; banners were paraphrased in most runs).
- v3 run 2's remaining errors were min_spacing on `pkt_bg`, the travelling packet (a GlowBox) overlapping blocks/containers at an end-state snapshot. Packets are transient; the linter treats them as blocks. This false-positive class cost attempts. Not tuned away for the benchmark.
- Error counts across attempts were not monotonic (13, 4, 7, runtime, 10, 6, 5, 1); one attempt was a LLM SyntaxError.
- Harness bugs found and fixed: `rep` variable shadowing in run_v2/run_v3 (result files repaired from run order).

## M1.5 update: spec conformance + packet rules (2026-10-03, after the first Darjeeling results)
Decisions applied (user):
- Conformance (ipmotion/conformance.py): the v3 prompt starts with generated `LABELS` / `BANNERS` dicts (blocks, domains, wire labels, packet/state text, spec title, banners). Static check: dicts intact, no hand-typed label or banner text (whitespace-insensitive, so a re-wrapped label is caught), no `lint_ignore`. Dynamic check on the lint snapshots: every block/domain label drawn, domain members inside their region (and non-members not), every connection drawn with the right arrowheads, no extra blocks or wires, every banner shown in order, packet/state text shown.
- Packets are transient: `Packet` class in ipmotion_lib, and any standalone packet-sized GlowBox. Spacing/overlap/occlusion/endpoint checks skip them; out_of_frame and min_text_size still apply. Banner-sized glows are NOT packets.
- Feedback: runtime errors alone first; otherwise conformance errors, then lint errors grouped by kind/object, at most 5 items per attempt.
- Pass = 0 lint errors AND 0 conformance errors, then a render.
- Old v3 Darjeeling runs (old prompt) are excluded from the report (prompt_version 2 required). The 3 v2 runs are kept and re-scored (bench/rescore_v2.py): current lint rules + dynamic conformance only (v2 never saw the LABELS rule).
- Fixes found while building it: Text.text is stale after Transform (Banner now uses TextTransform; the lint worker syncs .text for any Transform); dashed outlines are one unit; a rectangle banner defined by the script itself is not an "extra block" (banner texts and the title are allowed).
Known limits: highlight/activate per step and packet paths are not verified; a shared bus trunk with branches would be reported as missing connections; connection tolerance 0.6 units.
Pending: re-run v3 x3 on Darjeeling once the daily quota resets (`python bench/run_all.py darjeeling_periph_read --reps 3`; v3 jobs are keyed by prompt version, so the old v3 jobs in the state file are ignored and the v2 jobs are skipped as done). Earlgrey/Peppermint runs not started.

## Decisions recorded (user, 2026-10-03)
- **Feedback order stays runtime -> spec conformance -> lint.** Spec errors are structural (missing/extra blocks, labels, domains); fixing layout before the right blocks exist is wasted work.
- **If logic checks are added later** (signal values, step order, highlight timing), they go AFTER lint, per "aesthetics before logic."
- **Known limit, kept on purpose: shared/branched bus drawing.** The per-connection check is strict: each spec connection must be its own wire. A bus drawn as one trunk with branches is reported as missing connections. We may want to allow this later; not now.
