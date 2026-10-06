#!/bin/bash
# PreToolUse guard on the Bash tool. Closes the gap that guard-scope-edit.sh
# cannot see: the scope allowlist only guards Edit|Write|MultiEdit, so an agent
# with Bash can write anywhere with `cat > file`, `sed -i`, `tee`, `cp`, or `mv`
# and the contract never fires. This hook extracts write targets from the
# command and checks them against the same allowlist.
#
# Deliberately conservative: it only inspects targets that resolve inside the
# repo. Writes to /tmp, scratch dirs, and anything outside the working tree pass
# through, because build tools and test runners legitimately do that constantly.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_paths.sh
. "$SCRIPT_DIR/_paths.sh"

INPUT="$(cat)"
CMD="$(echo "$INPUT" | python3 -c "import json,sys
try:
    print(json.load(sys.stdin).get('tool_input',{}).get('command',''))
except Exception:
    print('')")"
[ -z "$CMD" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SCOPE_FILE="$REPO_ROOT/.claude/current-scope.yaml"
[ ! -f "$SCOPE_FILE" ] && exit 0

TARGETS="$(python3 - "$CMD" <<'PY'
import re, sys, shlex
cmd = sys.argv[1]
t = set()
# redirections: > file, >> file, 1> file
for m in re.finditer(r'(?<![0-9<>])>>?\s*([^\s;|&()<>]+)', cmd):
    t.add(m.group(1))
# tee [-a] file...
for m in re.finditer(r'\btee\s+(?:-a\s+)?([^\s;|&()<>]+)', cmd):
    t.add(m.group(1))
# sed -i ... file (last token of the segment)
for m in re.finditer(r'\bsed\s+[^;|&]*-i[^;|&]*', cmd):
    try:
        parts = shlex.split(m.group(0))
        if parts and not parts[-1].startswith('-'):
            t.add(parts[-1])
    except ValueError:
        pass
# cp/mv/install destination, rm targets, dd of=
for m in re.finditer(r'\b(?:cp|mv|install)\s+([^;|&]+)', cmd):
    try:
        parts = [p for p in shlex.split(m.group(1)) if not p.startswith('-')]
        if len(parts) >= 2:
            t.add(parts[-1])
    except ValueError:
        pass
for m in re.finditer(r'\brm\s+([^;|&]+)', cmd):
    try:
        t.update(p for p in shlex.split(m.group(1)) if not p.startswith('-'))
    except ValueError:
        pass
for m in re.finditer(r'\bdd\s+[^;|&]*\bof=([^\s;|&]+)', cmd):
    t.add(m.group(1))
for x in sorted(t):
    x = x.strip('\'"')
    if x and x not in ('/dev/null', '/dev/stdout', '/dev/stderr'):
        print(x)
PY
)"
[ -z "$TARGETS" ] && exit 0

ALLOWED="$(awk '/^allowed_paths:/{flag=1;next}/^[a-z_]+:/{flag=0}flag' "$SCOPE_FILE" | sed 's/^[[:space:]]*-[[:space:]]*//')"
[ -z "$ALLOWED" ] && exit 0

while IFS= read -r target; do
  [ -z "$target" ] && continue
  t="$(norm_path "$target")"
  case "$t" in
    /tmp/*|/var/tmp/*|/dev/*) continue ;;
    /*|[a-z]:/*)
      rr="$(norm_path "$REPO_ROOT")"; rr="${rr%/}"
      case "$t" in "$rr"/*) t="${t#"$rr"/}" ;; *) continue ;; esac ;;
  esac
  t="${t#./}"
  echo "$t" | grep -Eq "$PIPELINE_PATHS" && continue

  MATCH=0
  while IFS= read -r pattern; do
    [ -z "$pattern" ] && continue
    pattern="$(norm_path "$pattern")"
    regex="^$(echo "$pattern" | sed 's/\*\*/.*/g; s/\*/[^\/]*/g')$"
    if echo "$t" | grep -Eq "$regex"; then MATCH=1; break; fi
  done <<< "$ALLOWED"

  if [ "$MATCH" -eq 0 ] && [ "${ALLOW_SENSITIVE:-0}" != "1" ]; then
    echo "Blocked: this command writes to '$t', which is outside this ticket's declared scope." >&2
    echo "Command: $CMD" >&2
    echo "" >&2
    echo "Writing through Bash does not bypass the scope contract. If this file" >&2
    echo "genuinely needs to change, stop and ask a human to update $SCOPE_FILE." >&2
    exit 2
  fi
done <<< "$TARGETS"
exit 0
