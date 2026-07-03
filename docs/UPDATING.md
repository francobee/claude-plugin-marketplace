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

Conflicts concentrate in files you customized. Rules of thumb:

- `marketplace.config.yml`, `plugins/` — **keep yours** (the template only ships seed content).
- `scripts/`, `.github/workflows/`, `templates/`, `errors.json` — **take the template's** (that's the product).
- Rendered files (`CATALOG.md`, `docs/TROUBLESHOOTING.md`, `site/`) — take either, then re-render.

Then re-render and verify before pushing the PR:

```bash
python3 scripts/apply_config.py
scripts/test_all.sh
git push -u origin update/template-v1.1.0 && gh pr create --fill
```

The usual PR gate (validation, risk lint, drift check, CODEOWNERS review) applies — an update that breaks your instance doesn't merge.

_Roadmap: an `/update-marketplace` command that does all of the above and opens the PR for you; `/status` already flags when your instance lags the template._
