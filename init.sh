#!/usr/bin/env bash
# One-command fork bootstrap: rename the marketplace, set the owner, CODEOWNERS handle, and network allowlist domains.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"

prompt() { local var="$1" msg="$2" def="$3"; read -r -p "$msg [$def]: " val; printf -v "$var" '%s' "${val:-$def}"; }

echo "── claude-plugin-marketplace bootstrap ──"
echo "Answer a few questions; everything is a plain-text replace you can review with git diff."
echo

prompt MARKET   "Marketplace name (used in /plugin install <plugin>@<name>)" "internal"
prompt OWNER    "Owner display name (company or team)" "$(git -C "$REPO" config user.name 2>/dev/null || echo "Your Company")"
prompt EMAIL    "Owner contact email" "$(git -C "$REPO" config user.email 2>/dev/null || echo "it@example.com")"
prompt HANDLES  "GitHub handle(s) for CODEOWNERS, space-separated (e.g. @you @your-it-team)" "@your-github-handle"
prompt DOMAINS  "Extra allowed network domains for plugins, space-separated (blank for none)" ""

[[ "$MARKET" =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "✗ marketplace name must be lowercase kebab-case"; exit 1; }

python3 - "$REPO" "$MARKET" "$OWNER" "$EMAIL" <<'EOF'
import json, sys
repo, market, owner, email = sys.argv[1:5]
path = f"{repo}/.claude-plugin/marketplace.json"
mp = json.load(open(path))
mp["name"] = market
mp["owner"] = {"name": owner, "email": email}
for e in mp.get("plugins", []):
    e["author"] = {"name": owner, "email": email}
json.dump(mp, open(path, "w"), indent=2, ensure_ascii=False)
open(path, "a").write("\n")
print(f"✓ marketplace.json → name '{market}', owner '{owner}'")
EOF

# CODEOWNERS: swap every handle on the ownership lines
python3 - "$REPO" "$HANDLES" <<'EOF'
import re, sys
repo, handles = sys.argv[1:3]
path = f"{repo}/.github/CODEOWNERS"
out = []
for line in open(path):
    if line.strip() and not line.startswith("#"):
        pattern = line.split()[0]
        out.append(f"{pattern} {handles}\n")
    else:
        out.append(line)
open(path, "w").writelines(out)
print(f"✓ CODEOWNERS → {handles}")
EOF

# Network allowlist: append extra domains to risk_lint.py
if [[ -n "$DOMAINS" ]]; then
  python3 - "$REPO" $DOMAINS <<'EOF'
import re, sys
repo, domains = sys.argv[1], sys.argv[2:]
path = f"{repo}/scripts/risk_lint.py"
src = open(path).read()
m = re.search(r'NETWORK_ALLOWLIST = \(([^)]*)\)', src)
existing = m.group(1)
added = "".join(f' "{d}",' for d in domains if f'"{d}"' not in existing)
src = src.replace(m.group(0), f'NETWORK_ALLOWLIST = ({existing.rstrip(", ")},{added})', 1)
open(path, "w").write(src)
print(f"✓ risk_lint.py allowlist += {' '.join(domains)}")
EOF
fi

python3 "$REPO/scripts/build_catalog.py"
python3 "$REPO/scripts/build_site.py"
python3 "$REPO/scripts/validate.py"

echo
echo "Done. Review with: git diff"
echo "Next steps:"
echo "  1. Fill in plugins/company-essentials/skills/company-context/SKILL.md (the FILL-ME-IN markers)"
echo "  2. Push, then add repo secrets to arm the optional gates/announcements:"
echo "     ANTHROPIC_API_KEY (LLM security review), SLACK_WEBHOOK_URL (announcements),"
echo "     CONFLUENCE_BASE_URL/USER/TOKEN vars+secret (Confluence catalog page)"
echo "  3. Enable GitHub Pages (Settings → Pages → Source: GitHub Actions) for the catalog site"
echo "  4. Tell people: /plugin marketplace add <your-org>/<this-repo>"
