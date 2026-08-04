# STATBLOCK — HANDOFF: SBW10b exact Threat projection

**Created:** 2026-08-03  
**Status:** ACTIVE IMPLEMENTATION HANDOFF — documentation authority only  
**Flow / agent:** `STATBLOCK`  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw10b-exact-threat-projection.md`  
**Design base:** `b1479970aea69f47f678f35481125ebdfeabddd9` — merge of SBW10a  
**Predecessor:** merged SBW10a query/hydration, implementation head `16953ad21aa7ec923b70892307bf5244280f5382`  
**Suggested implementation branch:** `feat/statblock-sbw10b-exact-threat-projection`  
**Required implementation PR title prefix:** `statblock`  
**Planned PR number:** none — do not assign or predict one

> Turn one exact published World Graph Threat into one useful compact/full GM-facing Threat Sheet inside the shared Projection Host. Compose campaign identity and relationships with every exact SBW10a mechanics binding. Never substitute current head, label identity, first binding, latest mechanics, copied mechanics, or a generic authoring tool.

---

## §0 Capability decision

### Selected capability

A resolved published Threat opened from a graph reference renders as one composed **Threat Sheet projection**:

```text
exact graph snapshot + exact Threat node ID
→ SBW10a exact Threat query/hydration
→ exact node-ID match
→ compact or full derived Threat Sheet
→ identity + encounter meaning + relationships + every exact mechanics binding
```

This is one independently useful capability. It makes the already-published and already-queryable Threat usable to a GM without introducing another durable object or another mechanics authority.

### Included

- exact graph-snapshot scope on a resolved graph reference;
- exact selected Threat-node loading through the merged SBW10a endpoint;
- fail-closed exact node-ID selection from zero/one/many query results;
- one UI-local derived Threat Sheet view model;
- compact and full presentation modes inside the existing shared `ProjectionHost`;
- useful game information before metadata;
- every binding represented explicitly, including unavailable and corrupt bindings;
- reuse of the existing semantic `StatblockRenderer` for trusted mechanics;
- connected World Graph objects and relationship navigation;
- exact graph revision, binding, statblock revision, and digest status that remains inspectable;
- replacement of the grounded Threat path that currently opens the generic Statblock Workbench without loading the selected object.

### Explicitly excluded

- Threat or statblock editing;
- append-revision or revise flows;
- binding preference, primary selection, or revision adoption;
- Plan Markdown/Tiptap embedding;
- durable placement;
- combat insertion or mutable runtime state;
- image/media generation or selection;
- generic projection-host redesign;
- new graph writes or DungeonMind writes;
- backend query/hydration redesign;
- a second Plan-only statblock renderer;
- a latest, current-head, label, corpus, or first-result fallback.

### Named successors

- `MAGIC-D3` — real publish → reload → Hermes discovery → exact Threat projection dogfood;
- `SBW12` — exact revision Plan embed;
- `SBW13` — append immutable mechanics revision;
- `SBW14` — governed binding preference/revision adoption;
- `AOW03` / `AOW04` — durable placement and shared action routing;
- `COMBAT01` / `SBW15` — exact lineage into combat.

---

## §1 Mission and invariant

### Mission

When a GM opens one resolved published Threat from graph memory, DungeonBuddy presents a compact or full composed Threat Sheet whose identity and relationships come from the exact World Graph revision that resolved the reference and whose mechanics come only from every exact immutable DungeonMind revision returned by SBW10a.

### Merge-ready invariant

```text
For one selected resolved Threat, every displayed identity field is attributable to one exact
World Graph node at one exact graph revision, and every displayed mechanic is attributable to
one exact (binding_id, statblock_id, revision_id, definition_digest) chain. Zero, one, and many
bindings remain explicit. No presentation path silently chooses a different Threat, a first
binding, current graph head, latest statblock revision, corpus artifact, or copied mechanics body.
```

### Falsification test

The slice is invalid if it must:

- open the generic authoring Workbench instead of the selected published Threat;
- infer identity from label, title, path, or array position;
- request current head because the graph reference lacks its resolving revision;
- display one binding while silently hiding other eligible bindings;
- persist hydrated mechanics in the graph, browser storage, or a new durable projection record;
- modify `ProjectionHost` to understand Threats;
- add editing, placement, embed, combat, or media behavior.

---

## §2 Authority and ownership

| Concern | Authority |
| --- | --- |
| Campaign Threat identity and relationships | World Graph exact revision |
| Mechanics identity and immutable definition | DungeonMind statblock revision |
| Threat-to-mechanics connection | `ThreatStatblockBindingV1` in the World Graph |
| Query and exact mechanics composition | merged SBW10a `POST /api/live/threats/query-hydration` |
| Shared drawer lifecycle and compact/full host behavior | Surface Interaction `ProjectionHost` |
| Explicit renderer registration | Surface Interaction projection catalog |
| Current graph-reference content projection | Plan graph-reference adapter and `PlanReferenceObjectCard` |
| Candidate/draft authoring | `StatblockWorkbenchModule`; not this projection |
| Semantic mechanics rendering | existing `StatblockRenderer` |

### Ownership rules

- `ProjectionHost` remains surface-neutral and Threat-unaware.
- The projection catalog remains renderer-selection infrastructure, not domain logic.
- Plan provides exact graph-reference scope and host actions; it does not own mechanics truth.
- The Threat Sheet renderer consumes typed derived input and owns presentation only.
- SBW10a remains the sole backend composition boundary for published Threat mechanics.
- The browser does not call DungeonMind directly.
- No view-model field becomes durable authority.

---

## §3 Current truth at the design base

The base contains:

1. governed publication and exact commit recovery through SBW09c2b;
2. SBW10a exact Threat query/hydration and Hermes access;
3. a shared neutral `ProjectionHost` with compact, wide, and fullscreen sizes;
4. an explicit lease-scoped projection catalog;
5. an existing graph-reference content projection;
6. a semantic `StatblockRenderer` already used by the Workbench.

The product gap is specific:

- `PlanReferenceObjectCard` renders the selected graph object;
- Threat/statblock-shaped objects currently expose **Open statblock tool**;
- that action opens `StatblockWorkbenchModule`;
- its own help text admits that it does **not** load the selected object's statblock;
- no product path composes the exact selected Threat with the exact accepted mechanics already available through SBW10a.

SBW10b owns that gap. It does not replace authoring. It replaces the false implication that a generic authoring tool is the selected published Threat's projection.

---

## §4 User-visible behavior

### 4.1 Entry

Opening a resolved graph reference whose exact graph node is a Threat opens the existing graph-reference content projection. No second drawer and no Plan-specific host are introduced.

- `glanceOnly=true` renders the compact Threat Sheet.
- Expand renders the full Threat Sheet.
- Relationship navigation continues to use the existing graph-reference binding and stale-operation guard.
- Non-Threat graph objects continue through the existing graph-object projection unchanged.
- Corpus fallback, ambiguous, unresolved, and error references never claim a published Threat Sheet.

### 4.2 Compact view: useful at a glance

The compact view prioritizes:

1. Threat name;
2. threat kind and intended/graph role;
3. short campaign/encounter summary;
4. key mechanics when exactly one trusted mechanics binding is available;
5. mechanics-binding count and status;
6. the most useful connected graph objects and predicates;
7. an honest expand affordance.

When exactly one trusted binding is available, compact mechanics should include the existing renderer's bounded summary or equivalent typed values such as:

- AC;
- HP;
- speed;
- challenge/level signal when present;
- a bounded set of key actions, traits, or encounter-facing capabilities.

Do not invent a new mechanics summary from rendered Markdown or untyped string scraping.

When zero or several trusted bindings are available, compact mode does not choose a winner. It shows the binding state and defers per-binding mechanics to full mode.

### 4.3 Full view

The full view presents:

- Threat identity and authored summary;
- threat kind, role, aliases/tags when present;
- connected graph objects grouped or ordered by useful predicate;
- every enumerated binding in deterministic order;
- a full semantic statblock panel for every `available` binding;
- an honest locator/status panel for `unavailable`, `exact_revision_missing`, `integrity_failure`, or `not_requested` bindings;
- collapsed technical details for graph revision, node ID, relationship edge ID, binding ID, statblock ID, mechanics revision ID, and definition digest;
- provenance/evidence only behind an inspectable details affordance.

### 4.4 Binding policy

There is no implicit mechanics winner in this slice.

Deterministic display order:

```text
(binding role, phase key, variant label, binding ID)
```

Null optional values sort after populated values. IDs are final tie-breakers.

Rules:

- one available binding: compact may display its key mechanics;
- several available bindings: compact reports count/status; full renders each separately;
- unavailable binding: retain exact known locators and reason;
- missing exact revision: never fetch latest;
- integrity failure: never render the returned mechanics as trusted;
- malformed edge with no binding identity: identify the relationship edge only;
- `not_requested`: supported by the view model but normal SBW10b loads request mechanics.

`SBW14`, not this slice, owns a campaign preference or revision-adoption decision.

---

## §5 Exact selection and loading contract

### 5.1 Resolved graph scope

A `resolved_graph` reference used for Threat projection must carry the exact graph snapshot that produced it:

```text
world_id
campaign_id
graph_revision_id
threat_node_id
```

Recommended shape:

```ts
interface ExactGraphReferenceScope {
  worldId: string;
  campaignId: string;
  revisionId: string;
}

