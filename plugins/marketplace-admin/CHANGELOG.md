# Changelog — marketplace-admin

## [1.1.0] - 2026-07-03

- `/setup`: **Quick vs Advanced modes** — Quick asks 4 questions and shows every derived default in a plain-English summary before writing; Advanced walks each config key with its one-line description. Preflight now self-heals a missing `gh` (installs + `gh auth login --web`).
- `/setup`: catalog-site step follows `site.hosting` — GitHub Pages, free Cloudflare Pages (private-repo friendly, dashboard or CI mode), or none; graceful fallback to Cloudflare when GitHub refuses Pages on a free-plan private repo.
- `/status`: site check is hosting-aware (Pages API, site-cloudflare run status, or "disabled by config").
- `/setup`: the bootstrap PR is now gated and merged (with the admin's go-ahead) **before** branch protection and site publish — the site builds from `main`, and protection would otherwise demand a second reviewer.
- skill: `site.*` schema documentation for the new hosting options.

## [1.0.0] - 2026-07-03

- `/setup`: guided wizard — creates the private instance repo from the template, interviews the admin in plain English, writes marketplace.config.yml, renders everything, opens the bootstrap PR, enables branch protection and Pages, and prints exact fine-grained-PAT steps (never touching secret values).
- `/status`: plain-English health checklist — secrets present (names only), Pages live, branch protection, config drift, open error-code issues, template release lag, fleet health summary.
- `marketplace-admin` skill: config schema knowledge, safe-gh policy, integration explainers.
