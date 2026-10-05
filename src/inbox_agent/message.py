from dataclasses import dataclass

# The fixed set of labels the agent can apply. Jev chooses from exactly these.
LABELS = ("billing", "scheduling", "newsletter", "personal", "needs_human", "other")

# Not a label Jev chooses: the agent marks a message for a person when Jev is unsure.
REVIEW = "for_review"


@dataclass(frozen=True)
class Message:
    id: str
    thread_id: str
    sender: str
    subject: str
    body: str
    received_at: str
