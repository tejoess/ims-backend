---
description: Revise the plan, test plan, and scope contract together from developer feedback, then re-present for Gate 1.
argument-hint: <what to change>
allowed-tools: Read, Edit, Write, Bash, Grep, Glob, Task
---

Requested change: **$ARGUMENTS**

Preconditions — refuse and stop if either fails:

- `.claude/current-scope.yaml` exists and `.agentic/tickets/<KEY>/plan.md` exists.
  Nothing to revise otherwise; the human wants `/plan`.
- Phase is `WAITING_FOR_APPROVAL` or `REVIEW`. Any other phase means a revision
  would leave the plan and the work out of step — report the phase and stop.

## First, classify the feedback

Before changing anything, decide which of these it is and say so:

**Technical revision** — a different approach, a different file, a missing edge
case, a test that should exist. Yours to make. Proceed.

**Product decision** — it changes what the feature *does*: who may do it, when it
takes effect, what happens to related records. **Not yours to make.** Stop and
say it needs to go back to Part A (the requirement agent), because deciding it
here means inventing a requirement and the Jira ticket will no longer match the
code. Name the specific question that needs answering.

**Scope expansion** — the change adds work the ticket did not cover. Proceed, but
say plainly what it adds, and re-run `risk-classification`. If the tier moves up
(a migration appears, a public interface changes, auth is touched), say so
prominently — the human is approving a different-sized ticket than they were
about to.

## Then revise all three together

Never partially revise. `plan.md`, `test-plan.md` and `.claude/current-scope.yaml`
are one package, and a contract that no longer matches its plan is how scope
drift starts.

1. `plan.md` — apply the change. Append to a `## Revisions` section at the
   bottom: the date, what was asked for verbatim, and what you changed. Do not
   rewrite history; a plan that quietly becomes a different plan is not
   reviewable.
2. `test-plan.md` — add, remove or amend `TC-nnn` cases. Every `AC-nnn` must
   still have at least one TC. If the change removes an acceptance criterion,
   remove its test cases too rather than leaving them orphaned.
3. `.claude/current-scope.yaml` — update `acceptance_criteria`, `allowed_paths`,
   `forbidden_operations`, `risk` and `verification` to match. If the change
   introduces a migration, `migration_up` and `migration_down` both become
   `required`.
4. `state.json` — set `plan_approved: false` and phase `WAITING_FOR_APPROVAL`.
   A revised plan is unapproved by definition, even if the previous version was
   approved.

## If the phase was REVIEW (a Gate 2 scope rejection)

Implementation already exists and is now built against a superseded plan. Say
explicitly, before anything else, what is now stale:

- which frozen tests no longer match the revised test plan
- which committed code is outside the revised `allowed_paths`
- whether `red.log` is still valid or has to be recaptured

Then recommend one of: keep the branch and let `/implement` reconcile (small
changes), or `/abandon` back to the checkpoint and start clean (anything
structural). State which and why — do not leave the choice unframed.

Frozen tests stay frozen until the human approves this revision. Do not edit
them here.

## Finally

Re-present the three documents as a package with a short summary of what changed
and what it means for size and risk. Then stop. The human runs `/approve-plan`.