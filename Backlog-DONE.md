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

## [DONE] Permanently delete a statblock from Build — 2026-11-28

The World-scoped Build toolbar permanently deletes the selected statblock's
live mechanics revisions and exclusively owned published portrait. Buddy retains
an identifier-only receipt so retries are safe and old revision links report
that the statblock was deleted. The World creature, source PDF and review,
shared artwork, and saved encounters remain independently owned.

Hosted Buddy deployed revision `114db4321a73` on App schema `20261128_0218`.
In Buddy Cloud Pilot, the disposable illustrated Clockwork Mote had two published
mechanics revisions. The toolbar returned HTTP 204 and left a usable Build.
The picker omitted the statblock after reload. Both old URLs showed the deleted
message and their Buddy APIs returned HTTP 410. DungeonMindServer returned HTTP
404 for both exact revisions. The App storage check found zero retained
revision-operation rows and zero published portrait rows for the deleted
statblock, with the completed receipt present. The source review still held its
artwork, the creature opened in Graph, an unrelated saved statblock opened, and
Buddy's runtime read service reopened the existing Pilot encounter.

Permanent deletion applies to live storage. Retained operator-managed backups
can contain pre-deletion copies until their retention period ends. Buddy does
not automatically expire those backups.

[Buddy serving release](https://github.com/Drakosfire/DungeonMindBuddy/pull/5045)
· [Hosted deployment](https://github.com/Drakosfire/DungeonMindBuddy/actions/runs/46182915359)
· [Producer deletion](https://github.com/Drakosfire/DungeonMindServer/pull/57)

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

## [DONE] Delete the current Build page — 2026-11-28

This entry records the hosted verification of page Trash and statblock archival.
[Permanent statblock deletion](Backlog.md#permanently-delete-a-statblock-from-build) remains open.

Verified both direct toolbar actions in hosted Buddy Cloud Pilot on healthy release
`e217670f9b47f0e0c5f00a95f8afbddad5aea9ce`.
[Deployment evidence](https://github.com/Drakosfire/DungeonMindBuddy/actions/runs/46167726548)

- Page Delete moved the open disposable page to World Trash and returned to the
  Build workspace. Restore removed it from Trash, and reopening its saved URL
  displayed the original content.
- Statblock Delete archived the open disposable Clockwork Mote from discovery
  and returned to Build. After reload, the picker omitted the fixture and still
  listed an unrelated saved page. The exact saved statblock URL still rendered
  its mechanics. The archive has no World Trash restore action.
- The statblock fixture used a saved Workbench revision associated with a
  disposable World creature. This verification did not require PDF review
  writes or a production database grant.
