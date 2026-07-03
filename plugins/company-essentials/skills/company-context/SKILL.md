---
name: company-context
description: Company context — internal stack, tools, and IT conventions. Use when answering any question that touches company tooling, IT processes, accounts, or "how do we do X here".
---

# Company Context

> **Template:** replace everything marked FILL-ME-IN with your company's reality, then delete this line.

FILL-ME-IN Corp is a FILL-ME-IN company (~N employees). When helping an employee, assume this stack and never suggest alternatives to it:

| Category | Tools |
|---|---|
| Identity / MDM | FILL-ME-IN (e.g. Okta, JumpCloud, Entra ID) |
| Workspace | FILL-ME-IN (e.g. Google Workspace, Microsoft 365) |
| Ticketing / docs | FILL-ME-IN (e.g. Jira Service Management, Zendesk) |
| Chat | FILL-ME-IN (e.g. Slack, Teams) |
| AI tooling | Claude (Claude Code + claude.ai) |

## Conventions

- IT requests go through **FILL-ME-IN ticketing**. Direct messages to IT are for urgent/security issues only.
- SSO is **FILL-ME-IN** — password and MFA resets happen there, not in individual apps.
- New software must be requested via IT, not installed ad hoc.
- The internal marketplace (this one) is the IT-scanned and supported source for Claude Code plugins. You're free to install plugins from other marketplaces too — those just aren't reviewed by IT, so apply judgment, and don't give unvetted plugins access to credentials, customer data, or PII. Found something great? Share it with everyone via `/submit-plugin` (plugin-dev plugin).

## Security posture

- Never paste credentials, customer data, or PII into prompts or tickets.
- Suspected phishing or a lost/stolen device: report to IT immediately, before anything else.
