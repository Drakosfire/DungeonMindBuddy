# INGEST: refresh and verify a matched-main runtime for 5202

**Status:** ACTIVE for the exact rollout below. PRIME explicitly authorized refreshing the existing non-serving a044 candidate, resolving its independent runtime dependencies, checking migration 0030/shared-reader compatibility, and using standing same-port restart authority once all gates pass. This supersedes the preparation-only limits in the merged #1341 handoff.
**Authority:** PRIME direction received 2026-10-17. No further operator approval is needed for the bounded preparation, backup, dependency repair, compatible migration, and matched-main 5202/8000 rollout described here.
**Source:** Current main is 2f43bbffd5dfe042a5a913bd49efa94d0d3898f1, tree b8f437730e5f3020798ebb9627a95134acd8f812. It includes the reviewed #1342 cited-writer source changes. Comparison of af6779d to 2f43bbf shows 12 changed paths, all agent source/tests/handoffs; pyproject.toml, uv.lock, migrations and live-control UI are unchanged. Refresh the runtime source to exact current main; retain the already-built af6779d UI only after confirming the current main UI tree is identical.
**Topology:** Serial successor to merged #1341. This contract and rollout occupy one Ingest transition slice; no new product-code PR or source publication is authorized.

## Dogfood readiness

The currently served 5202 UI/API are stale and are not ready for real recap processing or acceptance. The route for Elderwyld Session 10 showed Session 27 selected in the prior-processed-recap area with stale/unverified lineage, while the source editor was blank. The user may give visual feedback on this old screen, but exact-session selection, processing, retry, review, and persistence must be judged only after the matched-main runtime is live.

When matched-main is ready, invite the operator to use the real Session 10 recap in its exact campaign/session: load or paste the source, process it, inspect the enriched node-bearing projection and linked evidence, open its exact review, and verify reopening. Normal mode should present enriched nodes, with raw Markdown available only through Advanced. Publication remains a separate action; this rollout does not publish source observations or graph assertions on the operator’s behalf.

## Exact lease and forbidden state

The only source/runtime candidate that may be changed is the existing non-serving candidate:

- Source: /home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-a044ac4e/source
- Runtime: /home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-a044ac4e/runtime
- Candidate root for rollback snapshots, manifests, logs and the fresh pre-migration database backup: /home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-a044ac4e/

The source candidate originally corresponds to a044ac4eed88919fb4f13b63f959714aaa58d62b (tree fb759a6f72d11f2470f22a0216d7aeca21f3cbdf), 7,565 files / 300,275,544 bytes; tracked files match that Git commit except one locally modified eval pointer. Git refs reconstruct the tracked source, so do not retain full duplicate source/runtime archives. Before refresh, preserve the single local tracked delta outside source, the untracked-input/symlink manifest, original source pin/lock hashes, and runtime package/freeze/direct-URL inventory. The local eval delta is evals/c2_live_prep/live/session_22/hermes_thread_pointers.json; keep its exact bytes in the existing candidate root as a sidecar, not over the refreshed main file. There are three source symlinks: apps/live-control-ui/dist and apps/live-control-ui/node_modules point into the separate buddy-main-ed7fc846 candidate; out/hermes-agent points to /home/drakosfire/.local/state/dungeonmindbuddy/nonlive-graph-review-ec1da1b/hermes-agent. Preserve links and targets unchanged; current uv.lock resolves Hermes from that local path. Preserve the local node_modules cache directory. The runtime Python interpreter symlink resolves to shared uv-managed Python 3.13.12; site-packages are independent. Refresh tracked source to exact 2f43bbf, removing only tracked files deleted between a044ac4 and 2f43bbf; preserve all untracked local inputs. Do not create another checkout, source export, worktree, environment, candidate or candidate root.

Install the exact unchanged dependency lock for 2f43bbf into the existing a044 runtime using the existing shared uv cache. Normal cache additions and metadata writes are allowed; do not clear or rewrite unrelated cached packages or touch another runtime. Do not print or copy secrets. Keep the project .env read-only and the existing user source, graph, conversation, and ingestion state intact.

The prepared UI bundle and rollback copy remain read-only at /home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-af6779d/ui-dist and rollback-5202-ui-dist. Verify the prepared bundle manifest still corresponds to af6779d before serving it.

Only these existing user services may be stopped/restarted/reconfigured for the matched-main same-port transition:
- dungeonmindbuddy-dogfood-ui-main-cb11bf86.service on 5202
- dungeonmindbuddy-dogfood-api-main-cb11bf86.service on 8000
- dungeonmindbuddy-main-ui-main-892cc46b.service on 5876
- dungeonmindbuddy-main-api-main-01980f14.service on 8002

The 8000 and 8002 APIs share the configured .env and durable data roots. Before a schema change, stop the old 8002 reader/writer and verify it is down; do not leave old application code running against the upgraded schema. Preserve prior unit definitions, executable identities, bundle hashes, runtime inventory, and health evidence for rollback. Keep the publication service on 8001 unchanged.

Do not alter the dirty 996b checkout, the dirty PRIME cited-writer checkout, any other candidate/runtime, service unrelated to the four listed above, project .env, durable source/World/Conversation data, or publication state.

## Gates before rollout

1. Re-anchor to the source and runtime pins above. Confirm the a044 source/runtime paths and their resolved targets; prove no serving process consumes them. Record the exact a044 Git source ref/tree, the single local tracked delta, symlink/untracked input manifest, source pyproject/uv.lock hashes, and runtime package/freeze/direct-URL inventory before mutation. Do not create full duplicate source or runtime archives. Preserve out/hermes-agent as an input.
2. Refresh tracked source to exact 2f43bbf without modifying source/runtime identity paths. Remove only the four tracked deletions between a044ac4 and 2f43bbf; overwrite tracked files from the exact Git archive, preserve all untracked inputs and three symlink targets, and verify every tracked file matches the current-main Git tree. Confirm the sidecar copy and local-input hashes.
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