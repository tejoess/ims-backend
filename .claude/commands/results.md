---
description: Publish the test-result evidence for a ticket as a visual HTML artifact. Tier 0 — read only.
argument-hint: <JIRA-KEY>
allowed-tools: Read, Bash, Glob, Artifact
---

Tier 0 — read only. No writes, no branch, no state.

Ticket: **$ARGUMENTS**

Steps:

1. Locate `.agentic/tickets/$ARGUMENTS/evidence.html`.
   - If it exists, read it and publish it as an Artifact (use the Artifact
     tool with `file_path` pointing to that file). Title: "$ARGUMENTS — Test Results".
   - If it does not exist but `evidence.md` does, tell the user the HTML
     report has not been generated yet and they should re-run
     `.claude/scripts/collect-evidence.sh $ARGUMENTS` to produce it, then
     run `/results $ARGUMENTS` again.
   - If neither exists, say "No evidence found for $ARGUMENTS — tester has
     not run yet."

2. After publishing, print one line: the Artifact URL and the overall result
   (PASS if no FAIL rows, FAIL otherwise — read from the HTML content).
   Nothing else.
