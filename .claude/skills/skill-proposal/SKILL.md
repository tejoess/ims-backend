---
name: skill-proposal
description: When the current ticket's fix resembles a pattern from an earlier ticket, draft a new skill capturing that reusable procedure — for human review. This is how the kit is meant to grow over time.
---

Use this when, during planning or implementation, you notice the current
work rhymes with something done on a previous ticket in this repo (check
`audit-log.md`, `DECISIONS.md`, and recent commit history for signal).

1. Describe the repeated pattern in one or two sentences — what keeps
   coming up, not just "this ticket is similar."
2. Draft a new skill folder at `.claude/skills/<short-name>-draft/SKILL.md`
   — **always keep the `-draft` suffix**. Never write directly into a
   non-draft skill folder; that's a decision for a human to make.
3. Write the draft skill the same way the other skills in this kit are
   written: a `name`/`description` frontmatter block, then a short
   numbered procedure — not a transcript of what you did this one time.
4. Note in your summary to the human: "proposed a new skill draft based on
   a pattern across ticket X and ticket Y — review at
   .claude/skills/<name>-draft/SKILL.md before promoting it."
5. Do not rename, activate, or reference the draft skill as if it were
   approved. It only becomes real once a human renames the folder
   (dropping `-draft`) and commits it.
