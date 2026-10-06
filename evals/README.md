# Evaluation memory

Project memory (`CLAUDE.md`) tells the agent what the system is. This
tells the team what the agent repeatedly gets right or wrong.

```
evals/
├── successful_cases/   # tickets that went well — reference examples
├── failures/            # tickets that failed, tagged per docs/failure-taxonomy.md
└── regressions/         # cases where a fix broke something else
```

Each case (one markdown or JSON file per ticket) should retain: the
ticket key, expected behavior, relevant inputs, verification results,
outcome, failure category (if applicable), rough cost/time, and any
notes worth remembering.

Do **not** automatically promote a successful case into a skill — that's
what `skill-proposal` is for, and it always produces a `-draft` for human
review, never a live skill on its own.

This is deliberately lightweight for now — structure and discipline
first, automation later. Don't build tooling around this folder until
you have enough real cases to know what tooling would actually help.
