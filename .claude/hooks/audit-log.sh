#!/bin/bash
# Appends one line to audit-log.md every time this hook fires.
# Called from .claude/settings.json on PostToolUse (file edits) and Stop
# (session end). Never edited by hand — this is the deterministic paper
# trail, separate from whatever an agent chooses to write in DECISIONS.md.

set -euo pipefail

EVENT_LABEL="${1:-event}"
INPUT="$(cat)"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
LOG_FILE="$REPO_ROOT/audit-log.md"

jget() { echo "$INPUT" | python3 -c "import json,sys
try:
    d = json.load(sys.stdin)
    for k in sys.argv[1].split('.'):
        d = d.get(k, {}) if isinstance(d, dict) else {}
    print(d if isinstance(d, (str, bool)) else '')
except Exception:
    print('')" "$1"; }

if [ "$EVENT_LABEL" = "session-end" ]; then
  STOP_ACTIVE="$(jget stop_hook_active)"
  if [ "$STOP_ACTIVE" = "True" ]; then
    exit 0
  fi
  echo "- [$TIMESTAMP] session ended" >> "$LOG_FILE"
  exit 0
fi

TOOL_NAME="$(jget tool_name)"
[ -z "$TOOL_NAME" ] && TOOL_NAME="n/a"
FILE_PATH="$(jget tool_input.file_path)"

DETAIL="tool=$TOOL_NAME"
if [ -n "$FILE_PATH" ]; then
  DETAIL="$DETAIL file=$FILE_PATH"
fi

echo "- [$TIMESTAMP] $DETAIL" >> "$LOG_FILE"
exit 0
