"""Run by hand when ipmotion_lib.py or the rules change: python web/make_context.py
Rewrites web/rag_context/10_library_api.txt (signatures only) and 20_example_axi.txt.
Not part of the site; the site only serves the .txt files."""
import ast, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "web" / "rag_context"
tree = ast.parse((root / "ipmotion_lib.py").read_text(encoding="utf-8"))
lines = ["# ipmotion_lib public API (signatures only). Use ONLY these names.", ""]
for n in tree.body:
    if isinstance(n, ast.ClassDef):
        bases = ", ".join(ast.unparse(b) for b in n.bases)
        lines.append(f"class {n.name}({bases})")
        doc = ast.get_docstring(n)
        if doc: lines.append("    # " + doc.splitlines()[0])
        for m in n.body:
            if isinstance(m, ast.FunctionDef) and (m.name == "__init__" or not m.name.startswith("_")):
                lines.append(f"    def {m.name}({ast.unparse(m.args)})")
    elif isinstance(n, ast.FunctionDef) and not n.name.startswith("_"):
        lines.append(f"def {n.name}({ast.unparse(n.args)})")
(out / "10_library_api.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
ex = (root / "gold_examples" / "axi_read_handshake.py").read_text(encoding="utf-8")
(out / "20_example_axi.txt").write_text("# GOLD EXAMPLE (renders with 0 lint errors; copy its layout habits)\n" + ex, encoding="utf-8")

# The big worked example: a whole 40-block chip, emitted from the engine itself, so it can never drift from what
# the engine actually draws. Earlgrey only -- Peppermint is the held-out exam (CLAUDE.md), and Darjeeling does
# not emit cleanly yet (its banner lands on the drawing; see docs/PROGRESS.md).
import sys
sys.path.insert(0, str(root))
from ipmotion.emit import emit  # noqa: E402
(out / "25_example_earlgrey.txt").write_text(emit("bench/stories/earlgrey_ibex_uart_read.yaml"), encoding="utf-8")
