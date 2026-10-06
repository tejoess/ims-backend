---
description: Brief pointwise summary of a Jira ticket. Tier 0 — read only.
argument-hint: <JIRA-KEY>
allowed-tools: Read, Bash
---

Tier 0 — read only. No writes, no branch, no state.

Ticket: **$ARGUMENTS**

Fetch the ticket using the Atlassian MCP. Print a concise summary:

- **Title** — one line
- **Type** — Bug / Story / Task / Subtask
- **Status** — current status
- **Priority** — if set
- **Goal** — what the ticket is trying to achieve (1–2 sentences max)
- **Acceptance criteria** — bullet list, each criterion one line
- **Out of scope** — anything explicitly excluded (skip section if none stated)
- **Dependencies** — linked tickets or blockers (skip if none)
- **Assignee / Sprint** — who owns it, which sprint

Keep every bullet to one line. No prose. No restatement of context.
If a field is not set, omit it rather than writing "not set."
