---
# Literal Markdown the worker MUST use as the PR-body skeleton.
# The complete checked-in handoff remains authoritative.
pr_body_template: |
  ## Outcome

  The generic World Graph projection is the single source of truth for recap
  node-view shape and relationship direction: recap reuses generic node views
  directly, and every World Graph direction is emitted as outgoing, incoming,
  or related before any surface consumes it.

  ## Merge-ready invariant

  For one exact WorldGraphProjection, every recap nodeViews[*] payload is the
  exact serialized generic WorldGraphProjectionNodeView for that node, and
  every direction emitted anywhere inside the World Graph projection contract
  is exactly outgoing, incoming, or related; no recap or Plan adapter performs
  field-by-field node copying or direction translation.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Recap nested views are structurally derived | recap response model + service | type-identity/parity test and exact per-node serialized-payload equality | {{TODO: pass/fail/not run + provenance}} |
  | Existing recap fields retain their values | recap route | before/after compatibility fixture excluding newly inherited generic fields | {{TODO}} |
  | World adjacency vocabulary is normalized | Kernel World projection | outgoing/incoming/related tests for adjacency and suggested expansions | {{TODO}} |
  | World relationship vocabulary is normalized | Kernel World projection | top-level and query-context relationship tests | {{TODO}} |
  | No surface direction translator remains | recap module + Plan adapter | source guard, focused Python tests, frontend tests, TypeScript typecheck | {{TODO}} |
  | Deferred union behavior is untouched | diff boundary | changed-path proof plus targeted union regression | {{TODO}} |

  ## Scope and explicit deferrals
  {{TODO: base/head, actual changed paths, paths outside §4, additive recap node fields, and named successors still false}}

  ## Evidence produced
  ### Automated
  {{TODO}}
  ### Adversarial
  {{TODO}}
  ### Regression
  {{TODO}}
  ### Manual / dogfood
  {{TODO}}

  ## Gaps, waivers, and stop conditions
  {{TODO: none, or exact missing evidence, operator waiver, baseline failure, and stop condition}}
---

# HANDOFF — Derive recap views and normalize World Graph direction

