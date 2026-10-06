---
description: Show the current ticket in flight, its phase, and what paths are allowed. Tier 0 — read only.
allowed-tools: Read, Bash, Glob
---

Tier 0 — read only. No writes, no branch, no state.

Print the current pipeline state:

1. Check if `.claude/current-scope.yaml` exists.
   - If not: "No ticket in flight." Stop.

2. Read `.claude/current-scope.yaml` and print:
   - **Ticket** — the key
   - **Phase** — from `state.json` (`.agentic/tickets/<KEY>/state.json`)
   - **Plan approved** — yes/no
   - **Attempt** — current / max
   - **Branch** — from `state.json`
   - **Allowed paths** — flat list from `allowed_paths`
   - **Forbidden ops** — flat list from `forbidden_operations`
   - **Frozen tests** — list from `frozen_tests`, or "none"
   - **Verification required** — which layers are `required`

3. One-line next action based on phase:
   - `WAITING_FOR_APPROVAL` → "Run `/approve-plan` or `/update-plan <feedback>`"
   - `IMPLEMENTATION` → "Run `/implement` to continue"
   - `VERIFICATION` → "Tester is running"
   - `EVIDENCE` → "Run `/review`"
   - `REVIEW` → "Awaiting human gate"
   - `APPROVED` → "Run `/create-pr`"
   - `PR` → "PR open, awaiting human merge"
   - `BLOCKED` → "Blocked — review attempt log and intervene"

Keep everything to one line per item. No prose.
