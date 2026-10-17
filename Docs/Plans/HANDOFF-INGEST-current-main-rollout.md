# INGEST: prepare and verify a matched-main dogfood rollout

**Status:** ACTIVE for non-disruptive preparation only. PRIME authorized this bounded prep on 2026-10-17. The operator has active work on the shared 5202 preview; do not stop, rebuild in place, or reconfigure 5202/8000 while that work is ongoing. No runtime write lease is active.
**Source:** Buddy `main@af6779d00155d4e7cfca6859295b381df1ea7e1d` (PR #1340, on top of #1333, #1336, and #1339).
**Topology:** one docs-only PR now; matched-main artifact preparation uses the existing clean checkout and rollout state. Any serving-unit switch is a later, separately gated operation after the operator releases Build.

## Why ingestion dogfood is not ready on 5202

The open route is `/ingest?world=elderwyld&campaign=longmont-c2&session=session-10`. The route selector says Session 10 while “Prior processed recap” has Session 27 selected and warns that the normalized recap is stale or its source lineage is unverified. Session 10 is present as an option. The source was not loaded or processed.

Read-only runtime evidence identifies the current serving pair and explains why its label is insufficient:

- `dungeonmindbuddy-dogfood-ui-main-cb11bf86.service` serves port 5202 from the shared `996b` checkout. Its HTML references `/assets/index-CIUSveQG.js`, last modified at 11:15:51 UTC. PR #1333 merged at 11:46:54 UTC, #1339 at 12:27:44 UTC, and #1340 at 12:37:52 UTC. Thus the served UI bundle predates all three changes.
- `dungeonmindbuddy-dogfood-api-main-cb11bf86.service` serves port 8000. It started before those merges; `/health` returned `{"status":"ok"}`, which does not prove the loaded source revision.
- Both processes use the shared checkout, currently branch `codex/combat-c0-durable-encounters` at `fa3e3c9a0b2168db43808743744957e620eb205c`, with dirty Build, Combat, and Ingest work. The active UI serves built `dist`, not the current source tree. Preserve the branch, all dirty files, and that serving bundle.
- `main-cb11bf86` is a historical service label, not proof of current-main source identity.
- The alternate `dungeonmindbuddy-main-ui-main-892cc46b.service` and `dungeonmindbuddy-main-api-main-01980f14.service` pair is active on 5876/8002, but is also an older candidate. The UI serves `index-DU514xbf.js` (SHA-256 `4eb543f769579e8201e4df6bac512eed03e0b256c3dc884b0f01acb03f2928e2`). The API launch script loads the same project `.env` and sets both artifact and managed-World roots to `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy`, as 8000 does; it only changes the local operator profile. Therefore this pair shares durable data with 5202/8000 and is not an isolated ingestion test target. Do not update or process a real recap on 5876/8002.

No recap was loaded or processed. No database, source, ingestion candidate, World Graph, or conversation state was changed; no service was restarted and no build was written into the serving checkout.

## Bounded preparation lease

PRIME designated the existing clean checkout `/home/drakosfire/.codex/worktrees/buddy-tool-denial-delivery/DungeonMindBuddy`, verified clean at exactly `af6779d00155d4e7cfca6859295b381df1ea7e1d`, as read-only source. Its UI `node_modules` symlink points to the shared dirty checkout; use it read-only, with no package install or dependency sync.

The only new build output may be placed under the existing rollout-state root at:

`/home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-af6779d/`

Store the static UI bundle and build/typecheck metadata there, separate from the 5202 `dist`. Do not create another checkout, source export, environment, dependency copy, or temporary directory. Keep the user's prior source/data/World state and the existing `app-pre-0029-20261017T083129Z.dump` unchanged.

The documentation write set for this PR is only:

- `Docs/Plans/HANDOFF-INGEST-current-main-rollout.md` — this operational contract and evidence.

The build may read the pinned source and existing dependency symlink and may write only the output path above. It must not edit either checkout, the shared `node_modules`, the 5202 `dist`, `.env`, runtime configuration, or any retained data. Do not print or copy secret environment values.

## Settlement of merged Ingest slices

- PR #1333 merged at `6531f0038d79431c6265afb3fd01e6d99458cd2b`: exact campaign/session route changes reset and reselect the prior recap by exact identity. The live Session 10/Session 27 mismatch is served-build evidence, not proof the current-main UI regressed.
- PR #1336 merged at `bcaacb31926967ecd9d728182235cd1f276eccbe`: identical Process retries reuse the exact graph run; provider-free recovery preserves immutable candidate bytes for no-op validation. Its synthetic owning suite passed 27 tests; real recap processing and persistence were not exercised.
- PR #1339 merged at `135083b7550fcf02fcf7931eb4cf631e44f38bad`: Graph Review opens the exact processed run and is unavailable without exact run identity. Its focused UI suite passed 65 tests with typecheck and diff-check; this did not prove the serving 5202 asset contains the change.
- PR #1340 advanced main to `af6779d00155d4e7cfca6859295b381df1ea7e1d`; it is an agent acquisition change and does not alter Ingest UI/API behavior.

## Preparation and verification

1. Keep the 5202/8000 services unchanged while Build is active. Record unit, PID, source, bundle digest, configuration identity without secrets, schema/version, and the existing data-root fingerprints before any later switch.
2. Build and typecheck exact `af6779d` into the separate output path, keeping compiler cache files there as well. **Prepared:** `tsc --noEmit` passed for app and node configs; Vite 6.4.2 built 707 modules successfully. The existing chunk-size warning remains. Output is under `rollout-candidates/buddy-main-af6779d/ui-dist`; `build-manifest.json` records the commit/tree, commands, cache path, asset names, and SHA-256 digests. Main JS is `index-dgaQSK7d.js` (SHA-256 `d6f78dd9410c353733c2d58aaaf4ee59a4758fd9151e7347fd731a7d3cf23ece`). No 5202 bundle or service was changed.
3. **5876/8002 check complete:** both old-candidate services are active, but 8002 points at the same `.env` and durable data roots as 8000. This is a shared-data hazard, so do not update those units or use them for real-recap acceptance.
4. Before a later serving switch, verify that the operator has released Build, capture read-only persistence baselines, and preserve the exact previous bundle and service identities for rollback. Reuse the configured `.env`, runtime, and managed data roots; no migration or reset is authorized by this handoff.

## Rendered acceptance before real recap dogfood

On the matched-main runtime, verify the exact Session 10 route at desktop and narrow widths. The selected processed recap must match campaign and session exactly or stay empty; it must never preselect Session 27. Confirm source-lineage warnings, load/process actions, retry recovery, exact Graph Review navigation, and the stable document/review surface while tools open. Then compare before/after persistence fingerprints and prove the UI/API source identities match this handoff. Only after these checks should the operator run a real recap. Record candidate, evidence, review, and persistence outcomes without publishing to the World Graph unless separately authorized.

This preparation is not live ingestion acceptance. The 5202 served JS SHA is `5056a7fa2397bd59aa54da90bc7374c2b5a1f9ebbbe1bddfc68528689718d132`, which differs from the prepared main JS bundle. The route discrepancy, stale served bundle, and pre-merge API process remain open until rendered matched-main behavior and the owning persistence boundary are verified.
