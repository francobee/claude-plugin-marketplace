# Claude Code Plugin Marketplace

**Security-gated, self-maintaining, fork-ready.** The trusted internal plugin source for your team — every plugin is schema-validated, risk-linted, secrets-scanned, smoke-tested, and reviewed by Claude for prompt injection before a human approves the merge.

[![pages](https://github.com/francobee/claude-plugin-marketplace/actions/workflows/pages.yml/badge.svg)](https://github.com/francobee/claude-plugin-marketplace/actions/workflows/pages.yml)
[![PR gate](https://img.shields.io/badge/PR%20gate-6%20checks-3fb950)](docs/SECURITY.md)
[![license](https://img.shields.io/github/license/francobee/claude-plugin-marketplace)](LICENSE)
[![template](https://img.shields.io/badge/GitHub-use%20this%20template-8250df)](https://github.com/new?template_name=claude-plugin-marketplace&template_owner=francobee)
[![catalog site](https://img.shields.io/badge/catalog-live%20site-63e69f)](https://francobee.github.io/claude-plugin-marketplace/)

[**Browse the catalog site**](https://francobee.github.io/claude-plugin-marketplace/) · [**Beginner guide**](docs/GETTING-STARTED.md) · [**Set up with an AI agent**](#-set-up-with-an-ai-agent) · [**Security model**](docs/SECURITY.md)

[![Catalog site screenshot](docs/assets/catalog-site.png)](https://francobee.github.io/claude-plugin-marketplace/)

## Why this one

Most marketplaces are a JSON file and vibes. Plugins run inside people's Claude Code sessions with their permissions, and auto-update — one bad merge ships to everyone. This repo is a marketplace **plus the pipeline that makes it trustworthy**:

| | Typical marketplace | This one |
|---|---|---|
| Manifest validation | — | ✔ schema + catalog consistency |
| Version/changelog gate | — | ✔ unbumped versions never ship |
| Secrets scan | — | ✔ gitleaks in CI |
| Static risk lint | — | ✔ dangerous patterns, hidden Unicode, risk tiers |
| Structural smoke test | — | ✔ catches merged-but-broken plugins |
| LLM security review | — | ✔ Claude reads every PR diff for injection/exfiltration |
| Vendored-plugin updates | manual | ✔ weekly watch → auto-update PRs (Renovate-style) |
| Catalog | README table, maybe | ✔ generated CATALOG.md + searchable GitHub Pages site |
| Per-plugin scorecard | — | ✔ scan/smoke/LLM/freshness badges |
| Permission visibility | read the source | ✔ auto-extracted manifest (MCP/tools/shell/endpoints) commented on every PR |
| Fleet rollout docs | — | ✔ MDM pre-registration guide |

## Quick start

<!-- gen:readme-quickstart -->
**Use this marketplace:**

```bash
# inside Claude Code
/plugin marketplace add francobee/claude-plugin-marketplace
/plugin install plugin-dev@internal
```
<!-- /gen:readme-quickstart -->

**Make your own** (fork for your company): read the [beginner guide](docs/GETTING-STARTED.md) — or let an agent do it:

## 🤖 Set up with an AI agent

Paste this into Claude Code, Claude, ChatGPT, or any agent that can run commands — fill in the brackets:

```text
Set up a security-gated Claude Code plugin marketplace for me, based on the template at
https://github.com/francobee/claude-plugin-marketplace

Fetch the raw file AGENTS.md from that repo and follow "Runbook A" exactly.
My details:
- marketplace name: [e.g. acme]
- company/owner:    [e.g. Acme Corp]
- contact email:    [e.g. it@acme.com]
- GitHub repo:      [e.g. acme-org/claude-plugins, private]
- CODEOWNERS:       [e.g. @acme-it-team]
- extra allowed network domains for plugins: [e.g. internal.acme.com — or none]

Also help me fill in plugins/company-essentials/skills/company-context/SKILL.md
with my company's stack, then run the verification commands before telling me it's done.
```

[AGENTS.md](AGENTS.md) is the machine-readable runbook: repo invariants, non-interactive bootstrap, plugin submission, and day-to-day operations — written for agents, honest for humans.

## Submit a plugin

1. Branch off `main` (never commit to main; CODEOWNERS + CI gate every merge).
2. **New plugin:** `./scripts/scaffold.sh my-plugin` (or `/new-plugin` with the plugin-dev plugin).
   **Found something on GitHub:** `./scripts/vendor_import.sh <github-url>` — pinned commit, license allowlist, upstream tracked ([docs/VENDORING.md](docs/VENDORING.md)).
3. Test locally: `claude --plugin-dir plugins/my-plugin`.
4. Run `/submit-plugin` — version bump, changelog, validation, commit, and PR handled for you. By hand instead: [docs/AUTHORING.md](docs/AUTHORING.md).
5. Automated scans + admin approval → merge → catalog, site, and announcements update themselves.

## Rules (CI-enforced)

- Explicit semver everywhere; any file change ⇒ version bump + CHANGELOG entry.
- Every plugin declares a risk tier tag: `tier-1` (markdown only), `tier-2` (read-only shell / allowlisted MCP), `tier-3` (hooks, MCP processes, `bin/` — hardest review).
- No secrets, no pipe-to-shell, no obfuscation, no network outside the allowlist, no hidden Unicode/HTML-comment instructions.

Full threat model and honest caveats: [docs/SECURITY.md](docs/SECURITY.md).

## Managed configuration

Everything company-specific lives in **one file: `marketplace.config.yml`** — marketplace name, owner, CODEOWNERS, network allowlist, integrations, fleet policy. Edit it, run `python3 scripts/apply_config.py`, and every derived file (catalog metadata, CODEOWNERS, doc values, troubleshooting guide, fleet payloads) regenerates. CI has a drift gate: hand-edits to rendered values don't merge.

Failures are first-class: every automation error has a code in `errors.json` (rendered to [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)), and `scripts/notify.py` auto-files a deduped GitHub issue when something breaks — Slack is an optional upgrade, never a dependency. Run the whole verification suite locally with `scripts/test_all.sh`.

**Roadmap** (designed, not yet shipped): pseudonymous usage analytics + Grafana fleet dashboard, first-class agent/hook/template taxonomy, trending-plugin digest, `/update-marketplace` one-command template updates ([docs/UPDATING.md](docs/UPDATING.md) covers the manual flow today).

## Repo map

| Path | Purpose |
|---|---|
| `marketplace.config.yml` | **Single source of truth** — all company-specific values |
| `.claude-plugin/marketplace.json` | The catalog (rendered from config + plugin entries) |
| `errors.json` | Error registry: every failure mode → code, impact, fix |
| `plugins/` | One directory per plugin (+ `.upstream.json` / `.scorecard.json` sidecars) |
| `scripts/` | The gate: validate, risk lint, versions, smoke test, LLM review, scorecard, catalog, site, scaffold, vendor import, upstream watch, apply_config, notify |
| `templates/` | Partials rendered into docs by apply_config.py |
| `.github/workflows/` | pr-validation (7-job gate incl. config drift), post-merge (render/catalog/site/scorecards/announce), upstream-watch (weekly), pages |
| `docs/` | GETTING-STARTED · AUTHORING · VENDORING · SECURITY · FLEET · TROUBLESHOOTING · UPDATING |
| `AGENTS.md` / `CLAUDE.md` | Runbooks + rules for AI agents working in this repo |
| `init.sh` | One-command fork bootstrap (writes marketplace.config.yml) |

## Docs

| Doc | Read it when |
|---|---|
| [GETTING-STARTED](docs/GETTING-STARTED.md) | You're new — the whole concept, setup, daily use, admin ops |
| [AUTHORING](docs/AUTHORING.md) | You're writing a plugin — tiers, versioning, what CI rejects |
| [VENDORING](docs/VENDORING.md) | You're importing a third-party plugin |
| [SECURITY](docs/SECURITY.md) | You want the threat model and the honest caveats |
| [FLEET](docs/FLEET.md) | You're pre-registering the marketplace on managed machines (MDM) |
| [TROUBLESHOOTING](docs/TROUBLESHOOTING.md) | Something failed with an error code (generated from errors.json) |
| [UPDATING](docs/UPDATING.md) | Your instance repo wants the latest template release |

## Seed plugins

- **company-essentials** — template company-context plugin (`/it-help`, `/standup`, company-context skill). Fill in and make it yours.
- **plugin-dev** — `/new-plugin`, `/vendor-plugin`, `/validate-plugin`, `/submit-plugin` + the authoring house-rules skill.

## Setup checklist (fork admins)

1. **Use this template** → clone → `./init.sh` (five questions — writes `marketplace.config.yml` and renders everything)
2. Fill in `company-essentials`'s FILL-ME-IN markers
3. Enable GitHub Pages (Settings → Pages → Source: **GitHub Actions**), then re-run the `pages` workflow — the first-push run fails until Pages exists
4. Add secrets to arm the optional layers (all fail-soft when unset): `ANTHROPIC_API_KEY` (LLM review — recommended), `SLACK_WEBHOOK_URL`, `CONFLUENCE_*`
5. Protect `main`: require PR + Code Owner review + status checks
6. Later config changes: edit `marketplace.config.yml` → `python3 scripts/apply_config.py` → PR

MIT licensed. Built with Claude Code.
