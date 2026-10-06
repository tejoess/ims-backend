---
name: traceability
description: Link acceptance criteria to tests with ids carried inside the test code itself, so requirement coverage is derived from the test run rather than asserted in a document.
---

A YAML file that says `AC-001 -> TC-001` is a claim nobody verifies and that
drifts the first time a test is renamed. Put the id where the runner will see it.

The chain: `REQ` (the ticket) → `AC-nnn` (scope contract) → `TC-nnn` (test plan)
→ the test function → the runner's output → `evidence.md`.

Rules:

1. Number acceptance criteria `AC-001..n` in `.claude/current-scope.yaml`. These
   are the ids everything else references.
2. Number test cases `TC-001..n` in `test-plan.md`, each naming the `AC-nnn` it
   covers. One AC may have several TCs; every AC must have at least one.
3. Carry the id **inside the test**, in whatever form the framework makes
   greppable and ideally filterable:

   - pytest: `@pytest.mark.tc("TC-001")` plus an `AC-002` mention in the
     docstring, or `def test_tc001_expired_policy_rejected():`
   - Vitest / Jest: `it("TC-001 / AC-002 — rejects an expired policy", ...)`
   - JUnit: `@Tag("TC-001")`
   - Go: `func TestTC001_RejectsExpiredPolicy(t *testing.T)`

   Follow whatever the repo already does if it has a convention; consistency
   inside the project beats consistency with this file.

4. `collect-evidence.sh` greps the test sources for each `TC-nnn` in the test
   plan. An id in the plan with no test in the tree is reported as **MISSING** —
   that is the check this whole convention exists to enable, and it is the
   quietest way an acceptance criterion gets dropped.

Do not maintain a separate traceability document. If the ids are in the tests,
the table generates itself; if they are not, a document would be wrong anyway.
