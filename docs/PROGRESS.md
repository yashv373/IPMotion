# IPMotion v3: Progress

| Milestone | Scope | Status |
|---|---|---|
| M0 | Housekeeping: git, .gitignore, scipy mock removal, MANIFEST, pytest, docs | Done (2026-10-03) |
| M1 | A (port API) + C (geometric lint) + tests | **Done** (2026-10-03) |
| M1.5 | End-to-end benchmark (spec -> animation), v2 vs v3 | **In progress**: Darjeeling run done, others pending |
| M1.6 | Whole-diagram polish + a second chip (Earlgrey) on the same engine | **Done** (2026-10-04) |
| M1.7 | Third chip (Peppermint) on the same engine | **Done** (2026-10-04) |
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

## M1.7 third chip: Peppermint (2026-10-04)

Goal (user, option A of three): put a third chip through the same whole-diagram engine, to find out what the
M1.6 polish had quietly tuned to Darjeeling and Earlgrey. Peppermint already had a truth file but no layout
file. No AI and no quota are involved anywhere in this pipeline.

**New files**
- `bench/truth/opentitan_peppermint.layout.yaml`: 24 block boxes, 3 region boxes and 9 edge-label boxes,
  detected from the reference image rather than guessed -- one connected region per fill colour (outer gray
  239,239,239; the two domain boxes 217,217,217; main-domain blocks 188,216,167; AON blocks 119,169,76; the
  lockstep shadow 156,197,123), and the nine edge labels are the bounding boxes of their black text. Only two
  wires needed a hand-read route (the DMI fork, below); the other 32 route automatically.
- `bench/stories/peppermint_ibex_retention_read.yaml` + `bench/scenes/peppermint_ibex_retention_read.py`:
  "Ibex reads from the Retention SRAM", a 6-step story that crosses from the main domain into the always-on one.

**What the third chip exposed, and what was changed for it (all in shared code, all additive)**
- *A picture with no legend.* Peppermint's truth file records `fill: light green / dark green` instead of a
  `fill_legend:` entry, because the picture explains nothing. `diagram.py` falls back to `fill` and has colours
  for those names; the legend panel prints "Drawing notes:" instead of an empty "Clock speed (fill color):"
  heading, and says "dashed box: the picture does not say" rather than claiming a meaning the picture never gave.
- *A box the picture never labels.* The AON domain holds a small symbol with no text. `conformance.py` no longer
  hunts for text that is not printed; instead `locate_blocks` pairs label-less spec blocks with the drawn boxes
  that own no text, in reference order -- the same way blocks that share a printed name are told apart -- so
  their wires resolve. The extras check skips the boxes that were paired. `spec_validator.py` accepts
  `label: null`, and the empty `Text` is dropped from the block entirely rather than drawn and measured.
