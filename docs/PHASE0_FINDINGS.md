# IPMotion v3: Phase 0 Findings (2026-10-03)

## Library structure (`ipmotion_lib.py`)
- **Diagram blocks:** `IPBlock`, `GlowBox`, `Banner`, `DomainGroup` are VGroups exposing `.bg` and `.txt`.
  - `IPBlock(ports=[{'label','edge'}])` only draws a 10pt label inside the edge. It creates no connectable point.
  - Edge names are `RIGHT/LEFT/UP/DOWN`.
- **Symbols:** `HWComponent` subclasses (gates, MUX/DEMUX, adder, ALU, DFF, latch, regfile, FIFOs, MOS, R/C, GND/VDD, bus, crossbar, SKY130 cells, `CustomMacro`) store named pins as invisible `Dot`s in `self.pins`.
  - `get_pin(name)` returns a position. Pins follow `move_to`/`scale` because they are real mobjects.
  - There is no side information. `CustomMacro` uses `TOP/BOTTOM/LEFT/RIGHT`, which is inconsistent with `IPBlock`.
  - `SHAPE_REGISTRY` maps names to classes.
- **Connectors:**
  - `Wire` goes from edge center to edge center, straight or as a 3-segment Manhattan route, or follows `waypoints`.
  - `DirectRoute` and `ManhattanRoute` add a glow and a `.transfer()` packet animation.
  - The gold examples mostly use raw `Arrow(a.get_right()+UP*k, b.get_left()+UP*k, buff=0.1)`.
- **Bug: `Banner.update_text`** returns `AnimationGroup(Transform(txt), bg.animate…)`. On play, Manim adds `Group(txt, bg)` to the scene in that order and drops `Banner` from the top level. The 0.9-opacity background is then drawn over the text, so banner text renders dim after the first update. Verified by probe; fix it in the library, never in the gold examples.

## Gold-example patterns
- **Layout:**
  - `VGroup(master, slave).arrange(RIGHT, buff=4.5)`: master on the left, slave on the right, signal flow left to right.
  - Parallel channels use edge anchors with offsets (`get_right() + UP*0.5/0.2/-0.2/-0.5`) and arrows with `buff=0.1`.
  - Channel labels are 15pt Consolas, placed with `next_to(arrow, UP/DOWN, buff=0.1)`.
  - Large diagrams (Darjeeling) use absolute `move_to` on a big canvas, then `scale_to_fit_height(frame_h*0.9)` and `center()`.
- **Colors:**
  - AXI uses `BLUE` for data, `GREEN` for control/valid, `YELLOW` for active, `GRAY` for inactive.
  - The Darjeeling scripts use `Theme` instead: active `#00FFF0`, success `#39FF14`, warning `#FFD700`, error `#FF003C`, stroke `#3A506B`, background `#05050A`.
- **Pacing:**
  - Each step is a `banner.update_text("Cycle N: …")`, then one state change per `play()`.
  - `wait(0.5)` between cycles, `run_time=0.3` for color flashes, a closing wait of 1–2s.
- **Text:** Consolas everywhere. Block titles are 16pt bold, auto-shrunk to fit.

## Environment
- Python 3.12.10, Manim 0.21.0, numpy 2.5.3, pycairo 1.29.1, ffmpeg 9.0.1, chromadb 1.5.9, sentence-transformers 6.1.0, scipy 1.18.1, pytest 9.1.1 (installed in M0).
- **No LaTeX:** `MathTex`/`Tex` must not be used, and the prompt and linter should forbid them.
- `google-generativeai` 0.8.6 is deprecated in favor of `google-genai`. Decide at milestone F.
- **Root cause of corrupted renders:** a mock `scipy/` in the project root (identity `Rotation`) shadowed the real scipy. It produced upside-down text and skewed rounded boxes, and broke sentence-transformers. It was removed in M0. The PRD has a correction note: the "PyAV stride bug" was this mock.
- Lint feasibility: a prototype with `config.dry_run=True` and patched `Scene.play`/`Scene.wait` captured 34 geometry snapshots of the AXI scene with no rendering. It took 26s because it still steps frames. Jumping each animation straight to its end state should get it under 3s.

