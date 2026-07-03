# Claude Code instructions for this repo

Read `AGENTS.md` first — it has the repo facts, the CI-enforced invariants, and step-by-step runbooks for setting up, submitting plugins, and operating this marketplace.

Hard rules:

- Never commit to `main`; always branch + PR.
- Any plugin file change ⇒ version bump in `plugin.json` AND `marketplace.json` + CHANGELOG entry (see AGENTS.md invariant 1).
- Never hand-edit generated files: `CATALOG.md`, `site/`, `plugins/*/.scorecard.json`.
- Before claiming any change works, run: `python3 scripts/validate.py && python3 scripts/risk_lint.py && python3 scripts/smoke_test.py`.
