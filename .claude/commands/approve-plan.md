---
description: Gate 1 — record human approval of the plan, test plan, and scope contract.
argument-hint: "[optional note]"
allowed-tools: Read, Edit, Bash
---

This command IS the approval. Running it is the human's decision — you are
recording it, not making it.

Preconditions — refuse and stop if any fails:

- `.agentic/tickets/<KEY>/state.json` exists and phase is `WAITING_FOR_APPROVAL`.
  Any other phase means there is nothing awaiting approval; say which phase it
  is in and stop.
- `plan.md`, `test-plan.md`, and `.claude/current-scope.yaml` all exist.
- `test-plan.md` has at least one `TC-nnn` for every `AC-nnn` in the scope
  contract. An acceptance criterion with no test case cannot be approved — the
  RED step would silently skip it and the coverage table would report MISSING at
  Gate 2. Report which ACs are uncovered and stop.
- Every open question in `plan.md` is answered. An unanswered *product* question
  is Part A's to resolve — say so and stop rather than letting it become an
  assumption.

Then:

1. Set in `state.json`: `plan_approved: true`, phase `IMPLEMENTATION`,
   `_metrics.approved_at` to the current UTC timestamp.
2. Append to `DECISIONS.md`: the ticket key, the date, what was approved (a
   one-line summary of the plan), the risk tier, and `$ARGUMENTS` if the human
   passed a note. Approving a plan is a decision worth remembering — especially
   the ones that later turn out wrong.
3. Restate, in three lines, what `/implement` is now authorised to do: the
   branch it will create, the `allowed_paths` it is confined to, and the number
   of tests it will write at RED.
4. Stop. Do not start implementing — the human runs `/implement` next.

If the human wants changes instead, they say so and you revise the plan, the
test plan and the contract together, then re-present. Do not partially approve:
the three documents are one package, and approving a plan whose contract no
longer matches it is how scope drift starts.
