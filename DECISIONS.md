# Decisions

Episodic memory: what was decided, and why, tied to specific tickets — not
just the general facts about the system (that's `CLAUDE.md`). Appended to
by `pr-reviewer` after each ticket is approved. Don't hand-wave entries —
"fixed the bug" is not a decision record.

Format per entry:

```
## <TICKET-KEY> — <one-line title>
Date: YYYY-MM-DD
Risk tier: LOW | MEDIUM | HIGH | CRITICAL
Decision: what was actually decided or changed, in plain language.
Against acceptance criteria: which ones this satisfies, verbatim from
  the scope contract, not paraphrased.
Notes: anything a future ticket touching this area should know —
  trade-offs taken, things deliberately left out of scope, alternatives
  considered and rejected and why.
```

---

<!-- Entries below this line, most recent first -->

## EPT-25 — Policy Search & Filtering (approved, PR opened)
Date: 2026-09-22
Risk tier: MEDIUM
Decision: Approved and merged into a draft PR: client-side search
  (partial match) and combinable status/type filters on the Policies
  catalog and My Policies pages, via a new shared PolicySearchFilter
  component and policyFilter.js helper. No backend/schema changes. At
  Gate 1 the human resolved three open items: (1) the catalog Policy
  model has no policy_number/status fields, so that tab keeps title
  search + type-only filtering rather than adding a schema migration for
  catalog "status"/SKU concepts (option a); (2) search/filter state
  resets independently per tab on navigation (no cross-tab persistence);
  (3) the existing single-select FILTERS bar on Policies.js was
  intentionally replaced by a multi-select type filter. At Gate 2 the
  reviewer additionally noted (not blocking, not discussed at Gate 1)
  that My Policies' type-filter chips are dynamically derived from
  owned policies while the catalog tab always shows a static 5-chip
  list — approved as-is.
Against acceptance criteria: AC-001..AC-007 in .claude/current-scope.yaml
  (search, combinable filters, tab scoping/isolation, empty-state split,
  clear action, visual alignment). All 18 TC-nnn test cases pass; full
  verification pyramid green (build, unit, integration/Playwright), no
  regressions in pre-existing suites.
Notes: True policy-number search and status filtering on the catalog tab
  were explicitly descoped, not deferred by accident — a future ticket
  adding catalog SKU/status concepts needs its own schema migration and
  PRD decision. Evidence bundle: .agentic/tickets/EPT-25/evidence.md.
