#!/usr/bin/env python3
"""Classify plugin risk tier + scan for dangerous patterns; writes risk-report.json. Exits with registry code GATE-002 on high findings or tier under-declaration."""
import json
import math
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE_ALLOWLIST = ("github.com", "githubusercontent.com", "api.anthropic.com", "keepachangelog.com")


def _allowlist() -> tuple:
    """Base domains + security.network_allowlist from marketplace.config.yml (fail-soft to base)."""
    try:
        import config_loader
        cfg = config_loader.load(REPO / "marketplace.config.yml")
        extra = config_loader.get(cfg, "security.network_allowlist", []) or []
        return BASE_ALLOWLIST + tuple(str(d) for d in extra)
    except Exception:
        return BASE_ALLOWLIST


NETWORK_ALLOWLIST = _allowlist()


def _load_rules() -> list:
    """Load scan rules from schemas/risk_rules.json, falling back to an empty list."""
    rules_path = Path(__file__).resolve().parent / "schemas" / "risk_rules.json"
    try:
        rules = json.loads(rules_path.read_text()).get("rules", [])
        return [(re.compile(r["pattern"]), r["severity"], r["message"]) for r in rules]
    except Exception as e:
        print(f"risk-lint: WARNING — could not load {rules_path}: {e}", file=sys.stderr)
        return []


PATTERNS = _load_rules()
URL_RE = re.compile(r"https?://([a-zA-Z0-9.-]+)")
URI_SCHEME_RE = re.compile(r"(wss?|ftp|data)://([a-zA-Z0-9.-]+)")
HIDDEN_UNICODE = re.compile("[​‌‍⁠﻿‪-‮⁦-⁩]")
HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.S)
TEXT_EXT = {".md", ".txt", ".json", ".sh", ".py", ".js", ".ts", ".yaml", ".yml", ".toml",
            ".mjs", ".cjs", ".jsx", ".tsx", ".mts", ""}


def _domain_ok(host: str) -> bool:
    """Check if a host exactly matches an allowlisted domain or is www.<domain>."""
    host = host.lower().rstrip(".")
    for d in NETWORK_ALLOWLIST:
        d = d.lower().rstrip(".")
        if host == d or host == f"www.{d}":
            return True
    return False


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {c: s.count(c) for c in set(s)}
    return -sum(n / len(s) * math.log2(n / len(s)) for n in freq.values())


def scan_file(path: Path, findings: list) -> None:
    rel = str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)
    try:
        text = path.read_text(errors="replace")
    except (OSError, UnicodeError):
        findings.append({"file": rel, "line": 0, "severity": "medium", "message": "unreadable file (binary?) — review manually"})
        return
    for lineno, line in enumerate(text.splitlines(), 1):
        for rx, sev, msg in PATTERNS:
            if rx.search(line):
                findings.append({"file": rel, "line": lineno, "severity": sev, "message": msg})
        for host in URL_RE.findall(line):
            if not _domain_ok(host):
                findings.append({"file": rel, "line": lineno, "severity": "high", "message": f"network destination outside allowlist: {host}"})
        for scheme, host in URI_SCHEME_RE.findall(line):
            if scheme == "data":
                findings.append({"file": rel, "line": lineno, "severity": "high", "message": f"data: URI (potential obfuscation vector)"})
            elif not _domain_ok(host):
                findings.append({"file": rel, "line": lineno, "severity": "high", "message": f"non-HTTP network destination outside allowlist: {scheme}://{host}"})
        for token in re.findall(r"[A-Za-z0-9+/=_-]{80,}", line):
            if shannon_entropy(token) > 4.5:
                findings.append({"file": rel, "line": lineno, "severity": "high", "message": "long high-entropy string (embedded blob/secret?)"})
        if HIDDEN_UNICODE.search(line):
            findings.append({"file": rel, "line": lineno, "severity": "high", "message": "zero-width/bidi Unicode (hidden-instruction vector)"})
    if path.suffix == ".md":
        for m in HTML_COMMENT.finditer(text):
            if m.group(1).strip():
                lineno = text[:m.start()].count("\n") + 1
                findings.append({"file": rel, "line": lineno, "severity": "medium", "message": "non-empty HTML comment in markdown (hidden-instruction vector)"})


