---
description: Guided setup — create and configure your company's private marketplace instance end-to-end (repo, config, branch protection, Pages, fleet PAT guidance)
argument-hint: [org/repo-name]
---

Walk the admin through creating their company marketplace instance: $ARGUMENTS

You are talking to an IT admin who may not be a developer. Explain each step in one plain-English sentence before doing it. Follow the `marketplace-admin` skill for the config schema and the safe-gh policy: **every mutating `gh` or `git` call is its own Bash invocation** (no `&&`-chaining of mutations), you never read or print secret values, and every step is audit-first — check current state before changing it, so the wizard is safe to re-run and resumes where it left off.

## 1. Preflight (read-only)

- Run `gh auth status`. If it fails: print the two commands the admin needs (`gh auth login`, then re-run `/setup`) and STOP — no partial writes.
- Confirm the GitHub account can create repos in the target org (ask which org/name to use if not given; suggest `<org>/claude-plugins`, private).
- If the current directory is already an instance checkout (has `marketplace.config.yml` and a git remote other than the template), skip repo creation and resume at step 3.

## 2. Create the private instance repo

- `gh repo create <org>/<name> --private --template francobee/claude-plugin-marketplace --clone`
- `cd` into the clone. Everything else happens there.

## 3. Interview → write the config

Ask, one at a time, with the default in brackets:

1. Company/team display name
2. Marketplace name — lowercase kebab-case, what users type in `/plugin install <plugin>@<name>` [company name, shortened]
3. IT contact email
4. GitHub handle(s) who must approve every plugin (CODEOWNERS)
5. Extra network domains plugins may reach [none]
6. Integrations — one sentence each, all optional, all can be added later:
   - *Claude security review of every PR* (needs an Anthropic API key) — recommended
   - *Slack announcements* (needs a webhook URL)
   - *Confluence catalog page* (needs base URL + space key)
   - *Atlassian company-context (Teamwork Graph)* — each user authorizes individually later
7. Fleet: device health-check interval in hours [6]; pin a Claude Code version or follow latest [latest]
8. Usage analytics: say "on the roadmap — ships disabled; when it arrives it is metrics-only and pseudonymous" and leave `telemetry.enabled: false`.

Edit `marketplace.config.yml` with those answers (values only — keep the comments), then render and verify:

- `python3 scripts/apply_config.py`
- `scripts/test_all.sh` — must be green before continuing
- Show the admin `git diff --stat` and summarize what was rendered.

## 4. Commit on a branch (never main)

- `git checkout -b setup/bootstrap`
- `git add -A`, then commit (`chore: bootstrap <name> marketplace`) and push with `-u`.
- `gh pr create` titled "Bootstrap <name> marketplace" — explain: "your own gate reviews your own setup; merge it after checks pass."

## 5. Protect main

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

## 6. Arm the optional integrations (names only — NEVER values)

For each integration the admin said yes to, print the exact command for THEM to run (do not run it yourself, do not ask for the value):

- `gh secret set ANTHROPIC_API_KEY` · `gh secret set SLACK_WEBHOOK_URL`
- `gh variable set CONFLUENCE_BASE_URL` · `gh variable set CONFLUENCE_USER` · `gh secret set CONFLUENCE_TOKEN`

Afterwards verify **names only** with `gh secret list` / `gh variable list`.

## 7. Fleet access (fine-grained PAT — guidance only)

Print these steps verbatim for the admin; the wizard never sees the token:

1. Create a bot GitHub account with read-only access to `<org>/<name>` only.
2. GitHub → Settings → Developer settings → Fine-grained tokens → single repository `<org>/<name>`, permission **Contents: Read-only**, sensible expiry.
3. In JumpCloud, open the *Configure repo access* command (script in `fleet/jumpcloud/`) and attach the token as the secret environment variable `JC_CLAUDE_REPO_PAT`.
4. Full walkthrough: `docs/FLEET.md` — including the pilot-device-group rollout and PAT rotation runbook.

## 8. Catalog site (two clicks)

- `gh api repos/<org>/<name>/pages -X POST -f build_type=workflow` (ignore "already exists" errors)
- `gh workflow run pages.yml`
- Confirm with `gh api repos/<org>/<name>/pages` and print the site URL.

## 9. Finish

- Tell the admin to fill in `plugins/company-essentials/skills/company-context/SKILL.md` (offer to do it with them from what you know of their stack).
- Run the `/status` checklist and hand them the result.
- Closing line: "Config changes later: edit marketplace.config.yml, run `python3 scripts/apply_config.py`, open a PR. Never edit rendered values."

**If anything fails mid-wizard** (auth expires, permission denied): print exactly what remains as copy-paste commands, and leave the repo in a clean state — config committed on the `setup/bootstrap` branch, nothing half-applied on main.
