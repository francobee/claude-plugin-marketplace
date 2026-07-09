#!/usr/bin/env python3
"""Structural smoke test: frontmatter parses, referenced files exist, JSON configs well-formed, managed-settings keys pinned. Exits with registry code GATE-003 on failure."""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
findings: list[str] = []


def err(msg: str) -> None:
    findings.append(msg)
    print(f"  ✗ {msg}")


def frontmatter(path: Path) -> dict | None:
    """Parse simple `key: value` YAML frontmatter without a yaml dependency."""
    text = path.read_text(errors="replace")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if line and not line.startswith((" ", "\t", "#")) and ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def check_plugin(pdir: Path) -> None:
    rel = pdir.relative_to(REPO)
    manifest = pdir / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        err(f"{rel}: missing .claude-plugin/plugin.json")
        return
    try:
        pj = json.loads(manifest.read_text())
    except json.JSONDecodeError as e:
        err(f"{rel}: plugin.json is not valid JSON ({e})")
        return
    if pj.get("name") != pdir.name:
        err(f"{rel}: plugin.json name '{pj.get('name')}' != directory name '{pdir.name}'")

    changelog = pdir / "CHANGELOG.md"
    if not changelog.is_file():
        err(f"{rel}: missing CHANGELOG.md")
    elif pj.get("version") and f"[{pj['version']}]" not in changelog.read_text(errors="replace"):
        err(f"{rel}: CHANGELOG.md has no entry for current version {pj['version']}")

    for cmd in sorted((pdir / "commands").glob("*.md")) if (pdir / "commands").is_dir() else []:
        fm = frontmatter(cmd)
        if fm is None:
            err(f"{cmd.relative_to(REPO)}: missing/unparseable frontmatter")
        elif "description" not in fm:
            err(f"{cmd.relative_to(REPO)}: frontmatter lacks 'description'")
        if fm and "Bash" in fm.get("allowed-tools", ""):
            print(f"  ⚠ {cmd.relative_to(REPO)}: declares allowed-tools: Bash — requires explicit reviewer approval")

    for agent in sorted((pdir / "agents").glob("*.md")) if (pdir / "agents").is_dir() else []:
        fm = frontmatter(agent)
        if fm is None or "description" not in fm:
            err(f"{agent.relative_to(REPO)}: missing frontmatter or 'description'")
        if fm and "Bash" in fm.get("allowed-tools", ""):
            print(f"  ⚠ {agent.relative_to(REPO)}: declares allowed-tools: Bash — requires explicit reviewer approval")

    if (pdir / "skills").is_dir():
        for sdir in sorted(p for p in (pdir / "skills").iterdir() if p.is_dir()):
            skill = sdir / "SKILL.md"
            if not skill.is_file():
                err(f"{sdir.relative_to(REPO)}: missing SKILL.md")
                continue
            fm = frontmatter(skill)
            if fm is None or "name" not in fm or "description" not in fm:
                err(f"{skill.relative_to(REPO)}: frontmatter must have 'name' and 'description'")

    for cfg in (".mcp.json", "hooks/hooks.json"):
        f = pdir / cfg
        if f.is_file():
            try:
                blob = json.loads(f.read_text())
            except json.JSONDecodeError as e:
                err(f"{f.relative_to(REPO)}: not valid JSON ({e})")
                continue
            # every ${CLAUDE_PLUGIN_ROOT}-relative path mentioned must exist
            for ref in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)", json.dumps(blob)):
                if not (pdir / ref).exists():
                    err(f"{f.relative_to(REPO)}: references missing file {ref}")


# Known-good managed-settings keys (verified against the Claude Code settings docs).
# If Claude Code renames a key, the template changes and this pin fires — a deliberate
# two-place change, so renames never slip through silently.
KNOWN_MANAGED_SETTINGS_KEYS = {
    "extraKnownMarketplaces", "strictKnownMarketplaces", "disableSideloadFlags",
    "enabledPlugins", "allowedMcpServers", "env",
}


def check_fleet() -> None:
    f = REPO / "fleet" / "managed-settings.json"
    if not f.is_file():
        return
    print("smoke: fleet/managed-settings.json")
    try:
        ms = json.loads(f.read_text())
    except json.JSONDecodeError as e:
        err(f"fleet/managed-settings.json: not valid JSON ({e})")
        return
    unknown = set(ms) - KNOWN_MANAGED_SETTINGS_KEYS
    if unknown:
        err(f"fleet/managed-settings.json: unpinned settings key(s) {sorted(unknown)} — verify against the "
            f"current Claude Code settings docs, then update KNOWN_MANAGED_SETTINGS_KEYS here")
    if "extraKnownMarketplaces" not in ms:
        err("fleet/managed-settings.json: extraKnownMarketplaces missing — devices would not get the marketplace")


def main() -> int:
    # resolve() matters on macOS: mktemp paths arrive as /var/... but REPO resolves to /private/var/...
    targets = [(REPO / a).resolve() for a in sys.argv[1:]] or sorted(p for p in (REPO / "plugins").iterdir() if p.is_dir())
    for pdir in targets:
        print(f"smoke: {pdir.name}")
        check_plugin(pdir)
    if len(sys.argv) == 1:  # repo-wide run also checks fleet payloads
        check_fleet()
    if findings:
        print(f"smoke: FAIL — {len(findings)} problem(s)")
        import errors as registry
        return registry.get("GATE-003")["exit"]
    print(f"smoke: PASS ({len(targets)} plugin(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
