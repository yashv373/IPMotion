# IPMotion v3
Read docs/PHASE0_FINDINGS.md and docs/PROGRESS.md at session start. Don't re-explore the repo.

## Rules
- Architecture facts come only from bench/truth/*.yaml (transcribed from opentitan_archs/ and openPulp_arch/). Never from memory. Truth files are never indexed or put in prompts.
- Gold examples are read-only. Index status lives in gold_examples/MANIFEST.toml.
- Fix aesthetics before logic.
- Never commit API keys; .env stays ignored.
- One milestone per session; commit at the end; update docs/PROGRESS.md.
- Ask before installing packages or making ambiguous design decisions.

## Keeping the user in the loop
- End every milestone or benchmark summary with a "What to look at" section. Use plain, simple words.
- List full Windows paths (C:\Users\Asus\Documents\IPMotion\...), one line each saying what to check:
  - the report/review HTML to open first: C:\Users\Asus\Documents\IPMotion\bench\report.html (the user keeps it open in a browser tab and refreshes it; keep updating it and say when to look)
  - the final script and last frame of each run
  - any file the user must review or approve (truth files, specs)

## Commands
- Render: python -m manim render -ql --progress_bar none -v WARNING <file> <Scene>
- Single frame: add -s
- Tests: pytest -q
- Render scratch output outside the project root.

## Token hygiene
- Read only the files and line ranges you need; don't cat whole files.
- Summarize tool output; never paste raw logs or full lint dumps.

# Compact instructions
Preserve: current milestone, decisions made, failing checks, file paths changed.
