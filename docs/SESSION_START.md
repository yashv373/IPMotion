# IPMotion: session start brief

Paste into a fresh Claude Code session: `Read docs/SESSION_START.md and follow it.`

---

## 1. What IPMotion is, and what "done" means
A visitor opens the website, writes a story, pastes a block diagram and an example write-up, adds their own API
key, presses Generate, downloads the `.py`, runs it locally with a manim command, and gets a **good first
animation**. That is the goal in the user's own words. If it needs more polish afterwards they can take the
script to any chat assistant; later IPMotion should do that refining itself.

**The user judges progress by the website**: how good the animation looks and how accurate it is. They have said
they have little interest in the YAML and internal design. Those stay only while they demonstrably serve the
above. Everything else is infrastructure or waste.

## 2. The two rules that were learned the hard way
1. **No unmeasured pivots.** The v4 pivot ran for three sessions and three chips before anyone checked whether it
   fed the product. It did not: a v4 run's output script is five lines, so none of it reached the prompt. The
   user said it "wasted a lot of money and effort". Before a multi-session build, get the number that would prove
   it works, even a crude one, FIRST.
2. **Examples teach a tendency; the library guarantees.** Adding a second big chip example made wiring worse. One
   rule (copy names exactly) maxed out two metrics. A library fix (DomainGroup fitting its own title) removed a
   whole class of ugliness without the model's cooperation. Prefer rules and library guarantees over more
   examples.

## 3. Load context cheaply (in this order, nothing else)
1. `docs/PROGRESS.md` — read the LAST THREE sections. They have the current numbers.
2. `docs/SOURCES.md` — what is cited and the rule for adding anything new.
3. Only if needed: `graphify-out/GRAPH_REPORT.md` for where code lives.

Do NOT list directories or grep to "get oriented".

## 4. Where things stand (2026-10-05)
**The product (the website generator).** One shot, no checking, no repair. Measured by replaying the exact
browser prompt against a held-out Peppermint exam, scored with the existing lint/conformance/fidelity checks:

| context | lint | spec | blocks | wires | regions | extras |
|---|---|---|---|---|---|---|
| 1 example (AXI only) | 13.3 | 53.3 | 29.3/33 | 16.0/32 | 0.0/3 | 15.7 |
| + Earlgrey | 16.0 | 42.3 | 30.0/33 | 18.7/32 | 0.0/3 | 8.3 |
| + Earlgrey + Darjeeling | 7.5 | 44.0 | 30.5/33 | 16.0/32 | 0.0/3 | 7.5 |
| + strict names | 19.0 | 49.0 | 31.0/33 | 10.0/32 | 2.0/3 | 9.5 |
| + library fit & pacing (**n=1**) | 22.0 | 37.0 | 31.0/33 | 19.0/32 | 2.0/3 | 6.0 |

**The ceiling with the current test input is 31/33 blocks and 2/3 regions**, because three labels the scorer
wants are not in the input verbatim. Blocks and regions are therefore AT their ceiling. **Wiring, 19/32, is the
open quality problem.**

**Live prompt contains:** rules, library API, AXI, Earlgrey, the wired SoC fabric example, input notes. Darjeeling was
removed (it cost prompt size without earning it). **Peppermint is held out and must never enter a prompt** — it
is the exam. A test enforces this.

**Gold examples** (all 0 lint errors, all cited in docs/SOURCES.md, all registered in MANIFEST.toml):
`axi_read_handshake`, `systolic_array_mac`, `mesi_cache_fsm`, `lockstep_safety_island`, `cim_crossbar_array`.
The last four are **deliberately not in the live prompt yet** — they are unmeasured.

## 4b. The one open question, ANSWERED (2026-10-05, evening)
**Does the model call `wire()`? Yes.** 23 `wire(` calls per script, 8 `Arrow(` left (the edge labels RULE 3
allows). Lint errors halved, 22 -> 10.5. See the last section of `docs/PROGRESS.md` for the numbers.

**The new finding: "wires 17.5/32" was mostly the exam, not the generator.** `bench/wire_buckets.py` splits the
rejected connections: 7 unscorable (an end-block label was not in the input verbatim), 8-9 arrowhead-only (the
right pair IS joined, only the heads differ), and 0 and 2 genuinely wrong. The exam input has been re-baselined and the `-> / <-> / --`
notation is now taught to every user. **That re-baseline is unmeasured**: the Gemini free tier (20/day) ran out.

**THE FIRST COMMAND NEXT SESSION** (quota resets ~05:00 local):

    python bench/run_web.py bench/web_inputs/peppermint.txt bench/web_inputs/peppermint.story.txt --reps 3
    python bench/wire_buckets.py

**Predicted**: unscorable 7 -> ~2, arrowhead-only -> ~0, wires 17.5 -> 26-29 of 32. Numbers below that mean the
remaining gap is real. Numbers at it mean wiring is done, and the next bug is the one named below.

**The next quality bugs, seen in both last frames, not started.** Three, all library guarantees:
1. the AON TL-UL Crossbar label is drawn at ~6pt and unreadable in both reps (`min_text_size`). A label must
   never shrink below readable -- rotate it in a narrow tall box, or widen the box;
2. one block escapes its region per rep, a different one each time (AON crossbar, then `ibex_core`);
3. the outer region was never drawn, because the exam input never named it. Fixed at the input this session.
Faults 2 and 3 are the regions drop, 2/3 -> 1/3. Fault 1 is separate; fixing text size will not move regions.

## 5. What to do next, in order
1. **Measure the re-baselined exam** (3 reps, 3 of the day's 20 calls) and run `bench/wire_buckets.py`. This is
   the number that says whether wiring is finished. Prediction is written in 4b; compare against it honestly.
2. **The unreadable AON crossbar label** (4b). A library guarantee: a label never shrinks below readable. Expect
   it to move regions 1/3 -> 2/3 and remove the `min_text_size` lint error.
3. **Measure a new shape going in.** Held-out exams are ready: `bench/web_inputs/systolic.*` and
   `bench/web_inputs/arbiter_fsm.*`. Score them with `--no-spec` (geometry only; there is no reference answer
   for a shape we invented the exam for).
4. **Retrieval.** With five gold examples, sending all of them is not viable — the prompt was already 85k
   characters with two. Pick the 1-2 that match the user's input. This is the user's own idea and it stops being
   optional at example three.
5. **Done this session:** the re-baseline of `bench/web_inputs/peppermint.txt`. It breaks comparability with
   every row above, so the next measurement starts a new baseline block in the table.

## 6. How to work
- **Measure before you build.** State the number you expect to move before starting.
- **Verify by eye.** Lint passing is not the same as looking right: the MESI labels passed lint while sitting on
  their own arcs, and a wordline bug that put four lines on one point passed lint too. Render a frame and look.
- **Check the live site after deploying.** A green Pages build has twice served a 404 asset (`*.mp4` is
  gitignored; a trailing comment broke the exception). Always curl the URL.
- Never put backslash escapes in a Bash heredoc — this environment eats them. Use the Write/Edit tools.
- Project rules in CLAUDE.md still apply: aesthetics before logic, gold examples read-only, never commit `.env`.
- End every summary with a plain-words "What to look at" section listing full Windows paths.

## 7. End of session
1. `pytest -q` green (198 at the time of writing).
2. Update `docs/PROGRESS.md` with numbers, not adjectives.
3. Commit, push, and confirm the deploy actually serves what you changed.
