---
pr_body_template: |
  ## Handoff pointer
  - Workstream: DEMO / J4
  - Direction: STEWARD → CODE → PRIME
  - Handoff: Docs/Plans/HANDOFF-DEMO-world-scoped-statblock-drafts-v1.md
  - PR topology: serial; one assigned implementation PR only

  ## Review contract
  A GM can create, generate and reopen a ThreatDraft owned by the selected
  managed World, without inventing a campaign or crossing World ownership.
  World-only drafts do not enter campaign-only graph publication. A Buddy-local
  journal-proven terminal outcome settles only its exact attempt; uncertain
  failures remain unresolved, and a deliberate new attempt preserves history.
---

# HANDOFF — DEMO: World-scoped statblock drafts

**Created:** 2026-09-27
**Status:** COMPLETE / HISTORICAL — #785 merged after three distinct review-head cycles; no active implementation lease
**Handoff locator:** this checked-in path, pinned by the steward before activation
**Conversation/workstream:** LOCAL DEMO ACCEPTED / DEMO-J4
**Flow / owner:** DEMO / Buddy asset authoring and selected-context interaction
**Direction:** STEWARD → CODE → PRIME
**Design authority base:** Buddy `main@faad16e319c1543f0a7743f66d0378785dda5201`
**Activation gate:** satisfied — PRIME independently ACCEPTED §6 at `de08711183e94065b12b3a4d24765b333a760a1e`; fresh open-PR/lease/runtime re-anchor completed 2026-09-27.
**Base revision:** `de08711183e94065b12b3a4d24765b333a760a1e`
**Dispatch base rule:** current remote main after acceptance and guarded activation; record exact branch base before code
**Implementation dispatch base:** `d3e0797d64572ef981b9d0f5d03c67ae5261e348`
**PR topology:** serial within DEMO
**PR authorization:** after ACTIVE, open/update exactly one assigned implementation PR without another operator prompt; no successor PR
**PR title:** `DEMO: scope statblock drafts to the selected World`

**Completion / historical state sync (2026-09-28):** this handoff's assigned
implementation PR #785 completed and merged to Buddy `main` as
`f8b923875f9444a1addfb2472a2b8fab35eceb4c`. The exact reviewed code head was
`471a967d11e315b24fd5cfe5541f447753fb81f4`; there were three distinct review-
head cycles and four formal review submissions (`5333492877`, `5333610809`,
`5341223774`, `5341878346`). This records J4 completion only; it does not claim
the connected LOCAL DEMO, J1–J6, or the remaining asset/publication/retrieval
successors are accepted.

## §1 Mission and merge-ready invariant

The GM can create, generate and reopen a ThreatDraft owned by the selected
managed World. This is actual generation, not a disable-only safety patch.

**Invariant:** every durable draft and generated candidate retains its immutable
launch World/scope and exact draft lineage; current UI actions and restored
working copies operate only on a server-verified draft in the current selected
scope. Navigation, delayed callbacks and failures cannot launch a second
generation, rebind an asset, or expose another World's working copy. Existing
campaign drafts retain their accepted semantics and serialized representation.

The slice owns one independently useful asset-draft lifecycle. It does not
publish a World object, bind an asset into Plan, generate images, or close J4.
Do not substitute a fake campaign for the missing world-only draft contract.

Pre-dispatch critique:

- Worst sequence: resolve A's head → switch to B → late A create response →
  automatically generate under B → overwrite B's global convenience join.
  Owning component tests must defer each await separately and inspect requests,
  durable identity, cache writes and later restoration.
- A second danger is reopening a foreign exact candidate ID and assuming its
  name proves ownership. Load/admit its server-owned source draft first.
- The under-tested boundary is store round-trip: a V2 world-only draft must
  remain V2 after candidate journaling, editing, acceptance and reload. Calling
  a V1 validator during an update is not allowed to erase or reinterpret scope.
- New graph publication policy, campaign creation or provider/job machinery
  forces stop/rebrief; none belongs inside draft ownership.

## §2 Context, authority, lane and sequencing

- Parent authority: sole `Docs/Roadmaps/ROADMAP-demo.md`, adopted
  `Docs/Plans/STEWARDS-HANDOFF-demo.md`, authored Threat/statblock domain design,
  and `Docs/Design/CONTRACT-world-container-v1.md`.
