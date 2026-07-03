# Authoring plugins

The full house rules live in the `plugin-authoring` skill (`plugins/plugin-dev/skills/plugin-authoring/SKILL.md`) — install the `plugin-dev` plugin and Claude enforces them for you. This is the human-readable summary.

## Quick start

```bash
git checkout -b submit/my-plugin
./scripts/scaffold.sh my-plugin          # or /new-plugin in Claude Code
claude --plugin-dir plugins/my-plugin    # test it live
# then: /submit-plugin  (or /validate-plugin + a hand-made PR)
```

## Risk tiers

Every plugin declares one `tier-N` tag in its marketplace.json entry. CI detects the real tier from the files and fails on under-declaration.

| Tier | Contents allowed | Review |
|---|---|---|
| `tier-1` | Only `commands/`, `agents/`, `skills/` markdown | Fastest |
| `tier-2` | Read-only shell commands, `.mcp.json` → allowlisted servers | PR must itemize every command + endpoint |
| `tier-3` | `hooks/`, MCP local processes, `bin/` | Written justification, pinned deps, re-review every bump |

## Versioning (CI-enforced)

- Semver `version` in `plugin.json` **and** the marketplace.json entry — identical.
- Any file change ⇒ version bump. Unbumped versions never reach users on auto-update.
- Every version gets a `## [x.y.z] - YYYY-MM-DD` entry in the plugin's `CHANGELOG.md`.

## Config markers (repo docs, not plugins)

Repo docs (README, docs/) carry values rendered from `marketplace.config.yml` between HTML-comment markers. Edit the config, not the rendered text:

```markdown
<!-- cfg:company.marketplace_name -->internal<!-- /cfg -->   ← inline value, one line
<!-- gen:NAME -->                     ← block whose body renders from templates/NAME.md
…generated body…                        (real names are lowercase; NAME here is inert)
<!-- /gen:NAME -->
```

`python3 scripts/apply_config.py --check` validates marker integrity (a corrupted marker fails with code `CFG-004` and the exact file:line). Template placeholders are `{{dotted.config.path}}`. Plugin markdown must NOT contain HTML comments at all — `risk_lint.py` flags them as a hidden-instruction vector.

## What CI runs on your PR

1. `validate.py` — manifest schemas + catalog consistency
2. `check_versions.py` — bump + changelog gate
3. gitleaks — secrets scan
4. `risk_lint.py` — tier detection + dangerous-pattern scan
5. `smoke_test.py` — structure: frontmatter, referenced files, JSON configs
6. `config-drift` — markers intact + rendered files match `marketplace.config.yml` (double render, clean tree)
7. `llm_review.py` — Claude reads the diff for prompt injection / exfiltration / hidden instructions
8. `permission_manifest.py` — extracts every MCP server, tool, hook, shell command, and endpoint your plugin touches, and posts it as a PR comment — so declare honestly; the reviewer sees the extracted truth next to your claims

Run all of it locally first: `/validate-plugin` — or the whole repo suite with `scripts/test_all.sh`.
