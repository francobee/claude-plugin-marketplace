---
description: Health-check the whole marketplace installation — secrets, Pages, protection, drift, open error issues, template lag — as a plain-English checklist
---

Produce a plain-English health checklist for this marketplace instance. Run from the instance checkout (the repo containing `marketplace.config.yml`). All checks are read-only; follow the `marketplace-admin` skill's safe-gh policy. If `gh auth status` fails, run the local checks anyway and mark the GitHub ones "skipped (not logged in)".

Determine `<org>/<repo>` from `company.github_repo` in `marketplace.config.yml`.

Check, in order:

1. **Config + rendered files**: `python3 scripts/apply_config.py --check`, then run `python3 scripts/apply_config.py` and `git status --porcelain` — a dirty tree means rendered files drifted (fix: commit the render, see TROUBLESHOOTING `CFG-005`; then `git stash` the render if the admin doesn't want it now).
2. **Gates green locally**: `scripts/test_all.sh` (summarize pass/fail count, don't dump output).
3. **Secrets/variables armed** (names only): `gh secret list` and `gh variable list` — report which optional integrations are armed vs dormant (dormant is fine, say so).
4. **Branch protection**: `gh api repos/<org>/<repo>/branches/main/protection` — required checks + code-owner review on? If 404: not protected — point at `/setup` step 5.
5. **Catalog site**: `gh api repos/<org>/<repo>/pages` — report the URL, or "not enabled" with the enable command.
6. **Open failure issues**: `gh issue list --state open --label claude-mgmt` — these are auto-filed error-code issues; list each with its code's one-line fix from `docs/TROUBLESHOOTING.md`.
7. **Template release lag**: latest template release via `gh api repos/francobee/claude-plugin-marketplace/releases/latest`; compare to the newest `## [x.y.z]` heading in this repo's root `CHANGELOG.md`. If behind: recommend the update flow in `docs/UPDATING.md` (merge the tag via PR — never silent).
8. **Fleet health**: ask the admin to paste the latest JumpCloud health-check results (Commands → Results), or skip. Decode any `HEALTH FAIL [CODE]` lines using `docs/TROUBLESHOOTING.md` — code, affected device, fix command.

Output: a checklist with ✅ / ⚠️ / ❌ per item, one line each, then a short "do next" list ordered by impact. No jargon — this reads like an IT runbook result, not a build log.
