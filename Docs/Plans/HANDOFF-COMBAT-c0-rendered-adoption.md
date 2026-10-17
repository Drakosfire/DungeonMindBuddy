# COMBAT: rendered adoption of durable C0

**Status:** BLOCKED — bounded adoption contract prepared under PRIME direction; no runtime, migration, or database write lease is active.
**Contract owner:** DOGFOOD authors the acceptance plan; PRIME owns activation and release of the shared API runtime; APP-STATE owns confirmation of the database target and backup/restore boundary.
**Base:** Buddy main at 3a3f119d86e4ad889f289bd65d1d54ea61513136, verified after fetching origin/main on 2026-10-17. Re-fetch and pin the exact main SHA at activation.
**Topology:** Serial with PRIME’s current API 8000 adoption. This contract does not run while that lease is active. One focused contract PR; C0 implementation remains merged PR #1327.
**Purpose:** Prove the merged C0 encounter flow in the rendered product and its owning persistence boundary without writing a test encounter into Elderwyld or disturbing current Ingest/Build work.

## 1. Scope and non-goals

This slice adopts and verifies **C0 only**: durable World-owned encounter drafts with explicit create/list/open/save/reopen, revision-checked writes, pinned generic manual-tracking ruleset snapshots, and generated-statblock insertion into a selected encounter.

It does not deliver graph-backed creature selection (C1), the full prototype command-board behavior (C2), Play continuity (C3), or configured D&D 5e projection and end-to-end readiness (C4). It does not resolve Ingest extraction issues, change the user’s World Graph, or claim that Combat is complete.

## 2. Completed predecessor

Combat PR #1327, “COMBAT: persist World-owned encounter drafts,” merged on 2026-10-17 at 3a3f119d86e4ad889f289bd65d1d54ea61513136. Its reviewed source head was dc950284a2987554255ca0b47903a8f0878db43b. The PR records 34 backend tests, 16 focused UI tests, TypeScript checks, a production build, Ruff, and diff checks as passing. Rendered desktop/narrow and live adoption were explicitly left open. These checks do not prove the current server or database has adopted C0.

The C0 source adds migration 20261017_0031, descending from 20261017_0030. It creates schema combat, table combat.encounter, and the world/recent index. Its downgrade refuses to run while encounter rows exist; when empty it drops the index, table, and schema.

## 3. Observed serving state and preservation

Read-only inspection on 2026-10-17 found:

- The 5202 Node process and API 8000 process both use /home/drakosfire/.codex/worktrees/buddy-tool-denial-delivery/DungeonMindBuddy, branch codex/harness-runtime-coherence at 7bc8c515e1b89130f9e264fc8ca8400ac9c407e8.
- That checkout has a modified tracked file at evals/c2_live_prep/live/session_22/hermes_thread_pointers.json. Preserve it byte-for-byte; do not switch, reset, stash, or edit this checkout.
- The browser was open to 5202 Ingest, Session 10. Treat that operator session as live user work; do not interrupt it during PRIME’s API adoption.
- API 8001 is a separate Python process whose working directory is /home/drakosfire/.local/state/dungeonmindbuddy/runtime-config. Its source, configuration, and database target have not been identified. Leave it untouched until its owner and role are established.
- PRIME owns the current API 8000 adoption to the reviewed pre-Combat release at 7bc8c515… and is keeping the 5202 UI unchanged. This contract waits for PRIME to release that runtime lease.
- The current APP-STATE database identity and Alembic revision have not been read. The code’s parent revision 0030 is not proof that the live database is at 0030.

The earlier app-import failure involving generationengine and ImageOptions is historical evidence only. The actual retained API now serves MEDIA routes. At activation, check startup/import against the exact candidate and installed environment; do not treat the old report as a current blocker unless it reproduces.

No repository-owned database backup/restore helper was found in the current main file inventory. Identify the actual operator-owned backup mechanism and exact target before activation; do not improvise a command against a live DSN.

## 4. Gates before activation

### Runtime ownership

