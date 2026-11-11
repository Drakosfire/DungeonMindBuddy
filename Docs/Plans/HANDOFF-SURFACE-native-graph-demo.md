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

Canvas budget amendment: the same canvas worker also owns `graphProjection.ts` and `graphProjection.test.ts` solely to add an explicit bounded explorer budget (up to 512 nodes and 1024 edges). Preserve default 48/96 behavior for existing callers. Native explorer opts in deliberately and retains displayed/omitted/unexamined counts; initial Fit must not falsely claim an incomplete projection is the entire native catalogue.

Frontend ownership is split for the expanded capability. The existing presentation worker now owns only `NativeGraphDemo.tsx`, `NativeGraphDemo.test.tsx` and `nativeGraphDemo.css`; its earlier one-line bounded AppChrome edit in `App.tsx` is preserved for the mode worker. NativeGraphDemo receives a verified mode/title and injected API, never relabels guest data as a managed World, and maps placement/connection intents into its existing review/recovery state machine. Native semantic writes are already saved when confirmed; navbar status and revision-pinned snapshot export must not imply an unsaved graph or a portable restorable World backup.

### Managed explorer implementation split

The managed backend worker owns new `apps/live_control_server/{models,routes,services}/native_graph_explorer.py`, `src/application_state/native_graph_explorer/{__init__,store}.py`, linear migration `20261110_0149_native_graph_explorer.py`, `tests/test_native_graph_explorer.py`, `tests/test_native_graph_explorer_storage.py`, and only the new router import/registration in `main.py`. It consumes existing native Graph principal, native_registry_source binding/read/descriptors and WorldKeeper registry_standing_consumer owners; no guest allocation/descriptors, old V5 overlay authoring, hosted auth exemption or primary database use. Persist bounded principal/World/binding/operation recovery records in APP-STATE, and let Core own semantic records and exact publication receipts. Native graph reads never allocate or seed a World. Binding/principal/request/review/parent must remain exact across prepare, confirm, status, concurrency and restart; unknown outcomes never trigger a new operation ID or blind dispatch.

Use the narrow transport prefix `/api/live/native-graph-explorer` with POST `graph`, `prepare`, `confirm` and `operations/read`. Every request names `managed_world_id`; prepare additionally binds the exact native World, binding version and expected revision returned by read. Confirm/status resolve a stored operation under the authenticated principal and selected World, then recheck its binding. Return the existing native graph DTO plus verified managed/native World and binding identity; expose only supported write capabilities from actual descriptors. The two workers may refine field names together before implementation, retaining these invariants. Hosted native access stays fail-closed unless the existing owner authorizes it; local-operator managed Worlds are the first runnable target.

The mode/client worker owns `App.tsx`, `App.test.tsx`, `App.guestEntry.test.tsx`, `auth/HostedAuthGate.tsx` and its tests, `selectedWorld/WorldSelector.tsx` and its tests, `chrome/CompactAppNavigation.tsx` and its tests, new `nativeGraphDemo/managedNativeGraphApi.ts` and its test, and only exact new native route allowlist entries in `api/liveApi.ts`. Paths are relative to `apps/live-control-ui/src`. Existing protected-route behavior stays unchanged. Root must check observable authentication status; authenticated/local-operator managed selection drives both canvas API and verified title, signed-out root gets an explicitly separate playground, and loading/error never silently falls back to another graph. World creation/selection reuse the existing navbar selector with an index-preserving destination; no automatic World creation or migration. Keep legacy browser data accessible only as explicitly separate older content, never a mismatched selected-World workspace.

Ownership preflight found those mode files clean in registered worktrees except an unrelated unpublished HTML-error wording edit in `api/liveApi.ts` in the old DungeonOverMind checkout. This lane's allowlist change is strictly additive to exact new route strings, disjoint from that parser change; preserve the other checkout. Coordinator owns this handoff, new test inventory entries, integrated commits and publication. No worker may edit another lane's files without a transfer.

The mode/client worker also owns a narrow additive optional completeness type/validator change in `nativeGraphDemo/nativeGraphDemoApi.ts` and its existing test. The managed envelope schema is `dmb_native_graph_explorer_v1`, containing verified managed/native World IDs, binding version and the existing graph DTO. Managed native completeness and frontend projection truncation are separate facts and must both remain visible; guest/standalone DTOs without the optional field remain compatible.

