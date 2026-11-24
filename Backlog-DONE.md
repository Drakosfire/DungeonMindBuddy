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

## [DONE] Semantic block writing and benchmarks — 2026-11-23

Buddy uses shared writing guidance for Read Aloud and GM Note blocks. Hosted
benchmarks in Buddy Cloud Pilot verified that the blocks survived Save and
reopen in Build, Plan, and Play. The suite also recorded Ingest source
preservation, Home eligibility, and the Combat no-write control.

The hosted Graph benchmark recovered the original Sealed Tower publication
and selected it in Graph. That surface offered no composer, so the
selected-object no-write control passed with the same Graph revision before
and after. Elderwyld was untouched.

- [Benchmark suite](https://github.com/Drakosfire/DungeonMindBuddy/pull/4275) and [shared writing contract](https://github.com/Drakosfire/DungeonMindBuddy/pull/4277)
- [Hosted release](https://github.com/Drakosfire/DungeonMindBuddy/pull/4618) and [benchmark evidence](Docs/Reports/REPORT-semantic-block-writer-observations.md)
