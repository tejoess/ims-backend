---
description: Locate behaviour, callers, duplication, or dead code. Read-only.
argument-hint: <what to find>
allowed-tools: Read, Grep, Glob
---

Tier 0 — read only. No writes, no branch, no state.

Find: **$ARGUMENTS**

For each hit, give the file path, the line, and one sentence on why it is
relevant. If there are more than ~15 hits, group them and report the shape of
the result rather than listing everything.

Then answer explicitly: where does this behaviour actually live, who calls it,
and is there more than one implementation of it?