The mode/client worker may add `api/liveApi.nativeGraphExplorerAuth.test.ts` to prove the actual authenticatedApiFetch boundary for the new exact routes, including lookalike/remote rejection, CSRF and no blind mutation retry. This does not transfer unrelated liveApi behavior or existing test sections. The coordinator classifies the new file additively.

Positioning authority amendment: a committed create response and its recovered operation status may include `created_node_id`, taken only from the verified native publication entity-result binding. The guest foundation worker owns this narrow response addition in `native_graph_demo/service.py` and existing tests; the managed backend owns the equivalent new adapter result. The mode/client worker owns the optional DTO/type/validation addition in the shared native API, and the presentation worker consumes it. Never identify a created object by name/kind or graph difference. Apply client placement only to the exact returned ID in the proper scope/readback; otherwise keep a truthful recoverable limitation. Connect and already-existing responses omit it.


## Explorer descriptor and evidence continuation

The managed graph capability DTO may add optional `allowed_predicates` and
`allows_custom_predicates`. Resolve both from the exact selected native profile.
Standard Buddy V2 permits the registered entity-reference labels `located_in`
and `allied_with`; arbitrary labels are available only when the actual V3 profile
admits the custom entity-reference namespace. The frontend must present the finite
set for V2, never silently invent a predicate namespace or alter immutable profiles.
The mode worker owns only this additive shared DTO validation and its tests; the
presentation worker consumes it in the existing review flow.

The guest CREATE result extension is verified by 30 tests and 10 subtests, with
lint, formatting and compilation checks. It derives `created_node_id` from the
exact verified entity-result binding, including committed replay and recovery;
connect and already-existing responses omit it. These are working-tree checks,
not final expanded-head qualification.

The real Buddy API checkpoint at clean source
`59d4254a909b8165e00d8c95b95b628c22bf6a89` passed two isolated guest allocations,
create/connect and exact readback, replay/duplicate/foreign-World denials, security
boundaries and a fresh-process restart with exact graph signatures and receipt
reads. The external harness hit a reporting-only dict attribute error after those
assertions; its evidence was finalized transparently after read-only database
correspondence checks, without repeating mutations. Retained task evidence is
`task/verification/buddy-index-runtime/runs/59d4254a/api-retry-3/api-proof.json`.
All three APP clones and the dedicated Core proof database remain retained. This
checkpoint does not qualify the expanded managed explorer or browser UX.

Re-anchor after worker recovery found remote main
`18359e0713763e55d986daa8a7966c3371aa09c5`, already present in the shared local
object store. A normal read-only fetch was blocked by the environment policy and
was not retried. The newer main retires obsolete Plan resolver paths, changes two
unrelated liveApi references and updates its own test inventory. Open PR #2349
continues Plan-only capability retirement; it does not own this explorer's paths.
After workers freeze, reconcile the integration lane once onto the verified main,
preserving all unrelated changes. Prior baseline diagnostics remain checkpoint
rather than final-source evidence; compare exact test identities and account for
independently authorized Plan test retirements. No gate or failure is suppressed.

## Integrated explorer completion gates

The navbar flow uses the actual selected managed World and preserves the index
route after creation. Creating a managed World only reserves its native identity;
it does not silently publish a synthetic graph. An uninitialized World remains an
explicit managed-graph error with the existing Build workflow available. Hosted
signed-out native access is not provided by the current local-only backend; the
root states that limitation rather than substituting browser data. Existing
local-operator playground and initialized managed Worlds are the runnable scope.

The presentation checkpoint adds circle nodes, placement and connector intents,
primary Surface navbar actions, revision-pinned read-only snapshot export, and
scope-isolated recovery. TypeScript, 95 focused cases in seven files and the
production build pass on the shared working tree. This is not exact-source final
qualification or browser acceptance. The exact source still needs rebase,
aggregate checks, independent final review and actual runtime/browser proof.

The coordinator's inventory lease is extended additively to four exact test paths:
`apps/live-control-ui/src/api/liveApi.nativeGraphExplorerAuth.test.ts`,
`apps/live-control-ui/src/nativeGraphDemo/managedNativeGraphApi.test.ts`,
`tests/test_native_graph_explorer.py`, and
`tests/test_native_graph_explorer_storage.py`. The first two use `fast`, the latter
two the existing `domain-integration` lane. Preserve all unrelated main inventory
changes; no gate or classification basis is changed.

