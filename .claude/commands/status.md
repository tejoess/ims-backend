---
description: Where the current ticket stands — phase, attempts, what is blocking.
allowed-tools: Read, Bash, Glob
---

Read `.claude/current-scope.yaml` and every `.agentic/tickets/*/state.json`.

Report, in a few lines:
- Ticket key, risk tier, branch, phase
- `plan_approved`, `attempt` / `max_attempts`
- Which artifacts exist so far (plan, test-plan, red.log, evidence, diff)
- The single next action, and which command performs it

If nothing is in flight, say so — that is a valid state, not an error.
This command is how you resume after a crashed or closed session.
