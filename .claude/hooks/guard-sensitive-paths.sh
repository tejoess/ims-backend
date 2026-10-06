#!/bin/bash
# PreToolUse guard on the Bash tool. Blocks commands that match a pattern in
# .claude/sensitive-paths.txt unless a human has set ALLOW_SENSITIVE=1 for
# that shell session. This is the GLOBAL denylist — always active,
# independent of any ticket's declared scope. See guard-scope-edit.sh for
# the per-ticket allowlist that layers on top of this.

set -euo pipefail

INPUT="$(cat)"
CMD="$(echo "$INPUT" | python3 -c "import json,sys
try:
    print(json.load(sys.stdin).get('tool_input',{}).get('command',''))
except Exception:
    print('')")"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PATTERN_FILE="$REPO_ROOT/.claude/sensitive-paths.txt"

if [ ! -f "$PATTERN_FILE" ]; then
  echo "Note: $PATTERN_FILE not found — global guard is inactive." >&2
  exit 0
fi

FILTERED_PATTERNS="$(grep -v '^[[:space:]]*#' "$PATTERN_FILE" | grep -v '^[[:space:]]*$' || true)"

if [ -n "$FILTERED_PATTERNS" ] && echo "$CMD" | grep -Eiqf <(echo "$FILTERED_PATTERNS"); then
  if [ "${ALLOW_SENSITIVE:-0}" != "1" ]; then
    echo "Blocked: command touches a sensitive path: $CMD" >&2
    echo "Matched a pattern in .claude/sensitive-paths.txt." >&2
    echo "Re-run with ALLOW_SENSITIVE=1 only after explicit human review." >&2
    exit 2
  fi
fi

exit 0
