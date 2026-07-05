#!/usr/bin/env bash
# JumpCloud command (runs as root): install node + gh via Homebrew and Claude Code via npm for the console user. Idempotent; silent for the user.
set -euo pipefail
cd / # MDM agents run commands from a root-only CWD; sudo'd tools (git/brew/npm) fail getcwd there

CUSER="$(stat -f%Su /dev/console)"
as_user() { sudo -u "$CUSER" -H "$@"; }

BREW=""
for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$b" ] && BREW="$b" && break; done
# shellcheck disable=SC2050 # rendered constant: config value baked in at render time
if [ "true" = "true" ] && [ -z "$BREW" ]; then
  echo "HEALTH FAIL [FLEET-001] Homebrew is missing on the device — the install script needs it for node and gh"
  exit 50
fi

want_brew() { # want_brew <formula> <enabled>
  [ "$2" = "true" ] || return 0
  [ -n "$BREW" ] || return 0
  as_user "$BREW" list --versions "$1" >/dev/null 2>&1 || as_user "$BREW" install --quiet "$1" >/dev/null
}
want_brew node "true"
want_brew gh "true"

NPM="$(as_user bash -lc 'command -v npm' 2>/dev/null || true)"
if [ -z "$NPM" ]; then
  echo "HEALTH FAIL [FLEET-002] Claude Code is not installed (or not on PATH) on the device (npm unavailable — enable fleet.install.node)"
  exit 51
fi
if ! as_user bash -lc 'command -v claude' >/dev/null 2>&1; then
  as_user "$NPM" install -g "@anthropic-ai/claude-code@latest" >/dev/null
fi
echo "install-claude-code: OK ($(as_user bash -lc 'claude --version 2>/dev/null | head -1' || echo installed))"
