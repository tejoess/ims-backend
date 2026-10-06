---
description: Quick summary of the current git diff — what changed and why it matters. Tier 0 — read only.
argument-hint: [base-branch or commit]
allowed-tools: Read, Bash, Grep, Glob
---

Tier 0 — read only. No writes, no branch, no state.

Base: **$ARGUMENTS** (default: `main` if no argument given)

Run `git diff $ARGUMENTS` (or `git diff HEAD` if on the base branch).
Summarise the diff in this format:

- **Files changed** — count and a flat list
- **What changed** — one bullet per file or logical group, one line each:
  `path/to/file — what was added/removed/modified`
- **Risk flags** — anything touching shared interfaces, auth, migrations,
  config, or secrets; write "none" if clean
- **Tests** — new tests added? existing tests changed? deleted? one line.

No prose. No restatement of code. Flag only meaningful changes.
Skip generated files (lock files, build output) unless they contain
something unexpected.
