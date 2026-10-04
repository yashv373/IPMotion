# Web UI handoff (for the main IPMotion builder)

Written 2026-10-04 by the web-track session. Read this before touching `web/` or anything it mirrors.
Full plan and decisions: docs/WEB_UI_SPEC.md. The Python engine (`ipmotion/`, `ipmotion_lib.py`) was NOT changed.

## How the main builder must treat web/ (user decision, 2026-10-04)
**The website is the surface the user judges progress by.** From here on, a milestone is not done until the
site shows it. `web/` is kept in sync in the SAME commit as the engine change, not left for a later session:
- `ipmotion_lib.py` or `gold_examples/axi_read_handshake.py` changed -> re-run `python web/make_context.py`.
- Lint thresholds, banned constructs or the system prompt changed -> hand-edit `rag_context/00_rules.txt`.
- A milestone finished -> add its row to `web/changelog.html`, in the same plain words as docs/PROGRESS.md.
- A new chip or example rendered -> add its card and GIF to the gallery in `web/index.html`.
- **Pushing a rebuilt `bench/report.html` publishes it.** The Pages workflow fires on `bench/report.html` as
  well as `web/**`, so a report rebuild is an outward-facing change. Expect it, or do not push the report.

## What exists
A static, zero-backend site in `web/`, deployed by `.github/workflows/pages.yml` (pushes touching `web/**` or
`bench/report.html`; the workflow copies `bench/report.html` into the artifact as `report.html`).
Live URL (once Pages source = "GitHub Actions"): https://yashv373.github.io/IPMotion/

| File | Role |
|---|---|
| `web/index.html` | Hero, GIF gallery (Darjeeling, Earlgrey, AXI), generator form, output + "Local setup" box |
| `web/how-it-works.html` | Pipeline explainer (truth/layout, schemas, ports, renderer-in-the-loop, 6 lint checks, conformance/fidelity, repair order, v3 vs v4) |
| `web/changelog.html` | Milestone table + button to `report.html` |
| `web/app.js` | The only script. Key in localStorage, builds prompt, calls LLM, renders output |
| `web/style.css` | Dark by default (`data-theme="dark"` on `<html>`), tokens in `:root` |
| `web/rag_context/*.txt` | The prompt context (see below) |
| `web/make_context.py` | Hand-run regenerator for two of the context files |
| `web/assets/gifs/*.gif` | 480px, 5fps, 16-colour GIFs rendered from existing scripts (~8 MB total) |

Header, footer and About block on every page carry: "Ideated by Yashvardhan Singh | Development by Claude Code" (exact text, required).
The three pages are plain hand-edited HTML with duplicated header/footer. No build step, no npm.

## User flow (generator on index.html)
1. User picks provider (Gemini default `gemini-3.5-flash`, or Anthropic `claude-opus-5-5`), optional model override, pastes API key.
   Key and provider/model are saved in `localStorage` (`ipm_key`, `ipm_provider`, `ipm_model`) and sent only to the provider. "Forget key" clears it.
2. User writes a Story and optionally pastes or loads (FileReader) a block-diagram text (any readable format).
3. Generate: `app.js` fetches `rag_context/00_rules, 10_library_api, 20_example_axi, 30_user_input_notes` in that order,
   joins them with `=====`, appends `## USER BLOCK DIAGRAM` and `## USER STORY`, and POSTs once straight to the provider
   (Anthropic needs the `anthropic-dangerous-direct-browser-access` header). Markdown fences are stripped (port of `rag_pipeline._clean_response`).
4. Output goes into `<code>` via `textContent` only. Buttons: Download .py (Blob), Copy. Errors (401/429/CORS) are shown as text.
5. The page tells the user plainly: one shot, no lint, no conformance check, no repair loop in the browser.
   The Local Setup box says to clone the repo (the script imports `ipmotion_lib`), `pip install "manim==0.21.0"`, then `manim -pql script.py SceneName`.

## Rules the web side depends on (keep in sync)
- **Output is v3 only** (LLM writes a whole Manim script). v4 (diagram.py/player.py + story YAML) is not exposed; its LLM story step is unbuilt.
- **`rag_context/` is a snapshot and drifts.** `10_library_api.txt` (signatures from `ipmotion_lib.py`) and `20_example_axi.txt`
  (copy of `gold_examples/axi_read_handshake.py`) are produced by `python web/make_context.py`. Re-run it after any change to
  `ipmotion_lib.py` or that gold file. `00_rules.txt` and `30_user_input_notes.txt` are hand-written; update `00_rules.txt`
  when lint thresholds or banned things change (it mirrors rag_pipeline.SYSTEM_PROMPT + the lint rules; no MathTex/Tex).
- **Only `indexable` gold files may go in rag_context** (MANIFEST.toml). Today that is only axi_read_handshake.
- **No truth files in rag_context** (CLAUDE.md rule). A visitor's own pasted diagram is their input, not ours.
- **No third-party scripts/CDN/analytics on the site.** Any injected script could read the stored API key.
- OpenAI was dropped: CORS from a browser was never verified.

## Not done / not verified
- No real LLM call has been tested (needs a key): the generator form is the one unverified path.
- Pages deploy IS confirmed live (2026-10-04): /, /changelog.html, /report.html, the gallery GIFs and
  /rag_context/*.txt all return 200 at https://yashv373.github.io/IPMotion/ and serve the current content.
- The Darjeeling GIF shows the banner text mid-change in some frames (the known "text at a keyframe can be caught mid-change" limit).
- Gallery text and changelog rows are hand-copied from docs/PROGRESS.md, so they go stale unless the rule above is kept. Nothing enforces it yet: two cheap tests would (rag_context holds no truth-file chip name; 20_example_axi.txt still matches the gold file).
- Regenerate GIFs: `python -m manim render -ql --format gif --fps 12 --media_dir <scratch> <file> <Scene>`, then ffmpeg
  down to 480px/5fps/16 colours (raw output is ~30 MB each).

## Test
`cd web && python -m http.server 8000`, open http://localhost:8000 (fetch() of the .txt files fails under file://).