resolved_graph {
  ...existing fields
  graphScope: ExactGraphReferenceScope
}
```

The names may adapt to established TypeScript naming, but all three scope IDs are required and nonblank. Do not derive the graph revision from bootstrap/current head at render time.

If the current resolver cannot provide this exact scope from the projection snapshot, stop and report the missing predecessor contract. Do not substitute current head.

### 5.2 SBW10a request

For the selected Threat:

```text
worldId        = resolved graph scope world ID
campaignId     = resolved graph scope campaign ID
revisionPin    = resolved graph scope revision ID
queryText      = exact Threat node ID
focusNodeIds   = [exact Threat node ID]
maxHits        = bounded value sufficient for explicit exact filtering
includeMechanics = true
```

The focus ID guarantees the selected Threat is requested as an exact graph anchor. Query text does not become durable identity.

### 5.3 Exact response filtering

Never consume `hits[0]`.

After a successful SBW10a response:

1. require `response.revisionId === requested revisionPin`;
2. filter hits by `hit.threat.nodeId === selected threatNodeId`;
3. exactly one match → eligible for projection;
4. zero matches → typed `not_found` presentation;
5. more than one exact-node match → typed integrity presentation;
6. never choose a label-equivalent or relationship-derived different Threat.

The selected Threat's `matchReasons` are useful diagnostics, not identity authority.

### 5.4 Async stale-result rule

Capture the exact selection tuple before loading:

```text
(world_id, campaign_id, graph_revision_id, threat_node_id)
```

A response may commit to component state only when the current tuple is byte-for-byte equal to the captured tuple. Selection change, graph-reference change, unmount, or lease replacement permanently invalidates the old completion.

Abort transport where supported, but correctness must not depend on abort succeeding.

### 5.5 Failure presentation

| Condition | Presentation |
| --- | --- |
| Loading | Identity shell plus “Loading exact mechanics…” |
| SBW10a 404 / exact Threat absent | Threat identity remains visible; exact mechanics not found |
| SBW10a unavailable | Threat identity and relationships remain visible; mechanics unavailable |
| Revision mismatch | Integrity warning; no mechanics rendered |
| Zero exact node matches | Exact selected Threat not returned; no substitute |
| Multiple exact node matches | Integrity warning; no arbitrary winner |
| Binding unavailable/missing | Per-binding status with locator retained |
| Digest/statblock mismatch | Integrity status; mechanics hidden as untrusted |

Do not collapse these into a generic empty card.

---

## §6 Derived view-model contract

Add one UI-local, non-durable view model owned by the Threat projection package. Suggested shape:

```ts
type ThreatSheetLoadStatus =
  | "loading"
  | "ready"
  | "not_found"
  | "unavailable"
  | "integrity_failure";

