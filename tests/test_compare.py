from pathlib import Path

from inbox_agent.compare import drift, one_run
from inbox_agent.gate import Decision

HOLDOUT = Path(__file__).resolve().parents[1] / "fixtures" / "holdout.json"


class FlipGate:
    """Says the opposite on alternate runs, to check that drift is counted."""

    def __init__(self, reply):
        self.reply = reply

    def decide(self, message):
        return Decision(label="billing" if self.reply else "other", label_confidence=1.0,
                        reply_probability=float(self.reply), needs_reply=self.reply)


def test_a_run_is_scored_and_timed():
    run = one_run(HOLDOUT, FlipGate(False))
    assert run["score"]["drafts written"] == 0
    assert run["score"]["replies missed"] > 0
    assert run["seconds per message"] >= 0


def test_drift_counts_messages_whose_answer_changed():
    runs = [one_run(HOLDOUT, FlipGate(False)), one_run(HOLDOUT, FlipGate(True))]
    changed = drift(runs)
    assert changed["different label between runs"] == changed["different reply decision between runs"] > 0
