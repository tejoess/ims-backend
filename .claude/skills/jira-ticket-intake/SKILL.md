---
name: jira-ticket-intake
description: Pull a Jira ticket's full context — description, acceptance criteria, comments, and linked issues — via the Atlassian MCP connector, before planning starts.
---

Given a ticket key:

1. Fetch the ticket's summary, description, and acceptance criteria.
2. Fetch comments — clarifications often live there, not in the original
   description.
3. Fetch linked issues (blocks/is blocked by/relates to) — a plan that
   ignores a linked ticket is a plan built on incomplete context.
4. If the ticket references a Technical PRD (e.g. from the Requirement
   Agent), fetch and read that in full before treating context as
   complete — it's the authoritative spec, the ticket description is a
   summary of it.
5. Do not proceed to planning on a ticket that's missing acceptance
   criteria entirely — flag it back on the ticket and ask, rather than
   guessing what "done" means.
