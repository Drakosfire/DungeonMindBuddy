# HANDOFF — PR #412 / PR380A World Graph recap projection contract

**Created:** 2026-07-25, America/Denver  
**Status:** ACTIVE — dispatch exactly one reconstitution capability from PR #380.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr412-world-graph-recap-projection-contract.md`  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Implementation base:** `0165d5e16efbc561e86fa942e3827ca78058fc18`  
**Suggested branch:** `agent/pr412-pr380a-world-graph-recap-projection`  
**Planned PR number:** `#412` (next free after open `#411` BLD-10a). If GitHub assigns a different number, rename this handoff/branch to match and continue — do not stop.  
**Source branch for selective reconstruction:** PR #380, head `8a60fe33efff4a8925eb741275d8fd70302cd863`  
**Roadmap anchor:** `Docs/Roadmaps/ROADMAP-cross-surface-statblock-demo.md` — `DEMO-00` and the read-contract foundation of `DEMO-01`  
**Product anchor:** GitHub issue #410 — Cross-surface World Graph + hoisted agent continuity demo  
**Operating mode:** reconstruct from current `main`; do not merge or cherry-pick PR #380 wholesale.

---

## §0 Capability decomposition decision

PR #380 is a 101-file integration branch containing multiple independently useful and independently revertible outcomes. This handoff reconstitutes only the first backend contract needed by the merge road.

| Candidate outcome | Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision |
|---|---:|---:|---:|---:|---:|---|
| Revision-pinned World Graph → recap-shaped read API | Yes | Yes — new response/route contract | No product UI yet | Yes | Yes | **Include** |
| Deterministic recap prose mentions using exact projected node IDs | No alone; required by the read API | Yes — response semantics | No | Yes | Yes | **Include under the same invariant** |
| Exact snapshot/trust metadata in the recap response | No alone; required to make the read API trustworthy | Yes | No | Yes | Yes | **Include under the same invariant** |
| Recap/Graph Review React consumer migration | Yes | Yes — frontend API/types and product behavior | Yes | Yes | Yes | Successor `PR380B` |
| Shared `GraphObjectCard` open/navigation path | Yes | Yes — shared UI interaction contract | Yes | Yes | Yes | Successor `PR380B` |
| Graph Review post-confirm authority transition | Yes | Yes — lifecycle UI contract | Yes | Yes | Yes | Successor `PR380C` |
| Projection cache, request coalescing, invalidation, telemetry | Yes | Yes — runtime coordination/observability | Indirectly | Yes | Yes | Successor `PR380D` / roadmap `DEMO-01` completion |
| Ingest primary-path simplification | Yes | No backend graph contract; product workflow changes | Yes | Yes | Yes | Successor `PR380E` |
| Extraction and identity hardening | Yes | Yes | No direct Recap consumer required | Yes | Yes | Successor `PR380F` |
| Session-specific graph repair scripts | Yes operationally | Yes — governed historical correction | No normal UI | Yes | Yes | Successor `PR380G`; outside demo critical path |
| Campaign-scope request widened to world scope to recover standing PCs | Yes but changes tenancy/scope semantics | Yes | Indirectly | Yes | Yes | **Reject from this slice** |
| Known-entity registry stubs inserted into the projection | Yes but invents a second node source | Yes | Indirectly | Yes | Yes | **Reject from this slice** |
| Heuristic thread aliases derived from recap prose | Yes but creates mention/identity semantics | Yes | Indirectly | Yes | Yes | **Reject from this slice** |
| Synthetic `member_of` adjacency or focus-session stamps | Yes but invents graph relationships/session support | Yes | Indirectly | Yes | Yes | **Reject from this slice** |

**Selected capability:** a caller can request a focus-session recap read model derived from one exact World Graph snapshot and one canonical normalized recap source, with durable node-linked mentions and explicit trust metadata, without consulting latest-ingest or preview-union state.

**Why included rows share one invariant:** the route, response schema, source read, mention projection, node-view adaptation, and tests all establish one claim: every graph-shaped field and clickable graph mention in the recap response comes from the exact returned World Graph snapshot, while the recap prose comes from the exact requested canonical source identity.

**Named successors:**

1. `PR380B` — Recap/Ingest UI migration plus shared graph-object navigation.
2. `PR380C` — post-confirm Graph Review authority transition.
3. `PR380D` — app/server projection cache, invalidation, and telemetry.
4. `PR380E` — Ingest primary-path simplification.
5. `PR380F` — extraction/identity hardening.
6. `PR380G` — governed historical repairs and benchmark cleanup.
7. Roadmap `DEMO-02` — persistent agent context and cross-surface thread continuity.

---

## §1 Mission

Recap and Graph Review consumers can request a focus-session recap projection from one exact World Graph revision and canonical normalized recap, so later UI slices can replace latest-ingest and preview-union reads without losing durable object identity or overstating evidence.

