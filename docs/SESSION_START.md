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

## 4b. Where wiring ended up (2026-10-06)
**Answered, at n=1.** On the re-baselined exam the generator scored **blocks 33/33, wires 32/32, regions 3/3,
extras 1** -- every structural number at its ceiling. The prediction written down beforehand was 26-29 wires.
In its own script: `wire(` 23 times, `heads="none"` exactly 10 times (the 10 undirected links), `domain_around(`
3 times. It used both new library guarantees on the first run it ever saw them.

**n=1 because the quota ran out on rep 2.** The number is provisional in size, not in shape.

**The bottleneck is now spacing, not correctness.** Lint went 10.5 -> 15 on that run: the picture is correct and
crowded where it used to be wrong and tidy. Boxes collide (Ibex Core with Interrupt Controller, Debug Module with
Life Cycle Controller) and the bottom edge labels run into each other and off the frame. One cause was the
library's own and is fixed -- a title that refuses to shrink used to hang over its neighbour, so `IPBlock` now
breaks a long title over up to three lines first. Re-linting the SAME script against the fixed library gives
**15 -> 12 errors**, measured, no model call. The rest is the model's own coordinates.

**THE FIRST COMMAND NEXT SESSION** (confirm at n=3 before building anything on this):

    python bench/run_web.py bench/web_inputs/peppermint.txt bench/web_inputs/peppermint.story.txt --reps 3
    python bench/wire_buckets.py

## 5. What to do next, in order
1. **Confirm at n=3** (above). The 33/32/3 result bundles the re-baselined input, the `-> / <-> / --` notation,
   RULE 5, `domain_around` and the title guarantees, so it attributes nothing. Confirm the size before adding to
   it.
2. **Block spacing.** The one number still bad. Same choice as every time: a rule ("leave 0.3 between boxes") or
   a library guarantee (a `row()`/`grid()` helper that spaces a list of blocks, the way `domain_around` sizes a
   region). The library has won every time so far. **Keep its rule out of the prompt until step 1 has run**, or
   the n=3 number is confounded too.
3. **New shapes, `--no-spec` (geometry only, no reference answer):**
   `bench/web_inputs/pulp_platforms.*` (a 5-group taxonomy chart with no wires between groups -- the first
   held-out exam that is not a block diagram), then `systolic.*` and `arbiter_fsm.*`.
4. **Retrieval.** With five gold examples, sending all of them is not viable. Pick the 1-2 that match the user's
   input. Stops being optional at example three.
5. **Done this session:** the re-baseline of `bench/web_inputs/peppermint.txt`, so the next measurement starts a
   new baseline block in the table.

## Waiting on the user (asked 2026-10-06, not answered)
- **Which SoC** to add as a fourth chip. They chose "I name the chip, you find it" but did not name one. Nothing
  can be built without it: `docs/SOURCES.md` forbids inventing hardware.
- **An OpenRouter key**, for the "measure on OpenRouter tonight, repeat on Gemini after the reset" plan they
  picked. The bench supports it: a model name with a `/` goes to OpenRouter, anything else to Gemini.
- **Where `openPulp_arch/pulp_story.png` came from**, before that chart appears anywhere public.

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