Independent pre-review identified an owning recovery requirement: existing Core
receipt identity and a matching child hash alone do not prove the stored prepared
intent was published. Before reporting a recovered operation committed, verify
the source receipt and stored preparation, require both immutable publication
aggregate and durable receipt, and use the pinned public WorldKeeper idempotent
verification path with the exact stored publication ID. Never enter this path for
an absent or partial receipt. Compare the verified full results and exact child
before changing APP recovery state or returning a created node ID. Normal commit
already uses the full verifier. The new managed adapter's deterministic native
source/publication IDs must also include the principal and managed-World scope,
matching the APP journal's ownership boundary. No old guest ID is changed.

Final runtime evidence uses a unique synthetic Core database in the existing
verified task-owned no-network PostgreSQL container, a distinct APP test clone,
and task-only artifacts under a scrubbed child environment. Fixture-only provisioning creates a real vNext KnowledgeSpace through the public
Core API and links its exact receipt/immutable Buddy descriptors through the owning
APP world catalog service in the isolated clone. The actual graph routes and local
GM authentication then run without overrides. This does not prove user-facing
World creation or bootstrap: inspection found that the existing first-world Build
initializer writes legacy WorldGraph, not a vNext KnowledgeSpace, and cannot safely
activate this explorer. Do not relabel, migrate or alter an existing World to bridge
that boundary in this slice.
No dependency override may replace the binding, principal, native repository or
operation store in that proof. In-memory unit contracts remain separate evidence.
All proof data is retained; live API/UI, primary databases and old previews remain
untouched. Browser proof waits the exact frozen source and isolated service pair.

Storage-test ownership split: the backend owner explicitly froze
`tests/test_native_graph_explorer_storage.py` after its starter; the dedicated
storage-verification worker now owns only that path. The backend retains store,
service, route, model, migration and service-test ownership. The independent test
lane uses existing unique APP clone fixtures, never native or operator databases.

The mode/API checkpoint reports 64 focused passing tests, one passing root App
case, TypeScript/build and clean diff checks. Its full App suite remains red with
31 passes and the same two retained baseline failures: the `/plan` rendering case
and E7 singular ToolHost/EditHost/Agent route-remount case. The raw App log is
retained externally; other checkpoint results are author-reported working-tree
evidence, not qualifying exact-source logs. No test is disabled. The final
repository verifier remains required.


The managed service checkpoint passes 16 focused native route/service tests,
including exact receipt recovery, corrupted aggregate refusal, principal-scoped
native IDs, and both registered/custom predicate contracts. Scoped lint/format and
diff checks pass. Raw logs are retained externally under
`verification/managed-backend-a4f33323a/`; final exact-SHA tests remain required.
A residual prototype limit is that the 8 MiB response guard runs after catalogue
construction; it is not a per-request memory/work bound. No new pagination or
upstream read contract is introduced here.

Following the verified legacy/vNext initialization distinction, the frozen mode
worker transfers only `selectedWorld/WorldSelector.tsx` and its test to the
presentation worker for accurate setup wording. No navigation, auth or creation
behavior is transferred. The existing Build link manages World content; it must
not promise that legacy first-world initialization creates a compatible vNext
graph. Hosted anonymous access, empty managed-World vNext initialization, and live
cutover remain separate unsatisfied product gates.

The real APP journal storage checkpoint passes 15 isolated PostgreSQL clone tests
with inherited environment, dotenv loading and pytest plugin autoload excluded.
It covers reopen, all five payload hashes, rollback before/after checkpoint,
independent-connection lock ownership/release, scope-local retained operation caps
and actual migrated-DDL constraints. Scoped lint/format/diff checks pass. Retained
logs are `verification/storage-managed-graph-final-20261110T081015Z-973790.log`
and `verification/storage-managed-graph-quality-20261110T081028Z-974219.log`.
There is no named CI contract for these new tests; direct owning-boundary tests
supplement, rather than alter, the repository's existing aggregate contracts.

## Frozen explorer reconciliation

The final scoped UI correction passes 30 focused tests with a retained log at
`task-verification/buddy-index-predicate-recovery-selector-focused-final.log`.
Custom relationship input now uses the server's exact plain-label grammar, with
registered options preserved. Preparation has a distinct in-flight state; a bare
`not_found` cannot release the old operation ID. Fresh review requires verified
stale rejection, and asynchronous results/errors retain their operation scope.
Client name input enforces the same 128 UTF-8-byte bound. Setup copy explicitly
states that new vNext graph initialization is unavailable in this explorer.

