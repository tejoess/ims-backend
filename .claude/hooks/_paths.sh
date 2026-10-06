# Sourced by the guard hooks. Normalises the two path representations that do
# not match on Windows:
#   git rev-parse --show-toplevel  ->  C:/Users/.../repo      (forward slashes)
#   tool_input.file_path           ->  C:\Users\...\file.py   (backslashes)
# A naive prefix-strip fails, REL_PATH stays absolute, and every allowlist glob
# misses — which fails CLOSED and blocks every edit in the repo.

norm_path () {
  local p="$1"
  p="${p//\\//}"                                   # backslashes -> forward
  # lowercase a leading drive letter so C:/ and c:/ compare equal
  if [[ "$p" =~ ^([A-Za-z]):(/.*)?$ ]] || [[ "$p" =~ ^([A-Za-z]):/ ]]; then
    local drive="${p:0:1}" rest="${p:1}"
    p="$(echo "$drive" | tr '[:upper:]' '[:lower:]')$rest"
  fi
  printf '%s' "$p"
}

rel_path () {           # rel_path <abs_file> <repo_root>
  local f r
  f="$(norm_path "$1")"
  r="$(norm_path "$2")"
  r="${r%/}"
  printf '%s' "${f#"$r"/}"
}

# The pipeline's own bookkeeping. Always writable regardless of the ticket's
# allowed_paths — the contract governs application code, not the machinery that
# records the contract. Without this, every ticket has to remember to allowlist
# its own state file, and forgetting deadlocks the run.
PIPELINE_PATHS='^(\.agentic/|\.claude/current-scope\.yaml$|DECISIONS\.md$|audit-log\.md$)'
