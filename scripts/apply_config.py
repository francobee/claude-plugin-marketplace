#!/usr/bin/env python3
"""Idempotent renderer: marketplace.config.yml → marketplace.json, CODEOWNERS, doc values, TROUBLESHOOTING.

Usage:
  apply_config.py            render everything (safe to run twice — second run is a no-op)
  apply_config.py --check    validate config + marker integrity only, write nothing
  apply_config.py --list     print the files this script manages (used by the test harness)

Doc markers (see docs/AUTHORING.md):
  inline value:    <!-- cfg:company.name -->rendered value<!-- /cfg -->     (one line)
  generated block: <!-- gen:name -->…<!-- /gen:name -->  body rendered from templates/name.md
Template placeholders: {{dotted.path}} → config value.
"""
import json
import re
import sys
from pathlib import Path

import hashlib

import config_loader
import errors

REPO = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO / "marketplace.config.yml"
DOC_FILES = ["README.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
             "docs/GETTING-STARTED.md", "docs/AUTHORING.md",
             "docs/VENDORING.md", "docs/SECURITY.md", "docs/FLEET.md", "docs/UPDATING.md",
             "docs/HOSTING.md", "docs/TUTORIAL-ADMIN.md", "docs/TUTORIAL-USER.md"]
# Lowercase-only on purpose: uppercase names (e.g. `gen:NAME` in doc examples) are inert.
CFG_RE = re.compile(r"<!-- cfg:([a-z0-9_.-]+) -->(.*?)<!-- /cfg -->")
GEN_TOKEN_RE = re.compile(r"<!-- (/?)gen:([a-z0-9-]+) -->")
PLACEHOLDER_RE = re.compile(r"\{\{([a-z0-9_.-]+)\}\}")

# Every key the config may contain, with its expected type. Unknown keys fail loud (CFG-003).
SCHEMA = {
    "schema_version": int,
    "company": {"name": str, "marketplace_name": str, "contact_email": str, "github_repo": str, "codeowners": list},
    "security": {"network_allowlist": list},
    "integrations": {
        "llm_review": {"enabled": bool},
        "slack": {"enabled": bool, "announce": bool, "digest": bool},
        "confluence": {"enabled": bool, "base_url": str, "space_key": str},
        "teamwork_graph": {"enabled": bool, "url": str},
    },
    "notifications": {"github_issues": bool, "labels": list},
    "telemetry": {"enabled": bool, "mode": str, "retention_days": int, "endpoint": str, "deploy_target": str},
    "fleet": {
        "mdm": str, "strict_marketplaces": bool, "disable_sideload": bool,
        "enabled_plugins": list, "allowed_mcp_servers": list,
        "install": {"homebrew": bool, "node": bool, "gh": bool, "auto_update": bool, "version": str},
        "health": {"enabled": bool, "interval_hours": int},
        "repo_access": {"method": str},
    },
    "watch": {"anthropic_official": bool, "community_marketplaces": list, "digest_day": str},
    "site": {"hosting": str, "cloudflare_project": str, "title": str, "sections": list},
}
ENUMS = {"telemetry.mode": ("pseudonymous", "anonymous"), "fleet.mdm": ("jumpcloud", "generic"),
         "fleet.repo_access.method": ("fine_grained_pat",),
         "site.hosting": ("github-pages", "cloudflare", "none")}


def load_config() -> dict:
    try:
        return config_loader.load(CONFIG_PATH)
    except FileNotFoundError:
        errors.die("CFG-001", str(CONFIG_PATH.relative_to(REPO)))
    except config_loader.ConfigError as e:
        errors.die("CFG-002", str(e))