- #784 is integrated at `b6c63a56f784be5cc2fc7de5bb6d167e32520bb8`, with
  completion/state sync at `c19a6c2bf51ae01337b2ad8a3188d45ad6f0fd64`.
  No predecessor sync is owed inside this implementation PR.
- Current observed defect: Plan Tools → Statblock in Of Conks shows and uses
  `eldyrwild / longmont-c2`. `resolveCreateScope()` hardcodes these for head
  reads, override and freestanding fallback. No create/generate was submitted.
- Existing ThreatDraft V1 requires a nonblank campaign. Build's World-ID-as-
  campaign compatibility rule covers sources, not asset publication. It cannot
  be extended by inference. This handoff proposes the explicit V2 decision.
- Existing `map_draft_to_generate_request()` sends description, intent,
  encounter context, actor and request ID to SERVER, not World/graph pointers.
  Consume that unchanged contract. A revision pin is recorded provenance, not
  proof that generation is graph-grounded.
- PRIME's first activation-design judgment on `84e8d87c2aa48c0d1732732a34ddaf7c3fa83d0d`
  was HOLD for two bounded repairs: explicitly lease the revision/history
  consumers and specify browser-persisted same-attempt generation identity.
  Those repairs are included below; this is not a PR review cycle or activation.
- Named successors: governed World-only Threat publication/lookup; Agent brief
  transfer; image generation/selection and Plan placement. J3 remains a separate
  source/read/write authority transition, not a prerequisite for inert drafts.
- Open DEMO implementation PRs at activation: none. #780 evidence preservation,
  #781 interaction-map proof and Rules #763–#765 own their existing disjoint
  paths. Recheck before activation; do not touch their dependency files.
- PRIME's second activation-design judgment ACCEPTED exact handoff pin
  `de08711183e94065b12b3a4d24765b333a760a1e`. This is not implementation
  approval or a PR review cycle. The preflight's two overlapping ACTIVE headers
  were stale: governed recap #742 and PR011A3 #366 are already merged ancestors.
  Their historical handoff headers were released in this guarded activation,
  without changing their preserved implementation contracts. No open PR overlaps.
- On 2026-09-28 PRIME authorized a bounded amendment in this same serial PR:
  project exact Buddy-local terminal generation authority and safely settle the
  matching client attempt. The response model/helper/tests were added to §4's
  lease before implementation; no SERVER status API, retry of unknown work,
  abandonment policy, successor PR, or runtime effect is authorized.
- Allocate the named isolated checkout only after this activation is on main.
  Record that activation commit as the implementation's exact dispatch base.
  No synthetic stack or new task is authorized.

| Lane fact | Value |
| --- | --- |
| Branch / isolated checkout | `codex/demo-world-scoped-statblock-drafts` / `/tmp/dmb-world-statblocks-fp0eww` |
| Runtime/state ownership | New API `8817`, UI `5198`, checkout-owned `out/`; serialize changes to the designated isolated PostgreSQL pair at `54329` (`dungeonmind_demo_ofconks_v1`, `dungeonbuddy_application_state_demo_ofconks_v1`). Existing API `8816` / UI `5197` and operator `5196` remain untouched. Tests use disposable roots. Copy only verified demo registry/runtime inputs when needed, not a shared writable output symlink; no C1/C2 mutation or DB authority migration. |

- Runtime: serialize demo environment changes; use Of Conks and one existing
  synthetic managed World on the same isolated DB pair, never C1/C2 data.
  A lane-owned output root must preserve the existing candidate/journal store
  containment checks. Reuse accepted SERVER generation, not copied responses.
- State-authority sync after merge: this handoff completion plus the sole
  roadmap and byte-identical `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-demo.md`.

## §3 Observable paths and adversarial sequences

1. Managed A with exact head → World-mode projection → create A draft → real
   generation → candidate whose `source_draft_id` resolves to A → reload A.
2. A head resolution pending → B: no late A create dispatch, no B fallback.
3. A create pending → B: A may durably exist, but late response cannot auto-
   launch generation or install its join into B; retain truthful recoverability.
4. A generation already dispatched → navigate/reload: completion belongs to A.
   Return to A reconciles existing lifecycle/request identity without another
   blind generation. B neither exposes nor mutates A's candidate/working copy.