## Gold-example status
See `gold_examples/MANIFEST.toml`.
- `axi_read_handshake`: zero-error lint baseline.
- `darjeeling_full`: renders but has block overlaps and text overflow, so it is **not** a baseline. Marked `known_bad`.
- `symbol_showcase`: excluded, `known_bad`. The banner sits off frame and the labels are about 8px tall.
- `darjeeling_v3_polished`, `darjeeling_v4_advanced`, `fifo_backpressure_test`: excluded because they call classes that don't exist.
- `darjeeling_exact`: excluded because it sets `config.pixel_width` and doesn't use the library.

## Decisions (user, 2026-10-03)
1. M0 order: git init, `.gitignore`, a baseline commit that includes `scipy/`, then a separate commit deleting `scipy/` and adding the PRD note.
2. pytest approved and installed.
3. `MANIFEST.toml` holds index status. The 3 broken scripts, `darjeeling_exact` and `symbol_showcase` are excluded. The user will provide the old library that had the missing classes separately.
4. Lint baseline is AXI with zero errors. Edge-hugging counts as a warning, not an error. `symbol_showcase` is a known-bad fixture: lint must report its off-frame banner and tiny labels. `darjeeling_full` would be a second baseline only if clean, and it is not.

## v3 plan
`ipmotion_lib.py` stays at the root (gold examples import it). Changes to it are additive and backward compatible.
```
ipmotion/
  style.toml, style.py      # B: machine-readable style; loader shared by prompt + linter
  lint/harness.py           # C: subprocess, dry_run, snapshot after each play()/wait()
  lint/checks.py            # C: one function per check
  lint/report.py            # C: JSON report, deduped across snapshots
  llm/ (base, gemini, cache)   # F
  runlog.py                 # G: runs/<timestamp>/
  repair/loop.py            # E
  vision/critique.py        # D
  rag/ (indexer, retrieve)  # H
  cli.py                    # python -m ipmotion run|lint|approve|index
docs/STYLE.md
tests/test_ports.py, tests/test_lint_checks.py, tests/fixtures/broken/*.py
runs/ (ignored), verified_examples/
```
- **A. Ports:**
  - `Port(name, side)` is an invisible Dot subclass.
  - `block.port(name)` returns it, with `.get_center()` and `.side` in {LEFT, RIGHT, UP, DOWN}.
  - `IPBlock(ports=[...])` turns the existing dicts into real ports, evenly distributed along the edge; label drawing is unchanged.
  - `HWComponent` pins become Ports, with the side inferred from the pin's position relative to the body. `get_pin()` and `.pins` keep working.
  - `Connection(src_port, dst_port, style="direct"|"manhattan")` routes the first segment outward along the source side and records `.src`/`.dst`.
- **C. Lint:**
  - After every `play()`/`wait()`, record each visible leaf's bounding box and type (text, block, connector, container).
  - Name each object by its variable name from `construct()`'s locals, and record the source line of the triggering call.
  - Checks:
    - `text_overlap`
    - `dangling_endpoint` (within buff + ε of a port or block boundary)
    - `out_of_frame` (error outside the frame, warning inside the margin)
    - `min_spacing`
    - `min_text_size` (pixel height at 1080p)
  - Objects at opacity 0 are ignored. Severities are error and warning; only errors fail the repair loop.
  - Report entries: `{check, severity, objects:[{name,type,bbox}], detail, snapshot, t, source_line}`.
  - Candidate extra check: text occluded by a filled shape drawn later. It would catch the `Banner.update_text` bug.
- **Milestones:**
  - **M0:** housekeeping (done).
  - **M1:** A + C. Ports, lint, 3–4 broken AXI fixtures (overlap, dangling wire, off frame, tiny text), and tests. AXI must report zero errors; `symbol_showcase` must report the banner and labels.
  - **M2:** B (style).
  - **M3:** F + G (LLM layer, run logging).
  - **M4:** E (repair loop).
  - **M5:** D (vision critique).
  - **M6:** H (approve and incremental index; the indexer reads `MANIFEST.toml`).