def validate_schema(cfg: dict) -> None:
    def walk(node, spec, path):
        for key, val in node.items():
            dotted = f"{path}.{key}" if path else key
            if key not in spec:
                errors.die("CFG-003", f"unknown key {dotted!r} in marketplace.config.yml")
            expected = spec[key]
            if isinstance(expected, dict):
                if not isinstance(val, dict):
                    errors.die("CFG-003", f"{dotted!r} must be an indented block")
                walk(val, expected, dotted)
            elif expected is bool:
                if not isinstance(val, bool):
                    errors.die("CFG-003", f"{dotted!r} must be true or false, got {val!r}")
            elif expected is int:
                if not isinstance(val, int) or isinstance(val, bool):
                    errors.die("CFG-003", f"{dotted!r} must be an integer, got {val!r}")
            elif expected is list:
                if not isinstance(val, list):
                    errors.die("CFG-003", f"{dotted!r} must be a list (`- item` lines) or []")
            elif expected is str:
                if not isinstance(val, str):
                    errors.die("CFG-003", f"{dotted!r} must be a string, got {val!r}")
            if dotted in ENUMS and val not in ENUMS[dotted]:
                errors.die("CFG-003", f"{dotted!r} must be one of {ENUMS[dotted]}, got {val!r}")

    walk(cfg, SCHEMA, "")
    if cfg.get("schema_version") != 1:
        errors.die("CFG-003", f"schema_version must be 1, got {cfg.get('schema_version')!r}")
    for req in ("company.name", "company.marketplace_name", "company.contact_email", "company.github_repo"):
        if not config_loader.get(cfg, req):
            errors.die("CFG-003", f"{req!r} is required")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", config_loader.get(cfg, "company.marketplace_name", "")):
        errors.die("CFG-003", "company.marketplace_name must be lowercase kebab-case")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", config_loader.get(cfg, "company.github_repo", "")):
        errors.die("CFG-003", "company.github_repo must look like org/repo")
    cf_project = config_loader.get(cfg, "site.cloudflare_project", "")
    if cf_project and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", cf_project):
        errors.die("CFG-003", "site.cloudflare_project must be lowercase kebab-case (it becomes <project>.pages.dev)")


def value_str(cfg: dict, dotted: str, where: str):
    val = config_loader.get(cfg, dotted, None)
    if val is None:
        errors.die("CFG-004" if "<!--" in where else "CFG-003", f"{where}: unknown config path {dotted!r}")
    if isinstance(val, list):
        return " ".join(str(v) for v in val)
    if isinstance(val, bool):
        return "true" if val else "false"
    return str(val)


def check_markers(text: str, rel: str, template_names: set) -> None:
    """Hard-fail (file:line) on unbalanced/unknown markers."""
    for lineno, line in enumerate(text.splitlines(), 1):
        opens, closes = line.count("<!-- cfg:"), line.count("<!-- /cfg -->")
        matched = len(CFG_RE.findall(line))
        if opens != closes or matched != opens:
            errors.die("CFG-004", f"{rel}:{lineno}: unbalanced <!-- cfg:… --> marker (open/close must pair on one line)")
    expect_close = None
    for m in GEN_TOKEN_RE.finditer(text):
        closing, name = m.group(1) == "/", m.group(2)
        lineno = text[:m.start()].count("\n") + 1
        if not closing:
            if expect_close:
                errors.die("CFG-004", f"{rel}:{lineno}: gen block {expect_close!r} not closed before {name!r} opens")
            if name not in template_names:
                errors.die("CFG-004", f"{rel}:{lineno}: gen block {name!r} has no templates/{name}.md")
            expect_close = name
        else:
            if expect_close != name:
                errors.die("CFG-004", f"{rel}:{lineno}: unexpected <!-- /gen:{name} -->")
            expect_close = None
    if expect_close:
        errors.die("CFG-004", f"{rel}: gen block {expect_close!r} never closed")


def render_template(cfg: dict, tpl_path: Path, extra: dict | None = None) -> str:
    rel = str(tpl_path.relative_to(REPO))

    def sub(m):
        key = m.group(1)
        if extra and key in extra:
            return extra[key]
        return value_str(cfg, key, rel)

    return PLACEHOLDER_RE.sub(sub, tpl_path.read_text())