5. A dirty candidate copy → B → A: restore A's exact unsaved working copy.
6. Clear/new attempt, unmount, Plan change or foreign exact ID during load:
   superseded UI callbacks do not change the current workspace or placement.
7. Unknown managed World, contradictory projection identity or foreign revision:
   fail before draft/provider admission. No legacy/C2 fallback.
8. World-only draft → begin campaign publication: typed rejection before any
   operation admission, graph read or write. Existing campaign publication passes.
9. A terminally failed A → explicitly start distinct B; a delayed/stale A
   response may preserve A's durable terminal history but cannot settle, replace,
   or unlock B. Generic transport uncertainty and unproven local state keep A
   unresolved.

## §4 Files in scope — ACTIVE write lease

| Action | Path | Purpose |
| --- | --- | --- |
| Modify | `apps/live_control_server/models/threat_draft.py` | Explicit V2 world-only draft/request/summary; V1 preserved |
| Modify | `apps/live_control_server/services/threat_draft_store.py` | Version-safe immutable scope and every update/journal round-trip |
| Modify | `apps/live_control_server/routes/threat_drafts.py` | World registry admission and typed response union |
| Modify | `apps/live_control_server/services/statblock_candidate_generation.py` | Consume versioned drafts without changing SERVER body; project exact journal-proven terminal disposition |
| Modify | `apps/live_control_server/models/statblock_candidate_workflow.py` | Optional typed terminal-outcome proof on the existing generation response; preserve generic failure compatibility |
| Modify | `apps/live_control_server/services/threat_publication_operations.py` | Owning-boundary World-only publication rejection |
| Modify | `apps/live-control-ui/src/api/types.ts` | Exact draft/request/summary wire union |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Typed calls; no new global context store |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx` | Scope admission, async launch guards and scoped restore |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx` | Deferred callbacks, exact ownership and legacy regressions |
| Modify | `apps/live-control-ui/src/statblocks/revision/statblockRevisionAttempt.ts` | Consume version-independent common fields or explicit draft union; no V2-to-V1 cast |
| Modify | `apps/live-control-ui/src/statblocks/revision/StatblockRevisePanels.tsx` | Version-safe proposal history/revision presentation |
| Modify | `apps/live-control-ui/src/statblocks/revision/statblockRevisionAttempt.test.ts` | V1/V2 revision lineage and reconciliation |
| Add | `apps/live-control-ui/src/surface/modules/statblockDraftScope.ts` | Small pure scope/restore guard if needed |
| Add | `apps/live-control-ui/src/surface/modules/statblockDraftScope.test.ts` | Pure guard support, not substitute for mounted proof |
| Modify | `tests/test_threat_draft_store.py` | V1/V2 and journal/acceptance round-trip |
| Modify | `tests/test_threat_draft_routes.py` | Registry admission, scope filtering, foreign/unknown requests |
| Modify | `tests/test_statblock_candidate_generation.py` | Exact source-draft lineage and unchanged provider contract |
| Modify | `tests/test_statblock_candidate_routes.py` | Typed route and generation/recovery regression |
| Add | `tests/test_world_scoped_threat_publication_guard.py` | Zero-operation/graph-call World-only rejection |
| Modify | `Docs/Plans/HANDOFF-DEMO-world-scoped-statblock-drafts-v1.md` | Activation facts and evidence pointer only; steward owns design |

Bounded discovery: at most three additional existing `apps/live_control_server/`
files and their three corresponding focused tests, only where direct V1 draft
validation/response typing prevents V2 draft candidate/edit/accept round-trip.
Record exact paths and reason before review. No other schema, operation snapshot,
publication proposal, query, media, provider or registry policy is included.

## §5 Exclusions and collisions

| Path | Boundary |
| --- | --- |
| `pyproject.toml`, `uv.lock`, UI lockfiles | Rules/other owners; no dependency change |
| `apps/live_control_server/integrations/dungeonmind/**` | No graph authority/read/write cutover |
| `apps/live_control_server/integrations/worldkeeper/**` | J3 owner seam remains separate |
| `src/graph_memory/vnext/**`, `Docs/Contracts/vnext/**` | No kernel/domain/profile changes |
| `apps/live_control_server/services/threat_publication_proposals.py` | No World-only contribution policy |
| `apps/live_control_server/models/threat_publication*.py` | No rewritten historical operation snapshots/digests |
| `corpus/**` | Licensed/local sources stay uncommitted and untouched |

