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
run "value CLI: site.hosting (workflow routing)" bash -c 'case "$(python3 scripts/config_loader.py marketplace.config.yml site.hosting github-pages)" in github-pages|cloudflare|none) exit 0;; *) exit 1;; esac'
run "value CLI: empty string falls back to default" bash -c '[ "$(python3 scripts/config_loader.py marketplace.config.yml site.cloudflare_project fallback)" = "fallback" ]'
run "value CLI: empty value + no default prints empty (not an error)" bash -c '[ "$(python3 scripts/config_loader.py marketplace.config.yml site.cloudflare_project)" = "" ]'

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
sed 's/cloudflare_project: acme-plugins/cloudflare_project: acme-plugins-/' tests/fixtures/fixture.config.yml > "$TMP/marketplace.config.yml"
expect_exit 12 "trailing-hyphen cloudflare project → CFG-003" python3 "$TMP/scripts/apply_config.py" --check
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

echo "── 9. scorecard ──"
run "scorecard.py produces valid JSON per plugin" bash -c '
  python3 scripts/scorecard.py >/dev/null 2>&1
  for f in plugins/*/.scorecard.json; do
    python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert set(d)>={\"risk_lint\",\"smoke_test\",\"date\"}, d" "$f" || exit 1
  done
'

echo "── 10. upstream_watch (unit tests) ──"
python3 - <<'EOF' && ok "bump_patch increments correctly" || bad "bump_patch logic broken"
import sys; sys.path.insert(0, "scripts")
from upstream_watch import bump_patch
assert bump_patch("1.0.0") == "1.0.1"
assert bump_patch("0.9.9") == "0.9.10"
assert bump_patch("2.3.4") == "2.3.5"
EOF

echo "── 11. scaffold.sh (creates valid plugin) ──"
SCAFFOLD_TMP="$(mktemp -d)"
rsync -a --exclude .git --exclude __pycache__ --exclude .worktrees "$REPO/" "$SCAFFOLD_TMP/"
(cd "$SCAFFOLD_TMP" && git init -q && git add -A && git commit -q -m "init" && bash scripts/scaffold.sh test-scaffold-plugin) >/dev/null 2>&1
if [ -f "$SCAFFOLD_TMP/plugins/test-scaffold-plugin/.claude-plugin/plugin.json" ]; then
  ok "scaffold.sh creates plugin structure"
else
  bad "scaffold.sh did not create plugin.json"
fi
python3 - "$SCAFFOLD_TMP" <<'EOF' && ok "scaffolded plugin passes smoke_test" || bad "scaffolded plugin fails smoke_test"
import subprocess, sys
r = subprocess.run([sys.executable, f"{sys.argv[1]}/scripts/smoke_test.py", f"{sys.argv[1]}/plugins/test-scaffold-plugin"],
                   capture_output=True, text=True, cwd=sys.argv[1])
sys.exit(r.returncode)
EOF
rm -rf "$SCAFFOLD_TMP"

echo "── 12. risk_lint (externalized rules) ──"
python3 - <<'EOF' && ok "risk_rules.json loads and compiles" || bad "risk_rules.json failed to load"
import json, re, sys
rules = json.loads(open("scripts/schemas/risk_rules.json").read())["rules"]
assert len(rules) >= 15, f"expected ≥15 rules, got {len(rules)}"
for r in rules:
    re.compile(r["pattern"])
    assert r["severity"] in ("high", "medium", "low"), f"bad severity in {r['id']}"
    assert r.get("id") and r.get("message"), f"rule missing id or message"
EOF
python3 - <<'EOF' && ok "subdomain matching blocks evil.allowlisted.com" || bad "subdomain matching broken"
import sys; sys.path.insert(0, "scripts")
from risk_lint import _domain_ok
assert _domain_ok("github.com"), "exact match failed"
assert _domain_ok("www.github.com"), "www prefix failed"
assert not _domain_ok("evil.github.com"), "subdomain should be blocked"
assert not _domain_ok("notgithub.com"), "unrelated domain should be blocked"
EOF

echo "── 13. fleet exit codes (registry consistency) ──"
python3 - <<'EOF' && ok "FLEET exit codes in errors.json referenced in fleet scripts" || bad "FLEET exit code mismatch"
import json, os
errors = json.loads(open("errors.json").read())
fleet_scripts = ""
for root, dirs, files in os.walk("fleet/jumpcloud"):
    for f in files:
        if f.endswith(".sh"):
            fleet_scripts += open(os.path.join(root, f)).read()
for code, info in errors.items():
    if not code.startswith("FLEET-"):
        continue
    if f"[{code}]" not in fleet_scripts:
        raise AssertionError(f"{code} (exit {info['exit']}) not referenced in any fleet script")
EOF

echo "── 14. check_versions edge cases ──"
run "check_versions: base==HEAD is PASS" bash -c 'python3 scripts/check_versions.py HEAD 2>&1 | grep -q PASS'

echo "── 15. schema validation (additionalProperties) ──"
python3 - <<'EOF' && ok "schema rejects unknown plugin.json key" || bad "schema did not reject unknown key"
import json, tempfile, sys
from pathlib import Path
sys.path.insert(0, "scripts")
from schema_validator import validate_file
tmp = Path(tempfile.mkdtemp())
pj = tmp / "plugin.json"
pj.write_text(json.dumps({"name": "test", "version": "1.0.0", "description": "x", "bogusKey": True}))
schema = Path("scripts/schemas/plugin.schema.json")
errs = validate_file(pj, schema)
assert any("bogusKey" in e for e in errs), f"Expected bogusKey rejection, got: {errs}"
EOF

echo "── 16. vendor_import tree hash ──"
VI_TMP="$(mktemp -d)"
(cd "$VI_TMP" && git init -q && mkdir sub && echo hello > sub/file.txt && git add -A && git commit -q -m init)
TH="$(git -C "$VI_TMP" rev-parse 'HEAD:sub')"
[ ${#TH} -eq 40 ] && ok "git rev-parse HEAD:<subdir> returns tree hash" || bad "tree hash computation failed"
grep -q '"treeHash"' scripts/vendor_import.sh && ok "vendor_import.sh records treeHash" || bad "vendor_import.sh missing treeHash"
rm -rf "$VI_TMP"

echo "── 17. analytics compose (roadmap — skips when absent) ──"
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
