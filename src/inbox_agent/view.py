"""See a run as an inbox: every message with the label the agent gave it and the drafts it wrote.

    uv run python -m inbox_agent.view --run-dir runs/before --title "After three runs without Jev" --out before.html

Mistakes are marked against the correct answers recorded in the inbox file: a
wrong label is struck through with the right one written beside it, extra drafts
on the same message are counted, and drafts nobody needed are flagged. Messages
the agent flagged for Nain to answer herself are marked as hers.
"""

import argparse
import html
import json
from collections import Counter
from pathlib import Path

from inbox_agent.message import REVIEW
from inbox_agent.score import label_ok

GENERIC_SENDERS = {"accounts", "billing", "news", "hello", "noreply", "no-reply", "info", "help", "office", "events",
                   "statements", "autopay", "alerts", "updates", "digest", "secretary", "legal", "support", "team"}
LABEL_NAMES = {"billing": "Billing", "scheduling": "Scheduling", "newsletter": "Newsletter", "personal": "Personal",
               "needs_human": "Needs Nain", "other": "Other", REVIEW: "For Nain to check"}


def sender_name(address: str) -> str:
    local, domain = address.split("@")
    if local.lower() in GENERIC_SENDERS:
        return domain.split(".")[0].replace("-", " ").title()
    return local.replace(".", " ").replace("_", " ").replace("-", " ").title()


def build(inbox: Path, run_dir: Path, title: str) -> str:
    data = json.loads(inbox.read_text())
    box = json.loads((run_dir / "mailbox.json").read_text())
    labels = box.get("labels", {})
    drafts = Counter(d["message_id"] for d in box.get("drafts", []))
    flagged = set(box.get("flagged", []))
    answered = set(data.get("replied_threads", []))

    rows, wrong, extra, unneeded, review, hers, friends = [], 0, 0, 0, 0, 0, 0
    for m in sorted(data["messages"], key=lambda m: m["received_at"], reverse=True):
        e, label, n = m["expected"], labels.get(m["id"]), drafts[m["id"]]
        marks = []
        if label == REVIEW:
            review += 1
            label_html = f'<span class="chip review">{LABEL_NAMES[REVIEW]}</span>'
        elif label is None:
            label_html = '<span class="none">not labelled</span>'
        elif label_ok(label, e):
            label_html = f'<span class="chip">{LABEL_NAMES[label]}</span>'
        else:
            wrong += 1
            label_html = (f'<span class="chip struck">{LABEL_NAMES[label]}</span>'
                          f'<span class="ink">should be {LABEL_NAMES[e["label"]].lower()}</span>')
        if n:
            draft_html = f'<span class="drafts">{n} draft{"s" if n > 1 else ""}</span>'
            if n > 1:
                extra += n - 1
                marks.append(f"{n - 1} extra")
            if not e["needs_reply"]:
                unneeded += n
                marks.append("no reply needed")
            elif e.get("from_friend"):
                friends += 1
                marks.append("Nain writes to friends herself")
            elif m["thread_id"] in answered:
                unneeded += n
                marks.append("already answered")
            if marks:
                draft_html = f'<span class="drafts marked">{n} draft{"s" if n > 1 else ""}</span><span class="ink">{", ".join(marks)}</span>'
        elif m["id"] in flagged:
            hers += 1
            draft_html = '<span class="mine">for Nain to write</span>'
        else:
            draft_html = ""
        flagged_row = " flagged" if ("struck" in label_html or marks) else ""
        rows.append(f"""
      <li class="row{flagged_row}">
        <span class="from">{html.escape(m.get("from_name") or sender_name(m["sender"]))}</span>
        <span class="msg"><span class="subject">{html.escape(m["subject"])}</span><span class="snippet">{html.escape(m["body"][:110])}</span></span>
        <span class="label">{label_html}</span>
        <span class="draft">{draft_html}</span>
      </li>""")

    folder_counts = Counter(labels.values())
    folders = "".join(
        f'<li><span>{LABEL_NAMES[k]}</span><span class="count">{folder_counts.get(k, 0)}</span></li>'
        for k in ("billing", "scheduling", "newsletter", "personal", "needs_human", "other", REVIEW)
        if k != REVIEW or folder_counts.get(REVIEW))
    folders += f'<li class="drafts-folder"><span>Drafts</span><span class="count">{sum(drafts.values())}</span></li>'
    tally = [f"<b>{wrong}</b> wrong label{'s' if wrong != 1 else ''}",
             f"<b>{extra}</b> extra draft{'s' if extra != 1 else ''}",
             f"<b>{unneeded}</b> unnecessary draft{'s' if unneeded != 1 else ''}"]
    if friends:
        tally.append(f"<b>{friends}</b> {'friend' if friends == 1 else 'friends'} written to for Nain")
    if hers:
        tally.append(f"<b>{hers}</b> for Nain to write herself")
    if review:
        tally.append(f"<b>{review}</b> for Nain to check")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Nain's inbox</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700&family=IBM+Plex+Mono:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
