# Companion repo: Old Nain 001

This is the open-source companion repo for Old Nain episode 001, "Wiring Jev into a local agent" (https://youtu.be/cm_4AmKAtmo).

## Writing code for this repo

- The code appears on screen in the episode, recorded with VHS. Keep files short and readable in one take, and keep names plain.
- Only the technique is real code: the state check and the Jev gate. The mail integration and the drafting model stay as clearly marked placeholders.
- Jev calls are written from TypeSafe's current docs, never from memory.
- Comments, docstrings and the README use complete sentences in plain language.
- Everything in `fixtures/` is synthetic and uses `.example` domains. Never add real email, names or companies.
- Run `uv run pytest` after changes.

## Keeping the test honest

- Never edit a message in `fixtures/inbox.json` so that it fits the gate's question wording. If a case is ambiguous, keep it and add a counterpart that tests the distinction (m-24 and m-35 are the model: the same payment request with and without a pay link).
- Never tune the label descriptions or the reply question against this inbox to raise the score. Before recording, freeze both, and check the numbers on messages written by someone who has not read the questions.
