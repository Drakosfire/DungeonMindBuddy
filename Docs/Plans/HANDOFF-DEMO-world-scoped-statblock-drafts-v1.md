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
  World-only drafts do not enter campaign-only graph publication.
---

# HANDOFF — DEMO: World-scoped statblock drafts

**Created:** 2026-09-27
**Status:** ACTIVE — independent scope/versioning design accepted; serial isolated implementation authorized
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

## §4 Files in scope — ACTIVE write lease

| Action | Path | Purpose |
| --- | --- | --- |
| Modify | `apps/live_control_server/models/threat_draft.py` | Explicit V2 world-only draft/request/summary; V1 preserved |
| Modify | `apps/live_control_server/services/threat_draft_store.py` | Version-safe immutable scope and every update/journal round-trip |
| Modify | `apps/live_control_server/routes/threat_drafts.py` | World registry admission and typed response union |
| Modify | `apps/live_control_server/services/statblock_candidate_generation.py` | Consume versioned drafts without changing SERVER body |
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
  provider generation or silently discard an unresolved key.
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
