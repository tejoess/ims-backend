#!/bin/bash
# PreToolUse guard on the Bash tool. Blocks operations the current ticket's
# scope contract explicitly forbids (forbidden_operations: in
# .claude/current-scope.yaml) — e.g. a LOW-risk ticket should never run a
# dependency install or a database migration, even if no path pattern
# happens to catch it. Fails open if no scope file exists yet.

set -euo pipefail

INPUT="$(cat)"
CMD="$(echo "$INPUT" | python3 -c "import json,sys
try:
    print(json.load(sys.stdin).get('tool_input',{}).get('command',''))
except Exception:
    print('')")"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SCOPE_FILE="$REPO_ROOT/.claude/current-scope.yaml"
[ ! -f "$SCOPE_FILE" ] && exit 0

FORBIDDEN_OPS="$(awk '/forbidden_operations:/{flag=1;next}/^[a-z_]+:/{flag=0}flag' "$SCOPE_FILE" | sed 's/^[[:space:]]*-[[:space:]]*//')"
[ -z "$FORBIDDEN_OPS" ] && exit 0

while IFS= read -r op; do
  [ -z "$op" ] && continue
  case "$op" in
    dependency_install) oppat='npm install|pip install|yarn add|bun add|poetry add' ;;
    migration)          oppat='migrate|alembic|db:push|db push' ;;
    deploy)              oppat='deploy|terraform apply|sam deploy|serverless deploy' ;;
    *)                   oppat="$op" ;;
  esac
  if echo "$CMD" | grep -Eiq "$oppat"; then
    if [ "${ALLOW_SENSITIVE:-0}" != "1" ]; then
      echo "Blocked: '$op' is a forbidden operation for this ticket (see $SCOPE_FILE)." >&2
      echo "Command was: $CMD" >&2
      exit 2
    fi
  fi
done <<< "$FORBIDDEN_OPS"

exit 0
