# Changelog

Product changelog for the marketplace **template** (instance repos merge these releases — see [docs/UPDATING.md](docs/UPDATING.md)). Individual plugins keep their own `plugins/<name>/CHANGELOG.md`.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: semver, tagged on `main`.

## [1.0.1] - 2026-07-03

### Fixed
- `secrets-scan` CI job: added `pull-requests: read` permission — gitleaks-action got 403 on private instance repos (public repos masked it).
- `test_all.sh` managed-settings assertions now derive from `marketplace.config.yml` instead of hardcoding the template's own values — they failed on any renamed instance.

### Changed
- Documentation rewritten audience-first (use / run your own / add a plugin / contribute); `/setup` wizard is the primary setup path.

### Added
- `CONTRIBUTING.md` (dev loop, ground rules, release process, maintainer-application path) and `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1).

## [1.0.0] - 2026-07-03

### Added
- **Config core**: `marketplace.config.yml` single source of truth; `scripts/apply_config.py` idempotent renderer with `--check` marker validation; strict stdlib YAML-subset loader (`scripts/config_loader.py`) with file:line errors.
- **Error registry**: `errors.json` — every failure mode gets a code, user impact, admin fix; rendered to `docs/TROUBLESHOOTING.md`; all gate scripts exit with registry codes.
- **Zero-config notifications**: `scripts/notify.py` — failures auto-file a deduped GitHub issue (comments on the open issue per error code instead of re-filing); Slack is an optional upgrade.
- **Test harness**: `scripts/test_all.sh` — config render idempotency, all gates, fixture-org end-to-end render, negative tests (broken marker, bad YAML, unarmed notifier), OTEL_LOG denylist.
- **CI**: `config-drift` PR gate (double render + `git diff --exit-code`); post-merge renders config before rebuilding catalog/site; workflow failures notify via `notify.py`; all Actions pinned to commit SHAs with least-privilege permissions.
- **Fleet (MDM)**: `templates/fleet/managed-settings.json.tmpl` — all Claude Code settings keys in one place (key list pinned by `smoke_test.py` as a rename alarm); generated JumpCloud lifecycle scripts (install, push settings, update with version pin, repo access via `JC_CLAUDE_REPO_PAT` secret env var — PAT never in the repo, health check whose exit code is the registry code = fleet dashboard v1); `FLEET-001..007` error codes with per-device fixes; JumpCloud-first `docs/FLEET.md` with PAT rotation runbook and staged pilot→fleet rollout.
- **marketplace-admin plugin**: `/setup` — creates and configures a private company instance end-to-end (repo from template, plain-English interview, branch protection, Pages, PAT guidance; never touches secret values); `/status` — plain-English installation health checklist; admin ops skill with binding safe-gh policy.
- **Update channel**: tagged releases + `docs/UPDATING.md` template-remote merge flow for instance repos.

### Changed
- `init.sh` now writes `marketplace.config.yml` and delegates all rendering to `apply_config.py` (no more source-rewriting of `risk_lint.py`).
- `risk_lint.py` reads extra allowlist domains from config at runtime; `build_site.py`/`build_catalog.py` read repo/title from config.

### Baseline (pre-1.0)
- Security-gated marketplace template: schema validation, risk-tier lint, secrets scan, smoke test, Claude LLM review, permission manifests, scorecards, generated CATALOG.md + Pages site, weekly upstream watch, vendoring flow, MDM fleet doc.
