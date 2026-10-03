# IPMotion v3
Read docs/PHASE0_FINDINGS.md and docs/PROGRESS.md at session start. Don't re-explore the repo.

## Rules
- Gold examples are read-only. Index status lives in gold_examples/MANIFEST.toml.
- Fix aesthetics before logic.
- Never commit API keys; .env stays ignored.
- One milestone per session; commit at the end; update docs/PROGRESS.md.
- Ask before installing packages or making ambiguous design decisions.

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
