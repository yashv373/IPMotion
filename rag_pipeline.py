"""
IPMotion v2 — RAG Pipeline
Retrieves relevant context from ChromaDB and generates Manim scripts via LLM.

Usage:
    from rag_pipeline import generate_script
    script = generate_script("Animate an AXI4 read handshake between master and slave")
"""

import os
import chromadb

# ── Config ──────────────────────────────────────────────────
CHROMA_DIR = os.environ.get("IPMOTION_CHROMA_DIR") or os.path.join(os.path.dirname(__file__), ".chroma_db")
COLLECTION_NAME = "ipmotion_knowledge"
TOP_K = 8  # Number of chunks to retrieve

SYSTEM_PROMPT = """You are IPMotion, an expert Manim Community v0.21.0 hardware IP animation engineer.

Your job is to generate a COMPLETE, RUNNABLE Manim Python script that animates a hardware IP concept described by the user.

## RULES — Follow these exactly:

1. ALWAYS start with `from manim import *` and then `from ipmotion_lib import *` (if using IPMotion library classes).
2. NEVER set `config.pixel_width`, `config.pixel_height`, or `config.frame_width` anywhere in the script. This causes broken video on Windows.
3. ALWAYS scale your final layout using `all_elements.scale_to_fit_height(config.frame_height * 0.9)` before playing animations.
4. Use `VGroup.arrange()` for layout whenever possible instead of hardcoding coordinates.
5. For wires between blocks, use the block's `.get_right()`, `.get_left()`, `.get_top()`, `.get_bottom()` methods to get exact edge positions.
6. For Manhattan-style routing, build piecewise `Line` + `Arrow` segments through a midpoint.
7. Every script must have exactly ONE class that inherits from `Scene` with a `construct(self)` method.
8. Use `self.play(FadeIn(...))` to reveal elements, not `self.add(...)`, so things animate in.
9. Use the font "Consolas" for all text labels.
10. Keep colors from the hardware domain: use BLUE for data, GREEN for control/valid, RED for errors, YELLOW for active, GRAY for inactive.

## CONTEXT
Below are relevant code snippets from the IPMotion library and verified example scripts.
Use these as reference for class names, constructor arguments, and visual style.
Do NOT invent classes or methods that are not shown in the context.

{context}

## USER REQUEST
{user_request}

## OUTPUT
Generate ONLY the complete Python script. No explanations, no markdown fences, just pure Python code.
"""


def get_collection():
    """Connect to existing ChromaDB collection."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_collection(name=COLLECTION_NAME)


def retrieve_context(query, top_k=TOP_K):
    """
    Retrieve the most relevant chunks from the vector store.
    Returns a formatted string of all retrieved documents.
    """
    collection = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas"],
    )

    context_parts = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        source = meta.get("source", "unknown")
        doc_type = meta.get("type", "unknown")
        class_name = meta.get("class_name", "")

        header = f"# --- [{doc_type}] {source}"
        if class_name:
            header += f" :: {class_name}"
        header += " ---"

        context_parts.append(f"{header}\n{doc}\n")

    return "\n".join(context_parts)


def build_prompt(user_request, context):
    """Build the full prompt with retrieved context injected."""
    return SYSTEM_PROMPT.format(
        context=context,
        user_request=user_request,
    )


def call_llm(prompt, api_key=None, model="gemini-3.8-flash"):
    """
    Call an LLM to generate the Manim script.
    Supports: Google Gemini (default), OpenAI, or local Ollama.
    """
    # Try Google Gemini first
    api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            gen_model = genai.GenerativeModel(model)
            response = gen_model.generate_content(prompt)
            return _clean_response(response.text)
        except ImportError:
            print("[rag] google-generativeai not installed. pip install google-generativeai")
        except Exception as e:
            print(f"[rag] Gemini API error: {e}")

    # Try OpenAI
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return _clean_response(response.choices[0].message.content)
        except ImportError:
            print("[rag] openai not installed. pip install openai")
        except Exception as e:
            print(f"[rag] OpenAI API error: {e}")

    # Try local Ollama
    try:
        import requests
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "codellama", "prompt": prompt, "stream": False},
            timeout=120,
        )
        if response.ok:
            return _clean_response(response.json().get("response", ""))
    except Exception:
        pass

    raise RuntimeError(
        "[rag] No LLM backend available. Set one of:\n"
        "  - GEMINI_API_KEY (for Google Gemini)\n"
        "  - OPENAI_API_KEY (for OpenAI GPT-4o)\n"
        "  - Run Ollama locally (ollama serve)"
    )


def _clean_response(text):
    """Strip markdown fences and leading/trailing whitespace."""
    text = text.strip()
    # Remove ```python ... ``` wrapper if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```python) and last line (```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        elif lines[0].startswith("```"):
            lines = lines[1:]
        text = "\n".join(lines)
    return text.strip()


def generate_script(user_request, api_key=None, model="gemini-3.8-flash", top_k=TOP_K):
    """
    Full RAG pipeline: retrieve context → build prompt → call LLM → return script.

    Args:
        user_request: Natural language description of the desired animation
        api_key: Optional API key (defaults to env vars)
        model: LLM model name
        top_k: Number of context chunks to retrieve

    Returns:
        str: Complete Manim Python script
    """
    print(f"[rag] Retrieving {top_k} relevant chunks...")
    context = retrieve_context(user_request, top_k=top_k)

    print(f"[rag] Building prompt ({len(context)} chars of context)...")
    prompt = build_prompt(user_request, context)

    print(f"[rag] Calling LLM ({model})...")
    script = call_llm(prompt, api_key=api_key, model=model)

    print(f"[rag] Generated {len(script)} chars of Manim code.")
    return script


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python rag_pipeline.py \"Your animation request\"")
        sys.exit(1)

    request = " ".join(sys.argv[1:])
    script = generate_script(request)
    print("\n" + "=" * 60)
    print(script)
    print("=" * 60)