A separately authorized read-only live metadata check confirmed Elderwyld is an
existing compatible vNext World, using `dungeonbuddy.world@2` and
`dungeonbuddy.dnd5e@2`. Its APP binding also retains a legacy validated head; the
native inspector correctly selects the current KnowledgeSpace head and exact
binding version, without changing either history. No graph content or live state
was changed. The initialization gap applies to new Worlds, not that existing
native graph.

The coordinator re-anchored main at
`e988a03747a4a195a2f018108c825dc7b2ba5ec6` and inspected current open work before
reconciliation. Preserve unrelated Plan retirement, composition and CI inventory
changes. The prior reviewed frontend source `04f5f0adcb9627605312343b8fc3c7af482ddf95`
has the identical UI tree `a251927d7190d115d13fbed1c72e8b0e95cf3b26` as that main.
Its retained default-discovered baseline has 7,203 passes, 159 failures, one pending
case and the same inherited collection error. Results artifact hash and exact
failed case IDs are retained in task `verification/baseline-e988-ui-*` for final
comparison only, not as explorer qualification. This accounts for the authorized
retired/renamed Plan cases without suppressing any failure.

## Annotated graph feedback continuation

Status: ACTIVE for the bounded UI correction below. Alan reported that the node
placement popup has no clear exit, asked to move the persistent "Explore the
graph" guidance into an information control with hover/focus help, and asked to
remove repeated object/relationship counts below the canvas. He also said,
"Otherwise wire this up, I like this alot." Preserve the existing palette and
native graph direction. This does not authorize merge, deployment, a new hosted
anonymous API, a live database change or bypassing existing authentication.

The preceding implementation is published at
`b0322b7d2e21714f5abefef3cbd5b09affb62b33`. Its exact hosted frontend verifier,
112 directly affected backend cases, 219 auth cases and 14 CI guards passed. The
full discovered diagnostic remains red with 7,307 passes, 159 unchanged inherited
failures, one pending case and the inherited mock-export collection error. Real
isolated PostgreSQL restart/native receipt readback and production-browser guest
and managed read/write proofs passed. The final width-only successor preserves
identical backend objects; a separate final-width connector gesture/cancel proof
also passed. Retained evidence is in task `verification/frontend-b0322b7d/`,
`verification/discovered-b0322b7d/`, `task/verification/backend-b0322b7d2/` and
`verification/browser-qa/artifact-digests-b032.json`. These are predecessor
results, not acceptance of the new UI changes.

Re-anchor: remote main and the fetched shared main are
`999a5eabe00b282d605c72044c9bf8a15e3c8ee3`; subsequent main changes are disjoint
COMPOSITION/writer work. The integration checkout is clean at b032 before this
continuation. PR #2330 remains the same open draft, with that published head and
its old stacked base. The attempted main retarget/title/body update was separately
denied; its unchanged outcome was verified. Do not retry that metadata operation
without relevant new approval or use another transport to bypass the denial.
Keep predecessor refs, preview data and proof artifacts.

### UI write ownership and invariants

The new UI worker exclusively owns these six existing files for this correction:

- `apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.tsx`
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/worldGraphCanvas.css`
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.test.tsx`
- `apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.tsx`
- `apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemo.css`
- `apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.test.tsx`

The coordinator owns this handoff. No backend, auth, dependency, migration,
registry, other route or shared global CSS lease is added. The existing managed
World adapters are already wired to native read/create/connect; a read-only
assessment of remaining initialization gaps does not allocate an implementation
lease or turn the playground into a managed-World initializer.

Make placement cancellation explicit in the palette and after selection but
before native preparation. Escape must exit that unprepared placement state,
with sensible focus and without losing typed input. Cancellation is presentation
only: do not dispatch native writes, erase pending operation identities, discard
uncertain outcomes, or imitate semantic cancellation. A pending native operation
keeps the existing explicit review/recovery behavior.

Move exploration help into a keyboard-focusable information control with an
accessible hover/focus description and retained help content. Remove only neutral
repeated counts from the embedded index; keep navbar counts, empty-state feedback,
projection/omission warnings, action feedback and standalone/other-canvas defaults.
Do not hide limitations or incomplete graph data in the name of visual cleanup.

### Verification and preview ownership

