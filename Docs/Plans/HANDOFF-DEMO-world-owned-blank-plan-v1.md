---
pr_body_template: |
  ## Handoff pointer
  - Workstream: DEMO / J1 — World-owned blank Plan
  - Direction: STEWARD → CODE → PRIME
  - Handoff: Docs/Plans/HANDOFF-DEMO-world-owned-blank-plan-v1.md
  - Topology: serial; this is the single authorized implementation PR

  ## Verification pointer
  - Exact dispatch base: `9f358bb9ecf4d28338ae4b6b0ef5e2c316700d59`
  - Review contract: ACTIVE handoff, cumulative diff, §7 evidence
---

# HANDOFF — start a World-owned Plan before importing anything

**Created:** 2026-09-27  
**Status:** ACTIVE — PRIME accepted scope and authorized this implementation lane
**Handoff locator:** canonical handoff on accepted Buddy main; PRIME-authorized exception activates it in this implementation PR.
**Workstream / owner:** DEMO / J1; Buddy Content/Plan ownership, not DungeonMind  
**Direction:** STEWARD → CODE → PRIME  
**Design authority base:** `fa740c73f66192a44926712661d9489ff12e54a8`  
**Activation record (2026-09-28):** PRIME accepted the World-Plan contract and explicitly activated this bounded implementation in the same PR. After #786 merged, this lane re-anchored to fresh `main` at exact dispatch base `9f358bb9ecf4d28338ae4b6b0ef5e2c316700d59`. #787's native source-authority witness admitted the actual 48,777-byte source variant (SHA-256 `4aeb773a02c41cfffb79abcb2ca44da72d5a2eb8ad331cc6f9a417a5c2919186`), while the pinned 48,778-byte source has SHA-256 `7a379fc9025635b1862b6af7eb5a43dd1ee9387b51cf63ba505491fffe7e68f1`; the admitted variant is the original with its final LF absent. This proves source authority only, not extracted facts or a semantic graph. The source witness is not a gate for this document-only capability. The previously observed unsaved local Plan is user data and is not acceptance evidence.
**Dispatch rule:** one isolated implementation checkout from the exact base above. PRIME expressly authorized this implementation PR to activate the already-landed handoff; no separate status/design PR or successor PR is authorized.
**PR topology:** serial  
**PR authorization:** open/update exactly this assigned implementation PR; no successor/repair PR.
**PR title:** `DEMO: start a World-owned Plan before source import`

Repository law is `AGENTS.md`; steward authority is
`Docs/Plans/STEWARDS-HANDOFF-demo.md`; current state lives only in
`Docs/Roadmaps/ROADMAP-demo.md`. This ACTIVE handoff leases only §4 paths.
Runtime and database ownership remain isolated from the live J1 source witness
and the user's unsaved Plan.

## §1 Mission and merge-ready invariant

A new GM can create a named managed World, immediately author a blank Plan,
and explicitly save/reopen that Plan under its real World identity before
creating a source, campaign, session or knowledge head.

**Invariant:** a World-owned Plan carries the exact server-allocated World ID
and no campaign/session surrogate from local draft through Content WorkObject,
immutable WorkRevision, ordinary editor Save, selector, URL, reload and restart.
Wrong-scope or superseded results cannot become the active document or receive
the wrong draft's save. World/document creation does not publish knowledge.
Existing campaign Plan and Runbook contracts remain unchanged.

Pre-dispatch critique:

- One capability: first-customer World-owned Plan authoring/persistence. The
  World container API already exists; its ordinary UI entry is a consumer,
  not a second new World identity contract.
- Likeliest falsifier: start World A's first Save, switch to B, receive A's
  create/commit response, then save/reload B or adopt A under B.
- Owning proof: PostgreSQL Content/route round-trip plus mounted create/save
  races and ordinary browser restart. A URL or fixture alone is insufficient.
- Under-tested seam: Content ownership currently cannot represent this scope;
  frontend World selection alone must not masquerade as durable ownership.
- Stop if the implementation needs a generic workspace/scope framework,
  changes another repository, or couples document creation to graph genesis.

## §2 Re-anchored context, authority and topology

