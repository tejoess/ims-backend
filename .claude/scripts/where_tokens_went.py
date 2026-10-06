# Where the tokens went in the latest Claude Code session.
# Counts three things: what tools returned, what Claude wrote into tools
# (file contents, commands, Jira payloads), and Claude's own text.
# Transcript format is internal to Claude Code and may change between versions.
import json, pathlib, collections, sys

root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.home() / ".claude" / "projects"
f = max(root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime)
tok = lambda x: len(x if isinstance(x, str) else json.dumps(x)) // 4   # ~4 chars/token

calls, results = {}, []
returned, written = collections.Counter(), collections.Counter()
text = 0
for line in f.read_text(encoding="utf-8").splitlines():
    try:
        msg = json.loads(line).get("message") or {}
    except Exception:
        continue
    content = msg.get("content")
    if not isinstance(content, list):
        continue
    for b in content:
        t = b.get("type")
        if t == "tool_use":
            name = b.get("name", "?")
            calls[b.get("id")] = (name, json.dumps(b.get("input", {}))[:80])
            written[name] += tok(b.get("input", {}))
        elif t == "tool_result":
            name, inp = calls.get(b.get("tool_use_id"), ("?", ""))
            n = tok(b.get("content"))
            returned[name] += n
            results.append((n, name, inp))
        elif t == "text" and msg.get("role") == "assistant":
            text += tok(b.get("text", ""))

R, W = sum(returned.values()), sum(written.values())
print(f"session: {f.name}\n")
print(f"  returned by tools   {R:>9,}")
print(f"  written by Claude   {W:>9,}   (file contents, commands, payloads)")
print(f"  Claude's own text   {text:>9,}")
print(f"  total               {R+W+text:>9,}\n")
print(f"  {'tool':40} {'returned':>9} {'written':>9}")
for name in sorted(set(returned) | set(written), key=lambda k: -(returned[k] + written[k])):
    print(f"  {name[:40]:40} {returned[name]:>9,} {written[name]:>9,}")
print("\nlargest single results:")
for n, name, inp in sorted(results, reverse=True)[:8]:
    print(f"  {n:>7,}  {name[:28]:28} {inp[:60]}")