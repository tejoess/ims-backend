---
description: Reset the current ticket to its checkpoint and clear the scope contract.
allowed-tools: Read, Bash
---

Destructive. Confirm with the human before running anything.

1. Show what will be lost: `git log --oneline <checkpoint>..HEAD` and
   `git status`.
2. On confirmation: `git reset --hard <checkpoint>` from `state.json`, then
   delete the branch if the human wants it gone.
3. Archive `.agentic/tickets/<KEY>/` — keep plan, test-plan and red.log, they
   are worth reading before a retry.
4. Delete `.claude/current-scope.yaml`.
5. Set phase `ABANDONED` and note why in `DECISIONS.md`. A ticket that failed
   for a structural reason is worth remembering.