interface ThreatSheetBindingViewModel {
  relationshipEdgeId: string;
  bindingId: string | null;
  role: string | null;
  phaseKey: string | null;
  variantLabel: string | null;
  statblockId: string | null;
  revisionId: string | null;
  definitionDigest: string | null;
  hydrationStatus:
    | "available"
    | "unavailable"
    | "exact_revision_missing"
    | "integrity_failure"
    | "not_requested";
  revision: ExactRevisionResourceV1 | null;
  message: string | null;
}

interface ThreatSheetViewModel {
  scope: ExactGraphReferenceScope;
  threatNodeId: string;
  label: string;
  summary: string | null;
  threatKind: string | null;
  intendedRole: string | null;
  aliases: readonly string[];
  relationships: readonly ThreatRelationshipViewModel[];
  bindings: readonly ThreatSheetBindingViewModel[];
  mechanicsDisposition: string;
  loadStatus: ThreatSheetLoadStatus;
  message: string | null;
}
```

Exact field names should follow existing generated/API types. Do not create a second canonical statblock interface. The revision field must reuse the existing exact DungeonMind response type consumed by `StatblockRenderer`.

The mapper must be pure, deterministic, and independently tested.

---

## §7 Renderer contract

### 7.1 One renderer family

Reuse `StatblockRenderer` for trusted mechanics definitions. Do not fork its semantic layout into a Threat-specific copy.

A thin Threat Sheet composition layer may add:

- Threat identity header;
- campaign/encounter summary;
- relationship list;
- binding status/header;
- compact/full policy;
- exact technical details.

It may not reinterpret or persist mechanics.

### 7.2 Information hierarchy

Default hierarchy:

```text
useful game information
→ campaign identity and encounter meaning
→ connected objects and navigable relationships
→ exact binding/revision status
→ provenance and technical IDs
```

Evidence scores, internal diagnostics, and full provenance must not dominate the default view. They remain inspectable.

### 7.3 Relationship display

- preserve exact relationship edge IDs internally;
- show human-useful predicate/target label;
- allow the existing relationship selection callback when authorized;
- do not navigate on render;
- do not infer a new Threat or mechanics binding from a related node;
- compact mode may bound the visible list but must disclose the remaining count;
- full mode shows the complete admitted relationship list returned for the exact Threat.

---

## §8 Integration and demolition

### 8.1 Existing host path

Use the existing content projection:

```text
graph reference opens
→ ProjectionHost
→ graph-reference catalog registration
→ PlanReferenceObjectCard
→ Threat Sheet composition when resolved exact node is a Threat
```

Do not add another `ProjectionHost`, another drawer state owner, or another global projection registry.

### 8.2 Non-Threat behavior

Existing graph-object, fallback, ambiguous, unresolved, relationship-navigation, and `/ingest` repair behavior must remain equivalent for non-Threat references.

### 8.3 Demolition declaration

```text
Replaced path: resolved published Threat → generic “Open statblock tool” action that opens
  StatblockWorkbenchModule without loading the selected Threat
