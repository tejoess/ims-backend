---
description: Phase 3 — pull a ticket, reproduce if a bug, plan, write the scope contract, request approval.
argument-hint: <JIRA-KEY>
allowed-tools: Read, Grep, Glob, Bash, Task
---

Ticket: **$ARGUMENTS**

Preconditions — check before doing anything:
- `.claude/current-scope.yaml` must NOT exist. If it does, another ticket is in
  flight. Report which one and stop; the human runs `/abandon` or finishes it.
- The working tree must be clean.

Before planning: the `planner` agent will read the parent ticket, all sibling
subtasks, and any linked tickets — pulling their comments for decisions,
API shapes, or constraints that affect this ticket. See step 1b in
`.claude/agents/planner.md`.

Run the `planner` agent for this ticket. It must produce, in
`.agentic/tickets/$ARGUMENTS/`:

- `plan.md` — summary, detailed steps, files/APIs/schema touched, trade-offs,
  assumptions, open questions, out of scope
- `test-plan.md` — one test case per acceptance criterion, each with a `TC-nnn`
  id mapped to its `AC-nnn` (see the `traceability` skill)
- A **Database changes** section inside `plan.md` whenever schema is touched —
  the concrete DDL shape, the up and down migration file paths, and an explicit
  statement of whether the down migration loses data. Write
  "Database changes: none" when it does not; an omitted section reads as
  "not considered."

- `state.json` — from `.agentic/state-template.json`, phase `WAITING_FOR_APPROVAL`

and `.claude/current-scope.yaml` at the repo root as usual.

Do not create the branch yet and do not write application code. Present the
plan, the test plan, and the scope contract together, then stop.

If the plan includes a migration, lead the summary with it and say in that same
line whether it reverses cleanly. Schema is the part of a change that a revert
does not undo, so it is the part a human should read first.

Gate 1 is the human answering: **is this what we actually want?**