#!/usr/bin/env python3
"""Extract what each plugin can touch — MCP servers, declared tools, hooks, shell commands, endpoints, executables —
into plugins/<name>/.permissions.json sidecars. --markdown prints a human report instead (used for the PR comment)."""
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from risk_lint import NETWORK_ALLOWLIST, URL_RE  # single source of truth for the allowlist

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
FENCE_RE = re.compile(r"```(?:bash|sh|zsh|shell)\n(.*?)```", re.DOTALL)
INLINE_EXEC_RE = re.compile(r"^\s*!\s*`(.+?)`", re.M)
# inline `code` spans that start with a real binary — prose like "run `git log ...`" is still an instruction to execute
KNOWN_BINS = r"git|gh|curl|wget|python3?|node|npx|npm|bash|sh|zsh|jq|make|docker|kubectl|brew|pip3?|go|cargo|aws|gcloud|claude"
INLINE_CMD_RE = re.compile(rf"`((?:{KNOWN_BINS})\s+[^`]+)`")
TEXT_EXT = {".md", ".txt", ".json", ".sh", ".py", ".js", ".ts", ".yaml", ".yml", ".toml"}
SCRIPT_EXT = {".sh", ".py", ".js", ".ts", ".rb", ".pl"}


def frontmatter_tools(path: Path) -> list[str]:
    m = FRONTMATTER_RE.match(path.read_text(errors="replace"))
    if not m:
        return []
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        if k.strip() in ("allowed-tools", "tools") and v.strip():
            return [t.strip() for t in v.split(",") if t.strip()]
    return []


def walk_commands(node, out: list[str]) -> None:
    """Collect every 'command' string anywhere in a hooks/MCP JSON structure."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "command" and isinstance(v, str):
                out.append(v)
            else:
                walk_commands(v, out)
    elif isinstance(node, list):
        for item in node:
            walk_commands(item, out)


def manifest_for(pdir: Path) -> dict:
    name = pdir.name
    pj = {}
    if (pdir / ".claude-plugin" / "plugin.json").is_file():
        pj = json.loads((pdir / ".claude-plugin" / "plugin.json").read_text())
    tier = None
    mp = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    for e in mp.get("plugins", []):
        if e.get("name") == name:
            tier = next((t for t in e.get("tags", []) if re.match(r"^tier-[123]$", t)), None)

    mcp_servers = []
    if (pdir / ".mcp.json").is_file():
        try:
            cfg = json.loads((pdir / ".mcp.json").read_text())
            for sname, server in cfg.get("mcpServers", cfg).items():
                if not isinstance(server, dict):
                    continue
                mcp_servers.append({
                    "name": sname,
                    "mode": "local-process" if server.get("command") else "remote",
                    "target": " ".join([server.get("command", "")] + server.get("args", [])).strip() or server.get("url", ""),
                })
        except json.JSONDecodeError:
            mcp_servers.append({"name": "(unparseable .mcp.json)", "mode": "unknown", "target": ""})

    hook_commands: list[str] = []
    if (pdir / "hooks" / "hooks.json").is_file():
        try:
            walk_commands(json.loads((pdir / "hooks" / "hooks.json").read_text()), hook_commands)
        except json.JSONDecodeError:
            hook_commands.append("(unparseable hooks.json)")

    declared_tools: dict[str, list[str]] = {}
    for md in sorted(list(pdir.rglob("commands/**/*.md")) + list(pdir.rglob("agents/**/*.md"))
                     + list(pdir.rglob("skills/*/SKILL.md"))):
        tools = frontmatter_tools(md)
        if tools:
            declared_tools[str(md.relative_to(pdir))] = tools

    shell_commands: list[str] = []
    endpoints: dict[str, bool] = {}
    for f in sorted(pdir.rglob("*")):
        if not (f.is_file() and f.suffix in TEXT_EXT):
            continue
        text = f.read_text(errors="replace")
        if f.suffix == ".md":
            for block in FENCE_RE.findall(text):
                for line in block.splitlines():
                    line = line.strip().lstrip("$ ").strip()
                    if line and not line.startswith("#"):
                        shell_commands.append(line)
            shell_commands.extend(m.strip() for m in INLINE_EXEC_RE.findall(text))
            shell_commands.extend(m.strip() for m in INLINE_CMD_RE.findall(text))
        for host in URL_RE.findall(text):
            endpoints[host] = any(host == d or host.endswith("." + d) for d in NETWORK_ALLOWLIST)

    executables = sorted(str(f.relative_to(pdir)) for f in pdir.rglob("*")
                         if f.is_file() and (f.suffix in SCRIPT_EXT or "bin/" in str(f.relative_to(pdir))))

    return {
        "plugin": name,
        "version": pj.get("version", "?"),
        "declared_tier": tier,
        "mcp_servers": mcp_servers,
        "hook_commands": sorted(set(hook_commands)),
        "declared_tools": declared_tools,
        "shell_commands": sorted(set(shell_commands)),
        "network_endpoints": [{"host": h, "allowlisted": ok} for h, ok in sorted(endpoints.items())],
        "executables": executables,
        "generated": date.today().isoformat(),
    }


def to_markdown(m: dict) -> str:
    lines = [f"### `{m['plugin']}` v{m['version']} — {m['declared_tier'] or 'untiered'}", ""]

    def section(title: str, items: list[str]) -> None:
        lines.append(f"**{title}:** " + ("none" if not items else ""))
        lines.extend(f"- `{i}`" for i in items)
        lines.append("")

    section("MCP servers", [f"{s['name']} ({s['mode']}) → {s['target']}" for s in m["mcp_servers"]])
    section("Hook commands", m["hook_commands"])
    section("Declared tools", [f"{f}: {', '.join(t)}" for f, t in m["declared_tools"].items()])
    section("Shell commands referenced", m["shell_commands"])
    lines.append("**Network endpoints:** " + ("none" if not m["network_endpoints"] else ""))
    for e in m["network_endpoints"]:
        lines.append(f"- `{e['host']}` {'(allowlisted)' if e['allowlisted'] else '⚠️ **NOT on allowlist**'}")
    lines.append("")
    section("Executables / scripts", m["executables"])
    return "\n".join(lines)


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--markdown"]
    markdown = "--markdown" in sys.argv
    targets = [REPO / a for a in args] or sorted(p for p in (REPO / "plugins").iterdir() if p.is_dir())
    reports = []
    for pdir in targets:
        if not pdir.is_dir():
            continue
        m = manifest_for(pdir)
        reports.append(m)
        if not markdown:
            (pdir / ".permissions.json").write_text(json.dumps(m, indent=2) + "\n")
            print(f"permissions: {m['plugin']} → {len(m['mcp_servers'])} MCP, {len(m['hook_commands'])} hooks, "
                  f"{len(m['shell_commands'])} shell, {len(m['network_endpoints'])} endpoints")
    if markdown:
        print("## 🔍 Permission manifest\n")
        print("What the changed plugin(s) can touch, extracted from their files. Verify this matches the PR's claims.\n")
        print("\n---\n".join(to_markdown(m) for m in reports))
    return 0


if __name__ == "__main__":
    sys.exit(main())
