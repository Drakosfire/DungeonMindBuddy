# SURFACE: demonstrate the native DungeonMind graph

Status: ACTIVE for the Buddy index integration below. The standalone runner is retained verification scaffolding, not the product path. Earlier topology/runtime sections are historical where superseded by the index integration amendment. No live cutover, migration, merge or deployment is authorized.

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

The approved already-local runtime image is `sha256:9b05db12a35460fff0587e009f9326e414a53e9484555547f96d214a2ba98ef7`, with repository digest `pgvector/pgvector@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b`. Bind only the owned host PGDATA directory to the image's declared `/var/lib/postgresql/data` target, preventing an anonymous volume. Inspect must prove that exact host-source/container-target mapping, while SQL must report the fixed container data path. The socket bind keeps the same resolved host/container path. Override the image entrypoint and command with an inert process; the image's standard automatic PostgreSQL initialization must never run. Only the bounded exact-ID runner may invoke the pinned PostgreSQL tools after ownership and isolation checks.

Publication gate resolved after Alan explicitly approved opening the draft PR: #2330 (`https://github.com/Drakosfire/DungeonMindBuddy/pull/2330`) is open/draft, targets the unchanged #2326 branch, and initially publishes reviewed head `00779be1b887108476a7d009bf39190d23eb3684`. Continue this same PR for the authorized runtime adaptation. No merge or deployment is authorized.

## First-use lifecycle clarification

