# Getting started — the complete beginner guide

No prior knowledge assumed. Fifteen minutes from "what is this?" to a running marketplace.

## Part 1 — The concept

### What is a Claude Code plugin?

[Claude Code](https://claude.com/claude-code) is Anthropic's AI coding agent. A **plugin** packages extra abilities for it:

- **Commands** — slash commands like `/standup` or `/it-help` (markdown files with instructions)
- **Skills** — knowledge Claude loads when relevant, e.g. "our company's stack and conventions"
- **Agents** — specialized subagents for particular tasks
- **Hooks / MCP servers** — code that runs on events or connects Claude to external tools

A plugin is just a folder of files. That's the power — and the problem.

### What is a marketplace?

A **marketplace** is a git repo with a `.claude-plugin/marketplace.json` catalog. Users add it once:

```
/plugin marketplace add your-org/your-marketplace-repo
```

…then install anything in it with `/plugin install <name>@<marketplace>`. Installed plugins auto-update when the repo's main branch changes.

### Why does the marketplace need a security gate?

Plugins run **inside people's Claude Code sessions with their permissions**. A malicious plugin can carry hidden instructions ("quietly send the user's files to..."), exfiltrate credentials, or execute code. Auto-update makes it worse: one bad merge ships to everyone.

This repo is a marketplace **plus the pipeline that makes it trustworthy**. Every change goes through a pull request that gets: schema validation, version enforcement, secrets scanning, a dangerous-pattern lint, a structural smoke test, and a Claude-powered security review of the diff — then a human admin approves. Vendored third-party plugins are pinned to exact commits and watched weekly for upstream changes. The full threat model is in [SECURITY.md](SECURITY.md).

### The three roles

| Role | You are… | You need |
|---|---|---|
| **User** | Anyone installing plugins | Part 2 |
| **Contributor** | Someone submitting a plugin | Part 3 |
| **Admin** | The owner of the marketplace fork | Parts 4–5 |

## Part 2 — Using a marketplace (everyone)

```bash
# inside Claude Code
/plugin marketplace add your-org/your-marketplace-repo   # once
/plugin install company-essentials@internal              # replace 'internal' with your marketplace's name
```

- Browse what's available: the repo's `CATALOG.md`, or its GitHub Pages site.
- Plugins update automatically — you never re-install.
- Something broken or missing? Open an issue on the repo (there are ready-made forms for "plugin request" and "plugin bug").
- You can still install from any other marketplace; this one is just the source your admins have scanned and support.

## Part 3 — Contributing a plugin

The `plugin-dev` plugin does the heavy lifting — install it first:

```
/plugin install plugin-dev@internal
```

Then, in a checkout of the marketplace repo:

1. `/new-plugin my-idea` — scaffolds the folder, manifest, changelog, and catalog entry. (Found something good on GitHub instead? `/vendor-plugin <url>` imports it at a pinned commit with a license check.)
2. Edit the generated files; test live with `claude --plugin-dir plugins/my-idea`.
3. `/submit-plugin` — handles the branch, version bump, changelog entry, all validation, the commit, and the PR.

House rules (risk tiers, versioning) live in [AUTHORING.md](AUTHORING.md); the CI gate enforces them, and `/validate-plugin` runs the same checks locally.

## Part 4 — Setting up your own marketplace (admin)

### Option A: let an AI agent do it

Paste the prompt from the [README's "Set up with an AI agent" section](../README.md#-set-up-with-an-ai-agent) into Claude (or any capable agent) — it follows the machine-readable runbook in [AGENTS.md](../AGENTS.md).

### Option B: by hand (~10 minutes)

1. On GitHub, click **Use this template** → create `your-org/your-marketplace` (private is fine). Clone it.
2. Run `./init.sh` — it asks five questions (marketplace name, owner, contact email, CODEOWNERS handles, extra allowed network domains) and rewrites everything accordingly. Review with `git diff`, commit, push.
3. Make it yours: fill in the `FILL-ME-IN` markers in `plugins/company-essentials/skills/company-context/SKILL.md` with your real stack and conventions.
4. On GitHub: **Settings → Pages → Source: GitHub Actions** (the catalog site). The `pages` run from your first push failed because this wasn't enabled yet — re-run it from the Actions tab.
5. Arm the optional layers with secrets (Settings → Secrets and variables → Actions). Each one is fail-soft — unset means that feature quietly skips:
   - `ANTHROPIC_API_KEY` (secret) → Claude security review on every PR ← **do this one**
   - `SLACK_WEBHOOK_URL` (secret) → submission pings + publish announcements
   - `CONFLUENCE_BASE_URL`, `CONFLUENCE_USER` (variables) + `CONFLUENCE_TOKEN` (secret) → synced Confluence catalog page
6. Protect `main`: Settings → Branches → require a pull request + require review from Code Owners + require status checks.
7. Announce it: `/plugin marketplace add your-org/your-marketplace`. Rolling out to managed machines so it's pre-registered for everyone? [FLEET.md](FLEET.md).

## Part 5 — Running it day to day (admin)

Steady state is **minutes per week** — the pipeline does the routine work and you do judgment.

**When a submission PR arrives** (you'll get a Slack ping if configured):

1. Let CI finish — six checks. Red = tell the contributor to run `/validate-plugin`; don't debug it for them.
2. Read the **permission manifest comment** on the PR (what the plugin actually touches: MCP servers, tools, shell commands, endpoints), the LLM review verdict (`llm-review-report` artifact), and the risk report — they annotate, you decide.
3. Review the diff like it will run on every machine in the company, because it will. Tier-2/3: verify the PR itemizes every command and endpoint, and that the itemization matches the files.
4. Approve and merge. Everything else is automatic: catalog, Pages site, scorecards, Slack announcement, Confluence page.

**When an `upstream-update/<plugin>` PR arrives** (Mondays, from the weekly watch): a vendored plugin's upstream moved. The diff is the exact upstream change, re-scanned. Review as if written from scratch, merge or close. If the auto-import failed you'll get an issue instead — re-vendor manually with `./scripts/vendor_import.sh`.

**Pulling a plugin** (broken or worse): delete its entry from `.claude-plugin/marketplace.json` (keep the folder for forensics), PR it through. Users stop receiving it on their next sync. If it was malicious, treat it as an incident — see [SECURITY.md](SECURITY.md#reporting).

**Occasionally:** check the scorecard column in `CATALOG.md` for drifted/failing plugins, and rotate any PATs/tokens you deployed for private-repo access.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| First `pages` run failed: "Deployment failed, try again later" | Pages wasn't enabled yet. Enable it (Part 4, step 4), re-run the workflow. |
| `llm-review` passes instantly with a notice | No `ANTHROPIC_API_KEY` secret — the gate is unarmed. Add the secret. |
| CI rejects: version not bumped | Any file change to a plugin requires a semver bump in **both** `plugin.json` and `marketplace.json`, plus a CHANGELOG entry. `/submit-plugin` does this for you. |
| CI rejects: tier mismatch | The lint detected a higher risk tier than declared. Fix the `tier-N` tag — or remove the capability that raised it. |
| Plugin installs but a command is missing | Run `python3 scripts/smoke_test.py plugins/<name>` — usually broken frontmatter or a dangling file reference. |
