---
name: smoke-test-dev
description: After a merge and deploy to dev, run a short set of known-good checks to confirm the service actually came up correctly before telling a human it's done.
---

1. Confirm the deploy finished (check CI status / deploy logs — don't just
   assume the merge triggered a successful deploy).
2. Hit 2-3 known-good requests/flows against dev — pick ones that would
   catch a broken cold start or a misconfigured route, not just a
   health-check endpoint that always returns 200.
3. Compare responses against expected shape/content, not just status code.
4. Record pass/fail and a one-line reason in `audit-log.md`.
5. Only report the ticket as "live" to the human if this passes. A merged
   PR with a failed smoke check is not a completed ticket.

TODO: replace the placeholder checks above with real endpoints/flows once
the target repo is wired in.