No image/job/provider framework, campaign registry, Plan placement, broad
Workbench redesign, migration of existing assets or second implementation PR.

## §6 Explicit durable scope/versioning decision for review

### V1 compatibility

Existing `dmb_threat_draft_v1` records retain valid nonblank `world_id` and
`campaign_id`, existing byte/semantic/digest representation and legacy campaign
behavior. Their reader may expose an internal campaign-scope view, but may not
rewrite them, add persisted scope fields or silently upgrade them on reload.
Existing campaign create bodies remain valid and create V1 records.

### New World-only branch

The new branch is explicitly versioned `dmb_threat_draft_v2`, with
`scope_mode="world"`, exact nonblank `world_id`, and `campaign_id=null`.
All other authored fields and candidate/accepted-mechanics lifecycle semantics
remain as in V1. The new create request explicitly selects `scope_mode="world"`
and requires null campaign; it must not be inferred from a blank legacy value.
Unknown schema/mode, blank World, mixed world+campaign or V1-null campaign fail
closed. No V2 campaign branch is needed for this slice.

The server verifies World-only create ownership against the managed World
registry. Scope is immutable after create. If a graph revision is supplied,
verify its exact selected-World ownership through existing authority; never
accept a foreign override. Missing/unknown head is not permission to fall back
to C2. The existing explicit freestanding choice can produce a correctly owned
draft with null graph pin and empty pointer lists, without claiming grounding.

Draft reads/updates, candidate journal/recovery, accepted-mechanics bookkeeping
and list summaries must round-trip the exact version. The API/type union is
explicit; old campaign-filtered results retain their shape. World-only summaries
carry their World/null-campaign scope. Immutable operation snapshots and digests
are not migrated. World-only drafts are rejected by the publication service's
eligibility boundary before operation/graph effects; show that limitation in UX.
Keep the publication panel campaign-only by narrowing the draft in Workbench;
show the World-only limitation instead of mounting it with a fake V1 view.
The existing operation lock infrastructure may create its lockfile before
eligibility. The required zero-effect boundary is no operation admission or
ledger write and no graph read/write; do not misreport lock acquisition as
publication or require an unrelated lock redesign.

### Generation and restore

Capture launch scope + activation generation before any await. Check exact
projection response World, scope and campaign fields; no `response || default`
identity repair. Recheck activation before create and before starting generation
from its returned draft. Once dispatched, use existing durable request/candidate
lineage and recovery instead of canceling/rebinding its result on navigation.

Generation recovery must bind the already accepted optional `client_request_id`:
mint it once per deliberate generation attempt and persist it under the original
verified scope/draft, with the exact source draft version, **before dispatch**.
Pass that same key to generation. Retain it while the outcome is unresolved;
reload, disconnect, navigation, Clear and remount must not silently replace it.
Same-attempt retry/reconciliation reuses the exact key and original source
version, including after candidate attachment advances the current draft version.
A new key requires an explicit new attempt after the prior attempt is settled;
this slice does not add an unresolved-attempt abandonment policy. Clear may
clear visible working state, but may not erase the unresolved attempt identity.
If local persistence cannot preserve the key, fail before starting a request
that promises recovery, or visibly retain an unresolved/non-auto-retry state.
Use the existing durable generation journal; no generic job store or SERVER
contract change is permitted.

### Bounded terminal-outcome projection amendment (2026-09-28)

The existing public generation response may carry an optional typed
`terminal_disposition` only when Buddy has loaded and validated the exact durable
local generation journal entry/tombstone for the response's request ID, stored
request-body digest, draft ID and original source-draft version, and has loaded
that same draft to establish its immutable selected World/campaign scope. The
disposition echoes those identities and exact scope; it does not expose provider
internals or imply a SERVER status lookup. Existing generic failure fields
remain unchanged for compatibility.

Do not emit the disposition when the journal is missing, corrupt, mismatched,
or cannot be persisted, or when only an HTTP/transport failure suggests that the
request may have ended. Those cases remain unresolved and reuse the same request
identity. No POST replay is used as a status probe for an unknown SERVER
operation; this amendment only projects already durable Buddy-local terminal
authority such as A's existing record.