Deleted in this PR: yes, for exact resolved Threats
If no: not applicable
Named remaining consumer: StatblockWorkbenchModule remains the authoring/review tool; corpus fallback
  may retain its existing generic statblock affordance until it becomes a governed graph Threat
Required deletion owner: SBW10b
```

The normal authoring tool registration remains. This slice removes only the misleading selected-published-Threat behavior.

---

## §9 Expected implementation paths

Default deny paths not listed here. Exact file names may adjust after bounded discovery, but the architectural owners may not change.

### Existing files likely modified

```text
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/graphReference/types.ts
apps/live-control-ui/src/planSurface/projection/LegacyProjectionHostAdapter.tsx
apps/live-control-ui/src/planSurface/projection/PlanProjectionCatalogRegistration.tsx
apps/live-control-ui/src/planSurface/projection/projectionBindings.ts
apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx
apps/live-control-ui/src/planSurface/reference/buildPlanGraphObjectActions.ts
```

Owning tests for each touched path are included in scope.

### New package suggested

```text
apps/live-control-ui/src/statblocks/projection/ThreatSheetProjection.tsx
apps/live-control-ui/src/statblocks/projection/threatSheetViewModel.ts
apps/live-control-ui/src/statblocks/projection/threatSheetProjection.css
apps/live-control-ui/src/statblocks/projection/ThreatSheetProjection.test.tsx
apps/live-control-ui/src/statblocks/projection/threatSheetViewModel.test.ts
```

### Bounded discovery

Maximum additional production paths: **8**  
Maximum additional test paths: **10**

Allowed reasons:

- exact graph scope originates in a different graph-reference resolver owner;
- SBW10a frontend transport types are generated or stored in a different established API module;
- current `StatblockRenderer` requires a narrow exported adapter already owned by its package;
- exact graph-reference fixtures require updates after the required scope becomes non-optional;
- CSS ownership follows an existing statblock projection stylesheet.

Forbidden reasons:

- broad renderer redesign;
- Surface Interaction contract expansion unrelated to exact Threat scope;
- generic graph-reference rewrite;
- authoring Workbench cleanup beyond the named demolition;
- backend changes to avoid threading exact frontend scope;
- placement, combat, embed, edit, media, or revision-adoption work.

Every discovered path must be listed in the implementation PR handback with one sentence explaining necessity.

---

## §10 Implementation sequence

1. Re-anchor on the exact `main` SHA that contains this merged handoff and merged SBW10a.
2. Record that immutable base SHA in the implementation PR body before code changes.
3. Add failing tests proving resolved graph references retain exact world/campaign/revision scope.
4. Thread exact graph scope from the graph projection snapshot; no current-head read.
5. Add frontend SBW10a request/response types and transport adapter.
6. Add pure exact-node response selector and view-model mapper with zero/one/many adversarial tests.
7. Add compact/full Threat Sheet composition using the existing `StatblockRenderer`.
8. Integrate Threat rendering into the existing graph-reference content projection.
9. Preserve non-Threat and relationship-navigation behavior.
10. Remove the generic “Open statblock tool” action for exact resolved Threats.
11. Run focused, owning, typecheck, build, and prohibition-search gates.
12. Perform the minimal live proof when a real published Threat and DungeonMind service are available.
13. Commit all final implementation and test changes with a `statblock:` commit.
14. Push the implementation branch.
15. Open the implementation PR with a `statblock:` title. Do not assign or predict its PR number.

---

## §11 Required adversarial evidence

### Exact scope and selection

- resolved Threat scope contains exact world, campaign, and graph revision IDs;
- blank/missing exact scope fails closed;
- graph head advances after open; request still uses resolving revision;
- response revision differs from pin; no mechanics rendered;
- selected Threat sorts after another returned Threat; exact node ID still wins;
- selected Threat absent but label-equivalent Threat present; no substitute;
- relationship-derived additional Threats do not displace selected exact node;
- stale response after selection change cannot commit.

### Bindings

- zero bindings shows identity and honest no-binding state;
- one available binding enables compact mechanics;
- two available bindings do not choose a first winner;
- multiple bindings render deterministically in full mode;
- exact revision missing retains locator, no latest call;
- DungeonMind unavailable retains identity and locators;
- malformed edge with nullable binding IDs renders relationship-edge integrity state;
- wrong statblock/digest/integrity result never reaches `StatblockRenderer` as trusted mechanics;
- `not_requested` remains honest if supplied by fixture.

### Projection and compatibility

- Threat glance mode is compact;
- Expand produces full presentation without changing exact selection tuple;
- non-Threat graph object rendering remains unchanged;
- corpus fallback does not claim published Threat mechanics;
- unresolved/ambiguous reference does not call SBW10a;
- relationship navigation still resolves through the current binding and stale guard;
- closing/unmounting during load blocks completion;
- authoring Workbench remains registered and usable as a tool;
- exact resolved Threat no longer offers the misleading generic Workbench action.

---

## §12 Verification commands

Implementation must adapt exact filenames to discovered owners and report the final list.

```bash
cd apps/live-control-ui