- *Edge labels on three sides.* Darjeeling prints all of its down the left, and the M1.6 gutter code assumed it.
  `_label_side()` now tells left, bottom and right apart, defaulting to left (Darjeeling's boxes overlap the
  drawing's own left edge, so left cannot be read from position). A left label is still pulled into the gutter
  at full size; a bottom or right label keeps its place and grows about it. All of them share one font size,
  sit against the edge facing the drawing, and are kept clear of the step panel, not just the frame edge.
- *The scale and the gutter are settled together.* `_margin_boxes()` is called at two different scales, and the
  panel used to be sized from one and placed from the other: Peppermint's panel came out 4.26 units wide against
  a 4.8 minimum, which is what clipped its legend. The two are now iterated to a fixed point. Measured after:
  Darjeeling 5.82, Earlgrey 4.80, Peppermint 4.80.
- *Region titles that do not fit their own box.* The AON title is long and its box is narrow. A nested title is
  now tried at one, two and three lines and drawn at whichever comes out biggest, measured against both the box
  width and the strip above the region's own blocks (`_header_height`), so a title can no longer sit on the
  blocks underneath it. The outermost title is only shrunk, which keeps it on one line as the reference has it.
- *The DMI fork.* The picture draws one thick line up from the bottom edge that forks to Debug Module and Life
  Cycle Controller. The recorded decision is that each spec connection is its own wire, so the fork is drawn as
  two wires of the same shape, kept far enough apart that the checker does not read them as one.
- `label_chars` in the layout file gives each edge label the reference's own line breaks.

**Results (`python bench/run_full.py bench/stories/<story>.yaml`, all three re-run after the changes)**
- Peppermint: 33/33 blocks (24 + 9 edge labels), 3/3 regions, 32/32 sure wires, 0 extras, 100% order agreement,
  3 unconfirmed, 0 lint errors, 0 conformance errors.
- Darjeeling: 49/49, 4/4, 53/53, 0 extras, 100%, 12 unconfirmed, 0 + 0 -- identical to M1.6.
- Earlgrey: 40/40, 4/4, 39/39, 0 extras, 100%, 1 unconfirmed, 0 + 0 -- identical to M1.6.
- CAVEAT, unchanged: these compare the drawing with the hand-written notes of the picture, not with the picture.
  The user judges by eye; the report shows the reference beside each render.

**Tests:** `tests/test_peppermint_diagram.py` (10 tests): spec/layout completeness, the panel is never narrower
than its minimum (on all three chips -- this is the test that would have caught the clipped legend), labels are
told apart by side and Darjeeling keeps its 12pt gutter text, no edge label runs into another, the unlabeled box
is found and is not an extra, a perfect fidelity score, and the story scene clean on both checks. Peppermint was
also added to the existing "no wire over a block" and "inside the frame and clear of the panel" tests (not to
the legend-swatch test, which needs a chip that has swatches). Whole suite: 191 passing.

**Known limits**
- All nine edge labels land on the new 9pt floor (`MARGIN_LABEL_MIN`), because the detected boxes are tight to
  the glyphs. 9pt was chosen so the bottom row does not collide; it is a floor, not a measurement. If a future
  reference needs them smaller still, the linter reports the collision rather than the engine solving it.
- The unlabeled symbol is drawn as a rounded box; the reference shows a square with a white up-triangle. A
  special case like the Ibex lockstep shadow would match it. Left as it is, pending the user's view.
- Two choices the session rules say to ask about, made here and still open for the user: the validator accepts
  `label: null` on a full-diagram spec, and the legend wording for a diagram with no legend.
- Unchanged from M1.6: the numbers compare the drawing with the notes, not the picture; reading a new image
  automatically (vision) and the story-from-text step (LLM) are still not built.

**Next:** user reviews the three renders in bench/report.html (Peppermint's 3 unconfirmed items, Darjeeling's 12);
then M2 (STYLE.md + style.toml layout conventions), now that three chips show which rules actually generalise.
Handoff for the main builder: docs/WEB_HANDOFF.md (UI flow, file map, what must be kept in sync).

## Direction correction + first honest baseline of the product (2026-10-04)

**The user's call, in their words:** the goal is that a stranger opens the website, writes a story, gives a block
diagram and an example write-up, adds an API key, hits Generate, downloads the .py, runs it with a manim command
and gets a **good first animation**. We are building that ecosystem, not hand-refining animations. Progress is
judged on how good and how accurate the animation on the website is. The user also said plainly that the v4
pivot "wasted a lot of money and effort" by running for three sessions before anyone checked it fed the product.

**What an audit of the product found (not an opinion -- these are counts):**
- The Generate button sends ~223 lines of context, makes ONE request, and does no lint, no conformance check and
  no retry. The repair loop exists only in the benchmark, never in the browser.
- Of those 223 lines, exactly 80 are a worked example: one, the AXI handshake. It is the only file marked
  `indexable` in gold_examples/MANIFEST.toml. Of the other six gold scripts, three crash with NameError and the
  rest teach overlapping blocks, text outside the frame, or bypass the library. There is no second example.
- **The three chips contributed nothing to it.** A v4 run's output script is five lines (`class FullStory(
  FullDiagramScene): STORY = ...`); all the drawing lives in diagram.py. There is no Manim code in it for a model
  to imitate, so Darjeeling, Earlgrey and Peppermint were invisible to the thing the website does.

**Decisions (user, 2026-10-04)**
- Darjeeling and Earlgrey may become worked examples inside the prompt. **Peppermint is held out and must never
  reach a prompt**, so scoring against it stays honest. This amends the blanket CLAUDE.md rule, which now says so.
- Quality is measured by replaying the website's exact one-shot prompt and scoring with the existing checks.
- Order corrected after the user's feedback: the measurement is built and run FIRST, so every later change to the
  examples is justified by a number instead of a theory. That is the mistake the v4 pivot made.

**Built: `bench/run_web.py`** -- replays `web/app.js` byte-for-byte (same four context files, same `=====`
joining, same user sections, same fence stripping, same model `gemini-3.5-flash`), once, with no feedback, then
scores the result with the existing lint + conformance + fidelity checks. Inputs are in `bench/web_inputs/`:
a plain-text Peppermint block diagram and a plain-English story, written the way a visitor would type them.

**BASELINE, 1 run, Peppermint held out (runs/20261004_203734_peppermint_web):**
- The script runs and renders -- it does not crash. 241 lines.
- 10 lint errors, 49 spec errors.
- Blocks 29/33, wires **16/32**, regions **0/3**, 11 extras.
- Typical failures: labels paraphrased ('Ibex Core (Lockstep)' for 'Ibex Core (RV32IMCB)', 'Mailboxes' for
  'Mailboxes (inbound & outbound)'), so the block counts as both missing and extra; no region/domain boxes drawn
  at all; half the wiring absent.
- Fixed while building the harness: it passed a file path where `common.scene_name` wants the source text, and
  reported a perfectly good script as having no Scene class.

**What this number means:** the drawing half of the framework is strong and the generating half is weak, and the
weakness is that the model has one worked example to learn from. Half the wires and all three regions missing is
not a prompt-wording problem.

**Next:** add Darjeeling and Earlgrey as worked examples (they need a flat Manim script emitted from diagram.py,
since the five-line stub teaches nothing), then re-run this exact baseline and compare. Peppermint stays out of
the prompt. Also still open: wiring the `web` pipeline into bench/make_report.py so these runs show up beside
the others.

## Worked examples in the RAG, measured three ways (2026-10-04)

Method: `python bench/run_web.py bench/web_inputs/peppermint.txt bench/web_inputs/peppermint.story.txt --reps 3`
-- a byte-for-byte replay of what the Generate button sends, one shot, no feedback, scored with the existing
lint + conformance + fidelity checks. Peppermint is never in the context (enforced by a test), so this measures
generalisation. Same input text every time.

| context | lint | spec | blocks | wires | regions | extras |
|---|---|---|---|---|---|---|
| 1 example (AXI only) | 13.3 | 53.3 | 29.3/33 | 16.0/32 | 0/3 | 15.7 |
| + Earlgrey (485 lines) | 16.0 | 42.3 | 30.0/33 | 18.7/32 | 0/3 | 8.3 |
| + Earlgrey + Darjeeling (630) | 7.5 | 44.0 | 30.5/33 | 16.0/32 | 0/3 | 7.5 |

(the third row averages 2 runs: one of the three crashed with `NameError: DoubleHeadedArrow`, the model
inventing a class -- the same failure that already excludes three of the seven gold scripts, not a new one.)

**Earlgrey earned its place:** extras nearly halved (15.7 -> 8.3) and spec errors fell 21%. The model stopped
drawing things that are not in the diagram.
**Darjeeling did not, on this evidence:** lint errors improved a lot (16.0 -> 7.5, better than baseline) but
wires went back down to 16.0 and spec errors did not move, while the prompt doubled from 42k to 85k characters.
Both are shipped because the user asked for both; the number says the second example is not paying for itself
and should be re-tested or dropped.

**A correction worth recording.** An earlier commit message here claimed the model "had never seen a region
drawn, hence 0/3". That was wrong, and checking the generated scripts proved it: the baseline runs already
contained 2 DomainGroups each. The model has been drawing regions all along. **The 0/3 is measuring name
matching, not region drawing** -- it writes "Main Power & Clock Domain" where the diagram says "Main power and
clock domain", so the region scores zero.

**That makes paraphrasing the single biggest remaining fault**, and it explains three numbers at once: regions
score 0, blocks are counted as missing, and the same blocks are then counted as extras. One root cause, three
symptoms. The next lever is name fidelity, not more examples.

**`ipmotion/emit.py`** turns a drawn reference diagram into a flat standalone Manim script. It only READS a
built Diagram, so no drawing logic is duplicated and an example can never drift from what the engine draws.
Getting both chips to emit cleanly took four fixes, each found by the linter, not by eye:
- a full-width Banner lands on a portrait drawing, so a tall diagram now puts its step caption in the gutter
  beside the drawing instead;
- a wire that points at something inside a block (Darjeeling's SoC Proxy trapezoid) is pulled back onto the
  block's edge, because in a flat script the linter can see the dangling end that the Diagram version hid;
- the title position is emitted as drawn, not assumed to be the block centre (SoC Proxy pins its title to the top);
- boxes are emitted as DRAWN, not as written in the notes, because the engine grows a sliver block so its title
  fits -- without that the example's own text overflowed.
Result: Earlgrey 485 lines and Darjeeling 630 lines, each 0 lint errors and 0 spec errors against its own spec.

**Prompt changes that went with them** (an example using absolute positions while the rules praised `arrange()`
would only confuse the model): rule 7 is now size-dependent and points at the examples, a new rule 8 requires a
DomainGroup per domain added before the blocks, and a closing section names what to copy.

**Tests:** `tests/test_web_context.py` (5, instant, no model calls) -- the harness sends exactly what the
browser sends (if these drift the measurement silently stops measuring the product), every listed context file
exists, Peppermint never reaches the prompt, the examples really do teach regions and absolute positions, and
the rules mention DomainGroup and paraphrasing.

**Known limits**
- `bench/web_inputs/peppermint.txt` is the "Explainer" input at its tidy end: a realistic BEST case. A messier
  "Copier" input (raw datasheet text) is untested and would likely score worse.
- Three runs is a small sample for a model this variable (lint errors ranged 11-26 within one group).
- The `web` pipeline still does not appear in bench/report.html.

**Next:** attack paraphrasing (exact-name fidelity). That is the one change that should move regions off 0 and
stop blocks being counted twice.

## The strict-name rule: two metrics hit their ceiling, the bottleneck moved (2026-10-04)

Change: RULE 0 at the very top of `00_rules.txt` -- "EXACT STRING MATCHING REQUIRED ... you are a parser, not a
copywriter", with worked wrong/right pairs -- and Darjeeling dropped from the live prompt (kept on disk as a
reserved asset for a future retrieval step). The clean comparator is the `+Earlgrey` row: same examples, old rules.

| context | lint | spec | blocks | wires | regions | extras |
|---|---|---|---|---|---|---|
| 1 example (AXI only) | 13.3 | 53.3 | 29.3/33 | 16.0/32 | 0.0/3 | 15.7 |
| + Earlgrey | 16.0 | 42.3 | 30.0/33 | 18.7/32 | 0.0/3 | 8.3 |
| + Earlgrey + Darjeeling | 7.5 | 44.0 | 30.5/33 | 16.0/32 | 0.0/3 | 7.5 |
| **+ Earlgrey + STRICT NAMES** | 19.0 | 49.0 | **31.0/33** | 10.0/32 | **2.0/3** | 9.5 |

**First, a fairness check that should have been done before any of this.** Three labels the scorer wants are not
in the user's input text verbatim: 'Entropy Source, CSRNG, EDN' (the input writes it without commas), 'Life Cycle
Function Control', and the outer region's full title with its en-dashes. So with this input the ceiling is
**31/33 blocks and 2/3 regions** -- 33 and 3 were never reachable, and every earlier row was being scored against
an impossible target.

**Against the real ceiling, the rule did exactly what it was predicted to do:**
- blocks 30.0 -> **31.0 of 31 possible**: maxed.
- regions 0.0 -> **2.0 of 2 possible**: maxed. The model was always drawing regions; it just named them
  "Main Power & Clock Domain" instead of "Main power and clock domain". Told to copy character for character,
  it does, and they count.
Name fidelity is solved for anything the user actually wrote.

**But the bottleneck moved, and the totals got worse.** Wires fell 18.7 -> 10.0, which drags spec errors up to
49.0 (22 missing wires are 22 errors) and lint to 19.0, and one of the three runs died with a SyntaxError at 749
lines. The plausible mechanism: the model now spends its output budget copying long exact names and producing
much longer files, and loses track of the wiring. That is a hypothesis, not a finding.

**Honest read:** this is not yet a better animation for a visitor, even though two sub-scores are perfect. The
next lever is wiring completeness, the same way names were attacked: say it bluntly and early in the rules, and
measure. Do not add more examples first.

**Measurement hygiene, to do before the next comparison:** fix the three labels in `bench/web_inputs/peppermint.txt`
so the ceiling is a true 33/33 and 3/3. That breaks comparability with the four rows above, so it should be done
as a deliberate re-baseline, not quietly.

**Website copy** (the user said it reads confusingly):
- "What it can make" -> "What IPMotion draws", with a line saying plainly that the four gallery animations are
  reference renders drawn by the engine, that they are what the generator learns from, and that a one-shot
  result will be rougher. The old heading implied the Generate button made them.
- The diagram box is no longer "(optional)" in spirit: it now says it is what makes the result good, and that
  names are copied character for character, with a worked placeholder.
- The "one shot" warning now says to treat the output as a strong first draft.
- Removed the internal "v4 pivot" changelog row (meaningless to a visitor) and added a plain-words row for this
  RAG work.

## Future direction recorded: sequential improvement (2026-10-04)

The user's framing: the website gives a good FIRST animation; if it needs more, the visitor can take the script
to any chat assistant, and later IPMotion should do that refining itself.

Written onto the site rather than left as a plan:
- index.html, with the generated script: "Not happy with the first result? Keep going." Three concrete moves --
  paste the script into any chat assistant and say what is wrong in plain words; run
  `python -m ipmotion.lint script.py` first so the assistant gets a precise list; or fix the diagram text, since
  most misses come from the input. Followed by a plain statement that this back-and-forth is work IPMotion
  should be doing for the visitor, and that bringing the local generate -> check -> repair loop into the page is
  the next direction.
- how-it-works.html gains a "Future direction: sequential improvement" section saying the same thing against the
  pipeline description, and noting the output is ordinary Manim code so nothing is locked to us.

Deliberately not claimed: that the repair loop runs in the browser. It does not. It exists in the local
benchmark harness only, and both pages say so.

## Library guarantees, pacing, and two new example shapes (2026-10-05)

**The user's question:** the demo looked shabby -- overflowing and misaligned text, wrong wiring, too fast to
read. Is the answer more polished examples in the RAG, or something else?

**Answer, from our own measurements: something else.** Adding a second big chip example (Darjeeling, 630 lines)
had already made wiring WORSE (18.7 -> 16.0) while doubling the prompt. A single RULE (copy names exactly) then
did what no example had: blocks and regions both reached their ceiling. Examples teach a tendency; they do not
guarantee anything.

**The actual cause of the overflowing titles, found by reading the library:** `IPBlock` shrinks its title to fit
its box. `DomainGroup` never did -- fixed `font_size=24`, no wrap, no shrink. That is precisely why "Main power
and clock domain" sat across Ibex Core and the AON title ran off the frame. More generally: **every quality
guarantee we built lives in `diagram.py`, where a generated script cannot reach it.** Wrapping, header
clearance, one common font size, wires routed around blocks -- all of it protects the engine's renders and none
of it protects the generator's. We had been polishing the path the product does not use.

**Fixes**
- `DomainGroup` now fits its own title (up to three lines, shrunk into the header strip, never enlarged, so a
  title that already fitted is byte-identical). `diagram.py` passes `fit=False` because it has better
  header-aware logic and its three chip renders are approved; 198 tests confirm they are unchanged.
- Pacing is now a rule of its own: `run_time >= 0.8`, `wait(1.2)` per step, 2.5s final hold, with the target
  stated plainly -- a 6-step story should last about 25 seconds, not 8.

**Measured (1 rep only; the daily Gemini free quota of 20 requests ran out mid-run)**

| context | lint | spec | blocks | wires | regions | extras |
|---|---|---|---|---|---|---|
| 1 example (AXI only) | 13.3 | 53.3 | 29.3/33 | 16.0/32 | 0.0/3 | 15.7 |
| + Earlgrey | 16.0 | 42.3 | 30.0/33 | 18.7/32 | 0.0/3 | 8.3 |
| + Earlgrey + Darjeeling | 7.5 | 44.0 | 30.5/33 | 16.0/32 | 0.0/3 | 7.5 |
| + strict names | 19.0 | 49.0 | 31.0/33 | 10.0/32 | 2.0/3 | 9.5 |
| **+ library fit & pacing** | 22.0 | **37.0** | 31.0/33 | **19.0/32** | 2.0/3 | **6.0** |

Best spec errors, best wires and fewest extras of any configuration so far, with blocks and regions still at
their ceiling. Lint errors are the one thing that went up (19 -> 22) and that is unexplained. **n=1, so none of
this is solid** -- the honest read is "promising, unconfirmed", and it must be re-run on three reps when the
quota resets.

**Two new gold examples, both 0 lint errors and 0 warnings**
- `gold_examples/systolic_array_mac.py`: 4x4 output-stationary MAC array. The first example that is not a
  floorplan. Teaches sixteen blocks from a loop rather than sixteen definitions (our one crashed run was a
  749-line script that broke syntax), grid coordinates computed from an origin and a pitch, and a whole diagonal
  animating in ONE `play()` call.
- `gold_examples/mesi_cache_fsm.py`: the MESI state machine. Circular nodes carrying their own labels, curved
  transitions, a self-loop. Took three passes to read well; the last fault was invisible to lint and obvious to
  the eye -- labels on a vertical arc were cleared by their height instead of their width.

Both are registered `indexable` in MANIFEST.toml but are **deliberately NOT in the live prompt yet**, because
adding them unmeasured is the mistake we already made with Darjeeling. They need measurement, and new shapes
also need held-out exams of their own shape before their value can be seen at all.

**`docs/SOURCES.md`**: every reference diagram and animated structure now carries a citation, including the
OpenTitan diagrams that were published on the site with no attribution at all (lowRISC, Apache-2.0). Rule
written down: a new animation takes its structure from a citable source and lands in that file the same commit.

**Website**: new logo and icons throughout (white background turned to real transparency, wordmark lifted so it
reads on dark, chip glyph alone for the favicon); every image given explicit width and height so the page does
not reflow; buttons given hover, active and focus states, which they had never had; focus-visible rings, a
blurred sticky header, input focus rings, a web manifest. The two new examples are in the gallery as video with
their citations, and the generated-Peppermint clip is now video instead of a 16-colour GIF.

**Harness fix**: `DailyQuotaError` is a `BaseException` by design, so `except Exception` could not catch it and a
quota stop threw away the reps that had already completed. `run_web.py` now stops cleanly and still reports them.

**Next:** re-run the 3-rep measurement when the quota resets; then measure the systolic example going into the
prompt, with a held-out exam of its own shape. Wiring correctness (19/32) is still the open quality problem.

## Overnight run: four new example shapes, new logo, and the site rebuilt on video (2026-10-05)

**New gold examples** (all 0 lint errors, 0 warnings; all cited in docs/SOURCES.md; all registered indexable in
MANIFEST.toml; **none of them in the live prompt yet, because they are unmeasured**):

| file | shape | what it teaches that the chip examples cannot |
|---|---|---|
| `systolic_array_mac.py` | 4x4 MAC array | 16 blocks from a loop, computed grid coordinates, a whole diagonal in one `play()` |
| `mesi_cache_fsm.py` | MESI state machine | circular nodes, curved transitions, a self-loop, highlight instead of a travelling packet |
| `lockstep_safety_island.py` | dual-core lockstep | strict mirror symmetry, two datapaths into one block without crossing, a safety region, a fault as a state change |
| `cim_crossbar_array.py` | compute-in-memory crossbar | the blocks ARE the intersections; cells recoloured in place; analog and digital visually separated |

Three faults the linter caught that the eye would have missed, and one the eye caught that lint did not:
- crossbar: every wordline and bitline originally stopped in empty space, so the decoder and sense amps are now
  built first and each line ends ON one of them;
- crossbar: six column wires ran straight through the sense-amp caption, and the wordline labels sat on the
  wordlines;
- lockstep: a banner line too long for the frame;
- **and the one lint passed happily**: `Line(decoder.get_right(), ...)` put all four wordlines at the decoder's
  mid-height, so they converged on a single point instead of leaving at their own rows. Only the rendered frame
  showed it. This is why a frame is always rendered and looked at.

**Website**
- New logo everywhere, built from the supplied artwork: white background turned into real transparency by
  un-premultiplying it, the near-black wordmark lifted to the site's text grey so it reads on the dark theme,
  and the chip glyph cropped alone for the favicon and app icons (the wordmark is unreadable at 32px). Every
  image now carries explicit width and height, so the page no longer reflows while loading.
- **The gallery is video now, not GIFs.** The four original animations were 480px, 5fps, 16-colour GIFs totalling
  11.5 MB; as H.264 they are 1.29 MB at 1280px and 30fps. About a ninth of the bytes and visibly sharper. The
  superseded GIFs are deleted. Hidden popup videos no longer preload themselves.
- Buttons had no hover, active or focus states at all. Added, with focus-visible rings throughout, a blurred
  sticky header, an accent rule under each heading, input focus rings, smooth scrolling that respects
  prefers-reduced-motion, and a web manifest so the 192px icon is finally used.
- Eight gallery cards, each with its citation in the window.

**Still true and still the open problem:** wiring completeness, 19/32 at best. Blocks and regions are at the
ceiling the test input allows (31/33 and 2/3). The library fit and pacing result is **n=1** -- the daily Gemini
free quota of 20 requests ran out mid-run -- so it must be re-run on three reps before it is believed.

**Ready for the next session, no quota needed to prepare:** `bench/run_web.py --no-spec` scores geometry only,
for a shape with no reference answer. Held-out exams are written for two new shapes: a 3x5 systolic array (a
different size from the example) and a round-robin arbiter FSM (a different machine from MESI), in
`bench/web_inputs/`.

**A trap worth writing down:** `.gitignore` has no trailing comments. `!web/assets/video/*.mp4   # comment` made
the pattern the whole line, so the exception never matched and a green Pages deploy served a 404 video. Twice.
Always curl the live URL after deploying.

## Wiring diagnosed, and a rule aimed at it (2026-10-05)

Before writing another wiring prompt, the earlier suspicion was checked: are wires missing, or drawn and failing
the endpoint tolerance? **No quota needed -- the generated scripts are kept.** Counting the last run's script:

- the input listed **32 connections**; the script contained **21 arrow objects**;
- fidelity scored **19/32**, so **19 of the 21 it drew were correct**;
- `Connection(` and `Line(` appear **zero** times -- it only ever uses `Arrow`.

So wires are genuinely **absent, not mis-anchored**. The model does not draw them badly; it stops early. That is
a completeness failure, which is the same shape as the naming failure that one blunt rule fixed.

**RULE 1 added**, directly above the old rule list and quoting the measurement back at the model: go through the
wiring list one line at a time, one arrow per line, if the user lists 32 connections the script contains 32
arrow objects, count them before finishing. Prompt grows to 46k characters.

**Honest caveat on the next measurement:** the pending 3-rep run will now be measuring the library fit, the
pacing rule AND this wiring rule together, against the `+ strict names` row. If wires move sharply, RULE 1 is
the likely cause since nothing else targets them; if they do not, the rule failed and should be reverted rather
than elaborated. Attribution is muddier than it should be -- the clean alternative was to leave the rule out
overnight, which would have wasted the next session's first run.

## Why the demo looked unchanged, and the fix that followed (2026-10-05)

**User's report:** after four new examples, the Peppermint demo still looked bad -- overflows, mismatches, wrong
wiring. Correct observation; both causes were mine and neither was the examples.

1. **The four new examples are not in the live prompt.** Held out as unmeasured, so they could not have changed
   anything. The user was asked to judge an effect that was never switched on.
2. **The clip on the site was stale.** `generated-peppermint.mp4` was rendered at 21:51; the prompt changed at
   22:05 (strict names), 23:49 (library fit + pacing) and 00:35 (RULE 1). It predated three of the four fixes
   while being labelled "what the generator makes today".

**The real bug, found by testing the fix against the model's own numbers.** `DomainGroup` fitting works: the
38-character AON title in its 3.2-unit box shrinks from 6.88 units to 2.79, comfortably inside. It fits the box
and still lands on the blocks, because it is drawn INSIDE the region at the top-left and the model leaves no
header room. **A region title cannot know where the blocks inside it were put.** So the title now draws ABOVE
the border, where nothing inside the region can reach it, falling back to the corner when there is no room
above. Height capped harder too: 14% of the region or 0.46 units, whichever is smaller.

**Demonstrated without spending a model call:** re-rendering the SAME generated script against the fixed library
puts both domain titles cleanly above their boxes. Same model output, better picture. That is the argument for
fixing the library rather than the prompt, shown in isolation.

**RULE 1 result (1 rep, quota ran out again):** arrows drawn went **21 -> 30** of 32 listed, so the completeness
rule worked on exactly what it targeted. But wires scored 18/32 and extras rose 6 -> 16: it now draws nearly all
of them and gets more of them wrong. **The bottleneck moved from "stops early" to "joins the wrong pair".**

**RULE 2 added** from what that frame then showed: a dozen block names were unreadable because wires were drawn
across them. Wires are added before blocks, or with `z_index(-1)`, and short wires between neighbours are
preferred over long ones that cross everything between.

**Reference diagrams** for the four new examples are drawn by us from the structure described in each cited work
and labelled as such -- reproducing a paper's own figure on a public page is someone else's copyright. The
citation underneath points at the real ones.

**Next:** wiring accuracy, not completeness. 3 reps when the quota resets, to see whether RULE 2 recovers the
hit rate that RULE 1 traded away.

## Answering "how do we make it do good wiring?" (2026-10-05)

User's read of the current demo: layout improved and text sits correctly inside blocks, but wiring is extremely
bad, domain boundaries are not well defined, and some edge labels are too small to read.

All three were library omissions, not prompt problems, and the same shape as the title bug:

**1. Wiring.** Every generated wire is a straight line between two blocks that ignores everything between them,
which is why it runs across OTBN, KMAC, HMAC and hides their names. The engine has solved this for a year inside
`diagram.py._avoid`, where a generated script cannot reach it. So the library now has its own router:

    wire_points(src, dst, avoid=[...])   -> orthogonal points that go around the obstacles
    wire(src, dst, avoid=blocks)          -> a VGroup of segments, z_index -1 so it sits BEHIND the blocks

It tries the short routes first (shared x or y band, then L, then Z) and falls back to a detour through a
channel just outside an obstacle. **The first version failed its own test**: with two blocks on the same row
every candidate it generated still ran straight through the block between them, because none of them left by
the top or bottom. Detour channels derived from each obstacle's own edges fixed it. `tests/test_wire_routing.py`
(9 tests) pins it: a clear run stays a straight line, a blocked run goes around, three obstacles in a row are
all avoided, the ends stay on their blocks, and the wire is behind them.

**2. Domain boundaries.** `DomainGroup` built its rectangle with `stroke_width=0`, so the stroke colour the
caller passed was silently ignored and a region had no visible edge at all. It now draws a 2.5-wide border in
the colour given. `diagram.py` sets its own stroke afterwards, so the chip renders are unchanged.

**3. Edge labels.** RULE 4 asks for font_size 16 or more outside a block, never below 14, and a line break
rather than shrinking.

**RULE 3** points the model at `wire()` and tells it not to draw connection arrows by hand, with the one
exception that still needs `Arrow`: a free-standing label pointing in from outside the diagram.
`web/make_context.py` regenerates the API file, so `wire` and `route_points` now appear in the signatures the
model is given.

**Not yet measured** -- the quota is spent. The next 3-rep run is the first that can show whether the model
actually calls `wire()`. If it does, the wire-over-block fault disappears structurally rather than by
persuasion; if it does not, the rule needs to be louder, not the router better.

## Wiring: the router proved out on a real layout, and an example that teaches it (2026-10-05)

**Shown without a model call, which is how it should have been done hours earlier.** The generator's own script
was already on disk, so the new library could be applied to the layout the model produced. Result in
`docs/wiring_after.png`: same blocks, every wire routed by `wire()`, no wire crossing a block name, and the
connections readable. `docs/wiring_before_shortest.png` is the intermediate where the router was still wrong.

**Three bugs in my own router, every one of them invisible to its nine unit tests** (which only exercise two
blocks on an empty canvas) and all three found in a single render against a real layout:
1. it returned the FIRST clear route instead of the shortest, so wires escaped right around the outside of the
   drawing -- avoiding every block and telling the reader nothing;
2. `z_index=-1` put wires BEHIND the region's opaque fill, so most of them vanished completely;
3. regions had no depth of their own. Layering is now explicit: region -2, wires -1, blocks 0.
A fourth improvement followed: when a dense layout leaves no clean route at all, take the route that crosses the
FEWEST blocks and use length only to break the tie, instead of the shortest-and-damn-the-crossings.

**The reason RULE 3 would have been ignored.** Neither example in the live prompt used `wire()` -- AXI draws
`Arrow`, the emitted Earlgrey draws explicit `Line` points. The examples contradicted the rule, and a model
imitates examples harder than it obeys rules. So `gold_examples/wired_soc_fabric.py` was written for exactly
this: seven blocks, seven links, **not one wire coordinate typed by hand**, 0 lint errors and 0 warnings. It is
now in the live prompt as `27_example_wired.txt`.

**Live prompt is now:** rules, library API, AXI, Earlgrey, wired SoC fabric, input notes.

**Still unmeasured, and this is the whole open question:** will the model actually call `wire()`? The router is
proven; the example now demonstrates it; the rule demands it. The Gemini free tier (20/day) is spent, and there
is no `.env`, so that key is the only provider configured. **The first command next session answers it**, and
the single thing to grep for in the generated script is `wire(`.

## Future work, recorded not started (2026-10-05)

Three directions came from outside the repo this session. **None of them is built, and none should be started
before wiring accuracy is fixed** -- that is the one number still far from its ceiling, and it is what every
outside tester sees first.

**1. RTL in, datapath out, animation after (a manager's suggestion).** Read Verilog/VHDL, work out the data
path, animate it. This removes the hand-written block diagram from the input, which is the single biggest
chore for a new user. Two things to settle before any code:
- It makes RTL a *second* source of architecture facts, which conflicts with the rule in CLAUDE.md that facts
  come only from `bench/truth/*.yaml`. Either the extracted netlist becomes a generated truth file (preferred:
  the lint and fidelity scorers then work unchanged), or the rule gets an exception.
- Measure the cheap version first. A Yosys/`pyverilog` hierarchy dump rendered straight into the existing
  block-diagram text format would show, in one afternoon, whether the output is worth animating -- before
  anyone builds datapath inference. (No unmeasured pivots.)

**2. Sequential improvement / self-refinement.** Already on the roadmap as M4 (ordered repair loop) and named on
the site under "Not happy with the first result?". The website hands over a one-shot script today; the repair
loop exists locally. Bringing generate -> lint -> repair into the browser is the same work, not new work.

**3. An ST-internal version.** Shown to the user's STMicroelectronics manager, who wants an internal build
later. Porting is a corpus swap, not an architecture change: `web/rag_context/`, `gold_examples/` and
`gold_examples/MANIFEST.toml` are the three things that would carry internal examples alongside the open-source
ones. **Build no abstraction for this now** -- the thing that makes the port easy is that the open-source
version stays good and the corpus stays data.

## Feedback from an outside tester (Saankhya Labs, 2026-10-05)

First user outside the project. What they said, and what was done with it:

| What they said | Status |
|---|---|
| "the generated script needed soo much more optimisation" | **The open problem.** This is wiring accuracy; see the section above. |
| "i don't have anthropic keys ... if you could put an open router / open source key vendors that would be great" | **Added, not yet run end-to-end** (nobody here has an OpenRouter key). `web/app.js` has an OpenRouter provider: OpenAI-compatible endpoint, `Bearer` key, `choices[0].message.content`. Verified by hand: the CORS preflight from the Pages origin returns `Access-Control-Allow-Origin: *`, and both default slugs exist in `/api/v1/models` (`deepseek/deepseek-chat-v3.1`, 163k context; `qwen/qwen3-coder`, 262k). **The first visitor with a key is the real test.** |
| "Manim didn't support my older python 3 version ... it needs the newer 3.11x" | **Done, and they were right.** `manim==0.21.0` declares `requires_python >=3.11` on PyPI; the page said 3.10 to 3.12. It now says 3.11 or 3.12, says plainly that an older Python 3 will not work, and gives the `py -3.11 -m pip install` line for Windows. |
| "You're not storing the prompts kya? ... so company can use this without worrying about ip stealing" | Already true and already on the page (static site, no backend). Worth saying it in the words a company cares about: **your diagram never leaves your browser except to the provider you chose.** |
| "i feel the context window was small" | **Measured, and the old claim was wrong.** The live prompt is **52,938 characters, about 13k tokens** (the 90k figure dates from when Darjeeling was still in it). The page now states that and asks for a 32k context or more. What the tester actually meant is not known -- do not guess. |
| "this is basically a deterministic video generation compiler being driven by ai, not ai video generation" | Their words, and a better one-line description of the product than anything currently on the site. Candidate for the hero text. |

## The wiring question, answered: the model does call wire(), and "wires 19/32" was mostly a scoring artefact (2026-10-05)

**The open question from last session was: will the model actually call `wire()`?** It does. Both scored reps
contain **23 `wire(` calls** and only 8 remaining `Arrow(` (the edge labels, which RULE 3 explicitly allows).
The router, the rule and the wired example together did the job.

**n=2, not 3.** The daily Gemini free quota (20 requests) ran out during rep 3. That is the whole budget for
2026-10-05; it resets in about 9 hours.

| context | lint | blocks | wires | regions | extras |
|---|---|---|---|---|---|
| + strict names (n=2) | 19.0 | 31.0/33 | 10.0/32 | 2.0/3 | 9.5 |
| + library fit & pacing (n=1) | 22.0 | 31.0/33 | 19.0/32 | 2.0/3 | 6.0 |
| **+ wire() router, RULES 1-4, wired example (n=2)** | **10.5** | 31.0/33 | 17.5/32 | **1.0/3** | 7.5 |

**Lint errors halved against the n=1 row, 22 -> 10.5.** That is what a
viewer actually sees: the last frame of rep 1 has orthogonal wires, nothing crossing a block name, and both
domain titles sitting above their borders. Looked at by eye, not inferred from the score.

**Wires did not move, and `bench/wire_buckets.py` says why.** It splits the connections the scorer rejected into
the three buckets that need three different fixes:

|  rep | wires_ok | unscorable | arrowhead-only | genuinely wrong or missing |
|---|---|---|---|---|
| 1 | 19/32 | 7 | 8 | **0** |
| 2 | 16/32 | 7 | 9 | **2** |

(`fidelity` was truncating `issue_details` to 20 entries, which hid the tail and made the first version of this
table a floor. The cap is now 200, and both scripts were **re-scored from disk at no cost in quota** -- the
numbers above are the complete ones.)

So of the 15 and 18 connections scored wrong, **all but 0 and 2 are not wiring mistakes**:
- **7 unscorable.** They end at `Entropy Source, CSRNG, EDN` or `Life Cycle Function Control`, two labels the
  exam input did not contain verbatim, so the end block can never match and the wire is marked wrong twice over.
- **8-9 arrowhead-only.** The right pair of blocks IS joined; only the heads differ. The truth file records the
  crossbar links as `heads: none` (plain bars in the real picture), the input wrote them as `<->`, and the model
  reasonably drew arrowheads.
- **0 in rep 1 and 2 in rep 2 genuinely wrong or missing.**

**The conclusion, and it reverses what this file said twelve hours ago:** wiring is not "far from its ceiling".
Against a fair input it is close to it. The number was being held down by the exam, not by the generator. The
sentence "wiring accuracy, not completeness" in the earlier section was wrong.

**The re-baseline (done, unmeasured).** `bench/web_inputs/peppermint.txt` has been corrected, deliberately, which
breaks comparability with every row above:
- `Entropy Source, CSRNG, EDN` is written with its commas, on its own line, flagged as one block;
- `Life Cycle Function Control` is added to the edge labels (it was missing entirely);
- the DUAL LOCKSTEP tag is described as a tag on the Ibex box, not a block, because the model kept drawing it as
  an extra block;
- the undirected links are written `--` instead of `<->`.

And the notation is now **defined for every user**, not just for the exam, in `30_user_input_notes.txt` and on
the site next to the diagram box: `->` one head at the target, `<->` a head at each end, `--` a plain link with
no head. This is a notation fix, not an exam fix: a visitor who types `<->` gets two heads, which is what they
mean by it.

**Expected next run** (state it before measuring, per the rule): unscorable 7 -> ~2 (`unlabeled_symbol` can never
match, so c25/c26 stay unscorable), arrowhead-only 8-9 -> ~0, and **wires 17.5 -> 26-29 of 32**. If it lands
there, wiring is done and the next quality problem is the one the frame shows, below. If it does not, the
remaining gap is real and is worth a rule.

**What the frames show, looked at by eye, and the next real bugs.** Both last frames were opened. Three faults,
all library guarantees rather than prompt problems, and all of them the same shape as the DomainGroup title fix:

1. **A label shrunk below readable.** The AON TL-UL Crossbar is a tall thin bar and its label is drawn at roughly
   6pt, unreadable, in **both** reps -- this is the `min_text_size` error in both. The model makes the box narrow
   because the input asks for "a tall bar", then shrinks the text until it fits. A label should never be allowed
   below readable: rotate it in a narrow tall box, or widen the box.
2. **A block escapes its region**, once per rep and a different block each time: `aon` does not contain the AON
   crossbar in rep 1, `main` does not contain `ibex_core` in rep 2. One shared bug, not two.
3. **The outer region is never drawn.** `domain 'outer'` fails in both reps -- the exam input did not name it at
   all until this session's re-baseline. That is one of the three region points, now fixed at the input.

So the regions drop (2/3 -> 1/3) is faults 2 and 3, and the unreadable crossbar label is fault 1. They are
separate: fixing the text size alone will not move regions.

**Quota note for whoever runs this next:** the free tier is 20 requests a day for `gemini-3.5-flash`, and a 3-rep
run costs 3. Spend them on the re-baseline first.

## Two library guarantees, and the hero rewritten (2026-10-05, late)

**Hero.** The tester's own sentence was better than ours, so the page now leads with it: *"A video compiler for
hardware, driven by AI"*, and says plainly that this is **not** AI video generation -- the pictures are drawn by
code, the model only writes the script. Meta description and the About paragraph follow it.

**Guarantee 1: a block title never shrinks below readable.** `IPBlock` scaled its title down without limit, which
is why the AON crossbar read at roughly 6pt in every generated chip. Now:
- a tall narrow box (height > 1.3 x width) writes its title **vertically along the bar**, which is what the
  printed diagrams do;
- the title never scales below `MIN_TITLE_FONT = 8.0` (about 9.6px cap height at 1080p, above lint's 9px error).
  A title that sticks out slightly is a layout fault the linter reports; a 4pt title is just dirt on the screen.
- `min_font_size=0` turns both off. `ipmotion/diagram.py` passes it, because the whole-chip renderer packs 44
  blocks into one frame, wraps its own labels, and the reference figure's own text is only ~8px. Without that
  opt-out it broke 8 Peppermint tests -- caught before commit, not after.

**Guarantee 2: `domain_around(title, blocks, fill)`** builds a region from the blocks inside it instead of from
hand-written x/y/w/h. A block cannot hang outside its own domain if the box is measured from the blocks. This is
the direct fix for the regions failure, which was a different block in each rep (AON crossbar, then `ibex_core`).
**RULE 5** points the model at it and says to add the region before the blocks.

**Shown without a model call**, which is the cheap way to prove a library fix: the generator's own script from
rep 1 was re-rendered against the new library. `docs/bar_label_after.png` is the result -- same model output, the
AON crossbar label now readable down the bar. The site's "what the generator makes today" clip is that same
re-render, so the page shows the current library rather than last night's.

`tests/test_readable_labels.py` (6 tests) pins both guarantees: a normal long title still shrinks, a title never
goes below the floor, a tall bar rotates, a short title in a tall bar is untouched, and every block handed to
`domain_around` is inside the box it returns. Suite is 220 green.

**Unmeasured, deliberately.** RULE 5 and `domain_around` change the prompt, so the next run measures the
re-baselined input AND these two rules together. Attribution will be muddy; the alternative was to leave a known
fix out overnight. Expect regions 1/3 -> 2-3/3 and the `min_text_size` error gone.

## Measuring without the Gemini free tier (2026-10-05, late)

The daily 20-request Gemini quota is the hard limit on how often anything here can be measured: one 3-rep run
spends three of them, and it ran out twice today. `rag_pipeline.call_llm` now takes an **OpenRouter** branch,
first in line when `OPENROUTER_API_KEY` is set, and `bench/common.MODEL` reads `IPMOTION_MODEL`:

    IPMOTION_MODEL="deepseek/deepseek-chat-v3.1" OPENROUTER_API_KEY=sk-or-... \
      python bench/run_web.py bench/web_inputs/peppermint.txt bench/web_inputs/peppermint.story.txt --reps 3

It is the same endpoint `web/app.js` calls, so a bench run through it measures what an OpenRouter visitor
actually gets, and it is the end-to-end test the new provider has not had. **The model name picks the
provider**: a slug with a `/` goes to OpenRouter, anything else to Gemini. Keying off the key alone meant
that once it was in `.env`, a run asked for `gemini-3.5-flash` would silently go to OpenRouter and still be
labelled `gemini-3.5-flash` in `final.json`. **Never mix providers inside one comparison table** -- a row is
one model.

**New SoCs are blocked on a source, not on code.** `bench/web_inputs/` holds two held-out exams that are not
chips (`systolic`, `arbiter_fsm`), and the only unused image in the repo, `openPulp_arch/pulp_story.png`, is a
platform taxonomy chart rather than an SoC floorplan -- a useful "new shape" exam, not a new SoC. Per
`docs/SOURCES.md` we do not invent hardware, so a fourth chip needs a published block diagram added to the repo
with its citation, and its truth file transcribed from that picture and approved. Waiting on the user to pick.

## The re-baselined exam: a perfect fidelity score, and the bottleneck moves to spacing (2026-10-06)

    python bench/run_web.py bench/web_inputs/peppermint.txt bench/web_inputs/peppermint.story.txt --reps 3

**n=1 again.** The quota had not reset as far as a 3-rep run was concerned; rep 2 got a 429. One run, so treat
the size of this as provisional -- but the shape of it is not ambiguous.

| context | lint | blocks | wires | regions | extras |
|---|---|---|---|---|---|
| + library fit & pacing (n=1, old exam) | 22.0 | 31/33 | 19/32 | 2/3 | 6.0 |
| + wire() router, RULES 1-4 (n=2, old exam) | 10.5 | 31/33 | 17.5/32 | 1/3 | 7.5 |
| **re-baselined exam + RULE 5 + title/region guarantees (n=1)** | 15 | **33/33** | **32/32** | **3/3** | **1** |

**Every structural number is at its ceiling.** Blocks 33/33, wires 32/32, regions 3/3, extras 1. The prediction
written down beforehand was 26-29 wires; the result beat it. The buckets are now unscorable 2 (the two wires
through the picture's unlabelled symbol, which can never match), arrowhead-only **0**, genuinely wrong **0**.

**What the model actually did**, counted in its script: `wire(` 23 times, `heads="none"` **10** times -- exactly
the 10 undirected links in the input -- and `domain_around(` **3** times, once per region. It used both new
guarantees on the first run it ever saw them.

**Honest attribution.** This run bundles the re-baselined input, the `-> / <-> / --` notation, RULE 5,
`domain_around` and the title guarantees. It cannot say which did what. The arrowhead bucket going 8-9 -> 0 is
clearly the notation; regions 1/3 -> 3/3 is clearly `domain_around` plus the outer-region line in the input. The
clean alternative was five separate 3-rep runs, which is 15 requests out of 20 a day.

**Lint got worse: 10.5 -> 15**, and that is now the whole problem. `text_overlap` 7, `min_spacing` 5,
`text_occluded` 2, `out_of_frame` 1. Looking at the frame: the boxes themselves collide -- Ibex Core overlaps
Interrupt Controller, Debug Module overlaps Life Cycle Controller -- and the bottom edge labels run into each
other and off the frame. **The picture is now correct and crowded, where before it was wrong and tidy.**

**One of those was a library fault and is fixed.** A title that refuses to shrink now hangs over its neighbours
instead ("Mailboxes (inbound & outbo" lying across the next block). `IPBlock` now **breaks a long title over up
to three lines before shrinking anything**, trying 1/2/3 lines and keeping whichever needs the least shrinking --
the same method `DomainGroup._fit_title` already used for a region title. Shown with no model call in
`docs/title_wrap_after.png`: the same script, Mailboxes now on two lines inside its box.

**The next bottleneck, stated plainly: block spacing.** Overlapping boxes are the model's own coordinates, so
this is the next thing to attack, and the choice is the usual one -- a rule ("leave 0.3 between boxes, count the
width before placing a row") or a library guarantee (a `row()`/`grid()` helper that spaces a list of blocks for
you, the way `domain_around` sizes a region). The library has won every time so far. Suite is 222 green.

## A held-out leak, found by looking for it (2026-10-06)

Three Peppermint-only strings had drifted into `00_rules.txt` as throwaway examples, and one into the Earlgrey
and Darjeeling example headers: `"Main power and clock domain"` (added by RULE 5 today), `"Memory bus egress for
Ibex and DMA"` and `"Noise source bits"` (RULE 4, yesterday), and `"Mailboxes (inbound & outbound)"` (in the
"do not shorten" example, oldest of the four). Peppermint is the exam. Those strings are now neutral inventions
(`"Compute domain"`, `"External memory port for the CPU"`, `"Entropy input"`, `"Timer Block (32-bit)"`).

**The existing leak guard did not catch it** -- it checks indexer chunks and denied paths, not the live prompt
files. `test_leakguard.py` now has a test that takes every label Peppermint has and Earlgrey and Darjeeling do
not, and fails if any of them appears in `web/rag_context/*.txt`.

**Does it invalidate the 33/32/3?** Probably not: the exam input contains those labels anyway, so the model did
not need the prompt to know them, and the leaked strings were region and edge-label names rather than the block
names being scored. But it cannot be proven either way from this run, which is reason enough to confirm at n=3
on the cleaned prompt.

**Other things tightened in the same pass:**
- `test_gemini.py` at the repo root was collected by pytest and called `genai.list_models()` on import, so every
  `pytest -q` made a live API call. Renamed to `list_gemini_models.py`. (It is a different quota metric from
  `generate_content`, so it is probably not what drained the day's 20 requests -- but a test run should not call
  anyone's API.)
- RULE 4 now tells the model never to pass `min_font_size`, which appears in the generated API signature and
  would turn the title guarantees off.
- `bench/web_inputs/pulp_platforms.*` said "four groups" and then listed five, and its story said "four" and
  named three. An exam that contradicts itself measures confusion, not the generator.
- The site's "what the generator makes today" clip is now today's run, with a caption written from its frame:
  perfect structure, colliding boxes, bottom edge labels running off the frame.
