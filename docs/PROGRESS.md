# IPMotion v3: Progress

| Milestone | Scope | Status |
|---|---|---|
| M0 | Housekeeping: git, .gitignore, scipy mock removal, MANIFEST, pytest, docs | Done (2026-10-03) |
| M1 | A (port API) + C (geometric lint) + tests | **Done** (2026-10-03) |
| M1.5 | End-to-end benchmark (spec -> animation), v2 vs v3 | **In progress**: Darjeeling run done, others pending |
| M1.6 | Whole-diagram polish + a second chip (Earlgrey) on the same engine | **Done** (2026-10-04) |
| M1.7 | Third chip (Peppermint) on the same engine | **In progress** (2026-10-04): it draws; 4 known problems open |
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

## M1.5 pivot: whole-diagram, code-drawn pipeline (v4) (2026-10-03)
Goal (user): give a reference diagram + a short story, get an animation that is overlap-free, text-clean and a 1:1 recreation of the picture (scale/colors may differ). More diagrams tried -> better RAG examples later.
Decisions (user): draw from the picture's own positions with code; the AI only writes the story. Unclear items are neither dropped nor drawn as sure lines: they are drawn amber-dashed ("unconfirmed") and listed in the report with a zoomed reference crop for the user to confirm.
Built:
- bench/truth/opentitan_darjeeling.layout.yaml: pixel boxes (detected from the image fills) + hand-read routes. `ipmotion/diagram.py` draws regions, blocks, wires, legend, step panel from truth+layout; `ipmotion/player.py` plays a story (highlight/activate/packets; response packets orange, reversed); `ipmotion/fullspec.py` builds the full spec from truth + a story (bench/stories/*.yaml); validator knows `scope: full`, nested domains, `unconfirmed`.
- `ipmotion/fidelity.py` (blocks / regions / wires / extras / left-right-above-below order / unconfirmed) and `bench/run_full.py` (writes runs/*_v4/final.json; no AI, no quota).
- Dense-diagram lint limits ([lint_full] in style.toml): text 6.5/8 px, gap 0.05; wires may end on a region border or a free label; packets/dashes handled in snapshots; conformance now assigns wires globally (min total distance).
- Library bug fixed: IPBlock title rotated 180 deg when the block was < 0.2 tall.
Result (Darjeeling, story "Ibex reads from the UART / I2C"): 49/49 blocks, 4/4 regions, 53/53 sure wires, 0 extras, 100% order agreement, 12 unconfirmed (10 wires, 2 blocks), lint errors 0, spec errors 0. CAVEAT: these compare the drawing with the hand-written notes of the picture, not with the picture; the user judges by eye (report shows reference beside render).
Known limits: three labels are as small as in the reference (warnings, not errors); text at the 25% keyframe can be caught mid-change; the notes (truth+layout) are hand-made for Darjeeling only; reading a new image automatically (vision model) and the story-from-text step (LLM) are not built; other diagrams (Earlgrey, Peppermint) have truth but no layout file yet.
Next: user reviews the report (reference vs render, and the 12 unconfirmed items); then layout files for Earlgrey/Peppermint to test the same engine on different chips; later the LLM story step and vision transcription when quota allows.

## M1.6 polish + second chip: Earlgrey (2026-10-04)
Goal (user): finish the look of the Darjeeling full-diagram render, then prove the engine repeats on another
chip. User also asked for 1920x1080 renders (the standard landscape video size).

**Polish (all in `ipmotion/diagram.py`, shared by every diagram):**
- *Text size.* Line breaks were chosen with a character-count guess that disagreed with the size the text was
  actually given, so a handful of blocks shrank far below the rest. `text_metrics()` now measures Consolas once
  (character width, line pitch, glyph height per point) and `wrap_label`/`fit_size` pick the break that really
  fits. Block titles also use `line_spacing=0.25` (new optional argument on `IPBlock`, default unchanged), so a
  3-line title is viable. Darjeeling: common size 9.8 -> 12.4, smallest 6.3 -> 7.8.
- *Margin labels* ("DMA System Egress", "IRQs & Alerts", "CTN Ingress / Egress") were tiny and clipped. They now
  have their own font size (12), are broken to ~11 characters a line, sit in a gutter left of the drawing (their
  wire leaves the drawing to reach them, as the reference shows), and are kept inside the frame.
- *Legend swatches* no longer land on letters: swatches go to free corners (top-left, then bottom-right), the
  title gives up that strip, and `_clear_markers` checks the real per-line glyph boxes afterwards.
- *Wires no longer run over blocks.* `_avoid` re-routes a wire that would cross a block that is not one of its
  own ends, through the nearest free channel, preferring the channel the reference used; nested blocks (Base Addr
  Translation inside SoC Proxy) are not treated as obstacles, margin labels are. A detour never starts where
  another wire ends (they would be read as one long wire). Darjeeling went from 8 crossings to 0.
- *Frame.* Renders are 1920x1080 at 30 fps (`bench/common.py`). The drawing is scaled to the frame height AND to
  the width left once the step panel has its minimum 4.8 units, so a landscape reference is not pushed off the
  panel; the panel, its title and its legend follow the drawing's edge. Frame margin 0.16 (above the linter's
  0.15 safe margin), so no more edge warnings.

**Earlgrey (second chip, same engine, no new drawing code):**
- `bench/truth/opentitan_earlgrey.layout.yaml`: 40 block boxes + 4 region boxes detected from the reference
  image's fill colours (one connected region per fill), 1 extra (the dual-lockstep shadow), 5 route hints.
  All 40 connections route automatically.
- `bench/stories/earlgrey_ibex_uart_read.yaml` + `bench/scenes/earlgrey_ibex_uart_read.py` (Ibex reads the 4x UART).
- Result: 40/40 blocks, 4/4 regions, 39/39 sure wires, 0 extras, 100% order agreement, 1 unconfirmed, 0 lint
  errors, 0 spec errors. Darjeeling re-run after the polish: 49/49, 4/4, 53/53, 0 extras, 100%, 12 unconfirmed,
  0 + 0 errors.

**Checker fix the second chip exposed (`ipmotion/conformance.py`):** a real diagram repeats names -- Earlgrey
draws "Pinmux", "Clk/Rst Managers" and "Analog Sensor Top" once per power domain -- and Manim's `Text.text`
drops spaces, so "TL-UL Crossbar" and "TL-UL Cross bar" also read the same. Block lookup used a label->text dict,
so all of them collapsed onto one box (31 false errors). New `conformance.locate_blocks(snaps, spec, layout)`
collects every drawn candidate for a name and, when several spec blocks share it, pairs them with the drawn
boxes in reference order (left-to-right, top-to-bottom). The layout is threaded through
`lint_script(..., layout=)` -> `conformance.check(..., layout)`; `fidelity` uses the same mapping. Without a
layout (v3, AI-written scripts) the old single-box behaviour stands and a warning is raised when a name is drawn
fewer times than the spec needs.

**Tests:** `tests/test_earlgrey_diagram.py` (11 tests): spec/layout completeness, no wire over a block (both
chips), swatch clearance (both chips), everything inside the frame and clear of the panel (both chips),
duplicate names told apart with the layout and not without it, perfect fidelity score, story scene clean.
Whole suite: 181 passing.

**Known limits unchanged:** the numbers compare the drawing with the hand-written notes of the picture, not with
the picture; Peppermint has truth but no layout file yet; the vision transcription and the LLM story step are
still not built.

## M1.7 third chip: Peppermint (2026-10-04) -- IN PROGRESS, left half-finished

Goal (user, option A of three): put a third chip through the same whole-diagram engine, to find out what the
M1.6 polish had quietly tuned to Darjeeling and Earlgrey. Peppermint already had a truth file but no layout
file. Nothing is committed yet; the working tree holds everything below.

**New files (done)**
- `bench/truth/opentitan_peppermint.layout.yaml`: 24 block boxes, 3 region boxes and 9 edge-label boxes, all
  detected from the reference image rather than guessed. One connected region per fill colour (outer gray
  239,239,239; the two domain boxes 217,217,217; main-domain blocks 188,216,167; AON blocks 119,169,76; the
  lockstep shadow 156,197,123); the nine edge labels are the bounding boxes of their black text. `routes` is
  still empty: every wire is routed automatically.
- `bench/stories/peppermint_ibex_retention_read.yaml` + `bench/scenes/peppermint_ibex_retention_read.py`:
  "Ibex reads from the Retention SRAM", a 6-step story that crosses from the main domain into the always-on one.

**What the third chip exposed, and what was changed for it (all in shared code, additive)**
- *No legend at all.* Peppermint's truth file records `fill: light green / dark green` instead of a
  `fill_legend:` entry, because the picture explains nothing. `diagram.py` now falls back to `fill`, has colours
  for those two names, and the legend panel prints "Drawing notes:" with no colour list instead of an empty
  "Clock speed (fill color):" heading.
- *A box with no label.* The AON domain has a small symbol the picture never names. `conformance.py` no longer
  looks for text that is not printed, the extras check no longer calls that box an intruder, and
  `spec_validator.py` accepts `label: null` on a full-diagram spec.
- *Edge labels on three sides.* Darjeeling only ever had labels in the left margin, and the M1.6 gutter code
  assumed it. Peppermint prints them left, bottom and right. Labels now also keep the reference's own place on
  the other two sides, are given one common font size, sit against the edge that faces the drawing, and are kept
  clear of the step panel, not just the frame edge.
- *Region titles wider than their own box.* The AON title is long and its box is narrow. A nested title is now
  broken over lines, as the reference does, instead of being shrunk until it cannot be read; the outermost title
  is still shrunk, which keeps it on one line as the picture has it.
- `label_chars` in the layout file gives each edge label the reference's own line breaks.

**Where it stands (last full run: `python bench/run_full.py bench/stories/peppermint_ibex_retention_read.yaml`)**
- 33/33 blocks, 3/3 regions, 32/32 sure wires, 100% order agreement, 3 unconfirmed.
- 2 extras, 4 conformance errors, 2 lint errors -- all four causes are known and listed below.
- A single frame renders and reads close to the reference.

**The four problems left open (none of them guesses; each was reproduced)**
1. **Darjeeling regression, must be fixed first.** The new "is this label in the left gutter?" test is
   `box[2] > drawing_left`, and Darjeeling's drawing starts at x=8 while its label boxes end at x=90/62/62, so
   all three are now treated as right/bottom labels. Measured: they drop from 12pt to the 9pt floor and sit on
   the drawing's left edge instead of in their gutter. That undoes part of the M1.6 margin-label polish. Fix:
   classify by side properly -- right if `box[0] >= drawing_right`, bottom if `box[1] >= drawing_bottom`, else
   left (which keeps Darjeeling's behaviour exactly) -- and use that one test in both `_margin_boxes` and
   `_place_labels`.
2. **The step panel is too narrow on Peppermint, which is what clips the legend line** (`out_of_frame` on
   "amber dashed line: not sure (see report)"). `_margin_boxes()` is called twice at two different scales: once
   with the height-fit scale, where the labels do not overhang and the gutter is 0.06, and once with the final
   scale, where the gutter is about 0.55. The panel is sized from the first and placed from the second.
   Measured panel widths: Darjeeling 6.86, Earlgrey 4.80, Peppermint 4.26 against a 4.8 minimum. Fix: settle
   the scale and the gutter together (2-3 rounds) and use the same gutter for both. Add a test that the panel
   is never narrower than `MIN_PANEL_W` on all three chips -- it would have caught this.
3. **The unlabeled symbol has no box, so its two wires are reported wrong** (c25/c26 "an end block is not
   drawn", plus the same two wires counted as extras). Cause: skipping label-less blocks in
   `conformance.locate_blocks` also skipped giving them a position. Fix: pair label-less spec blocks with the
   drawn boxes that own no text, in reference order, the same way blocks that share a name are paired; then
   have the extras check skip the boxes that were paired, instead of counting them.
4. **One wire runs through the "Debug module interface (DMI)" label** (`text_overlap`). Two causes:
   `label_chars: 14` breaks "interface (DMI)" (15 characters) onto a third line the reference does not have,
   and the automatic stem for c23 lands at x=468 where the grown text now reaches. Fix: `label_chars: 15`, and
   hand-read `routes` for c23 and c24 that follow the reference's fork, kept more than the 0.06-unit join
   tolerance apart so the checker does not read them as one wire.

**Also worth the user's eye before this is called done**
- The unlabeled symbol is drawn as a rounded pill; the reference shows a square with a white up-triangle. A
  special case like the Ibex lockstep shadow would match it.
- All nine edge labels land on the new 9pt floor (`MARGIN_LABEL_MIN`), because the detected boxes are tight to
  the glyphs. 9pt was chosen so the bottom row does not collide; it is a floor, not a measurement.
- Two choices made here that the session rules say to ask about: the validator now accepts `label: null` on a
  full-diagram spec, and the legend wording "dashed box: the picture does not say" for a diagram with no legend.

**Verification state, honestly**
- `pytest -q`: 181 passed, but that run started before the last three edits, so it does **not** cover the tree
  as it stands. It must be re-run.
- Darjeeling and Earlgrey have **not** been re-run since these changes. Both must go through `run_full.py` again
  and match their recorded numbers exactly (Darjeeling 49/49, 4/4, 53/53, 0 extras, 100%, 12 unconfirmed, 0+0
  errors; Earlgrey 40/40, 4/4, 39/39, 0 extras, 100%, 1 unconfirmed, 0+0 errors) before any of this is kept.
- No tests have been written for Peppermint yet. Planned: add it to the frame/panel and no-wire-over-a-block
  tests in `tests/test_earlgrey_diagram.py` (not to the swatch test, which needs a chip that has swatches), plus
  a story-clean test and the panel-width test from problem 2.
- `bench/report.html` has not been rebuilt, so it does not show Peppermint yet.

**Next session, in order:** problem 1, then 2, then 3, then 4; re-run all three chips; write the tests;
`python bench/make_report.py`; commit.
