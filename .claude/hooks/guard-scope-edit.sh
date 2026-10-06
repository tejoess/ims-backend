#!/bin/bash
# PreToolUse guard on Edit|Write|MultiEdit. Enforces the current ticket's
# declared scope contract (.claude/current-scope.yaml) — the allowlist half of
# the scope guard. Fails OPEN if no scope file exists (nothing in flight).

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

# Outside the repo entirely (temp files, scratch dirs) — not this hook's business.
case "$REL_PATH" in /*|[A-Za-z]:/*) exit 0 ;; esac

# Pipeline bookkeeping is always writable.
echo "$REL_PATH" | grep -Eq "$PIPELINE_PATHS" && exit 0

ALLOWED="$(awk '/^allowed_paths:/{flag=1;next}/^[a-z_]+:/{flag=0}flag' "$SCOPE_FILE" | sed 's/^[[:space:]]*-[[:space:]]*//')"
[ -z "$ALLOWED" ] && exit 0

MATCH=0
while IFS= read -r pattern; do
  [ -z "$pattern" ] && continue
  pattern="$(norm_path "$pattern")"
  regex="^$(echo "$pattern" | sed 's/\*\*/.*/g; s/\*/[^\/]*/g')$"
  if echo "$REL_PATH" | grep -Eq "$regex"; then MATCH=1; break; fi
done <<< "$ALLOWED"

if [ "$MATCH" -eq 0 ] && [ "${ALLOW_SENSITIVE:-0}" != "1" ]; then
  echo "Warning: $REL_PATH is outside this ticket's declared scope (allowed paths in $SCOPE_FILE)." >&2
  echo "Proceeding — update the scope contract if this path should be permanent." >&2
fi
exit 0
