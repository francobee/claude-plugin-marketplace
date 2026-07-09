#!/usr/bin/env bash
# One-command fork bootstrap: writes your answers into marketplace.config.yml, then renders everything via scripts/apply_config.py.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"

prompt() { local var="$1" msg="$2" def="$3"; read -r -p "$msg [$def]: " val; printf -v "$var" '%s' "${val:-$def}"; }

echo "── claude-plugin-marketplace bootstrap ──"
echo "Tip: inside Claude Code, the /setup wizard (marketplace-admin plugin) does all of this plus repo creation,"
echo "branch protection, and Pages. This script is the offline fallback: answers land in marketplace.config.yml."
echo

prompt MARKET   "Marketplace name (used in /plugin install <plugin>@<name>)" "internal"
prompt OWNER    "Owner display name (company or team)" "$(git -C "$REPO" config user.name 2>/dev/null || echo "Your Company")"
prompt EMAIL    "Owner contact email" "$(git -C "$REPO" config user.email 2>/dev/null || echo "it@example.com")"
prompt HANDLES  "GitHub handle(s) for CODEOWNERS, space-separated (e.g. @you @your-it-team)" "@your-github-handle"
prompt DOMAINS  "Extra allowed network domains for plugins, space-separated (blank for none)" ""

echo
echo "── Optional modules ──"
echo "Toggle later in marketplace.config.yml → modules: section."
prompt MOD_FLEET    "Enable fleet/device management (MDM payloads for JumpCloud etc.)? (y/n)" "y"
prompt MOD_CATALOG  "Enable catalog site (browsable HTML page + CATALOG.md)? (y/n)" "y"
prompt MOD_LLM      "Enable LLM security review in CI (requires ANTHROPIC_API_KEY secret)? (y/n)" "y"

[[ "$MARKET" =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "✗ marketplace name must be lowercase kebab-case"; exit 1; }

# Derive org/repo from the origin remote (instance repos are created before init runs).
GH_REPO="$(git -C "$REPO" remote get-url origin 2>/dev/null | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##' || true)"

python3 - "$REPO" "$MARKET" "$OWNER" "$EMAIL" "$GH_REPO" "$HANDLES" "$DOMAINS" "$MOD_FLEET" "$MOD_CATALOG" "$MOD_LLM" <<'EOF'
import re, sys
repo, market, owner, email, gh_repo, handles, domains, mod_fleet, mod_catalog, mod_llm = sys.argv[1:11]
path = f"{repo}/marketplace.config.yml"
lines = open(path).read().splitlines(keepends=True)


def set_scalar(key: str, value: str) -> None:
    rx = re.compile(rf"^(  {key}:)\s*[^#\n]*(#.*)?$")
    for i, line in enumerate(lines):
        m = rx.match(line.rstrip("\n"))
        if m:
            comment = f" {m.group(2)}" if m.group(2) else ""
            lines[i] = f"  {key}: {value}{comment}\n"
            return
    sys.exit(f"✗ key {key!r} not found in marketplace.config.yml")


def set_list(key: str, items: list, quote: bool) -> None:
    for i, line in enumerate(lines):
        m = re.match(rf"^(  {key}:)(\s*\[\])?\s*(#.*)?$", line.rstrip("\n"))
        if not m:
            continue
        comment = f"{' ' + m.group(3) if m.group(3) else ''}"
        end = i + 1
        while end < len(lines) and lines[end].startswith("    - "):
            end += 1
        if items:
            block = [f"  {key}:{comment}\n"] + [f"    - {chr(34) + it + chr(34) if quote else it}\n" for it in items]
        else:
            block = [f"  {key}: []{comment}\n"]
        lines[i:end] = block
        return
    sys.exit(f"✗ key {key!r} not found in marketplace.config.yml")


set_scalar("name", owner)
set_scalar("marketplace_name", market)
set_scalar("contact_email", email)
if gh_repo:
    set_scalar("github_repo", gh_repo)
set_list("codeowners", handles.split(), quote=True)
set_list("network_allowlist", domains.split(), quote=False)
for mod_key, mod_val in [("fleet", mod_fleet), ("catalog_site", mod_catalog), ("llm_review", mod_llm)]:
    set_scalar(mod_key, "true" if mod_val.lower().startswith("y") else "false")
open(path, "w").writelines(lines)
mods_on = [k for k, v in [("fleet", mod_fleet), ("catalog", mod_catalog), ("llm-review", mod_llm)] if v.lower().startswith("y")]
print(f"✓ marketplace.config.yml → name '{market}', owner '{owner}'" + (f", repo '{gh_repo}'" if gh_repo else ""))
print(f"  modules: {', '.join(mods_on) or 'none'}")
EOF

python3 "$REPO/scripts/apply_config.py"
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
echo "  3. Catalog site: keep site.hosting: github-pages (Settings → Pages → Source: GitHub Actions),"
echo "     or set it to 'cloudflare' for free hosting on private repos — see docs/HOSTING.md"
echo "  4. Tell people: /plugin marketplace add <your-org>/<this-repo>"
echo "  Config changes later: edit marketplace.config.yml → python3 scripts/apply_config.py"
