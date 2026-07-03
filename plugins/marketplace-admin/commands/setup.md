---
description: Guided setup — create and configure your company's private marketplace instance end-to-end (repo, config, branch protection, catalog site, fleet PAT guidance). Quick mode for non-technical admins, Advanced for full control.
argument-hint: [org/repo-name]
---

Walk the admin through creating their company marketplace instance: $ARGUMENTS

You are talking to an IT admin who may not be a developer — assume zero git/YAML knowledge unless they choose Advanced. Explain each step in one plain-English sentence before doing it. Follow the `marketplace-admin` skill for the config schema and the safe-gh policy: **every mutating `gh` or `git` call is its own Bash invocation** (no `&&`-chaining of mutations), you never read or print secret values, and every step is audit-first — check current state before changing it, so the wizard is safe to re-run and resumes where it left off.

## 1. Preflight (read-only, self-healing)

- Check `gh --version`. If `gh` is missing, say "I need GitHub's command-line tool — installing it now" and install it (`brew install gh` on macOS, `winget install GitHub.cli` on Windows, distro package on Linux), with their approval.
- Run `gh auth status`. If not logged in, run `gh auth login --web` and tell them: "a browser window will open — sign in to GitHub there, then come back."
- Confirm the account can create repos in the target org (ask which org/name to use if not given; suggest `<org>/claude-plugins`, private).
- If the current directory is already an instance checkout (has `marketplace.config.yml` and a git remote other than the template), skip repo creation and resume at step 3.

## 2. Choose a mode

Ask exactly one question first:

> **Quick setup** (recommended) — I ask 4 questions and pick safe defaults for everything else, then show you every choice before saving.
> **Advanced setup** — we walk through every setting one by one, each with a one-line explanation.

Either mode can be changed later by editing one file, so nothing is locked in.

## 3. Create the private instance repo

- `gh repo create <org>/<name> --private --template francobee/claude-plugin-marketplace --clone`
- `cd` into the clone. Everything else happens there.

## 4. Interview → write the config

### Quick mode — 4 questions, defaults for the rest

1. **Company or team name** (display only)
2. **IT contact email**
3. **Who must approve plugins?** GitHub handle(s) — default: the admin's own handle from `gh api user -q .login`
4. **Do you want a catalog website?** (a browsable page listing your plugins)
   - "Yes, free" → `site.hosting: cloudflare` (works with the private repo; 5-click walkthrough comes in step 8)
   - "Yes, we pay for GitHub" (Pro/Team/Enterprise) → `site.hosting: github-pages`
   - "No / later" → `site.hosting: none` (CATALOG.md in the repo shows the same thing)

Derive the rest: `marketplace_name` = company name lowercased/kebab-cased (confirm it — this is what users type after `@`); allowlist empty; all integrations off (fail-soft, can be armed any time); fleet defaults (strict lockdown on, health check every 6h, latest Claude Code); telemetry off.

**Then show the full picture before writing** — a two-column table of EVERY setting (including the defaults you chose) with a plain-English meaning per row, and ask "look right?". No hidden choices.

### Advanced mode — every setting, explained

