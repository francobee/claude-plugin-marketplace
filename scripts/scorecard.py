#!/usr/bin/env python3
"""Emit a .scorecard.json sidecar per plugin: scanner results + upstream freshness. Consumed by build_catalog.py and build_site.py."""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent


def run_check(script: str, plugin_rel: str) -> bool:
    r = subprocess.run([sys.executable, str(SCRIPTS / script), plugin_rel],
                       capture_output=True, text=True, cwd=REPO)
    return r.returncode == 0


def upstream_fresh(pdir: Path) -> bool | None:
    sidecar = pdir / ".upstream.json"
    if not sidecar.is_file():
        return None
    up = json.loads(sidecar.read_text())
    repo, pinned = up.get("repo"), up.get("commit", "")
    if not repo or not pinned:
        return None
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/commits?per_page=1",
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": "claude-plugin-marketplace"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            head = json.load(r)[0]["sha"]
        return head == pinned
    except Exception as e:  # freshness is best-effort — never block
        print(f"  warning: upstream check failed for {repo}: {e}", file=sys.stderr)
        return None


def main() -> int:
    mp = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    llm = None
    llm_report = REPO / "llm-review.json"
    if llm_report.is_file():
        llm = json.loads(llm_report.read_text()).get("verdict") == "pass"
    for e in mp.get("plugins", []):
        name = e["name"]
        pdir = REPO / "plugins" / name
        sc = {
            "risk_lint": run_check("risk_lint.py", f"plugins/{name}"),
            "smoke_test": run_check("smoke_test.py", f"plugins/{name}"),
            "llm_review": llm,
            "upstream_fresh": upstream_fresh(pdir),
            "date": date.today().isoformat(),
        }
        (pdir / ".scorecard.json").write_text(json.dumps(sc, indent=2) + "\n")
        print(f"scorecard: {name} → {sc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
