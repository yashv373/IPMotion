"""
IPMotion v2 — Vector Store Indexer
Chunks ipmotion_lib.py (class-by-class), Manim docs, and gold example
scripts into a local ChromaDB collection for RAG retrieval.

Usage:
    python indexer.py                  # Index everything
    python indexer.py --reset          # Wipe and re-index
"""

import os
import re
import sys
import chromadb
from chromadb.config import Settings

from ipmotion.leakguard import assert_no_truth_leak, is_denied

# ── Config ──────────────────────────────────────────────────
CHROMA_DIR = os.environ.get("IPMOTION_CHROMA_DIR") or os.path.join(os.path.dirname(__file__), ".chroma_db")
COLLECTION_NAME = "ipmotion_knowledge"

LIB_PATH = os.path.join(os.path.dirname(__file__), "ipmotion_lib.py")

# Directories to scan for gold example scripts
EXAMPLE_DIRS = [
    os.path.join(os.path.dirname(__file__), "gold_examples"),
]

# File patterns to treat as gold examples
EXAMPLE_PATTERNS = [
    "*_exact.py", "*_full.py", "*_polished.py", "*_advanced.py",
    "axi_*.py", "fdu_*.py", "fifo_*.py", "symbol_*.py"
]


def get_client(reset=False):
    """Create or connect to local ChromaDB."""
    if reset and os.path.exists(CHROMA_DIR):
        import shutil
        shutil.rmtree(CHROMA_DIR)
        print("[indexer] Wiped existing ChromaDB.")

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client


def chunk_library(lib_path):
    """
    Split ipmotion_lib.py into one chunk per top-level class definition.
    Each chunk contains the full class source code.
    """
    with open(lib_path, "r", encoding="utf-8") as f:
        source = f.read()

    # Split on top-level class definitions
    # Pattern: line starts with "class " (no leading whitespace)
    class_pattern = re.compile(r"^(class \w+.*?$)", re.MULTILINE)
    positions = [m.start() for m in class_pattern.finditer(source)]

    chunks = []
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(source)
        class_source = source[start:end].strip()

        # Extract class name for metadata
        class_name_match = re.match(r"class (\w+)", class_source)
        class_name = class_name_match.group(1) if class_name_match else f"chunk_{i}"

        # Extract the docstring if present
        doc_match = re.search(r'"""(.*?)"""', class_source, re.DOTALL)
        docstring = doc_match.group(1).strip() if doc_match else ""

        chunks.append({
            "id": f"lib_{class_name}",
            "text": class_source,
            "metadata": {
                "source": "ipmotion_lib.py",
                "type": "library_class",
                "class_name": class_name,
                "docstring": docstring[:200],
            }
        })

    # Also grab the imports and module-level code before the first class
    if positions:
        preamble = source[:positions[0]].strip()
        if preamble:
            chunks.insert(0, {
                "id": "lib_preamble",
                "text": preamble,
                "metadata": {
                    "source": "ipmotion_lib.py",
                    "type": "library_preamble",
                    "class_name": "_imports_and_config",
                    "docstring": "Imports, Theme dataclass, and module-level helpers",
                }
            })

    return chunks


def indexable_examples():
    """Basenames that gold_examples/MANIFEST.toml marks status = "indexable". Anything not listed is skipped."""
    import tomllib
    path = os.path.join(os.path.dirname(__file__), "gold_examples", "MANIFEST.toml")
    with open(path, "rb") as fh:
        files = tomllib.load(fh).get("files", {})
    return {name for name, meta in files.items() if meta.get("status") == "indexable"}


