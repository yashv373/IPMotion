"""
IPMotion v2 — Self-Healing Runner
Generates a Manim script via RAG, renders it, and if it fails,
feeds the error back to the LLM for automatic correction.

Usage:
    python runner.py "Animate an AXI4 read handshake between master and slave"
    python runner.py "Show a 4-stage pipeline with stall detection"
"""

import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime

from rag_pipeline import generate_script, retrieve_context, build_prompt, call_llm, _clean_response

# ── Config ──────────────────────────────────────────────────
MAX_RETRIES = 8
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "generated")

ERROR_FIX_PROMPT = """The following Manim script failed to render. Fix the error.

## THE ERROR
```
{error}
```

## THE FAILING SCRIPT
```python
{script}
```

## RELEVANT CONTEXT FROM THE IPMOTION LIBRARY
{context}

## RULES
1. Return ONLY the complete fixed Python script. No explanations.
2. Fix ONLY the error. Do not rewrite unrelated parts.
3. Do NOT use any Manim API that is not shown in the context above.
4. NEVER set config.pixel_width, config.pixel_height, or config.frame_width.
5. Make sure to import everything needed at the top of the file.

## OUTPUT
The complete, fixed Python script:
"""


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_scene_name(script):
    """Extract the Scene subclass name from the script."""
    import re
    match = re.search(r"class (\w+)\(Scene\)", script)
    if match:
        return match.group(1)
    # Fallback: look for any Scene-like class
    match = re.search(r"class (\w+)\(.*Scene.*\)", script)
    if match:
        return match.group(1)
    return None


def render_script(script_path, scene_name):
    """
    Run manim on the script. Returns (success, stdout+stderr).
    """
    cmd = [
        sys.executable, "-m", "manim",
        "render", "-ql",  # low quality for fast iteration
        script_path, scene_name,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(script_path),
        )
        output = result.stdout + "\n" + result.stderr
        success = result.returncode == 0
        return success, output
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT: Manim rendering took longer than 120 seconds."
    except Exception as e:
        return False, f"EXCEPTION: {str(e)}"


def extract_error(output):
    """Extract the most relevant error from manim output."""
    lines = output.strip().split("\n")

    # Look for Python traceback
    error_lines = []
    in_traceback = False
    for line in lines:
        if "Traceback" in line:
            in_traceback = True
        if in_traceback:
            error_lines.append(line)

    if error_lines:
        # Keep last 30 lines of traceback (trim very long ones)
        return "\n".join(error_lines[-30:])

    # Look for ERROR lines
    error_lines = [l for l in lines if "ERROR" in l.upper() or "Error" in l]
    if error_lines:
        return "\n".join(error_lines[-10:])

    # Fallback: last 15 lines
    return "\n".join(lines[-15:])


def run_pipeline(user_request, api_key=None, model="gemini-3.8-flash"):
    """
    Full self-healing pipeline:
    1. Generate script via RAG
    2. Try to render
    3. If error, feed error back to LLM and retry
    4. Repeat up to MAX_RETRIES times
    """
    ensure_output_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"ipmotion_{timestamp}"

    print(f"\n{'='*60}")
    print(f"  IPMotion v2 — RAG Self-Healing Pipeline")
    print(f"  Request: {user_request[:80]}...")
    print(f"{'='*60}\n")

    # Step 1: Generate initial script
    print("[runner] Step 1: Generating initial script via RAG...")
    script = generate_script(user_request, api_key=api_key, model=model)

    scene_name = extract_scene_name(script)
    if not scene_name:
        print("[runner] WARNING: Could not find Scene class name. Using 'GeneratedScene'.")
        # Inject a wrapper
        script = f"from manim import *\n\nclass GeneratedScene(Scene):\n    def construct(self):\n        pass\n\n# Original output had no Scene class"
        scene_name = "GeneratedScene"

    # Save iterations for debugging
    iteration_dir = os.path.join(OUTPUT_DIR, base_name)
    os.makedirs(iteration_dir, exist_ok=True)

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n[runner] --- Attempt {attempt}/{MAX_RETRIES} ---")

        # Save current script
        script_path = os.path.join(iteration_dir, f"attempt_{attempt}.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)
        print(f"[runner] Saved: {script_path}")

        # Also save to a stable path for rendering (manim needs imports to work)
        render_path = os.path.join(os.path.dirname(__file__), f"_render_temp.py")
        with open(render_path, "w", encoding="utf-8") as f:
            f.write(script)

        # Try to render
        print(f"[runner] Rendering with manim (scene: {scene_name})...")
        success, output = render_script(render_path, scene_name)

        if success:
            print(f"\n[runner] SUCCESS on attempt {attempt}!")

            # Copy the final script to output
            final_path = os.path.join(iteration_dir, f"FINAL_{scene_name}.py")
            shutil.copy(render_path, final_path)

            # Find the rendered video
            media_dir = os.path.join(os.path.dirname(__file__), "media", "videos", "_render_temp", "480p15")
            if os.path.exists(media_dir):
                videos = [f for f in os.listdir(media_dir) if f.endswith(".mp4")]
                if videos:
                    video_src = os.path.join(media_dir, videos[-1])
                    video_dst = os.path.join(iteration_dir, f"FINAL_{scene_name}.mp4")
                    shutil.copy(video_src, video_dst)
                    print(f"[runner] Video saved: {video_dst}")

            # Cleanup temp file
            if os.path.exists(render_path):
                os.remove(render_path)

            print(f"[runner] All iteration files in: {iteration_dir}")
            print(f"[runner] Final script: {final_path}")
            return final_path

        # Failed — extract error and retry
        error_msg = extract_error(output)
        print(f"[runner] FAILED. Error:\n{error_msg[:300]}...")

        # Save error log
        error_path = os.path.join(iteration_dir, f"error_{attempt}.txt")
        with open(error_path, "w", encoding="utf-8") as f:
            f.write(output)

        if attempt < MAX_RETRIES:
            print(f"[runner] Feeding error back to LLM for fix...")

            # Retrieve fresh context relevant to the error
            error_context = retrieve_context(
                f"Manim error: {error_msg[:200]}",
                top_k=5,
            )

            fix_prompt = ERROR_FIX_PROMPT.format(
                error=error_msg,
                script=script,
                context=error_context,
            )

            try:
                script = call_llm(fix_prompt, api_key=api_key, model=model)
                script = _clean_response(script)

                # Re-extract scene name in case it changed
                new_scene = extract_scene_name(script)
                if new_scene:
                    scene_name = new_scene
            except Exception as e:
                print(f"[runner] LLM fix call failed: {e}")
                break

    # All retries exhausted
    print(f"\n[runner] FAILED after {MAX_RETRIES} attempts.")
    print(f"[runner] All attempts saved in: {iteration_dir}")

    # Cleanup
    render_path = os.path.join(os.path.dirname(__file__), f"_render_temp.py")
    if os.path.exists(render_path):
        os.remove(render_path)

    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python runner.py \"Your animation request\"")
        print()
        print("Examples:")
        print('  python runner.py "Animate an AXI4 read handshake between master and slave"')
        print('  python runner.py "Show a 4-stage pipeline with stall and bubble insertion"')
        print('  python runner.py "Visualize a FIFO queue with enqueue and dequeue operations"')
        sys.exit(1)

    request = " ".join(sys.argv[1:])
    result = run_pipeline(request)

    if result:
        print(f"\nDone! Final script at: {result}")
    else:
        print("\nPipeline failed. Check the generated/ directory for debugging.")
