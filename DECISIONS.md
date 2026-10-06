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

## EPT-27 — Backend: Platform Audit Trail
Date: 2026-10-07
Risk tier: HIGH
Decision: Approved plan to implement the complete backend audit logging infrastructure.
  New `audit_logs` table (additive DDL, no existing tables touched). A synchronous
  `write_audit_event()` helper that never commits — callers own the transaction.
  All 18 events in the Audit Event Catalogue instrumented across 7 existing files.
  Four new trigger endpoints added (POST /logout, PUT /users/{id}/password,
  POST /claims/{id}/withdraw, PUT /userpolicies/{id}/auto-renew). Two new admin
  endpoints: GET /admin/audit-log (paginated, filterable) and GET /admin/audit-log/export
  (CSV, capped at 1 000 rows, writes ADMIN_AUDIT_LOG_EXPORTED before streaming).
  `PUT /claims/{id}/status` gains admin_only() guard as a bundled security fix.
  Commit pattern in `claims.py` restructured: db.flush() used to get claim ID before
  the first commit so CLAIM_SUBMITTED is atomic with claim creation.
  Down migration drops audit_logs entirely — data loss, not reversible.
Against acceptance criteria: AC-01 (table + indexes), AC-02 (all 18 catalogue events),
  AC-03/10 (USER_LOGIN_FAILURE without session), AC-04 (transactional writes),
  AC-05 (paginated list + all filters), AC-06 (CSV export + EXPORTED event),
  AC-07 (admin_only 403), AC-08 (no modification endpoints), AC-09 (EXPORTED before stream).
  33 TC-nnn test cases defined in test-plan.md.
Notes: entity_id stored as VARCHAR(100) rather than INT to avoid a future schema change
  if UUID-typed entities are introduced. POLICY_DUPLICATE_ATTEMPT and USER_LOGIN_FAILURE
  are the two events that commit independently before raising an exception — both are
  failure-path events with no successful triggering transaction. The admin_only() guard
  on PUT /claims/{id}/status is not optional: without it CLAIM_STATUS_ADMIN_CHANGED
  attribution is meaningless. EPT-28 (Frontend) cannot start until this ticket is
  deployed. Evidence bundle: .agentic/tickets/EPT-27/evidence.md (generated post-implementation).

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
