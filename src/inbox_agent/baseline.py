"""The agent without Jev, for comparison.

One call to a local model does everything at once: it chooses the label,
decides whether a reply is needed, and writes the draft. This is how many email
agents are built, and it is the "before" in the episode. It sees the same label
descriptions Jev does, so the only difference is who makes the decisions.

Thinking is on by default, because switching it off weakens the model and would
make the comparison unfair to it. It can be switched off to compare speed, and
the report says which was used. Generation is never timed out: a slow model is
slow, not broken.

It talks to an Ollama server. Run it with --baseline (see __main__.py).
"""

import json
import urllib.request

from inbox_agent.gate import QUESTIONS, Decision
from inbox_agent.message import LABELS, Message

PROMPT = """You sort email for a busy person who runs a small business from home. They rely on you so that nothing important is missed and nothing trivial asks for their time.

Choose exactly one label:
{labels}

Decide whether the email needs a written reply from the person who received it.
A reply is needed when: {reply_true}
No reply is needed for: {reply_false}

If a reply is needed, write a short draft reply. Otherwise leave the draft empty.

From: {sender}
Subject: {subject}

{body}"""

# Constrained decoding: the answer can only be one of the labels and a true/false decision.
SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": list(LABELS)},
        "needs_reply": {"type": "boolean"},
        "draft": {"type": "string"},
    },
    "required": ["label", "needs_reply", "draft"],
}


class OneCallBaseline:
    def __init__(self, model: str, ollama_url: str = "http://localhost:11434", num_ctx: int | None = None,
                 think: bool = True):
        self.model = model
        self.think = think
        self.base_url = ollama_url.rstrip("/")
        self.num_ctx = num_ctx
        self.unfinished: list[str] = []  # messages where the model did not finish an answer
        # Check the server is there, and has the model, before starting. This probe has a timeout; generation does not.
        tags = json.loads(urllib.request.urlopen(self.base_url + "/api/tags", timeout=10).read())
        names = {m["name"] for m in tags.get("models", [])}
        if model not in names and f"{model}:latest" not in names:
            raise LookupError(f"model {model} is not pulled on this Ollama server")

    def decide(self, message: Message) -> Decision:
        label_q, reply_q = QUESTIONS["label"], QUESTIONS["needs_reply"]
        prompt = PROMPT.format(
            labels="\n".join(f"- {name}: {desc}" for name, desc in label_q.criteria.items()),
            reply_true=reply_q.criteria["true"],
            reply_false=reply_q.criteria["false"],
            sender=message.sender,
            subject=message.subject,
            body=message.body,
        )
        answer = self._chat(prompt)
        if answer is None:
            # Recorded, not hidden: an unfinished answer drafts nothing and is reported after the run.
            self.unfinished.append(message.id)
            return Decision(label="other", label_confidence=0.0, reply_probability=None, needs_reply=False)
        return Decision(label=answer["label"], label_confidence=1.0,
                        reply_probability=None,
                        needs_reply=answer["needs_reply"])

    def _chat(self, prompt: str) -> dict | None:
        options = {"num_ctx": self.num_ctx} if self.num_ctx else {}
        body = json.dumps({"model": self.model, "messages": [{"role": "user", "content": prompt}],
                           "format": SCHEMA, "think": self.think, "stream": False, "options": options}).encode()
        request = urllib.request.Request(self.base_url + "/api/chat", data=body,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request) as response:  # no timeout: never cut off a generation
            reply = json.loads(response.read())
        if reply.get("done_reason") != "stop":  # "length" means cut off, which is not an answer
            return None
        try:
            answer = json.loads(reply["message"]["content"])
        except json.JSONDecodeError:
            return None
        if answer.get("label") not in LABELS or not isinstance(answer.get("needs_reply"), bool):
            return None
        return answer
