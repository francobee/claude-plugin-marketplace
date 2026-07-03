#!/usr/bin/env bash
# Local verification harness — config core, all gates, builds, fixture-org e2e, negative tests. Green here = shippable.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1

PASS=0; FAIL=0; FAILED=()
ok()   { PASS=$((PASS+1)); printf '  ✓ %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); FAILED+=("$1"); printf '  ✗ %s\n' "$1"; }
run()  { local desc="$1"; shift; if "$@" >/tmp/test_all.last 2>&1; then ok "$desc"; else bad "$desc"; sed 's/^/      /' /tmp/test_all.last | tail -20; fi; }
expect_exit() { # expect_exit <code> <desc> <cmd…>
  local want="$1" desc="$2"; shift 2
  "$@" >/tmp/test_all.last 2>&1; local got=$?
  if [ "$got" -eq "$want" ]; then ok "$desc (exit $got)"; else bad "$desc — wanted exit $want, got $got"; sed 's/^/      /' /tmp/test_all.last | tail -10; fi
}

echo "── 1. config core ──"
run "config parses (strict YAML subset)"       python3 scripts/config_loader.py marketplace.config.yml
run "apply_config --check (markers intact)"    python3 scripts/apply_config.py --check
run "apply_config renders"                     python3 scripts/apply_config.py
run "value CLI: site.hosting (workflow routing)" bash -c '[ "$(python3 scripts/config_loader.py marketplace.config.yml site.hosting github-pages)" = "github-pages" ]'
run "value CLI: empty string falls back to default" bash -c '[ "$(python3 scripts/config_loader.py marketplace.config.yml site.cloudflare_project fallback)" = "fallback" ]'

echo "── 2. render idempotency (double run) ──"
sum_managed() { python3 scripts/apply_config.py --list | while read -r f; do [ -f "$f" ] && shasum "$f"; done; }
S1="$(sum_managed)"
python3 scripts/apply_config.py >/dev/null 2>&1
S2="$(sum_managed)"
if [ "$S1" = "$S2" ]; then ok "second render is a no-op"; else bad "second render changed files"; diff <(echo "$S1") <(echo "$S2") | sed 's/^/      /'; fi

echo "── 3. gates ──"
run "validate.py"          python3 scripts/validate.py
run "risk_lint.py"         python3 scripts/risk_lint.py
run "smoke_test.py"        python3 scripts/smoke_test.py
run "check_versions.py"    python3 scripts/check_versions.py
run "permission_manifest"  python3 scripts/permission_manifest.py

echo "── 4. builds ──"
run "build_catalog.py"     python3 scripts/build_catalog.py
run "build_site.py"        python3 scripts/build_site.py

echo "── 4b. fleet payloads (skips when templates/fleet absent) ──"
if [ -d templates/fleet ]; then
  python3 - <<'EOF' && ok "managed-settings: JSON valid + every key tracks the config" || { bad "managed-settings assertions"; sed 's/^/      /' /tmp/test_all.last 2>/dev/null | tail -5; }
import json, sys
sys.path.insert(0, "scripts")
import config_loader
cfg = config_loader.load("marketplace.config.yml")
get = config_loader.get
market = get(cfg, "company.marketplace_name")
ms = json.load(open("fleet/managed-settings.json"))
assert market in ms.get("extraKnownMarketplaces", {}), "marketplace registration missing"
assert ("strictKnownMarketplaces" in ms) == bool(get(cfg, "fleet.strict_marketplaces", True)), "strict key vs config"
assert ms.get("disableSideloadFlags", False) == bool(get(cfg, "fleet.disable_sideload", True)), "sideload key vs config"
want = {f"{p}@{market}": True for p in (get(cfg, "fleet.enabled_plugins", []) or [])}
assert ms["enabledPlugins"] == want, ms["enabledPlugins"]
telemetry_on = bool(get(cfg, "telemetry.enabled", False) and get(cfg, "telemetry.endpoint", ""))
assert ("env" in ms) == telemetry_on, "env must exist iff telemetry armed"
assert ("allowedMcpServers" in ms) == bool(get(cfg, "fleet.allowed_mcp_servers", []) or []), "empty allowlist must be omitted (would block everything)"
EOF
  run "push script embeds the payload sha" bash -c 'grep -q "$(shasum -a 256 fleet/managed-settings.json | awk "{print \$1}")" fleet/jumpcloud/push-managed-settings.sh'
  expect_exit 52 "health-check: settings missing → FLEET-003"   env HC_SKIP="claude version marketplace repo" HC_SETTINGS=/nonexistent bash fleet/jumpcloud/health-check.sh
  expect_exit 53 "health-check: repo unreachable → FLEET-004"   env HC_SKIP="claude version settings marketplace" HC_REPO_URL=https://github.invalid/nope/nope GIT_TERMINAL_PROMPT=0 bash fleet/jumpcloud/health-check.sh
  expect_exit 0  "health-check: reachable repo + claude present" env HC_SKIP="settings marketplace version" bash fleet/jumpcloud/health-check.sh
else
  echo "  · no templates/fleet yet — skipped"
fi

echo "── 5. fixture-org end-to-end (Acme) ──"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
rsync -a --exclude .git --exclude __pycache__ --exclude .worktrees "$REPO/" "$TMP/"
cp tests/fixtures/fixture.config.yml "$TMP/marketplace.config.yml"
run "fixture renders"      python3 "$TMP/scripts/apply_config.py"
grep -q '"name": "acme"' "$TMP/.claude-plugin/marketplace.json" && ok "marketplace.json → acme" || bad "marketplace.json missing acme rename"
grep -q '@acme-it @acme-sec' "$TMP/.github/CODEOWNERS" && ok "CODEOWNERS → acme handles" || bad "CODEOWNERS not re-rendered"
grep -q 'plugin-dev@acme' "$TMP/README.md" && ok "README quickstart → @acme" || bad "README gen block not re-rendered"
grep -q 'marketplace add acme-corp/claude-plugins' "$TMP/README.md" && ok "README quickstart → acme repo" || bad "README repo not re-rendered"
run "fixture validate.py"  python3 "$TMP/scripts/validate.py"
run "fixture risk_lint.py (allowlist from config)" python3 "$TMP/scripts/risk_lint.py"
[ "$(python3 "$TMP/scripts/config_loader.py" "$TMP/marketplace.config.yml" site.hosting github-pages)" = "cloudflare" ] \
  && ok "fixture routes site deploys to cloudflare" || bad "fixture site.hosting not readable by workflows"
if [ -d templates/fleet ]; then
  python3 - "$TMP" <<'EOF' && ok "fixture fleet: acme plugin pin + MCP allowlist" || bad "fixture fleet assertions failed"
import json, sys
ms = json.load(open(f"{sys.argv[1]}/fleet/managed-settings.json"))
assert ms["enabledPlugins"] == {"company-essentials@acme": True}, ms["enabledPlugins"]
assert {"serverName": "github"} in ms.get("allowedMcpServers", []), ms.get("allowedMcpServers")
EOF
  python3 - "$TMP" <<'EOF' && ok "fixture fleet: telemetry on ⇒ env present; strict off ⇒ lockdown gone" || bad "fleet config-toggle assertions failed"
import json, subprocess, sys
tmp = sys.argv[1]
cfg = open(f"{tmp}/marketplace.config.yml").read()
cfg = cfg.replace("telemetry:\n  enabled: false", "telemetry:\n  enabled: true")
cfg = cfg.replace('endpoint: ""', 'endpoint: "http://collector.acme.internal:4317"')
cfg = cfg.replace("strict_marketplaces: true", "strict_marketplaces: false")
open(f"{tmp}/marketplace.config.yml", "w").write(cfg)
subprocess.run([sys.executable, f"{tmp}/scripts/apply_config.py"], check=True, capture_output=True)
ms = json.load(open(f"{tmp}/fleet/managed-settings.json"))
assert "strictKnownMarketplaces" not in ms, "strict off must drop lockdown key"
assert ms["env"]["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://collector.acme.internal:4317", ms.get("env")
assert ms["env"]["CLAUDE_CODE_ENABLE_TELEMETRY"] == "1"
assert not any("OTEL_LOG" in k for k in ms["env"]), "no logs pipeline ever"
EOF
  cp tests/fixtures/fixture.config.yml "$TMP/marketplace.config.yml"
  python3 "$TMP/scripts/apply_config.py" >/dev/null 2>&1
fi
python3 - "$TMP" <<'EOF' && ok "fixture allowlist includes internal.acme.com" || bad "config allowlist not picked up by risk_lint"
import importlib.util, sys
sys.path.insert(0, f"{sys.argv[1]}/scripts")
spec = importlib.util.spec_from_file_location("rl", f"{sys.argv[1]}/scripts/risk_lint.py")
rl = importlib.util.module_from_spec(spec); spec.loader.exec_module(rl)
sys.exit(0 if "internal.acme.com" in rl.NETWORK_ALLOWLIST else 1)
EOF

echo "── 6. negative tests (must fail with the right registry code) ──"
expect_exit 11 "bad YAML: tab indentation → CFG-002"    python3 scripts/config_loader.py tests/fixtures/bad-tab.yml
expect_exit 11 "bad YAML: flow collection → CFG-002"    python3 scripts/config_loader.py tests/fixtures/bad-flow.yml
cp tests/fixtures/bad-unknown-key.yml "$TMP/marketplace.config.yml"
expect_exit 12 "unknown config key → CFG-003"           python3 "$TMP/scripts/apply_config.py" --check
cp tests/fixtures/fixture.config.yml "$TMP/marketplace.config.yml"
python3 "$TMP/scripts/apply_config.py" >/dev/null 2>&1
sed -i.bak 's|<!-- /gen:readme-quickstart -->||' "$TMP/README.md"
expect_exit 13 "broken doc marker → CFG-004"            python3 "$TMP/scripts/apply_config.py" --check
mv "$TMP/README.md.bak" "$TMP/README.md"
sed -i.bak 's|plugin-dev@acme|plugin-dev@HANDEDIT|' "$TMP/README.md"
python3 "$TMP/scripts/apply_config.py" >/dev/null 2>&1
grep -q 'plugin-dev@acme' "$TMP/README.md" && ok "hand-edit inside gen block reverted by render" || bad "hand-edit survived render"
printf 'OTEL_LOG_EXPORTER {{company.name}}\n' > "$TMP/templates/evil.md"
expect_exit 15 "OTEL_LOG in template → CFG-006"         python3 "$TMP/scripts/apply_config.py" --check
rm -f "$TMP/templates/evil.md"
sed 's/hosting: cloudflare/hosting: dropbox/' tests/fixtures/fixture.config.yml > "$TMP/marketplace.config.yml"
expect_exit 12 "invalid site.hosting → CFG-003"         python3 "$TMP/scripts/apply_config.py" --check
sed 's/cloudflare_project: acme-plugins/cloudflare_project: Not_Kebab/' tests/fixtures/fixture.config.yml > "$TMP/marketplace.config.yml"
expect_exit 12 "invalid site.cloudflare_project → CFG-003" python3 "$TMP/scripts/apply_config.py" --check
cp tests/fixtures/fixture.config.yml "$TMP/marketplace.config.yml"

echo "── 7. notifier (must never break a pipeline) ──"
expect_exit 0 "notify --dry-run"                        python3 scripts/notify.py --code CI-001 --context "test_all dry run" --dry-run
expect_exit 0 "notify with no gh available (silent-fail)" env NOTIFY_GH_BIN=/nonexistent GITHUB_REPOSITORY= python3 scripts/notify.py --code CI-001 --context "unarmed"

echo "── 8. telemetry denylist + shell syntax ──"
if grep -rn "OTEL_LOG" templates/ fleet/ 2>/dev/null | grep -v Binary; then bad "OTEL_LOG found in templates/ or fleet/"; else ok "no OTEL_LOG anywhere in templates/ or fleet/"; fi
SH_OK=1; while IFS= read -r -d '' f; do bash -n "$f" || SH_OK=0; done < <(find . -path ./.git -prune -o -name '*.sh' -print0)
[ "$SH_OK" = 1 ] && ok "bash -n on all shell scripts" || bad "shell syntax errors"
if command -v shellcheck >/dev/null 2>&1; then
  if find . -path ./.git -prune -o -name '*.sh' -print0 | xargs -0 shellcheck -S error; then ok "shellcheck (errors only)"; else bad "shellcheck errors"; fi
else
  echo "  · shellcheck not installed — skipped"
fi

echo "── 9. analytics compose (roadmap — skips when absent) ──"
if [ -f analytics/docker-compose.yml ]; then
  if command -v docker >/dev/null 2>&1; then run "docker compose config" docker compose -f analytics/docker-compose.yml config -q
  else echo "  · docker not available — skipped"; fi
else
  echo "  · no analytics/ yet — skipped"
fi

echo
if [ "$FAIL" -gt 0 ]; then
  echo "test_all: FAIL — $FAIL of $((PASS+FAIL)) checks failed:"
  for f in "${FAILED[@]}"; do echo "  ✗ $f"; done
  exit 1
fi
echo "test_all: PASS — all $PASS checks green"
