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
- `apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemoEntry.tsx`
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

## Discovered capability and inventory boundaries

The existing accepted Buddy vNext V2/V3 profiles classify only `dnd5e:npc`, `dnd5e:location`, `dungeonbuddy:faction` and `dungeonbuddy:organization`. The legacy recap vocabulary's `dnd5e:event` is a separate contract and is not accepted by the WorldKeeper vNext resolver. `observed_event` is an assertion claim mode, not an Event classification. Therefore this implementation proves genuine native People (NPCs) and Location creation/connect, keeps Event visibly unavailable, and does not claim the originally requested four-node example complete. A native Event profile extension needs an owning semantic slice; do not mutate immutable profile declarations or relabel an untyped entity as Event.

The new graph response includes explicit supported object kinds and limitations. Native rename/retract/delete remain unavailable. The incomplete seed has two People and one Location, not a falsely represented Event. This is a partial native implementation, not a replacement completion criterion.

Inventory preflight inspected current pinned CI handoffs from #2298/#2299/#2302/#2288 and relevant local CI worktrees. Their classification leases are narrowed to their own individual CI guard entries; the inspected inventory files are clean. Under coordinator direction, this slice's classification lease is split to its five new test filenames only: two frontend entries and three Python entries. No existing entry, CI guard, classification basis, discovery configuration or gate is changed. Preserve this additive-only delta when reconciling the stack.

## Local run contract

Build only `apps/live-control-ui/native-demo.html` through `native-demo.vite.config.ts`. The result is an asset bundle for the dedicated Python host, not a static replacement for port 4182. A plain Vite preview has no native API/session capability and is not a working DungeonMind demo.

The launcher is `scripts/native_graph_demo.py`. Required arguments are `--state-dir` (a new private task-owned directory), `--dungeonmind-source` (clean exact Core pin including migrations), and `--assets` (the isolated build directory). Optional `--postgres-bin` names an already authorized installed PostgreSQL binary directory; no software is downloaded or installed by this script. `--check` is read-only. Default HTTP port is 4183. The launcher initializes a dedicated cluster with Unix-socket peer authentication, disables TCP listening, checks the actual data-directory identity and required pgvector extension, applies existing pinned Core migrations, and stops its own PostgreSQL process on normal exit. Semantic data survives in that owned data directory; this guarantee still requires actual restart verification before acceptance.

Do not pass the ordinary Buddy database URL, use the old `.env`, alter Docker permissions, or supply an operator/live cluster. No arbitrary DSN parameter exists. The session capability rotates every HTTP launch and appears only in the same-origin served HTML, never a URL or saved browser credential. Browser state stores only layout and recoverable input/operation IDs. PostgreSQL and the native receipt remain graph authority.

Inventory qualification found one inherited omission from #2313/#2326: `apps/live-control-ui/src/App.guestEntry.test.tsx` was absent from all classification lanes. The coordinator authorized the additive predecessor repair separately. This existing Vitest file is now classified in `fast`, alongside the new demo UI tests. Its contents and all gates remain unchanged. Total inventory delta is six added lines; zero removed or reclassified entries.

## Verification checkpoint (working tree only)

A scoped independent transport/launcher review found and then cleared three issues: migration pin checks now verify the exact on-disk inventory and Git-object bytes (including ignored files), Git repository overrides are excluded from verification calls, and SIGTERM/uncertain startup outcomes are handled before the owned PostgreSQL process is started. Its rerun passed 18 HTTP/launcher tests, including a real HTTP-to-WorldKeeper-to-DungeonMind in-memory create/readback/replay case. A later transport regression also permits a top-level link into the HTML entry while continuing to deny cross-site API/iframe access. These are working-tree diagnostics, not final exact-SHA qualification or PostgreSQL evidence.

The isolated launcher `--check` currently exits 2 with the explicit PostgreSQL-server-tools blocker, before allocating runtime state. No PostgreSQL database, ordinary Buddy service, existing preview or browser profile was touched.

Backend owning tests are intentionally run as the three explicit `unittest` modules with `PYTHONPATH=.:src`, a task-owned `TMPDIR` and the already-installed exact-pin Python environment. They do not load the root pytest dotenv fixture. Existing named CI contracts remain unchanged: their historical-exactness guard does not permit adding a new contract without a separate CI guard/fixture change, which this slice does not take over. Full backend/PG qualification remains unrun.

Frontend entry allowlist amendment: `nativeGraphDemoEntry.tsx` replaces the untracked planned `nativeGraphDemo.tsx` entry. This avoids TypeScript case-only collision with `NativeGraphDemo.tsx`; no shared config or other path is transferred.

## Integrated source checkpoint

The implementation checkpoint passes 39 isolated backend/HTTP/launcher tests, 14 focused UI tests, strict TypeScript, the separate native-demo build, Python lint and the complete test inventory. HTTP/service cleanup now closes the SQLite journal explicitly. These are pre-commit diagnostics, not final exact-SHA or durable PostgreSQL evidence.