### Invariant

> Every node view, relationship, focus marker, and `dmb-node:` mention returned by this endpoint resolves to the exact World Graph snapshot named in the response; the adapter may reshape existing graph facts for recap presentation but must not invent nodes, aliases, edges, session membership, evidence binding, or authority.

### Mission falsification test

```text
This is not one slice if implementation must also:
- migrate the React Recap or Ingest consumer;
- open GraphObjectCard or add shared card actions;
- change Graph Review prepare/confirm behavior;
- add cache, telemetry, or warm-load policy;
- widen campaign scope to world scope;
- supplement the graph from a party/known-entity registry;
- infer aliases or relationships from prose;
- bind source spans/evidence not already available through an authoritative contract;
- change extraction, identity resolution, graph publication, or historical data.
```

---

## §2 Context, authority, and boundaries

### Parent authority

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
3. `Docs/Roadmaps/ROADMAP-cross-surface-statblock-demo.md`
4. GitHub issue #410
5. `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`
6. This handoff
7. Current implementation and owning-boundary tests on base `0165d5e`
8. PR #380 as source material only

### Repository rules

- `AGENTS.md`
- `.cursor/rules/external-agent-pr-loop.mdc`
- `.cursor/skills/external-agent-pr-loop/SKILL.md`
- `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`
- graph Kernel boundary tests and public import rules

### Authority precedence

```text
1. Campaign Supergraph architecture and active tracker
2. Cross-Surface Statblock Demo roadmap and issue #410 product invariant
3. This checked-in handoff
4. Current main implementation and tests
5. PR #380 patch as selective reconstruction source
6. Attached/local Project Sources
7. Chat summaries
```

PR #380 is not implementation authority. Its useful code may be adapted, but behavior conflicting with this handoff must be deleted or not reconstructed.

### Exact predecessor contracts consumed

**WorldGraphProjectionRequest** (`dmb_world_graph_projection_request_v1`)

```text
schema
world_id
campaign_id
focus:
  kind: none | session
  session_id?
  campaign_id?
admissibility
revision_pin?
query_text?
scope_mode: campaign | world
```

**WorldGraphProjection** (`dmb_world_graph_projection_v1`)

```text
snapshot:
  world_id
  campaign_id
  revision_id
  head_revision_id
  is_head
  focus
  admissibility
  scope_mode
summary
nodes[]
relationships[]
attributes[]
evidence[]
source_artifacts[]
query_context?
diagnostics[]
trust_boundary
```

**Recap presentation vocabulary**

```text
campaign_id
session_id
graph_id
markdown
focus
node_views
mentions
source_spans
```

The new response may reuse these existing recap presentation fields, but it must add an explicit versioned schema and exact World Graph snapshot identity rather than relying on `graph_id` alone.

### Exact input consumed

```text
1. One validated WorldGraphProjectionRequest constrained by this endpoint.
2. One exact World Graph projection returned by the Kernel/service for that request.
3. One canonical normalized recap body for the requested campaign/session.
```

### Request restrictions for v1

- `focus.kind` must equal `session`.
- `focus.session_id` is required.
- `focus.campaign_id`, when present, must equal top-level `campaign_id`.
- `scope_mode` must equal `campaign`.
- `query_text` must be absent/null; a recap projection is not a search-result projection.
- `revision_pin` remains optional and follows the generic World Graph projection contract.
- `admissibility` is passed through unchanged to the generic projection contract.
- Query parameters and unknown body fields remain rejected.

### Named successor

`PR380B` consumes the route in React and proves that Recap/Ingest open the same durable node through the shared object-card path. This slice does not change a normal product screen.

### What remains false after this slice

- Recap View still has not been migrated off its current selector.
- Ingest still has not been migrated off its current selector.
- No shared card opens from recap prose.
- No Graph Review post-confirm authority flip exists on `main` because of this slice.
- No projection request cache, warm load, invalidation event, or load telemetry exists because of this slice.
- No node can be pinned into Agent Interaction from the recap.
- No cross-surface conversation continuity is delivered.
- Missing standing PCs remain missing when they are absent from the requested campaign projection.
- Low chip coverage remains visible rather than being “fixed” through heuristic aliases.
- `source_spans` remain empty unless an existing exact source-span contract can be consumed without new authority semantics.

### Base movement rule

The handoff is based on `0165d5e16efbc561e86fa942e3827ca78058fc18`. Before implementation:

1. resolve current `main` with `git rev-parse HEAD`;
2. compare current `main` to this base;
3. specifically inspect active Build/statblock merges for changes to:
   - `apps/live_control_server/routes/world_graph_projection.py`;
   - `apps/live_control_server/services/world_graph_projection.py`;
   - `apps/live_control_server/services/union_supergraph_projection_adapter.py`;
   - `src/graph_memory/projection/*`;
   - relevant tests.

