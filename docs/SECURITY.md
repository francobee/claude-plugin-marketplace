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

## Repo hardening (the settings around the pipeline)

The pipeline is only as strong as the repository settings enforcing it. The `/setup` wizard applies these (step 6); to audit or re-apply by hand:

| Setting | Why | Command / where |
|---|---|---|
| Branch protection on `main` | The 5 required checks + code-owner review actually block merges | wizard step 6, or `gh api -X PUT repos/<org>/<repo>/branches/main/protection` |
| Actions: selected allowlist | CI can only run allowlisted actions (GitHub-owned + gitleaks). Repo-level `sha_pinning_required` stays **off**: it applies inside composite actions too, and GitHub's own Pages actions reference nested actions by tag — enabling it breaks deploys (found by testing). First-party pins are full SHAs, refreshed by Dependabot. | `gh api -X PUT repos/<org>/<repo>/actions/permissions` / `…/selected-actions` |
| Workflow token read-only, no PR approval | A compromised workflow can't push or self-approve | Settings → Actions → General (GitHub's default; verify with `gh api repos/<org>/<repo>/actions/permissions/workflow`) |
| Secret scanning + push protection | Blocks committed tokens before they land | free on public repos (Settings → Security); private repos rely on the gate's gitleaks job |
| Dependabot: security updates + weekly actions-pin PRs | SHA pins stay current, through the same gate | Settings → Security; `.github/dependabot.yml` ships in this repo |
| Auto-delete merged branches, private vulnerability reporting (public repos) | Hygiene; private channel for reports | `gh api -X PATCH repos/<org>/<repo> -f delete_branch_on_merge=true`; `gh api -X PUT …/private-vulnerability-reporting` |

**Plan wall, honestly:** on GitHub's Free plan, *private* repos get no branch protection, rulesets, or native secret scanning (same wall as Pages — see [HOSTING.md](HOSTING.md)). The gate still runs on every PR (including gitleaks), but merging without checks can't be *prevented*. If your marketplace repo is private and this matters — it should — put it in a paid GitHub org. `/status` flags this state.

## Honest caveats

- **LLM review is fail-soft**: without the `ANTHROPIC_API_KEY` secret the job passes with a notice. Set the secret to arm it. It is one layer, not a guarantee — a sufficiently clever payload can fool it, which is why the static lint and human review exist alongside.
- **Scanners run at merge time**: a plugin is only as trustworthy as its last reviewed version. That's why unbumped versions never ship and vendored updates come as PRs, not silent merges.
- **The human gate is the real gate.** CODEOWNERS review of the actual diff is the layer everything else exists to make tractable.

## Reporting

Suspected malicious or vulnerable plugin: open a [plugin-bug issue](../.github/ISSUE_TEMPLATE/plugin-bug.yml) and contact your marketplace admin directly. Admins: pull the plugin by removing its marketplace.json entry (users stop receiving it on next sync), then investigate.
