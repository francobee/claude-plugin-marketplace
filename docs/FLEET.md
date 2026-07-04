# Fleet rollout (MDM)

Zero-setup Claude Code for every managed Mac: devices get Claude Code installed, the <!-- cfg:company.marketplace_name -->internal<!-- /cfg --> marketplace pre-registered and (optionally) locked, core plugins force-enabled, repo credentials configured, and a scheduled health check that reports problems as error codes — users never touch any of it.

Everything below is **rendered from `marketplace.config.yml`** (the `fleet:` block) into `fleet/` by `scripts/apply_config.py`. Change the config, re-render, re-push — never edit `fleet/` files by hand.

## JumpCloud (first-class)

Four commands run the whole lifecycle. The generated ops sheet at [`fleet/README.md`](../fleet/README.md) mirrors this table with your rendered values.

| # | JumpCloud command | Script (paste from `fleet/jumpcloud/`) | When |
|---|---|---|---|
| 1 | Install Claude Code | `install-claude-code.sh` | new devices (device-group bound) |
| 2 | Push managed settings | `push-managed-settings.sh` | new devices + every settings change |
| 3 | Configure repo access | `configure-repo-access.sh` | once + on PAT rotation |
| 4 | Health check | `health-check.sh` | scheduled, every `fleet.health.interval_hours` |

Console steps, per command: **Commands → + → Mac**, Run As: **root**, paste the script, bind to your device group. For #4 set **Schedule → repeating** at your configured interval. For #3, on the Command Details page use **+ Create Variable**: name `JC_CLAUDE_REPO_PAT`, type String, **Secret Variable ON**, scope Local, value = the PAT — that is the only place the PAT ever lives (never in this repo). JumpCloud injects it by rendering the double-braced `JC_CLAUDE_REPO_PAT` token already present in the script — it is NOT an environment variable, so don't remove that line.

**Reading results:** Commands → Results. Every run prints one line — `HEALTH OK …` or `HEALTH FAIL [CODE] …`. Each code has a meaning, user impact, and fix in [TROUBLESHOOTING](TROUBLESHOOTING.md); the exit code is the registry code, so you can filter failures in the JumpCloud API too. This is the fleet dashboard v1 — no servers involved.

## What the managed settings enforce

The rendered payload lives at [`fleet/managed-settings.json`](../fleet/managed-settings.json) and lands at `/Library/Application Support/ClaudeCode/managed-settings.json` (root-owned, 0644). Driven by config:

- `fleet.strict_marketplaces: true` → devices can only add THIS marketplace (`strictKnownMarketplaces`); the marketplace itself is auto-registered via `extraKnownMarketplaces`.
- `fleet.disable_sideload: true` → `--plugin-dir`/`--mcp-config`-style sideload flags rejected on devices.
- `fleet.enabled_plugins` → force-enabled for everyone (keep this list tiny).
- `fleet.allowed_mcp_servers` → MCP allowlist. **Empty list = unmanaged** (no restriction); a non-empty list restricts devices to exactly those servers (plus the Atlassian Teamwork Graph server when that integration is enabled).
- `telemetry.enabled: false` → the `env` block (OTel metrics) is omitted entirely; devices send nothing.

Managed-settings key names evolve with Claude Code releases: they live in exactly one file (`templates/fleet/managed-settings.json.tmpl`) and `smoke_test.py` pins the known-good key list, so a rename fails CI instead of silently shipping a dead key. Verify against the [settings docs](https://code.claude.com/docs/en/settings) at each major Claude Code release.

## Private-repo access (fine-grained PAT)

1. Create a bot/machine GitHub account with **read-only** access to <!-- cfg:company.github_repo -->francobee/claude-plugin-marketplace<!-- /cfg --> only.
2. GitHub → Settings → Developer settings → **Fine-grained tokens**: single repository, permissions = **Contents: Read-only**. Set an expiry you'll actually honor.
3. On the *Configure repo access* command, create the secret Custom Variable `JC_CLAUDE_REPO_PAT` with the token as its value (String, Secret ON, scope Local) and run the command against the device group.
4. The script installs a git credential **scoped to the marketplace repo URL only** in the console user's `~/.config/claude-marketplace/`.

**Rotation runbook:** issue new PAT → update the `JC_CLAUDE_REPO_PAT` Custom Variable's value → re-run command #3 fleet-wide → revoke old PAT. Health check (#4) flags devices that missed the rotation as `FLEET-004`. Blast radius of a leaked PAT: read-only access to plugin markdown in one repo.

## Staged rollout (THE path)

1. Create a **pilot device group** (IT + a few friendly users). Bind all four commands to it.
2. Watch health-check results for one interval cycle; fix anything red.
3. Re-bind (or duplicate) the commands to the **fleet device group**. Done.

Ship stability knob: `fleet.install.version` in the config pins the Claude Code version fleet-wide (`latest` = follow releases). The health check reports pin mismatches as `FLEET-006`.

## Other MDMs (Jamf, Intune, Kandji, generic)

The payloads are MDM-agnostic; only the delivery mechanism differs:

- macOS target: `/Library/Application Support/ClaudeCode/managed-settings.json` · Linux: `/etc/claude-code/managed-settings.json` · Windows: `C:\ProgramData\ClaudeCode\managed-settings.json`
- Deploy `fleet/managed-settings.json` with your MDM's file-drop, or run `fleet/jumpcloud/push-managed-settings.sh` as a root script — it's plain bash with no JumpCloud dependency.
- Run the install/update/health scripts the same way; pass the PAT via your MDM's secret-variable mechanism instead of `JC_CLAUDE_REPO_PAT`.

## Update cadence

Installed plugins auto-update when the marketplace repo's main branch moves — which only happens through the gated PR flow. Pulling a plugin = removing its entry from marketplace.json via PR.
