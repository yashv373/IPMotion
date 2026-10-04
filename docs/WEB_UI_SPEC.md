# IPMotion Web UI — Spec (plan only, nothing built yet)

Status: **built** (2026-10-04). Decisions: v3 .py output only; no truth files in rag_context (user's own pasted diagram text goes in the prompt); GIFs rendered from existing scripts; Gemini `gemini-3.5-flash` default + Anthropic `claude-opus-5-5` option; OpenAI dropped; Actions workflow for hosting; `web/make_context.py` built (regenerates the API digest + example). Parallel track; the Python engine in `ipmotion/`
is not touched.

Attribution string, used verbatim in the header, the footer and the About block of every page:

> Ideated by Yashvardhan Singh | Development by Claude Code

## 1. What it is

A static, zero-backend site in `web/`, hosted on GitHub Pages. The visitor brings their own LLM API
key. The page stuffs our library rules + gold example into one prompt, calls the LLM **from the
browser**, and hands back a Manim script they run locally. We pay for nothing and run nothing.

## 2. Files (all of them)

```
web/
  index.html          Home: hero, gallery, generator form, output
  how-it-works.html   Pipeline explainer
  changelog.html      Milestones + link to the benchmark report
  style.css           One stylesheet, dark by default
  app.js              One script: key storage, prompt build, fetch, output
  rag_context/
    00_rules.txt        library rules + hard don'ts  (~4 KB; from rag_pipeline.SYSTEM_PROMPT + PHASE0 findings)
    10_library_api.txt  public API of ipmotion_lib   (~12 KB; class/signature list, NOT the 70 KB source)
    20_example_axi.txt  gold_examples/axi_read_handshake.py (3.5 KB; the ONLY indexable gold file)
    30_story_format.txt story YAML shape + a sample  (~2 KB; from bench/stories/*.yaml)
  assets/gifs/*.gif   gallery placeholders (empty at first; see open question 3)
.github/workflows/pages.yml   (repo root, see section 6)
```

Header/footer markup is duplicated in the three HTML files. No templating, no build step, no npm,
no Vite — Pages serves these as-is.

### RAG context budget

~21 KB of context (~6k tokens) plus the user's story and layout file. `ipmotion_lib.py` is 69 KB on
its own, so we ship a hand-written API digest instead of the source. Only `axi_read_handshake.py` is
`status = "indexable"` in `gold_examples/MANIFEST.toml`; every other gold file is `excluded` /
`known_bad` and must **not** go into `rag_context/` — stuffing `darjeeling_full.py` would teach the
model overlapping blocks.

These `.txt` files are a **manual snapshot** and will drift from the repo. A ~20-line
`web/make_context.py`, run by hand when the library changes, can regenerate them — not a backend,
never executed by the site. Optional; see open question 6.

## 3. Page 1 — Home

- **Hero:** what IPMotion is, in plain words; attribution; button down to the generator.
- **Gallery:** one card per chip — Darjeeling, Earlgrey (Peppermint once it has a layout file).
  GIF placeholder plus 2–3 lines on what the animation shows. All chip facts (block names, counts)
  are copied from `bench/truth/*.yaml` and the PROGRESS numbers, never from memory.
- **Generator form:**
  - API key (`type="password"`), provider select, model text field (free text, default
    `gemini-3.5-flash`, the model the benchmark used).
  - Story / prompt textarea.
  - Block-diagram structure: textarea plus "load file" (`<input type="file">` read with
    `FileReader`) — the file never leaves the browser except inside the prompt.
  - Buttons: Generate, Forget key.
- **Output:** `<pre><code>` filled with `textContent` (never `innerHTML`), a Download `.py` button
  (`Blob` + `URL.createObjectURL`), and the Local Setup box (section 5).

## 4. The generate path (`app.js`, ~120 lines)

1. `Promise.all(rag_context/*.txt -> fetch -> text())`, concatenated in filename order.
2. Build one prompt: rules + API digest + example + story format + user story + user layout text.
3. One `fetch` to the chosen provider, key from the form / `localStorage`:

| Provider | Endpoint | Auth headers | Browser-direct |
|---|---|---|---|
| Google Gemini (default) | `https://generativelanguage.googleapis.com/v1beta/models/<model>:generateContent` | `x-goog-api-key: <key>` | yes, CORS allowed |
| Anthropic | `https://api.anthropic.com/v1/messages` | `x-api-key: <key>`, `anthropic-version: 2023-06-01`, **`anthropic-dangerous-direct-browser-access: true`** | yes, with that header. Default model `claude-opus-5-5` |
| OpenAI | `https://api.openai.com/v1/chat/completions` | `Authorization: Bearer <key>` | **must be verified in a real browser before shipping**; if CORS blocks it the option is dropped, not proxied |

4. Strip ```` ```python ```` fences from the reply — a JS port of `rag_pipeline._clean_response`.
5. Show the script. Errors (401, 429 / quota, CORS) are shown as plain text, never swallowed.

No lint, no conformance check, no repair loop runs in the browser: it is one shot. The page says so
in those words.

### Key handling ("securely" = as good as a static page gets)

- `localStorage` only, and sent nowhere except the chosen provider's endpoint.
- No CDN, no third-party script, no analytics anywhere on the site — any injected script could read
  `localStorage`.
- LLM output rendered with `textContent` only.
- "Forget key" button clears it.
- Honest note on the page: a browser-stored key is readable by any script running on this origin,
  and GitHub Pages is a shared `github.io` origin unless a custom domain is used. Use a key with a
  spend cap.

## 5. Local Setup box (must be honest)

The generated script imports `ipmotion_lib`; the v4 path also needs `ipmotion/` and the YAML files.
`manim -pql script.py` on the bare download fails with `ImportError`. So the box says:

```
git clone https://github.com/yashv373/IPMotion
cd IPMotion
pip install "manim==0.21.0"      # no LaTeX needed; MathTex/Tex are forbidden
# save the script in this folder, then:
python -m manim render -ql --progress_bar none -v WARNING script.py SceneName
```

## 6. Page 2 and Page 3

- **How It Works:** truth files -> layout -> `ipmotion/diagram.py` draws regions/blocks/wires ->
  `player.py` plays the story -> `lint` (6 geometric checks, snapshot after every `play()`/`wait()`)
  -> `conformance.py` (labels, banners, wires, domains) -> `fidelity.py` score ->
  `bench/report.html`. It states plainly which parts run locally and which the browser skips.
- **Changelog:** M0 through M1.6 from `docs/PROGRESS.md`, plus a prominent "Open the benchmark
  report" button.

### Hosting and the report link

Branch-based Pages can only serve `/` or `/docs`, so publishing `web/` needs a GitHub Actions
workflow (`actions/upload-pages-artifact` with `path: web`) — config, not backend code.
`bench/report.html` is 9.1 MB and fully self-contained (every image is a `data:` URI; no external
`src` or `href`), so the workflow **copies** it into the artifact as `report.html`. Nothing is
duplicated in git. Alternative, if you would rather not add a workflow: publish the repo root and
put a redirect `index.html` there.

## 7. Open questions (need your answer before coding)

1. **Which output, v3 or v4?** v3 = the LLM writes a whole Manim script against `ipmotion_lib`
   (self-contained, which is what "download a .py" implies). v4 = `diagram.py` / `player.py` draw
   from truth + layout and the LLM writes only the story YAML — better output, but PROGRESS says the
   LLM story step is not built, and the download would be a story YAML plus a 4-line scene file.
   **Recommendation: v3 only**, with the uploaded layout/truth text used as prompt context; v4 as a
   later mode.
2. **CLAUDE.md says "Truth files are never indexed or put in prompts."** My reading: that bans
   `bench/truth/*.yaml` from `web/rag_context/` (they will not go there, not even as a format
   example), but a visitor's *own* uploaded file is user input and does go into their prompt.
   Please confirm.
3. **GIFs.** None exist in the repo (`media/` is gitignored). Ship CSS placeholders now and you
   record the GIFs later, or add a step that exports GIFs from the two existing runs?
4. **Default provider and model.** Gemini + `gemini-3.5-flash` to match the benchmark, or
   Anthropic + `claude-opus-5-5`?
5. **Hosting choice** — Actions workflow (recommended) or publishing the repo root.
6. **`web/make_context.py` regenerator** — build it or skip it?

## 8. Test plan

`fetch()` of local `.txt` files fails under `file://`, so testing is `python -m http.server` run
from `web/`, opened at `http://localhost:8000`. Checks: context files load; the prompt assembles
(log its length); one real key call per provider; fence stripping; download; Forget key; dark and
light; phone width; the report button.

## 9. Where we are leaving off

Spec written. Nothing exists in `web/` yet, and no file outside `docs/WEB_UI_SPEC.md` was touched.
Next action: your answers to section 7, then build the three pages, `style.css`, `app.js` and
`rag_context/`.

---

Ideated by Yashvardhan Singh | Development by Claude Code