def detect_tier(pdir: Path, findings: list) -> int:
    tier = 1
    if (pdir / "hooks").is_dir() or (pdir / "hooks" / "hooks.json").is_file() or (pdir / "bin").is_dir():
        tier = 3
    exec_exts = {".sh", ".py", ".js", ".ts", ".rb", ".pl"}
    for f in pdir.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix in exec_exts or os.access(f, os.X_OK):
            tier = max(tier, 3)
    mcp = pdir / ".mcp.json"
    if mcp.is_file():
        try:
            cfg = json.loads(mcp.read_text())
        except json.JSONDecodeError:
            findings.append({"file": str(mcp.relative_to(REPO)), "line": 0, "severity": "high", "message": "invalid .mcp.json"})
            return 3
        for name, server in cfg.get("mcpServers", cfg).items():
            if server.get("command"):
                tier = max(tier, 3)  # spawns a local process
            else:
                url = server.get("url", "")
                host = URL_RE.search("x://" + url.split("://")[-1])
                tier = max(tier, 2)
    # commands/agents with bash-executing frontmatter (`!` prefix or allowed-tools with Bash)
    for md in list(pdir.rglob("commands/**/*.md")) + list(pdir.rglob("agents/**/*.md")):
        text = md.read_text(errors="replace")
        if re.search(r"^\s*!\s*`", text, re.M) or re.search(r"allowed-tools:.*Bash", text):
            tier = max(tier, 2)
    return tier


def declared_tier(plugin_name: str) -> int | None:
    mp = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    for e in mp.get("plugins", []):
        if e.get("name") == plugin_name:
            for t in e.get("tags", []):
                m = re.match(r"^tier-([123])$", t)
                if m:
                    return int(m.group(1))
    return None


def main() -> int:
    targets = [Path(a).resolve() for a in sys.argv[1:]] or sorted(p for p in (REPO / "plugins").iterdir() if p.is_dir())
    report, exit_code = [], 0
    for pdir in targets:
        if not pdir.is_dir():
            print(f"risk-lint: {pdir} is not a directory")
            return 2
        findings: list = []
        for f in sorted(pdir.rglob("*")):
            if f.is_file() and (f.suffix in TEXT_EXT or os.access(f, os.X_OK)):
                scan_file(f, findings)
        detected = detect_tier(pdir, findings)
        declared = declared_tier(pdir.name)
        highs = [f for f in findings if f["severity"] == "high"]
        status = "pass"
        if highs:
            status = "fail"
        if declared is not None and declared < detected:
            status = "fail"
            findings.append({"file": pdir.name, "line": 0, "severity": "high",
                             "message": f"tier under-declared: declared tier-{declared}, detected tier-{detected}"})
        report.append({"plugin": pdir.name, "detected_tier": detected, "declared_tier": declared,
                       "status": status, "findings": findings})
        if status == "fail":
            exit_code = 1

    (REPO / "risk-report.json").write_text(json.dumps(report, indent=2))
    for r in report:
        icon = "✓" if r["status"] == "pass" else "✗"
        print(f"{icon} {r['plugin']}: detected tier-{r['detected_tier']}"
              f" (declared: {'tier-' + str(r['declared_tier']) if r['declared_tier'] else 'NONE'}),"
              f" {len(r['findings'])} finding(s)")
        for f in r["findings"]:
            print(f"    [{f['severity'].upper()}] {f['file']}:{f['line']} — {f['message']}")
    print(f"risk-lint: {'FAIL' if exit_code else 'PASS'} — report written to risk-report.json")
    if exit_code:
        import errors
        return errors.get("GATE-002")["exit"]
    return 0


if __name__ == "__main__":
    sys.exit(main())