Re-anchor before this correction found main `185e07be2557825a8fd7b14477cbe2d819972ad1` (disjoint COMPOSITION #2329), while parent #2326 remains unchanged at `b30833ede97cb4c79acf17a1fe55ff50446c7452`. Keep this stacked lane and its dependency pins; no rebase or dependency update is part of this correction.

Real Docker inspection proved the dedicated runtime's exact four mounts, no-network configuration and pinned image. Docker 29 omits the false `ReadOnly` field on writable mounts and leaves the derived `Mode` empty; validate authoritative `RW`/`ReadOnly` fields with false as the omitted default, retain exact source/target/count checks, and explicitly reject automatic port publishing. Do not relax the readonly identity mounts.

For a first-use cluster, PostgreSQL 16 reports `pg_ctl status` exit 4 rather than the initialized-but-stopped exit 3. The only permitted first-use exception is the exact owned inert container with a verified private, completely empty PGDATA directory. Preserve the actual status code and prove this condition separately. Initialized or nonempty data with exit 4, any already-running PostgreSQL, and uncertain outcomes remain fail-closed. After initialization, exit 3 is still required before starting PostgreSQL. Never remove partially initialized data or recreate a container to make a check pass.

## Buddy index integration amendment (current authority)

Alan clarified that this is part of Buddy and must use the running DungeonMind instance, then directed: “Place it at the index page, and clean up the index page. Not perfect or anything, we are learning about this idea. The surface we've been building is for the graph presentation, it may also become the landing page if it works and is fun.” The coordinating steward approved a local-first implementation with scoped guest spaces, normal APP-STATE migration in the branch, existing managed-world authentication unchanged, and synthetic isolated verification. No new anonymous hosted API, public deployment, live schema change or runtime cutover is authorized here.

### Re-anchor, lane and supersession

Current main is `7517a42083d7244f8adf6ff3166027b7cfedbdd0`; its APP-STATE migration chain ends at `20261109_0147`. The older stack ended at 0144, so appending a migration there would fork the chain. The steward explicitly approved reconciling the combined graph/index changes onto current main in an isolated integration lane, then retargeting the same draft #2330 after cumulative review and verification. Leave predecessor drafts #2313/#2326 and all their data/refs untouched until separately settled.

- New implementation checkout: `/home/drakosfire/Projects/.codex/native-graph-demo-20261110/worktrees/BuddyIndexIntegration`, branch `codex/buddy-index-native-20261110`. The fourteen feature commits were replayed cleanly onto the verified main; no conflict resolution or unrelated source edits were needed.
- Original checkout/branch at `8c0d8ce15c6e5acda0b656adff4aff5f9898bde0` is retained. Its standalone 4183 process/container/data remain untouched and are not the Buddy product runtime.
- Read-only live inventory identifies Buddy API `127.0.0.1:8000`, UI `127.0.0.1:5202`, installed release `76bb8c4b38178158e9a94a4b00cf65773edbda87`, mode `local` / `local_operator`. Buddy already embeds DungeonMind through its configured native repository; there is no separate DungeonMind HTTP app to invent. Existing primary APP-STATE and World data remain untouched.
- Ownership preflight inspected current open SURFACE drafts, disjoint CONVERSATION/COMPOSITION work and existing registered worktrees. No unpublished edits were found in App.tsx, App.guestEntry.test.tsx, main.py, hosted_auth.py or APP-STATE authority.py. The steward transfers the narrow successor App/index test edits into this integration lane only. Do not edit predecessor checkouts or their handoffs. Existing hosted auth policy remains read-only.

### Bounded product contract and critique

One capability: make Buddy's existing index show the exploratory native graph surface. Reuse WorldGraphCanvas and NativeGraphDemo's reviewed preparation, confirmation and recovery behavior; modestly clean up the index rather than building another product page. Keep client layout/preferences and recoverable drafts where compatible. Existing IndexedDB Worlds/notes are not migrated, overwritten or deleted. Keep any legacy access honest and secondary, not a second claimed native graph authority.

The backend router is `/api/live/index-graph` within Buddy's normal FastAPI app. It uses the existing configured DungeonMind repository and APP-STATE DSN; no arbitrary client DSN, World/space selector, environment fallback or database lifecycle tool. Local/development `local_operator` mode only. The existing global hosted boundary stays intact and no hosted route exemption is added. Production/hosted mode must fail closed before allocation. Existing managed-world routes, principals and permissions are unchanged.

Use a bounded server-owned browser session with a private opaque cookie, exact configured local UI Origin/API Host, unproxied loopback checks and CSRF for mutation. It grants access only to its own synthetic graph, never an operator/managed-world capability. Persist a hash of the cookie credential and its server-owned session identity in APP-STATE, not the raw credential. Separate native allocation IDs and operation namespaces per session; client-supplied graph/space/session selectors cannot establish authority. Preserve session/graph state across ordinary process restart. Cookie loss/expiration must be explained truthfully, with no implicit account sync or promise to recover an unknown browser identity. Bound session issuance and per-graph operations; no automatic deletion/pruning of existing graphs.

API contract for the frontend/backend workers: POST `/session` bootstraps or resumes the cookie-bound session and returns `csrf_token`; GET `/graph`, GET `/operations/{operation_id}`, POST `/prepare` and POST `/confirm` use the existing native DTOs. Unsafe requests require the session CSRF header `X-DMB-Index-Graph-CSRF` and trusted Origin. GETs never accept cross-site access. Cookie name must be profile-namespaced because ports do not scope cookies; path `/api/live/index-graph`, HttpOnly and SameSite Strict. No capability is added to URLs or application logs. The API client is injected into NativeGraphDemo and does not require the standalone HTML capability meta tag.

APP-STATE owns session/binding/command-recovery metadata in a small domain-specific store and normal linear migration `20261110_0148` after `20261109_0147`. DungeonMind remains semantic graph authority. No SQLite product store or new PostgreSQL instance. Reuse the service through an injected store and server-controlled allocation identity, while preserving the standalone default solely for tests. Cross-process serialization must survive journal checkpoints: use a session-scoped database advisory lock on the same connection, not a transaction-only lock that disappears before native dispatch. Native mutations remain separately receipt-verified; unknown-before-dispatch, request/preparation binding, stale parents and duplicate/replay protections must not regress.

Failure cases before dispatch: missing/expired/forged cookie, two guests, operation-ID reuse across guests, forged World selectors, cross-origin/proxy requests, oversized input/session exhaustion, concurrent bootstrap, concurrent prepare/confirm, APP-STATE or native readback outage, process restart between checkpoint and native dispatch, and stale prepared revisions. Reject safely, retain recoverable drafts/data and never infer that an unavailable authority means an operation did not commit. Profile Event and native rename/delete limitations remain explicit; no ontology expansion is authorized.

### Expanded exclusive write lease and worker split

The original eighteen-file lease stays only in this new integration checkout, with the standalone launcher/host frozen. The following additions/narrow successor transfers are authorized:

Frontend worker:
- `apps/live-control-ui/src/App.tsx`
- `apps/live-control-ui/src/App.guestEntry.test.tsx`
- `apps/live-control-ui/src/App.test.tsx` (only affected index expectations/mocks)
- `apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.tsx`
- `apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemo.css`
- `apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.test.tsx`
- `apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemoApi.ts` (shared response validation/transport seam only)
- `apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemoApi.test.ts`
- `apps/live-control-ui/src/nativeGraphDemo/buddyIndexGraphApi.ts`
- `apps/live-control-ui/src/nativeGraphDemo/buddyIndexGraphApi.test.ts`

Backend worker:
- `apps/live_control_server/main.py` (router registration only)
- `apps/live_control_server/routes/index_graph.py`
- `apps/live_control_server/services/index_graph.py`
- `apps/live_control_server/native_graph_demo/service.py` (store/allocation injection only, no semantic redesign)
- `src/application_state/index_graph/__init__.py`
- `src/application_state/index_graph/store.py`
- `src/application_state/index_graph/sessions.py`
- `src/application_state/migrations/versions/20261110_0148_index_graph.py`
- `tests/test_native_graph_demo.py` (injection/isolation regressions only)
- `tests/test_index_graph.py`
- `tests/test_index_graph_storage.py`

Coordinator only: this handoff and additive test inventory. Any change beyond these files or the narrow stated reasons returns to the steward first. No hosted_auth.py, config/dependency, infrastructure or live-release edits are granted.

### Verification and runtime boundary

Prove two independent guest sessions against synthetic native repositories and disposable APP-STATE fixtures, create/connect/readback and exact replay, cross-guest denial, session resume and fresh-process journal recovery, interrupted confirmation and draft preservation. Test the index itself, not only the standalone entry, including normal App navigation/Back and protected-route authentication. CSS must be scoped so importing the graph does not restyle every Buddy page. Keep source tests, typecheck/build, full discovered comparison and exact-head hosted evidence under the existing shared frontend lock, with independent cumulative review.

The normal migration is code only until runtime cutover is separately assessed and authorized. Do not apply it to primary APP-STATE, restart or replace the running Buddy release, point tests at primary data, or promote a fixture as the running instance. Report the real cutover steps and any required authorization once the integrated branch is verified. No merge/deployment follows from this implementation lease.

Inventory amendment after current-main reconciliation: main #2328 added `tests/test_native_plan_opening.py` without classification. All inspected registered inventory worktrees are clean; add that filename to `domain-integration`, matching its neighboring native Plan tests, alongside this slice's new test filenames. This repairs an inherited omission only; no test body, lane reclassification, selector or CI gate changes. The coordinator owns this additive inventory delta.

Verification environment for the reconciled branch: use the existing read-only `/home/drakosfire/Projects/.codex/ge-native-structured-runtime/bin/python`, whose installed exact Core/WK/GenerationEngine pins match the reconciled source. The older recorded-names environment has the previous GenerationEngine pin and remains retained rather than modified. New checkout and parent dotenv search paths were checked absent; tests must still scrub inherited provider/runtime settings and use only the repository's uniquely owned disposable APP-STATE template/clones on the test server. The running 54331 APP-STATE authority is already at 0147 and is never a test target.

### Index integration diagnostic checkpoint

The index client and guest composition pass 28 focused transport/UI/guest tests plus the two affected App index/navigation tests. Typecheck and the normal Buddy build pass. The broader App suite still reports the same two failures recorded by the exact current-main discovered baseline: `App inspector integration > renders plan surface from /plan` and `App inspector integration > E7: route remount keeps singular ToolHost, EditHost, and Agent chrome`. This is working-tree evidence, not exact-head qualification.

Backend diagnostics pass 32 tests and 10 subtests using disposable APP-STATE clones and a genuine in-memory DungeonMind repository. They cover independent guest allocations, operation-ID namespace isolation, concurrent bootstrap/prepare/confirm, request boundary rejection, session limits, no replacement for unknown cookies, journal restart/replay and the PostgreSQL session lock across checkpoints. Native PostgreSQL and whole-process restart proof are still separate requirements.

The shared disposable APP-STATE server on 54329 lacks the `vector` extension required by the exact Core migration chain. Do not use either primary database or modify that shared server to work around this. Assess the already-retained task-owned pgvector substrate read-only for a separately named synthetic Core database; any proof there remains test scaffolding, not a new product runtime or Buddy cutover. Preserve its existing database, processes and data.

The pre-commit remote re-anchor found main `f99642591340d9b7af4f411600bf6381d1c76a73`. Its changes since the integration base `7517a42083d7244f8adf6ff3166027b7cfedbdd0` are disjoint conversation/connected-page/composition work, with no change to this lane's paths or migration head. Relevant SURFACE and CI drafts remain open. Keep the pinned integration base for exact-source comparison rather than silently importing unrelated work during verification; the assigned PR will target main and disclose this base. No predecessor draft is closed or overwritten.

### Graph-first index layout refinement

Alan's next feedback preserves the palette and asks to use the existing Surface NavBar rather than a long column. The screenshot was the retained legacy index, but apply the direction to this native index. The frozen backend/native integration checkpoint is `813e7285f6dc1e7d88abfc48ac825bb450ad197f`; its isolated PostgreSQL proof can proceed independently of this presentation-only follow-up.

The frontend worker resumes its existing allowlist, limited to `App.tsx`, index composition tests, `NativeGraphDemo.tsx`, its tests and scoped CSS. Reuse `useSurfaceContextContribution` and `SurfaceContextModule` in the existing AppChrome SurfaceContextHost for compact graph identity/status and Add, Connect, Refresh and Info controls. Prefer the existing context contribution seam, not a new navigation component or a pageActions-only bridge. Use AppChrome's existing bounded workspace option and make the graph fill the available width and height. Show one requested form panel at a time; pending review/recovery stays prominent and uses the existing handlers. Move repeated hero/help/limitations/diagnostics out of the primary canvas viewport without hiding unavailable capabilities or the session recovery caveat.

Preserve the gold/charcoal palette, standalone proof behavior, client layout/drafts, browser-only legacy access and guest/protected-route boundaries. No shared Navbar, global stylesheet, auth, backend or managed-World selection edits are added to the lease. Do not change or restart the actual Buddy runtime or any existing World while the separate live World-selection investigation proceeds. Verify desktop/mobile layout, navigation and interrupted/repeated authoring before the final exact-head frontend runs.

### Expanded explorer authority

Alan subsequently requested an exploratory read/write graph explorer and explicitly said to execute it while he is away. This supersedes the minimal guest-only product target: the signed-out experience is a clearly identified playground; an authenticated or local-operator managed World selection must populate the actual native World graph, with no silent fallback to another World. Preserve the palette. Use circles, a canvas tool palette, position-aware node creation and connector-dot dragging, with native validation/review/recovery still owning writes. Put graph controls, Save/export, World selection and creation entry in the existing surface navbar. Fit the whole graph initially, preserve user pan/zoom afterward, and retain an accessible Fit action.

Proceed on this integration lane and assigned draft PR; the user has authorized the expanded capability, so ordinary topology choices do not require another approval. Live schema/runtime changes, deployment, auth weakening, new public anonymous authority and use of existing Worlds as test data are not authorized. The current local-only guest API cannot be represented as a hosted signed-out implementation. Existing hosted and native principal/membership boundaries remain mandatory; any unavailable hosted mode must be described honestly.

The shared canvas presentation lease is now transferred into this integration lane for `apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.tsx`, `worldGraphCanvas.css` and `WorldGraphCanvas.test.tsx`. No other worker edits these files. A dedicated canvas worker adds optional native interaction-intent props and circle geometry while preserving current card/local-edit defaults. Canvas gestures emit draft intent only; NativeGraphDemo/its successor owns preparation, confirmation and recovery. Existing semantic records are never rewritten by geometry or placement controls.

The backend foundation worker may additionally correct `_map_native_error` in `native_graph_demo/service.py` and its tests so native persistence-integrity failures are authority failures, not permanent user-operation rejections. This narrow review correction is independent of the managed-World adapter design. The steward will record the concrete managed backend/mode composition paths after inspecting the existing native registry and standing-consumer owners, before assigning those edits.