1. PRIME explicitly releases the API 8000 adoption lease and records its resulting commit and state.
2. Recheck listeners, process working directories, current 5202 source branch, proxy target, dirty files, and open PR/lease collisions. The plan reuses the existing operator runtime after that check; do not start a parallel API or switch the dirty checkout.
3. Preserve the user’s open Ingest/Build work. Restart only after the safety preflight confirms that the active UI state is saved or otherwise safe to interrupt. Existing operator restart authority applies after this concrete preflight; no additional approval-only wait is required.
4. Confirm that the exact current-main API can import and start with its effective .env configuration without printing secrets. Verify the migration entry point and API/UI pairing before touching the database.

### Database and source preservation

1. Identify the exact APP-STATE database/owner and read its current Alembic revision without mutation. Require revision 20261017_0030 before applying 0031. If it differs, stop and re-anchor the migration plan.
2. PRIME reports a 0030 backup/restore rehearsal for Agent adoption. Do not assume it is reusable. Verify its exact database identity, timestamp, post-backup writes, retained location, integrity, and restore result. If any element is unknown or state changed, take a fresh full backup and prove restore into a separate disposable database. Keep backup data outside Git and do not expose credentials.
3. Before applying 0031, inventory the effective DUNGEONMIND_LIVE_SESSION_DIR and checksum current combat, named saves, and backups. C0 does not import, rewrite, delete, or reinterpret those files; preserve their bytes.
4. Apply only 20261017_0031 after a successful rehearsal and confirm the resulting schema/revision through the owning persistence boundary. Do not alter World Graph data.

### Isolated acceptance target

Use a disposable APP-STATE database and a synthetic, verified managed World binding dedicated to acceptance. Do not create or retain a test encounter in Elderwyld. The acceptance target must exercise the real UI/API route pairing while remaining isolated from user data. Pin its exact configuration and cleanup/retention plan in the activation record. If the current 5202 wiring cannot target that isolation safely, stop; do not fall back to a write in Elderwyld.

### Rendered and persistence acceptance

At the owning UI/API boundary:

1. At desktop and 390px narrow width, open Combat and confirm the C0 encounter controls fit, remain legible, and preserve the shared surface shell.
2. Create a named encounter in the synthetic World. Confirm it appears in the explicit encounter list without replacing another encounter.
3. Open it, insert one known generated statblock revision into the explicitly selected encounter, and verify exact source/statblock revision provenance and the returned encounter revision.
4. Edit C0-supported values, save explicitly, refresh the UI, reopen the same encounter ID, and verify the saved values and pinned ruleset snapshot/digest survive. Repeat the readback after the authorized API restart if the isolated target and lease permit it.
5. Exercise stale expected_revision rejection at the API boundary and verify the committed record remains unchanged. Preserve the UI conflict/reload path when a stale write is surfaced.
6. Inspect the final rendered desktop/narrow result and record evidence, exact commits, schema revision, and limits. Do not infer C1–C4 behavior from this C0 proof.

## 5. Stop and rollback

Stop before migration or UI/API replacement if PRIME has not released the runtime lease, 5202 is still carrying unsaved operator work, the process/DB identity is ambiguous, the DB revision is not 0030, backup freshness or restore proof fails, the synthetic acceptance target is not isolated, the exact candidate fails real startup, or the UI is not paired to the intended API.

Prefer application rollback: restore the previously accepted API/UI source while leaving the additive combat schema and any encounter rows intact. Never downgrade 0031 while combat.encounter contains rows; the migration itself rejects that. A database restore is allowed only from the verified backup with no unaccounted writes since capture and a recorded preservation plan. Do not remove legacy save files or use them as implicit encounter authority.

## 6. Ownership and activation

- PRIME: release API 8000; record the accepted source and runtime state; activate this contract only after the gates are satisfied.
- APP-STATE: identify the exact database owner/revision and attest to backup/restore evidence.
- DOGFOOD: after lease release, perform read-only target identification, freshness verification, disposable restore rehearsal, isolated acceptance-target design, and rendered C0 acceptance within the activated lease.
- No source-code paths are leased by this BLOCKED contract. The only planned runtime write is the isolated acceptance database; the only potential live schema operation is 0031 after explicit activation and a successful safety preflight. The 5202 source checkout and API 8001 are excluded until ownership is established.

**Activation requirements:** replace unknowns with exact process/port, database identity, revision, backup path/hash and restore evidence, isolated target, branch/commit, path/resource allowlist, stop/rollback procedure, and PR topology. PRIME must change the handoff to ACTIVE and pin those values before any runtime or database write. Until then, this document grants no migration, restart, or user-data write authority.
