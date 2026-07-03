# Security model

## Threat model

Plugins run inside users' Claude Code sessions with the user's permissions. The threats this marketplace is built to stop:

- **Prompt injection** — plugin text that subverts user intent, hides behavior, or manipulates the model.
- **Data exfiltration** — plugin code/instructions sending files, credentials, or conversation data out.
- **Hidden instructions** — zero-width/bidi Unicode, HTML comments, encoded blobs carrying directives.
- **Malicious code** — pipe-to-shell, credential file reads, persistence, off-allowlist network calls.
- **Supply-chain drift** — a vendored plugin's upstream turning malicious after import.

## Layers

| Layer | Tool | Catches |
|---|---|---|
| Schema gate | `validate.py` | Malformed/mismatched manifests, `strict` ≠ true |
| Version gate | `check_versions.py` | Silent changes shipping without a bump/changelog |
| Secrets | gitleaks (CI) | Committed tokens/keys |
| Static risk lint | `risk_lint.py` | Dangerous patterns, hidden Unicode, tier under-declaration, off-allowlist domains |
| Structure | `smoke_test.py` | Broken frontmatter, dangling file references, malformed `.mcp.json`/`hooks.json` |
| Permission manifest | `permission_manifest.py` | Extracts what each plugin touches — MCP servers, declared tools, hooks, shell commands, endpoints — posted as a PR comment for reviewers, published as `.permissions.json` sidecars |
| Semantic review | `llm_review.py` (Claude) | Injection/exfiltration intent that regexes can't see |
| Pinning | `vendor_import.sh` | Moving-target upstreams (pinned commits only) |
| Drift watch | `upstream_watch.py` (weekly) | Upstream changes after import — surfaced as reviewable PRs |
| Human gate | CODEOWNERS | Everything else — nothing merges without admin approval |

Per-plugin results are published as `.scorecard.json` sidecars, shown in CATALOG.md and on the site.

## Honest caveats

- **LLM review is fail-soft**: without the `ANTHROPIC_API_KEY` secret the job passes with a notice. Set the secret to arm it. It is one layer, not a guarantee — a sufficiently clever payload can fool it, which is why the static lint and human review exist alongside.
- **Scanners run at merge time**: a plugin is only as trustworthy as its last reviewed version. That's why unbumped versions never ship and vendored updates come as PRs, not silent merges.
- **The human gate is the real gate.** CODEOWNERS review of the actual diff is the layer everything else exists to make tractable.

## Reporting

Suspected malicious or vulnerable plugin: open a [plugin-bug issue](../.github/ISSUE_TEMPLATE/plugin-bug.yml) and contact your marketplace admin directly. Admins: pull the plugin by removing its marketplace.json entry (users stop receiving it on next sync), then investigate.
