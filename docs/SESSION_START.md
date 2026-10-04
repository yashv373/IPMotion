# IPMotion: session start brief

Paste into a fresh Claude Code session: `Read docs/SESSION_START.md and follow it.`

---

## 1. Who you are working for and what IPMotion is
IPMotion turns a hardware block diagram (e.g. OpenTitan Darjeeling, Earlgrey) plus a short "story"
(e.g. "Ibex reads from the UART") into a presentation-ready Manim animation that is overlap-free,
text-clean and a 1:1 recreation of the reference picture. The long-term goal (docs/IPMotion_PRD.md)
is a Renderer-in-the-Loop engine: generate -> lint -> check conformance -> repair, with no human
acting as the layout engine. The user judges results by eye in bench/report.html.

## 2. Load context cheaply (do this first, in this order, and nothing else)
1. `docs/PROGRESS.md`: milestone table + what each milestone built and its known limits.
2. `graphify-out/GRAPH_REPORT.md`: the codebase map (communities, hubs, key classes).
3. Only if needed: `docs/PHASE0_FINDINGS.md` (repo facts) and `docs/SPEC.md` (spec format).

Do NOT list directories, cat whole files, or grep the repo to "get oriented". For any question
about where something lives or how pieces connect, use `graphify query "<question>"` first, then
open only the exact file and line range it points to.

## 3. Where things stand (as of 2026-10-04, confirm against PROGRESS.md)
- Done: M0 housekeeping, M1 port API + geometric lint, M1.6 whole-diagram polish + Earlgrey.
- M1.5 still open: v3 x3 Darjeeling re-run and Earlgrey/Peppermint benchmark runs, blocked by the
  daily Gemini free quota (`python bench/run_all.py <spec> --reps 3`, state in runs/bench_state.json).
- Open follow-ups from M1.6: user review of the Darjeeling report (12 unconfirmed items) and the
  Earlgrey render; Peppermint has truth but no layout file.
- Next in the plan: M2 = STYLE.md + style.toml layout conventions. Then M3 LLM layer + run logging,
  M4 ordered repair loop, M5 vision critique (flagged), M6 approve CLI + incremental indexing.
- Test suite: 181 passing. Keep it green.

## 4. What to do this session
1. Summarise in at most 10 lines: current milestone, what is left, any blockers.
2. Propose the next unit of work as 2-3 options (e.g. Peppermint layout to prove a third chip,
   start M2, or resume the M1.5 benchmark), each with: goal, files touched, how we verify it,
   rough size (S/M/L). Recommend one.
3. **Stop and wait for my choice.** Do not write code before I pick.
4. Once I pick: write a short plan (steps + acceptance checks), then build it step by step.

## 5. How to work
- **Skills:** use the installed agent-skills when they fit: spec/plan before building,
  test-driven development for new logic, code review before committing. Say which skill you are using.
- **Keep it small (YAGNI):** reuse existing code in `ipmotion/` and `ipmotion_lib.py` before adding new
  code; no new dependencies without asking; no speculative abstractions.
- **Project rules (from CLAUDE.md) still apply:** aesthetics before logic; gold examples are read-only;
  feedback order stays runtime -> spec conformance -> lint; never commit `.env`.
- **Verification is not optional:** a step is done only when `pytest -q` passes and, for anything
  visual, a single-frame render (`-s`) has been checked. Render scratch output outside the project
  root. Report fidelity/lint numbers the same way PROGRESS.md does.
- **Be honest about limits:** the fidelity numbers compare the drawing with hand-written notes, not the
  picture. Don't claim a visual result is correct without showing me the frame.
- **Ask before:** installing packages, changing thresholds in style.toml, changing the spec format,
  touching gold examples, or any ambiguous design decision.

## 6. Token discipline
- Read only the files and line ranges you need. Summarise tool output; never paste raw logs.
- Don't rebuild the knowledge graph. After large code changes run `graphify . --update`.
- One milestone (or one sub-task) per session. If the conversation gets long, tell me and suggest
  `/compact` or a fresh session.
- Use subagents only for clearly separable work, and tell me before launching one.

## 7. End of session (always)
1. `pytest -q` green.
2. Update `docs/PROGRESS.md`: milestone table + a short section (goal, what was built, results, known
   limits, next). Same plain style as the existing entries.
3. `graphify . --update` if code changed meaningfully.
4. Commit with a clear message. Tell me what to review (e.g. refresh bench/report.html).
