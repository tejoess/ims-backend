---
description: Rough plan and effort for a ticket, without entering the pipeline.
argument-hint: <JIRA-KEY>
allowed-tools: Read, Grep, Glob, Bash
---

Tier 0 — read only. This is NOT `/plan`. Do not write a scope contract, do not
create a ticket folder, do not create a branch, do not write state.json.

Pull ticket **$ARGUMENTS** via the `jira-ticket-intake` skill, then give:

1. A rough risk tier (`risk-classification` skill) and why.
2. The files and layers a change would likely touch.
3. Rough size: hours / a day / multi-day, and what drives it.
4. The open questions that would need answering before `/plan` could produce a
   real contract.

Stop there. If it looks ready to start, say so and let the human run `/plan`.