The client settles only the exact current unresolved local attempt matching the
returned draft ID, client request ID, original source version and admitted
scope. It retains A's request identity and terminal proof in scope-local history
before offering the existing explicit “Start another threat” action. Starting
B creates a distinct request ID; delayed A completion may append/update only
A's history and may never settle, replace, or unlock B. A terminally proven
failure is settlement, not abandonment. No policy for abandoning an unknown or
unresolved attempt is added.

Consume `useSelectedWorld()` and existing admitted legacy campaign context.
Unknown/loading/error context cannot submit, restore foreign work, or fall back.
Scope the workbench convenience join by admitted World/campaign. Old joins are
hints requiring a server draft load, never ownership authority. Verify restored
candidate membership/`source_draft_id` against that exact draft before allowing
edit, revise, regenerate or acceptance. Preserve each scope's dirty working copy.
An explicit foreign candidate/draft ID must fail closed, not override selection.

Plan document is launch context, not asset ownership. Document switches cannot
attach results to the new Plan. Do not introduce document placement in this slice.
Only description/intent/context go to the unchanged SERVER generation contract;
recording a World revision does not claim the model retrieved that graph.

## §7 Evidence required to merge

- Store/route proof: legacy V1 unchanged; V2 create/reload/update/journal/accept
  retains immutable World/null campaign/version; registry unknown/mixed/foreign
  identity rejected; scoped lists do not return foreign entries.
- Provider seam: unchanged SERVER request shape, real candidate exact source-
  draft lineage, failure/retry/reconciliation preserves identity and authored brief.
  Reload/disconnect while provider pending retains exact attempt key/source
  version; later same-key recovery after draft version advancement, Clear/New
  attempt interleavings and persistence failure cannot launch a second logical
  provider generation or silently discard an unresolved key. In addition,
  exact journal-proven terminal replay (zero external calls) settles only the
  matching attempt; absent/mismatched/unpersisted terminal proof remains
  unresolved, terminal history survives reload/remount, and A→B plus late-A
  interleavings preserve B's identity.
- Mounted Workbench: defer head/create/generate/load callbacks at each §3
  interleaving, inspect dispatched requests and localStorage writes, verify A→B→A
  restore including dirty copy. Helper-only guards are insufficient.
- Publication service: World-only input yields typed eligibility rejection and
  zero graph/operation effects; campaign publication regression remains valid.

Exact scoped commands (run from implementation root/UI as indicated):

```bash
.venv/bin/pytest -q tests/test_threat_draft_store.py tests/test_threat_draft_routes.py tests/test_statblock_candidate_generation.py tests/test_statblock_candidate_routes.py tests/test_world_scoped_threat_publication_guard.py tests/test_cutover_threat_authority_port.py
.venv/bin/ruff check apps/live_control_server/models/threat_draft.py apps/live_control_server/services/threat_draft_store.py apps/live_control_server/routes/threat_drafts.py apps/live_control_server/services/statblock_candidate_generation.py apps/live_control_server/services/threat_publication_operations.py
cd apps/live-control-ui
npx vitest run src/surface/modules/StatblockWorkbenchModule.test.tsx src/surface/modules/statblockDraftScope.test.ts src/statblocks/revision/statblockRevisionAttempt.test.ts --maxWorkers=1
npm run typecheck
cd ../..
git diff --check
```

Include any bounded-discovery tests and existing publication-operation regression
cohort once exact collection paths are established. If no optional scope helper
is created, omit only that test path. Do not call a missing/empty cohort green.
UI typecheck currently has the inherited unchanged ThreatPublicationPanel JSX
error; compare base/head and report it, rather than broadening the lease.

Live proof on exact implementation head: use normal Plan Tools → Statblock in
isolated Of Conks A; create a short GM-invented creature brief, launch real
generation, navigate to synthetic B while pending, return/reload A and recover
the exact completed candidate without ID repair or blind duplicate generation.
Inspect stable ownership and source-draft identity from durable reads. Reopen
and edit a working copy, switch A→B→A, and preserve it. Prove publication is
unavailable with the truthful World-only reason. Record observed model, provider
calls if available, input/output tokens, cost if reported, model and wall time.
Necessary bounded API calls are operator-authorized; no per-call permission
prompt. Missing provider/runtime access is an owner-routed dependency, not a
reason to fabricate a candidate or treat a fixture as live acceptance.

