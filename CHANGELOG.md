# Changelog

Product changelog for the marketplace **template** (instance repos merge these releases — see [docs/UPDATING.md](docs/UPDATING.md)). Individual plugins keep their own `plugins/<name>/CHANGELOG.md`.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: semver, tagged on `main`.

## [1.0.0] - 2026-07-03

### Added
- **Config core**: `marketplace.config.yml` single source of truth; `scripts/apply_config.py` idempotent renderer with `--check` marker validation; strict stdlib YAML-subset loader (`scripts/config_loader.py`) with file:line errors.
- **Error registry**: `errors.json` — every failure mode gets a code, user impact, admin fix; rendered to `docs/TROUBLESHOOTING.md`; all gate scripts exit with registry codes.
- **Zero-config notifications**: `scripts/notify.py` — failures auto-file a deduped GitHub issue (comments on the open issue per error code instead of re-filing); Slack is an optional upgrade.
- **Test harness**: `scripts/test_all.sh` — config render idempotency, all gates, fixture-org end-to-end render, negative tests (broken marker, bad YAML, unarmed notifier), OTEL_LOG denylist.
- **CI**: `config-drift` PR gate (double render + `git diff --exit-code`); post-merge renders config before rebuilding catalog/site; workflow failures notify via `notify.py`; all Actions pinned to commit SHAs with least-privilege permissions.
- **Update channel**: tagged releases + `docs/UPDATING.md` template-remote merge flow for instance repos.

### Changed
- `init.sh` now writes `marketplace.config.yml` and delegates all rendering to `apply_config.py` (no more source-rewriting of `risk_lint.py`).
- `risk_lint.py` reads extra allowlist domains from config at runtime; `build_site.py`/`build_catalog.py` read repo/title from config.

### Baseline (pre-1.0)
- Security-gated marketplace template: schema validation, risk-tier lint, secrets scan, smoke test, Claude LLM review, permission manifests, scorecards, generated CATALOG.md + Pages site, weekly upstream watch, vendoring flow, MDM fleet doc.
