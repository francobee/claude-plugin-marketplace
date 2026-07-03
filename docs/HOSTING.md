# Hosting the catalog site

Your marketplace ships with a browsable catalog website (searchable cards for every plugin, risk tiers, install commands). Where that site lives is one config value:

```yaml
site:
  hosting: github-pages   # github-pages | cloudflare | none
```

Change it in `marketplace.config.yml`, run `python3 scripts/apply_config.py`, open a PR — the right deploy workflow activates on merge and the other one skips cleanly.

**The site is always optional.** [CATALOG.md](../CATALOG.md) in the repo shows the same information, and `/plugin install` never depends on the website. If you don't want a site at all, set `hosting: none` and you're done.

## Which option should I pick?

| Your situation | Pick | Why |
|---|---|---|
| Public repo | `github-pages` | Free, zero accounts beyond GitHub, enabled in two clicks. |
| **Private repo, free GitHub plan** | `cloudflare` | GitHub Pages on private repos requires a paid GitHub plan. Cloudflare Pages is **free regardless of repo visibility**. |
| Private repo, paid GitHub plan (Pro/Team/Enterprise) | either | Both work; GitHub Pages is one less account. |
| No website wanted | `none` | CATALOG.md and `/plugin` cover everything. |

> **Who can see the site?** The site only lists plugin names, descriptions, and risk tiers — never code or secrets. GitHub Pages sites are always public URLs (even from private repos, unless you're on GitHub Enterprise). Cloudflare sites are public URLs too, but you can put [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/) in front for free (up to 50 users) to restrict it to your company. If any of that is a concern, `none` is always safe.

## GitHub Pages (`hosting: github-pages`)

1. On GitHub: **Settings → Pages → Source: GitHub Actions**.
2. Re-run the `pages` workflow (Actions tab → pages → Run workflow), or just merge anything.
3. Your site: `https://<org>.github.io/<repo>/`.

The `/setup` wizard does step 1–2 for you (`gh api repos/<org>/<repo>/pages -X POST -f build_type=workflow`).

**Private repo on a free plan?** GitHub will refuse to enable Pages — that's their pricing, not a bug. Switch to Cloudflare below.

## Cloudflare Pages (`hosting: cloudflare`) — free, works with private repos

Set the config first:

```yaml
site:
  hosting: cloudflare
  cloudflare_project: ""    # optional; defaults to your marketplace name → https://<name>.pages.dev
```

Then pick ONE of two paths:

### Path A — connect in the dashboard (recommended, no tokens)

Best for non-technical admins: five clicks, nothing to maintain, no secrets anywhere.

1. Create a free account at [dash.cloudflare.com](https://dash.cloudflare.com) (no credit card).
2. **Workers & Pages → Create → Pages → Connect to Git** and authorize the Cloudflare GitHub App for your marketplace repo (private repos work).
3. Pick the repo. Build settings:
   - **Build command:** `python3 scripts/build_site.py`
   - **Build output directory:** `site`
4. Click **Save and Deploy**. Done — every merge to `main` redeploys automatically, on Cloudflare's side.
5. Your site: `https://<project>.pages.dev` (shown on the project page).

With this path the repo's `site-cloudflare` workflow notices you haven't given it a token and simply reports "nothing to do" — Cloudflare is already deploying.

### Path B — deploy from CI (for admins who prefer everything in GitHub)

The repo's `site-cloudflare` workflow deploys `site/` with wrangler on every merge. Arm it with two values (Settings → Secrets and variables → Actions):

1. **Variable** `CLOUDFLARE_ACCOUNT_ID` — dashboard → Workers & Pages → right sidebar, "Account ID".
2. **Secret** `CLOUDFLARE_API_TOKEN` — dashboard → My Profile → API Tokens → Create Token → Custom token with the single permission **Account · Cloudflare Pages · Edit**, scoped to your account. Set an expiry and calendar the rotation.

```bash
gh variable set CLOUDFLARE_ACCOUNT_ID --repo <!-- cfg:company.github_repo -->francobee/claude-plugin-marketplace<!-- /cfg -->
gh secret set CLOUDFLARE_API_TOKEN --repo <!-- cfg:company.github_repo -->francobee/claude-plugin-marketplace<!-- /cfg -->
```

The workflow creates the Pages project on first run (idempotent) and deploys on every merge. Failures auto-file a deduped GitHub issue with code `CI-003` ([TROUBLESHOOTING.md](TROUBLESHOOTING.md#ci-003)).

**Free plan limits** (generous for a catalog page): 500 builds/month on Path A (Path B doesn't count — you build in GitHub Actions), unlimited requests and bandwidth for static assets, 20,000 files per deploy. This site is one HTML file.

## No site (`hosting: none`)

Both deploy workflows skip. Point people at [CATALOG.md](../CATALOG.md) — same content, rendered as a table in the repo, refreshed on every merge.

## Previewing locally (any hosting choice)

```bash
python3 scripts/build_site.py && open site/index.html
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `pages` workflow failed with "Deployment failed" / 404 on enable | Pages isn't enabled (or private repo + free plan). Enable it, or switch to `hosting: cloudflare`. Code `CI-002`. |
| `site-cloudflare` says "nothing to do" | Either `site.hosting` isn't `cloudflare`, or (Path A) that's the expected message — Cloudflare deploys dashboard-side. |
| wrangler: authentication / 10000 error | Token expired or under-scoped — recreate with **Cloudflare Pages: Edit** and update the secret. Code `CI-003`. |
| wrangler: project name already taken | `*.pages.dev` names are global. Set a more specific `site.cloudflare_project` in the config. |
| Site loads but looks stale | Deploys follow merges to `main`. Check the latest `site-cloudflare` / `pages` run in the Actions tab. |
