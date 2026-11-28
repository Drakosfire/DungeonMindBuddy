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

## [DONE] Shared semantic block writing and hosted round trips — 2026-11-23

Buddy uses shared writing guidance for Read Aloud and GM Note blocks. Hosted
benchmarks in Buddy Cloud Pilot verified that the blocks survived Save and
reopen in Build, Plan, and Play. The suite also recorded Ingest source
preservation, Home eligibility, and the Combat no-write control.

The hosted Graph benchmark recovered the original Sealed Tower publication
and selected it in Graph. That surface offered no composer, so the
selected-object no-write control passed with the same Graph revision before
and after. Elderwyld was untouched.

The benchmark suite still tracks full route qualification, including the
remaining live repetitions and quality checks.

- [Benchmark suite](https://github.com/Drakosfire/DungeonMindBuddy/pull/4275) and [shared writing contract](https://github.com/Drakosfire/DungeonMindBuddy/pull/4277)
- [Hosted release](https://github.com/Drakosfire/DungeonMindBuddy/pull/4618) and [benchmark evidence](Docs/Reports/REPORT-semantic-block-writer-observations.md)

## [DONE] Permission-aware guidance for a loaded empty Graph — 2026-11-24

[#4626](https://github.com/Drakosfire/DungeonMindBuddy/pull/4626) shipped on
`386bdf65`. A writable empty Graph prompts users to add an object. A read-only
empty Graph offers an available navigation step. Tests on the deployed source
covered both cases and loading. Hosted smoke checks covered unavailable and
filtered, nonempty Graphs.

## [DONE] Plain-language GM facts review label — 2026-11-24

[#4631](https://github.com/Drakosfire/DungeonMindBuddy/pull/4631) shipped on
`826d6220`. The shared Build and Plan fieldset now uses “Review GM facts” for
its visible legend and accessible name. The saved Pilot review reached
confirmation with its existing evidence. The check stopped before publishing.

## [DONE] Conversation library lifecycle — 2026-11-27

Hosted release `bef1f4b5` on App schema `20261126_0215` defaulted to Recent and
supported deliberate Archive, individual and bulk Trash/Restore, and single and
bulk permanent deletion from Trash. Legacy chats remained accessible. In signed-in
Buddy Cloud Pilot, switching kept prior chats in Recent, an archived chat reopened
with its saved reply, and Restore left the original current chat selected.

After confirming the targets, one disposable chat was deleted individually and two
as a batch. All disappeared after reload. The signed-in transcript route refused
all three, and both export modes in a stale tab refused the individually deleted
chat. Production readback found no associated conversations, turns, traces,
composer drafts, or outstanding erasure-file work. Copper Lantern Post, its
separate artwork fixture, and the published Pilot Graph still opened. Pilot had
no published statblock fixture for this smoke. Production signed-out access returned
401. The exact-source hosted authorization tests covered a synthetic signed-in
non-owner, and focused tests covered command replay and restore/delete conflicts.

Permanent deletion removes live conversation-owned content. Operator-managed
backups may retain copies according to the deployment retention policy. See the
[recovery runbook](Docs/Runbooks/RUNBOOK-application-state-authority-recovery.md#conversation-erasure-and-retained-backups).
The independent hosted Rename issue is tracked separately in [#5011](https://github.com/Drakosfire/DungeonMindBuddy/pull/5011).

- [Backend #4860](https://github.com/Drakosfire/DungeonMindBuddy/pull/4860) and [delete controls #4868](https://github.com/Drakosfire/DungeonMindBuddy/pull/4868)
- [Combined release #5010 and hosted evidence](https://github.com/Drakosfire/DungeonMindBuddy/pull/5010) and [production activation](https://github.com/Drakosfire/DungeonMindBuddy/actions/runs/46104134466)