Run affected canvas/native surface tests and typecheck/build under the existing
frontend lock. Freeze and independently review the exact successor, run the
repository hosted verifier and discovered diagnostic with inherited failures
preserved, then verify real-browser Escape/Cancel/re-entry, tooltip hover/focus,
count placement, unchanged native review boundaries and responsive layout.

The task-owned production UI preview is loopback port 5382 against the retained
synthetic API on 8382. Replace only its owned UI process/build after verification,
using the same API and storage. Preserve old build/source, browser drafts, all
native data and proof records. Do not restart or modify live Buddy 8000/5202,
primary databases, other previews, or existing production configuration. Empty
managed-World vNext initialization and hosted authentication expansion still need
their owning design/authorization; do not invent either as a UI shortcut.

### Loaded snapshot inspection continuation

Alan clarified the requested wiring: "I mean that I want what graph is displayed
in the visualizer to track with what graph is loaded. I want to be able to pick a
point on that graph and zoom in and inspect." This is ACTIVE as the same bounded
explorer continuation on the b032 source pin and same PR. Preserve the preceding
feedback changes. No new API, schema, principal or graph publication contract is
introduced.

The canvas already uses the selected managed World's native explorer snapshot.
The independent navbar Graph dialog currently fetches a fresh catalogue, so it
can disagree with the displayed revision. On the index, make this control target
the loaded canvas instead. Retain the independent browser on other routes.
Selected managed objects must use the existing native inspection read route at
the exact managed World, native World, binding version, revision and World-scope
pin that produced the displayed snapshot. Do not fetch a newer catalogue first.
Reject mismatched/stale replies and clear details when selection or loaded graph
changes. Guest details may describe only the actual returned toy node/edges.

Add an inspect/details panel using existing native record presentation. Selection
and camera focus are separate actions: explicit Focus zooms to the selection;
Exit focus restores the prior camera; Fit graph clears focus. Keep native pending
review and recovery prominent and unchanged. Preserve partial/omission feedback,
manual camera changes, drafts and World isolation. This is not a live subscription.

The API/header worker additionally owns:

- `apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemoApi.ts`
- `apps/live-control-ui/src/nativeGraphDemo/managedNativeGraphApi.ts`
- `apps/live-control-ui/src/nativeGraphDemo/managedNativeGraphApi.test.ts`
- `apps/live-control-ui/src/chrome/AppChromeWorldGraphStatus.tsx`
- `apps/live-control-ui/src/chrome/AppChromeWorldGraphStatus.test.tsx`
- `apps/live-control-ui/src/chrome/CompactAppNavigation.tsx`
- `apps/live-control-ui/src/chrome/CompactAppNavigation.test.tsx`

The existing six UI files remain exclusively with the UI worker, serialized after
its annotated-feedback patch. Coordinate the optional inspection method and the
index-only focus target before integration. The separately authorized hosted
owner-access lane owns its own backend/auth transport work; App.tsx, WorldSelector,
liveApi and HostedAuthGate paths are released to that lane, not edited here.

Add regressions for displayed revision versus a concurrently advanced head,
response pin rejection, invalidation/abort, stale selection, keyboard details,
Focus/Exit camera restoration and Fit reset. Run final exact-source verification
and browser evidence as above; record unchanged inherited failures honestly.

Alan's colorful sortable/rearrangeable bubble-chart reference is the longer-term
visual direction, not a claim that this slice finishes it. Use actual graph types
and relationships; proximity must not imply a relationship and no importance
metric is invented. Keep stable positions and camera behavior as the foundation.

The final pre-freeze re-anchor observed main
`af88d3ac71232d02fe9f4cde72ae5cca50f4fe32`. Its delta from the preceding 999a5eab
observation is proposal-history and ingestion work, with no overlapping graph
feedback paths or agent-policy changes. This branch retains its existing e988
merge base; no unrelated main change is reverted or imported during verification.
The separately authorized hosted owner-access lane is a dependent successor, not
part of this UI acceptance claim. It must reconcile the finalized parent SHA and
run its own cumulative exact-source checks.

The implemented inspection boundary registers validated graph objects from read,
existing-object preparation, confirmation and operation recovery against immutable
native inspection pins. A later head advance does not retarget an already loaded
snapshot. Selection inspection remains read-only, and valid unavailable entities
are shown as unavailable rather than replaced by a guest object. The index Graph
button focuses the canvas without opening an independent latest-head dialog or
changing the URL. Non-index Graph browsers retain their existing behavior.

