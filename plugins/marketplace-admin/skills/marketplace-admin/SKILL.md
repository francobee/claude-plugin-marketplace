---
name: marketplace-admin
description: Operating knowledge for administering this Claude Code plugin marketplace — config schema, safe-gh policy, integration explainers, error codes. Use whenever running /setup, /status, changing marketplace.config.yml, or answering "how do I administer this marketplace".
---

# Marketplace Admin

## The one rule

**`marketplace.config.yml` is the single source of truth.** Every company-specific value (names, owners, CODEOWNERS, allowlist, integrations, fleet policy) changes there, then `python3 scripts/apply_config.py` re-renders everything derived. Hand-editing a rendered value is rejected by the `config-drift` CI job. Rendered = marketplace.json name/owner/authors, CODEOWNERS, values inside cfg/gen doc markers, `docs/TROUBLESHOOTING.md`, everything under `fleet/`.

## Config schema (plain English)

- `company.*` — display name, marketplace name (kebab-case, what users type after `@`), contact email, `org/repo`, CODEOWNERS handles.
- `security.network_allowlist` — extra domains plugin content may reference; base domains (github.com etc.) are built in.
- `integrations.*` — all off by default and fail-soft: `llm_review` (Claude reads every PR diff for injection/exfiltration; arm with the ANTHROPIC_API_KEY secret), `slack` (announcements; SLACK_WEBHOOK_URL), `confluence` (catalog page sync), `teamwork_graph` (Atlassian company-context MCP; each user authorizes individually — the URL lives in the config, nowhere else).
- `notifications.github_issues` — the zero-config alert channel: any automation failure files ONE GitHub issue per error code (deduped — it comments instead of re-filing). GitHub's own email notifications do the rest. Slack is an upgrade, never a dependency.
- `telemetry.*` — roadmap; ships disabled. When it lands: metrics only, pseudonymous (salted hash, salt never in the repo), never logs. Say "pseudonymous", never "anonymous", unless `mode: anonymous` (which drops the user id entirely).
- `fleet.*` — what managed devices get: marketplace lockdown (`strict_marketplaces`), sideload-flag rejection, force-enabled plugins (keep tiny), MCP allowlist (**empty = unmanaged**, non-empty = exactly these), install/update policy + version pin, health-check interval, repo access method (fine-grained PAT via JumpCloud secret env var — the PAT value never exists in any repo file).
- `watch.*` — upstream/trending watch knobs.
- `site.*` — catalog-site hosting: `site.hosting` is `github-pages` (free for public repos, paid GitHub plan for private) | `cloudflare` (free regardless of visibility — docs/HOSTING.md) | `none` (CATALOG.md always works); plus project name, title, sections. The deploy workflows read this value and skip cleanly when it isn't theirs.

## Safe-gh policy (binding for all admin commands)

1. Every mutating `gh`/`git` call is a **separate Bash invocation** — never chain mutations with `&&`.
2. Audit-first: GET/state-check before any PUT/create; report what will change.
3. Secrets: print the `gh secret set NAME` command for the admin to run — never accept, read, or echo a secret value; verify with `gh secret list` (names only).
4. Idempotent + resumable: re-running any wizard step must be safe; detect done-state and skip.
5. Never commit to main; wizard writes go through a branch + PR like everything else.

## Error codes

Every automation failure exits with a code from `errors.json`, rendered to `docs/TROUBLESHOOTING.md`: `CFG-*` config/render, `GATE-*` PR gates, `BUILD-*`/`CI-*` pipelines, `FLEET-*` devices (these appear in JumpCloud command results as `HEALTH FAIL [CODE] …`). When an admin reports a code: quote its meaning, user impact, and fix from TROUBLESHOOTING — end users never see codes; they just use Claude while admins fix things.

## Keeping the instance current

The template tags releases (root `CHANGELOG.md`). `docs/UPDATING.md` has the merge flow (template remote → merge tag → PR). `/status` reports when the instance lags the latest template release. Updates are always explicit PRs — no silent auto-merge.
