# Claude Code instructions for this repo

Read `AGENTS.md` first — it has the repo facts, the CI-enforced invariants, and step-by-step runbooks for setting up, submitting plugins, and operating this marketplace.

Hard rules:

- Never commit to `main`; always branch + PR.
- Any plugin file change ⇒ version bump in `plugin.json` AND `marketplace.json` + CHANGELOG entry (see AGENTS.md invariant 1).
- Company-specific values live in `marketplace.config.yml` — edit it and run `python3 scripts/apply_config.py`; never hand-edit rendered values (CI drift gate).
- Never hand-edit generated files: `CATALOG.md`, `site/`, `docs/TROUBLESHOOTING.md`, `plugins/*/.scorecard.json`, `plugins/*/.permissions.json`.
- Every scripted failure exits with a code from `errors.json` — add new failure modes there first.
- Before claiming any change works, run: `scripts/test_all.sh`.