def render_doc(cfg: dict, text: str, rel: str) -> str:
    text = CFG_RE.sub(lambda m: f"<!-- cfg:{m.group(1)} -->{value_str(cfg, m.group(1), f'{rel} <!-- marker')}<!-- /cfg -->", text)

    def gen_body(m):
        name = m.group(1)
        rendered = render_template(cfg, REPO / "templates" / f"{name}.md").rstrip("\n")
        return f"<!-- gen:{name} -->\n{rendered}\n<!-- /gen:{name} -->"

    return re.sub(r"<!-- gen:([a-z0-9-]+) -->\n?(.*?)<!-- /gen:\1 -->", gen_body, text, flags=re.S)


def render_marketplace_json(cfg: dict) -> Path:
    path = REPO / ".claude-plugin" / "marketplace.json"
    mp = json.loads(path.read_text())
    mp["name"] = config_loader.get(cfg, "company.marketplace_name")
    mp["owner"] = {"name": config_loader.get(cfg, "company.name"),
                   "email": config_loader.get(cfg, "company.contact_email")}
    for e in mp.get("plugins", []):
        e["author"] = dict(mp["owner"])
    path.write_text(json.dumps(mp, indent=2, ensure_ascii=False) + "\n")
    return path


def render_codeowners(cfg: dict) -> Path:
    path = REPO / ".github" / "CODEOWNERS"
    handles = " ".join(config_loader.get(cfg, "company.codeowners", []) or ["@your-github-handle"])
    out = []
    for line in path.read_text().splitlines(keepends=True):
        if line.strip() and not line.startswith("#"):
            out.append(f"{line.split()[0]} {handles}\n")
        else:
            out.append(line)
    path.write_text("".join(out))
    return path


def render_troubleshooting() -> Path:
    reg = errors.registry()
    lines = ["# Troubleshooting",
             "",
             "_Generated by `scripts/apply_config.py` from `errors.json` — do not hand-edit._",
             "",
             "Every automation failure in this marketplace exits with a registry code below. "
             "End users never see these; they surface to admins via auto-filed GitHub issues, "
             "CI logs, and fleet health-check results.",
             "",
             "| Code | Meaning | Exit |",
             "|---|---|---|"]
    for code in sorted(reg):
        lines.append(f"| [`{code}`](#{code.lower()}) | {reg[code]['meaning']} | {reg[code]['exit']} |")
    for code in sorted(reg):
        e = reg[code]
        lines += ["", f"## {code}", "", f"**Meaning:** {e['meaning']}", "",
                  f"**User impact:** {e['user_impact']}", "", f"**Admin fix:** {e['admin_fix']}"]
        if e.get("device_fix"):
            lines += ["", f"**Per-device fix:** `{e['device_fix']}`"]
    path = REPO / "docs" / "TROUBLESHOOTING.md"
    path.write_text("\n".join(lines) + "\n")
    return path


