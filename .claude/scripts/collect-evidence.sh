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

# ── HTML report ───────────────────────────────────────────────────────────────
badge () {
  local r="$1"
  case "$r" in
    PASS)        echo "<span class='badge pass'>PASS</span>" ;;
    FAIL)        echo "<span class='badge fail'>FAIL</span>" ;;
    SKIPPED*)    echo "<span class='badge skip'>SKIPPED</span>" ;;
    "NOT COVERED"|*MISSING*) echo "<span class='badge fail'>MISSING</span>" ;;
    "see logs")  echo "<span class='badge warn'>see logs</span>" ;;
    *)           echo "<span class='badge skip'>$r</span>" ;;
  esac
}

GENERATED="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RISK_TIER="$(grep -E '^risk:' "$ROOT/.claude/current-scope.yaml" 2>/dev/null | awk '{print $2}')"
FILES_CHANGED="$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')"
MIGRATION_TOUCHED="$([ -n "$MIGRATE_UP_CMD" ] && echo yes || echo no)"
DIFF_STAT="$(git diff --stat "$(python3 -c "
import json,pathlib
p=pathlib.Path('$DIR/state.json')
print(json.loads(p.read_text()).get('checkpoint_sha') or 'HEAD~1')
" 2>/dev/null)"...HEAD 2>/dev/null || git diff --stat HEAD 2>/dev/null)"

{
cat <<HTMLHEAD
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evidence — $KEY</title>
<style>
:root{--bg:#fff;--fg:#111;--border:#e5e7eb;--muted:#6b7280;--card:#f9fafb}
@media(prefers-color-scheme:dark){:root{--bg:#0f0f0f;--fg:#e5e7eb;--border:#27272a;--muted:#9ca3af;--card:#18181b}}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:var(--bg);color:var(--fg);max-width:860px;margin:2.5rem auto;padding:0 1.25rem;font-size:15px;line-height:1.6}
h1{font-size:1.4rem;font-weight:700;margin-bottom:.25rem}
h2{font-size:.72rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:2.25rem 0 .75rem}
.meta{font-size:.82rem;color:var(--muted);margin-bottom:2rem}
table{width:100%;border-collapse:collapse;margin-bottom:.5rem;font-size:.88rem}
th{text-align:left;padding:.45rem .75rem;border-bottom:2px solid var(--border);font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600}
td{padding:.5rem .75rem;border-bottom:1px solid var(--border);vertical-align:middle}
tr:last-child td{border-bottom:none}
.badge{display:inline-block;padding:2px 10px;border-radius:9999px;font-size:.75rem;font-weight:700;letter-spacing:.04em}
.pass{background:#16a34a;color:#fff}
.fail{background:#dc2626;color:#fff}
.skip{background:#6b7280;color:#fff}
.warn{background:#d97706;color:#fff}
pre{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:1rem;font-size:.78rem;overflow-x:auto;margin:.5rem 0}
ul.risk{list-style:none;padding:0;font-size:.88rem}
ul.risk li{padding:.3rem 0;border-bottom:1px solid var(--border);display:flex;gap:.5rem}
ul.risk li span.label{color:var(--muted);min-width:180px}
footer{margin-top:3rem;font-size:.75rem;color:var(--muted);border-top:1px solid var(--border);padding-top:1rem}
</style>
</head>
<body>
<h1>Evidence — $KEY</h1>
<p class="meta">Generated $GENERATED &nbsp;·&nbsp; Raw logs: <code>.agentic/tickets/$KEY/logs/</code> &nbsp;·&nbsp; RED baseline: <code>red.log</code></p>

<h2>Verification</h2>
<table>
<tr><th>Layer</th><th>Result</th></tr>
HTMLHEAD

  for i in "${!NAMES[@]}"; do
    echo "<tr><td>${NAMES[$i]}</td><td>$(badge "${RESULTS[$i]}")</td></tr>"
  done

cat <<HTMLCOV
</table>

<h2>Requirement Coverage</h2>
<table>
<tr><th>AC</th><th>TC</th><th>In test suite</th><th>Result</th></tr>
HTMLCOV

  if [ -f "$DIR/test-plan.md" ]; then
    grep -oE 'AC-[0-9]+[^A-Z]*TC-[0-9]+|TC-[0-9]+[^A-Z]*AC-[0-9]+' "$DIR/test-plan.md" 2>/dev/null \
    | grep -oE '(AC|TC)-[0-9]+' | paste - - 2>/dev/null | while read -r a b; do
        tc="$(echo -e "$a\n$b" | grep TC- | head -1)"
        ac="$(echo -e "$a\n$b" | grep AC- | head -1)"
        if grep -rq "$tc" --include='*test*' --include='*spec*' "$ROOT" 2>/dev/null; then
          if grep -qi "$tc.*\(pass\|ok\)" "$LOGS"/*.log 2>/dev/null; then
            echo "<tr><td>$ac</td><td>$tc</td><td>yes</td><td>$(badge PASS)</td></tr>"
          else
            echo "<tr><td>$ac</td><td>$tc</td><td>yes</td><td>$(badge "see logs")</td></tr>"
          fi
        else
          echo "<tr><td>$ac</td><td>$tc</td><td>$(badge MISSING)</td><td>$(badge "NOT COVERED")</td></tr>"
        fi
      done
  else
    echo "<tr><td colspan='4' style='color:var(--muted)'>no test-plan.md found</td></tr>"
  fi

cat <<HTMLCHANGES
</table>

<h2>Changes</h2>
<pre>$DIFF_STAT</pre>

<h2>Risk Inputs</h2>
<ul class="risk">
  <li><span class="label">Risk tier</span><strong>$RISK_TIER</strong></li>
  <li><span class="label">Files changed</span>$FILES_CHANGED</li>
  <li><span class="label">Migration touched</span>$MIGRATION_TOUCHED</li>
  <li><span class="label">Public interface changed</span>reviewer to confirm from diff.patch</li>
</ul>

<footer>No overall risk rating is asserted here. These are the inputs; the pr-reviewer agent and the human draw the conclusion.</footer>
</body>
</html>
HTMLCHANGES

} > "$DIR/evidence.html"

echo "Wrote $DIR/evidence.html"
printf '%s\n' "${RESULTS[@]}" | grep -q FAIL && exit 1
exit 0
