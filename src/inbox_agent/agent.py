"""The agent loop: fetch, check state, let Jev decide, and only then draft."""

from collections import Counter
from typing import Callable, Protocol

from inbox_agent.gate import Decision
from inbox_agent.message import REVIEW, Message
from inbox_agent.placeholders.mail import MailProvider
from inbox_agent.placeholders.model import DraftModel
from inbox_agent.state import State, reason_to_skip


class Gate(Protocol):
    def decide(self, message: Message) -> Decision: ...


def run_once(
    mail: MailProvider,
    state: State,
    gate: Gate,
    model: DraftModel,
    log: Callable[[str], None] = print,
    check_state: bool = True,
) -> Counter:
    stats: Counter = Counter()
    for message in mail.fetch_new():
        stats["seen"] += 1

        skip = reason_to_skip(state, mail, message) if check_state else None
        if skip:
            log(f"skip   {message.id}: {skip}")
            stats["skipped"] += 1
            continue

        decision = gate.decide(message)
        if decision.needs_review:
            mail.apply_label(message.id, REVIEW)
            log(f"review {message.id}: Jev is unsure (best guess {decision.label}, confidence {decision.label_confidence:.2f})")
            stats["review"] += 1
            state.mark_handled(message.id)
            continue

        mail.apply_label(message.id, decision.label)
        reply = "yes" if decision.needs_reply else "no"
        if decision.reply_probability is not None:
            reply = f"{decision.reply_probability:.2f}"
        log(f"label  {message.id}: {decision.label} (needs reply: {reply})")

        if decision.needs_reply and decision.from_friend:
            mail.flag(message.id)
            log(f"flag   {message.id}: from a friend or relative, so Nain writes this one herself")
            stats["flagged"] += 1
        elif decision.needs_reply:
            mail.create_draft(message, model.draft_reply(message))
            log(f"draft  {message.id}")
            stats["drafted"] += 1

        state.mark_handled(message.id)
    return stats
