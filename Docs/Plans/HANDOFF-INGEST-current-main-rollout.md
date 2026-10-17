# INGEST: refresh and verify a matched-main runtime for 5202

**Status:** ACTIVE for the exact rollout below. PRIME explicitly authorized refreshing the existing non-serving a044 candidate, resolving its independent runtime dependencies, checking migration 0030/shared-reader compatibility, and using standing same-port restart authority once all gates pass. This supersedes the preparation-only limits in the merged #1341 handoff.
**Authority:** PRIME direction received 2026-10-17. No further operator approval is needed for the bounded preparation, backup, dependency repair, compatible migration, and matched-main 5202/8000 rollout described here.
**Source:** Current main is 6c438883fc71ccb36dbb96fc910dfa8d7403dbec. The only change after runtime source af6779d00155d4e7cfca6859295b381df1ea7e1d is the #1341 operational handoff; use exact tracked runtime source at af6779d, tree 01e03adca73b811057dbae81cb9634ebe38647fc.
**Topology:** Serial successor to merged #1341. This contract and rollout occupy one Ingest transition slice; no new product-code PR or source publication is authorized.

## Dogfood readiness

The currently served 5202 UI/API are stale and are not ready for real recap processing or acceptance. The route for Elderwyld Session 10 showed Session 27 selected in the prior-processed-recap area with stale/unverified lineage, while the source editor was blank. The user may give visual feedback on this old screen, but exact-session selection, processing, retry, review, and persistence must be judged only after the matched-main runtime is live.

When matched-main is ready, invite the operator to use the real Session 10 recap in its exact campaign/session: load or paste the source, process it, inspect the enriched node-bearing projection and linked evidence, open its exact review, and verify reopening. Normal mode should present enriched nodes, with raw Markdown available only through Advanced. Publication remains a separate action; this rollout does not publish source observations or graph assertions on the operator’s behalf.

## Exact lease and forbidden state

The only source/runtime candidate that may be changed is the existing non-serving candidate:

- Source: /home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-a044ac4e/source
- Runtime: /home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-a044ac4e/runtime
- Candidate root for rollback snapshots, manifests, logs and the fresh pre-migration database backup: /home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-a044ac4e/

The source candidate currently corresponds to a044ac4eed88919fb4f13b63f959714aaa58d62b (tree fb759a6f72d11f2470f22a0216d7aeca21f3cbdf), with 7,565 files / 300,275,544 bytes. Before refresh, the full source is archived at source-pre-refresh-af6779d.tar.zst (SHA-256 3352ab79447ac2a90ea4eaa83daa1d4fd1e7bb2eb7884c37b3e6053a68a3362a), and the full runtime at runtime-pre-refresh-af6779d.tar.zst (SHA-256 a3f934c61675cf0aa0088e3254c9c4b40d36d9a08b59e3e559b62e98fe7d9980). Source/runtime inventories and package freeze are also recorded in the existing candidate root. The source contains three symlinks: apps/live-control-ui/dist and apps/live-control-ui/node_modules point into the separate buddy-main-ed7fc846 candidate, while out/hermes-agent points to /home/drakosfire/.local/state/dungeonmindbuddy/nonlive-graph-review-ec1da1b/hermes-agent. Preserve all links and targets unchanged; the main uv.lock resolves Hermes from that local path. The candidate has a local node_modules cache directory as well; preserve it without using it as a source dependency. Refresh tracked application source to exact af6779d, removing only tracked paths deleted between a044ac4 and af6779d; leave all untracked local inputs intact. Do not make another checkout, source export, worktree, environment, candidate, or candidate root. The runtime’s Python interpreter symlink resolves to the shared uv-managed Python 3.13.12, while its site-packages are independent. Resolve every symlink before writing; the runtime must remain isolated from active e778.

Use the existing shared package cache only to install the exact dependency lock for af6779d into the existing a044 runtime. Do not mutate another runtime or shared package cache. Do not print or copy secrets. Keep the project .env read-only and the existing user source, graph, conversation, and ingestion state intact.

The prepared UI bundle and rollback copy remain read-only at /home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-af6779d/ui-dist and rollback-5202-ui-dist. Verify the prepared bundle manifest still corresponds to af6779d before serving it.

