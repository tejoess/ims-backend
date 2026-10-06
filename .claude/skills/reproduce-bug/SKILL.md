---
name: reproduce-bug
description: For bug tickets, reproduce the reported failure — ideally as a failing test — before writing any fix. Required before the implementer starts work on anything tagged as a bug.
---

Preferred bug flow, from the POC design doc section 8: ticket → reproduce
→ failing regression test → implement fix → test passes. Never skip
straight from "plausible cause" to "fix."

Steps:

1. Read the bug report and acceptance criteria closely — what's the exact
   expected vs. actual behavior?
2. Attempt to reproduce it directly: a script, a manual command, or
   (preferably) a new test that currently fails for the reported reason.
3. If it reproduces: capture the failing test or reproduction command as
   the first artifact. This becomes the evidence that the eventual fix
   actually addresses the reported defect, not just a plausible-looking
   change.
4. If it does NOT reproduce: stop. Do not guess at a fix for a bug you
   can't observe. Report back — the ticket may be stale, environment-
   specific, or already fixed — and ask before proceeding.
5. Only after reproduction succeeds does the plan move to "how to fix it."
   The plan you present for approval should reference the reproduction
   artifact directly.
