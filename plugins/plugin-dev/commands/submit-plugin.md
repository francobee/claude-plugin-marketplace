---
description: Submit a plugin to the marketplace — handles branch, version, changelog, validation, commit, and PR for you
argument-hint: [plugin-name]
---

Handle the entire marketplace submission for the user: $ARGUMENTS

Work from their local marketplace checkout (a repo containing `.claude-plugin/marketplace.json` alongside a `plugins/` directory). If the plugin name wasn't given, infer it from what changed (`git status`) and confirm with the user.

1. **Branch**: if on `main`, create `submit/<plugin-name>` and switch to it. Never commit to main.
2. **Version + changelog**: check whether `plugins/<name>/.claude-plugin/plugin.json` version is bumped vs main and matches the marketplace.json entry. If not, do it for them: patch bump for fixes, minor for new capability; add a matching `## [x.y.z] - YYYY-MM-DD` entry to the plugin's CHANGELOG.md summarizing the change.
3. **Validate** (same code CI runs) and fix anything fixable, explaining anything that needs the user's call:
   ```bash
   python3 scripts/validate.py
   python3 scripts/risk_lint.py plugins/<name>
   python3 scripts/smoke_test.py plugins/<name>
   python3 scripts/check_versions.py main
   ```
   The detected tier from risk-lint must match the `tier-N` tag in marketplace.json — correct the tag if needed.
4. **Commit** with a message like `feat(<name>): <what changed> (v<x.y.z>)`.
5. **PR**: if the repo has a GitHub remote and `gh auth status` succeeds, push the branch and run `gh pr create`, filling the PR template (`.github/PULL_REQUEST_TEMPLATE.md`): plugin@version, submission type, declared tier (from risk-lint), what it does, and check off the checklist items you actually verified. For tier-2/3, itemize every command/endpoint from the plugin's files.
6. **No remote / no gh auth**: stop after the commit and tell the user exactly what's left, e.g. "committed on branch submit/<name> — once the repo has a GitHub remote, run: `git push -u origin submit/<name> && gh pr create --fill`".

Then tell them what happens next: automated scans run on the PR, an admin reviews and merges, and the plugin is announced in the marketplace channel.
