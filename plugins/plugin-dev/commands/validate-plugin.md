---
description: Run the marketplace CI validation suite locally on a plugin before opening a PR
argument-hint: [plugin-name]
---

Validate a marketplace plugin locally (same checks CI runs): $ARGUMENTS

From the marketplace repo root, run these and walk the user through any failures:

1. `python3 scripts/validate.py` — manifest schema + catalog consistency.
2. `python3 scripts/risk_lint.py plugins/<plugin-name>` — risk-tier detection + dangerous-pattern scan. The detected tier must match the plugin's `tier-N` tag in marketplace.json.
3. `python3 scripts/smoke_test.py plugins/<plugin-name>` — structural checks: frontmatter parses, referenced files exist, `.mcp.json`/`hooks.json` well-formed.
4. `python3 scripts/check_versions.py` — if the plugin already exists on main, its version must be bumped and CHANGELOG.md must have a matching entry.
5. Optional but recommended before submitting: `python3 scripts/llm_review.py plugins/<plugin-name>` — the same Claude security review CI will run (prompt injection, exfiltration, hidden instructions). Needs `ANTHROPIC_API_KEY`.

Fix every finding rather than arguing with the scanner; CI runs the identical code and CODEOWNERS won't merge red PRs.
