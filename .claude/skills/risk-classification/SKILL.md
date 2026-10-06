---
name: risk-classification
description: Classify a ticket's risk tier (LOW/MEDIUM/HIGH/CRITICAL) before planning begins. Determines how much autonomy the rest of the pipeline gets and what the scope contract should restrict.
---

Every ticket gets exactly one risk tier before a plan is drafted. Use this table (from the POC design doc) — don't invent new tiers:

| Risk | Typical change | What it means downstream |
|---|---|---|
| LOW | Unit-tested internal logic, small features, docs | Agent may implement after plan approval, normal flow |
| MEDIUM | API behavior, DB queries, shared services | Extra verification pass before review |
| HIGH | Auth, schema, security-sensitive logic | Extra human checkpoint, restricted autonomy |
| CRITICAL | Production infra, IAM, payments, destructive ops | Plan-only — a human executes, the agent does not |

Steps:

1. Read the ticket and its acceptance criteria. Identify what layer of the
   system it touches (isolated feature code vs. shared service vs.
   auth/schema vs. infra).
2. Pick the tier honestly — when in doubt, round up, not down. A ticket
   that's probably LOW but touches one shared file is MEDIUM.
3. Write the tier into `risk:` in the scope contract (see
   `definition-of-done` skill). This is not optional — every ticket must
   have a declared tier before implementation starts.
4. If the tier is HIGH or CRITICAL, say so explicitly in the plan you
   present for approval, and flag that extra scrutiny is warranted —
   don't let a HIGH-risk ticket look routine in the summary.
5. For a first POC or demo, prefer selecting LOW-risk tickets deliberately
   — this proves the workflow without betting the demo on maximum
   autonomy.
