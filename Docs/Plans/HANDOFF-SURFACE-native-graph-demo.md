# SURFACE: demonstrate the native DungeonMind graph

Status: ACTIVE for isolated implementation; durable runtime/browser qualification is blocked until an authorized, dedicated local PostgreSQL runtime is available. No claim of completion or durable save is allowed while that gate remains open.

## Authority and topology

Alan corrected the product direction: “The toy should operate using DungeonMind, it's a demonstration of DungeonMind.” The coordinating steward assigned design and implementation and explicitly approved this bounded stacked topology on 2026-11-10. The existing canvas is retained as presentation, not semantic authority.

- Stacked parent: draft #2326, exact `b30833ede97cb4c79acf17a1fe55ff50446c7452`; its parent is draft #2313 at `41990c0b2930668e1a1579e24b3a7d6010a38340`. Merge/rebase order is #2313, #2326, this slice. No merge or deployment authority.
- Main re-anchor: GitHub connector verified `77006af9a813cf74dde12e35a29341b1d450087e`; a read-only collaborator successfully fetched the same main. DungeonMind `430c1a6db631d097dfa0a273f8933067f708bc56` and WorldKeeper `ef9c50f2d6aa89a35e9408f83fc4d0ba47825ca2` are Buddy's existing exact dependency pins. No dependency changes.
- Branch: `codex/native-graph-demo-20261110`; checkout `/home/drakosfire/Projects/.codex/native-graph-demo-20261110/worktrees/DungeonMindBuddy`.
- Storage filesystem UUID verified as `48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8`; task parent writable.
- Remote lease preflight inspected open PRs #2326, #2313, #2262 and #2219 and exact changed paths. They keep their old files and previews. All executable files in this slice are new, narrowly named native-demo paths. Existing renderer, repository, root routes, auth, dependencies and registries are read-only.
- Runtime ownership: proposed loopback port 4183, exclusively owned isolated PostgreSQL data/socket directories and verification outputs below this task directory. Verify availability before use. No current preview, user browser storage or application service is replaced. Production configuration, credentials and databases are neither loaded nor used.

## Invariant and design critique

Every displayed semantic object/assertion and successful create/connect comes from real DungeonMind admission, WorldKeeper prepare/commit and exact native revision readback. Browser data is limited to presentation and recoverable form drafts. The server binds one isolated demo KnowledgeSpace; requests cannot select another World or database. Synthetic example content is explicitly demo content.

Use the existing native libraries, domain/profile and public source/revision contracts. Do not call Buddy's ambient production repository factory, ordinary app startup, model providers or Page-creation orchestration. Do not create an alternate semantic store or snapshot the in-memory repository to pretend it is durable. A supported native PostgreSQL adapter owns saved graph state. The command journal may persist input/prepared/recovery metadata, never authoritative graph snapshots.

Create and connect are explicit authored actions. Stable operation IDs bind exact input, parent and preparation across retries. Preparation is reviewed before confirmation. A repeated identical directed relationship is refused at the demo's intent boundary with a truthful existing relationship result, without conflating legitimate independently evidenced native assertions. Lost responses recover via native publication receipts before any replay. Stale parents preserve drafts and require a new review. An uncertain outcome never becomes generic retry-success. Limits bound request/source bytes, nodes, edges and operation growth.

Only supported operations are exposed. Native rename/retract/delete are unavailable in the current WorldKeeper operation union. The UI must say so and must not submit a second name assertion as a fake rename. Existing local browser Worlds are neither migrated nor overwritten.

## Exclusive expected write lease

- `Docs/Plans/HANDOFF-SURFACE-native-graph-demo.md`
- `apps/live_control_server/native_graph_demo/__init__.py`
- `apps/live_control_server/native_graph_demo/service.py`
- `apps/live_control_server/native_graph_demo/server.py`
- `apps/live_control_server/native_graph_demo/storage.py`
- `scripts/native_graph_demo.py`
- `apps/live-control-ui/native-demo.html`
- `apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.tsx`
- `apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemo.tsx`
- `apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemo.css`
- `apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemoApi.ts`
- `apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.test.tsx`
- `apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemoApi.test.ts`
- `apps/live-control-ui/native-demo.vite.config.ts`
- `tests/test_native_graph_demo.py`
- `tests/test_native_graph_demo_storage.py`
- `tests/test_native_graph_demo_http.py`
- `ci/test-classification.json` (coordinator-only additive test inventory update, after collision recheck)

No wildcards. Frontend worker owns only the eight new frontend files. Coordinator owns the backend, launcher, tests, handoff and additive inventory. Shared renderer/canvas and all predecessor files are consumed read-only.

## Security and runtime gate

The dedicated host binds 127.0.0.1 only, enforces its exact Host/Origin and a launch-scoped session capability, rejects cross-site and arbitrary World requests, and serves only its built demo assets. It does not mount existing authenticated application routes or change their auth. Do not accept an ambient or arbitrary production DSN. The launcher may use only an explicitly owned dedicated local PostgreSQL instance, validating its data-directory identity before migrations or writes. No Docker security changes, privileged containers, sudo, remote DB, hosted service, payment or deployment.

Initial read-only Docker inspection returned permission denied at `/var/run/docker.sock`. The host has no PostgreSQL server binaries. This denial must not be bypassed; a durable execution target remains a blocker unless an independently authorized supported target is provided. Real in-memory native integration tests can prove semantics but must not be described as restart persistence evidence.

## Verification and acceptance

Prove native seed/create/connect and exact immutable readback, stable identities, stale-parent conflicts, duplicate prevention, exact retry/replay and lost-response recovery, prepared-input tamper rejection, cross-World rejection, request/source caps and navigation/draft survival. Prove auth/Origin/Host failure paths and no production config import/provider calls. Run real PostgreSQL process restart and readback before claiming durable save; missing PostgreSQL is visibly blocked, never skipped into a passing claim.

Use task-owned outputs and existing frontend verification lock. Run affected tests and strict typecheck/build, then exact-SHA hosted verifier and default-discovered diagnostic at an integrated checkpoint; preserve inherited failures. Run affected backend contract through repo verifier where inventory supports it. Inspect cumulative parent-to-head diff, commit intended changes, independently review exact head, push and open one draft stacked PR. Publication and acceptance must explicitly report any unavailable database/browser evidence. No merge/deploy.

## State and retention

#2326 is a usable browser-local preview, not completion of this native demo. Existing local records remain untouched. Retain the new worktree, source, local proof and outputs for review; no cleanup permission is inferred. Later task completion must inventory retained paths and note cleanup follow-up.