Before commit, GitHub re-anchor found main `76bb8c4b38178158e9a94a4b00cf65773edbda87` (Plan request-admission presentation #2328, disjoint paths). Stacked parent #2326 remains open/draft at exact `b30833ede97cb4c79acf17a1fe55ff50446c7452`. This slice remains pinned to that parent; no unrelated merge or rebase is inferred.

The native runtime has no Event support in this pinned Buddy profile, not a claim that DungeonMind's general ontology excludes Event. Parent ontology discussion remains open. This slice does not decide that ontology or extend the accepted profile.

## Retained integrated qualification and publication gate

At clean integrated head `0c8a511d46d2c7ec1f28a5b7eaacf36c85a7a2bf`, the unchanged repository hosted verifier completed with npm offline mode using the existing local cache: 1,262 + 4 + 1 cases passed, exact collection parity, strict TypeScript/build, clean isolated source and successful cleanup. Receipt validation passed. Evidence: task `verification/hosted-0c8a511d4-offline/evidence.json`.

The full default-discovered diagnostic at the same head remains RED: 7,317 passing cases, 164 failed cases, one skipped case, and the inherited `SELECTED_WORLD_LOCATION_CHANGED_EVENT` mock-export collection failure. All 164 failed test IDs exactly match the retained predecessor integrated baseline `d4f47f301b30a8207c2af5107fcb3730b2afa07d`; no new or missing failures. Evidence: task `verification/discovered-0c8a511d4-offline/evidence.json` and `verification/failure-comparison-0c8a511d4.json`. This is an integrated checkpoint, not final-head discovered or release qualification.

Initial normal npm installation was denied by network policy at registry.npmjs.org before testing. No network retry was made; offline cache installation is a distinct no-network verification path. The interrupted initial verifier worktree under task `scratch/dmb-local-frontend-nktazttj/source` is retained, not represented as cleaned or passing.

Branch push was denied by network policy at github.com:443, known not executed. No alternative write route was attempted; no new PR exists yet. Publication requires an authorized transport, not bypassing this denial. No merge/deploy authority is granted.

The launcher additionally refuses ambient `PG*` process variables before importing or connecting through psycopg. Cleaning child-process environments alone is insufficient because libpq can also consult the current process environment. This refusal changes no user security setting and avoids exposing or using those values.

## Authorized isolated-container runner amendment

Status: ACTIVE bounded continuation of this same slice. Alan explicitly granted both durable isolated storage/restart verification and publication after the recorded denials. The authorized escalated branch push succeeded at reviewed head `00779be1b887108476a7d009bf39190d23eb3684`. The corresponding Docker read-only retry also succeeded and found a local `pgvector/pgvector:0.8.6-pg16` image. Host PostgreSQL tools remain absent. Draft PR creation separately requires explicit approval after its action-review rejection; no alternate publication route is authorized by this amendment.

The coordinating steward approved a narrow runner adaptation using one isolated dedicated container, without changes to host network/security settings, existing containers, production credentials or production data. This supersedes only the earlier host-binary-only runner restriction. Keep the existing native binary path; add an explicit container option, never automatic fallback. Do not download an image, install host packages, mount a Docker socket into a container, use privileged/host-network mode or expose database TCP ports. Pin and verify the already-local image's immutable identity before using it.

Topology and source ownership remain the same stacked branch, parent and eighteen-path allowlist. The runtime worker receives only `scripts/native_graph_demo.py` and `tests/test_native_graph_demo_http.py` for this continuation. The coordinator owns this handoff. All other executable paths stay read-only unless another explicit transfer is recorded. Runtime/proof scratch stays under `/home/drakosfire/Projects/.codex/native-graph-demo-20261110` on the verified filesystem; use a new private owned runtime directory and retain all database data.

The new container must have no network. Its complete permitted bind-mount set is two separate task-owned writable directories (PGDATA and Unix socket), plus two generated private read-only identity files at `/etc/passwd` and `/etc/group` for the bounded host-UID/name mapping below. These must be generated task files, never host `/etc` files. Do not mount the whole state directory: ownership markers, launcher locks, SQLite command journals, source and credentials must stay inaccessible to the database container. Put container PostgreSQL logs within PGDATA. Preserve exact Unix-socket peer authentication and current-process `PG*` refusal. A bounded host-UID/name mapping is permitted for the new container only, so its server can authenticate the same local user without a trust-auth shortcut or saved credential. Existing production identifiers, environment and configuration must remain inaccessible. Retain pinned migration verification, dedicated database identity checks, HTTP loopback/capability guards and all semantic/recovery invariants.

Critique before implementation: distinguish absent, stopped, running and uncertain owned-container states; refuse adoption of pre-existing or unproven runtime ownership. Bind startup and cleanup to the exact container identity created by this launcher. Handle interrupted creation/start and failed subprocess outcomes without stopping or deleting another runtime. Normal stop must preserve the data directory and must never use volume deletion or blanket pruning. Prove a clean restart reopens the same native KnowledgeSpace, graph revision/digest, object IDs, command journal and native publication receipts. Repeated confirmed commands must not create new semantic objects/assertions. Inspect lifecycle, mount and network identity as well as native readback; an in-memory or mocked test is insufficient for the live gate.

Re-anchor for this amendment: main `76bb8c4b38178158e9a94a4b00cf65773edbda87`; parent #2326 remains open/draft at `b30833ede97cb4c79acf17a1fe55ff50446c7452`. No other source or runtime lease is taken over. No merge, deployment, model/provider invocation, ontology extension or production access is granted.

The isolation review also requires a private host ownership record of the full container ID. Reuse requires that ID plus the exact configuration and immutable image, not only a matching name or labels. Ambiguous create/start outcomes are inspected and reported; without sufficient ownership proof, no adoption or cleanup is allowed.
