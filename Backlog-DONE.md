# Completed backlog history

The completed and dropped records formerly kept here are preserved in
[the exact historical log](https://github.com/Drakosfire/DungeonMindBuddy/blob/ea9726ca8e9730f2cea0f7cb323bf190f0c7bf62/Backlog-DONE.md).

- Historical size: 296,911 bytes.
- SHA256: `b2244132d35b5a80cbf89ac1ce7d940d9dde2d8cdc3e8be2a9337c00468c44c3`.

Those dated records describe earlier implementation and verification outcomes.
They do not certify current runtime behavior, deployment readiness, or completion
of the ongoing cleanup audit. Open owner follow-ups remain open.

For current work, consult [the product backlog](Backlog.md), the
[maintenance queue](Docs/Backlog/MAINTENANCE.md), the
[release rehearsal checklist](Docs/Runbooks/RELEASE-REHEARSAL-buddy-checklist.md),
and the owning issues and PRs. Repository operating policy lives in
[AGENTS.md](AGENTS.md).

## [DONE] App-wide theme system — completed 2026-11-20

**Captured:** 2026-09-26. Refined in the 2026-11-14 product discussion.

Buddy ships its original default, Deep Teal, and Wayfinder through shared Appearance settings. Dossier is independently selectable for Build pages, tables, and campaign statblocks. Explicit reader styles keep precedence. Chat can propose a bounded accent change through the same preview and approval flow.

[Wayfinder #4241](https://github.com/Drakosfire/DungeonMindBuddy/pull/4241) and [Dossier #4245](https://github.com/Drakosfire/DungeonMindBuddy/pull/4245) shipped together on hosted release `70f27ff1`. See the [shared appearance design guide](Docs/Design/ARCHITECTURE-surface-interaction-layer.md#appearance-and-authored-content) and [hosted verification report](Docs/Reports/REPORT-wayfinder-hosted-verification.md) for cross-surface checks and matched timing samples.
