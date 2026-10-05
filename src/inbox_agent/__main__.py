"""Run the agent against the synthetic inbox.

    uv run python -m inbox_agent [--inbox fixtures/inbox.json] [--runs N] [--threshold 0.6] [--fresh]
    uv run python -m inbox_agent --baseline [--model qwen3.5:9b] [--no-state] [--no-think]   # without Jev
"""

import argparse
import os
import shutil
import sys
import urllib.error
from pathlib import Path

from inbox_agent.agent import run_once
from inbox_agent.baseline import OneCallBaseline
from inbox_agent.fixtures import OWNER, FixtureMailProvider
from inbox_agent.gate import JevGate
from inbox_agent.placeholders.model import TemplateDraftModel
from inbox_agent.score import score
from inbox_agent.state import State

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inbox", type=Path, default=ROOT / "fixtures" / "inbox.json")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--threshold", type=float, default=0.4, help="low on purpose: an ambiguous email gets a draft to rewrite rather than no reply")
    parser.add_argument("--baseline", action="store_true", help="no Jev: one local-model call decides everything")
    parser.add_argument("--model", default="qwen3.5:9b", help="local model for --baseline")
    parser.add_argument("--num-ctx", type=int, default=32768, help="context for --baseline; match what the server already runs so the model is not reloaded")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama server for --baseline")
    parser.add_argument("--no-think", action="store_true", default=os.environ.get("INBOX_AGENT_NO_THINK") == "1", help="switch the local model's thinking off for --baseline (faster, weaker)")
    parser.add_argument("--no-state", action="store_true", help="skip the check-before-you-act memory, as many agents do")
    parser.add_argument("--run-dir", type=Path, default=ROOT / ".run", help="where the mailbox and state are kept")
    parser.add_argument("--fresh", action="store_true", help="forget earlier runs first")
    args = parser.parse_args()

    if args.baseline:
        try:
            gate = OneCallBaseline(model=args.model, ollama_url=args.ollama_url, num_ctx=args.num_ctx,
                                   think=not args.no_think)
        except (urllib.error.URLError, OSError, LookupError):
            sys.exit(f"--baseline needs an Ollama server at {args.ollama_url} with {args.model} pulled "
                     f"(ollama pull {args.model}). See the README.")
    else:
        if not os.environ.get("TYPESAFE_API_KEY"):
            sys.exit("Set TYPESAFE_API_KEY to your TypeSafe API key first. See the README.")
        gate = JevGate(threshold=args.threshold, owner=OWNER)
    run_dir = args.run_dir
    if args.fresh and run_dir.exists():  # only after the setup checks, so a failed start forgets nothing
        shutil.rmtree(run_dir)
    mail = FixtureMailProvider(args.inbox, run_dir)
    state = State(run_dir / "state.json")
    model = TemplateDraftModel()

    for n in range(1, args.runs + 1):
        print(f"--- run {n}")
        stats = run_once(mail, state, gate, model, check_state=not args.no_state)
        print(f"seen {stats['seen']}, skipped {stats['skipped']}, drafted {stats['drafted']}, flagged {stats['flagged']}")

    if args.baseline and gate.unfinished:
        print(f"unfinished answers (counted as no draft): {len(gate.unfinished)} {gate.unfinished}")
    print("--- score against the correct answers")
    for name, value in score(args.inbox, mail).items():
        if name == "sent to a person for review" and not value:
            continue
        print(f"{name:>38}: {value}")


if __name__ == "__main__":
    main()
