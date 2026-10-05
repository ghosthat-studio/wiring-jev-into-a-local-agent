"""A synthetic inbox, so the agent can run without any real mail.

Every message in fixtures/inbox.json is invented. Labels and drafts the agent
writes are saved under .run/ so that state carries over between runs, the way
a real mailbox would.
"""

import json
from pathlib import Path

from inbox_agent.message import Message

# Who the synthetic inbox belongs to. Jev needs this to tell mail for the owner from mail meant for someone else.
OWNER = {
    "name": "Nain Pritchard",
    "addressed_as": ["Nain", "Mrs Pritchard"],
    "work": "Runs a small home technology business from her cottage: fitting cameras, fixing computers, setting up home networks.",
}


class FixtureMailProvider:
    def __init__(self, inbox_path: Path, run_dir: Path):
        data = json.loads(inbox_path.read_text())
        self.messages = [Message(**{k: m[k] for k in Message.__dataclass_fields__}) for m in data["messages"]]
        self.replied_threads = set(data.get("replied_threads", []))
        self.store_path = run_dir / "mailbox.json"
        stored = json.loads(self.store_path.read_text()) if self.store_path.exists() else {}
        self.labels: dict[str, str] = stored.get("labels", {})
        self.drafts: list[dict] = stored.get("drafts", [])
        self.flagged: list[str] = stored.get("flagged", [])

    def fetch_new(self) -> list[Message]:
        # Like an inbox the agent never marks as read: every message comes back on every run.
        return list(self.messages)

    def thread_has_draft(self, thread_id: str) -> bool:
        return any(d["thread_id"] == thread_id for d in self.drafts)

    def thread_has_reply(self, thread_id: str) -> bool:
        return thread_id in self.replied_threads

    def apply_label(self, message_id: str, label: str) -> None:
        self.labels[message_id] = label
        self._save()

    def flag(self, message_id: str) -> None:
        if message_id not in self.flagged:
            self.flagged.append(message_id)
            self._save()

    def create_draft(self, message: Message, body: str) -> None:
        self.drafts.append({"message_id": message.id, "thread_id": message.thread_id, "body": body})
        self._save()

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps({"labels": self.labels, "drafts": self.drafts, "flagged": self.flagged}, indent=2))
