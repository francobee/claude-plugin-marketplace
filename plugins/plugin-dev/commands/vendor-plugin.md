---
description: Import a plugin or skill from a public GitHub repo into the marketplace
argument-hint: <github-url> [subdir]
---

Vendor a public GitHub plugin into the marketplace: $ARGUMENTS

1. Locate the local marketplace repo checkout (a directory containing `.claude-plugin/marketplace.json` alongside a `plugins/` directory).
2. From the repo root, run: `./scripts/vendor_import.sh <github-url> [subdir]`. It clones at a pinned commit, gates on license (MIT/Apache-2.0/BSD/ISC/MPL-2.0 allowed; GPL/AGPL/none = hard stop → admin sign-off required), copies only the plugin payload, and writes `plugins/<name>/.upstream.json` (drives star counts in the catalog and weekly upstream-drift checks).
3. Review the imported payload WITH the user before opening a PR — especially any hooks, `.mcp.json`, or scripts. Vendored code is reviewed as if written from scratch.
4. Run `/validate-plugin` on it, fix findings, then open a PR. Note in the PR that you diffed the payload against upstream.
