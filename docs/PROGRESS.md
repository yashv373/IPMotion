# IPMotion v3: Progress

| Milestone | Scope | Status |
|---|---|---|
| M0 | Housekeeping: git, .gitignore, scipy mock removal, MANIFEST, pytest, docs | Done (2026-10-03) |
| M1 | A (port API) + C (geometric lint) + tests | **Next** |
| M2 | B (STYLE.md + style.toml) | Pending |
| M3 | F (LLM layer) + G (run logging) | Pending |
| M4 | E (ordered repair loop) | Pending |
| M5 | D (vision critique, behind a flag) | Pending |
| M6 | H (approve CLI + incremental indexing) | Pending |

## M0 notes
- The real scipy now loads from the project root. AXI renders correctly from the root (frame checked).
- `darjeeling_full` is not clean, so it is not a second baseline (see `MANIFEST.toml`).
- Open for M1:
  - Fix `Banner.update_text` draw order (dim banner text).
  - Decide whether to add a `text_occluded` lint check.
- `indexer.py` does not read `MANIFEST.toml` yet; that is planned for M6. Until then, don't re-run the v2 indexer.
