#!/usr/bin/env bash
# Import a public GitHub plugin into plugins/<name> at a pinned commit, with license gate and .upstream.json sidecar.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
URL="${1:?usage: vendor_import.sh <github-url> [subdir]}"
SUBDIR="${2:-}"

UPSTREAM="$(echo "$URL" | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##; s#/$##')"
[[ "$UPSTREAM" =~ ^[^/]+/[^/]+$ ]] || { echo "✗ could not parse owner/repo from $URL"; exit 1; }

TMP="$REPO/.vendor-tmp"
rm -rf "$TMP"
git clone --depth 1 "https://github.com/$UPSTREAM.git" "$TMP"
COMMIT="$(git -C "$TMP" rev-parse HEAD)"

SRC="$TMP${SUBDIR:+/$SUBDIR}"
[[ -d "$SRC" ]] || { echo "✗ subdir $SUBDIR not found in upstream"; rm -rf "$TMP"; exit 1; }

# --- license gate ---
LICENSE="unknown"
for f in "$SRC/LICENSE" "$SRC/LICENSE.md" "$SRC/LICENSE.txt" "$TMP/LICENSE" "$TMP/LICENSE.md" "$TMP/LICENSE.txt"; do
  if [[ -f "$f" ]]; then
    head -5 "$f" | grep -qi "MIT"        && LICENSE="MIT"
    head -5 "$f" | grep -qi "Apache"     && LICENSE="Apache-2.0"
    head -5 "$f" | grep -qi "BSD"        && LICENSE="BSD"
    head -5 "$f" | grep -qi "ISC"        && LICENSE="ISC"
    head -5 "$f" | grep -qi "Mozilla"    && LICENSE="MPL-2.0"
    head -20 "$f" | grep -qiE "GNU (Affero |Lesser )?General Public" && LICENSE="GPL-family"
    break
  fi
done
case "$LICENSE" in
  MIT|Apache-2.0|BSD|ISC|MPL-2.0) echo "✓ license: $LICENSE" ;;
  *) echo "✗ license '$LICENSE' is not on the allowlist (MIT/Apache-2.0/BSD/ISC/MPL-2.0)."
     echo "  GPL-family or unlicensed code needs explicit IT sign-off before vendoring. Stopping."
     rm -rf "$TMP"; exit 1 ;;
esac

# --- determine plugin name ---
if [[ -f "$SRC/.claude-plugin/plugin.json" ]]; then
  NAME="$(python3 -c "import json,sys; print(json.load(open('$SRC/.claude-plugin/plugin.json'))['name'])")"
  UPVER="$(python3 -c "import json,sys; print(json.load(open('$SRC/.claude-plugin/plugin.json')).get('version','0.1.0'))")"
else
  echo "⚠ upstream has no .claude-plugin/plugin.json — importing as a bare skill/command payload."
  NAME="$(basename "$UPSTREAM" | tr '[:upper:]_.' '[:lower:]--')"
  UPVER="0.1.0"
fi
DEST="$REPO/plugins/$NAME"
[[ -e "$DEST" ]] && { echo "✗ plugins/$NAME already exists — this is an update; diff manually and bump version"; rm -rf "$TMP"; exit 1; }

# --- copy payload only (strip upstream CI, tests, VCS) ---
mkdir -p "$DEST"
(cd "$SRC" && tar cf - --exclude .git --exclude .github --exclude tests --exclude test --exclude node_modules .) | (cd "$DEST" && tar xf -)

# --- ensure manifest + changelog ---
mkdir -p "$DEST/.claude-plugin"
if [[ ! -f "$DEST/.claude-plugin/plugin.json" ]]; then
  cat > "$DEST/.claude-plugin/plugin.json" <<EOF
{
  "name": "$NAME",
  "version": "$UPVER",
  "description": "FILL ME IN — imported from $UPSTREAM"
}
EOF
fi
TODAY="$(date +%Y-%m-%d)"
if [[ ! -f "$DEST/CHANGELOG.md" ]]; then
  cat > "$DEST/CHANGELOG.md" <<EOF
# Changelog — $NAME

## [$UPVER] - $TODAY

### Added
- Imported from $UPSTREAM@${COMMIT:0:7} (license: $LICENSE).
EOF
fi

# --- upstream sidecar (drives star counts + upstream-watch) ---
cat > "$DEST/.upstream.json" <<EOF
{
  "repo": "$UPSTREAM",
  "subdir": "${SUBDIR}",
  "commit": "$COMMIT",
  "license": "$LICENSE",
  "importedBy": "$(git -C "$REPO" config user.email || echo unknown)",
  "importedAt": "$TODAY",
  "upstreamVersion": "$UPVER"
}
EOF

rm -rf "$TMP"
echo "✓ vendored $UPSTREAM@${COMMIT:0:7} → plugins/$NAME (license: $LICENSE)"
echo "Next steps (required):"
echo "  1. Add a marketplace.json entry (tags must include \"vendored\" + correct tier)"
echo "  2. REVIEW EVERY FILE — vendored code is reviewed as if written from scratch"
echo "  3. python3 scripts/validate.py && python3 scripts/risk_lint.py plugins/$NAME"
