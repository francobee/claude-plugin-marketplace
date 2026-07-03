---
description: Summarize my day's work from local git activity into a standup update
---

Produce a short standup update for me.

1. Look at my local git activity from the last working day: `git log --since=yesterday --author="$(git config user.email)" --oneline --all` in the current repo (and mention if the directory isn't a git repo).
2. Group the work into: **Done**, **In progress** (uncommitted changes via `git status --short`), **Blockers** (only if I mention any).
3. Output 3-6 bullet points, terse, paste-ready for Slack. No preamble.