If the generic projection request/response or recap source loader changed materially, stop and report the re-anchor consequence before editing.

---

## §3 Observable-path inventory

| Observable path | Current behavior on `main` | Required behavior after this slice | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Valid campaign/session request, head policy, world head and recap present | Only generic World Graph projection exists; no recap-shaped World Graph route | Return versioned recap projection with exact head snapshot, canonical recap prose, exact adapted node views, and deterministic mentions | Yes | service + route |
| Valid request with `revision_pin` to non-head revision | Generic route supports revision pin; no recap route | Return recap projection from exactly the pinned revision and report `is_head=false` plus current `head_revision_id` | Yes | Kernel/service + route |
| `focus.kind=none` or missing session ID | No recap route | Stable 422 `invalid_request`; no inferred session and no latest fallback | Yes | request validation/service |
| `focus.campaign_id` disagrees with top-level campaign | Generic contract can represent both fields | Stable 422; no cross-campaign reinterpretation | Yes | service |
| `scope_mode=world` | Generic projection supports it | Stable 422 for recap v1; no incidental world-union product decision | Yes | service |
| `query_text` provided | Generic projection supports bounded search | Stable 422; recap v1 cannot silently chip a filtered graph subset | Yes | service |
| World head or pinned revision missing | Generic service returns stable projection error | Preserve stable Kernel/service error; no preview union, ingest run, fixture, or registry fallback | Yes | Kernel/service + route |
| Canonical normalized recap absent | Existing private loader returns no content | Stable 404 `recap_markdown_unavailable`; no manifest/latest-ingest/unnormalized fallback | Yes | source reader + service |
| Canonical recap identity ambiguous | Existing loader may choose a filename candidate | Fail closed with stable `recap_source_ambiguous`; never first-file wins | Yes | source reader + service |
| Canonical recap unreadable or invalid UTF-8 | Unspecified | Stable internal/source-read error with no partial response | Yes | source reader + service |
| Exact unique projected label appears in prose | No World Graph recap mention path on `main` | Replace the text span with `dmb-node:<exact node_id>` and emit a mention record | Yes | pure projection helper |
| Exact unique explicit alias appears in prose | No World Graph recap mention path on `main` | Same as label; aliases come only from the returned projection | Yes | pure projection helper |
| Same case-insensitive surface belongs to multiple projected nodes | Unspecified | Do not chip; preserve prose; emit bounded `ambiguous_mention_surface` diagnostic | Yes | pure projection helper |
| Longer and shorter unique surfaces overlap | Unspecified | Longest valid surface wins deterministically; no nested/overlapping chips | Yes | pure projection helper |
| Surface appears inside an existing Markdown link or `dmb-node:` link | Unspecified | Preserve existing link syntax; do not nest or retarget it | Yes | pure projection helper |
| Surface appears inside inline/fenced code | Unspecified | Preserve code text; do not create a graph link inside code | Yes | pure projection helper |
| Node is absent because of campaign scope or admissibility | PR #380 attempted registry/world-scope supplementation | Prose remains plain; response does not synthesize or retrieve from another scope | Yes | service + mention helper |
| Node has graph relationships/session IDs | Generic projection provides exact state | Adapt exact relationship fields and focus flags only; no added IDs, edges, session stamps, or party membership | Yes | adapter |
| Mention text matches a node but no source-span contract binds that occurrence | PR #380 attached node evidence IDs to mention and returned empty source spans | Mention is navigation-only: no mention-level evidence refs; `source_spans=[]`; trust boundary states highlight/evidence binding is unavailable | Yes | response model + service |
| Query parameters or extra body fields | Generic route rejects | Recap route uses the same stable 422 error envelope | Yes | route |
| Same request replayed against same revision/source bytes | No recap route | Deterministic equivalent response; no writes | Yes | service/serialization |
| Head advances and request has no pin | No recap route | A later request resolves the new head; no cache in this slice | Yes | generic projection service |

A row marked required is merge-blocking. Poor mention coverage caused by insufficient durable aliases is an honest product result, not authorization to infer aliases in this slice.

---

## §4 Files in scope — allowlist

