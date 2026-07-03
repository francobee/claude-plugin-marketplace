---
name: plugin-authoring
description: House rules for authoring marketplace plugins — risk tiers, versioning, changelog format, and what CI rejects. Use whenever creating, editing, vendoring, or reviewing a plugin for this marketplace.
---

# Plugin Authoring Rules

## Risk tiers (declared as a `tier-N` tag in marketplace.json; CI verifies)

- **tier-1 — prompt-only**: only `commands/`, `agents/`, `skills/` markdown. No executables, no `hooks/`, no `.mcp.json`, no `bin/`. Fastest review.
- **tier-2 — read/config**: shells out to read-only commands, or `.mcp.json` pointing at allowlisted servers (official Anthropic servers + your company's domains). PR must itemize every command and endpoint.
- **tier-3 — code-executing**: anything with `hooks/hooks.json`, MCP servers spawning local processes, or `bin/`. Requires written justification, exactly-pinned dependency versions, and re-review on every version bump.

Declare the highest tier that applies. Under-declaring fails CI.

## Versioning & changelog (CI-enforced)

- Explicit semver `version` in plugin.json AND the marketplace.json entry — keep them identical.
- Any change to a plugin's files ⇒ bump the version. An unbumped version silently never ships to users on auto-update.
- Every version gets a `## [x.y.z] - YYYY-MM-DD` entry in the plugin's CHANGELOG.md (Keep a Changelog format).

## What CI rejects

- Secrets of any kind (gitleaks) — use `userConfig` with `"sensitive": true` for tokens.
- Dangerous patterns: piping downloads to a shell, dynamic code evaluation, decoding embedded blobs, raw TCP connections, AppleScript execution, reading SSH/AWS/Keychain credentials or dotenv files, persistence via launch daemons or cron.
- Network destinations outside the allowlist (github.com, api.anthropic.com + domains your marketplace admin added in `scripts/risk_lint.py`).
- Hidden text in markdown: zero-width/bidi Unicode, HTML comments containing instructions.
- Prompt injection / exfiltration instructions (Claude security review).
- Structural breakage (smoke test): frontmatter that doesn't parse, references to files that don't exist, malformed `.mcp.json`/`hooks.json`.
- Tier under-declaration, missing changelog entry, unbumped version, `strict` ≠ true.

## Process

Branch → author (scaffold with `/new-plugin` or import with `/vendor-plugin`) → test with `claude --plugin-dir` → `/validate-plugin` → `/submit-plugin` (or a hand-made PR with the template filled honestly) → automated scans + admin approval → merge → published, catalog + site rebuild automatically.
