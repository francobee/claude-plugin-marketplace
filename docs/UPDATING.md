# Updating your instance from the template

Your marketplace repo was created from the [template](https://github.com/francobee/claude-plugin-marketplace). The template keeps improving — releases are tagged (semver) with a product [CHANGELOG](../CHANGELOG.md). Your instance pulls those improvements **explicitly, via a reviewable PR** — never a silent auto-merge.

## One-time setup

```bash
git remote add template https://github.com/francobee/claude-plugin-marketplace.git
```

## Pull a release

```bash
git fetch template --tags
git log --oneline HEAD..v1.1.0            # what you'd get (read CHANGELOG.md at that tag)
git checkout -b update/template-v1.1.0
git merge v1.1.0                          # your config + plugins win; template scripts/workflows update
```

**First pull only:** repos created with GitHub's "Use this template" button share **no git history** with the template, so the first merge fails with `refusing to merge unrelated histories`. Run it once as:

```bash
git merge v1.1.0 --allow-unrelated-histories
```

This first merge conflicts on most customized files (there's no common ancestor — resolve with the rules below) and records a shared ancestor, so every later pull is a normal, mostly-clean merge without the flag.

Conflicts concentrate in files you customized. Rules of thumb:

- `marketplace.config.yml`, `plugins/` — **keep yours** (the template only ships seed content). If the release added **new config keys** (the CHANGELOG says so), copy those lines in from the template's `marketplace.config.yml` — the renderer only rejects *unknown* keys, but new features default off/legacy until the key exists.
- `scripts/`, `.github/workflows/`, `templates/`, `errors.json` — **take the template's** (that's the product).
- Rendered files (`CATALOG.md`, `docs/TROUBLESHOOTING.md`, `site/`) — take either, then re-render.
- A merge can **resurrect seed plugins you deleted** (e.g. `plugins/company-essentials/` on the first pull) — `git rm -rf` them again; `validate.py` catches any that sneak through as "directory exists but is not listed in marketplace.json".

Then re-render and verify before pushing the PR:

```bash
python3 scripts/apply_config.py
scripts/test_all.sh
git push -u origin update/template-v1.1.0 && gh pr create --fill
```

The usual PR gate (validation, risk lint, drift check, CODEOWNERS review) applies — an update that breaks your instance doesn't merge.

_Roadmap: an `/update-marketplace` command that does all of the above and opens the PR for you; `/status` already flags when your instance lags the template._
