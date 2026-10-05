"""PLACEHOLDER: your mail integration goes here.

This repo does not connect to a real mailbox. Implement MailProvider for your
own setup (IMAP, the Gmail API, a local Maildir, and so on). Setting up the
email side of the agent is covered in a later Old Nain episode.

To try the agent without any real mail, use FixtureMailProvider in fixtures.py.
"""

from typing import Protocol

from inbox_agent.message import Message


class MailProvider(Protocol):
    def fetch_new(self) -> list[Message]:
        """Return messages that have arrived and not been read."""

    def thread_has_draft(self, thread_id: str) -> bool:
        """Return True if a draft reply already exists on this thread."""

    def thread_has_reply(self, thread_id: str) -> bool:
        """Return True if someone has already replied on this thread."""

    def apply_label(self, message_id: str, label: str) -> None: ...

    def flag(self, message_id: str) -> None:
        """Mark a message for the owner's attention, like a star in Gmail."""

    def create_draft(self, message: Message, body: str) -> None:
        """Save a draft reply. The agent never sends; a person does."""


class YourMailProvider:
    """Replace this with a real implementation of MailProvider."""

    def fetch_new(self) -> list[Message]:
        raise NotImplementedError("Connect your mailbox here.")

    def thread_has_draft(self, thread_id: str) -> bool:
        raise NotImplementedError("Connect your mailbox here.")

    def thread_has_reply(self, thread_id: str) -> bool:
        raise NotImplementedError("Connect your mailbox here.")

    def apply_label(self, message_id: str, label: str) -> None:
        raise NotImplementedError("Connect your mailbox here.")

    def flag(self, message_id: str) -> None:
        raise NotImplementedError("Connect your mailbox here.")

    def create_draft(self, message: Message, body: str) -> None:
        raise NotImplementedError("Connect your mailbox here.")