def chunk_example_scripts():
    """
    Load gold example scripts as full-file chunks.
    Each script is one chunk so the LLM sees complete working examples.
    """
    import glob

    chunks = []
    seen = set()
    allowed = indexable_examples()

    for directory in EXAMPLE_DIRS:
        for pattern in EXAMPLE_PATTERNS:
            for filepath in glob.glob(os.path.join(directory, pattern)):
                if filepath in seen:
                    continue
                seen.add(filepath)
                if is_denied(filepath):      # truth files / source diagrams are never indexed
                    continue

                basename = os.path.basename(filepath)
                if basename not in allowed:   # MANIFEST.toml is the single source of truth for indexing
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue

                if len(content) < 100:
                    continue  # skip trivially small files

                # Extract Scene class name if present
                scene_match = re.search(r"class (\w+)\(Scene\)", content)
                scene_name = scene_match.group(1) if scene_match else basename

                chunks.append({
                    "id": f"example_{basename}",
                    "text": content,
                    "metadata": {
                        "source": basename,
                        "type": "gold_example",
                        "scene_name": scene_name,
                        "docstring": f"Complete working Manim script: {basename}",
                    }
                })

    return chunks


def chunk_manim_api_basics():
    """
    Hardcoded essential Manim API reference snippets.
    These cover the most commonly hallucinated APIs.
    """
    snippets = [
        {
            "id": "api_scene_basics",
            "text": """# Manim Scene Basics (v0.21.0)
from manim import *

class MyScene(Scene):
    def construct(self):
        # Create objects
        circle = Circle(radius=1, color=BLUE)
        square = Square(side_length=2, color=RED)
        text = Text("Hello", font="Consolas", font_size=24)

        # Add to scene
        self.add(circle)
        self.play(FadeIn(square))
        self.play(Transform(circle, square))
        self.wait(1)

        # Positioning
        circle.move_to(LEFT * 2)
        square.next_to(circle, RIGHT, buff=0.5)
        text.to_edge(UP)

        # Grouping
        group = VGroup(circle, square)
        group.arrange(RIGHT, buff=1)
        group.scale_to_fit_height(config.frame_height * 0.8)
""",
            "metadata": {"source": "manim_api", "type": "api_reference", "class_name": "Scene", "docstring": "Basic Scene structure and common operations"}
        },
        {
            "id": "api_animations",
            "text": """# Manim Animation Types (v0.21.0)
# IMPORTANT: Never set config.pixel_width or config.frame_width in the script on Windows.

# FadeIn / FadeOut
self.play(FadeIn(obj))
self.play(FadeOut(obj))

# Movement
self.play(obj.animate.move_to(RIGHT * 3))
self.play(obj.animate.shift(UP * 2))

# Transform
self.play(Transform(source, target))
self.play(ReplacementTransform(source, target))

# MoveAlongPath — move obj along a path
path = Line(LEFT * 3, RIGHT * 3)
self.play(MoveAlongPath(obj, path), run_time=2)

# Succession — chain animations
self.play(Succession(FadeIn(a), FadeIn(b), FadeIn(c)))

# AnimationGroup — simultaneous animations
self.play(AnimationGroup(FadeIn(a), FadeIn(b), lag_ratio=0.5))

# Color changes
self.play(obj.animate.set_color(GREEN))
self.play(obj.animate.set_fill(BLUE, opacity=0.5))
""",
            "metadata": {"source": "manim_api", "type": "api_reference", "class_name": "Animations", "docstring": "Common animation types and their usage"}
        },
        {
            "id": "api_shapes_arrows",
            "text": """# Manim Shapes and Arrows (v0.21.0)
from manim import *

# Rectangles
rect = Rectangle(width=3, height=2, fill_color=BLUE, fill_opacity=0.2, stroke_color=WHITE, stroke_width=2)
rounded = RoundedRectangle(corner_radius=0.2, width=3, height=2)

# Lines and Arrows
line = Line(LEFT * 2, RIGHT * 2, color=WHITE, stroke_width=3)
arrow = Arrow(start=LEFT * 2, end=RIGHT * 2, color=YELLOW, buff=0, stroke_width=4, max_tip_length_to_length_ratio=0.1)
darrow = DoubleArrow(LEFT * 2, RIGHT * 2)

# Getting positions from objects
center = rect.get_center()
right_edge = rect.get_right()
left_edge = rect.get_left()
top_edge = rect.get_top()
bottom_edge = rect.get_bottom()
edge_center = rect.get_edge_center(RIGHT)

# Connecting objects with arrows
arrow = Arrow(block_a.get_right(), block_b.get_left(), buff=0.1)

# Text inside shapes
label = Text("CPU", font="Consolas", font_size=20, color=WHITE)
label.move_to(rect.get_center())
group = VGroup(rect, label)
""",
            "metadata": {"source": "manim_api", "type": "api_reference", "class_name": "Shapes", "docstring": "Rectangles, lines, arrows, and positioning"}
        },
        {
            "id": "api_windows_constraints",
            "text": """# CRITICAL Windows Constraints for Manim v0.21.0
# These MUST be followed or the output will be broken.

# 1. NEVER set config.pixel_width, config.pixel_height, or config.frame_width
#    inside the Python script. It causes diagonal video shearing on Windows (PyAV stride bug).

# 2. ALWAYS scale your entire scene to fit the default canvas:
#    all_elements = VGroup(*all_your_objects)
#    all_elements.scale_to_fit_height(config.frame_height * 0.9)
#    This ensures everything fits regardless of how many blocks you have.

# 3. Use VGroup.arrange() for layout instead of manual coordinates when possible:
#    row = VGroup(block_a, block_b, block_c).arrange(RIGHT, buff=1.5)

# 4. For Manhattan-style wire routing, use piecewise Lines, not a single Arrow:
#    mid_x = (start[0] + end[0]) / 2
#    path = VGroup(
#        Line(start, [mid_x, start[1], 0]),
#        Line([mid_x, start[1], 0], [mid_x, end[1], 0]),
#        Arrow([mid_x, end[1], 0], end, buff=0, stroke_width=3),
#    )
""",
            "metadata": {"source": "manim_api", "type": "api_reference", "class_name": "WindowsConstraints", "docstring": "Critical Windows-specific constraints that must be followed"}
        },
    ]
    return snippets


