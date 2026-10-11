# Wiring Jev into a local agent

Companion code for **Old Nain, episode 001**: [Granny fixes your AI agent while the biscuits cool](https://www.youtube.com/watch?v=cm_4AmKAtmo). More episodes are on the [Old Nain YouTube channel](https://www.youtube.com/@Old_Nain).

This is a small local email agent. It reads new mail, labels each message, decides whether the message needs a reply, and, if it does, writes a draft. When the message is from a friend or relative, it flags it instead, because the owner writes those replies herself. It never sends anything, because a person always sends.

The episode is about one idea: an agent's judgment calls should not be made by the model that writes the replies. Here, three decisions are handed to Jev instead. In a single request, Jev chooses each message's label from a fixed set (a Choice), gives the probability that the message needs a reply (a Noul), which is compared against a threshold you set, and gives the probability that it comes from a friend, neighbour or relative (another Noul). The code decides what the answers mean together: a friend who needs a reply gets a flag rather than a draft. The drafting model only writes, and it only runs for messages that pass the gate.


## Disclaimer

This code is for educational purposes only. It was written to teach one technique in an Old Nain episode, and it is not meant for production use. It has not been hardened, audited, or tested against real mail, real customers or real money. If you use it, or any part of it, you do so at your own risk, and you take complete responsibility for how you use it and for anything that results. It is provided as is, without warranty of any kind, as the Apache License 2.0 sets out.

## Jev will not fix everything

Before Jev can help, the agent needs state. If the agent does not remember what it has already done, it will draft a fresh reply to the same thread on every run, however good its decisions are. That is a memory problem, not a judgment problem. So the agent checks before it acts: it skips a message it has already handled, a thread that already has a draft, and a thread someone has already answered. You can find that check in `src/inbox_agent/state.py`. Wire in state first, and then Jev's decisions can do their job.

## How it fits together

```
fetch new mail -> check state -> Jev: label -> Jev: needs a reply? -> draft (only if it passes)
```

| File | What it does |
|---|---|
| `src/inbox_agent/agent.py` | The loop that ties everything together. |
| `src/inbox_agent/state.py` | Check before you act. |
| `src/inbox_agent/gate.py` | The Jev gate. |
| `src/inbox_agent/placeholders/mail.py` | **Placeholder** for your mail integration. |
| `src/inbox_agent/placeholders/model.py` | **Placeholder** for your local drafting model. |
| `src/inbox_agent/fixtures.py` and `fixtures/inbox.json` | A synthetic inbox, so you can run the agent with no real mail. |

## What you need to bring

This repo does not connect to a mailbox or choose a local model for you. Those depend on your setup, and building them is the subject of a later episode. To use the agent on real mail, implement `MailProvider` in `placeholders/mail.py` and `DraftModel` in `placeholders/model.py`. Until then, the synthetic inbox and the template drafting model let you run everything end to end.

## Running it

You need [uv](https://docs.astral.sh/uv/), which installs Python 3.12 or newer for you if you do not have it, and a TypeSafe API key. Create the key on the [TypeSafe console](https://console.typesafe.ai/keys) and set it in your environment as `TYPESAFE_API_KEY`. The [TypeSafe quick start](https://docs.typesafe.ai/introduction/quickstart) covers the rest.

```bash
git clone https://github.com/ghosthat-studio/wiring-jev-into-a-local-agent
cd wiring-jev-into-a-local-agent
export TYPESAFE_API_KEY=...
uv run python -m inbox_agent --fresh --runs 3
```

`--fresh` forgets earlier runs. `--runs` runs the agent several times in a row, as if over several days, so you can see that it never drafts twice on the same thread. `--threshold` sets how likely, according to Jev, a message must be to need a reply before a draft is written (the default is 0.4, low on purpose: when an email could go either way, a draft to rewrite costs less than a missed reply). After the runs, the agent scores itself against the correct answers recorded in the synthetic inbox. On the episode's inbox you should see no wrong labels, no drafts to mail that needed no reply, no drafts to friends, three messages flagged for the owner to answer herself, and two or three sent to a person for review.

The tests do not need a key:

```bash
uv run pytest
```

### Messages the questions were not written against

`fixtures/inbox.json` is the inbox from the episode, and Jev's instructions were written while looking at it. To check that the instructions are not simply tuned to it, the repo includes two more inboxes written by someone who had not seen the instructions:

```bash
uv run python -m inbox_agent --fresh --inbox fixtures/holdout.json
uv run python -m inbox_agent --fresh --inbox fixtures/holdout2.json
```

### The agent without Jev

The "before" in the episode is the same agent with one local model making every decision as it writes. It runs on [Ollama](https://ollama.com/) and needs the model pulled first:

```bash
ollama pull qwen3.5:9b
uv run python -m inbox_agent --baseline --no-state --fresh --runs 3
```

`--no-state` turns off the check-before-you-act memory, which is how the repeated drafts in the episode happen. `--no-think` switches the model's thinking off, which is faster and weaker; the episode's recording used it. Use `--model` for a different Ollama model. A local model's answers vary from run to run, so your numbers will not match the episode's exactly, but the kinds of mistake will.

### Seeing a run as an inbox

```bash
uv run python -m inbox_agent.view --run-dir .run --title "After three runs with Jev" --out inbox.html
```

This writes a page that shows each message with the label the agent gave it and the drafts it wrote, with mistakes marked against the correct answers. `inbox_agent.compare` runs the agent with and without Jev on the same inbox and writes the scores side by side.

Every message in the synthetic inboxes is invented, and every address uses the reserved `.example` domain.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
