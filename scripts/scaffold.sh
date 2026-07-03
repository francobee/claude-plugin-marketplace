#!/usr/bin/env bash
# Scaffold plugins/<name> with plugin.json, CHANGELOG, example command, and a draft marketplace.json entry.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
NAME="${1:?usage: scaffold.sh <plugin-name>}"

[[ "$NAME" =~ ^[a-z][a-z0-9-]*$ ]] || { echo "✗ plugin name must be kebab-case"; exit 1; }
DIR="$REPO/plugins/$NAME"
[[ -e "$DIR" ]] && { echo "✗ $DIR already exists"; exit 1; }

AUTHOR_NAME="$(git -C "$REPO" config user.name || echo "Your Name")"
AUTHOR_EMAIL="$(git -C "$REPO" config user.email || echo "you@example.com")"
TODAY="$(date +%Y-%m-%d)"

mkdir -p "$DIR/.claude-plugin" "$DIR/commands"

cat > "$DIR/.claude-plugin/plugin.json" <<EOF
{
  "name": "$NAME",
  "displayName": "$NAME",
  "version": "0.1.0",
  "description": "FILL ME IN — one sentence, what this plugin does and for whom.",
  "author": { "name": "$AUTHOR_NAME", "email": "$AUTHOR_EMAIL" }
}
EOF

cat > "$DIR/CHANGELOG.md" <<EOF
# Changelog — $NAME

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com), semver.

## [0.1.0] - $TODAY

### Added
- Initial version.
EOF

cat > "$DIR/commands/example.md" <<'EOF'
---
description: FILL ME IN — what this command does
---

FILL ME IN: the prompt Claude executes when the user runs this command.
EOF

# append a draft entry to marketplace.json (kept sorted by insertion; validate.py enforces the rest)
python3 - "$NAME" "$AUTHOR_NAME" "$AUTHOR_EMAIL" "$REPO" <<'PYEOF'
import json, sys
from pathlib import Path
name, author, email, repo = sys.argv[1:5]
mp_path = Path(repo) / ".claude-plugin" / "marketplace.json"
mp = json.loads(mp_path.read_text())
if any(p["name"] == name for p in mp["plugins"]):
    sys.exit(f"✗ {name} already in marketplace.json")
mp["plugins"].append({
    "name": name,
    "source": f"./plugins/{name}",
    "displayName": name,
    "description": "FILL ME IN — must match plugin.json",
    "version": "0.1.0",
    "author": {"name": author, "email": email},
    "category": "productivity",
    "keywords": [],
    "tags": ["tier-1"],
    "strict": True,
})
mp_path.write_text(json.dumps(mp, indent=2) + "\n")
print(f"✓ added draft entry for {name} to marketplace.json (declared tier-1 — raise it if you add hooks/MCP/scripts)")
PYEOF

echo "✓ scaffolded plugins/$NAME"
echo "Next: fill in descriptions, build your commands/skills, test with:"
echo "  claude --plugin-dir \"$DIR\""
echo "Then validate: python3 scripts/validate.py && python3 scripts/risk_lint.py \"plugins/$NAME\""
