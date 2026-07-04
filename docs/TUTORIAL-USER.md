# Tutorial: using company plugins (for everyone)

*No technical knowledge needed. Ten minutes, once.*

Your IT team runs a **plugin catalog** for Claude: pre-approved add-ons that give Claude extra abilities — company-specific commands, knowledge about your stack, shortcuts for everyday requests. Every plugin in it has been security-checked before you can see it. This tutorial gets you from nothing to using them.

## Step 1 — Install the Claude desktop app

1. Go to [claude.ai/download](https://claude.ai/download) and install the app (Mac or Windows).
2. Open it and **sign in with your work email**.

Already use Claude in the browser or terminal? That works too — every command below is the same everywhere.

## Step 2 — Open Claude Code

In the desktop app, open **Claude Code** (in the sidebar). It will ask you to pick a folder — pick any folder you work in (or your home folder; it just needs somewhere to start).

You'll see a message box. Everything below is typed there.

## Step 3 — Is your laptop company-managed?

**If IT manages your laptop** (they installed Claude for you): the catalog is already connected and your starter plugins are already installed. **Skip to step 5.**

Not sure? Type `/plugin` and press Enter — if you see your company's marketplace listed, you're managed. 

## Step 4 — Connect and install (unmanaged laptops)

<!-- gen:tutorial-user-install -->
Type this into the message box and press Enter (one line at a time):

```
/plugin marketplace add francobee/claude-plugin-marketplace
```

```
/plugin install company-essentials@internal
```

The first line connects you to the company catalog (you only ever do it once). The second installs a plugin — swap `company-essentials` for any name from your catalog.
<!-- /gen:tutorial-user-install -->

> If Claude asks you to log in to GitHub the first time: follow the prompt in your browser using your work GitHub account. If you don't have one, ask IT — takes them a minute.

## Step 5 — Use it

- Type **`/`** in the message box — a menu of every command you now have pops up. Try one.
- Plugins also work invisibly: Claude simply *knows* company things (your tools, your conventions) when it's relevant.
- **Updates are automatic.** When IT publishes a new version, you get it the next time Claude refreshes the catalog (usually within a day, or right after a restart) — nothing to re-install, ever.

## Browsing what's available

- Type `/plugin` → browse the marketplace right inside Claude, or
- Open the catalog: your marketplace repo's **CATALOG.md** page (or the catalog website if IT enabled one — ask them for the link).

## Something broken? Want a plugin that doesn't exist?

Open an issue on the marketplace repo — there are fill-in-the-blanks forms for **"plugin request"** and **"plugin bug"** — or just tell your IT team. You'll never be asked to fix anything yourself: if a plugin misbehaves, IT pulls it centrally and it disappears from everyone's Claude on the next sync.

## Quick answers

| Question | Answer |
|---|---|
| Do I need to update plugins? | No — automatic. |
| Is this safe? | Every plugin passes eight automated security checks and a human review before it reaches you. |
| Can I install plugins from elsewhere? | Company laptops may be locked to the company catalog on purpose. Ask IT. |
| I typed `/` and see nothing new | Restart Claude Code once after your first install. Still nothing? Tell IT — they have a health check for this. |
