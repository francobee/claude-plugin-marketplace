# Contributing

Thanks for being here. This project runs on contributions — and it's deliberately built so that helping is easy: no dependencies to install, one command to verify everything, and CI that tells you exactly what's wrong.

**We are actively looking for co-maintainers.** See [Becoming a maintainer](#becoming-a-maintainer).

## Ways to contribute

| What | How | Good if you… |
|---|---|---|
| **A plugin** | `/submit-plugin` inside Claude Code, or [docs/AUTHORING.md](docs/AUTHORING.md) by hand | built something your team loves |
| **A bug report** | [Open an issue](../../issues/new/choose) — there are guided forms | hit anything confusing or broken |
| **A product improvement** | PR against `scripts/`, `templates/`, workflows | like small, sharp tools |
| **Docs** | PR that says it simpler | got confused by anything here — that's a doc bug |
| **Maintainership** | Issue titled `maintainer: <your handle>` | want to help review and steward |

## Ground rules (the short version)

1. **Never commit to `main`** — branch + PR, always. CI and a CODEOWNERS review gate every merge, including for admins.
2. **Company-specific values live in `marketplace.config.yml`** — edit the config and run `python3 scripts/apply_config.py`; never hand-edit rendered files (`CATALOG.md`, `site/`, `docs/TROUBLESHOOTING.md`, `fleet/`, values inside cfg/gen markers). The `config-drift` CI job enforces this.
3. **Every failure mode gets an error code** — add new ones to `errors.json` first; scripts exit with registry codes, never ad-hoc ones.
4. **Python stdlib + bash only** — no dependencies, ever. That's why setup is `git clone` and nothing else.
5. **Silent for end users, loud for admins** — users should never see warnings from this machinery; admins get error codes and auto-filed issues.
6. Plugin changes bump the version in **both** `plugin.json` and `marketplace.json` + a CHANGELOG entry ([docs/AUTHORING.md](docs/AUTHORING.md) has the details; `/submit-plugin` does it for you).

## Developing

```bash
git clone https://github.com/francobee/claude-plugin-marketplace
cd claude-plugin-marketplace
scripts/test_all.sh        # the whole suite — 37 checks, ~30 seconds, no setup
```

Green here means CI will be green. The harness covers: config parsing, render idempotency, all PR gates, fleet payload assertions, a fixture-org end-to-end render, negative tests (each must fail with its exact registry code), and shell lint.

Before opening a PR: run `scripts/test_all.sh`, keep the diff focused, and write the PR body for a reviewer who treats your change as code that will run on every machine in a company — because it will.

## Release process (for maintainers)

Releases are semver tags on `main` with a matching entry in [CHANGELOG.md](CHANGELOG.md), published as GitHub releases. Instance repos pull releases explicitly via the [template-remote merge flow](docs/UPDATING.md) — never silently, so a release must stand on its own: changelog entry, green `test_all.sh`, no half-shipped config keys.

## Becoming a maintainer

Maintainers review plugin submissions (see [Runbook C in AGENTS.md](AGENTS.md#runbook-c--operate-the-marketplace)), triage issues, and steward releases. It's a real-review job — the pipeline annotates, humans decide.

Interested? **Open an issue titled `maintainer: <your handle>`** with a couple of sentences on your background and which part you want to own (plugin review, fleet/MDM, docs, CI). A current maintainer will follow up. Consistent, high-quality contributions are the usual path in.

## Conduct

We follow the [Code of Conduct](CODE_OF_CONDUCT.md). tl;dr: be kind, assume good intent, disagree about code not people.