The feedback also covers first measured fit versus subsequent panel resizing,
selection/focus reset on a changed snapshot, explicit Close details and Exit
focus, and keyboard restoration. Tooltip and placement exits are presentation
changes, never semantic graph cancellations. Final exact-SHA and browser evidence
is required before claiming preview acceptance; working-tree focused tests are
only diagnostics.

### Managed client lifecycle review correction

Independent cumulative review of 1ca2a807 identified an inherited integration
blocker: BuddyIndexPage memoizes a managed client, then permanently invalidates
that same client in effect cleanup. Development StrictMode replays cleanup/setup
without recreating the memo, leaving managed reads unusable. Production-preview
success is not evidence against this development lifecycle defect.

The hosted owner-access steward explicitly transferred the App.tsx lifecycle
seam back for this predecessor correction. The lifecycle worker owns only
`apps/live-control-ui/src/App.tsx` for an effect-owned ManagedWorldGraph helper and
its local call replacement, and `apps/live-control-ui/src/App.guestEntry.test.tsx`
for regression tests. Preserve original local World keys and all auth decisions.
The separate hosted lane retains subject/account and entity-only presentation
changes; do not import them here. Do not resurrect invalidated clients or weaken
stale-response rejection. The helper is keyed by managed World, creates a fresh
client for each effect setup, and invalidates only that setup's client on cleanup.

Verify StrictMode setup/cleanup replay, managed World switching, and final unmount
with fresh usable clients and permanent invalidation of retired clients. Re-run
exact-source aggregate checks on the corrected successor and request independent
review of the material correction. Keep predecessor test reports labeled with
their actual SHA; do not relabel 1ca2 evidence as successor qualification.

### Short-screen palette browser correction

Real-browser c836 acceptance passed the primary desktop placement exits, help
hover/focus/toggle/Escape, exact displayed-revision inspection, Focus/Exit camera
restoration and refresh behavior without graph mutation requests. It found one
remaining feedback defect at 390 by 320 CSS pixels: the palette was clamped to the
canvas rather than the visible browser viewport, leaving Cancel below the fold.
The c836 source/evidence remains retained and published; this correction does not
relabel that browser finding as a pass.

The existing UI worker is ACTIVE again only for WorldGraphCanvas.tsx,
worldGraphCanvas.css and WorldGraphCanvas.test.tsx under the prior exact paths.
Keep the palette and its exit inside the visible viewport, including short-screen
or scrolled placement, while preserving the actual requested graph coordinate,
style, keyboard focus and all native intent/review boundaries. A presentation-only
portal or visible-viewport bound is permitted; no dependency, API, auth, graph
layout authority or semantic-write change is included. Keep the old preview
running until the successor is qualified. Add focused positioning/exit regression
coverage, then exact-source aggregate verification and targeted browser recheck.

The correction re-anchored at main
`765e05b50f3648561427fd45e7c10ab2474e25cb`. New ingestion and Play reference
changes since af88d3ac do not overlap the three canvas files or agent policy.
The existing unmerged parent and hosted successor remain separate; no App,
authorization, production service, database or deployment change is included.

## Active mainline migration reconciliation

Before the authorized merge, main advanced to
`1c238dcaa9d549afc3d292c02709fab9b3dc5b57` through #2382. Its captured-source
reader fence owns `20261110_0148` after `20261109_0147`. The published graph
head `763adc1e2f56f3ab587c36937cec33defda41a31` independently used that same
revision for index storage. Git merges these different filenames without a
conflict, but Alembic finds a duplicate revision and multiple heads. Merge is
held until this bounded reconciliation is verified and separately approved.

Topology remains stacked: this repair updates #2330; #2374 at
`f622e8eea2bd5bc766bd6cbedf6a1d577eeaca19` remains its separate dependent
successor. Its branch, auth behavior and retained evidence are not changed here.
The isolated repair lane is `codex/graph-migration-reconcile-20261110` under
`/home/drakosfire/Projects/.codex/graph-migration-reconcile-20261110/`.
It incorporates current main without discarding either lane's source.

