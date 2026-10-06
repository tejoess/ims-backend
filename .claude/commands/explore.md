---
description: Read-only tour of an area of the codebase. No branch, no state, no gates.
argument-hint: <area or subsystem>
allowed-tools: Read, Grep, Glob
---

Tier 0 — read only. You may not write, edit, or run anything that mutates state.
Do not create a branch, a scope contract, or a ticket folder.

Map this area of the codebase: **$ARGUMENTS**

Report:
1. Entry points and the main modules involved.
2. How data flows through it, at the level someone new would need.
3. Existing conventions in play — test framework, error handling, naming.
4. Anything that looks like two competing implementations of the same thing.
5. What you could NOT determine from the code, and what would answer it.

If you find something you think should change, say so and stop. Proposing a
change is in scope; making one is not.
