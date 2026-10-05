"""Compare the agent with and without Jev on the same inbox.

    uv run python -m inbox_agent.compare --inbox fixtures/holdout.json --model qwen3.5:9b --out results.json

Three versions run on a fresh mailbox: with Jev, and without Jev with the local
model's thinking off and on. Every run is scored against the correct answers,
timed, and checked for messages whose answer changed from one run to the next.
"""

import argparse
import json
import tempfile
import time
from pathlib import Path

from inbox_agent.agent import run_once
from inbox_agent.baseline import OneCallBaseline
from inbox_agent.fixtures import OWNER, FixtureMailProvider
from inbox_agent.gate import JevGate
from inbox_agent.message import REVIEW
from inbox_agent.placeholders.model import TemplateDraftModel
from inbox_agent.score import score
from inbox_agent.state import State


def one_run(inbox: Path, gate) -> dict:
    with tempfile.TemporaryDirectory() as run_dir:
        mail = FixtureMailProvider(inbox, Path(run_dir))
        start = time.time()
        stats = run_once(mail, State(Path(run_dir) / "state.json"), gate, TemplateDraftModel(), log=lambda _: None)
        seconds = time.time() - start
        data = json.loads(inbox.read_text())
        missed = sum(1 for m in data["messages"] if m["expected"]["needs_reply"]
                     and m["thread_id"] not in data.get("replied_threads", [])
                     and mail.labels.get(m["id"]) != REVIEW  # a person sees it, so it is not missed
                     and m["id"] not in mail.flagged  # flagged for the owner to write herself
                     and m["id"] not in {d["message_id"] for d in mail.drafts})
        return {
            "score": {**score(inbox, mail), "replies missed": missed},
            "seconds per message": round(seconds / max(stats["seen"] - stats["skipped"], 1), 2),
            "labels": mail.labels,
            "drafted": sorted(d["message_id"] for d in mail.drafts),
        }


def drift(runs: list[dict]) -> dict[str, int]:
    ids = runs[0]["labels"].keys()
    return {
        "different label between runs": sum(1 for i in ids if len({r["labels"].get(i) for r in runs}) > 1),
        "different reply decision between runs": sum(1 for i in ids if len({i in r["drafted"] for r in runs}) > 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inbox", type=Path, default=Path("fixtures/holdout.json"))
    parser.add_argument("--model", default="qwen3.5:9b")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--num-ctx", type=int, default=32768)
    parser.add_argument("--out", type=Path, default=Path("results.json"))
    args = parser.parse_args()

    versions = [  # (name, gate, number of runs)
        ("with Jev", JevGate(owner=OWNER), 3),
        ("without Jev, thinking off", OneCallBaseline(args.model, args.ollama_url, args.num_ctx, think=False), 3),
        ("without Jev, thinking on", OneCallBaseline(args.model, args.ollama_url, args.num_ctx, think=True), 1),
    ]
    report = {"inbox": str(args.inbox), "local model": args.model, "versions": {}}
    for name, gate, count in versions:
        runs = []
        for n in range(1, count + 1):
            runs.append(one_run(args.inbox, gate))
            print(f"{name}, run {n}: {runs[-1]['score']} | {runs[-1]['seconds per message']}s per message", flush=True)
        report["versions"][name] = {"runs": runs, "drift": drift(runs) if count > 1 else None,
                                    "unfinished": getattr(gate, "unfinished", [])}
        args.out.write_text(json.dumps(report, indent=2))  # saved after each version, so a stop loses little

    print("\n--- summary")
    for name, v in report["versions"].items():
        for key in ("mislabeled", "drafts to mail that needed no reply", "drafts to friends and family", "replies missed"):
            print(f"{name:>26} | {key}: {[r['score'][key] for r in v['runs']]}")
        print(f"{name:>26} | seconds per message: {[r['seconds per message'] for r in v['runs']]}")
        if v["drift"]:
            for key, value in v["drift"].items():
                print(f"{name:>26} | {key}: {value}")
        if v["unfinished"]:
            print(f"{name:>26} | unfinished answers: {v['unfinished']}")


if __name__ == "__main__":
    main()