Open `marketplace.config.yml` and walk it top-to-bottom, block by block. For each key: state the **one-line description from its inline comment** (the comments in that file are the schema documentation — read them, don't invent), show the default in brackets, and accept Enter-to-keep. Where a key is an enum (`site.hosting`, `fleet.mdm`, `telemetry.mode`), list the allowed values with a clause on when to pick each. For `telemetry`: say "on the roadmap — ships disabled; when it arrives it is metrics-only and pseudonymous" and leave it off.

### Both modes — write, render, verify

Edit `marketplace.config.yml` with the answers (values only — keep the comments), then:

- `python3 scripts/apply_config.py`
- `scripts/test_all.sh` — must be green before continuing
- Show the admin `git diff --stat` and summarize what was rendered in one sentence.

## 5. Commit on a branch, gate it, land it (never commit straight to main)

- `git checkout -b setup/bootstrap`
- `git add -A`
- `git commit -m "chore: bootstrap <name> marketplace"`
- `git push -u origin setup/bootstrap`
- `gh pr create` titled "Bootstrap <name> marketplace" — explain: "your own gate reviews your own setup."
- `gh pr checks setup/bootstrap --watch` — wait until every check is green (fix and re-push if not).
- With the admin's go-ahead: `gh pr merge setup/bootstrap --squash --delete-branch`, then `git checkout main` and `git pull`. **Merge before the next steps** — branch protection (step 6) would demand a second reviewer, and the catalog site (step 8) publishes from `main`, so triggering it earlier would build the un-customized template.

## 6. Protect main

Write the protection rules to a temp file, then apply — one call, audit-first (GET before PUT to show what changes):

```json
{
  "required_status_checks": { "strict": true, "contexts": ["validate-manifests", "enforce-versioning", "risk-lint", "smoke-test", "config-drift"] },
  "enforce_admins": false,
  "required_pull_request_reviews": { "require_code_owner_reviews": true, "required_approving_review_count": 1 },
  "restrictions": null
}
```

- `gh api -X PUT repos/<org>/<name>/branches/main/protection --input <tempfile>`
- **If GitHub answers 403 "Upgrade to GitHub Pro"** (private repo on the Free plan): branch protection isn't available at that plan — that's pricing, not an error. Explain it, continue the wizard, and note the compensating controls: the CI gate still runs on every PR, and all changes go through PRs by convention. Recommend moving the repo into the company's paid GitHub org (or upgrading) when they can; `/status` will keep flagging it.

Then harden the repo settings (free on every plan; each is one call, explain each in a sentence):

- `gh api -X PATCH repos/<org>/<name> -f delete_branch_on_merge=true` — merged branches clean themselves up.
- `gh api -X PUT repos/<org>/<name>/actions/permissions --input -` with `{"enabled": true, "allowed_actions": "selected", "sha_pinning_required": true}` — CI may only run commit-pinned actions.
- `gh api -X PUT repos/<org>/<name>/actions/permissions/selected-actions --input -` with `{"github_owned_allowed": true, "verified_allowed": false, "patterns_allowed": ["gitleaks/gitleaks-action@*"]}` — GitHub-owned actions plus the secrets scanner, nothing else.
- Public repos only: `gh api -X PUT repos/<org>/<name>/private-vulnerability-reporting` — lets outsiders report security issues privately.

## 7. Arm the optional integrations (names only — NEVER values)

Explain each in one sentence, then for every one the admin wants, print the exact command for THEM to run (do not run it yourself, do not ask for the value):

- `gh secret set ANTHROPIC_API_KEY` — Claude reads every plugin PR for prompt injection (recommended)
- `gh secret set SLACK_WEBHOOK_URL` — Slack pings on submissions and publishes
- `gh variable set CONFLUENCE_BASE_URL` · `gh variable set CONFLUENCE_USER` · `gh secret set CONFLUENCE_TOKEN` — synced Confluence catalog page

Afterwards verify **names only** with `gh secret list` / `gh variable list`.

## 8. Catalog site — follow `site.hosting`

The site builds from `main`, so the bootstrap PR (step 5) must be merged first — never trigger these workflows while the config only exists on a branch.

- **`github-pages`**: `gh api repos/<org>/<name>/pages -X POST -f build_type=workflow` (ignore "already exists"), then `gh workflow run pages.yml`; confirm with `gh api repos/<org>/<name>/pages` and print the URL. If GitHub refuses (403/404 on a private repo): that's their paid-plan requirement, not an error — offer to flip the config to `cloudflare` and redo this step.
- **`cloudflare`**: print the five dashboard steps from `docs/HOSTING.md` Path A verbatim (create free account → Workers & Pages → Connect to Git → build command `python3 scripts/build_site.py`, output `site` → Save and Deploy) and tell them their URL will be `https://<project>.pages.dev`. Only if they'd rather keep deploys in GitHub: Path B — `gh variable set CLOUDFLARE_ACCOUNT_ID` + `gh secret set CLOUDFLARE_API_TOKEN` (token permission: Account · Cloudflare Pages · Edit), then `gh workflow run site-cloudflare.yml`.
- **`none`**: say "no website — `CATALOG.md` in the repo is the catalog" and move on.

## 9. Fleet access (fine-grained PAT — guidance only)

Print these steps verbatim for the admin; the wizard never sees the token:

1. Create a bot GitHub account with read-only access to `<org>/<name>` only.
2. GitHub → Settings → Developer settings → Fine-grained tokens → single repository `<org>/<name>`, permission **Contents: Read-only**, sensible expiry.
3. In JumpCloud, open the *Configure repo access* command (script in `fleet/jumpcloud/`) and attach the token as the secret environment variable `JC_CLAUDE_REPO_PAT`.
4. Full walkthrough: `docs/FLEET.md` — including the pilot-device-group rollout and PAT rotation runbook.

## 10. Finish

- Tell the admin to fill in `plugins/company-essentials/skills/company-context/SKILL.md` (offer to do it with them from what you know of their stack).
- Run the `/status` checklist and hand them the result.
- Closing line: "Config changes later: edit marketplace.config.yml, run `python3 scripts/apply_config.py`, open a PR. Never edit rendered values. Re-run `/setup` any time — it resumes where it left off."

**If anything fails mid-wizard** (auth expires, permission denied): print exactly what remains as copy-paste commands, and leave the repo in a clean state — config committed on the `setup/bootstrap` branch, nothing half-applied on main.
