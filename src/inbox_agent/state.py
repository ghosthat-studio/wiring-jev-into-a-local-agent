"""State: check before you act.

Jev makes judgment calls. It cannot tell the agent what the agent has already
done. Without this check, the agent drafts a fresh reply to the same thread on
every run, however good its decisions are.
"""

import json
from pathlib import Path

from inbox_agent.message import Message
from inbox_agent.placeholders.mail import MailProvider


class State:
    """Remembers which messages the agent has already handled."""

    def __init__(self, path: Path):
        self.path = path
        self._handled: set[str] = set(json.loads(path.read_text())) if path.exists() else set()

    def handled(self, message_id: str) -> bool:
        return message_id in self._handled

    def mark_handled(self, message_id: str) -> None:
        self._handled.add(message_id)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(sorted(self._handled), indent=2))


def reason_to_skip(state: State, mail: MailProvider, message: Message) -> str | None:
    """Return why the agent should leave this message alone, or None to proceed."""
    if state.handled(message.id):
        return "already handled on an earlier run"
    if mail.thread_has_draft(message.thread_id):
        return "thread already has a draft"
    if mail.thread_has_reply(message.thread_id):
        return "thread has already been answered"
    return None
