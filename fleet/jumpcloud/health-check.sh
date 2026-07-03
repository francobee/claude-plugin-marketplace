#!/usr/bin/env bash
# JumpCloud command (runs as root, schedule every 6h): Claude Code device health.
# Output contract: one line "HEALTH OK …" or "HEALTH FAIL [CODE] …" + the registry exit code — read it in
# JumpCloud command results; codes map to docs/TROUBLESHOOTING.md. Silent for end users by design.
# Test hooks (harness only): HC_SKIP="claude version settings marketplace repo" skips checks;
# HC_REPO_URL overrides the repo URL; HC_SETTINGS overrides the managed-settings path.
set -uo pipefail

MARKET="internal"
REPO_URL="${HC_REPO_URL:-https://github.com/francobee/claude-plugin-marketplace}"
EXPECTED_SHA="f8e4168ca5459baac8d3a84399509c4b1829e0599fe1c43cac9574fc1d14cf5d"
VERSION_PIN="latest"
TELEMETRY_ENDPOINT=""
SETTINGS="${HC_SETTINGS:-/Library/Application Support/ClaudeCode/managed-settings.json}"

SKIP="${HC_SKIP:-}"
skip() { case " $SKIP " in *" $1 "*) return 0;; *) return 1;; esac; }
FAIL_EXIT=0; FAIL_MSG=""
note_fail() { if [ "$FAIL_EXIT" -eq 0 ]; then FAIL_EXIT="$1"; FAIL_MSG="$2"; fi; }

CUSER="$(stat -f%Su /dev/console 2>/dev/null || echo root)"
UHOME="$(dscl . -read "/Users/$CUSER" NFSHomeDirectory 2>/dev/null | awk '{print $2}')"
# Root (the JumpCloud context) acts as the console user; non-root (local testing) runs directly.
as_user() { if [ "$(id -u)" -eq 0 ] && [ "$CUSER" != "root" ]; then sudo -u "$CUSER" -H "$@"; else "$@"; fi; }

# 1. Claude Code installed
CLAUDE_VERSION=""
if ! skip claude; then
  if as_user bash -lc 'command -v claude' >/dev/null 2>&1; then
    CLAUDE_VERSION="$(as_user bash -lc 'claude --version 2>/dev/null' | head -1 | awk '{print $1}')"
  else
    note_fail 51 "[FLEET-002] Claude Code is not installed (or not on PATH) on the device"
  fi
fi

# 2. Version pin
if ! skip version && [ "$VERSION_PIN" != "latest" ] && [ -n "$CLAUDE_VERSION" ] && [ "$CLAUDE_VERSION" != "$VERSION_PIN" ]; then
  note_fail 55 "[FLEET-006] Claude Code version on the device does not match the fleet pin (fleet.install.version) (device: $CLAUDE_VERSION, pin: $VERSION_PIN)"
fi

# 3. Managed settings present + unchanged
if ! skip settings; then
  if [ ! -f "$SETTINGS" ] || [ "$(shasum -a 256 "$SETTINGS" | awk '{print $1}')" != "$EXPECTED_SHA" ]; then
    note_fail 52 "[FLEET-003] managed-settings.json is missing or drifted on the device (hash mismatch with the rendered payload)"
  fi
fi

# 4. Marketplace registered (only checkable after the user's first launch)
if ! skip marketplace; then
  KNOWN="$UHOME/.claude/plugins/known_marketplaces.json"
  if [ -f "$KNOWN" ] && ! grep -q "\"$MARKET\"" "$KNOWN"; then
    note_fail 54 "[FLEET-005] The company marketplace is not registered on the device (user has launched Claude Code, but the marketplace is absent)"
  fi
fi

# 5. Marketplace repo reachable with the device credential
if ! skip repo; then
  if ! as_user env GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code "$REPO_URL" HEAD >/dev/null 2>&1; then
    note_fail 53 "[FLEET-004] The marketplace repo is unreachable from the device (network or credential problem)"
  fi
fi

# Optional heartbeat to the analytics collector (fleet plane: device-identified, ZERO usage content).
# No-ops silently until telemetry.endpoint is configured (roadmap).
case "$TELEMETRY_ENDPOINT" in
  *://*:[0-9]*)
    HB_URL="${TELEMETRY_ENDPOINT%:*}:4318/v1/metrics"
    SERIAL="$(ioreg -rd1 -c IOPlatformExpertDevice 2>/dev/null | awk -F'"' '/IOPlatformSerialNumber/{print $4}')"
    STATUS=$([ "$FAIL_EXIT" -eq 0 ] && echo ok || echo fail)
    ERRCODE="$(printf '%s' "$FAIL_MSG" | sed -n 's/^\[\([A-Z0-9-]*\)\].*/\1/p')"
    NOW="$(date +%s)000000000"
    curl -s -o /dev/null --max-time 5 -X POST "$HB_URL" -H 'Content-Type: application/json' -d '{
      "resourceMetrics":[{"resource":{"attributes":[
        {"key":"device.serial","value":{"stringValue":"'"$SERIAL"'"}},
        {"key":"device.hostname","value":{"stringValue":"'"$(hostname)"'"}},
        {"key":"claude.version","value":{"stringValue":"'"$CLAUDE_VERSION"'"}}]},
        "scopeMetrics":[{"metrics":[{"name":"claude.fleet.health","gauge":{"dataPoints":[{
          "asInt":"'"$FAIL_EXIT"'","timeUnixNano":"'"$NOW"'",
          "attributes":[{"key":"health.status","value":{"stringValue":"'"$STATUS"'"}},
                        {"key":"error.code","value":{"stringValue":"'"$ERRCODE"'"}}]}]}}]}]}]}' || true
    ;;
esac

if [ "$FAIL_EXIT" -ne 0 ]; then
  echo "HEALTH FAIL $FAIL_MSG"
  exit "$FAIL_EXIT"
fi
echo "HEALTH OK claude=${CLAUDE_VERSION:-unchecked} market=$MARKET"