def render_fleet(cfg: dict) -> list:
    """Render fleet/ payloads: managed settings JSON, JumpCloud lifecycle scripts, ops README.
    All Claude Code settings key names live ONLY in templates/fleet/managed-settings.json.tmpl."""
    tdir = REPO / "templates" / "fleet"
    if not tdir.is_dir():
        return []
    get = config_loader.get
    market = get(cfg, "company.marketplace_name")

    raw = render_template(cfg, tdir / "managed-settings.json.tmpl")
    try:
        ms = json.loads(raw)
    except json.JSONDecodeError as e:
        errors.die("CFG-004", f"templates/fleet/managed-settings.json.tmpl renders invalid JSON — {e}")
    ms["enabledPlugins"] = {f"{p}@{market}": True for p in get(cfg, "fleet.enabled_plugins", []) or []}
    if not get(cfg, "fleet.strict_marketplaces", True):
        ms.pop("strictKnownMarketplaces", None)
    if not get(cfg, "fleet.disable_sideload", True):
        ms.pop("disableSideloadFlags", None)
    servers = [str(s) for s in get(cfg, "fleet.allowed_mcp_servers", []) or []]
    if servers:
        # Teamwork Graph MCP joins the allowlist only when one is already in force —
        # an empty list means "unmanaged", and allowedMcpServers=[] would block everything.
        if get(cfg, "integrations.teamwork_graph.enabled", False) and "atlassian" not in servers:
            servers.append("atlassian")
        ms["allowedMcpServers"] = [{"serverName": s} for s in servers]
    else:
        ms.pop("allowedMcpServers", None)
    if not (get(cfg, "telemetry.enabled", False) and get(cfg, "telemetry.endpoint", "")):
        ms.pop("env", None)  # telemetry off ⇒ no OTEL env on devices at all

    ms_text = json.dumps(ms, indent=2, ensure_ascii=False) + "\n"
    ms_sha = hashlib.sha256(ms_text.encode()).hexdigest()
    written = []
    out = REPO / "fleet" / "managed-settings.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(ms_text)
    written.append(out)

    extra = {"managed_settings_json": ms_text.rstrip("\n"), "managed_settings_sha": ms_sha}
    for code, entry in errors.registry().items():
        if code.startswith("FLEET-"):
            extra[f"msg_{code.lower().replace('-', '_')}"] = entry["meaning"]

    jdir = REPO / "fleet" / "jumpcloud"
    jdir.mkdir(parents=True, exist_ok=True)
    for tmpl in sorted(tdir.glob("*.sh.tmpl")):
        dest = jdir / tmpl.name[: -len(".tmpl")]
        dest.write_text(render_template(cfg, tmpl, extra))
        dest.chmod(0o755)
        written.append(dest)
    if (tdir / "readme.md.tmpl").is_file():
        dest = REPO / "fleet" / "README.md"
        dest.write_text(render_template(cfg, tdir / "readme.md.tmpl", extra))
        written.append(dest)
    return written


def fleet_outputs() -> list:
    """Paths render_fleet would write (for --list, even before first render)."""
    tdir = REPO / "templates" / "fleet"
    if not tdir.is_dir():
        return []
    outs = [REPO / "fleet" / "managed-settings.json"]
    outs += [REPO / "fleet" / "jumpcloud" / t.name[: -len(".tmpl")] for t in sorted(tdir.glob("*.sh.tmpl"))]
    if (tdir / "readme.md.tmpl").is_file():
        outs.append(REPO / "fleet" / "README.md")
    return outs


def denylist_scan(paths) -> None:
    """Logs pipelines are never allowed — OTEL_LOG_* must not appear in config or templates."""
    for p in paths:
        if not p.is_file():
            continue
        for lineno, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            if "OTEL_LOG" in line:
                errors.die("CFG-006", f"{p.relative_to(REPO)}:{lineno}")


def managed_docs() -> list:
    return [REPO / f for f in DOC_FILES if (REPO / f).is_file()]


def main() -> int:
    args = sys.argv[1:]
    cfg = load_config()
    validate_schema(cfg)
    template_names = {p.stem for p in (REPO / "templates").glob("*.md")} if (REPO / "templates").is_dir() else set()
    scan_targets = [CONFIG_PATH] + sorted((REPO / "templates").glob("**/*")) if (REPO / "templates").is_dir() else [CONFIG_PATH]
    denylist_scan(scan_targets)

    if "--list" in args:
        managed = [REPO / ".claude-plugin" / "marketplace.json", REPO / ".github" / "CODEOWNERS",
                   REPO / "docs" / "TROUBLESHOOTING.md", *managed_docs(), *fleet_outputs()]
        for p in managed:
            print(p.relative_to(REPO))
        return 0

    for doc in managed_docs():
        check_markers(doc.read_text(), str(doc.relative_to(REPO)), template_names)
    if "--check" in args:
        print("apply-config: CHECK PASS — config valid, all markers balanced")
        return 0

    written = [render_marketplace_json(cfg), render_codeowners(cfg), render_troubleshooting(), *render_fleet(cfg)]
    for doc in managed_docs():
        old = doc.read_text()
        new = render_doc(cfg, old, str(doc.relative_to(REPO)))
        if new != old:
            doc.write_text(new)
            written.append(doc)
    print(f"apply-config: rendered {len(written)} file(s) from marketplace.config.yml")
    for p in written:
        print(f"  → {p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
