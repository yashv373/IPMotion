"""Leakage protection: ground-truth transcriptions and source diagrams must never reach RAG or prompts.

- is_denied(path)              path-level exclusion, used by the indexer
- find_leaks(text)             content-level detection on retrieved context / prompts
- assert_no_truth_leak(...)    raises LeakError; the benchmark calls this on every retrieved context
The spec itself (the pipeline INPUT) may name blocks from a truth file; only retrieved CONTEXT is checked.
"""
from __future__ import annotations

import glob
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DENY_DIRS = ("bench/truth", "opentitan_archs", "openPulp_arch")
MIN_LABEL_LEN = 6
MIN_DISTINCT_LABELS = 3      # a context chunk naming this many truth labels is treated as a leak


class LeakError(AssertionError):
    pass


def _norm(path: str) -> str:
    return os.path.abspath(path).replace("\\", "/").lower()


def is_denied(path: str) -> bool:
    p = _norm(path)
    return any(f"/{d.lower()}/" in p + "/" or p.endswith("/" + d.lower()) for d in DENY_DIRS)


def truth_files() -> list[str]:
    return sorted(glob.glob(os.path.join(ROOT, "bench", "truth", "*.yaml")))


def truth_labels() -> set[str]:
    """Distinctive printed labels from every truth file (lowercased)."""
    labels: set[str] = set()
    for f in truth_files():
        if f.endswith(".layout.yaml"):          # positions only (ids and pixels), no labels; still protected by DENY_DIRS
            continue
        with open(f, encoding="utf-8") as fh:
            d = yaml.safe_load(fh) or {}
        for key in ("blocks", "externals", "regions"):
            for item in d.get(key, []) or []:
                lab = item.get("label")
                if isinstance(lab, str) and len(lab) >= MIN_LABEL_LEN:
                    labels.add(lab.lower())
    return labels


def find_leaks(text: str, labels: set[str] | None = None) -> list[str]:
    low = text.lower().replace("\\", "/")
    problems = [f"mentions denied path {d!r}" for d in DENY_DIRS if d.lower() in low]
    for f in truth_files():
        if os.path.basename(f).lower() in low:
            problems.append(f"mentions truth file {os.path.basename(f)!r}")
    labels = truth_labels() if labels is None else labels
    hit = sorted(l for l in labels if l in low)
    if len(hit) >= MIN_DISTINCT_LABELS:
        problems.append(f"contains {len(hit)} truth labels, e.g. {hit[:4]}")
    return problems


def assert_no_truth_leak(chunks, where: str = "context") -> None:
    """chunks: iterable of str, or of dicts with 'text' and optional 'metadata'/'id'."""
    labels = truth_labels()
    for i, c in enumerate(chunks):
        text = c if isinstance(c, str) else c.get("text", "")
        extra = "" if isinstance(c, str) else f"{c.get('id', '')} {c.get('metadata', {})}"
        problems = find_leaks(text + "\n" + extra, labels)
        if problems:
            raise LeakError(f"truth leakage in {where} chunk {i}: " + "; ".join(problems))