pnpm exec vitest run \
  src/statblocks/projection \
  src/planSurface/reference/PlanReferenceObjectCard.test.tsx \
  src/planSurface/reference/buildPlanGraphObjectActions.test.ts \
  src/planSurface/projection/LegacyProjectionHostAdapter.test.tsx \
  src/planSurface/projection/projectionBindings.test.tsx

pnpm exec vitest run \
  src/surfaceInteraction/projection \
  src/planSurface/projection/projectionCatalogRegistrations.test.tsx \
  src/planSurface/projection/projectionRegistry.test.tsx

pnpm run build
```

Backend predecessor regression:

```bash
uv run pytest \
  tests/test_threat_query_hydration.py \
  tests/test_threat_query_hydration_api.py -q
```

Prohibition searches:

```bash
rg -n "latest|currentHead|current_head|first\(|hits\[0\]|bindings\[0\]|corpus" \
  apps/live-control-ui/src/statblocks/projection \
  apps/live-control-ui/src/planSurface/reference \
  apps/live-control-ui/src/api

rg -n "StatblockWorkbenchModule" \
  apps/live-control-ui/src/statblocks/projection \
  apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx
```

Every match must be explained. Fail the PR for any identity/mechanics fallback or Threat projection dependency on the Workbench.

---

## §13 Minimal live proof

Use one real published Threat, preferably Mireward Latchling or another campaign Threat with an exact accepted binding.

Record:

```text
world_id
campaign_id
graph_revision_id
threat_node_id
relationship_edge_id
binding_id
statblock_id
mechanics revision_id
definition_digest
```

Proof sequence:

1. Open the Threat from a graph reference.
2. Confirm compact view shows useful identity, encounter context, binding status, and key mechanics when exactly one trusted binding exists.
3. Expand and confirm full exact statblock plus connected graph objects.
4. Advance or otherwise change current graph head; reopen using the original exact reference/snapshot and confirm the same graph revision and mechanics chain.
5. Stop DungeonMind or simulate dependency unavailability; confirm identity/relationships remain while mechanics become unavailable.
6. Restore DungeonMind; reload exact same reference and confirm mechanics recover without rebinding.

If no real published Threat is available in the implementation environment, automated evidence may merge only with an explicit `MAGIC-D3 still required` statement. Do not fabricate live proof.

---

## §14 Acceptance rubric

- [ ] Exact graph world/campaign/revision scope is carried by the resolved reference.
- [ ] No current-head read or default is used for Threat projection.
- [ ] SBW10a is the only published-Threat mechanics loader.
- [ ] Response revision must equal the requested pin.
- [ ] Exact Threat selection is by node ID, never first result or label.
- [ ] Compact/full views run inside the existing shared ProjectionHost.
- [ ] Useful game information appears before evidence and technical metadata.
- [ ] Every binding remains explicit; no first-win or hidden preference.
- [ ] Trusted mechanics reuse the existing semantic StatblockRenderer.
- [ ] Unavailable/missing/integrity states preserve honest identity and locators.
- [ ] Relationship navigation remains functional and stale-safe.
- [ ] Non-Threat graph references remain behavior-equivalent.
- [ ] Exact resolved Threats no longer open the generic Workbench as their projection.
- [ ] No durable writes, copied mechanics, editing, embed, placement, combat, or media behavior ships.
- [ ] Focused tests, typecheck/build, backend predecessor tests, and prohibition searches are green.
- [ ] Implementation branch is committed, pushed, and opened with a `statblock:` PR title without preassigning a PR number.

---

## §15 Reviewer protocol

1. Confirm implementation ancestry contains the merge of this handoff and SBW10a merge `b1479970`.
2. Find where exact graph scope enters `resolved_graph`; reject current-head reconstruction.
3. Trace selected `graphNodeId` through the SBW10a request and exact response filter.
4. Search for `hits[0]`, `bindings[0]`, latest/current-head APIs, and label/corpus fallbacks.
5. Confirm multiple bindings remain explicit in compact and full behavior.
6. Confirm only `available` bindings can reach `StatblockRenderer` as trusted mechanics.
7. Confirm malformed/integrity responses retain locators and do not render mechanics.
8. Confirm `ProjectionHost` contains no Threat-specific imports or branches.
9. Confirm the existing graph-reference content projection remains the host path.
10. Confirm non-Threat, fallback, unresolved, and relationship-navigation tests remain green.
11. Confirm the generic Workbench path is removed only for exact resolved Threats and authoring remains intact.
12. Confirm no successor capability was pulled into scope.

---

## §16 Stop conditions

Stop and report instead of widening scope when:

- the graph-reference resolver cannot provide the exact snapshot revision that produced the selected node;
- SBW10a cannot retrieve the exact focused Threat by node ID at that revision;
- the frontend would need a direct DungeonMind credential or request;
- the existing exact revision resource cannot be consumed by `StatblockRenderer` without creating a second canonical statblock interface;
- multiple bindings require a product preference decision to render honestly;
- a required production path exceeds bounded discovery;
- implementation requires `ProjectionHost` to become Threat-aware;
- the requested work expands into editing, embedding, placement, combat, media, or binding adoption;
- a backend change is proposed merely to avoid threading exact scope through the UI.

For a genuine predecessor contract gap, return a narrow design amendment proposal. Do not implement a fallback.

---

## §17 Required implementation handback

The implementation PR must state:

- exact immutable base SHA containing this handoff;
- actual head SHA;
- all changed paths and every bounded-discovery justification;
- exact selected Threat request and response-filter behavior;
- compact/full information hierarchy;
- zero/one/many binding behavior;
- demolition result for the generic resolved-Threat Workbench action;
- focused test, build, backend regression, and prohibition-search results;
- live proof IDs, or an honest `MAGIC-D3 still required` limitation;
- explicit confirmation that edit, embed, placement, combat, media, and binding adoption remain false;
- final commit and pushed branch evidence;
- no assigned or predicted PR number.

---

## Final dispatch check

- [ ] This handoff is merged to `main`.
- [ ] Implementation begins from the exact handoff-bearing `main` SHA.
- [ ] SBW10a merge `b1479970` is in ancestry.
- [ ] No implementation PR number has been assigned in advance.
- [ ] Implementation PR title begins with `statblock:`.
- [ ] Exact graph scope is designed before rendering.
- [ ] Exact node-ID filtering is tested before UI integration.
- [ ] Multiple bindings remain explicit.
- [ ] Existing ProjectionHost and StatblockRenderer are reused.
- [ ] Named demolition is completed.
- [ ] Final implementation changes are committed and pushed before review request.