## §8 Handback and §9 acceptance

Implementation checkpoint 1 (not merge-ready): explicit V2 models and
version-preserving store updates; mixed-version list summaries; existing
generation body consumes the union unchanged; World-only publication rejects
with the existing typed `publication_source_mismatch` response and a truthful
scope limitation before graph/ledger effects. The owning backend cohort above
passes **129 tests**, scoped Ruff and diff check pass, and no model calls ran.
The separately inspected historical `test_threat_publication_identity_routes.py`
has three stale `pub_svc.kernel` fixture failures on both exact dispatch base
and this implementation; it is not reported green or repaired outside the lease.
Registry/revision route admission, frontend union/async/attempt recovery,
exact-head live generation and independent implementation review remain false.

Implementation checkpoint 2 (not merge-ready): the CRUD route now admits managed
World ownership from the existing registry and verifies exact revision ownership
through the existing read port before create/update. Explicit freestanding
snapshots do not read the graph. Unknown/mixed scopes, foreign/missing revisions,
unavailable authority, V2 update/restart and legacy/scoped lists have owning-route
regressions. The complete backend cohort passes **140 tests** (11 inherited
warnings). Frontend draft/request unions and both revision/history consumers
preserve V1/V2 explicitly; World-only mechanics never mount campaign publication.
The new pure scope/generation-attempt helper plus revision tests pass **29 tests**.
The helper is preparation, not mounted recovery evidence: scoped cache admission,
selected-context submission, async navigation guards and same-attempt browser
recovery remain to be wired and proved. No paid calls have run.

The larger Workbench/revision cohort currently reports **114 passed / 20 failed**.
Do not report that cohort green: create/publication fixtures still mock the old
bootstrap endpoint while the current component reads native projection. A fresh
comparison at `671cc18deafd4a39dd822931eebaa90f014e6d27` (the tested production
files are unchanged from dispatch base) reports **113 passed / the same 20 failed**.
These are inherited fixture failures, not accepted proof; the mounted-scope work
must update the stale owning fixtures and prove the new behavior. Typecheck
reports only `ThreatPublicationPanel.tsx:553` (`TS2503`, JSX namespace); the file's
SHA-256 is identical on dispatch base and head
(`c7b2257adbffd1b3bd7e7de04cb33b3d779df4a9e4a8e50830c2f3e3d05c0fd8`).
Scoped Ruff and diff check pass. Real exact-head generation/recovery and independent
PRIME implementation review remain outstanding; no merge or full DEMO acceptance.

Implementation checkpoint 3 (not merge-ready): Workbench now consumes admitted
selected-World/legacy-campaign context; no scope is fabricated. Create/head/load
callbacks are activation-guarded, restored candidates require server-owned draft
scope and exact candidate-ref membership, and Advanced/cache hints cannot grant
edit/revise/accept authority. Convenience joins and dirty copies are scoped;
generation request identity and original source version are persisted before
dispatch and retained through navigation, Clear, transport loss and reload.
Successful background completion remains in its launch scope; already-attached
candidate recovery uses reads rather than a second generation. World-only
publication shows its limitation without mounting campaign publication.

The explicitly filtered checkpoint cohort passes **51 tests**: **22 mounted
Workbench interleavings/ownership cases** and the **29 scope/revision tests**.
The remaining **111 legacy Workbench tests were excluded by this checkpoint
filter**, not passed or waived; their fixtures must be migrated to admitted
context and server-owned candidate lineage before the full §7 cohort is proof.
Mounted cases include both legacy campaigns, delayed candidate/draft reads,
Plan-document changes, A→B→A dirty restore, lost response after attachment,
same-key recovery after version advancement, and pre-dispatch persistence failure.
Structured failure retains the unresolved key: the current response does not
reliably prove terminal journal status, so no terminal-failure abandonment policy
or new provider contract is inferred. Scoped Ruff and diff checks pass;
typecheck still has only the previously hashed inherited JSX error. A read-only
request to the existing Of Conks runtime confirms its World projection identity
fields match the client checks. This is not the required exact-head live witness.
No paid calls, independent implementation review, merge or J4 acceptance yet.