<style>
  :root {{
    --ground: #0A0B0E; --panel: #0D0F12; --line: #1E2228; --text: #C4C9D4; --dim: #B3B9C4;
    --spectral: #B8C7D6; --brass: #5C4220; --ink: #E0B66C;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--ground); color: var(--text); font-family: "Bricolage Grotesque", sans-serif; font-size: 22px; }}
  .app {{ display: grid; grid-template-columns: 300px 1fr; min-height: 100vh; }}
  nav {{ background: var(--panel); border-right: 1px solid var(--line); padding: 48px 32px; }}
  nav h1 {{ font-size: 32px; font-weight: 700; letter-spacing: -0.01em; margin-bottom: 36px; }}
  nav ul {{ list-style: none; font-family: "IBM Plex Mono", monospace; font-size: 20px; }}
  nav li {{ display: flex; justify-content: space-between; padding: 10px 0; color: var(--dim); }}
  nav .count {{ color: var(--text); }}
  nav .drafts-folder {{ margin-top: 18px; padding-top: 22px; border-top: 1px solid var(--line); }}
  main {{ padding: 48px 56px; }}
  header {{ margin-bottom: 36px; }}
  header p {{ font-family: "IBM Plex Mono", monospace; font-size: 20px; color: var(--dim); margin-bottom: 14px; }}
  .tally {{ font-size: 44px; font-weight: 600; line-height: 1.2; letter-spacing: -0.015em; max-width: 44ch; }}
  .tally b {{ color: var(--ink); font-weight: 700; }}
  ul.list {{ list-style: none; border-top: 1px solid var(--line); }}
  .row {{ display: grid; grid-template-columns: 250px minmax(0, 1fr) 420px 290px; gap: 28px; align-items: center;
          padding: 16px 12px; border-bottom: 1px solid var(--line); }}
  .row.flagged {{ background: linear-gradient(90deg, rgba(224, 182, 108, 0.07), transparent 70%); box-shadow: inset 4px 0 0 var(--ink); }}
  .from {{ font-weight: 600; font-size: 23px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .msg {{ display: flex; gap: 14px; min-width: 0; white-space: nowrap; overflow: hidden; }}
  .subject {{ font-weight: 600; }}
  .snippet {{ color: var(--dim); overflow: hidden; text-overflow: ellipsis; }}
  .label {{ display: flex; gap: 14px; align-items: baseline; }}
  .draft {{ display: flex; flex-direction: column; gap: 2px; }}
  .label, .draft {{ font-family: "IBM Plex Mono", monospace; font-size: 19px; white-space: nowrap; }}
  .chip {{ border: 1px solid var(--spectral); color: var(--spectral); border-radius: 4px; padding: 3px 10px; }}
  .chip.struck {{ border-color: var(--dim); color: var(--dim); text-decoration: line-through; text-decoration-color: var(--ink); text-decoration-thickness: 2px; }}
  .chip.review {{ background: var(--spectral); color: var(--ground); }}
  .drafts {{ color: var(--text); }}
  .drafts.marked {{ color: var(--ink); }}
  .ink {{ color: var(--ink); font-style: italic; }}
  .none {{ color: var(--dim); }}
  .mine {{ color: var(--spectral); border: 1px dashed var(--spectral); border-radius: 4px; padding: 3px 10px; align-self: flex-start; }}
</style></head>
<body><div class="app">
  <nav><h1>Inbox</h1><ul>{folders}</ul></nav>
  <main>
    <header><p>{html.escape(title)}</p><h2 class="tally">{". ".join(tally)}.</h2></header>
    <ul class="list">{"".join(rows)}
    </ul>
  </main>
</div></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inbox", type=Path, default=Path("fixtures/inbox.json"))
    parser.add_argument("--run-dir", type=Path, default=Path(".run"))
    parser.add_argument("--title", default="Nain's inbox")
    parser.add_argument("--out", type=Path, default=Path("inbox.html"))
    args = parser.parse_args()
    args.out.write_text(build(args.inbox, args.run_dir, args.title))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
