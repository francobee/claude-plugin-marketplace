---
description: Scaffold a new plugin for the marketplace
argument-hint: [plugin-name]
---

Scaffold a new marketplace plugin named: $ARGUMENTS

1. Locate a local checkout of the marketplace repo (a directory containing `.claude-plugin/marketplace.json` alongside a `plugins/` directory; ask the user where it is if unclear). If none exists, clone it first (ask the user for the repo URL).
2. From the repo root, run: `./scripts/scaffold.sh <plugin-name>` — it creates `plugins/<plugin-name>/` with plugin.json, CHANGELOG.md, an example command, and appends a draft entry to `.claude-plugin/marketplace.json`.
3. Read the generated files with the user and help them fill in: description, first command/skill content, correct `tags` risk tier (`tier-1` if markdown-only; see the plugin-authoring skill).
4. Remind them to test locally (`claude --plugin-dir plugins/<plugin-name>`), then run `/validate-plugin`, then open a PR on a branch — never commit to main. Or just run `/submit-plugin` to have all of that handled.
