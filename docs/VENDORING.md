# Vendoring external plugins

Found a great plugin/skill on GitHub? Vendor it in so everyone gets the scanned, pinned, supported version.

## Flow

```bash
./scripts/vendor_import.sh https://github.com/owner/repo [subdir]   # or /vendor-plugin
```

The importer:

1. Clones at a **pinned commit** — the marketplace never tracks a moving branch.
2. Gates on license: MIT / Apache-2.0 / BSD / ISC / MPL-2.0 pass; GPL-family or no license is a hard stop (admin sign-off required).
3. Copies only the plugin payload (strips upstream CI, tests, VCS).
4. Writes `plugins/<name>/.upstream.json` — the sidecar that drives catalog star counts, scorecard freshness, and the weekly upstream watch.

Then: **review every imported file as if it were written from scratch**, add the marketplace.json entry (tags must include `vendored` + the correct tier), run `/validate-plugin`, open the PR.

## Staying current

The `upstream-watch` workflow runs weekly:

- Compares each pinned commit against the upstream HEAD.
- On drift, it re-imports the payload at the new commit on a branch, re-runs all scanners, and opens a **ready-to-review PR** (with version bump + changelog entry handled).
- If the auto-import fails, it opens an issue instead.

Auto-update PRs still go through the full CI gate and human review — automation prepares the diff, never merges it.
