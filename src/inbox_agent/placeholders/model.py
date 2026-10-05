"""PLACEHOLDER: your local drafting model goes here.

The drafting model only writes replies. It makes no decisions: Jev decides the
label and whether a reply is needed before the model is ever called. Choosing
and running a local model is covered in a later Old Nain episode.

TemplateDraftModel writes a canned reply so the agent can run end to end
without a model.
"""

from typing import Protocol

from inbox_agent.message import Message


class DraftModel(Protocol):
    def draft_reply(self, message: Message) -> str: ...


class YourLocalModel:
    """Replace this with a call to the local model you run."""

    def draft_reply(self, message: Message) -> str:
        raise NotImplementedError("Call your local model here.")


class TemplateDraftModel:
    """Writes a fixed reply. Useful for trying the agent without a model."""

    def draft_reply(self, message: Message) -> str:
        return f"Thank you for your note about {message.subject!r}. I will reply properly soon."
