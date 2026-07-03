#!/usr/bin/env python3
"""Create-or-update a Confluence catalog page from marketplace.json (optional integration). Fail-soft: missing config exits 0 with a notice."""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from base64 import b64encode
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAGE_TITLE = os.environ.get("CONFLUENCE_PAGE_TITLE", "Claude Code Plugin Marketplace")


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tier_of(entry: dict) -> str:
    for t in entry.get("tags", []):
        m = re.match(r"^tier-([123])$", t)
        if m:
            return {"1": "T1 prompt-only", "2": "T2 read/config", "3": "T3 code-executing"}[m.group(1)]
    return "untiered"


def storage_body(mp: dict) -> str:
    market = mp.get("name", "internal")
    rows = "".join(
        f"<tr><td><strong>{esc(e.get('displayName', e['name']))}</strong> (<code>{esc(e['name'])}</code>)</td>"
        f"<td>{esc(e['version'])}</td><td>{esc(tier_of(e))}</td><td>{esc(e.get('category', '—'))}</td>"
        f"<td>{esc(e.get('description', ''))}</td>"
        f"<td><code>/plugin install {esc(e['name'])}@{esc(market)}</code></td></tr>"
        for e in sorted(mp.get("plugins", []), key=lambda x: x["name"])
    )
    return (
        "<p>The trusted internal source for Claude Code plugins — everything below is "
        "security-scanned and admin-approved. You may install plugins from other marketplaces too; "
        "they just aren't reviewed internally.</p>"
        "<table><tbody>"
        "<tr><th>Plugin</th><th>Version</th><th>Risk tier</th><th>Category</th><th>Description</th><th>Install</th></tr>"
        f"{rows}</tbody></table>"
        "<p><em>This page is generated from the marketplace repo — do not hand-edit.</em></p>"
    )


def api(base: str, auth: str, method: str, path: str, payload: dict | None = None):
    req = urllib.request.Request(
        base.rstrip("/") + path,
        data=json.dumps(payload).encode() if payload else None,
        headers={"Authorization": auth, "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def main() -> int:
    base = os.environ.get("CONFLUENCE_BASE_URL", "")   # e.g. https://yourcompany.atlassian.net/wiki
    user = os.environ.get("CONFLUENCE_USER", "")
    token = os.environ.get("CONFLUENCE_TOKEN", "")
    space = os.environ.get("CONFLUENCE_SPACE", "IT")
    if not (base and user and token):
        print("confluence: config absent (CONFLUENCE_BASE_URL/USER/TOKEN) — skipping, not an error")
        return 0

    auth = "Basic " + b64encode(f"{user}:{token}".encode()).decode()
    mp = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    body = storage_body(mp)

    try:
        q = urllib.parse.urlencode({"title": PAGE_TITLE, "spaceKey": space, "expand": "version"})
        found = api(base, auth, "GET", f"/rest/api/content?{q}").get("results", [])
        if found:
            page = found[0]
            api(base, auth, "PUT", f"/rest/api/content/{page['id']}", {
                "id": page["id"], "type": "page", "title": PAGE_TITLE,
                "version": {"number": page["version"]["number"] + 1},
                "body": {"storage": {"value": body, "representation": "storage"}},
            })
            print(f"confluence: updated page {page['id']} in space {space}")
        else:
            page = api(base, auth, "POST", "/rest/api/content", {
                "type": "page", "title": PAGE_TITLE, "space": {"key": space},
                "body": {"storage": {"value": body, "representation": "storage"}},
            })
            print(f"confluence: created page {page['id']} in space {space}")
        return 0
    except urllib.error.HTTPError as e:
        print(f"confluence: API error {e.code} — {e.read().decode()[:300]}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
