#!/usr/bin/env python3
"""Admin notification ladder — zero-config first, silent-for-end-users, never blocks a pipeline.

Ladder: (1) auto-filed GitHub issue in this repo, deduped by error code (comments on the
existing open issue instead of re-filing); (2) GitHub's own email does the rest;
(3) Slack message only if integrations.slack.enabled and SLACK_WEBHOOK_URL is set.

Usage: notify.py --code CFG-005 [--title "…"] [--context "extra detail"] [--dry-run]
Always exits 0 — a broken notifier must never break the thing it reports on.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import config_loader
import errors

REPO = Path(__file__).resolve().parent.parent
GH = os.environ.get("NOTIFY_GH_BIN", "gh")


def load_cfg() -> dict:
    try:
        return config_loader.load(REPO / "marketplace.config.yml")
    except Exception:
        return {}  # fail-soft: env-driven defaults still work


def gh_json(*args: str):
    r = subprocess.run([GH, *args], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}…: {r.stderr.strip()[:200]}")
    return json.loads(r.stdout) if r.stdout.strip() else None


def gh_run(*args: str) -> None:
    r = subprocess.run([GH, *args], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}…: {r.stderr.strip()[:200]}")


def build_body(code: str, entry: dict, context: str) -> str:
    lines = [f"**[{code}] {entry['meaning']}**", "",
             f"- **User impact:** {entry['user_impact']}",
             f"- **Admin fix:** {entry['admin_fix']}"]
    if entry.get("device_fix"):
        lines.append(f"- **Per-device fix:** `{entry['device_fix']}`")
    if context:
        lines += ["", "```", context[:3000], "```"]
    run_id = os.environ.get("GITHUB_RUN_ID")
    if run_id:
        lines += ["", f"CI run: {os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
                      f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{run_id}"]
    lines += ["", "_Auto-filed by scripts/notify.py — see docs/TROUBLESHOOTING.md#"
              + code.lower() + "_"]
    return "\n".join(lines)


def github_issue(cfg: dict, code: str, title: str, body: str, dry: bool) -> None:
    repo = os.environ.get("GITHUB_REPOSITORY") or config_loader.get(cfg, "company.github_repo", "")
    if not repo:
        raise RuntimeError("no GITHUB_REPOSITORY env or company.github_repo config")
    labels = config_loader.get(cfg, "notifications.labels", None) or ["claude-mgmt", "error-code"]
    if dry:
        print(f"notify(dry-run): would file/comment GitHub issue in {repo}: {title!r} labels={labels}")
        return
    existing = gh_json("issue", "list", "--repo", repo, "--state", "open",
                       "--search", f"[{code}] in:title", "--json", "number,title") or []
    match = next((i for i in existing if i["title"].startswith(f"[{code}]")), None)
    if match:
        gh_run("issue", "comment", str(match["number"]), "--repo", repo, "--body", body)
        print(f"notify: commented on existing issue #{match['number']} in {repo}")
        return
    for label in labels:
        try:
            gh_run("label", "create", label, "--repo", repo, "--force",
                   "--description", "claude-plugin-marketplace automation")
        except RuntimeError:
            pass  # label may already exist or perms may be narrow — issue create is what matters
    args = ["issue", "create", "--repo", repo, "--title", title, "--body", body]
    for label in labels:
        args += ["--label", label]
    gh_run(*args)
    print(f"notify: filed new issue in {repo}: {title}")


def slack(cfg: dict, title: str, body: str, dry: bool) -> None:
    if not config_loader.get(cfg, "integrations.slack.enabled", False):
        return
    url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not url:
        print("notify: slack enabled but SLACK_WEBHOOK_URL unset — skipping (GitHub issue is the primary channel)")
        return
    if dry:
        print(f"notify(dry-run): would post to Slack: {title!r}")
        return
    payload = json.dumps({"text": f":rotating_light: {title}\n{body[:1500]}"}).encode()
    req = urllib.request.Request(url, payload, {"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)
    print("notify: posted to Slack")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--context", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_cfg()
    entry = errors.registry().get(args.code)
    if entry is None:
        print(f"notify: unknown code {args.code!r} — filing generic notification", file=sys.stderr)
        entry = {"meaning": args.title or "unregistered failure", "user_impact": "Unknown.",
                 "admin_fix": "Investigate the CI run linked below.", "device_fix": ""}
    title = args.title or f"[{args.code}] {entry['meaning']}"
    body = build_body(args.code, entry, args.context)

    if config_loader.get(cfg, "notifications.github_issues", True):
        github_issue(cfg, args.code, title, body, args.dry_run)
    slack(cfg, title, body, args.dry_run)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:  # NOTIFY-001: the notifier itself must never break a pipeline
        print(f"notify: [NOTIFY-001] delivery failed — {e}", file=sys.stderr)
        sys.exit(0)
