// IPMotion generator: runs entirely in the browser. No backend.
const $ = (id) => document.getElementById(id);
const CTX = ["00_rules", "10_library_api", "20_example_axi", "25_example_earlgrey", "26_example_darjeeling", "30_user_input_notes"].map((n) => `rag_context/${n}.txt`);
const DEFAULT_MODEL = { gemini: "gemini-3.5-flash", anthropic: "claude-opus-5-5" };
const store = {
  get: (k) => { try { return localStorage.getItem(k) || ""; } catch { return ""; } },
  set: (k, v) => { try { v ? localStorage.setItem(k, v) : localStorage.removeItem(k); } catch {} },
};

// Fetch the static context files and join them with the user's input into one big prompt.
async function buildPrompt(story, diagram) {
  const parts = await Promise.all(CTX.map(async (u) => {
    const r = await fetch(u);
    if (!r.ok) throw new Error(`Could not load ${u} (${r.status})`);
    return r.text();
  }));
  return parts.join("\n\n=====\n\n") +
    "\n\n=====\n\n## USER BLOCK DIAGRAM\n" + (diagram.trim() || "(none given)") +
    "\n\n## USER STORY\n" + story.trim() +
    "\n\n## OUTPUT\nReturn ONLY the complete Python script.";
}

// Same job as rag_pipeline._clean_response: drop markdown fences if the model added them.
function cleanResponse(t) {
  const m = t.match(/```(?:python)?\s*\n([\s\S]*?)```/);
  return (m ? m[1] : t).trim() + "\n";
}

async function callLLM(provider, model, key, prompt) {
  let res, data;
  if (provider === "anthropic") {
    res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json", "x-api-key": key,
        "anthropic-version": "2023-06-01", "anthropic-dangerous-direct-browser-access": "true",
      },
      body: JSON.stringify({ model, max_tokens: 16000, messages: [{ role: "user", content: prompt }] }),
    });
  } else {
    res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-goog-api-key": key },
      body: JSON.stringify({ contents: [{ role: "user", parts: [{ text: prompt }] }], generationConfig: { temperature: 0.2 } }),
    });
  }
  data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = (data.error && (data.error.message || data.error)) || res.statusText;
    throw new Error(`${provider} returned ${res.status}: ${typeof msg === "string" ? msg : JSON.stringify(msg)}` +
      (res.status === 429 ? "\n(Quota or rate limit reached.)" : ""));
  }
  const text = provider === "anthropic"
    ? (data.content || []).map((b) => b.text || "").join("")
    : ((data.candidates || [])[0]?.content?.parts || []).map((p) => p.text || "").join("");
  if (!text) throw new Error("The model returned no text.\n" + JSON.stringify(data).slice(0, 400));
  return cleanResponse(text);
}

async function generate() {
  const provider = $("provider").value, model = $("model").value.trim() || DEFAULT_MODEL[provider];
  const key = $("key").value.trim(), story = $("story").value;
  $("err").textContent = "";
  if (!key) return ($("err").textContent = "Enter your API key.");
  if (!story.trim()) return ($("err").textContent = "Write a story first.");
  store.set("ipm_key", key); store.set("ipm_provider", provider); store.set("ipm_model", $("model").value.trim());
  $("go").disabled = true; $("status").textContent = "Loading context...";
  try {
    const prompt = await buildPrompt(story, $("diagram").value);
    $("status").textContent = `Prompt is ${prompt.length.toLocaleString()} characters. Waiting for ${provider}...`;
    $("code").textContent = await callLLM(provider, model, key, prompt); // textContent only, never innerHTML
    $("out").hidden = false; $("out").scrollIntoView({ behavior: "smooth" });
    $("status").textContent = "Done.";
  } catch (e) {
    $("err").textContent = String(e.message || e);
    $("status").textContent = "";
  } finally { $("go").disabled = false; }
}

$("provider").value = store.get("ipm_provider") || "gemini";
$("key").value = store.get("ipm_key");
$("model").value = store.get("ipm_model");
const setPh = () => ($("model").placeholder = DEFAULT_MODEL[$("provider").value]);
$("provider").onchange = setPh; setPh();
$("go").onclick = generate;
$("forget").onclick = () => { store.set("ipm_key", ""); $("key").value = ""; $("status").textContent = "Key removed from this browser."; };
$("file").onchange = (e) => {
  const f = e.target.files[0]; if (!f) return;
  const r = new FileReader(); r.onload = () => ($("diagram").value = r.result); r.readAsText(f);
};
$("cp").onclick = () => navigator.clipboard.writeText($("code").textContent);
$("dl").onclick = () => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([$("code").textContent], { type: "text/x-python" }));
  a.download = "script.py"; a.click(); URL.revokeObjectURL(a.href);
};

// Example gallery: hover (mouse) or tap (touch) a card to open its detail window; leave or tap away to close.
{
  const touch = matchMedia("(hover: none)").matches;
  const cards = [...document.querySelectorAll(".ex")];
  const setOpen = (c, on) => { c.classList.toggle("open", on); c.setAttribute("aria-expanded", on); document.body.classList.toggle("pop-open", cards.some((x) => x.classList.contains("open"))); };
  const closeAll = (except) => cards.forEach((c) => c !== except && setOpen(c, false));
  cards.forEach((c) => {
    let t;
    c.addEventListener("mouseenter", () => { if (touch) return; clearTimeout(t); t = setTimeout(() => { closeAll(c); setOpen(c, true); }, 140); }); // short delay: a mouse passing over does not flash a window
    c.addEventListener("mouseleave", () => { if (touch) return; t = setTimeout(() => setOpen(c, false), 320); });
    c.addEventListener("click", (e) => {
      if (e.target.closest(".popx")) return setOpen(c, false);
      if (!touch || e.target.closest(".pop")) return;
      closeAll(c); setOpen(c, !c.classList.contains("open"));
    });
    c.addEventListener("keydown", (e) => {
      if (e.target !== c && e.key !== "Escape") return;
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); closeAll(c); setOpen(c, !c.classList.contains("open")); }
      if (e.key === "Escape") setOpen(c, false);
    });
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".ex")) closeAll(); });
}
