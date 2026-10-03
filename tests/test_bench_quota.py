import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))
import common as C  # noqa: E402

DAILY = ("RuntimeError: Gemini API failed: 429 You exceeded your current quota ... "
         "quota_id: GenerateRequestsPerDayPerProjectPerModel-FreeTier")


def make(errors, sleeps):
    calls = []

    def original(prompt, api_key=None, model=None):
        calls.append(model)
        if errors:
            raise RuntimeError(errors.pop(0))
        return "ok"
    return C.wrap_llm(original, sleep=sleeps.append), calls


def test_model_is_pinned():
    assert C.MODEL == "gemini-3.5-flash"
    w, calls = make([], [])
    assert w("p") == "ok" and calls == ["gemini-3.5-flash"]


def test_daily_quota_stops_immediately_without_retrying():
    sleeps = []
    w, calls = make([DAILY, DAILY, DAILY], sleeps)
    with pytest.raises(C.DailyQuotaError):
        w("p")
    assert len(calls) == 1 and sleeps == []


def test_daily_quota_cannot_be_swallowed_by_except_exception():
    w, _ = make([DAILY], [])
    try:
        try:
            w("p")
        except Exception:                      # what runner.py does around its fix call
            pytest.fail("DailyQuotaError was caught by `except Exception`")
    except C.DailyQuotaError:
        pass


def test_transient_errors_are_retried_with_backoff_then_succeed():
    sleeps = []
    w, calls = make(["429 rate limit per minute", "503 unavailable"], sleeps)
    assert w("p") == "ok" and len(calls) == 3 and sleeps == [20, 40]


def test_persistent_transient_error_gives_up_with_runtimeerror():
    w, calls = make(["503 unavailable"] * 9, [])
    with pytest.raises(RuntimeError, match="still failing"):
        w("p")
    assert len(calls) == 4


def test_non_transient_error_is_raised_untouched():
    w, calls = make(["400 invalid argument: bad prompt"], [])
    with pytest.raises(RuntimeError, match="invalid argument"):
        w("p")
    assert len(calls) == 1


def test_wrapper_installed_on_both_pipelines():
    import rag_pipeline, runner
    assert hasattr(rag_pipeline.call_llm, "__wrapped__") and runner.call_llm is rag_pipeline.call_llm
