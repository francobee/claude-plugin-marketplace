#!/usr/bin/env python3
"""Watch vendored plugins' upstreams (.upstream.json sidecars). Report drift; with --create-prs, open ready-to-review auto-update PRs (issue fallback)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXCLUDES = (".git", ".github", "tests", "test", "node_modules")


def sh(*args: str, cwd: Path = REPO, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=check)


def gh_api(path: str) -> dict | list:
    req = urllib.request.Request(f"https://api.github.com{path}",
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": "claude-plugin-marketplace"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def detect_drift() -> list[dict]:
    drifted = []
    for sidecar in sorted(REPO.glob("plugins/*/.upstream.json")):
        up = json.loads(sidecar.read_text())
        name, repo, pinned = sidecar.parent.name, up.get("repo"), up.get("commit", "")
        if not (repo and pinned):
            continue
        try:
            head = gh_api(f"/repos/{repo}/commits?per_page=1")[0]["sha"]
        except Exception as e:
            print(f"  warning: {name}: upstream check failed ({e})", file=sys.stderr)
            continue
        status = "fresh" if head == pinned else "DRIFTED"
        print(f"  {name}: {repo} pinned {pinned[:7]} / head {head[:7]} → {status}")
        if head != pinned:
            drifted.append({"name": name, "repo": repo, "subdir": up.get("subdir", ""),
                            "pinned": pinned, "head": head, "sidecar": up})
    return drifted


def bump_patch(v: str) -> str:
    parts = v.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def refresh_payload(d: dict) -> str:
    """Re-import the upstream payload at HEAD into plugins/<name>. Returns the new plugin version."""
    pdir = REPO / "plugins" / d["name"]
    tmp = Path(tempfile.mkdtemp(prefix="upstream-watch-"))
    try:
        sh("git", "clone", "--depth", "1", f"https://github.com/{d['repo']}.git", str(tmp), cwd=REPO)
        src = tmp / d["subdir"] if d["subdir"] else tmp
        keep = {p.name: (pdir / p.name).read_text() for p in (pdir / "CHANGELOG.md", pdir / ".upstream.json") if p.is_file()}
        shutil.rmtree(pdir)
        shutil.copytree(src, pdir, ignore=shutil.ignore_patterns(*EXCLUDES))

        # version: follow upstream plugin.json if present, else patch-bump the previous local version
        manifest = pdir / ".claude-plugin" / "plugin.json"
        old_ver = d["sidecar"].get("upstreamVersion", "0.1.0")
        new_ver = json.loads(manifest.read_text()).get("version", "") if manifest.is_file() else ""
        if not new_ver or new_ver == old_ver:
            new_ver = bump_patch(old_ver)
            if manifest.is_file():
                pj = json.loads(manifest.read_text())
                pj["version"] = new_ver
                manifest.write_text(json.dumps(pj, indent=2) + "\n")

        entry = (f"## [{new_ver}] - {date.today().isoformat()}\n\n### Changed\n"
                 f"- Auto-update from upstream {d['repo']}@{d['head'][:7]} (was {d['pinned'][:7]}).\n")
        changelog = keep.get("CHANGELOG.md", f"# Changelog — {d['name']}\n")
        lines = changelog.splitlines(keepends=True)
        insert_at = next((i for i, ln in enumerate(lines) if ln.startswith("## [")), len(lines))
        (pdir / "CHANGELOG.md").write_text("".join(lines[:insert_at]) + entry + "\n" + "".join(lines[insert_at:]))

        sidecar = d["sidecar"] | {"commit": d["head"], "upstreamVersion": new_ver,
                                  "importedAt": date.today().isoformat(), "importedBy": "upstream-watch"}
        (pdir / ".upstream.json").write_text(json.dumps(sidecar, indent=2) + "\n")

        mp_path = REPO / ".claude-plugin" / "marketplace.json"
        mp = json.loads(mp_path.read_text())
        for e in mp.get("plugins", []):
            if e["name"] == d["name"]:
                e["version"] = new_ver
        mp_path.write_text(json.dumps(mp, indent=2) + "\n")
        return new_ver
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def create_pr(d: dict) -> None:
    branch = f"upstream-update/{d['name']}"
    if sh("git", "ls-remote", "--heads", "origin", branch).stdout.strip():
        print(f"  {d['name']}: branch {branch} already open — skipping")
        return
    sh("git", "checkout", "-B", branch)
    try:
        ver = refresh_payload(d)
        for script in ("validate.py", "risk_lint.py", "smoke_test.py"):
            args = [sys.executable, f"scripts/{script}"] + ([f"plugins/{d['name']}"] if script != "validate.py" else [])
            r = subprocess.run(args, cwd=REPO, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"{script} failed:\n{r.stdout}{r.stderr}")
        sh("git", "add", "-A")
        sh("git", "commit", "-m", f"chore({d['name']}): auto-update from upstream @{d['head'][:7]} (v{ver})")
        sh("git", "push", "-u", "origin", branch)
        sh("gh", "pr", "create", "--title", f"Upstream update: {d['name']} → {d['head'][:7]} (v{ver})",
           "--body", f"Automated re-import of `{d['repo']}` at `{d['head']}` (was `{d['pinned']}`).\n\n"
                     f"Scanners passed locally; full CI gate applies. **Review the diff as if written from scratch.**")
        print(f"  {d['name']}: PR opened ({branch})")
    except Exception as e:
        sh("git", "checkout", "main", check=False)
        sh("git", "branch", "-D", branch, check=False)
        title = f"Upstream drift: {d['name']} ({d['repo']})"
        body = (f"Upstream moved to `{d['head']}` (pinned `{d['pinned']}`) but the automated re-import failed:\n\n"
                f"```\n{str(e)[:1500]}\n```\nUpdate manually with `./scripts/vendor_import.sh`.")
        existing = sh("gh", "issue", "list", "--search", title, "--json", "title", check=False).stdout
        if title not in existing:
            sh("gh", "issue", "create", "--title", title, "--body", body, check=False)
        print(f"  {d['name']}: auto-update failed → issue filed ({e})")
    finally:
        sh("git", "checkout", "main", check=False)


def main() -> int:
    print("upstream-watch: checking vendored plugins")
    drifted = detect_drift()
    if not drifted:
        print("upstream-watch: all fresh")
        return 0
    if "--create-prs" not in sys.argv:
        print(f"upstream-watch: {len(drifted)} drifted (run with --create-prs to open update PRs)")
        return 0
    if not shutil.which("gh"):
        print("upstream-watch: gh CLI not available — cannot open PRs", file=sys.stderr)
        return 1
    for d in drifted:
        create_pr(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
