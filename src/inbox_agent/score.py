"""Score a run against the correct answers recorded in the synthetic inbox."""

import json
from pathlib import Path

from inbox_agent.fixtures import FixtureMailProvider
from inbox_agent.message import REVIEW


def label_ok(label: str, expected: dict) -> bool:
    return label == expected["label"] or label in expected.get("also_ok", [])


def score(inbox_path: Path, mail: FixtureMailProvider) -> dict[str, int]:
    messages = json.loads(inbox_path.read_text())["messages"]
    expected = {m["id"]: m["expected"] for m in messages}
    reviewed = {mid for mid, label in mail.labels.items() if label == REVIEW}
    drafted = [d["message_id"] for d in mail.drafts]
    threads = [d["thread_id"] for d in mail.drafts]
    flagged = set(getattr(mail, "flagged", []))
    # Friends and relatives who need a reply should be flagged for the owner, not drafted.
    for_owner = {m["id"] for m in messages if m["expected"]["needs_reply"] and m["expected"].get("from_friend")
                 and m["thread_id"] not in mail.replied_threads}
    return {
        "messages": len(expected),
        "sent to a person for review": len(reviewed),
        "flagged for Nain to write herself": len(flagged),
        "mislabeled": sum(1 for mid, label in mail.labels.items() if mid not in reviewed and not label_ok(label, expected[mid])),
        "drafts written": len(drafted),
        "drafts to mail that needed no reply": sum(1 for mid in drafted if not expected[mid]["needs_reply"]),
        "drafts to friends and family": sum(1 for mid in drafted if expected[mid].get("from_friend")),
        "friends and family not flagged": sum(1 for mid in for_owner if mid not in flagged and mid not in reviewed),
        # A thread that already has a draft or a reply is rightly left alone, so it is not a miss,
        # and neither is a message flagged for the owner. from_friend is null where either answer is fine.
        "needed a reply but got no draft": sum(1 for m in messages if m["expected"]["needs_reply"]
                                               and m["id"] not in for_owner and m["id"] not in flagged
                                               and m["thread_id"] not in threads and m["thread_id"] not in mail.replied_threads
                                               and m["id"] not in reviewed),
        "duplicate drafts on a thread": len(threads) - len(set(threads)),
        "drafts on answered threads": sum(1 for t in threads if t in mail.replied_threads),
    }