Only these existing user services may be stopped/restarted/reconfigured for the matched-main same-port transition:
- dungeonmindbuddy-dogfood-ui-main-cb11bf86.service on 5202
- dungeonmindbuddy-dogfood-api-main-cb11bf86.service on 8000
- dungeonmindbuddy-main-ui-main-892cc46b.service on 5876
- dungeonmindbuddy-main-api-main-01980f14.service on 8002

The 8000 and 8002 APIs share the configured .env and durable data roots. Before a schema change, stop the old 8002 reader/writer and verify it is down; do not leave old application code running against the upgraded schema. Preserve prior unit definitions, executable identities, bundle hashes, runtime inventory, and health evidence for rollback. Keep the publication service on 8001 unchanged.

Do not alter the dirty 996b checkout, the dirty PRIME cited-writer checkout, any other candidate/runtime, service unrelated to the four listed above, project .env, durable source/World/Conversation data, or publication state.

## Gates before rollout

1. Re-anchor to the source and runtime pins above. Confirm the a044 source/runtime paths and their resolved targets; prove no serving process consumes them. Capture checksums and a recoverable archive of the source tree and runtime package inventory before mutation. Preserve out/hermes-agent as an input.
2. Refresh tracked source to exact af6779d without modifying the source or runtime identity paths. Confirm tree provenance and preserved local input hashes.
3. Read the exact committed dependency lock. Install only its locked packages into the existing isolated runtime, using the shared package cache. Verify package versions, required imports, generationengine provenance/pin, and API startup. A passing health check alone is insufficient.
4. Record current database revision, relevant agent.turn counts, and integrity checks. Confirm the existing schema is 20261017_0029 and the exact main head is 20261017_0030. Create and verify a fresh restorable backup under the existing a044 candidate root before any migration. Preserve the older app-pre-0029-20261017T083129Z.dump unchanged.
5. Prove migration 0029→0030 source and rollback behavior. The exact main migration drops and recreates only the agent.turn graph-completion CHECK constraint to admit a typed Build-authoring completion; it contains no data UPDATE/DELETE. PostgreSQL will validate existing rows when adding the constraint, so verify it succeeds and record row counts/data before and after. Exact main ends at 0030; do not apply 0031 from the dirty Combat checkout. Stop both old APIs (8000 and 8002) before migration. Apply only against the configured database after backup verification; verify schema 0030, integrity, and preserved row counts/data. If migration or startup fails before new user writes, restore through the captured rollback plan and verify the prior 0029 state.
6. Verify the prepared UI bundle’s hashes and exact source pin. Run the candidate API with the existing .env and isolated a044 runtime before switching ports; verify startup, required imports, and readiness. Capture rollback unit definitions and old UI/API identities.
7. Only after all gates pass, stop incompatible 5876/8002 and switch 5202/8000 to the matched-main UI/API. Confirm served JavaScript hash, API source/runtime identity, health/readiness, and a rendered Session 10 route with no Session 27 preselection. Keep existing data roots. Do not process the real recap automatically.
8. Ask the operator to dogfood Session 10. If the route, candidate/evidence view, exact review, or reopening fails, preserve the source and trace and repair the in-scope Ingest defect before declaring readiness. Publication is explicitly out of scope.

## Prior preparation and known blockers

The merged #1341 record identified the active 5202/8000 pair as using the dirty 996b checkout and stale UI asset, and the alternate 5876/8002 pair as sharing the same durable data. It prepared the exact af6779d UI bundle and byte-identical 5202 UI rollback copy, but did not establish runtime compatibility or grant a runtime mutation lease. Those two gates are addressed here.

Read-only preflight found the database at 20261017_0029 while main requires 20261017_0030. The existing e778 runtime cannot import current main: startup probe failed at apps/live_control_server/routes/media_images.py because generationengine lacks ImageOptions. It also lacks aiofiles, asyncstdlib, fal-client, httpx-sse, msgpack, and typesafe-sdk. Do not run current main source on e778. The a044 runtime has its own site-packages and is not currently serving; re-verify all paths and consumers before using it.

Previous escalation attempts without host permissions failed to access the user systemd bus or localhost; the approved host execution path is required for service and database checks. Preserve command failures and exact compatibility errors in the rollout evidence.

## Completion evidence

Record exact source/tree and runtime/package hashes, backup integrity, before/after schema and row counts, migration result, service/process identities, served UI digest, API startup/readiness, and rendered Session 10 acceptance. Do not report real ingestion success until the operator’s actual recap is processed and the exact candidate/review can be reopened.