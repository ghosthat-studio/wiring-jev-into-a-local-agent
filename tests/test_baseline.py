from inbox_agent.baseline import OneCallBaseline
from inbox_agent.message import Message

MESSAGE = Message("m-x", "t-x", "a@b.example", "Lunch?", "Are you free on Friday?", "2026-10-05T08:00:00Z")


def baseline_answering(answer):
    baseline = OneCallBaseline.__new__(OneCallBaseline)  # skip the server probe in tests
    baseline.unfinished = []
    baseline._chat = lambda prompt: answer
    return baseline


def test_reads_the_models_decision():
    decision = baseline_answering({"label": "personal", "needs_reply": True, "draft": "Yes."}).decide(MESSAGE)
    assert decision.label == "personal" and decision.needs_reply


def test_an_unfinished_answer_is_recorded_and_drafts_nothing():
    baseline = baseline_answering(None)
    assert not baseline.decide(MESSAGE).needs_reply
    assert baseline.unfinished == ["m-x"]