Every changed path must appear below or be admitted by the bounded discovery exception.

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-pr412-world-graph-recap-projection-contract.md` | Canonical dispatch authority for PR #412 / PR380A |
| Create | `src/graph_memory/projection/world_recap_projection.py` | Own the versioned recap response schema, trust boundary, mention diagnostic vocabulary, and pure deterministic node/mention adaptation contract |
| Modify | `src/graph_memory/projection/__init__.py` | Export only the new public projection models/helpers required by service/tests, if repository style requires it |
| Create | `apps/live_control_server/services/world_graph_recap_projection.py` | Validate recap-specific request constraints, call the generic World Graph service exactly once, read the canonical recap, adapt exact graph state, and produce the response |
| Modify | `apps/live_control_server/routes/world_graph_projection.py` | Add `POST /api/live/world-graph/recap-projection` using existing validation/error-envelope behavior |
| Modify | `apps/live_control_server/services/union_supergraph_projection_adapter.py` | Expose the existing normalized-recap body loader as a public helper while retaining the private alias for current callers; no telemetry or legacy behavior changes |
| Create | `tests/test_world_graph_recap_projection.py` | Service, pure mention/adaptation, identity, fail-closed, pinned-revision, and route tests for this capability |
| Modify | `tests/test_world_graph_projection_routes.py` | Add only route-shared regression coverage when it cannot be owned cleanly by the new focused test file |
| Modify | `tests/test_graph_kernel_boundaries.py` | Only when required to prove the new service uses the public Kernel/projection boundary and introduces no latest-ingest/preview-union selector |

### Bounded discovery exception

```text
Directory: src/graph_memory/projection/ and apps/live_control_server/services/
Maximum additional paths: 3
Allowed path kinds:
  - one existing public model/export module that must change to represent the exact response contract;
  - one existing normalized recap path/identity helper required to fail closed on ambiguous canonical source identity;
  - one focused test file owning that exact existing helper.
Decision rule for including a path:
  include only when the path directly validates, serializes, reads, adapts, or proves the §1 recap read invariant.
Required report when a path is added:
  name the path, why an allowlisted path could not own the guarantee, the public contract consequence, and whether a successor split is now required.
