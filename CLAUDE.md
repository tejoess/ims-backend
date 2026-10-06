# Project memory

This file is read every session. Keep it accurate — it's the single source
of truth Claude relies on before touching code. Update it deliberately when
architecture facts change; don't let it go stale.

## What this project is

TODO: one paragraph — what the system does, who it's for.

## The pipeline

1. **Requirement clarification** (`requirement-agent`, or the standalone
   Streamlit app in `requirement-agent-app/`) — PM's PRD/text → zero-
   assumption technical PRD, via MCQ clarifying questions.
2. **Task breakdown** — approved PRD → Jira ticket(s), pushed via the
   Atlassian MCP connector.
3. **Development planning** (`planner`) — ticket + PRD → reproduction (if
   bug) → risk tier → plan → test plan with AC→TC ids → scope contract
   (`current-scope.yaml`) → human approval. **Gate 1.**
4. **Implementation** (`implementer`) — RED first (the test plan written as
   real failing tests, captured in `red.log`, then frozen), then a bounded
   code/fix loop inside the declared scope.
5. **Testing** (`tester`) — fully automated verification pyramid, no human
   involved, bounded loop back to implementer on failure. Evidence is
   generated from raw runner output, not narrated.
6. **PR review** (`pr-reviewer`) — risk/bottleneck review + ONE consolidated
   human gate (evidence + diff + findings together) → draft PR. **Gate 2.**

Two human checkpoints total: plan approval (phase 3) and the consolidated
review gate (phase 6). Everything else is automated and bounded.

### Commands

Tier 0 is read-only and has no gates, no branch, no state — most day-to-day
agent use lives here and should not pay the pipeline's overhead:

| Command | Does |
|---|---|
| `/explore <area>` | Map a subsystem: entry points, flow, conventions |
| `/find <thing>` | Locate behaviour, callers, duplication, dead code |
| `/explain <ref>` | Walk through a file, module, or diff |
| `/estimate <KEY>` | Rough plan and size, without entering the pipeline |
| `/ticket <KEY>` | Brief pointwise summary of a Jira ticket |
| `/diff [base]` | Quick summary of current git diff vs base branch |
| `/scope` | Show current ticket in flight, phase, allowed paths |

The pipeline proper. Each refuses to run if `state.json` is not in its
required phase — that refusal is what makes the gates real rather than
conventional:

| Command | Requires | Does |
|---|---|---|
| `/plan <KEY>` | no ticket in flight | Phase 3 → Gate 1 |
| `/fix-bug <KEY>` | no ticket in flight | Phase 3, reproduce-first variant |
| `/implement` | `plan_approved: true` | Branch, RED, code, verify, fix loop |
| `/review` | phase `EVIDENCE` | Gate 2, three outcomes |
| `/create-pr` | phase `APPROVED` | Draft PR, Jira, DECISIONS.md |
| `/status` | any | Phase, attempts, next action — how you resume |
| `/abandon` | any | Reset to checkpoint, clear the contract |
| `/update-plan <feedback>` | phase `WAITING_FOR_APPROVAL` or `REVIEW` | Revise the plan package, back to Gate 1 |
### State

`.agentic/tickets/<KEY>/state.json` (from `.agentic/state-template.json`) holds
the phase, `plan_approved`, `red_captured`, `attempt`/`max_attempts`, the branch
and the checkpoint SHA. It is the resume point after a crashed or closed
session — `/status` reads it. Phases:

```
ANALYSIS → WAITING_FOR_APPROVAL → IMPLEMENTATION → VERIFICATION
                                                      │
                                        FAIL → FIX ───┤ 3 attempts → BLOCKED
                                                      │
                                                    PASS → EVIDENCE → REVIEW
                                                                        │
                                    wrong scope → back to ANALYSIS ─────┤
                                    broken → back to VERIFICATION ──────┤
                                                                        │
                                                            APPROVED → PR
```

### Reverse clarification

If a ticket turns out to contain a business question that phase 1 did not
resolve, that is not something to decide here. Raise it back to the requirement
agent (Part A), get the answer recorded there, let the Jira ticket and project
memory update, then resume. A business question answered inside the
implementation loop is an invented requirement.

## Architecture notes

TODO: the load-bearing facts an agent needs before making changes — key
services, where core logic lives, which layer owns what. Flag anything
unconfirmed as unconfirmed, don't guess.

## How to run things

These are also the commands `collect-evidence.sh` runs — fill them in or the
evidence bundle reports layers as SKIPPED.

- Build: `TODO`            (`BUILD_CMD`)
- Lint/format: `TODO`      (`LINT_CMD`)
- Type check: `TODO`       (`TYPE_CMD`)
- Unit tests: `TODO`       (`UNIT_CMD`)
- Integration tests: `TODO` (`INTEGRATION_CMD`)
- Migration up / down: `TODO` / `TODO`  (`MIGRATE_UP_CMD` / `MIGRATE_DOWN_CMD`)
- Local dev server: `TODO`

## Branch and PR conventions

- Branch naming: `feature/<JIRA-KEY>` unless this repo says otherwise — one
  branch per ticket, created by `/implement` with a checkpoint commit whose SHA
  goes into `state.json`.
- Base branch: `TODO`
- PRs open as **drafts**. A human marks ready and merges.
- PR description must link back to the originating Jira ticket key and to
  `.agentic/tickets/<KEY>/evidence.md`.

## Cross-ticket coordination

Before planning or implementing, read the comments on related tickets (parent,
siblings, linked) and use anything relevant. After opening a PR, comment on the
ticket with decisions, changes, and notes for related tickets.

## Guardrails — do not cross without explicit human approval

- Do not modify deploy configuration, IAM policies, secrets, or `.env`
  files. Enforced by `.claude/hooks/guard-sensitive-paths.sh` (global
  denylist, always active) and `.claude/hooks/guard-scope-edit.sh` +
  `guard-scope-ops.sh` (per-ticket allowlist, active once a plan is
  approved). If a hook blocks you, stop and ask — don't work around it.
  If a legitimate path keeps getting blocked, the fix is a human updating
  `.claude/current-scope.yaml` or `sensitive-paths.txt`, not the scripts.
- Do not exceed 3 fix attempts on a failing check without stopping and
  reporting back (`implementer.md`, `tester.md`).
- **Never edit a frozen test.** Once `frozen_tests` is populated in the scope
  contract, those files are off limits — enforced by
  `.claude/hooks/guard-frozen-tests.sh`. Making a failing assertion pass by
  changing the assertion invalidates every piece of evidence the review gate
  reads. If a test is genuinely wrong, that is a finding to report, not a fix
  to make.
- **Never merge a PR, and never mark one ready for review.** PRs open as
  drafts. Both actions are a human's, every time, however green the evidence.
- Do not write pass/fail results by hand. Evidence comes from
  `.claude/scripts/collect-evidence.sh`, which only transcribes what the
  runners actually printed.
- Never invent API endpoints, schema fields, or config values you haven't
  actually read from the codebase, the ticket, or its Technical PRD.
- Every ticket must have a declared risk tier before implementation
  starts (`risk-classification` skill).

## Skills

Repeatable procedures live in `.claude/skills/`. If a pattern repeats
across tickets, use `skill-proposal` to draft a new skill for human
review — it only ever produces a `-draft`, never a live skill on its own.