> **COMPLETED — 2026-07-26T19:09:02Z.** Shipped via [PR #416](https://github.com/Drakosfire/DungeonMindBuddy/pull/416)
> (`main` merge commit `6410e04763846b1752336e9725a00e360ba8579f`).
> Recap nested views reuse `WorldGraphProjectionNodeView`; World Graph directions are
> closed `outgoing`/`incoming`/`related`.
> **Three review rounds** (all GitHub `COMMENTED` under self-review fallback; treat banners as the verdict):
> 1. APPROVE (`pullrequestreview-4782314232`, head `c939a026`) — architecture/invariant held on first independent re-verify.
> 2. REQUEST CHANGES (`pullrequestreview-4782325624`) — blockers: recap compatibility baseline lived only in `/tmp` (head-vs-head tests); typecheck red without base/head diagnostic equivalence + explicit operator waiver; no compile-time proof that World Graph direction rejects `outbound`.
> 3. REQUEST CHANGES / waiver gate (`pullrequestreview-4782346430`, corrective heads `3e3c28bd`/`635b569a`) — technical evidence closed (committed `recap_compat_baseline_v1.json` + replay test; base/head typecheck 37→36, `only_head=0`; `WorldGraphDirectionContractProof`); remaining gate was explicit operator waiver for red `npm run typecheck`, which the operator granted before merge.
> Archived as `HANDOFF-pr416-…`.
> **Follow-ups (named successors still open — see DECISION next-gate fork):** `migrate-union-mention-path`; `normalize-union-direction-vocabulary`; PR380B. **Archived for historical reference; do not re-dispatch.**

**Created:** 2026-07-26, America/Denver.
**Status:** DONE — merged as GitHub **PR #416** (`6410e04763846b1752336e9725a00e360ba8579f`).
**Canonical handoff path:** `Docs/Plans/archive/2026-07-26/graph-lens-projection-handoffs/HANDOFF-pr416-derive-recap-views-normalize-direction.md`
**Implementation base:** `5c19d433c9e103573ea6bd72ae1f34483862569f` — merge of PR #414.
**Suggested branch:** `agent/derive-recap-views-normalize-direction`
**Content slug:** `derive-recap-views-normalize-direction`

> **Dispatch gate:** Dispatch is prohibited until the worker has read this handoff in full, resolved current `main`, inventoried actual raw direction values, and confirmed that no external consumer imports the recap-private nested view classes scheduled for deletion.
>
> This checked-in handoff is the complete authority for the slice. The worker must not compress, replace, or reinterpret it before implementation. The PR description must use the frontmatter skeleton and remain a truthful merge contract; it cannot substitute for this handoff.

## Shared vocabulary

| Term | Definition |
|---|---|
| **World projection contract** | The versioned `dmb_world_graph_projection_v1` models and serialized payload produced by `src/graph_memory/kernel/world_projection.py`. |
| **Recap envelope** | The independently versioned `dmb_world_graph_recap_projection_v1` response: recap identity, document, focus overlay, node map, mentions, source spans, diagnostics, and trust boundary. |
| **Derived nested view** | A recap nested value represented by the generic World Graph model itself, not a parallel hand-written class or field-by-field adapter. |
| **Direction vocabulary** | The presentation-safe closed set `outgoing` \| `incoming` \| `related`. |
| **Raw direction vocabulary** | Persisted or lower-layer values such as `outbound`, `inbound`, `outgoing`, `incoming`, an empty value, or `related`. Raw vocabulary is not rewritten in storage by this slice. |
| **Parity proof** | A test proving that recap node serialization equals generic node serialization, so a new generic field cannot be silently omitted by a recap adapter. |
| **Existing-field compatibility** | Every recap field that existed before this slice retains its name, alias, type, default, and value, except the explicitly authorized direction normalization. |
| **Additive inherited fields** | Generic node fields previously omitted by the recap fork but now present because recap reuses `WorldGraphProjectionNodeView`; currently `evidenceRefIds` and `sourceArtifactIds`. |
| **Stop condition** | A discovered fact that invalidates this scope or requires a product/schema decision before implementation continues. |

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | Product surface changed? | Failure model changed? | Independently testable/revertible? | Decision |
|---|---|---|---|---|---|---|
| Make generic World Graph node views the recap nested-view source of truth | Yes | Yes — recap nested wire shape | No normal screen migration | Yes | Yes | **Include** |
| Normalize every World Graph projection direction to `outgoing`/`incoming`/`related` | Yes | Yes — generic World Graph wire semantics | Existing Plan consumer alignment only | Yes | Yes | **Include** under the same invariant |
| Delete recap-private node/evidence/adjacency/highlight adapters | No alone | No additional contract | No | No | Yes | **Include** as required removal |
| Delete Plan’s `outbound`/`inbound` translation | No alone | No additional contract | No visible behavior intended | No | Yes | **Include** as consumer proof |
| Additive inheritance of generic `evidenceRefIds` and `sourceArtifactIds` into recap node views | No alone | Yes — additive nested fields | No normal screen migration | No | Yes | **Include** and declare explicitly |
| Normalize Union Supergraph projection direction | Yes | Yes — different endpoint/model family | Potentially | Yes | Yes | Successor: `normalize-union-direction-vocabulary` |
| Migrate union recap mention matching to the hoisted linker | Yes | Yes — behavior changes under existing endpoint | Potentially | Yes | Yes | Successor: `migrate-union-mention-path` |
| Migrate Recap/Ingest product UI to the World Graph recap route | Yes | Yes | Yes | Yes | Yes | Successor: PR380B |
| Fully type World Graph relationships in TypeScript | Yes | Yes — frontend API model | No | No | Yes | Successor; not required here |
| Rewrite persisted edge/contribution direction values | Yes | Yes — durable graph data | Indirectly | Yes | Yes | **Reject** from this slice |
| Change `dmb_world_graph_recap_projection_v1` to `v2` | Yes | Yes | Potentially | Yes | Yes | **Stop condition** requiring operator decision |

**Selected capability:** the generic World Graph projection becomes the sole presentation contract for recap node shape and relationship direction, eliminating surface-owned copies and translations before PR380B consumes the route.

**Why the included rows share one invariant:** both changes remove a second source of truth at the same World Graph → surface boundary. Recap must not redefine generic node fields, and surfaces must not redefine generic direction semantics. The additive inherited fields and adapter deletions are consequences of that single contract, not separate product capabilities.

**Named successors:**

- `normalize-union-direction-vocabulary` — decide and normalize the separate `UnionSupergraphProjectionResponse` family.
- `migrate-union-mention-path` — apply the hoisted CommonMark-safe linker to the union preview path.
- PR380B — migrate Recap/Ingest UI and shared object navigation to the World Graph recap route.
- Full TypeScript typing for generic World Graph relationships/attributes/evidence.

## §1 Mission and merge-ready invariant

```text
A surface consuming WorldGraphProjection can rely on one nested node shape and one
relationship-direction vocabulary, so recap and Plan no longer maintain parallel
field-copying or direction-translation contracts.
```

**Merge-ready invariant:** `For one exact WorldGraphProjection, every recap nodeViews[*] payload is the exact serialized generic WorldGraphProjectionNodeView for that node, and every direction emitted anywhere inside the World Graph projection contract is exactly outgoing, incoming, or related; no recap or Plan adapter performs field-by-field node copying or direction translation.`

### Mission falsification test

This is not one slice if implementation must also:

- migrate the Recap or Ingest product UI;
- change union-supergraph mention behavior or CommonMark protection;
- normalize the `UnionSupergraphProjectionResponse` contract;
- rewrite persisted edge/contribution data;
- collapse the recap envelope into `dmb_world_graph_projection_v1`;
- introduce code generation or a general schema framework;
- add full frontend models for relationships, attributes, evidence, or source artifacts;
- change graph selection, revision pinning, campaign scope, admissibility, focus, evidence authority, or mention semantics.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every changed layer? | Yes. The generic World projection owns both the node representation and direction semantics. Recap and Plan changes merely cease translating that contract. |
| What is the highest-risk schema defect? | Calling a hand-maintained parity assertion “derivation” while retaining a second recap class tree. The implementation must directly reuse generic nested models; another generated or copied class is not sufficient unless direct reuse is proven impossible and reported as a stop condition. |
| What is the highest-risk direction defect? | Normalizing adjacency but forgetting suggested expansions, top-level relationships, or query-context relationships, leaving dual vocabulary inside one `WorldGraphProjection`. |
| What is the highest-risk scope defect? | Updating `unionSupergraphFixture.ts` or union projection builders merely because they also contain `outbound`. They are a separate wire family and separate behavior change. |
| What compatibility change is intentional? | Recap `nodeViews[*]` gains generic node fields previously omitted by the fork, currently `evidenceRefIds` and `sourceArtifactIds`; all existing fields retain their values, except directions normalize at the generic boundary. |
| What fact forces a stop? | Unknown non-empty raw direction values; an external consumer of deleted recap-private nested classes; a requirement to version the recap envelope; or any need to touch union projection behavior. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/DECISION-graph-lens-projection-boundary.md`, decisions 2 and 3, plus its sequencing table |
| Repository rules | `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, `.cursor/rules/dungeonbuddy-git-workflow.mdc`, `QUICK-REFERENCE-DungeonMind.mdc`; all Python via `uv run` |
| Base revision | `5c19d433c9e103573ea6bd72ae1f34483862569f` |
| Predecessor contract | PR #414: surface-neutral Markdown linker and thin recap mention adapter |
| Generic source contract | `WorldGraphProjection*` in `src/graph_memory/projection/world_projection.py` |
| Current recap fork | `WorldGraphRecap*` nested classes plus `_adapt_*` and `adapt_relationship_direction` in `world_recap_projection.py` |
| Exact input consumed | One exact `WorldGraphProjection`, including generic nodes, adjacency, suggested expansions, relationships, and optional query context |
| Exact outputs changed | Generic World Graph directions; recap nested node serialization; Plan adapter’s treatment of already-normalized directions |
| Named successors | `normalize-union-direction-vocabulary`, `migrate-union-mention-path`, PR380B |
| What remains false | Union projection may still carry legacy direction values; union mention path remains unprotected; Recap/Ingest screens remain unmigrated; no new graph facts or authority are created |
| Explicit non-goals | Schema framework, code generation, storage migration, product UI redesign, mention behavior, cache/telemetry, Graph Review lifecycle, extraction/identity changes |

Read authoritative inputs in this order before editing:

1. `Docs/Design/DECISION-graph-lens-projection-boundary.md`
2. This handoff in full
3. `src/graph_memory/projection/world_projection.py`
4. `src/graph_memory/kernel/world_projection.py`
5. `src/graph_memory/projection/world_recap_projection.py`
6. `apps/live_control_server/services/world_graph_recap_projection.py`
7. `apps/live-control-ui/src/api/types.ts`
8. `apps/live-control-ui/src/planSurface/reference/worldGraphProjectionAdapter.ts`
9. `tests/test_graph_kernel_world_projection.py`
10. `tests/test_world_graph_recap_projection.py`
11. `apps/live-control-ui/src/planSurface/reference/worldGraphProjectionAdapter.test.ts`
12. Repository workflow and review rules

### Authority precedence

1. Accepted graph-lens projection decision
2. Graph Kernel public-boundary authority
3. This checked-in handoff
4. Current `main` implementation and owning-boundary tests
5. PR #414 handback and merged patch
6. Local/attached project sources
7. Chat summaries

### Base movement rule

Before implementation:

```bash
git fetch origin
git rev-parse origin/main
git diff --name-only 5c19d433c9e103573ea6bd72ae1f34483862569f..origin/main
```

Inspect any drift touching every §4 path, World Graph route/service contracts, or frontend World Graph types.

If `main` moved materially in those areas, re-anchor the base and report the consequence before editing. A docs-only movement may be recorded without stopping.

### Mandatory raw-direction inventory

Before changing code, search tracked source, tests, and active fixtures for direction producers and consumers:

```bash
git grep -n -E 'outbound|inbound|outgoing|incoming|related' -- \
  src/graph_memory \
  apps/live_control_server \
  apps/live-control-ui/src \
  tests
```

Classify every hit as one of:

- persisted/raw graph vocabulary;
- lower union-projection vocabulary;
- World Graph projection producer;
- World Graph consumer;
- test/fixture for one of those contracts;
- prose/docs only.

The PR handback must include this inventory or a concise machine-generated table derived from it. Finding a non-empty runtime direction outside the recognized matrix in §6 is a stop condition.

## §3 Observable-path and adversarial-sequence inventory

| Observable path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Generic World node adjacency from source endpoint | May emit `outbound` or `outgoing` depending on lower input | Emit `outgoing` | Yes | Kernel conversion |
| Generic World node adjacency from target endpoint | May emit `inbound` or `incoming` depending on lower input | Emit `incoming` | Yes | Kernel conversion |
| Generic World adjacency with null/empty/undirected value | Can pass through empty/legacy value | Emit `related` | Yes | Kernel conversion |
| Suggested expansion | Inherits whatever adjacency conversion emitted | Emit only the closed direction vocabulary | Yes | Kernel conversion |
| Top-level `relationships[]` | Copies raw edge/assertion direction | Emit only `outgoing`/`incoming`/`related` | Yes | Kernel relationship builder |
| `queryContext.relationships[]` | Reuses World relationship views | Emit the same normalized vocabulary | Yes | Kernel query-context builder |
| Generic World route payload | May contain dual direction vocabulary | Contain no serialized `outbound`, `inbound`, empty, or null direction fields | Yes | serializer + route |
| Recap service node construction | Builds a second node class field by field | Reuse the generic node object/model; no nested adapter | Yes | recap response model + service |
| Recap route existing nested fields | Current forked values | Preserve names and values, with direction now already normalized | Yes | recap route |
| Recap route inherited generic-only node fields | Omitted | Include exact generic values, currently `evidenceRefIds` and `sourceArtifactIds` | Yes | recap response model + serializer |
| Recap mention/focus/source/trust fields | Existing PR #412/#414 behavior | Unchanged | Yes | recap helper + service |
| Plan World Graph node adapter | Translates `outbound`/`inbound` while changing camelCase to snake_case | Preserve camelCase→snake_case adaptation, pass normalized direction through unchanged | Yes | frontend adapter |
| GraphObjectCard direction guard | Accepts only UI vocabulary and returns null otherwise | Remains defensive; no translation added or required | Yes | card view-model builder |
| Union Supergraph projection | Separate legacy contract may emit `outbound`/`inbound` | Unchanged by this slice | Yes, by exclusion | diff boundary |
| Unknown non-empty raw direction | Current behavior can pass through | Do not guess or coerce; stop during inventory or fail closed with an explicit projection error if reached in a bounded test | Yes | Kernel boundary |
| Pinned World revision | Exact node/relationship state from pinned snapshot | Remains exact; normalization changes presentation vocabulary only | Yes | Kernel + recap service |

### Required adversarial sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Lower adjacency uses `outbound`; same edge appears as suggested expansion | Both serialize as `outgoing`; no translator runs in recap or Plan | Kernel + frontend focused tests |
| Lower adjacency uses `inbound` | Serializes as `incoming` through generic route and recap route | Kernel + recap route tests |
| Lower direction is `None` or empty | Serializes as `related`, never null/empty | pure normalizer + Kernel tests |
| Relationship direction comes from an active assertion overriding stored edge direction | Normalization applies after assertion selection; serialized relationship uses UI vocabulary | Kernel relationship test |
| Generic node carries evidence IDs, source artifact IDs, full-paragraph flag, and highlight spans | Recap node payload equals the generic node payload exactly | exact JSON parity test |
| A new field is later added to `WorldGraphProjectionNodeView` | Direct reuse carries it automatically; no recap adapter exists to omit it | type identity + absence-of-adapter guard |
| World Graph frontend fixture attempts `direction: "outbound"` | TypeScript rejects it after direction type narrowing | typecheck |
| Union fixture still contains `outbound` | It remains untouched and its union tests retain baseline behavior | changed-path proof + targeted regression |

## §4 Files in scope — allowlist

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Modify | `src/graph_memory/projection/world_projection.py` | Define the closed World direction type/normalizer contract; type adjacency and relationship views with it |
| Modify | `src/graph_memory/kernel/world_projection.py` | Normalize adjacency, suggested-expansion base views, top-level relationships, and query-context relationship output at the World boundary |
| Modify | `src/graph_memory/projection/world_recap_projection.py` | Delete recap-private nested view classes, `_adapt_*`, `adapt_world_node_to_recap_view`, and `adapt_relationship_direction`; type recap `node_views` as generic nodes |
| Modify | `src/graph_memory/projection/__init__.py` | Remove the deleted adapter export and, if required by existing package conventions, export the closed direction type/normalizer |
| Modify | `apps/live_control_server/services/world_graph_recap_projection.py` | Build `node_views` directly from `world.nodes`; preserve the recap envelope and every other service rule |
| Modify | `tests/test_graph_kernel_world_projection.py` | Own normalization tests for adjacency, suggested expansions, relationships, query context, route serialization, and unknown-direction failure |
| Modify | `tests/test_world_graph_recap_projection.py` | Own generic-type reuse, exact nested JSON parity, additive-field declaration, recap compatibility, and absence-of-adapter tests |
| Modify | `apps/live-control-ui/src/api/types.ts` | Narrow World Graph adjacency direction to the closed UI vocabulary without expanding unrelated `unknown[]` contracts |
| Modify | `apps/live-control-ui/src/planSurface/reference/worldGraphProjectionAdapter.ts` | Delete `outbound`/`inbound` translation; preserve casing/shape adaptation and pass direction through |
| Modify | `apps/live-control-ui/src/planSurface/reference/worldGraphProjectionAdapter.test.ts` | Prove `outgoing`/`incoming`/`related` pass-through and update typed fixtures |

### Bounded discovery exception

```text
Directory:
  tests/fixtures/graph_memory/
Maximum additional paths:
  3
Allowed path kinds:
  Existing fixtures directly consumed by tests/test_graph_kernel_world_projection.py
  or tests/test_world_graph_recap_projection.py.
Decision rule for including a path:
  The owning test cannot represent the normalized World Graph response without
  updating an existing expected World Graph payload containing outbound/inbound.
Explicit exclusions:
  Union-supergraph fixtures, recap preview fixtures, corpus data, contribution
  bundles, and persisted graph payloads.
Required report when a path is added:
  Exact test importing it, old/new direction values, and proof that the fixture
  represents dmb_world_graph_projection_v1 rather than a union contract.
```

No other path may change. If another path is required, stop and report it rather than broadening scope silently.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `src/graph_memory/projection/recap_projection.py` | Owns the union-supergraph recap projection and unprotected mention implementation; separate successor |
| `src/graph_memory/union_supergraph/**` | Persisted/lower union vocabulary is not the World Graph presentation boundary |
| `apps/live-control-ui/src/planSurface/graphPreview/unionSupergraphFixture.ts` | Typed as `UnionSupergraphProjectionResponse`; changing it would normalize a different contract |
| Other union preview fixtures/tests | Same separate contract |
| `src/graph_memory/projection/markdown_mentions.py` | PR #414 is closed; no mention or CommonMark behavior belongs here |
| `tests/test_markdown_mentions.py` and its golden fixture | Byte-identity predecessor evidence; must remain untouched |
| Recap/Ingest components, selectors, or product routing | PR380B product migration |
| `apps/live-control-ui/src/graphObjectCard/buildGraphObjectCardFromNodeView.ts` | Its function validates the UI enum; it does not translate `outbound`/`inbound` and may remain defensive |
| Full TypeScript models for `WorldGraphProjection.relationships`/`attributes`/`evidence` | Separate API-typing capability; only direction-owning types needed by current consumer are in scope |
| Contribution bundles, approved graph data, or migration scripts | This slice normalizes read presentation, not durable storage |
| Graph Kernel contribution/merge semantics | Raw semantic values stay intact |
| Schema code generation or dynamic Pydantic model factories | Disproportionate tooling; direct generic-model reuse is the selected derivation mechanism |
| Cache, invalidation, telemetry, warm loading | Separate runtime capability |
| Graph Review lifecycle, authoring, or write authority | Separate product capability |
| `Docs/Design/DECISION-graph-lens-projection-boundary.md` | Authority document; the worker does not edit its own authority |

Nearby work is not authorization.

## §6 Implementation contract and conditional matrices

### A. Recap envelope versus derived nested views

The recap envelope stays independently versioned. Only its nested graph node representation stops being a second source of truth.

| Recap field | Required representation after this slice | Compatibility rule |
|---|---|---|
| `schema` | Existing literal `dmb_world_graph_recap_projection_v1` | Unchanged unless schema policy forces a stop |
| `campaign_id` | Recap-specific scalar | Unchanged |
| `session_id` | Recap-specific scalar | Unchanged |
| `graph_id` | Exact alias of `snapshot.revision_id` | Unchanged |
| `snapshot` | `WorldGraphProjectionSnapshot` | Already reused; unchanged |
| `markdown` | Canonical recap with neutral-linker mentions | Unchanged |
| `focus` | `WorldGraphRecapFocusOverlay` | Remains recap-specific |
| `node_views` | `dict[str, WorldGraphProjectionNodeView]` | Direct generic reuse; no parallel nested class |
| `mentions` | `list[WorldGraphRecapMention]` | Remains recap-specific/navigation-only |
| `source_spans` | `list[WorldGraphRecapSourceSpan]` | Remains recap-specific; v1 still empty |
| `diagnostics` | `list[WorldGraphProjectionDiagnostic]` | Unchanged |
| `trust_boundary` | `WorldGraphProjectionTrustBoundary` | Unchanged |

Required implementation property:

```python
WorldGraphRecapProjection.node_views  # annotation resolves to:
dict[str, WorldGraphProjectionNodeView]
```

Required service behavior:

```python
node_views = {node.node_id: node for node in world.nodes}
```

Equivalent direct generic-model construction is allowed only if it does not enumerate node fields. The following are **prohibited**:

- another `WorldGraphRecapNodeView` class;
- generated recap copies of generic nested classes;
- `create_model` or schema-code-generation infrastructure;
- `model_dump(include={...})` field allowlists;
- a field-by-field `adapt_world_node_to_recap_view` replacement;
- parity tests used to excuse a second class tree.

Delete these recap-private symbols unless discovery proves a current external consumer, which is a stop condition:

- `WorldGraphRecapEvidenceBadge`
- `WorldGraphRecapTextHighlightSpan`
- `WorldGraphRecapAdjacencyCandidate`
- `WorldGraphRecapSuggestedExpansion`
- `WorldGraphRecapNodeView`
- `_adapt_evidence_badge`
- `_adapt_highlight_spans`
- `_adapt_adjacency`
- `_adapt_suggested_expansion`
- `adapt_world_node_to_recap_view`

### B. Additive recap nested fields

Direct reuse intentionally adds generic node fields the fork omitted:

```text
evidenceRefIds
sourceArtifactIds
```

Rules:

- Values must come verbatim from the exact returned generic projection.
- No recap-specific filtering or evidence interpretation is allowed.
- Mention `evidenceRefIds` remain empty; node provenance and mention authority are different contracts.
- The PR body must call these fields **additive**, not “byte-identical.”
- Existing recap nested fields must retain exact serialized values after direction normalization.

If repository/API policy requires a schema version bump for this additive change, stop for operator decision. Do not silently introduce `v2` or suppress the fields to preserve `v1` bytes.

### C. Closed World direction contract

Define one closed type:

```python
WorldGraphRelationshipDirection = Literal["outgoing", "incoming", "related"]
```

Both of these generic World models must use it:

- `WorldGraphProjectionAdjacencyCandidate.direction`
- `WorldGraphProjectionRelationshipView.direction`

`WorldGraphProjectionRelationshipView.direction` must no longer serialize null. Builders must provide a normalized value.

### D. Direction normalization matrix

| Raw/lower value | World Graph output | Rule |
|---|---|---|
| `outbound` | `outgoing` | Legacy alias |
| `outgoing` | `outgoing` | Idempotent |
| `inbound` | `incoming` | Legacy alias |
| `incoming` | `incoming` | Idempotent |
| `related` | `related` | Idempotent |
| `None` | `related` | No oriented direction |
| `""` or whitespace-only | `related` | No oriented direction |
| Any other non-empty value | No silent output | Stop during inventory; if reached at runtime in a test, fail closed with an explicit projection error |

Normalization must occur **after** the authoritative raw relationship/assertion value is selected and **before** constructing any `WorldGraphProjection*` model.

Apply the same normalizer to:

- `_convert_adjacency_candidate`;
- suggested expansions through their converted adjacency base;
- `_build_relationship_views` after active-assertion override selection;
- any bounded query-context relationship construction not already reusing row 3.

Do **not** mutate `UnionSupergraphEdge.direction`, assertion values, contribution payloads, or lower `GraphProjectionAdjacencyCandidate` values.

### E. Recap and frontend translator deletion

Delete `adapt_relationship_direction` from `world_recap_projection.py`. Recap receives normalized generic nodes.

In `worldGraphProjectionAdapter.ts`:

```typescript
// Required concept, not mandatory formatting:
direction: candidate.direction
```

Delete the function that recognizes `outbound`/`inbound`. Keep the adapter itself because it still converts camelCase World API fields to the existing snake_case `GraphProjectionNodeView` consumed by Plan cards.

Narrow the TypeScript World direction contract:

```typescript
export type WorldGraphRelationshipDirection = "outgoing" | "incoming" | "related";
```

Use it for `WorldGraphProjectionAdjacencyCandidate.direction`. Do not expand this slice into complete typing for `WorldGraphProjection.relationships`.

### F. Existing behavior that must remain unchanged

- exact World snapshot and revision-pin semantics;
- campaign/world scope semantics of the generic route;
- recap endpoint’s campaign-only/session-focused restrictions;
- recap source selection and ambiguity failure;
- mention matching, ordering, offsets, and diagnostics;
- focus overlay contents;
- navigation-only recap mentions;
- trust-boundary text;
- source spans remaining empty;
- node order and node ID keys;
- relationship facts, predicates, labels, provenance, session IDs, and campaign scope;
- union-supergraph projection output.

### G. Compatibility aliases

No compatibility alias for deleted recap nested classes is authorized by default. A compatibility alias would preserve a second public name and weaken the “one source of truth” contract.

If code search finds a real consumer outside §4 importing one of those classes or `adapt_world_node_to_recap_view`, stop and report:

- exact path/import;
- whether it is production, test, or docs;
- whether direct generic replacement is source-compatible;
- minimum additional path needed;
- recommendation: expand, split, or retain a temporary alias with explicit sunset.

Do not add the alias silently.

## §7 Verification plan and evidence ledger

All Python commands run from repository root with `uv run`. Frontend commands run from `apps/live-control-ui`.

| # | Guarantee | Owning boundary | Required command/evidence | Merge-blocking result |
|---:|---|---|---|---|
| 1 | Closed direction helper obeys the full matrix | projection/Kernel unit boundary | focused normalizer test including unknown non-empty failure | Any wrong mapping or silent pass-through |
| 2 | Adjacency and suggested expansions emit only UI vocabulary | Kernel World projection | `uv run pytest tests/test_graph_kernel_world_projection.py -q -k "direction or adjacency or suggested"` | Any `outbound`/`inbound`/null/empty output |
| 3 | Top-level and query-context relationships normalize after assertion selection | Kernel World projection | focused relationship and query-context tests | Any dual vocabulary or pre-selection normalization |
| 4 | Recap reuses generic node models | recap model/service | annotation/type assertion and exact model-dump equality | Any recap-private nested class or enumerated field adapter |
| 5 | Existing recap contract remains stable except declared changes | recap route | compatibility fixture/snapshot comparing all pre-existing fields | Undeclared value/name/default change |
| 6 | Additive inherited fields are exact | recap route | assert `evidenceRefIds` and `sourceArtifactIds` equal generic node payload | Missing, filtered, or invented values |
| 7 | Mention/focus/trust behavior unchanged | recap tests | complete `tests/test_world_graph_recap_projection.py` | Any unrelated regression |
| 8 | Plan adapter performs no direction translation | frontend adapter | focused Vitest + source assertion or code inspection | `outbound`/`inbound` branch remains |
| 9 | World frontend contract rejects legacy values | TypeScript boundary | `npm run typecheck` with fixtures using closed vocabulary | Typecheck failure or direction remains `string` |
| 10 | Union contract remains untouched | diff + regression | no union files in diff; existing focused union tests at baseline | Any union behavior/path change |
| 11 | No unrelated Python regression | repository test boundary | broader projection-focused suite with baseline protocol | New failures |
| 12 | Diff is clean and bounded | Git | name-only/stat/check evidence | Path outside §4/exception or whitespace errors |

### Required commands

```bash
# Base and scope
git fetch origin
git rev-parse origin/main
git merge-base origin/main HEAD
git diff --name-only $(git merge-base origin/main HEAD)...HEAD
git diff --stat $(git merge-base origin/main HEAD)...HEAD
git diff --check

# Direction inventory
git grep -n -E 'outbound|inbound|outgoing|incoming|related' -- \
  src/graph_memory \
  apps/live_control_server \
  apps/live-control-ui/src \
  tests

# Focused Python owning tests
uv run pytest tests/test_graph_kernel_world_projection.py -q
uv run pytest tests/test_world_graph_recap_projection.py -q
uv run pytest tests/test_graph_kernel_world_retrieval.py -q
uv run pytest \
  tests/test_graph_kernel_world_projection.py \
  tests/test_world_graph_recap_projection.py \
  tests/test_graph_kernel_world_retrieval.py \
  -q -k "direction or adjacency or relationship or node_view or recap"

# Broader projection regression; baseline protocol applies
uv run pytest tests/ -q -k "world_graph_projection or world_graph_recap_projection"

# Python static checks
uv run ruff check \
  src/graph_memory/projection/world_projection.py \
  src/graph_memory/kernel/world_projection.py \
  src/graph_memory/projection/world_recap_projection.py \
  src/graph_memory/projection/__init__.py \
  apps/live_control_server/services/world_graph_recap_projection.py \
  tests/test_graph_kernel_world_projection.py \
  tests/test_world_graph_recap_projection.py

# Frontend owning tests
cd apps/live-control-ui
npm test -- src/planSurface/reference/worldGraphProjectionAdapter.test.ts
npm run typecheck
```

### Required exact assertions

At minimum, tests must prove:

1. `normalize(outbound) == outgoing`
2. `normalize(outgoing) == outgoing`
3. `normalize(inbound) == incoming`
4. `normalize(incoming) == incoming`
5. `normalize(related) == related`
6. `normalize(None/empty/whitespace) == related`
7. `normalize(unknown-nonempty)` does not silently return a string
8. every serialized World node adjacency direction is in the closed set
9. every serialized suggested-expansion direction is in the closed set
10. every serialized top-level relationship direction is in the closed set
11. every query-context relationship direction is in the closed set
12. recap node type is `WorldGraphProjectionNodeView`
13. recap node JSON equals generic node JSON exactly
14. recap node inherited evidence/source IDs equal generic values
15. recap mention `evidence_ref_ids` remain `[]`
16. no `adapt_relationship_direction` symbol remains
17. no `adapt_world_node_to_recap_view` symbol remains
18. Plan adapter receives and returns `outgoing`/`incoming`/`related` unchanged
19. World Graph TypeScript fixtures cannot use `outbound`/`inbound`
20. union fixture behavior remains baseline and union files are absent from the diff

### Compatibility fixture rule

Before production edits, capture one representative current recap response containing:

- evidence badge;
- adjacency with source excerpt;
- full-paragraph flag and highlight spans;
- suggested expansion;
- `evidence_ref_ids` and `source_artifact_ids` on the generic source node;
- mention, focus overlay, diagnostics, source spans, snapshot, and trust boundary.

The head assertion must compare:

- every pre-existing recap field by exact serialized value;
- direction against the normalized expected value;
- newly inherited generic fields separately as declared additive fields.

Do **not** call the full payload byte-identical.

### Baseline failure protocol

If any required suite fails on the branch:

- run the exact command at the merge base in a clean worktree;
- compare exact failing test IDs and error classes;
- report base and head counts separately;
- prove zero new failures;
- do not call a nonzero command green;
- obtain an explicit operator waiver if the command is a hard acceptance gate despite unchanged failures.

### Manual/dogfood proof

No new product screen is authorized. Manual proof is limited to an existing World Graph request and existing Plan card path:

- request a World Graph projection containing at least one outgoing and one incoming adjacency;
- inspect response JSON for only the closed direction vocabulary;
- adapt a returned node through the existing Plan adapter;
- confirm displayed relationship direction remains semantically unchanged;
- request the recap route for the same revision and confirm nested node payload equality.

Record exact request identity, revision, and whether the proof used real data or a test fixture. Manual proof does not replace automated evidence.

## §8 Required handback and PR-body ledger

The PR description must use the frontmatter skeleton and include:

1. exact base SHA and head SHA;
2. actual changed paths and any bounded-discovery path;
3. raw-direction inventory summary by contract family;
4. exact derivation mechanism used;
5. deleted recap-private symbols;
6. declared additive recap fields;
7. before/after direction matrix;
8. evidence table with command, exit code, counts, and provenance;
9. baseline failures with base/head comparison;
10. explicit statement that union projection files and behavior remain unchanged;
11. explicit statement that `migrate-union-mention-path` and PR380B remain false;
12. stop conditions encountered and operator waivers;
13. any schema-version decision or confirmation that `v1` remains accepted;
14. focused diff and path-boundary evidence.

Required handback summary shape:

```markdown
## Outcome
<exact mission result>

## Contract changes
- Recap nested node type: <before → after>
- Direction vocabulary: <before → after>
- Additive recap fields: <list>
- Deleted translators/adapters: <list>

## Evidence
| Guarantee | Command/proof | Exit | Result | Provenance |
|---|---|---:|---|---|

## Scope
- Base: <sha>
- Head: <sha>
- Changed paths: <list>
- Paths outside allowlist: <none or justified exception>

## Still false
- Union direction normalization
- Union mention-path migration
- PR380B product migration

## Gaps, waivers, stop conditions
<none or exact details>
```

## §9 Acceptance criteria

The slice is merge-ready only when all are true:

- [ ] `WorldGraphRecapProjection.node_views` uses `WorldGraphProjectionNodeView` directly.
- [ ] No recap-private nested node/evidence/adjacency/suggested/highlight class tree remains.
- [ ] No field-by-field recap node adapter remains.
- [ ] Exact generic-node versus recap-node serialized equality is tested.
- [ ] Additive `evidenceRefIds` and `sourceArtifactIds` are explicit in tests and PR body.
- [ ] Existing recap fields retain exact values except authorized direction normalization.
- [ ] `WorldGraphProjectionAdjacencyCandidate.direction` is a closed three-value type.
- [ ] `WorldGraphProjectionRelationshipView.direction` is normalized and non-null in serialized output.
- [ ] Adjacency, suggested expansions, top-level relationships, and query context all normalize.
- [ ] Unknown non-empty raw values are not silently passed through or coerced.
- [ ] `adapt_relationship_direction` is deleted.
- [ ] `adapt_world_node_to_recap_view` and `_adapt_*` are deleted.
- [ ] Plan’s World Graph adapter no longer maps `outbound`/`inbound`.
- [ ] World Graph TypeScript direction is narrowed to the closed vocabulary.
- [ ] Union-supergraph source, fixtures, and behavior are untouched.
- [ ] PR #414’s linker and golden fixture are untouched.
- [ ] Revision pinning, scope, focus, mentions, evidence authority, and trust boundaries are unchanged.
- [ ] Every required command is reported truthfully with exit status and provenance.
- [ ] No new failures exist relative to base.
- [ ] Diff contains only §4 paths or a valid bounded-discovery exception.
- [ ] `git diff --check` is clean.

## §10 Reviewer checklist

Reviewers must verify, in this order:

1. **Scope:** no union projection, CommonMark, product migration, or durable data path changed.
2. **Derivation reality:** recap uses the generic model directly; a new copied/generated class tree is an automatic request-changes finding.
3. **Direction completeness:** inspect adjacency, suggested expansions, relationships, and query context—not only one constructor.
4. **Unknown handling:** no `return direction` fallback and no `unknown→related` coercion.
5. **Compatibility:** pre-existing recap values remain stable; additive fields are declared rather than hidden.
6. **Frontend:** camelCase→snake_case adaptation remains, direction translation is gone, type is narrowed.
7. **Evidence:** exact payload parity, focused tests, typecheck, baseline protocol, and changed-path proof are present.
8. **Successor honesty:** union direction, union mention protection, and PR380B remain explicitly false.

### Automatic request-changes findings

- a surviving `WorldGraphRecapNodeView` parallel class;
- any field allowlist used to construct recap nodes;
- `adapt_relationship_direction` or equivalent surface translation;
- a `WorldGraphProjection*` direction typed as arbitrary `str` and allowed to serialize unknown values;
- normalization applied before active-assertion relationship selection;
- union fixture/source changes without explicit operator scope expansion;
- claims of byte-identical recap payload despite additive fields;
- schema version changed without operator decision;
- unreported path outside the allowlist.

## §11 Re-review protocol

For every corrective commit after review:

- compare the new head to the previously reviewed head;
- inspect the corrective delta first;
- rerun the exact evidence owning the finding;
- re-evaluate the complete invariant, not only the changed lines;
- refresh every PR-body SHA, command result, and path count;
- report CI separately from author-local evidence;
- preserve unresolved successor boundaries.

## Stop conditions

Stop and report before continuing if any occurs:

- `origin/main` materially changed a §4 contract after base `5c19d433...`.
- Code search finds a production consumer outside §4 importing recap-private nested classes or `adapt_world_node_to_recap_view`.
- Actual raw runtime data contains a non-empty direction outside the §6 matrix.
- Direct generic-model reuse cannot preserve existing recap aliases/defaults without another class tree.
- The additive nested fields require `dmb_world_graph_recap_projection_v2` under repository policy.
- TypeScript direction narrowing forces changes to `UnionSupergraphProjectionResponse` or its fixtures.
- World relationship normalization requires mutating persisted graph data or contribution semantics.
- Any CommonMark/linker behavior must change.
- Any Recap/Ingest component or selector must change.
- More than three bounded fixture paths are required.
- A required test reveals a current behavior defect outside the mission.
- A second independently useful outcome emerges.

When stopped, report the exact fact, affected invariant clause, minimum scope consequence, and recommended split or operator decision. Do not improvise around the boundary.
