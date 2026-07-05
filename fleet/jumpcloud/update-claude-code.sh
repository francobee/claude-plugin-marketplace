#!/usr/bin/env bash
# JumpCloud command (runs as root): update Claude Code to the fleet pin (fleet.install.version) or latest. Honors auto_update.
set -euo pipefail
cd / # MDM agents run commands from a root-only CWD; sudo'd tools (git/brew/npm) fail getcwd there
# shellcheck disable=SC2050 # rendered constant: config value baked in at render time
[ "true" = "true" ] || { echo "update-claude-code: fleet.install.auto_update is off — skipping"; exit 0; }

CUSER="$(stat -f%Su /dev/console)"
as_user() { sudo -u "$CUSER" -H "$@"; }
NPM="$(as_user bash -lc 'command -v npm' 2>/dev/null || true)"
if [ -z "$NPM" ]; then
  echo "HEALTH FAIL [FLEET-002] Claude Code is not installed (or not on PATH) on the device (npm unavailable — run Install Claude Code first)"
  exit 51
fi
as_user "$NPM" install -g "@anthropic-ai/claude-code@latest" >/dev/null
echo "update-claude-code: now $(as_user bash -lc 'claude --version 2>/dev/null | head -1' || echo unknown)"
