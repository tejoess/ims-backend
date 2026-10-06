# Failure taxonomy

"The agent failed" is not actionable. This taxonomy (from the POC design
doc, section 11) is — it tells you which part of the harness needs
engineering attention, rather than which prompt to tweak.

When a ticket ends up in `evals/failures/` or `evals/regressions/`, tag it
with one of these:

- **Requirement misunderstanding** — the technical PRD or ticket was
  ambiguous and got interpreted wrong. Fix: the Requirement Agent should
  have asked about this.
- **Context retrieval failure** — the agent didn't find the relevant code.
  Fix: improve repository context/retrieval, not the prompt.
- **Planning failure** — the plan was reasonable-looking but wrong. Fix:
  the plan-review gate should have caught this; look at why it didn't.
- **Wrong implementation** — plan was right, code was wrong.
- **Test-generation failure** — the tests written didn't actually cover
  the acceptance criteria.
- **Test failure** — implementation genuinely doesn't work yet (expected,
  bounded-retry territory, not necessarily a real "failure" to log).
- **Regression** — something unrelated broke. Check whether `allowed_paths`
  was too broad.
- **Scope violation** — the agent tried to touch something outside its
  contract. If a guard hook caught it, that's the system working; log it
  anyway to see if it's a pattern.
- **Security violation** — anything touching auth/secrets/IAM without
  the CRITICAL tier and explicit human execution.
- **Tool/environment failure** — MCP server down, flaky test infra, etc.
  Not the agent's fault; still worth tracking if it recurs.
- **Dependency failure** — a forbidden dependency change was attempted or
  a real one broke something.
- **Cost/token exhaustion** — ran over budget before finishing.
- **Repeated-loop failure** — hit the 3-attempt cap without resolving.
- **Human rejection** — plan or PR sent back with notes. Not a bug in the
  system, but worth tracking if the same kind of thing keeps getting
  rejected.
- **False positive / false negative** — verification said pass when it
  should have failed, or vice versa.

The point of tracking this: if 40% of your failures are context-retrieval
failures, better prompts won't fix it — better repository context will.
