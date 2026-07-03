# Tutorial: setting up your company marketplace (for non-technical admins)

*You don't need to know git, YAML, or the terminal. Claude does the technical work; you answer questions and approve. Budget ~20 minutes.*

## What you'll have at the end

- A **private company catalog** of Claude plugins, on your company's GitHub.
- A **security pipeline**: nothing reaches your users without passing eight automated checks and your approval.
- Optionally a **catalog website** (free) and **automatic setup of employee laptops** (if you use an MDM like JumpCloud).

## What you need before starting

1. **A GitHub account that can create a private repository** in your company's GitHub organization. Don't have an organization? A personal private repo works too.
2. **The Claude desktop app** — [claude.ai/download](https://claude.ai/download) (Mac or Windows), signed in with your work email.

That's the whole list. No developer tools — if something's missing on your machine, Claude installs it and tells you what it's doing.

## Step 1 — Open Claude Code

In the desktop app, open **Claude Code** (in the sidebar) and pick any folder when asked (your Documents folder is fine — the wizard creates its own project folder).

## Step 2 — Start the setup wizard

Type these three lines into the message box, one at a time, pressing Enter after each:

```
/plugin marketplace add francobee/claude-plugin-marketplace
```

```
/plugin install marketplace-admin@internal
```

```
/setup
```

## Step 3 — Choose "Quick setup"

The wizard offers **Quick** or **Advanced**. Pick **Quick** — it asks four questions and chooses safe defaults for everything else, then shows you *every* setting in plain English before saving. (Advanced walks through each setting individually, with a one-line explanation next to each — for when you want full control. You can switch any setting later either way.)

The four questions, with suggestions:

| Question | What to answer |
|---|---|
| Company or team name | e.g. `Acme Corp` — display only |
| IT contact email | where "something's wrong" reports go |
| Who approves plugins? | your GitHub username (add teammates later) |
| Catalog website? | **"Yes, free"** is right for almost everyone — see below |

**About the website question:** the catalog site is a nice-to-have browsing page. "Yes, free" hosts it on Cloudflare's free plan (works even though your repo is private, no credit card; you'll click through a 5-step connect at the end — the wizard hands you the exact steps). "Yes, we pay for GitHub" uses GitHub Pages instead. "No" is fine too — the catalog is always readable as a page in the repo itself.

## Step 4 — Let Claude drive, and know what you'll be asked

From here Claude creates the repository, fills in the configuration, runs the full test suite, and opens everything for your review. Things to expect:

- **Claude asks permission before commands.** That's the app working as designed — approve them. Anything destructive is flagged first.
- **A browser window may open for GitHub login.** Sign in there; Claude never sees your password.
- **Secrets (API keys):** Claude will *never ask you to paste a key into the chat*. For optional extras (like Claude reviewing every plugin for hidden attacks — recommended), it prints a short command **for you to run** or a GitHub settings page to open, and the key goes straight to GitHub.
- At the end you get a **health checklist** (`/status`) with ✅ / ⚠️ per item and what, if anything, is left.

## Step 5 — Invite your users

Send your team the **user tutorial** (`docs/TUTORIAL-USER.md` in your new repo — a share-ready page): install the Claude app, two lines to type, done. If your laptops are IT-managed (JumpCloud etc.), users skip even that — `docs/FLEET.md` has the rollout, and the wizard already prepared the payloads.

## Living with it (minutes per week)

- **Someone submits a plugin** → you get a pull request with all security checks already run and annotated. Read the summary, approve or reject. That's the job.
- **Something breaks** → a GitHub issue is filed automatically with an error code and the exact fix. You'll get GitHub's normal email.
- **Change a setting** (name, approvers, website, policy) → tell Claude "change X in my marketplace config" in the repo folder — it edits the one config file, regenerates everything, opens the change for your approval.
- **Monthly**: type `/status` for the health checklist.

## If something goes wrong

- Re-run `/setup` — it detects what's already done and resumes where it stopped.
- Every error has a code (like `CFG-005`) and a lookup table with the fix: `docs/TROUBLESHOOTING.md` in your repo.
- Ask Claude — it has an admin skill loaded with this exact system's runbook. "Why is my catalog site not updating?" gets a real answer.