Implementation checkpoint 4 (not merge-ready): legacy owning fixtures now admit
an actual campaign context and source-draft identity. The mature revision and
publication cohorts use exact generated-source versions and native projection
reads rather than the retired bootstrap mock. All **29 mounted revision/
publication cases** pass. An ownership-failing load also now quarantines the
previous draft's action authority without deleting its scoped dirty copy or
journal; two new mounted foreign/orphan cases exercise that transition.

The explicitly filtered combined cohort passes **82 tests / zero failures**
(24 mounted World/campaign cases, 29 scope/revision helper cases, and the 29
legacy mounted revision/publication cases). **82 other UI cases remain excluded
by this checkpoint filter**; the full §7 cohort is not green. A full intermediate
fixture-migration probe reported 77 passed / 85 failed before the revision/
publication repairs; this is author diagnostic evidence, not acceptance or a
claim that all those failures are inherited. Generation, acceptance/reload and
remaining interleaving fixtures still require owning-boundary migration.
The backend cohort independently reran on checkpoint 3: 140 passed, 11 warnings,
28.62 seconds. Typecheck still reports only the unchanged inherited JSX error.

Exact-head local runtime preparation exposed missing disposable-admin DSN
configuration and an offline configured SERVER endpoint. Normal configuration
was used; process-environment credential copying was rejected and not retried.
The new API was stopped after the authentication/readiness failures; operator
5196 and existing 8816/5197 were untouched. SERVER's existing owner supplied the
accepted runtime/configuration boundary and is preparing an isolated service;
PRIME was asked for the intended persistent demo-admin configuration source.
No credential values are requested in the handback, no model call ran, and the
required real generation/reload witness and implementation review remain false.

Implementation checkpoint 5 (not merge-ready): the remaining legacy generation,
acceptance and create/restore fixtures now prove admitted source ownership rather
than promoting Advanced IDs into authority. Acceptance/recovery passes all **35
mounted cases**; the create/restore cohort passes all **22 cases**; generation
interleavings pass all **4 cases**, and the previously repaired editor
interleavings pass all **4 cases**. These are targeted reruns, not substitutes for
the complete §7 run. Candidate switches in recovery tests use ordinary candidate
loads with explicit server-owned lineage. Null-head creation requires explicit
freestanding opt-in, failed native projections do not inherit old bootstrap
semantics, and successful generation fixtures bind the persisted request key.

The preceding full migration probe reported **153 passed / 11 failed / zero
excluded** before the last create/restore corrections. The final full cohort
must now rerun against a committed head. Scoped Ruff and diff checks pass;
typecheck still reports only the hashed, unchanged JSX namespace failure.
The operator reaffirmed standing authorization for necessary bounded OpenAI
calls; no per-call prompt is required. The prepared isolated SERVER runtime is
available, but connecting to the discovered persistent demo database pair is
separately pending exact-target approval. No model calls or DB writes have run
for this live witness, and independent implementation review remains outstanding.

Implementation checkpoint 6 (code/test evidence complete; live acceptance still
false): exact code head `2e931b31643ca00ec7f322d63618ee4d7aeab285` passes the
entire §7 UI cohort: **164 passed / zero failures / zero excluded** (135 mounted
Workbench cases and 29 scope/revision helper cases). The owning backend rerun
passes **140 tests**, 11 inherited warnings, in **29.86 seconds**. Scoped Ruff
and diff checks pass. Typecheck has only the independently verified unchanged
`ThreatPublicationPanel.tsx:553` JSX namespace failure.

Re-anchor `33b21c8687724c266dbc58af2161c2d06d5e8817` incorporates current main
`671cc18deafd4a39dd822931eebaa90f014e6d27`; its only additions to the tested code
head are the already-landed roadmap and mirror checkpoint. All executable and
test files are byte-identical. A final exact review-head verification remains
part of independent review; prior scoped/filter runs are no longer substituted
for the full owning cohort.

The discovered Of Conks authority is the persistent named demo pair on
`54330`/`54331`, not the disposable `54329` recorded in §2. Auto-review rejected
connecting the isolated API to those persistent targets without exact-target
approval; the action was not retried or bypassed. The separate operator question
is pending. Existing operator runtime and C1/C2 remain untouched. SERVER's owner
prepared an isolated accepted runtime at `127.0.0.1:7861`, with lane-specific
asset collections and its ordinary private configuration. No paid calls,
required exact-head browser witness, implementation approval or merge yet.