Observed on frozen #785 `07ec031ab5b62b8dbcd34f51ed4b6eaf0fa25262` with
accepted DungeonMind `b83baf82…`, isolated API8817/UI5198 and initially empty
handoff DB pair at54329:

1. World picker only offers **New World in Build**. Actual new-World submission
   is embedded in Build's source-create/import dialog and requires a source title.
2. Existing managed World `pr776-second-synthetic-world` had no source document
   and no graph head, yet opened a real local editable Plan shell.
3. Ordinary author → Save → reload preserved the authored text in document
   `da85ba58-ff9a-4599-8ed5-ea301c076367`, committed revision3.
4. Public GET returned `world_id=null`,
   `campaign_id=pr776-second-synthetic-world`, `target_session=1`.
   This is document-persistence evidence, **not** World-only ownership.

Current owning code agrees: workspace create rejects `world_id` for Plan;
Content requires nonblank `campaign_id`; SQL declares that column NOT NULL.
`world_id` is already a nullable Content column, but Plan creation never sets it.
The blank-shell/promotion lifecycle already exists; reuse it, do not rebuild it.

Authorities: accepted APP-STATE Content architecture, shared Markdown Canvas,
selected-World primitive (#776), managed Plan reads (#775/#782), blank authoring
shell (#661), and the DEMO roadmap. Those predecessors do not prove this contract.

- At design time, #785 was the only open DEMO implementation PR. At activation,
  fresh review of current open PR path leases found no overlap with this serial
  lane. #786's independent four-code-path statblock lease was disjoint and then
  merged at this base; it remains untouched. No stacked predecessor.
- #787 source witness: merged at `f7ce9b99b8e9b73129c6f474989cdb30875a31c8`
  (reviewed head `232a42614b1453a815df2dd12f172c0be3c7a155`). Ordinary Build import admitted World
  `of-conks-and-cons`, document
  `1e00479a-cd51-4ffc-81f7-c980b32fed6a`, revision 2, exact stored span
  `0..48777`. The admitted 48,777-byte content SHA is
  `4aeb773a02c41cfffb79abcb2ca44da72d5a2eb8ad331cc6f9a417a5c2919186`; the
  pinned original is 48,778 bytes with SHA
  `7a379fc9025635b1862b6af7eb5a43dd1ee9387b51cf63ba505491fffe7e68f1`.
  The admitted variant is the pinned source with its final LF absent.
  Do not call these byte-identical.
  This establishes durable native source authority after reload/fresh API
  process only; it establishes no extracted semantic facts, graph head, or
  retrieval. Preserve this independent witness and do not migrate or reconfigure
  its shared database for this slice.
- Native empty-KnowledgeSpace initialization is separately MIND-owned. MIND #82
  design acceptance is not its runtime implementation and is **not a prerequisite
  to a document-only Plan**. No DungeonMind or WorldKeeper write in this slice.
- Named successor: first-customer source admission/governed knowledge and later
  Agent retrieval; World-only Run adoption remains its later consumer contract.
- Use one isolated checkout, named API/UI ports, a disposable APP-STATE
  PostgreSQL database pair and owned output/source root. Do not run migrations
  against or modify the live J1 source-witness database. Do not upgrade the
  frozen #785 rehearsal underneath its running process.
| Runtime/state ownership | This lane owns only API 8821, UI 5201, a disposable PostgreSQL pair on 55441, and its isolated World/output roots; it does not own shared 8817/5198 services or the live J1 database. |
- Predecessor sync in this PR: #785 exact merge/head/review evidence, #787 exact
  merge/head/review and source-witness limitation, both predecessor handoff
  states, roadmap and identical design-agent mirror. Do not premark this slice
  or J1–J6 accepted.

## §3 Observable and adversarial paths

- **New World:** name-only intent through existing world-container API; returned
  exact ID selects ordinary Plan, no placeholder source or graph initializer.
- **Existing graphless World:** blank editor/tools ready without source/recap;
  first explicit Save promotes current content to that exact World-owned Plan.
- **Reload/restart:** reopen same UUID and committed Markdown with same ownership.
- **Second World:** its inventory and local draft are disjoint, even if a campaign
  happens to have the same textual ID as either World.
- **Explicit wrong document:** mismatch is an error; never default to C2, create
  another document, or borrow the other World's draft.
- **World create succeeds / Plan activation fails:** retain/reselect the existing
  World; retry does not manufacture another World or source.
- **Plan create succeeds / snapshot or commit fails:** retain created document
  identity and draft bytes; ordinary retry reconciles that document, not a new POST.
- **A Save pending → B selected → late A completion:** A remains recoverable,
  B remains authoritative; mounted publication and promotion pointers are scoped.
- **Two simultaneous saves:** existing CAS/lease guarantees still own the result;
  a conflict preserves edits rather than silently replacing them.
- **Legacy C1/C2 Plan/Runbook:** unchanged campaign identity/target-session paths.

## §4 Write lease — ACTIVE for this implementation PR only

| Path | Bounded role |
| --- | --- |
| `src/application_state/content/types.py` | World-only Plan content shape |
| `src/application_state/content/service.py` | World Plan service boundary |
| `src/application_state/content/repository.py` | PostgreSQL persistence |
| `src/application_state/migrations/versions/20260928_0007_world_owned_plan.py` | Additive migration and safe downgrade |
| `apps/live_control_server/services/workspace_document_registry.py` | World Plan registry/read contract |
| `apps/live_control_server/routes/workspace_documents.py` | World Plan routes |
| `apps/live_control_server/routes/live.py` | Managed Plan-context branch only |
| `apps/live_control_server/services/tiptap_markdown_write.py` | Scope admission and confirmation binding |
| `apps/live-control-ui/src/api/types.ts` | Explicit V2 wire unions |
| `apps/live-control-ui/src/api/liveApi.ts` | Exact V2 API clients |
| `apps/live-control-ui/src/selectedWorld/WorldSelector.tsx` | Name-only World create UI |
| `apps/live-control-ui/src/selectedWorld/SelectedWorldContext.tsx` | Exact selected-World admission |
| `apps/live-control-ui/src/selectedWorld/SelectedWorldContext.test.tsx` | Selected-World regressions |
| `apps/live-control-ui/src/selectedWorld/WorldSelector.test.tsx` | World-create UI regression |
| `apps/live-control-ui/src/selectedWorld/WorldSelector.test.tsx` | World-create UI regression |
| `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` | World-owned Plan surface and local recovery |
| `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx` | World Plan V2 and recovery regression |
| `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | Existing managed-document consumer fixtures |
| `apps/live-control-ui/src/api/liveApi.test.ts` | Exact V2 route payloads |
| `tests/test_world_owned_plan_contract.py` | World context/legacy compatibility contract |
| `tests/test_workspace_document_registry.py` | Content/registry invariants |
| `tests/test_live_plan_view_projection.py` | Managed context route evidence |
| `tests/test_tiptap_markdown_write.py` | Prepare/commit semantics |
| `tests/test_live_tiptap_markdown_write.py` | PostgreSQL no-effects and confirmation binding |
| `Docs/Plans/HANDOFF-DEMO-world-owned-blank-plan-v1.md` | Activation facts and implementation authority |
| `Docs/Plans/HANDOFF-DEMO-J1-native-world-source-authority-v1.md` | Completed predecessor state |
| `Docs/Plans/HANDOFF-STATBLOCK-explains-wire-compatibility-v1.md` | Completed predecessor state |
| `Docs/Plans/HANDOFF-BUILD-dogfood-polish-plan-session-affinity-workspace-drafts.md` | PRIME-authorized stale-lease reconciliation: record merged #546 completion and release its historical write lease; preserve its shipped behavior/evidence |
| `Docs/Roadmaps/ROADMAP-demo.md` | Current DEMO sequencing and predecessor sync |
| `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-demo.md` | Byte-identical roadmap mirror |

Bounded discovery: maximum six additional existing frontend paths under
`apps/live-control-ui/src/planSurface/` or `src/workspaceDocument/` (beneath the
same UI root), plus their paired tests, only for World-Plan typing, exact editor
ownership or promotion persistence. Name/reason in handback. Further production
paths, Agent/Run semantics or another lane's lease require steward re-brief.
At activation, the exact base and cohort were rechecked against current PR
leases. This table is the active bounded write lease; new production paths,
Agent/Run semantics or another lane's lease require steward re-brief.

## §5 Exclusions and collision boundaries

No DungeonMind/WorldKeeper/GE/SERVER code or dependency changes; no model calls
needed for this capability. No graph/source admission, extraction, evidence
policy, native genesis, source-body reader or campaign registry. No source DTO
redesign, World deletion/rename, existing document migration/adoption, Runbook
scope migration, Agent/retrieval behavior, statblock/image/Run/Combat work, theme
or shell redesign. No fake campaign, default session1, synthetic graph, manual
ID binding, database-per-World, mutable graph repair or legacy-document inference.

Existing campaign-compatible artifacts whose campaign slug happens to equal a
World ID remain unchanged historical artifacts, not proof of World ownership.

## §6 Exact implementation contract

### Content ownership — one Plan contract, not a generic workspace ontology

Reuse Content's existing WorkObject/WorkRevision/WorkingCopy and World column.
Introduce a typed **World-owned Plan** alongside unchanged campaign-owned Plans:

```text
World-owned Plan:
  kind = plan
  exact world_id = admitted managed World container ID
  campaign_id = null
  target_session = null
  title = GM-facing title
  server-owned opaque document_id + target_relpath

Campaign Plan / Runbook:
  existing nonblank campaign_id and existing target-session semantics
  no reinterpretation of current rows or callers
```

Buddy's consumer boundary verifies the exact managed World before create. Content
stores document ownership; it does not resolve a graph, call MIND, or own World
registry semantics. Make World ownership immutable through all metadata/write
paths. Derive its wire scope from the explicit admitted Content representation,
not a slug naming heuristic.

Use new discriminated World-Plan wire variants with `scope_mode=world`, nonempty
`world_id`, `campaign_id=null`, kindPlan and null target session:

- Explicit World create body: `dmb_workspace_document_create_v2`.
- Record: `dmb_workspace_document_record_v2`.
- Explicit World-filtered inventory: `dmb_workspace_document_registry_v2`.
- Scope-bearing snapshot: `dmb_workspace_document_snapshot_v2`.
- Scope-bearing committed revision: `dmb_workspace_committed_revision_v2`.
- Managed Plan context: `dmb_managed_world_plan_context_v2`.

Keep current unversioned V1 create bodies and all campaign/source/Runbook V1
responses unchanged. Existing unscoped/campaign lists retain V1 semantics and
do not silently mix in World-owned Plans; the new World-specific request lists
only exact World-owned Plans. Reject combined World/campaign selectors and
World-only Runbook/source creation in the new variant. By-ID World-Plan reads
return V2 and consumers explicitly narrow it. Do not return nullable campaigns
under a V1 schema promising strings. Capture exact accepted/rejected union
fixtures in the route/frontend tests before implementation review.
This is one document-ownership contract across its create/read/save boundaries,
not authorization for generalizing every product DTO.

Add a new APP-STATE migration permitting this narrow representation and enforcing
its shape at SQL and domain boundaries. Reuse `world_id`; do not add a generic
scope registry. Preserve every existing campaign row/revision/working copy.
Do not edit historical migration files. A downgrade must refuse nonrepresentable
World-owned rows rather than delete them or invent campaigns.

The managed Plan context also needs an explicit World-only wire variant:
`scope_mode=world`, exact `world_id`, null campaign/session, container-derived
context, no implied graph authority. Current `/plan-view?world_id=…` returns
`dmb_managed_world_plan_context_v1` with campaign equal to World and session0;
that compatibility sentinel must not flow into the new document descriptors.
Keep legacy campaign `/plan-view` behavior unchanged. No other `live.py` route
or Agent/knowledge policy change is leased by this correction.

World-filtered inventory means exact World-owned Plans only, not campaign ID
equality. Campaign-filtered V1 inventory must not gain World-owned rows. Reject
ambiguous/mixed selectors. By-ID reads plus editor save admission must prove
document scope against the selected context before mounting/committing.
Scope-neutral existing ID/revision/CAS write receipts need not be versioned
merely for ceremony; any receipt carrying campaign ownership must be exact.

The save path must close the prepare/commit time-of-check gap:

1. **Prepare:** resolve and verify the stored World-Plan scope against the exact
   selected `world_id` and document identity before creating/updating a
   WorkingCopy, staging bytes, allocating a revision, or causing any other
   persistence effect. A mismatch fails with no partial effect.
2. **Confirmation binding:** issue a confirmation token bound to the exact
   document ID, World ID, expected revision/content digest, and prepared write
   identity. A token prepared for World A/document A cannot authorize a commit
   submitted under World B/document B, even when either request is stale or
   reordered.
3. **Commit:** re-read and verify the persisted owner and exact selected scope
   immediately before the governed write; require the matching scope-bound
   confirmation token. Any mismatch, stale token, or changed owner fails before
   commit effects. No A-prepare/B-commit sequence may write foreign content or
   leave a partial WorkingCopy/revision.

Tests must exercise the route/service boundary and prove both rejection and
absence of persistence effects, not only a pure token helper.

### Ordinary UI and promotion

Give the existing World picker a name-only New World entry. Reuse accepted
name-idempotent world creation and selected-World navigation; do not submit a
Build source to obtain a World. Select its returned exact ID and open Plan.
No WorkObject is silently created by route entry: blank remains local until
explicit Save or the existing intentional create control.

Managed World local/durable descriptors and recovery keys carry typed World
scope, disjoint from legacy campaign keys. The World promotion journal uses
`dmb_plan_promotion_recovery_v2`, with explicit scope and retained document ID;
existing campaign V1 journals remain unchanged and are never implicitly adopted.
Do not pass World ID as campaignId,
invent a target session, or adopt old recovery journals by text equality.
Use a friendly blank-Plan title; do not label the local draft as a missing active
document. Preserve ordinary editing, registered-component Markdown round-trip,
tools and explicit first-Save promotion; scope-unavailable dependent tools are
truthful, never redirected to legacy C1/C2 authority.

Retain the create/activation/save epochs and exact document/version checks from
existing blank-authoring machinery. A known successful create followed by a
failed load/commit retains that UUID; never clear it simply to retry a fresh POST.
Preserve source-independent local edits across A→B→A. This contract does not
invent durable create idempotency for an unknown/lost POST outcome: if existing
recovery cannot safely prove/reconcile that outcome, stop/re-brief, not blind retry.
The server-side prepare/commit rule above is mandatory alongside these UI
epochs: client-side generation checks alone cannot prevent a prepared World-A
write from being committed under World B.

Commit points remain World-container creation, then explicit Content WorkObject
creation, then existing governed Content save. Partial results stay truthful.
No one cross-domain transaction or automatic knowledge publication is promised.

## §7 Evidence required before merge

1. Domain/SQL: fresh World Plan has exact World and null campaign/session; invalid
   kind/missing World/blank scope/mixed scope rejected; ownership cannot be patched.
   Old campaign Plan/Runbook bytes and semantics remain readable and writable.
2. Migration: seed campaign WorkObject/revisions/copy using previous accepted
   schema, upgrade, compare exact identity/content; create/save/reopen World Plan
   on real disposable PostgreSQL. Re-run migration; no scope rewrite/data loss.
3. Route: managed World registry checked; create/get/list/snapshot/commit exact
   scope. Cross-World/campaign document and incompatible V1 body fail before save.
   Prepare rejects A under selected B before any WorkingCopy/revision effects;
   a confirmation token bound to A/document/revision/content cannot commit as
   B/document, and commit rechecks stored ownership before governed effects.
   Assert persistent state is unchanged after each rejected sequence.
4. Mounted UI: bare graphless World → edit → first Save → reload; partial create
   success plus activation/commit failure recovers same UUID; wrong-scope fixture
   is quarantined; A→B pending-save races do not activate/overwrite B. Same-text
   campaign/World keys remain distinct. No default-C2/session1 request emitted.
5. Required ordinary browser witness on exact review head: name-only New World
   → Plan before any source → author prose + one registered Read Aloud block
   → Save → reload → restart owned API → reopen same UUID/content/scope.
   Repeat selection with World B and show isolated inventory. Public reads prove
   zero source/campaign/head prerequisite, actual World/null-campaign Content
   ownership; no SQL/console/ID repair. Graph-dependent tools may be unavailable.
6. Focused full cohorts, scoped Ruff, frontend build/typecheck, cumulative/local
   `git diff --check` and actual changed paths versus §4. Inherited JSX failure
   requires exact unchanged base/head hash; no broader waiver or filtered-green
   fixture cohort. Normal API witness must not rely on a sandbox TestClient stall.

Required focused commands, with new World-Plan route cases in the named new
`tests/test_world_owned_plan_contract.py` module:

```bash
uv run --frozen pytest -q tests/test_world_owned_plan_contract.py tests/test_workspace_document_registry.py tests/test_selected_world_plan_context.py tests/test_live_plan_view_projection.py tests/test_tiptap_markdown_write.py tests/test_live_tiptap_markdown_write.py tests/application_state/test_plan_work_object_postgres.py
uv run --frozen ruff check src/application_state/content apps/live_control_server/services/workspace_document_registry.py apps/live_control_server/services/tiptap_markdown_write.py apps/live_control_server/routes/workspace_documents.py apps/live_control_server/routes/live.py tests/test_world_owned_plan_contract.py
```

From `apps/live-control-ui/`:

```bash
npm test -- --run src/selectedWorld/WorldSelector.test.tsx src/selectedWorld/WorldCreateControl.test.tsx src/selectedWorld/worldSelectionNavigation.test.ts src/workspaceDocument/workspaceDocumentCreation.test.ts src/api/liveApi.test.ts src/planSurface/PlanSurfacePage.test.tsx src/planSurface/PlanSurfaceShell.test.tsx src/planSurface/planBlankAuthoringState.test.ts src/planSurface/config/planSessionDescriptor.test.ts src/planSurface/config/planSurfaceConfig.test.ts src/planSurface/components/PlanDocumentCreateControl.test.tsx src/planSurface/components/PlanDocumentSelector.test.tsx
npx tsc --noEmit
npm run build
```

Include paired tests for all additionally modified save/authoring paths. Real
PostgreSQL must be reachable with the explicitly designated disposable pair and
current migration; no skipped PG test counts as proof. Record exact commands,
base/head, environment and outputs; no helper-only substitute. Finally run
`git diff --check` and `git diff --name-only <dispatch-base>...HEAD`.
MIND native-head success, Agent knowledge retrieval and full DEMO remain unproved.

## §8 Review handback

Record exact base/head, review cycle, actual paths/lease exceptions, named runtime
and dependency pins, migrations applied, required versus produced owning evidence,
full test counts/exclusions, failure/partial-result recovery, legacy regressions,
new wire fixture, predecessor sync and outstanding downstream gaps. PRIME judges
the complete cumulative invariant; task completion is not approval or a cycle.

## §9 Acceptance rubric

- [ ] PRIME activation and exact dispatch base recorded; the handoff's ACTIVE
      status is carried in this authorized implementation PR rather than a
      separate status-only PR.
- [ ] Serial topology/one assigned PR and lease honored.
- [ ] Name-only World creation enters blank Plan before any source/campaign/head.
- [ ] Content and every exposed ownership boundary prove exact World/null campaign.
- [ ] Explicit first Save, CAS, reload/restart and partial failure recovery proved.
- [ ] Wrong-scope/superseded results cannot mount, save or overwrite another scope.
- [ ] Campaign Plan/Runbook and historical data preserved; no inferred migration.
- [ ] Independent exact-head review and ordinary product witness complete.
- [ ] No native knowledge, source admission, Agent/Run or full DEMO acceptance claim.

## Stop conditions

BLOCKED/false gate; second implementation PR; conflicting active lease; required
generic kernel/provider/ontology change; new create-recovery/public contract not
described above; required unleased path; evidence only at a helper boundary;
unsafe migration/runtime collision; silent campaign/World coercion; loss of
legacy records; or a requirement to seed a graph/import material just to author.
Report affected invariant/path/owner, missing evidence and proposed re-brief
before editing outside the bounded contract.
