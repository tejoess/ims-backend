---
name: evidence-bundle
description: Assemble the review package the human gate reads — generated from raw runner output, never narrated. Used by the tester agent at the end of phase 5.
---

The reviewer is checking the agent's work. If the agent also writes the report
on that work, the gate is reviewing an opinion. So the bundle is generated.

Run `.claude/scripts/collect-evidence.sh <TICKET-KEY>`. It writes:

```
.agentic/tickets/<KEY>/
├── evidence.md     verification table + AC→TC coverage + change stats
├── diff.patch      full diff from the checkpoint
├── red.log         the same tests failing, before implementation
└── logs/           raw stdout/stderr per layer
```

Your job around the script:

1. Make sure the layer commands are set (`UNIT_CMD`, `INTEGRATION_CMD`, etc.,
   from CLAUDE.md's "How to run things"). A layer with no command is reported as
   SKIPPED, which is honest — but a layer the scope contract marked `required`
   showing SKIPPED means verification did not actually happen. Fix that before
   handing off.
2. Read `evidence.md` before passing it on. Any `MISSING` row in the coverage
   table means an acceptance criterion has no test. That is a blocker, not a
   footnote.
3. Add what the script cannot compute: what the UI flow actually exercised via
   Playwright, and anything about the change a reviewer would otherwise have to
   discover from the diff.

Two things you must **not** do:

- Do not write pass/fail lines yourself. If a result is not in a log file, it is
  not a result.
- Do not assert an overall risk rating. The script reports risk *inputs* — files
  touched, migration present, tier. The `pr-reviewer` agent and the human draw
  the conclusion. "Risk: Low" written by the thing that made the change is noise.