Implementation checkpoint 7 (Cycle 1 repair, not merge-ready): PRIME formally
held exact head `2e33b57737164ac0393975ab31d42a1c91a43d34` in
[review 5333492877](https://github.com/Drakosfire/DungeonMindBuddy/pull/785#pullrequestreview-5333492877).
Its independent complete-cohort evidence is 164/164 UI tests, 140/140 backend
tests (11 warnings, 28.19 seconds), scoped Ruff/diff pass and the same inherited
JSX error. Approval was not granted: a delayed old completion could replace a
newer settled same-World recovery pointer, and the live witness remains false.

The repair compares settlement with the exact currently persisted draft,
request and source-version identity, even after the newer attempt settles.
Superseded or missing pointers are not replaced or recreated; current original
attempts still reconcile after unmount, retry and source-version advancement.
The Workbench honors the settlement result before installing completion state.
PRIME's mounted two-generation/unmount/remount/reload regression reproduced
both old-pointer and old-candidate failures before the fix. The pre-commit full
UI cohort now passes 169 tests with zero exclusions, including four additional
helper cases for changed identity/missing pointers. Exact frozen-head evidence
and the subsequent independent review remain required; the PR evidence record
identifies that head. PRIME subsequently merged Buddy #780 at
`11d7b5801b51f664e7a6eeafcb2aa2b0f5922b71`, pinning accepted DungeonMind
`b83baf82c381b1929c2c7989326d667200ff544c` after its independent Cycle 2
PASS (review 5333525840; 98 tests, zero skips). The repair incorporates that
integration state without changing dependency policy. Final backend evidence
must use that accepted pin in a private lane environment, not the prior
runtime's shared Python environment or its old dependency. WorldKeeper remains
`49a8620f066ce7ef8972a699020c012f50af9158`; #780 does not prove J3/native
admission or the asset live witness. No paid calls, live acceptance or merge
of this slice is claimed.

Implementation checkpoint 8 (PRIME-authorized terminal-outcome repair; not
independently reviewed): the existing generation response now includes an
optional typed terminal disposition only after exact Buddy journal reread,
request-body digest verification, and same-draft immutable-scope validation.
Unknown transport/generic HTTP failure and failed journal persistence remain
unresolved. The mounted client archives exact terminal proof before settling
only the matching local attempt; explicit B receives a distinct key, and late A
can add its history but cannot alter B. No provider call, SERVER API change,
database mutation or runtime restart was made.

- Backend store + candidate-generation + publication guard cohort: **104 passed**.
- Candidate-route response serialization witness: **1 passed**, asserting the
  new typed proof crosses the existing route unchanged.
- Full owning UI cohort: **177 passed / zero failed / zero excluded** (137
  mounted Workbench, 17 scope/history helpers, 23 revision-attempt cases).
- Scoped Ruff and `git diff --check` pass. Typecheck still reports only the
  unchanged inherited `ThreatPublicationPanel.tsx:553` JSX namespace error.
- The remaining TestClient-backed draft/candidate route cohorts reproduce the
  known local harness hang on their first request; they were stopped, not
  reported green. The new route-serialization test is direct and bounded; an
  independent exact-head backend verifier should rerun the canonical route
  cohort in its accepted host harness. PRIME review of this new head remains
  required; this checkpoint is not merge approval.

- [x] Design decision independently accepted and handoff ACTIVE before code.
- [ ] Exact dispatch base, branch, head, nano-commit story and serial topology recorded.
- [ ] V1 preserved and V2 scope survives every durable lifecycle update.
- [ ] Managed World exact admission and foreign identity failures proved.
- [ ] Real generation/recovery works in selected A, with no B mutation or duplicate launch.
- [ ] Mounted asynchronous/cached restore proof covers all §3 cases.
- [ ] World-only publication rejects at its service boundary before effects.
- [ ] Tests, inherited failures, changed paths and observed paid telemetry are honest.
- [ ] No graph publication, image/Plan-placement or full DEMO acceptance claimed.

Stop/rebrief for a new campaign identity policy, World graph publication,
asset rebinding/migration, unsupported native head contract, provider/job/media
infrastructure, DM/WK/SERVER changes, unleased writes or missing owning-boundary
proof. Return the precise contract gap to the steward; do not open another PR.