def run_indexer(reset=False):
    client = get_client(reset=reset)

    # Get or create collection
    try:
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as e:
        print(f"[indexer] Error creating collection: {e}")
        return

    all_chunks = []

    # 1. Library classes
    if os.path.exists(LIB_PATH):
        lib_chunks = chunk_library(LIB_PATH)
        all_chunks.extend(lib_chunks)
        print(f"[indexer] Parsed {len(lib_chunks)} chunks from ipmotion_lib.py")
    else:
        print(f"[indexer] WARNING: {LIB_PATH} not found!")

    # 2. Gold example scripts
    example_chunks = chunk_example_scripts()
    all_chunks.extend(example_chunks)
    print(f"[indexer] Found {len(example_chunks)} gold example scripts")

    # 3. Manim API basics
    api_chunks = chunk_manim_api_basics()
    all_chunks.extend(api_chunks)
    print(f"[indexer] Added {len(api_chunks)} Manim API reference chunks")

    # Leakage protection: refuse to index anything derived from the ground-truth diagrams
    assert_no_truth_leak(all_chunks, where="indexer input")

    # Upsert into ChromaDB
    if all_chunks:
        collection.upsert(
            ids=[c["id"] for c in all_chunks],
            documents=[c["text"] for c in all_chunks],
            metadatas=[c["metadata"] for c in all_chunks],
        )
        print(f"[indexer] Indexed {len(all_chunks)} total chunks into '{COLLECTION_NAME}'")
    else:
        print("[indexer] No chunks to index!")

    # Print summary
    print(f"\n[indexer] Collection '{COLLECTION_NAME}' now has {collection.count()} documents.")


if __name__ == "__main__":
    do_reset = "--reset" in sys.argv
    run_indexer(reset=do_reset)
