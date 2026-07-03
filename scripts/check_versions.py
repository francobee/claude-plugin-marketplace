#!/usr/bin/env python3
"""Diff-aware gate: any changed plugin must bump its semver and add a matching CHANGELOG entry (registry code GATE-004 on failure). Usage: check_versions.py [base-ref]."""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=False).stdout


def base_ref() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    for ref in ("origin/main", "main"):
        if subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify", "--quiet", ref],
                          capture_output=True).returncode == 0:
            return ref
    return "HEAD~1"


def semver_tuple(v: str):
    m = SEMVER.match(v or "")
    return tuple(int(x) for x in m.groups()) if m else None


def main() -> int:
    base = base_ref()
    head_sha = git("rev-parse", "HEAD").strip()
    if git("rev-parse", base).strip() == head_sha:
        print(f"check-versions: PASS — base {base} == HEAD, nothing to compare")
        return 0

    changed = git("diff", "--name-only", f"{base}...HEAD").splitlines() or \
              git("diff", "--name-only", base, "HEAD").splitlines()
    GENERATED = {".scorecard.json", ".permissions.json"}  # bot-refreshed sidecars don't require a version bump
    plugins = sorted({p.split("/")[1] for p in changed
                      if p.startswith("plugins/") and len(p.split("/")) > 2
                      and p.split("/")[-1] not in GENERATED})
    if not plugins:
        print("check-versions: PASS — no plugin files changed")
        return 0

    errors = []
    for name in plugins:
        pj_path = f"plugins/{name}/.claude-plugin/plugin.json"
        old_raw = git("show", f"{base}:{pj_path}")
        new_file = REPO / pj_path
        if not new_file.is_file():
            continue  # plugin deleted — allowed, catalog consistency is validate.py's job
        new_ver = json.loads(new_file.read_text()).get("version", "")
        if not semver_tuple(new_ver):
            errors.append(f"{name}: version {new_ver!r} is not semver x.y.z")
            continue
        if old_raw:
            old_ver = json.loads(old_raw).get("version", "")
            if semver_tuple(old_ver) and semver_tuple(new_ver) <= semver_tuple(old_ver):
                errors.append(f"{name}: files changed but version not bumped ({old_ver} → {new_ver}). "
                              f"Fix: bump version in {pj_path} AND marketplace.json, add a CHANGELOG entry.")
        changelog = REPO / "plugins" / name / "CHANGELOG.md"
        if not changelog.is_file() or f"## [{new_ver}]" not in changelog.read_text():
            errors.append(f"{name}: CHANGELOG.md missing a '## [{new_ver}]' entry for the new version")

    if errors:
        print(f"check-versions: FAIL — {len(errors)} finding(s) (base: {base})")
        for e in errors:
            print(f"  ✗ {e}")
        import errors as registry
        return registry.get("GATE-004")["exit"]
    print(f"check-versions: PASS — {', '.join(plugins)} correctly versioned (base: {base})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
