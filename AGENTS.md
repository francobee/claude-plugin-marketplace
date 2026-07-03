# AGENTS.md — machine-readable guide for AI agents

You are an AI agent (Claude, ChatGPT, Cursor, Copilot, …) working with this repo: a **security-gated Claude Code plugin marketplace template**. This file tells you exactly how to set it up for a user, submit plugins to it, and operate it. Prefer these runbooks over improvising.

## Repo facts

- **Company config / single source of truth: `marketplace.config.yml`** — marketplace name, owner, CODEOWNERS, network allowlist, integrations, fleet policy. `python3 scripts/apply_config.py` renders everything derived from it.
- Catalog: `.claude-plugin/marketplace.json` (the `name` field is the marketplace name users type in `/plugin install <plugin>@<name>`; `name`/`owner`/authors are rendered from the config — plugin entries are edited by hand)
- One directory per plugin under `plugins/`, each with `.claude-plugin/plugin.json` + `CHANGELOG.md`
- Error registry: `errors.json` — every automation failure exits with a code from it; `docs/TROUBLESHOOTING.md` is generated from it; `scripts/notify.py` files deduped GitHub issues keyed by code
- The gate lives in `scripts/` and `.github/workflows/pr-validation.yml`; humans approve via CODEOWNERS
- All scripts are Python 3 stdlib or bash — no dependencies to install
- Generated files (never hand-edit): `CATALOG.md`, `site/index.html`, `docs/TROUBLESHOOTING.md`, `plugins/*/.scorecard.json`, `plugins/*/.permissions.json`, and every value inside cfg/gen doc markers (see docs/AUTHORING.md, "Config markers")

## Invariants (violating these fails CI)

1. Any change to a plugin's files ⇒ bump semver `version` in BOTH `plugins/<name>/.claude-plugin/plugin.json` and its `.claude-plugin/marketplace.json` entry (keep identical) + add a `## [x.y.z] - YYYY-MM-DD` entry to the plugin's `CHANGELOG.md`.
2. Every marketplace entry declares exactly one risk-tier tag: `tier-1` (markdown only), `tier-2` (read-only shell / allowlisted MCP), `tier-3` (hooks, local processes, `bin/`). `scripts/risk_lint.py` detects the real tier; declared must match.
3. Never commit to `main` — always a branch + PR.
4. No secrets in files, no network destinations outside the allowlist (base list in `scripts/risk_lint.py` + `security.network_allowlist` in the config), no HTML comments or zero-width characters in plugin markdown.
5. Company-specific values change in `marketplace.config.yml` only, then `python3 scripts/apply_config.py` — the `config-drift` CI job rejects hand-edited rendered values.

## Runbook A — set up a new marketplace for the user

Inside Claude Code, prefer the `/setup` wizard (`marketplace-admin` plugin) — it runs this whole runbook interactively, plus branch protection and fleet PAT guidance. The manual path:

Ask the user for (or infer from context): **marketplace name** (lowercase kebab-case, e.g. `acme`), **owner/company name**, **contact email**, **GitHub org/user + repo name**, **CODEOWNERS handle(s)**, **extra allowed network domains** (optional).

```bash
# 1. Create the user's repo from this template (private is fine) and clone it
gh repo create <org>/<repo> --template francobee/claude-plugin-marketplace --private --clone
cd <repo>

# 2. Bootstrap (non-interactive: answers piped in order — name, owner, email, handles, domains)
printf '<marketplace-name>\n<Owner Name>\n<email>\n<@handle1 @handle2>\n<domains-or-empty>\n' | ./init.sh

# 3. Verify, commit, push
python3 scripts/validate.py && python3 scripts/risk_lint.py && python3 scripts/smoke_test.py
git add -A && git commit -m "chore: bootstrap marketplace" && git push

# 4. Enable the catalog site + re-run the pages workflow (first-push run fails by design until Pages exists)
gh api repos/<org>/<repo>/pages -X POST -f build_type=workflow
gh workflow run pages.yml

# 5. Arm the optional gates (ask the user for values; each is fail-soft if skipped)
gh secret set ANTHROPIC_API_KEY        # recommended: enables Claude security review on PRs
gh secret set SLACK_WEBHOOK_URL        # optional: submission pings + publish announcements
gh variable set CONFLUENCE_BASE_URL; gh variable set CONFLUENCE_USER; gh secret set CONFLUENCE_TOKEN  # optional
```

Then tell the user to:
- Fill in `plugins/company-essentials/skills/company-context/SKILL.md` (FILL-ME-IN markers) — or do it with them from what you know of their stack.
- Protect `main` (require PR + Code Owner review + status checks) — needs repo admin in the browser, or `gh api` branch-protection if you have permission.
- Share with their team: `/plugin marketplace add <org>/<repo>`.

## Runbook B — submit a plugin

From a checkout of the user's marketplace repo:

1. `git checkout -b submit/<plugin-name>`
2. New plugin: `./scripts/scaffold.sh <plugin-name>`, then write the commands/skills. Vendor an existing GitHub plugin: `./scripts/vendor_import.sh <github-url> [subdir]`.
3. Apply invariant 1 (version + changelog) and set the correct `tier-N` tag.
4. Validate — fix everything before pushing:
   ```bash
   python3 scripts/validate.py
   python3 scripts/risk_lint.py plugins/<plugin-name>
   python3 scripts/smoke_test.py plugins/<plugin-name>
   python3 scripts/check_versions.py main
   ```
5. Commit `feat(<name>): <what> (v<x.y.z>)`, push, `gh pr create` filling `.github/PULL_REQUEST_TEMPLATE.md` honestly (tier-2/3: itemize every command and endpoint).

Inside Claude Code, the `plugin-dev` plugin's `/submit-plugin` command does all of this.

## Runbook C — operate the marketplace

- **Review a submission PR**: wait for the 6 CI checks; read the `llm-review-report` and `risk-report` artifacts; review the diff as code that will run on every user's machine; merge only via CODEOWNERS-approved review. Post-merge automation handles catalog/site/scorecards/announcements.
- **`upstream-update/<name>` PRs** (weekly bot): the pinned upstream moved; diff is the upstream change re-imported and re-scanned. Review as new code.
- **Pull a plugin**: remove its entry from `.claude-plugin/marketplace.json` via PR (keep the directory). Users lose it on next sync.
- **Health check**: `python3 scripts/scorecard.py && python3 scripts/build_catalog.py` then read the Scorecard column in `CATALOG.md`.

## Verification commands (run before claiming success)

```bash
scripts/test_all.sh                # the whole suite: config, gates, builds, fixtures, negative tests
```

Or piecemeal:

```bash
python3 scripts/apply_config.py --check   # config parses + doc markers intact
python3 scripts/validate.py        # manifests + catalog consistency
python3 scripts/risk_lint.py       # dangerous patterns + tier detection
python3 scripts/smoke_test.py      # structure: frontmatter, refs, JSON configs
python3 scripts/build_catalog.py && python3 scripts/build_site.py  # regenerate outputs
```

Human-oriented docs: [README](README.md) · [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md) · [docs/AUTHORING.md](docs/AUTHORING.md) · [docs/VENDORING.md](docs/VENDORING.md) · [docs/SECURITY.md](docs/SECURITY.md) · [docs/FLEET.md](docs/FLEET.md)
