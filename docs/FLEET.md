# Fleet rollout (MDM)

Make the marketplace zero-setup for everyone: pre-register it on managed machines so plugins are one `/plugin install` away, with auto-update. Convenience only — pre-registering does **not** block other marketplaces or force any plugin.

## Pre-register via managed settings

Claude Code reads managed settings from a system-level file your MDM (Jamf, Intune, Kandji, JumpCloud, …) can deploy:

- macOS: `/Library/Application Support/ClaudeCode/managed-settings.json`
- Linux: `/etc/claude-code/managed-settings.json`
- Windows: `C:\ProgramData\ClaudeCode\managed-settings.json`

```json
{
  "extraKnownMarketplaces": {
    "internal": {
      "source": {
        "source": "github",
        "repo": "your-org/claude-plugin-marketplace"
      }
    }
  }
}
```

Replace `internal` with your marketplace name (the `name` in `.claude-plugin/marketplace.json`) and `repo` with your fork. Deploy the file with your MDM's file-drop mechanism; Claude Code picks it up on next launch. Verify field names against the current [Claude Code settings docs](https://docs.anthropic.com/en/docs/claude-code/settings) — managed-settings keys evolve.

You can also auto-install core plugins for everyone by deploying `enabledPlugins` in the same file — keep that list tiny (e.g. just `company-essentials`).

## Private-repo access

If the marketplace repo is private, machines need read access without a human logging in:

1. Create a bot/machine account with **read-only** access to the marketplace repo only.
2. Issue a fine-grained PAT scoped to that single repo (contents: read).
3. Deploy a git credential helper via MDM that serves that PAT **only for the marketplace repo URL**, e.g. a static entry in `~/.git-credentials` scoped with `credential.https://github.com/your-org/claude-plugin-marketplace.helper`.
4. Rotate the PAT on a schedule; it can only read plugin markdown, so blast radius is small.

## Update cadence

Installed plugins auto-update when the marketplace repo's main branch moves — which only happens through the gated PR flow. Pulling a plugin = removing its entry from marketplace.json.
