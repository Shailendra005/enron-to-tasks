import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NETWORK = re.compile(r"\b(curl|wget|pip3?\s+install|apt(-get)?\s+install|git\s+clone|nc|ssh)\b|https?://", re.IGNORECASE)


def tool_calls(log):
    for line in log.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            yield ("init", event.get("tools", []))
        message = event.get("message") or {}
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield ("tool", block)


def main():
    rows = []
    for root in [Path(p).expanduser() for p in sys.argv[1:]]:
        for log in sorted(root.glob("*/agent/claude-code.txt")):
            tools = Counter()
            network = []
            web_tools_offered = None
            for kind, item in tool_calls(log):
                if kind == "init":
                    web_tools_offered = any(t in item for t in ("WebSearch", "WebFetch"))
                    continue
                tools[item.get("name", "?")] += 1
                cmd = json.dumps(item.get("input", {}))
                if item.get("name") == "Bash" and NETWORK.search(cmd):
                    network.append(cmd[:160])
            rows.append((log.parent.parent.name, web_tools_offered, sum(tools.values()), dict(tools), network))
    lines = ["| Trial | Web tools offered | Tool calls | Network-like Bash commands |", "|---|---|---|---|"]
    for name, offered, n, tools, network in rows:
        lines.append(f"| {name} | {'yes' if offered else 'no'} | {n} | {len(network)} |")
    total_net = sum(len(r[4]) for r in rows)
    offered = sum(1 for r in rows if r[1])
    lines.append("")
    lines.append(f"{len(rows)} trials; web tools offered in {offered}; network-like Bash commands in total: {total_net}.")
    out = REPO / "results" / "transcripts.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-1:]))
    for r in rows:
        for cmd in r[4]:
            print("  network-like:", r[0], cmd)


if __name__ == "__main__":
    main()