This section supersedes the earlier graph-only migration numbers. All open PR
changed-file lists were inspected at allocation: only #2330 introduces migrations,
and no other open PR writes the existing schema-head test module. The repository
uses pinned handoff reservations rather than a central allocator. This lane
reserves `20261110_0150` for index storage after canonical main `20261110_0148`,
then `20261110_0151` for native explorer storage. Do not reuse prototype `0149`
for a different schema. Recheck main and active migration ownership before push.

Exclusive repair write lease:
- This handoff.
- Rename `20261110_0148_index_graph.py` to `20261110_0150_index_graph.py` and
  `20261110_0149_native_graph_explorer.py` to
  `20261110_0151_native_graph_explorer.py` beneath the existing APP migrations.
  Only their revision/down-revision assignments change; table operations remain
  byte-for-byte equivalent.
- `tests/application_state/test_cli_schema_head.py` for source-level unique IDs,
  a connected linear chain, offline SQL order/counts and current-head refusal of
  prototype revisions. The merged reader-fence file remains unchanged.

Retained prototype databases, data, code/runtime pairings and evidence must remain
untouched. In particular, prototype graph `0148` and canonical main `0148` cannot
be distinguished by the revision number. Runtime head refusal of `0148`/`0149`
is not schema-shape detection or upgrade safety proof. Do not upgrade, stamp,
alias or adopt a retained prototype database with this source. Recovery requires
a separately approved, data-preserving plan and an inspected exact database.
No migration, production service change or deployment is authorized here.

Verification uses offline graph/SQL tests with database connections forbidden;
real database and retained-data upgrade acceptance is not claimed. The first
baseline pytest attempt unexpectedly entered the repository's automatic
application-state fixture, created a disposable test database, and failed before
migration bodies. Its finally cleanup returned without error. Preserve that
failed log; it does not establish zero database activity. Subsequent offline
runs disable conftest collection explicitly and never request a database fixture.
The offline baseline reproduces all six new regression failures. Final exact-head
verification, cumulative independent review and renewed source-specific merge
approval remain required. No previous head's evidence is relabeled as this head.

## Interrupted prepare recovery continuation (2026-11-11)

The coordinator continued this assigned graph lane under Alan's request to finish
it. Current repository policy accepts this durable pinned branch handoff. The
owner-access successor remains separate and transfers only the predecessor's
prepare-recovery seam back to this lane; preserve its access/binding checks when
restacking. No merge, deployment, retained-database migration or runtime cutover
is authorized.

Independent review of candidate `91cbec516da32b0c504033ae335913a7a11ff09b`
found that a durable interrupted preparation (`unknown`, no saved preparation)
returned prose suggesting an exact retry, while the UI offered status checks
forever. This continuation repairs that existing native recovery invariant.
The backend supplies `recovery_action: retry_prepare` only for an intact
pre-review `reserved`/`unknown` journal with no saved preparation, preparation
parent, source receipt/admission metadata or committed result. The prepare owner
still validates the identical request hash, scope, binding and deterministic
source receipt. A retry is not a graph confirmation and never creates a new ID.
Unknown publication/confirmation outcomes do not receive this action.

The shared DTO validates the recovery action; the managed adapter retains exact
World/binding/operation identity checks. The UI exposes an explicit same-ID retry
only when both that server action and the retained local prepare phase agree.
Navigation/remount preserves the draft, ID and phase. A recovered review still
requires explicit confirmation. No automatic retry or fresh-operation escape is
added.

The bounded write set adds only the existing native explorer service/test,
NativeGraphDemo component/test, shared API/test, managed API test and this handoff.
There is no schema, dependency, storage, authentication or profile change.
Working-tree evidence before current-main composition: 144 focused frontend
cases and TypeScript/production build pass; 25 native HTTP/service cases pass
against the real in-memory Core/WorldKeeper fixture. That Python environment's
GenerationEngine pin differs from the current lock, so this is explicitly
non-qualifying diagnostic evidence. Twelve offline migration checks pass with
conftest disabled and two database cases deselected.

Current-main re-anchor is `11505add65802454390dbb48e73ea109925eb655`, independently
read through the connector. Its intervening BUILD changes merge without graph
conflicts. Exact final-source aggregate checks and independent review remain
required. The normal frontend verifier's fresh npm installation was network-policy
blocked before tests; retain that failed attempt and do not call manual cached
runs repository-verifier qualification. All new artifacts remain under
`/home/drakosfire/Projects/.codex/graph-finish-20261111/` on the verified Projects
filesystem. Prototype databases and earlier source/evidence remain untouched.
