# Claude Code Plugin Marketplace — security-gated, self-maintaining

A fork-ready [Claude Code plugin marketplace](https://docs.anthropic.com/en/docs/claude-code/plugins) for teams that want a **trusted internal source** for plugins: everything published here is schema-validated, risk-linted, secrets-scanned, smoke-tested, and reviewed by Claude for prompt injection — before a human approves the merge.

Most marketplaces are a JSON file and vibes. This one is a pipeline:

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
| Fleet rollout docs | — | ✔ MDM pre-registration guide |

## Use it

```bash
# inside Claude Code
/plugin marketplace add francobee/claude-plugin-marketplace
/plugin install plugin-dev@internal
```

Browse: [CATALOG.md](CATALOG.md) or the GitHub Pages site.

## Fork it (make it your company's marketplace)

1. **Use this template** (or fork), clone it.
2. Run `./init.sh` — interactive rename: marketplace name, owner, CODEOWNERS handles, allowed network domains. Under a minute.
3. Fill in `plugins/company-essentials/skills/company-context/SKILL.md` (the FILL-ME-IN markers) — your stack, your conventions.
4. Push, then arm the optional integrations with repo secrets/vars:
   - `ANTHROPIC_API_KEY` → LLM security review on every PR
   - `SLACK_WEBHOOK_URL` → new-submission pings + publish announcements
   - `CONFLUENCE_BASE_URL`/`CONFLUENCE_USER` (vars) + `CONFLUENCE_TOKEN` (secret) → synced Confluence catalog page
   - Everything is fail-soft: unset secrets just skip that feature.
5. Enable GitHub Pages (Settings → Pages → Source: **GitHub Actions**) for the catalog site. The `pages` run from your first push fails if Pages wasn't enabled yet ("Deployment failed, try again later") — just re-run it from the Actions tab afterwards.
6. Rolling out to a managed fleet? See [docs/FLEET.md](docs/FLEET.md).

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

## Repo map

| Path | Purpose |
|---|---|
| `.claude-plugin/marketplace.json` | The catalog — single source of truth |
| `plugins/` | One directory per plugin (+ `.upstream.json` / `.scorecard.json` sidecars) |
| `scripts/` | The gate: validate, risk lint, versions, smoke test, LLM review, scorecard, catalog, site, scaffold, vendor import, upstream watch |
| `.github/workflows/` | pr-validation (6-job gate), post-merge (catalog/site/scorecards/announce), upstream-watch (weekly), pages |
| `docs/` | AUTHORING · VENDORING · SECURITY · FLEET |
| `init.sh` | One-command fork bootstrap |

## Seed plugins

- **company-essentials** — template company-context plugin (`/it-help`, `/standup`, company-context skill). Fill in and make it yours.
- **plugin-dev** — `/new-plugin`, `/vendor-plugin`, `/validate-plugin`, `/submit-plugin` + the authoring house-rules skill.

MIT licensed. Built with Claude Code.
