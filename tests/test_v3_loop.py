"""The v3 loop end to end with a scripted fake LLM (no API calls): bad answer first, good answer second."""
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))
import common as C  # noqa: E402
import run_v3  # noqa: E402
import rag_pipeline  # noqa: E402
from test_conformance import BODY  # noqa: E402
from ipmotion import conformance  # noqa: E402

SPEC_PATH = os.path.join(ROOT, "bench", "specs", "axi_write.yaml")
SPEC = yaml.safe_load(open(SPEC_PATH, encoding="utf-8"))


def good():
    return conformance.preamble(SPEC) + "\n" + BODY


def bad():
    # hand-typed block title + lint_ignore: conformance must reject it before lint is even considered
    body = BODY.replace('IPBlock(LABELS["master"]', 'IPBlock("AXI Master"').replace(
        "        self.wait(0.5)\n", '        master.lint_ignore = ["text_overlap"]\n        self.wait(0.5)\n')
    return conformance.preamble(SPEC) + "\n" + body


def test_prompt_puts_labels_and_banners_first_and_hides_provenance():
    block = C.labels_block(SPEC_PATH)
    assert block.lstrip().startswith("## READ THIS FIRST") and "LABELS = {" in block and "BANNERS = [" in block
    assert "NEVER use lint_ignore" in block
    full = block + "\n" + rag_pipeline.build_prompt(C.user_request(SPEC_PATH), "context")
    assert full.index("LABELS = {") < full.index("## SPEC FORMAT")
    assert "truth" not in full.lower().replace("never type", "") or "truth" not in C.prompt_spec(SPEC_PATH)


def test_feedback_order_grouping_and_cap():
    lint = [{"check": "min_spacing", "severity": "error", "source_line": 5, "first_t": float(i),
             "detail": f"overlap {i}", "objects": [{"name": "pkt_bg", "bbox": [0, 0, 1, 1]}]} for i in range(6)]
    lint += [{"check": "text_overlap", "severity": "error", "source_line": 9, "first_t": 1.0, "detail": "t",
              "objects": [{"name": f"label{j}", "bbox": [0, 0, 1, 1]}]} for j in range(7)]
    conf = [{"check": "conformance_connection", "severity": "error", "detail": "no wire from a to b"}]
    kind, text, counts = run_v3.build_feedback({"issues": lint, "conformance": conf})
    lines = [l for l in text.splitlines() if l.startswith("- ")]
    assert kind == "spec conformance errors" and len(lines) == 5          # capped
    assert lines[0].startswith("- [conformance_connection]")               # conformance before lint
    assert any("(+5 similar on pkt_bg)" in l for l in lines)               # duplicates grouped, biggest group first
    assert counts == {"runtime": 0, "conformance": 1, "lint": 13}
    rt = {"check": "runtime_error", "severity": "error", "traceback": "Traceback...\nNameError: x"}
    kind, text, _ = run_v3.build_feedback({"issues": [rt] + lint, "conformance": conf})
    assert kind == "runtime error" and "NameError" in text and "conformance" not in text   # runtime errors go alone


def test_loop_rejects_bad_script_then_passes_on_the_fix(tmp_path, monkeypatch):
    monkeypatch.setenv("IPMOTION_RUNS_DIR", str(tmp_path))
    answers = [bad(), good()]
    prompts = []

    def fake(prompt, api_key=None, model=None):
        prompts.append(prompt)
        return answers.pop(0)

    monkeypatch.setattr(rag_pipeline, "call_llm", fake)
    r = run_v3.run(SPEC_PATH, 1)
    assert r["status"] == "pass" and r["attempts_used"] == 2
    assert r["attempts"][0]["kind"] == "spec conformance errors" and r["attempts"][0]["conformance_errors"] >= 2
    assert r["attempts"][1]["kind"] == "pass" and r["final_conformance_errors"] == 0 and r["final_lint_errors"] == 0
    assert r["prompt_version"] == 2 and r["final_frames"]
    assert prompts[0].lstrip().startswith("## READ THIS FIRST")
    assert "hand-typed" in prompts[1] and "lint_ignore is not allowed" in prompts[1]      # feedback reached the model
    assert not answers
