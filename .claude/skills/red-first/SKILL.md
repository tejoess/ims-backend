---
name: red-first
description: Write the approved test plan as real failing tests, confirm they fail for the right reason, and freeze them — before any implementation code is written. Used by the implementer agent at the start of phase 4.
---

Test-first is only a claim until something proves the tests failed before the
code existed. This skill is that proof, and it costs one extra test run.

Sequence:

1. Read `.agentic/tickets/<KEY>/test-plan.md`. Write **every** case in it as a
   real test in the project's existing framework — not a subset, not
   placeholders. Tag each with its `TC-nnn` and `AC-nnn` ids (see the
   `traceability` skill).

2. Run them. Capture the full output to `.agentic/tickets/<KEY>/red.log`.

3. Read the failures. Each one must fail for the reason the test plan predicts —
   a missing endpoint, a wrong return value, an absent column. A test failing on
   an import error, a typo, or a fixture problem is not RED, it is broken; fix
   the test and re-run before moving on.

4. **If a test passes here, stop.** Either the test does not assert what the
   acceptance criterion says, or the behaviour already exists and the ticket is
   narrower than it looks. Both are things a human needs to know before you
   write code, not after.

5. Commit the tests on their own: `test(<KEY>): failing tests for AC-001..n`.
   A separate commit is what makes the RED state reviewable in the diff later.

6. Add the test file paths to `frozen_tests` in `.claude/current-scope.yaml`
   AND write the same list to `.agentic/tickets/<KEY>/frozen.lock`, one path per
   line. Set `red_captured: true` in `state.json`.

   Both files, deliberately: the scope contract is writable by the pipeline, so
   a list kept only there could be unfrozen by deleting a line. `frozen.lock` is
   matched by `sensitive-paths.txt` and cannot be edited without a human setting
   `ALLOW_SENSITIVE=1`. `guard-frozen-tests.sh` reads the union of the two.

`red.log` is part of the evidence bundle. The pair — these tests failing, then
the same tests passing — is the strongest single artifact the review gate reads.

For bug tickets the reproduction from `reproduce-bug` already is the RED
artifact; record it and skip step 1 for that criterion.
