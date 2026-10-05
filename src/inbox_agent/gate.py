"""The Jev gate: the agent's judgment calls, made by Jev instead of the writer.

Three decisions are taken away from the drafting model, and Jev answers all
three in one request:
  - which label the message gets: a Choice over a fixed set of labels
  - whether it needs a reply: a Noul, the probability that the answer is yes,
    compared against a threshold you set
  - whether it is from a friend or relative: another Noul

Jev answers each question on its own, so the code combines the answers:
  - When Jev is unsure of the label, the agent does not guess. It sends the
    message to a person for review, and writes no draft.
  - A newsletter never gets a draft, whatever the reply probability says.
  - A friend or relative who needs a reply gets no draft either. The owner
    writes those herself, so the agent flags the message for her instead.
"""

from dataclasses import dataclass

from typesafe_sdk import Choice, Noul, NoulCriteria, TypeSafeClient

from inbox_agent.message import LABELS, Message

QUESTIONS = {
    "label": Choice(
        instructions="Which label best fits this email, for the inbox owner described in `owner`?",
        criteria={
            "billing": {
                "what": "Money the owner owes or is owed: invoices, payment requests, receipts, refunds, statements, renewals, and problems moving money.",
                "not_for": "Marketing that mentions prices, discounts or free trials (newsletter). A customer complaint that asks for a refund or replacement (needs_human).",
            },
            "scheduling": {
                "what": "Arranging, moving, accepting or declining meetings, calls, visits, talks and events the owner takes part in.",
                "not_for": "Invitations to webinars or promotional events sent to many people (newsletter).",
            },
            "newsletter": {
                "what": "Mail sent in bulk: newsletters, marketing, offers, free-trial reminders, promotional events and announcements to all customers.",
                "not_for": "Notices about the owner's own account, such as security alerts or expiring access (other).",
                "note": "Bulk mail is still bulk mail when it uses the owner's name, comes from a named salesperson, or invites a reply.",
            },
            "personal": {
                "what": "Friends, family and neighbours writing to the owner as individuals about matters outside work.",
            },
            "needs_human": {
                "what": "Business matters that need the owner's own decision: customer complaints, refund or replacement demands, quotes, proposals, partnerships and legal matters.",
                "not_for": "Sales pitches from companies (newsletter).",
            },
            "other": {
                "what": "Anything that fits none of the labels above, such as automated notices about the owner's own accounts, and mail clearly meant for someone else.",
            },
        },
    ),
    "needs_reply": Noul(
        instructions="Does this email need a written reply from the inbox owner described in `owner`?",
        criteria=NoulCriteria(
            true="A real person writing to the owner personally, who would reasonably expect an answer: questions, requests, "
            "and personal notes from friends and family.",
            false="Receipts, notifications, confirmations, newsletters and marketing, even if they invite replies; "
            "anything where the only action is to pay, update details or read; and mail meant for someone else.",
        ),
    ),
    "from_friend": Noul(
        instructions="Is this email from a friend, neighbour or relative of the inbox owner described in `owner`, "
        "writing to her personally?",
        criteria=NoulCriteria(
            true="Family, friends and neighbours who know her personally, writing as themselves: news, invitations, "
            "favours, questions and notes between people who know each other.",
            false="People writing because of her business or theirs: customers, suppliers, companies, organisations "
            "and services, even when they are warm or use her first name; bulk mail; and strangers.",
        ),
    ),
}

assert set(QUESTIONS["label"].criteria) == set(LABELS)


# Below this, Jev is telling us it is unsure of the label (TypeSafe's suggested floor).
CONFIDENCE_FLOOR = 0.5

# A friend's email wrongly drafted costs about as much as a business email wrongly flagged, so the middle.
FRIEND_THRESHOLD = 0.5


@dataclass(frozen=True)
class Decision:
    label: str
    label_confidence: float
    reply_probability: float | None  # None when the decider only says yes or no
    needs_reply: bool
    needs_review: bool = False
    from_friend: bool = False  # the owner writes these replies herself


class JevGate:
    def __init__(self, threshold: float = 0.4, client: TypeSafeClient | None = None, owner: dict | None = None):
        self.threshold = threshold
        self.owner = owner or {}
        self.client = client or TypeSafeClient()  # reads TYPESAFE_API_KEY from the environment

    def decide(self, message: Message) -> Decision:
        response = self.client.system_one(
            model="jev-latest",
            state={"owner": self.owner,
                   "email": {"from": message.sender, "subject": message.subject, "body": message.body}},
            questions=QUESTIONS,
        )
        label = response.choices["label"]
        reply = response.nouls["needs_reply"].noul
        friend = response.nouls["from_friend"].noul
        unsure = label.confidence < CONFIDENCE_FLOOR
        return Decision(
            label=label.choice,
            label_confidence=label.confidence,
            reply_probability=reply,
            needs_reply=reply >= self.threshold and label.choice != "newsletter" and not unsure,
            needs_review=unsure,
            from_friend=friend >= FRIEND_THRESHOLD,
        )
