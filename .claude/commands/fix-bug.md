---
description: Phase 3 for a bug — reproduce first, then plan the fix.
argument-hint: <JIRA-KEY>
allowed-tools: Read, Grep, Glob, Bash, Task
---

Ticket: **$ARGUMENTS**

Same preconditions and outputs as `/plan`, with one change to the planner's job:
its deliverable is a **reproduction, not a design**.

1. Run the `reproduce-bug` skill FIRST. If it does not reproduce, stop and
   report — do not plan a fix for a defect you cannot observe.
2. The failing reproduction test IS this ticket's RED artifact. Record its path
   in `test-plan.md` and in `frozen_tests` in the scope contract. `/implement`
   will not need to write a separate failing test.
3. State the root cause explicitly and separately from the proposed fix.

Gate 1 for a bug is a narrower question: **is this the right root cause?**