```

No UI, cache, telemetry, extraction, repair, benchmark, or graph-publication path is admitted by this exception.

---

## §5 Files and capabilities explicitly out of scope

| Path, ownership layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/**` | React consumption, shared cards, caching, and route continuity are successor capabilities |
| `apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx` | `PR380B` owns consumer migration and demolition of latest-ingest selection |
| `apps/live-control-ui/src/planSurface/graphProjectionReader/**` | Shared open/card behavior is `PR380B` |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/**` | Authority transition is `PR380C` |
| `apps/live-control-ui/src/planSurface/reference/projectionRequestCache*` | Cache/coalescing/invalidation is `PR380D` |
| `src/graph_memory/world_projection_cache.py` | Server cache is `PR380D`; do not hide correctness under caching in the first contract slice |
| `src/graph_memory/projection_load_telemetry.py` and benchmark artifacts | Telemetry/benchmarking is `PR380D` |
| `apps/live_control_server/services/extract_promote.py` | Graph Review writes and post-confirm behavior are separate |
| `apps/live_control_server/services/graph_ingest_run_registry.py` | Latest/exact run selection is not a recap World Graph read source |
| `apps/live_control_server/routes/recap_ingest.py` | Ingest workflow is `PR380E` |
| `src/graph_memory/extraction/**` | Extraction/identity hardening is `PR380F` |
| `src/graph_memory/identity_resolution.py` and `extract_identity_gate.py` | Same as above |
| `scripts/supersede_*` and repair tests | Historical repair is `PR380G` |
| `evals/graph_memory_layer/artifacts/projection_load_benchmark/**` | Large benchmark artifacts are not needed to prove the contract |
| Plan default `scope_mode=world` | Separate product decision; recap v1 is campaign-scoped |
| Known entity/party registry reads | Would introduce a second source of node identity and graph-shaped state |
| Synthetic focus/session/relationship enrichment | Would invent facts not present in the exact graph snapshot |
| Source-span generation or evidence highlighting | Requires a separate authoritative source-span binding contract |
| Agent Interaction or “Use as context” | Roadmap `DEMO-02`, after shared object consumption exists |
| Statblock/ThreatDraft code | This slice only lays the graph read foundation for the later statblock demo |

Nearby code in PR #380 is not authorization.

---

## §6 Implementation contract and conditional matrices

### Public request and response

```text
Input:
  WorldGraphProjectionRequest v1
  constrained to:
    focus.kind=session
    focus.session_id present
    focus.campaign_id absent or equal to campaign_id
    scope_mode=campaign
    query_text absent/null

Output:
  WorldGraphRecapProjection v1
    schema
    campaign_id
    session_id
    graph_id                  // exact alias of snapshot.revision_id for recap compatibility
    snapshot                  // exact WorldGraphProjectionSnapshot
    markdown                  // canonical recap body with deterministic navigation-only chips
    focus                     // derived only from exact returned projection data
    node_views                // exact adapted world node views keyed by durable node ID
    mentions                  // exact text ranges and durable node IDs; no evidence claim
    source_spans=[]           // explicit in v1 unless authoritative spans already exist
    diagnostics               // bounded mention/source diagnostics
    trust_boundary

Invariant:
  Every graph-shaped output and mention target is traceable to snapshot.

Failure behavior:
  invalid recap request -> 422 stable projection error envelope
  world/revision missing or denied -> preserve generic projection service error
  recap absent -> 404 recap_markdown_unavailable
  recap identity ambiguous -> fail closed recap_source_ambiguous
  recap read/integrity failure -> stable non-200 response; no partial payload
  ambiguous mention surface -> successful payload, unchanged prose for that surface, bounded diagnostic

Replay / idempotency:
  same request + same graph revision + same recap bytes -> deterministic equivalent response
  changed head with no revision pin -> next request may return the new head
  exact revision pin -> remains exact and reports non-head when appropriate
  retry after read failure -> safe; no durable mutation occurred
  duplicate request -> safe; no side effect

Trust boundary:
  Verifies:
    request constraints;
    exact graph snapshot identity;
    durable node IDs present in the returned projection;
    exact canonical recap source selection;
    unique deterministic mention surfaces;
    response schema.
  Records or trusts without proving:
    semantic completeness of graph labels/aliases;
    whether a text mention is evidentiary support for every node assertion;
    whether missing nodes should exist in another campaign/world scope.
  Rejects:
    latest-ingest/run/manifest selectors;
    preview-union stores;
    registry node supplementation;
    label-first ambiguous identity;
    inferred aliases or relationships;
    copied source-span/evidence authority;
    query-filtered recap projections.
```

### Commit point

```text
Not applicable — this capability is read-only and creates no graph, corpus, registry, cache, or UI persistence.
```

### §6A State and fallback matrix

| Observable path | Loading or initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity or contract failure | Stale or superseded | Retry or replay |
|---|---|---|---|---|---|---|---|
| Request validation | Parse strict request | Admitted to service | N/A | N/A | 422 stable error | N/A | Safe |
| World Graph projection | Open requested head/revision | Exact snapshot returned | Missing world/revision follows generic stable error | Generic service error | Fail closed | Revision pin remains exact; unpinned request uses current head | Safe |
| Canonical recap source | Resolve exact campaign/session normalized recap | Body returned | 404 | Stable source-read error | Ambiguous identity/read integrity fails closed | Source is read per request; no cache in this slice | Safe |
| Mention projection | Scan eligible Markdown text against exact labels/aliases | Unique surfaces become durable links | No surface = unchanged prose | N/A | Ambiguity = unchanged prose + diagnostic | New revision/source bytes recompute | Deterministic |
| Node view adaptation | Adapt exact returned node | Exact fields preserved | Missing node cannot be targeted | N/A | Schema mismatch fails | Pinned revision stays exact | Deterministic |
| Route serialization | Serialize v1 schema in camelCase | 200 exact payload | N/A | N/A | Stable non-200 envelope | Snapshot says whether head | Safe |

**Permitted fallback sources:** none.

The route must not consult:

- latest graph ingest;
- GraphIngestRun registry;
- preview union store;
- default fixtures;
- known-entity registry;
- corpus index search;
- world-scope retry;
- arbitrary Markdown paths.

### §6B Identity matrix

| Situation | Required matching rule | Ambiguity behavior | Fallback permitted? | Persistence consequence |
|---|---|---|---|---|
| Exact graph node | Exact `node_id` from returned World Graph projection | Missing remains unresolved | No | Response reference remains tied to returned revision |
| Label mention | Case-insensitive exact surface match to one projected node label, outside protected Markdown/code ranges | Multiple node IDs = no chip + diagnostic | No | None; response is derived |
| Explicit alias mention | Same as label; alias must already be in the projected node | Multiple node IDs = no chip + diagnostic | No | None |
| Overlapping surfaces | Longest unique eligible span wins; no overlap/nesting | Equal/ambiguous ownership remains unlinked | No | None |
| Normalized key or slug | Prohibited for mention resolution | N/A | No | None |
| Existing `dmb-node:` link | Preserve exact existing syntax; do not rebind | Invalid existing link is not repaired here | No | None |
| Rename in a later revision | New projection labels/aliases apply only to that revision | Old prose may no longer chip | No hidden compatibility alias | Node ID remains graph-owned |
| Node deletion/retraction | Node absent at that revision cannot be a new mention target | Plain prose | No | Prior responses remain historical derived output only |
| Campaign/world collision | Campaign-scoped projection determines candidates | No world-scope retry | No | None |
| Admissibility denial | Denied/omitted node cannot be mentioned | Plain prose | No | None |

First-win alias matching is prohibited.

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate or replay behavior | Compatibility or migration | Rollback or reversion |
|---|---|---|---|---|---|
| Read unpinned head | None created; response names exact snapshot | Response fields serialize/parse exactly | Safe repeat; may observe a later head | New response schema v1 only | Revert route/schema PR |
| Read pinned revision | None created | Exact `revision_id`, `head_revision_id`, `is_head` retained | Deterministic for same graph/source bytes | No “latest” compatibility mode | Revert route/schema PR |
| Read canonical recap | Existing corpus Markdown remains authority | Body is not written or normalized again | Safe repeat | No source migration | N/A |
| Project mentions | Derived response only | Mention node IDs and offsets survive response serialization | Deterministic | No stored-link migration | N/A |

No cache or persisted derived payload is introduced.

### §6D Predecessor-to-consumer mapping

**Grounding source**

```text
- graph_memory.projection.world_projection.WorldGraphProjectionRequest
- graph_memory.projection.world_projection.WorldGraphProjection
- graph_memory.projection.recap_projection recap presentation models
- apps.live_control_server.services.world_graph_projection.project_world_graph
- current canonical normalized-recap path rules
```

| Predecessor field or outcome | Real shape and optionality | Consumer field or behavior | Transformation | Proof fixture or test |
|---|---|---|---|---|
| `request.world_id` | required string | generic projection request + response snapshot | exact pass-through | service/route test |
| `request.campaign_id` | required string | source selection and snapshot campaign | exact; focus campaign must agree | mismatch negative test |
| `request.focus` | `none` or `session` | recap `session_id` and focus overlay | require session; exact session ID | request matrix tests |
| `request.revision_pin` | optional string | exact snapshot | exact pass-through | pinned non-head test |
| `request.admissibility` | string | exact snapshot and filtering | exact pass-through | admissibility test or generic regression |
| `request.scope_mode` | campaign/world | recap v1 admission | require campaign | negative test |
| `request.query_text` | optional string | recap v1 admission | require absent/null | negative test |
| `projection.snapshot` | exact typed object | `snapshot`; `graph_id=revision_id` | exact serialization; no reconstruction | schema/route test |
| `projection.nodes[].node_id` | durable string | `node_views` key and mention target | exact | node/mention tests |
| node label/kind/role/aliases/source domains/summary/campaign scope | typed fields, some optional | recap node view | exact field adaptation | field-mapping test |
| node evidence badges | list | recap node view badges | exact fields only | adaptation test |
| node adjacency | list with `inbound/outbound` direction vocabulary | recap node adjacency | vocabulary-only direction map when required by existing recap model; all IDs/session/evidence fields exact | adaptation test |
| suggested expansions | list | recap suggested expansions | exact plus required direction vocabulary map | adaptation test |
| projection evidence `session_id` | optional | focus evidence IDs | include only exact focus-session matches | focus test |
| projection relationships `session_ids` | list | focus edge IDs | include only exact focus-session membership | focus test |
| node `anchored_to_focus_session` | bool | focus node IDs | exact | focus test |
| canonical recap body | string or missing | `markdown` | preserve body except inserted navigation links | source/mention tests |
| unique label/alias match | text range | mention record + Markdown link | longest-first, protected-range aware | pure helper tests |
| ambiguous label/alias match | multiple node IDs | unchanged text + diagnostic | no first-win | ambiguity test |
| no authoritative span binding | absent | `source_spans=[]`; mention evidence empty | explicit trust limitation | response trust test |
| generic projection error | stable error schema/code/status | recap route error | preserve envelope/status | route negative tests |

### Response trust boundary minimum

The response must make these claims machine-readable:

```text
can_trust:
  - snapshot identifies the exact graph read
  - node_views and graph mention targets come from that snapshot
  - markdown body comes from the requested canonical normalized recap
  - graph_id equals snapshot.revision_id

cannot_trust:
  - mention spans are evidence bindings
  - source highlighting is available
  - absent nodes were searched in other campaigns or world scope
  - label/alias coverage is semantically complete
  - recap prose has been promoted merely because it is displayed beside graph nodes
```

---

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command or manual scenario | Expected evidence |
|---|---|---|---|
| Strict v1 response schema and camelCase route payload | model + HTTP route | focused schema/route tests | schema ID, exact snapshot fields, no snake_case leakage |
| Exact pinned revision | Kernel/service/route integration | initialized world fixture with a non-head revision pin | response revision equals pin; `isHead=false`; head remains current |
| No latest-ingest/preview fallback | service boundary + static boundary test | monkeypatch forbidden selectors to fail if called; boundary scan | valid route never calls them; miss remains non-200 |
| Campaign scope is not widened | service integration | spy generic projection call | exactly one call with `scope_mode=campaign` |
| Missing graph fails closed | route integration | empty temporary graph root | stable generic error; no fixture/run fallback |
| Missing recap fails closed | source reader/service | initialized graph + missing canonical recap | 404 `recap_markdown_unavailable` |
| Ambiguous recap source fails closed | source reader | two canonical candidates fixture/temp tree | stable `recap_source_ambiguous` |
| Unique label/alias produces exact durable link | pure helper | focused unit tests | exact `dmb-node:<node_id>` and mention offsets |
| Ambiguous alias does not first-win | pure helper | focused unit test | unchanged prose + diagnostic |
| Markdown/code protected regions remain untouched | pure helper | inline link, dmb-node link, inline/fenced code tests | no nested or code links |
| No synthetic graph state | adaptation/service tests | projection fixture with absent PC/edge/session | no registry node, no synthetic edge, no added session ID |
| Mention does not claim evidence binding | response model/service | focused test | mention evidence empty, source spans empty, trust boundary explicit |
| Generic projection route remains unchanged | existing route tests | current projection route suite | all existing tests pass |
| Kernel import boundary remains intact | boundary test | graph Kernel boundary suite | no forbidden direct store/path selector imports |

### Required commands

```bash
uv run pytest \
  tests/test_world_graph_recap_projection.py \
  tests/test_world_graph_projection_routes.py \
  tests/test_graph_kernel_boundaries.py \
  -q

uv run pytest \
  tests/test_graph_kernel_world_projection.py \
  tests/test_graph_kernel_world_retrieval.py \
  -q

uv run ruff check \
  src/graph_memory/projection/world_recap_projection.py \
  apps/live_control_server/services/world_graph_recap_projection.py \
  apps/live_control_server/routes/world_graph_projection.py \
  apps/live_control_server/services/union_supergraph_projection_adapter.py \
  tests/test_world_graph_recap_projection.py \
  tests/test_world_graph_projection_routes.py

git diff --check

git diff --stat 0165d5e16efbc561e86fa942e3827ca78058fc18...HEAD -- \
  Docs/Plans/HANDOFF-pr412-world-graph-recap-projection-contract.md \
  src/graph_memory/projection/world_recap_projection.py \
  src/graph_memory/projection/__init__.py \
  apps/live_control_server/services/world_graph_recap_projection.py \
  apps/live_control_server/routes/world_graph_projection.py \
  apps/live_control_server/services/union_supergraph_projection_adapter.py \
  tests/test_world_graph_recap_projection.py \
  tests/test_world_graph_projection_routes.py \
  tests/test_graph_kernel_boundaries.py

git diff --name-only 0165d5e16efbc561e86fa942e3827ca78058fc18...HEAD
```

If `tests/test_graph_kernel_world_retrieval.py` does not exist at the implementation base, report that exact fact and run the current owning retrieval test file identified by SymDex; do not invent or silently omit the gate.

### Minimal live proof

```text
Existing surface used:
  Existing FastAPI live-control server; no new UI.

Smallest scenario:
  Start the server against an initialized local Eldyrwild World Graph and an existing canonical normalized recap.

Action:
  POST /api/live/world-graph/recap-projection with campaign scope and focus session.

Expected observation:
  200 response names the exact World Graph snapshot, contains canonical recap body with at least one durable node link when a unique projected surface exists, and contains no latest-ingest/run/preview selectors.

Negative observation:
  Repeat with a missing recap session and receive the stable 404; repeat with scopeMode=world and receive 422.

Evidence captured:
  Request payload, response status/schema/snapshot, one mention target, and negative response envelopes in PR handback. No screenshot or new panel is required.
```

### Baseline failure protocol

For any required command failing on base:

| Command | Base result | Head result | New failure introduced? | Acceptance effect | Waiver |
|---|---|---|---:|---|---|
| `<command>` | record exact output | record exact output | Yes/No | blocked or explicit waiver | none unless operator grants |

The implementation agent must run the same command on base and head when practical. Author-reported, independently rerun, CI, and manual evidence must remain distinct. The repository currently has no general PR CI guarantee; local evidence must not be described as CI.

---

## §8 Required implementation handback

The PR body/handback must include:

1. Base SHA and head SHA.
2. Confirmation that work began from current `main`, not by merging/cherry-picking PR #380.
3. Actual changed paths.
4. Focused diff stat limited to §4 paths.
5. Exact response schema with one sample success payload and stable error payloads.
6. Every §7 command and exact result.
7. Evidence provenance: author-local, independently rerun local, CI, or manual.
8. Base/head comparison for any failing gate.
9. Explicit waivers; write `none` when none exist.
10. Paths outside §4; write `none` or provide a stop report.
11. Stop conditions encountered; write `none` when none exist.
12. Deviations from §6 matrices; write `none` when none exist.
13. A mapping from each PR #380 source fragment reused to its rewritten current-main destination.
14. Confirmation that these PR #380 behaviors were not reconstructed:
    - campaign→world scope widening;
    - known-entity registry stubs;
    - heuristic thread aliases;
    - synthetic focus/session membership;
    - mention-level evidence claims without source spans;
    - cache/telemetry;
    - UI migration.
15. Named successors and confirmation they remain false.
16. Confirmation that the complete handoff was followed without omitted constraints.

---

## §9 Acceptance rubric

The reviewer accepts only when every item is true.

- [ ] Exactly one independently useful capability was delivered: the recap-shaped World Graph read contract.
- [ ] The response names an exact versioned World Graph snapshot and `graph_id` agrees with its revision.
- [ ] Every returned node view and graph mention target exists in that exact snapshot.
- [ ] The request performs exactly one campaign-scoped generic World Graph projection call.
- [ ] `scope_mode=world`, `query_text`, missing session focus, and campaign mismatch fail with stable 422 behavior.
- [ ] Missing/ambiguous recap source fails closed with no latest/run/preview fallback.
- [ ] Mention matching is unique-only, deterministic, overlap-safe, and protected-range aware.
- [ ] Ambiguous surfaces never first-win.
- [ ] No registry node, inferred alias, synthetic edge, or synthetic session membership enters the response.
- [ ] Mentions are navigation-only; they do not claim source-span/evidence binding.
- [ ] Existing generic World Graph projection behavior remains green.
- [ ] Kernel boundaries remain intact.
- [ ] No UI, cache, telemetry, extraction, repair, or statblock file changed.
- [ ] No unexpected path changed.
- [ ] Baseline failures and evidence provenance are reported truthfully.
- [ ] `PR380B` and later successors remain unimplemented and unclaimed.
- [ ] The authoritative handoff survived dispatch without compression or omitted constraints.

---

## §10 Reviewer protocol

Review the invariant before individual code.

1. Verify the branch started from current `main`, not PR #380.
2. Compare the actual diff with the §4 allowlist.
3. Inspect the new response schema and exact snapshot fields.
4. Confirm recap request restrictions prevent world-scope and query-filtered behavior.
5. Trace the service call graph and prove there is one generic World Graph projection read.
6. Search for forbidden selectors and sources:
   - latest graph ingest;
   - graph run manifest/registry;
   - preview union store;
   - default fixture;
   - known-entity registry;
   - world-scope retry.
7. Audit label/alias ambiguity and protected Markdown/code regions.
8. Inspect every adapted field for invention or loss.
9. Confirm no source-span/evidence authority is implied.
10. Run route, service, pure-helper, Kernel, and boundary tests.
11. Compare base/head failures.
12. Confirm consumer migration and shared cards remain successors.

A large copy of the PR #380 service with a few methods deleted is not sufficient evidence of cleanup. The implementation should be the smallest current-main-native contract satisfying this handoff.

---

## §11 Re-review protocol

Begin each re-review from the prior finding ledger.

| Prior finding | Claimed fix | Owning files/tests | Verified? | New consequence? |
|---|---|---|---:|---|
| `<finding>` | `<resolution>` | `<paths>` | Yes/No | `<none or consequence>` |

For every fix:

1. verify the literal correction;
2. rerun the whole read invariant;
3. re-audit forbidden fallback sources;
4. recheck ambiguity behavior and protected ranges;
5. inspect whether the fix introduced new identity, evidence, cache, or source semantics;
6. update the ledger.

---

## Stop conditions

Stop and report rather than broadening the slice when implementation discovers:

- the generic projection cannot provide enough exact snapshot identity without changing its public contract;
- recap source identity cannot be selected uniquely without a new registry or persisted source contract;
- useful mention coverage requires inferred aliases, registry nodes, or world-scope widening;
- UI consumption is required to prove the backend contract;
- source highlighting requires creating a new source-span/evidence contract;
- a cache or telemetry layer is required for acceptable correctness rather than performance;
- the current main request/response schema differs materially from this handoff;
- a required path falls outside §4 and the bounded exception;
- active Build/statblock work introduces a conflicting API/type contract;
- a baseline failure requires operator waiver;
- (PR number collision is not a stop — rename handoff/branch to the opened number and continue.)

Use this report:

```text
Stop condition:
Why the current mission cannot absorb it:
New public/durable contract discovered:
Affected observable paths:
Affected ownership layers:
Required path outside scope:
Proposed successor slice:
Tracker or authority update needed:
Operator decision required:
```

The worker must not resolve a stop condition by silently adding a fallback, UI, registry, alias heuristic, synthetic graph fact, or second response authority.

---

## Final dispatch check

- [x] §0 decomposes PR #380 into independently useful outcomes.
- [x] §1 names one independently useful contract.
- [x] One invariant governs service, route, model, source read, adaptation, and tests.
- [x] §2 identifies immutable base and authority precedence.
- [x] §3 inventories success, miss, failure, ambiguity, pinning, and replay paths.
- [x] §4 provides an explicit allowlist and bounded discovery exception.
- [x] §5 excludes all successor capabilities and problematic PR #380 enrichment.
- [x] §6 defines request, response, identity, fallback, trust, and replay semantics.
- [x] §7 maps every guarantee to an owning-boundary proof.
- [x] Stop conditions and named successors are explicit.
- [x] The handoff advances roadmap `DEMO-00` and establishes the backend foundation for `DEMO-01` without recreating an omnibus PR.
