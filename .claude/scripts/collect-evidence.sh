#!/bin/bash
# Generates the evidence bundle from RAW RUNNER OUTPUT.
#
# The point: an agent that writes its own "AC-001 PASS" line can write it when
# the test did not pass. This script only ever transcribes what the runners
# actually printed, and the AC->TC coverage table is derived by grepping the
# test sources for their ids. If a TC id from test-plan.md never appears in a
# test file, it shows as MISSING — which is the failure mode where an agent
# quietly skips an acceptance criterion.
#
# Usage: .claude/scripts/collect-evidence.sh <TICKET-KEY>
# Reads:  .claude/current-scope.yaml, .agentic/tickets/<KEY>/test-plan.md
# Writes: .agentic/tickets/<KEY>/{evidence.md,diff.patch,logs/}

set -uo pipefail
KEY="${1:?usage: collect-evidence.sh <TICKET-KEY>}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DIR="$ROOT/.agentic/tickets/$KEY"
LOGS="$DIR/logs"
mkdir -p "$LOGS"

# Commands are read from CLAUDE.md's "How to run things" in a real repo; these
# are the fallbacks. Override by exporting before calling.
BUILD_CMD="${BUILD_CMD:-}"
LINT_CMD="${LINT_CMD:-}"
TYPE_CMD="${TYPE_CMD:-}"
UNIT_CMD="${UNIT_CMD:-}"
INTEGRATION_CMD="${INTEGRATION_CMD:-}"
MIGRATE_UP_CMD="${MIGRATE_UP_CMD:-}"
MIGRATE_DOWN_CMD="${MIGRATE_DOWN_CMD:-}"

declare -a NAMES=() RESULTS=()

run_layer () {
  local name="$1" cmd="$2" slug
  slug="$(echo "$name" | tr '[:upper:] ' '[:lower:]-')"
  if [ -z "$cmd" ]; then
    NAMES+=("$name"); RESULTS+=("SKIPPED (no command configured)"); return 0
  fi
  echo "== $name: $cmd" | tee "$LOGS/$slug.log"
  if bash -c "$cmd" >>"$LOGS/$slug.log" 2>&1; then
    NAMES+=("$name"); RESULTS+=("PASS")
  else
    NAMES+=("$name"); RESULTS+=("FAIL")
  fi
}

run_layer "Build"        "$BUILD_CMD"
run_layer "Lint"         "$LINT_CMD"
run_layer "Type check"   "$TYPE_CMD"
run_layer "Unit tests"   "$UNIT_CMD"
run_layer "Integration"  "$INTEGRATION_CMD"
run_layer "Migration up" "$MIGRATE_UP_CMD"
# Down-migration matters as much as up: an irreversible migration is a release
# risk the review gate should see, not discover in production.
run_layer "Migration down" "$MIGRATE_DOWN_CMD"

git diff "$(python3 -c "
import json,sys,pathlib
p=pathlib.Path('$DIR/state.json')
print(json.loads(p.read_text()).get('checkpoint_sha') or 'HEAD~1')
")"...HEAD > "$DIR/diff.patch" 2>/dev/null || git diff HEAD > "$DIR/diff.patch"

{
  echo "# Evidence — $KEY"
  echo
  echo "_Generated $(date -u +%Y-%m-%dT%H:%M:%SZ) by collect-evidence.sh from runner output._"
  echo "_Raw logs: \`.agentic/tickets/$KEY/logs/\` · RED baseline: \`red.log\`_"
  echo
  echo "## Verification"
  echo
  echo "| Layer | Result |"
  echo "|---|---|"
  for i in "${!NAMES[@]}"; do echo "| ${NAMES[$i]} | ${RESULTS[$i]} |"; done
  echo
  echo "## Requirement coverage"
  echo
  echo "| AC | TC | In test suite | Result |"
  echo "|---|---|---|---|"
  if [ -f "$DIR/test-plan.md" ]; then
    grep -oE 'AC-[0-9]+[^A-Z]*TC-[0-9]+|TC-[0-9]+[^A-Z]*AC-[0-9]+' "$DIR/test-plan.md" 2>/dev/null \
    | grep -oE '(AC|TC)-[0-9]+' | paste - - 2>/dev/null | while read -r a b; do
        tc="$(echo -e "$a\n$b" | grep TC- | head -1)"
        ac="$(echo -e "$a\n$b" | grep AC- | head -1)"
        if grep -rq "$tc" --include='*test*' --include='*spec*' "$ROOT" 2>/dev/null; then
          if grep -qi "$tc.*\(pass\|ok\)" "$LOGS"/*.log 2>/dev/null; then r="PASS"; else r="see logs"; fi
          echo "| $ac | $tc | yes | $r |"
        else
          echo "| $ac | $tc | **MISSING** | NOT COVERED |"
        fi
      done
  else
    echo "| — | — | no test-plan.md found | — |"
  fi
  echo
  echo "## Changes"
  echo
  echo '```'
  git diff --stat "$(python3 -c "
import json,pathlib
p=pathlib.Path('$DIR/state.json')
print(json.loads(p.read_text()).get('checkpoint_sha') or 'HEAD~1')
")"...HEAD 2>/dev/null || git diff --stat HEAD
  echo '```'
  echo
  echo "## Risk inputs"
  echo
  echo "- Risk tier: $(grep -E '^risk:' "$ROOT/.claude/current-scope.yaml" 2>/dev/null | awk '{print $2}')"
  echo "- Files changed: $(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')"
  echo "- Migration touched: $([ -n "$MIGRATE_UP_CMD" ] && echo yes || echo no)"
  echo "- Public interface changed: reviewer to confirm from diff.patch"
  echo
  echo "_No overall risk rating is asserted here. These are the inputs; the"
  echo "pr-reviewer agent and the human draw the conclusion._"
} > "$DIR/evidence.md"

echo "Wrote $DIR/evidence.md"
printf '%s\n' "${RESULTS[@]}" | grep -q FAIL && exit 1
exit 0
