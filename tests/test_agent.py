import json

import pytest
from pathlib import Path

from inbox_agent.agent import run_once
from inbox_agent.fixtures import FixtureMailProvider
from inbox_agent.gate import Decision
from inbox_agent.message import LABELS
from inbox_agent.placeholders.model import TemplateDraftModel
from inbox_agent.state import State

INBOX = Path(__file__).resolve().parents[1] / "fixtures" / "inbox.json"


class ReplyToEverythingGate:
    """Stands in for Jev in these tests. Says every message needs a reply."""

    def decide(self, message):
        return Decision(label="needs_human", label_confidence=1.0, reply_probability=1.0, needs_reply=True)


def run(tmp_path, runs):
    mail = FixtureMailProvider(INBOX, tmp_path)
    state = State(tmp_path / "state.json")
    for _ in range(runs):
        run_once(mail, state, ReplyToEverythingGate(), TemplateDraftModel(), log=lambda _: None)
    return FixtureMailProvider(INBOX, tmp_path)


@pytest.mark.parametrize("path", [INBOX, INBOX.with_name("holdout.json"), INBOX.with_name("holdout2.json")])
def test_fixture_is_well_formed(path):
    data = json.loads(path.read_text())
    ids = [m["id"] for m in data["messages"]]
    assert len(ids) == len(set(ids))
    for m in data["messages"]:
        assert m["expected"]["label"] in LABELS
        assert set(m["expected"].get("also_ok", [])) <= set(LABELS)
        assert m["expected"]["from_friend"] in (True, False, None)  # None: a flag or a draft are both fine
        assert m["sender"].split("@")[1].endswith(".example")


def test_never_drafts_twice_on_a_thread_across_runs(tmp_path):
    mail = run(tmp_path, runs=4)
    threads = [d["thread_id"] for d in mail.drafts]
    assert len(threads) == len(set(threads))


def test_never_drafts_on_an_answered_thread(tmp_path):
    mail = run(tmp_path, runs=1)
    assert not any(d["thread_id"] in mail.replied_threads for d in mail.drafts)


def test_state_survives_a_restart(tmp_path):
    run(tmp_path, runs=1)
    state = State(tmp_path / "state.json")
    assert state.handled("m-01")


def test_without_state_the_agent_drafts_again_on_every_run(tmp_path):
    mail = FixtureMailProvider(INBOX, tmp_path)
    state = State(tmp_path / "state.json")
    for _ in range(2):
        run_once(mail, state, ReplyToEverythingGate(), TemplateDraftModel(), log=lambda _: None, check_state=False)
    threads = [d["thread_id"] for d in mail.drafts]
    assert len(threads) > len(set(threads))


def test_a_thread_left_alone_on_purpose_is_not_a_missed_reply(tmp_path):
    from inbox_agent.score import score

    inbox = tmp_path / "inbox.json"
    inbox.write_text(json.dumps({
        "replied_threads": ["t-done"],
        "messages": [
            {"id": "a", "thread_id": "t-1", "sender": "x@a.example", "subject": "Lunch?", "body": "Free Friday?",
             "received_at": "2026-10-05T08:00:00Z", "expected": {"label": "personal", "needs_reply": True}},
            {"id": "b", "thread_id": "t-1", "sender": "x@a.example", "subject": "Re: Lunch?", "body": "Or Saturday?",
             "received_at": "2026-10-05T09:00:00Z", "expected": {"label": "personal", "needs_reply": True}},
            {"id": "c", "thread_id": "t-done", "sender": "y@a.example", "subject": "Quote", "body": "Here it is.",
             "received_at": "2026-10-05T10:00:00Z", "expected": {"label": "needs_human", "needs_reply": True}},
            {"id": "d", "thread_id": "t-4", "sender": "z@a.example", "subject": "Help", "body": "Can you call me?",
             "received_at": "2026-10-05T11:00:00Z", "expected": {"label": "personal", "needs_reply": True}},
        ],
    }))
    mail = FixtureMailProvider(inbox, tmp_path / "run")
    for mid in "abcd":
        mail.apply_label(mid, "personal")
    mail.create_draft(mail.messages[0], "Yes.")  # one draft covers thread t-1; c is already answered; d is missed
    assert score(inbox, mail)["needed a reply but got no draft"] == 1


class FriendGate:
    """Says every message needs a reply and comes from a friend."""

    def decide(self, message):
        return Decision(label="personal", label_confidence=1.0, reply_probability=1.0, needs_reply=True, from_friend=True)


def test_a_friend_gets_a_flag_and_no_draft(tmp_path):
    mail = FixtureMailProvider(INBOX, tmp_path)
    run_once(mail, State(tmp_path / "state.json"), FriendGate(), TemplateDraftModel(), log=lambda _: None)
    mail = FixtureMailProvider(INBOX, tmp_path)
    assert not mail.drafts
    assert "m-26" in mail.flagged
