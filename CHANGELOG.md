# Changelog

Product changelog for the marketplace **template** (instance repos merge these releases — see [docs/UPDATING.md](docs/UPDATING.md)). Individual plugins keep their own `plugins/<name>/CHANGELOG.md`.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: semver, tagged on `main`.

## [1.2.1] - 2026-07-09

### Fixed
- **`.gitleaks.toml`: removed the `jumpcloud-api-key` rule** — its pattern (40-char hex, entropy ≥ 3.5) matches git commit SHAs, so SHA-pinned GitHub Actions references (`uses: …@<sha>`) in ordinary commits were flagged as leaked keys and failed `secrets-scan`. JumpCloud API keys are shape-identical to git SHAs, making the rule false-positive-by-construction in any git repo; prefix-anchored rules (Anthropic, Atlassian, Slack) are unaffected and remain.

## [1.2.0] - 2026-07-09

Upstreamed from live operation of the Optibus instance (built there across instance PRs #17–#21, battle-tested in production).

### Added
- **Optional modules**: `modules.fleet` / `modules.catalog_site` / `modules.llm_review` config flags gate the fleet payloads, catalog/site builds, and CI LLM review. `init.sh` and the `/setup` wizard (Quick mode question 5; Advanced walks the block first) ask which modules to enable; **marketplace-admin 1.1.1**.
- **JSON Schema gate**: stdlib-only `scripts/schema_validator.py` validates `marketplace.json` and every `plugin.json` against tightened schemas (`additionalProperties: false`, typed author blocks) before the imperative checks in `validate.py`.
- **ShellCheck CI job** on all shell scripts (`-S error`), part of pr-validation.
- **Vendored-plugin provenance**: `vendor_import.sh` and `upstream_watch.py` record a git `treeHash` in `.upstream.json` — content-addressed proof of what was imported, not just the commit pointer.
- **Externalized risk rules**: `risk_lint.py` patterns live in `scripts/schemas/risk_rules.json`.
- `.gitleaks.toml` with Anthropic/JumpCloud key patterns extending the default ruleset.
- `post-merge.yml` gains `workflow_dispatch` for manual re-triggers against current main.
- `pages.yml` failure now auto-files a `CI-002` issue; Slack notify in `pr-notify.yml` respects `integrations.slack.enabled`; `test_all.sh` grows to 55 checks.

### Fixed
- `pr-validation.yml`: unquoted colon in the llm-review skip notice made the workflow file invalid YAML — on an instance this silently disabled ALL PR validation repo-wide. (Found live; the skip notice is now a block scalar.)
- `smoke_test.py`: resolve CLI target paths — on macOS, `mktemp` paths (`/var/...`) vs the resolved repo root (`/private/var/...`) made `relative_to()` raise; the scaffold check passed on Linux CI but failed on every Mac.
- `llm_review.py` warns when truncating oversized diffs (malicious content could hide past the review boundary); clearer SKIPPED notice when unarmed.

## [1.1.7] - 2026-07-07

### Fixed
- **Post-merge publishing failed on hardened repos** (`GH006: Protected branch update failed`, auto-filed as `CI-001`): branch protection from `/setup` step 6 also blocks the post-merge bot's catalog/scorecard refresh push to `main`, and GitHub doesn't allow the Actions app as a ruleset bypass actor on personal repos. The publish job now pushes with an optional `PUBLISH_PUSH_TOKEN` secret (fine-grained admin PAT, single repo, Contents: Read+Write) and falls back to the default bot token when unset — zero change for unprotected instances. Documented in `docs/SECURITY.md` (hardening table) and the `CI-001` registry fix.

## [1.1.6] - 2026-07-06

### Fixed
- **Fleet credential only matched the suffix-less repo URL, but Claude Code clones marketplaces with a `.git` suffix** — git's URL matching treats the two as different paths, so employee devices (no owner keychain to fall back on) would still fail `claude plugin marketplace add` even after a successful *Configure repo access* run. The credentials file now carries both URL forms and the gitconfig registers `helper` + `useHttpPath` for both; the health check probes the `.git` form Claude Code actually uses. Found in post-success verification on a pilot device; owner machines mask the gap via their keychain helper.

## [1.1.5] - 2026-07-05

### Fixed
- **`configure-repo-access.sh` no longer sudos to the console user at all**: the git getcwd failure (exit 128) persisted on a real device even with `cd /`, so the script now writes the user's git config as root via `git config --file "$UHOME/.gitconfig"` — the exact file `--global` would edit — and chowns it back, mirroring how the credentials file is written. No user-context process remains, making the script immune to the MDM agent's sudo execution-context quirks.

## [1.1.4] - 2026-07-05

### Fixed
- **`sudo -u` steps in fleet scripts failed with `fatal: Unable to read current working directory: Permission denied`** (exit 128): the JumpCloud agent executes commands from a root-only working directory, which the console user can't read — git/brew/npm all call `getcwd()` and die. All five fleet scripts now `cd /` first. Found live on the third real run of the *Configure repo access* command (the PAT injection itself worked).

## [1.1.3] - 2026-07-05

### Fixed
- **JumpCloud console refused to save the 1.1.2 fleet script** ("Failed to update command"): JumpCloud validates `{{ }}` tokens in the command body on save, and the unrendered-token guard's literal `*"{{"*` pattern is an unpaired double brace. The guard now builds the braces at runtime (`B='{'` → `"$B$B"`), so the only literal double-braced text in the body is the real `JC_CLAUDE_REPO_PAT` token. Behavior unchanged.

## [1.1.2] - 2026-07-04

### Fixed
- **Fleet PAT never reached devices on JumpCloud** (found on the first live fleet run — exit 56 / FLEET-007 despite a correctly configured secret): JumpCloud delivers Custom Variables by mustache-rendering the double-braced `JC_CLAUDE_REPO_PAT` token into the command body (auto-single-quoted at runtime), never as environment variables, but `configure-repo-access.sh` only checked the env var. The script now reads the rendered token (guarding against an unrendered `{{` when the variable is missing) and keeps the env-var path as the generic-MDM fallback. `docs/FLEET.md`, the fleet README, and the `FLEET-007` registry entry now describe the real console flow: **+ Create Variable → String → Secret Variable ON → scope Local**.

## [1.1.1] - 2026-07-04

### Fixed
- **User tutorial install example named a nonexistent plugin on real instances**: the `tutorial-user-install` gen block hardcoded `company-essentials` (the template's seed-plugin name), so a copy-pasting user on any bootstrapped instance got `Plugin not found`. New template placeholder `{{catalog.example_plugin}}` renders the first plugin from `.claude-plugin/marketplace.json` (falls back to `company-essentials` when no manifest exists). Found by a live end-to-end user-journey test.
- `docs/TUTORIAL-USER.md`: "updates are automatic" now says updates land on the next catalog refresh (restart / within a day), not the instant of publish — matches observed behavior.

## [1.1.0] - 2026-07-03

### Added
- **Free catalog-site hosting**: `site.hosting: github-pages | cloudflare | none` — new `site-cloudflare.yml` workflow deploys to Cloudflare Pages' free plan (works for private repos; dashboard-connected or CI mode via `CLOUDFLARE_API_TOKEN`/`CLOUDFLARE_ACCOUNT_ID`); `pages.yml` now skips cleanly when the instance isn't on GitHub Pages; registry code `CI-003`; `docs/HOSTING.md` decision table + walkthroughs.
- **Non-technical tutorials**: `docs/TUTORIAL-ADMIN.md` (set it up from the Claude desktop app — the wizard does the work) and `docs/TUTORIAL-USER.md` (install and use plugins, zero jargon). Both render instance-specific values via config markers.
- `config_loader.py` value mode: `config_loader.py <file> <dotted.path> [default]` — used by workflows to route on config; empty-string values fall back to the default.
- **Repo hardening baseline**: `.github/dependabot.yml` (weekly grouped PRs refreshing the SHA-pinned actions), a "Repo hardening" section in `docs/SECURITY.md` (protection, actions allowlist, plan-wall honesty — and why repo-level SHA-pin *enforcement* must stay off: it breaks GitHub's own composite Pages actions), and the wizard now applies these settings and degrades gracefully when GitHub's Free plan refuses branch protection on private repos.

### Changed
- **marketplace-admin 1.1.0**: `/setup` gains Quick mode (4 questions, safe defaults, full plain-English summary before writing) vs Advanced mode (every key with its one-line description); self-healing `gh` preflight; hosting-aware site step with graceful Pages→Cloudflare fallback; bootstrap PR gated + merged before protection/site publish; repo-settings hardening in step 6 with plan-wall fallback; `/status` site + protection checks follow the config and detect the plan wall.

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
