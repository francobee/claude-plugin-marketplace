## Plugin submission

- **Plugin:** <!-- name@version -->
- **Type:** <!-- new / update / vendored import / vendored update -->
- **Declared risk tier:** <!-- tier-1 (markdown only) / tier-2 (read-only shell or allowlisted MCP) / tier-3 (hooks, MCP processes, bin/) -->
- **What it does / who it's for:**

### For tier-2/3 only
List every command executed, endpoint contacted, and file path touched:

### For vendored plugins only
- Upstream: <!-- owner/repo@commit -->
- License:
- [ ] I diffed the imported payload against upstream

### Checklist
- [ ] Version bumped in plugin.json AND marketplace.json
- [ ] CHANGELOG.md entry for this version
- [ ] `python3 scripts/validate.py` + `python3 scripts/risk_lint.py plugins/<name>` pass locally
- [ ] Tested with `claude --plugin-dir plugins/<name>`
- [ ] No secrets, tokens, customer data, or PII anywhere in the diff
