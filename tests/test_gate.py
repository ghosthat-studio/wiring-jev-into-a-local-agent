from typesafe_sdk import SystemOneResponse

from inbox_agent.gate import QUESTIONS, JevGate
from inbox_agent.message import LABELS, Message

MESSAGE = Message("m-x", "t-x", "a@b.example", "Lunch?", "Are you free on Friday?", "2026-10-05T08:00:00Z")


class FakeClient:
    """Returns a canned Jev response so the gate can be tested without an API key."""

    def __init__(self, label, noul, top=1.0, friend=0.0):
        self.label, self.noul, self.top, self.friend, self.calls = label, noul, top, friend, []

    def system_one(self, state, questions, model=None):
        self.calls.append({"state": state, "questions": questions, "model": model})
        return SystemOneResponse.model_validate({
            "model": "jev-test",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "answers": {
                "label": {"type": "choice", "choice": self.label, "confidence": (self.top - 1 / len(LABELS)) / (1 - 1 / len(LABELS)),
                          "probabilities": {name: (self.top if name == self.label else (1 - self.top) / (len(LABELS) - 1)) for name in LABELS}},
                "needs_reply": {"type": "noul", "noul": self.noul},
                "from_friend": {"type": "noul", "noul": self.friend},
            },
        })


def test_label_options_are_exactly_the_agents_labels():
    assert set(QUESTIONS["label"].criteria) == set(LABELS)


def test_threshold_decides_whether_to_draft():
    assert JevGate(threshold=0.6, client=FakeClient("personal", 0.61)).decide(MESSAGE).needs_reply
    assert not JevGate(threshold=0.6, client=FakeClient("personal", 0.59)).decide(MESSAGE).needs_reply


def test_one_request_answers_all_three_questions():
    client = FakeClient("scheduling", 0.9)
    decision = JevGate(client=client).decide(MESSAGE)
    assert decision.label == "scheduling"
    assert len(client.calls) == 1
    assert set(client.calls[0]["questions"]) == {"label", "needs_reply", "from_friend"}
    assert client.calls[0]["state"]["email"]["subject"] == "Lunch?"


def test_a_newsletter_never_gets_a_draft():
    assert not JevGate(client=FakeClient("newsletter", 0.95)).decide(MESSAGE).needs_reply


def test_when_jev_is_unsure_the_message_goes_to_a_person_and_gets_no_draft():
    decision = JevGate(client=FakeClient("billing", 0.95, top=0.4)).decide(MESSAGE)
    assert decision.needs_review and not decision.needs_reply


def test_a_friend_or_relative_is_marked_so_the_owner_writes_the_reply():
    decision = JevGate(client=FakeClient("personal", 0.9, friend=0.8)).decide(MESSAGE)
    assert decision.needs_reply and decision.from_friend
    assert not JevGate(client=FakeClient("scheduling", 0.9, friend=0.2)).decide(MESSAGE).from_friend
