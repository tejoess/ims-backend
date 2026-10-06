---
description: Walk through an existing file, module, or diff. Read-only.
argument-hint: <file, module, or commit/PR ref>
allowed-tools: Read, Grep, Glob, Bash
---

Tier 0 — read only. You may run read-only git commands (log, show, diff, blame).
No writes, no branch, no state.

Explain: **$ARGUMENTS**

Cover what it does, why it is shaped the way it is (use git history if it
helps), what depends on it, and the parts that would surprise someone changing
it. Skip anything obvious from the code itself.
