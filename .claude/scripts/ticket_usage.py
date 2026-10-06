# Actual API token usage for one ticket, across every session that touched it.
#
#   python .claude/scripts/ticket_usage.py EPT-25
#
# Sums the `usage` block the API returned on each assistant message, which is
# what you are billed on, not the size of the conversation.
#
# Two details this gets right that a naive sum does not:
#   1. One API response is stored as several transcript entries (one per content
#      block), each repeating the same usage. Entries are deduped by message id,
#      or the total comes out 2-4x too high.
#   2. /clear starts a new session file, so a ticket spans several. Any session
#      whose transcript mentions the ticket key is included.
#
# Transcript format is internal to Claude Code and may change between versions.
# Cross-check one session against /usage before trusting the total.
import json, pathlib, sys, collections, datetime

KEY = sys.argv[1]
root = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path.home() / ".claude" / "projects"

# Optional: fill in $ per million tokens from the official pricing page to get
# a cost estimate. Left empty on purpose, so nothing here is a guess.
PRICES = {
    # "claude-sonnet-5": {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0},
}

FIELDS = [("input_tokens", "input"), ("cache_creation_input_tokens", "cache_write"),
          ("cache_read_input_tokens", "cache_read"), ("output_tokens", "output")]

sessions = []
for f in root.rglob("*.jsonl"):
    try:
        raw = f.read_text(encoding="utf-8")
    except Exception:
        continue
    if KEY in raw:
        sessions.append((f, raw))

if not sessions:
    sys.exit(f"No session transcripts mention {KEY} under {root}")

seen = set()
total = collections.Counter()
by_model = collections.defaultdict(collections.Counter)
by_session = []
first = last = None

for f, raw in sessions:
    s_tot, turns = collections.Counter(), 0
    for line in raw.splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        msg = e.get("message") or {}
        u = msg.get("usage")
        if msg.get("role") != "assistant" or not u:
            continue
        mid = msg.get("id") or e.get("requestId") or e.get("uuid")
        if mid in seen:
            continue
        seen.add(mid)
        turns += 1
        model = msg.get("model", "?")
        for src, dst in FIELDS:
            v = u.get(src) or 0
            s_tot[dst] += v; total[dst] += v; by_model[model][dst] += v
        ts = e.get("timestamp")
        if ts:
            first = min(first, ts) if first else ts
            last = max(last, ts) if last else ts
    by_session.append((f.name[:13], turns, s_tot))

def fmt(c):
    return f"{c['input']:>10,} {c['cache_write']:>11,} {c['cache_read']:>12,} {c['output']:>9,}"

print(f"\n{KEY} — {len(sessions)} session(s), {len(seen)} API calls")
if first and last:
    d = (datetime.datetime.fromisoformat(last.replace('Z', '+00:00'))
         - datetime.datetime.fromisoformat(first.replace('Z', '+00:00')))
    print(f"wall time first→last call: {d}")
print(f"\n{'session':15}{'calls':>6} {'fresh in':>10} {'cache write':>11} {'cache read':>12} {'output':>9}")
for name, turns, c in by_session:
    print(f"{name:15}{turns:>6} {fmt(c)}")
print(f"{'TOTAL':15}{len(seen):>6} {fmt(total)}")

billed = sum(total.values())
if billed:
    print(f"\nbilled tokens, all types: {billed:,}")
    print(f"  cache reads are {total['cache_read']/billed:.0%} of that — re-sent context, "
          f"billed at a fraction of fresh input")
    print(f"  output (the work itself): {total['output']:,}")

cost = 0.0
for model, c in by_model.items():
    p = PRICES.get(model)
    if p:
        cost += sum(c[k] * p[k] for k in p) / 1_000_000
if cost:
    print(f"\nestimated cost: ${cost:,.2f}")
else:
    print("\nfor a dollar figure: fill PRICES from the official pricing page, "
          "or add up the /usage cost for each session.")