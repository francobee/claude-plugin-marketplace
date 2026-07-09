#!/usr/bin/env python3
"""Validate marketplace.json and every plugin.json for schema + cross-consistency. Exits with registry code GATE-001 on any finding."""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
KEBAB = re.compile(r"^[a-z][a-z0-9-]*$")
RESERVED_MARKETPLACE_NAMES = {
    "claude-code-marketplace", "claude-code-plugins", "claude-plugins-official",
    "claude-plugins-community", "anthropic-marketplace", "anthropic-plugins",
    "agent-skills", "anthropic-agent-skills",
}

findings: list[str] = []


def err(msg: str) -> None:
    findings.append(msg)


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        err(f"{path.relative_to(REPO)}: missing")
    except json.JSONDecodeError as e:
        err(f"{path.relative_to(REPO)}: invalid JSON — {e}")
    return None


def main() -> int:
    mp_path = REPO / ".claude-plugin" / "marketplace.json"
    mp = load_json(mp_path)
    if mp is None:
        report()
        import errors as registry
        return registry.get("GATE-001")["exit"]

    # schema validation (structural/type errors before imperative cross-file checks)
    import schema_validator
    schema_dir = Path(__file__).resolve().parent / "schemas"
    for e in schema_validator.validate_file(mp_path, schema_dir / "marketplace.schema.json"):
        err(f"marketplace.json schema: {e}")

    # marketplace-level checks
    name = mp.get("name", "")
    if not KEBAB.match(name):
        err(f"marketplace name {name!r} is not kebab-case")
    if name in RESERVED_MARKETPLACE_NAMES:
        err(f"marketplace name {name!r} collides with a reserved official name")
    if not mp.get("owner", {}).get("name"):
        err("marketplace owner.name is required")

    plugin_root = (REPO / mp.get("metadata", {}).get("pluginRoot", ".")).resolve()

    entries = mp.get("plugins")
    if not isinstance(entries, list) or not entries:
        err("marketplace plugins[] must be a non-empty array")
        report()
        import errors as registry
        return registry.get("GATE-001")["exit"]

    seen: set[str] = set()
    cataloged_dirs: set[Path] = set()
    for i, e in enumerate(entries):
        label = f"plugins[{i}] ({e.get('name', '?')})"
        pname = e.get("name", "")
        if not KEBAB.match(pname):
            err(f"{label}: name is not kebab-case")
        if pname in seen:
            err(f"{label}: duplicate plugin name")
        seen.add(pname)
        if not e.get("description"):
            err(f"{label}: description is required (house rule)")
        if not SEMVER.match(str(e.get("version", ""))):
            err(f"{label}: version must be explicit semver x.y.z (house rule — omitted versions ship every commit)")
        if e.get("strict") is not True:
            err(f"{label}: strict must be true (house rule — fail at publish, not at install)")
        tags = e.get("tags", [])
        if not any(re.match(r"^tier-[123]$", t) for t in tags):
            err(f"{label}: tags must include a risk tier tag (tier-1|tier-2|tier-3)")

        src = e.get("source")
        if isinstance(src, str):
            pdir = (plugin_root / src).resolve()
            if not pdir.is_dir():
                err(f"{label}: source dir {src!r} not found under pluginRoot")
                continue
            cataloged_dirs.add(pdir)
            pj_path = pdir / ".claude-plugin" / "plugin.json"
            pj = load_json(pj_path)
            if pj is None:
                continue
            for se in schema_validator.validate_file(pj_path, schema_dir / "plugin.schema.json"):
                err(f"{label}: plugin.json schema: {se}")
            if pj.get("name") != pname:
                err(f"{label}: plugin.json name {pj.get('name')!r} != marketplace entry name {pname!r}")
            if not SEMVER.match(str(pj.get("version", ""))):
                err(f"{label}: plugin.json version must be explicit semver x.y.z")
            elif pj.get("version") != e.get("version"):
                err(f"{label}: plugin.json version {pj.get('version')} != marketplace entry version {e.get('version')}")
            if not pj.get("description"):
                err(f"{label}: plugin.json description is required (house rule)")
            if not (pdir / "CHANGELOG.md").is_file():
                err(f"{label}: CHANGELOG.md is required (house rule)")
            elif SEMVER.match(str(pj.get("version", ""))):
                heading = f"## [{pj['version']}]"
                if heading not in (pdir / "CHANGELOG.md").read_text():
                    err(f"{label}: CHANGELOG.md has no '{heading}' entry for the current version")
        else:
            err(f"{label}: house rule — plugins must live in this repo as relative paths "
                f"(vendor external code via scripts/vendor_import.sh), got source={src!r}")

    # orphan plugin dirs not in the catalog
    plugins_dir = REPO / "plugins"
    if plugins_dir.is_dir():
        for d in sorted(plugins_dir.iterdir()):
            if d.is_dir() and d.resolve() not in cataloged_dirs:
                err(f"plugins/{d.name}: directory exists but is not listed in marketplace.json")

    report()
    if findings:
        import errors as registry
        return registry.get("GATE-001")["exit"]
    return 0


def report() -> None:
    if findings:
        print(f"validate: FAIL — {len(findings)} finding(s)")
        for e in findings:
            print(f"  ✗ {e}")
    else:
        print("validate: PASS — marketplace.json and all plugin manifests are consistent")


if __name__ == "__main__":
    sys.exit(main())
