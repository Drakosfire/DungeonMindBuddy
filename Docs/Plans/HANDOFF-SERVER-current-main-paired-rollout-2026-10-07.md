# SERVER current-main paired rollout proposal — 2026-10-07

Status: **REVIEW READY; NOT ACTIVATED**. PRIME owns funding, independent review, and any later live execution lease. This packet authorizes no live migration, process restart, provider call, or data mutation.

## Decision requested

Review a single coordinated Buddy/Core code and schema rollout from the inspected UI checkpoint to current Buddy main plus the reviewed Plan conversation presentation. The release must preserve the current graph corpus, profiles, live-session state, and rollback path. A Buddy-only schema upgrade is insufficient: current Buddy main pins DungeonMind Core `5d4e98963991995bdc280e57df52b8d0fe8de79e`, whose graph authority database needs six migrations.

## Pinned candidate and ownership

- Buddy remote `main` re-anchored at `3d59386fd4868e5b365fd8b6210cfa8ea909e78b` (includes #1012 and #1011 design). Candidate branch: `codex/server-current-main-rollout-candidate`. Its final implementation head and tree are recorded in the PR/branch review packet; recheck both before activation.
- UI content is copied byte-for-byte from reviewed DOGFOOD #1007 head `aeda767c6c9dd785ce2e4344e17615e9efd439c7`: the three Plan conversation component/style files and owning world-history test. #1007 remains open; reconcile any later merge before executing.
- The only additional executable path is `scripts/current_main_rollout_backup.py`, a paired backup helper. It does not deploy, migrate, stop services, or call providers. Its source schema and database identity checks are deliberately specific to this one rollout.
- The currently inspected live Buddy code is detached `f6e7d0ef0dabb8f13690f3b3161f204df167927e` (UI-only checkpoint). The current live Buddy schema is `20261005_0017`, and the live Core graph authority schema is `0007_reviewed_world_init`. No backend rollout has occurred.
- Buddy owns the product API and application-state migration. DungeonMind Core owns the graph authority migration. `DungeonOverMind` owns any cross-repository sequence change; this packet changes neither owner contract.

## Exact schema pair and rehearsal

| Store | Source | Candidate target | Migration source |
| --- | --- | --- | --- |
| Buddy application state, `dungeonbuddy_application_state` | `20261005_0017` | `20261007_0018` | Buddy `application_state` CLI in candidate |
| DungeonMind graph authority, `dungeonmind_cutover_live` | `0007_reviewed_world_init` | `0013_adopted_withdrawal_v1` | Core `5d4e98963991995bdc280e57df52b8d0fe8de79e`, revisions 0008–0013 |

Private, read-only live `pg_dump` copies were restored into disposable PostgreSQL 16 instances (Core used pgvector 0.8.6, matching the live extension environment). All preexisting table rows matched their live source before the rehearsal: Buddy 16 tables / 112 rows; Core 21 tables / 549 rows. Both upgrades reached their target heads. Every preexisting data table still matched the source by canonical row hash: Buddy 15 data tables / 111 rows; Core 20 / 548. Clean downgrades back to 0017/0007 also succeeded with zero preexisting data differences. A second upgraded pair was then dropped and restored from paired backups; the restored old heads and all 16/21 preexisting tables again matched source with zero differences. Private rehearsal artifacts live under `/tmp/dmb-current-main-rehearsal-5o8gafzy/`; they must not be committed or published.

The Core migrations add authority tables; they do not alter existing corpus tables. This observation is from the exact pinned Core migration source and the disposable clone, not a claim that a future live upgrade is risk-free.

## Backup and rollback contract for a funded execution lease

1. Re-anchor Buddy main, #1007, relevant open PRs, exact Core pin, live process/code identity, both live schema heads, database identities, and all open application-state turns/actions. If any differs, stop and revise this packet before touching live state. The #1011 indexed-completion design is merged, but its implementation successor is separate; a new schema or runtime change in that lane invalidates this exact candidate.
2. Stop writes and record process IDs, detached runtime head/tree, environment fingerprint without secret values, active ports, corpus/profile and artifact counts, and live health. Acquire an exclusive operational lease covering Buddy API, UI, both databases, and runtime files. Do not let another owner restart or migrate them during this sequence.
3. Run the paired backup helper under that lease. Verify its private manifest, SHA-256 of both custom-format dumps, `pg_restore --list` inventories, preserved file archive, and free-space gate. Keep the backups outside Git with owner-only permissions. Rehearsal of the helper against disposable source-schema databases produced both dumps, inventories, file archive, and manifest successfully.
4. Recreate the isolated candidate environment with `uv sync --locked` and the pinned patched Hermes 0.18.2 local source. The rehearsal environment installed exact Core 5d; package `direct_url.json` identified that commit. Run the Buddy 0018 and Core 0008–0013 upgrades only against their named databases. Check both version heads and preexisting table counts/hashes before starting services.
5. Switch the Buddy runtime code to the exact reviewed candidate and restart the owned processes. Validate UI/API health, read-only graph retrieval, Plan history, corpus/profile visibility, and the user-facing inspection path. Provider calls require separate explicit authorization.
6. If a gate fails, stop services and restore **both** database backups and preserved runtime/file state as one unit, then restore the prior detached code and verify old heads and health before reopening writes. The clean downgrade result is a rehearsal fact, not the production rollback mechanism: Buddy 0018 and Core's new authority tables guard against downgrading once new rows exist. Do not restart from a partially restored pair.

## Acceptance witness and stop conditions

- UI: Node 24 production Vite/TypeScript build passed (671 modules); all 109 owning Plan conversation tests passed after the #1011 rebase. The resulting asset remained `index-B3AE5OTA.js`.
- Environment: `uv lock --check` passed with an isolated cache; the installed DungeonMind package's `direct_url.json` identifies exact Core commit 5d4e98963991995bdc280e57df52b8d0fe8de79e.
- Backup helper: Ruff and Python compilation passed; an end-to-end disposable fixture verified source heads, both dumps, inventories, private archive, and manifest.
- Migration: exact Core 5d and Buddy candidate upgrades, clean downgrades, and paired backup restores passed on disposable copies with zero prior-row differences.
- Stop for an altered schema head, unexpected DB identity, stale Core pin, new overlapping APP-STATE implementation, dirty/live state change, active write, failed backup checksum/inventory, migration error, row mismatch, or missing rollback artifact. Stop rather than broadening this lease into schema repair or corpus reconstruction.

No acceptance token is asserted. PRIME's independent review and funding decision precede any live activation.
