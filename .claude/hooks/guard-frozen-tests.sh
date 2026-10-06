#!/bin/bash
# PreToolUse guard on Edit|Write|MultiEdit. Blocks edits to the test files this
# ticket froze at its RED step — the most likely way a bounded fix loop
# "succeeds" wrongly is by editing the assertion instead of the code under it.
#
# Reads the UNION of frozen_tests in current-scope.yaml and the frozen.lock
# snapshot written at RED time. The lock matters: current-scope.yaml is writable
# by the pipeline, so an agent could otherwise unfreeze a test by deleting its
# line. frozen.lock is listed in sensitive-paths.txt and cannot be edited
# without a human setting ALLOW_SENSITIVE=1.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_paths.sh
. "$SCRIPT_DIR/_paths.sh"

INPUT="$(cat)"
FILE_PATH="$(echo "$INPUT" | python3 -c "import json,sys
try:
    print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))
except Exception:
    print('')")"
[ -z "$FILE_PATH" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SCOPE_FILE="$REPO_ROOT/.claude/current-scope.yaml"
[ ! -f "$SCOPE_FILE" ] && exit 0

REL_PATH="$(rel_path "$FILE_PATH" "$REPO_ROOT")"

FROZEN="$(awk '/^frozen_tests:/{flag=1;next}/^[a-z_]+:/{flag=0}flag' "$SCOPE_FILE" 2>/dev/null | sed 's/^[[:space:]]*-[[:space:]]*//')"
LOCK="$(cat "$REPO_ROOT"/.agentic/tickets/*/frozen.lock 2>/dev/null || true)"
ALL_FROZEN="$(printf '%s\n%s\n' "$FROZEN" "$LOCK" | sed '/^[[:space:]]*$/d' | sort -u)"
[ -z "$ALL_FROZEN" ] && exit 0

while IFS= read -r pattern; do
  [ -z "$pattern" ] && continue
  pattern="$(norm_path "$pattern")"
  regex="^$(echo "$pattern" | sed 's/\*\*/.*/g; s/\*/[^\/]*/g')$"
  if echo "$REL_PATH" | grep -Eq "$regex"; then
    echo "Blocked: $REL_PATH is a frozen test for this ticket." >&2
    echo "" >&2
    echo "These tests were written from the approved test plan and confirmed failing" >&2
    echo "at the RED step. Changing one to make the suite pass would invalidate the" >&2
    echo "evidence the review gate reads." >&2
    echo "" >&2
    echo "If the test is genuinely wrong, that is a finding, not a fix: stop, report" >&2
    echo "which assertion is wrong and why, and let a human decide." >&2
    exit 2
  fi
done <<< "$ALL_FROZEN"
exit 0
