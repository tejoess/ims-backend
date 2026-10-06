---
description: Open the draft PR, update Jira, record the decision, clear the scope contract.
allowed-tools: Read, Bash, Grep, Glob
---

Precondition: phase is `APPROVED`. If Gate 2 has not been passed, stop.

1. Push the branch.
2. Open the PR **as a draft**. You never merge, and you never mark it ready for
   review on your own — a human does both.
3. PR description: what changed, why, the Jira key, a link to
   `.agentic/tickets/<KEY>/evidence.md`, and any assumptions still unconfirmed.
4. Transition the Jira ticket and post the following comment on it (the
   subtask if you worked on a subtask, the ticket itself otherwise). Keep it
   short and factual — this is what the next agent reads in step 1b:

   ```
   **<TICKET-KEY> — <one line of what was built>**

   Decisions made
   - <field name / error shape / default / approach chosen> — why

   Changed
   - <files or components, one line each>

   Tests
   - <what was added, and the pass result>

   PR: <link>

   Notes for related tickets
   - <anything a sibling ticket needs to know — e.g. "the endpoint returns
     cancelled_at, nullable", "status filter values are active|cancelled">
     Write "none" if there is nothing.
   ```

   Put this in the comment body. Attach `evidence.md` and `diff.patch` as
   files too if useful for humans, but the comment body is what carries the
   information — attachments cannot be read back by the Atlassian connector.

5. Append to `DECISIONS.md`: what was decided, against which acceptance criteria,
   and the ticket key as the source.
6. Archive `.claude/current-scope.yaml` to `.agentic/tickets/<KEY>/` so the
   guards fall back to "no ticket in flight".
7. Set phase `PR`. Tell the human the functionality is complete and awaiting
   their merge.
