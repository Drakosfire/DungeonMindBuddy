---
# Literal Markdown the worker MUST use as the PR-body skeleton.
# The complete checked-in handoff remains authoritative.
pr_body_template: |
  ## Outcome

  The Union Supergraph projection-compatible node-view family now emits one
  closed relationship-direction vocabulary. Raw store values and reusable
  pre-change projection snapshots are normalized at the shared snake_case wire
  model boundary, so adjacency and suggested expansions serialize only
  outgoing, incoming, or related before any frontend consumer sees them.

  ## Merge-ready invariant

  For one exact UnionSupergraphStore, focus session, identity context, optional
  authored-overlay enrichment, and reusable projection snapshot, every
  relationship direction serialized inside the UnionSupergraphProjectionResponse-
  compatible node-view family is exactly outgoing, incoming, or related.
  Relative to the characterized base payload, the only authorized value changes
  are direction leaves mapped by the accepted alias table; all other fields,
  ordering, identity/evidence behavior, and raw store values remain exact.
  Unknown non-empty values fail closed. No frontend adapter translates
  outbound/inbound, and no World Graph, mention, storage, authoring-direction,
  or PR380B path changes.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Characterization predates implementation | Git history + committed fixture | fixture-only commit before production edit; real base SHA recorded | {{TODO}} |
  | Base dual vocabulary is proven | pre-change union projection | full-payload fixture containing legacy and closed direction leaves | {{TODO}} |
  | One normalization owner covers every ingress | shared snake_case wire model | model validator tests for live construction and persisted payload validation | {{TODO}} |
  | Mapping behavior matches World Graph | delegated helper + union-family wrapper | full alias/empty/unknown matrix | {{TODO}} |
  | Python wire contract is closed | GraphProjectionAdjacencyCandidate | Literal/type and validation tests rejecting legacy output values | {{TODO}} |
  | TypeScript wire contract is closed | union-compatible API types | compile-time proof rejecting outbound/inbound | {{TODO}} |
  | Adjacency and expansions are closed | union projection builder | exact direction-path assertions across store and edge-walk paths | {{TODO}} |
  | Existing reusable projections remain readable | manifest-backed adapter | persisted outbound snapshot validates and returns outgoing | {{TODO}} |
  | Only direction leaves change | full-payload characterization | recursive JSON-path diff allowlist | {{TODO}} |
  | Source/target semantics remain coherent | union projection | one edge: source-side outgoing, target-side incoming | {{TODO}} |
  | Gold and authored-overlay producers remain healthy | shared model consumers | focused regression suites; no production edits | {{TODO}} |
  | Object cards receive healthy non-null direction | frontend card builder | union fixture through card view-model test | {{TODO}} |
  | Raw store vocabulary remains unchanged | storage/import boundary | exact changed-path proof and raw-producer regression | {{TODO}} |
  | World Graph and unrelated slices remain untouched | diff boundary | denylist/source guard | {{TODO}} |
  | Existing endpoint serves only closed values | HTTP boundary | focused route JSON walk; baseline protocol if currently red | {{TODO}} |

  ## Scope and explicit deferrals
  {{TODO: resolved base/head, fixture and first-production SHAs, actual changed paths, exact direction-path deltas, paths outside the allowlist, baseline failures/waivers, and successors still false}}

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
  {{TODO}}
---

> **COMPLETED (2026-07-26):** Merged as [PR #427](https://github.com/Drakosfire/DungeonMindBuddy/pull/427) (`7a024363667f459560668df85928a4b6399c7cff`).
>
> **Review rounds (3 COMMENT submissions; REQUEST_CHANGES/APPROVE posted as COMMENT because reviewer and PR author share the repo account):**
> 1. `4783243121` — REQUEST CHANGES: endpoint direction walk missing; characterization could self-authorize wrong mapping; reusable-snapshot proof not full-payload; operator waiver/ledger gates.
> 2. `4783395237` — REQUEST CHANGES (waiver/ledger only): technical blockers closed by `39685a84`; still needed explicit operator waiver posture and PR-body ledger refresh.
> 3. `4783416821` — APPROVE at `39685a84`: endpoint, mapping-lock, and reusable full-payload proofs held; baseline-identical red tests not a separate merge gate per operator direction.
>
> **Follow-ups:** PR380B (Recap/Ingest UI + shared object navigation onto World Graph recap route); durable Union store/contribution direction migration remains deferred.
>
> Archived from `Docs/Plans/HANDOFF-normalize-union-direction-vocabulary.md` as part of the post-merge atomic doc-sync after PR #427.

# HANDOFF — Normalize the Union Supergraph projection direction vocabulary

**Created:** 2026-07-26, America/Denver.
**Status:** COMPLETED — merged as GitHub PR #427 (`7a024363`).
**Canonical handoff path:** `Docs/Plans/HANDOFF-normalize-union-direction-vocabulary.md`
**Implementation base:** `eb2d40ba86a9992c2df526e78efc5e8a1033c3eb` — merge of PR #423, `migrate-union-mention-path`.
**Suggested branch:** `agent/normalize-union-direction-vocabulary`
**Content slug:** `normalize-union-direction-vocabulary`

> **Dispatch gate:** Do not edit production code until the worker has read this handoff in full, resolved current `origin/main`, inventoried every producer and consumer of the snake_case `GraphProjectionAdjacencyCandidate` family, and committed the required pre-change direction characterization fixture by itself.
>
> This is the Union Supergraph-compatible wire family only. Do not edit World Graph production files, do not reopen mention linking, and do not combine this with PR380B.
>
> This checked-in handoff is the complete authority for the slice. The worker must not compress, replace, or reinterpret it before implementation. The PR description must use the frontmatter skeleton and remain a truthful merge contract; it cannot substitute for this handoff.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Union projection** | `RecapGraphProjection` produced from `UnionSupergraphStore` and exposed through the existing Union Supergraph projection endpoint. |
| **Union-compatible node-view family** | The snake_case `GraphProjectionNodeView`, `GraphProjectionAdjacencyCandidate`, and `GraphProjectionSuggestedExpansion` models used by Union, Gold Graph, and authored-overlay projection paths. This is distinct from the camelCase `WorldGraphProjection*` family. |
| **Closed direction vocabulary** | `outgoing` \| `incoming` \| `related`. These are the only healthy serialized wire values after this slice. |
| **Raw direction vocabulary** | Lower-layer or persisted store values such as `outbound`, `inbound`, `outgoing`, `incoming`, `related`, an empty string, or whitespace. Raw vocabulary may remain in `UnionSupergraphStore` and its producers. |
| **Legacy alias** | `outbound` or `inbound`, mapped respectively to `outgoing` or `incoming`. |
| **Normalization owner** | The shared snake_case adjacency wire model. Every candidate construction or model validation crosses this boundary, including reusable persisted projection snapshots. |
| **Live build path** | Projection construction from a current `UnionSupergraphStore` through `build_recap_graph_projection`. |
| **Reusable projection snapshot** | A previously persisted projection payload returned by `load_reusable_projection_from_snapshot` and validated as `RecapGraphProjection` without rebuilding from the store. |
| **Store-adjacency path** | `_build_node_adjacency` consuming `store.adjacency[node_id][*].direction` directly. This is the main source of `outbound`/`inbound`. |
| **Edge-walk fallback** | `_build_node_adjacency` deriving adjacency by walking `store.edges` when the adjacency index lacks the edge. It currently supplies source-side `edge.direction` or `"outgoing"` and target-side `incoming`. |
| **Direction leaf** | A JSON value at `node_views.<node>.adjacency[*].direction` or `node_views.<node>.suggested_expansions[*].direction`. The current Union response has no separate top-level relationship list. |
| **Full-payload characterization** | A committed base serialization of the complete public projection, not a direction-only excerpt. |
| **Authorized delta** | A direction leaf changes according to the explicit alias table, or an empty/whitespace input becomes `related`. No other field or ordering change is authorized. |
| **Fail closed** | An unknown non-empty direction raises a scoped validation/normalization error; it is not passed through and is not silently coerced to `related`. |
| **Defensive null-collapse** | The current frontend object-card helper accepts only the closed set and returns `null` for an unexpected value. It remains as defense in depth, not as a healthy-payload translator. |
| **Storage migration** | Rewriting `UnionSupergraphEdge.direction`, `UnionSupergraphAdjacencyItem.direction`, contribution data, preview imports, or stored adjacency values. This is not part of the slice. |
| **Stop condition** | A discovered requirement for a new endpoint error schema/status, a World Graph edit, a storage rewrite, a product migration, or another contract outside this invariant. |

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | Product surface changed? | Failure model changed? | Independently testable/revertible? | Decision |
|---|---|---|---|---|---|---|
| Normalize Union projection adjacency to the closed vocabulary | Yes | Yes — existing snake_case wire values | Existing consumers become healthy | Yes | Yes | **Include** |
| Normalize Union suggested expansions | No alone; inherited from adjacency | Same wire family | Existing consumers | Yes | Yes | **Include** under the same invariant |
| Normalize reusable persisted Union projection snapshots | No alone; required for compatibility | Existing projection-read behavior | No new screen | Yes | Yes | **Include** at the same model boundary |
| Close the Python adjacency direction type | No alone | Additive narrowing of public model | No | Yes | Yes | **Include** as enforcement |
| Close the TypeScript Union-compatible direction type | No alone | Frontend API contract narrowing | No redesign | Yes | Yes | **Include** as enforcement |
| Update the Union frontend fixture | No alone | Test/sample contract | No | No | Yes | **Include** as required consumer proof |
| Preserve Gold Graph and authored-overlay projections | No alone | No intended change | No | Prevents collateral breakage | Yes | **Include** as regression evidence only |
| Rewrite `UnionSupergraphStore` edge/adjacency directions | Yes | Yes — durable/read-model storage | Indirect | Yes | Yes | **Reject**; separate storage migration if desired |
| Change preview import, contribution merge, or reconciliation vocabulary | Yes | Yes — lower-layer semantics | Indirect | Yes | Yes | **Reject** |
| Normalize World Graph again or move its helper | No useful outcome here | Reopens completed PR #416 contract | Potentially | Yes | Yes | **Reject** |
| Remove frontend defensive null-collapse | No | No needed contract gain | Could alter unknown handling | Yes | Yes | **Reject**; keep defense in depth |
| Migrate Recap/Ingest UI to World Graph | Yes | Yes | Yes | Yes | Yes | Successor: **PR380B** |
| Reopen CommonMark mention linking | Yes | Separate behavior family | Potentially | Yes | Yes | **Reject**; PR #423 already merged |
| Normalize authoring `directed`/`undirected` | Yes | Different concept and schema | Authoring UI | Yes | Yes | **Reject** |
| Add a new Union projection error response/version | Yes | Yes | Existing endpoint | Yes | Yes | **Stop condition** requiring operator decision |

**Selected capability:** close the Union-compatible snake_case relationship-direction contract at the shared adjacency wire-model boundary, reusing the accepted World Graph mapping behavior without editing World Graph production code.

**Why the normalization owner is the shared model, not only `_build_adjacency_candidate`:** the normal live builder is not the only ingress. `build_plan_union_supergraph_projection` may return a reusable persisted payload through `RecapGraphProjection.model_validate(reusable)` without calling `_build_node_adjacency` or `_build_adjacency_candidate`. A builder-only normalizer would either reject healthy pre-change snapshots after the type narrows or continue emitting legacy vocabulary if the model remains open. The shared adjacency model covers live construction, persisted payload validation, Gold Graph construction, and authored-overlay enrichment through one enforceable contract.

**Named successors, still false after this slice:**

- **PR380B** — migrate Recap/Ingest UI and shared object navigation onto the World Graph recap route.
- Any durable Union store/contribution direction migration.
- Any authoring `directed`/`undirected` vocabulary decision.
- Any broader unification of the Union and World response families.

## §1 Mission, invariant, and pre-dispatch critique

### Mission

A consumer of `UnionSupergraphProjectionResponse`-compatible node views can rely
on one closed relationship-direction vocabulary, regardless of whether the
payload was freshly built from a Union store, loaded from a reusable projection
snapshot, derived from a Gold fixture, or enriched by an authored overlay.

### Merge-ready invariant

For one exact `UnionSupergraphStore`, focus session, identity context, optional
authored-overlay enrichment, and reusable projection snapshot, every
relationship direction serialized inside the `UnionSupergraphProjectionResponse`-
compatible node-view family is exactly `outgoing`, `incoming`, or `related`.
Relative to the characterized base payload, the only authorized value changes
are direction leaves mapped `outbound→outgoing`, `inbound→incoming`, and
empty/whitespace→`related` at the shared projection wire boundary; all other
fields, collection ordering, identity/evidence behavior, and raw store values
remain exact. Unknown non-empty values fail closed. No frontend adapter
translates `outbound`/`inbound`, and no World Graph, mention, storage,
authoring-direction, or PR380B path changes.

### Mission falsification test

This is not one slice if implementation must also:

- edit `src/graph_memory/projection/world_projection.py` or `src/graph_memory/kernel/world_projection.py`;
- change the World Graph direction type, table, error, or serialization;
- rewrite `UnionSupergraphEdge.direction` or `UnionSupergraphAdjacencyItem.direction`;
- edit preview import, contribution merge, candidate-to-contribution, or merge reconciliation production code;
- add a direction translator to a frontend adapter;
- delete or broaden the object-card defensive null-collapse;
- migrate Recap/Ingest screens or navigation to another endpoint;
- alter mention matching, Markdown, mention IDs, offsets, evidence, or redirects;
- alter authored relationship `directed`/`undirected` semantics;
- change edge selection, adjacency deduplication, expansion ranking, focus, evidence, identity, or source-excerpt behavior;
- add a new route, endpoint, response schema, version, or public error body;
- normalize every repository occurrence of the word `outbound`.

If any item becomes necessary, stop and report the smallest split rather than expanding this PR.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every changed production path? | Yes. The shared snake_case adjacency model is the serialized boundary for Union, Gold, authored overlay, and reusable projection payloads. Frontend changes only narrow the matching wire type and repair its fixture. |
| Why is a normalizer only in `_build_adjacency_candidate` insufficient? | Reusable persisted projections bypass that builder and are validated directly as `RecapGraphProjection`. Narrowing the model would make legacy snapshots fail; leaving the model open would keep the contract unenforced. |
| What is the highest-risk behavior defect? | Normalizing live store projections while stale reusable snapshots still emit or fail on `outbound`/`inbound`, producing source-dependent behavior under the same endpoint. |
| What is the highest-risk schema defect? | Changing only a fixture while Python and TypeScript directions remain `str`/`string`, leaving the contract open and future drift undetectable. |
| What is the highest-risk scope defect? | Treating every lower-layer `outbound` occurrence as a bug and rewriting store/import/contribution vocabulary. This slice owns projection emission, not storage. |
| What is the highest-risk semantic defect? | Coercing an unknown non-empty value to `related`, hiding corrupt or novel input as a valid relationship. Unknown values must fail closed. |
| What is the highest-risk compatibility defect? | A strict `Literal` rejects a reusable pre-change projection before the alias can normalize. A `mode="before"` model validator must normalize raw input before `Literal` validation. |
| Does the shared model affect non-Union producers? | Yes. Gold Graph and authored-overlay projection use the same candidate model. They already emit `outgoing`/`incoming`; focused regression proves no payload drift and no production edits are needed. |
| Does the Union response carry direction anywhere else? | Current inventory finds only adjacency and suggested expansions nested under `node_views`. There is no separate top-level relationship list in `RecapGraphProjection`. Discovery of another serialized carrier is a bounded-expansion question, not permission to guess. |
| What deliberate product effect is expected? | Union relationship cards that previously received `outbound` and collapsed it to `null` now receive `outgoing`. No component redesign is authorized. |
| What fact forces a stop? | A reusable payload cannot be normalized without changing snapshot identity rules; an unknown direction requires a new HTTP error contract; a producer emits a semantically distinct value not covered by the accepted table; or a World/storage/product file becomes necessary. |

## §2 Context, authority, and current-state inventory

### Authority and repository context

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/DECISION-graph-lens-projection-boundary.md`, especially direction decision and sequencing split |
| Completed analogue | PR #416 / archived `HANDOFF-pr416-derive-recap-views-normalize-direction.md` |
| Immediate predecessor | PR #423 (`eb2d40ba…`), which migrated Union mention linking and is now on `main` |
| Repository rules | `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, `.cursor/rules/dungeonbuddy-git-workflow.mdc`, `QUICK-REFERENCE-DungeonMind.mdc`; Python through `uv run` |
| Exact raw inputs | `UnionSupergraphStore`, reusable `RecapGraphProjection` payloads, Gold candidate fixtures, authored-overlay relationship candidates |
| Exact public output | Snake_case `UnionSupergraphProjectionResponse`-compatible `node_views[*].adjacency` and `suggested_expansions` |
| Mapping authority | Existing `normalize_world_graph_relationship_direction`; call it, do not copy or edit its alias table |
| Raw-store authority | `UnionSupergraphEdge.direction` and `UnionSupergraphAdjacencyItem.direction` remain open `str` |
| What remains false | No storage migration, no endpoint version change, no PR380B UI migration, no authoring direction normalization, no World Graph change |

Read authoritative inputs in this order before editing:

1. `Docs/Design/DECISION-graph-lens-projection-boundary.md`
2. This handoff in full
3. `Docs/Plans/archive/2026-07-26/graph-lens-projection-handoffs/HANDOFF-pr416-derive-recap-views-normalize-direction.md`
4. `src/graph_memory/projection/world_projection.py` — read-only mapping authority
5. `src/graph_memory/projection/node_view.py`
6. `src/graph_memory/projection/recap_projection.py`
7. `src/graph_memory/union_supergraph/model.py` — read-only raw boundary
8. `apps/live_control_server/services/union_supergraph_projection_adapter.py`
9. `apps/live_control_server/services/graph_gold_review.py` — read-only producer regression
10. `apps/live_control_server/services/graph_authoring_overlay_projection.py` — read-only producer regression
11. `apps/live-control-ui/src/api/types.ts`
12. `apps/live-control-ui/src/graphObjectCard/buildGraphObjectCardFromNodeView.ts`
13. `apps/live-control-ui/src/planSurface/graphPreview/unionSupergraphFixture.ts`
14. Owning tests named in §7

### Base movement rule

Before fixture generation or production edits:

```bash
git fetch origin
BASE=$(git rev-parse origin/main)
printf '%s\n' "$BASE"
git merge-base --is-ancestor eb2d40ba86a9992c2df526e78efc5e8a1033c3eb "$BASE"
git diff --name-only eb2d40ba86a9992c2df526e78efc5e8a1033c3eb.."$BASE"
```

If `origin/main` moved:

- use the new exact `origin/main` as the fixture generation base;
- inspect movement for any Union projection, node-view, adapter, frontend type, fixture, Gold, overlay, or World direction change;
- regenerate the fixture against the resolved base;
- record the new `base_sha` and `fixture_parent_sha`;
- stop if another in-flight slice overlaps the allowlist or changes the invariant.

Do not retain `eb2d40ba…` in fixture metadata merely because this handoff names it.

### Current serialized direction carriers

| Carrier | Current producer | Current behavior | This slice |
|---|---|---|---|
| `node_views[*].adjacency[*].direction` | Union store-adjacency path | Raw `item.direction`, commonly `outbound`/`inbound` | Normalize and close |
| `node_views[*].adjacency[*].direction` | Union edge-walk fallback | Source `edge.direction` or `outgoing`; target `incoming` | Normalize and close without changing selection/default logic |
| `node_views[*].suggested_expansions[*].direction` | Copies ranked adjacency candidate | Inherits whichever dialect adjacency carried | Closed by construction |
| Same nested fields | Reusable projection snapshot | Bypasses live builder; currently validated under open `str` | Normalize before `Literal` validation |
| Same nested fields | Gold Graph projection | Already emits `outgoing`/`incoming` | Regression only |
| Same nested fields | Authored overlay | Already emits `outgoing` | Regression only |
| Frontend `GraphProjectionAdjacencyCandidate.direction` | `apps/live-control-ui/src/api/types.ts` | Open `string` | Narrow to closed type |
| Object-card relationship direction | `buildGraphObjectCardFromNodeView` | Closed values pass; anything else becomes `null` | Keep behavior; prove healthy Union input no longer becomes `null` |
| `UnionSupergraphEdge.direction` | Store | Raw `str` | Untouched |
| `UnionSupergraphAdjacencyItem.direction` | Store adjacency index | Raw `str` | Untouched |
| World Graph direction fields | World projection family | Already closed by PR #416 | Untouched |

### Current defect in one response

The live Union builder currently has two direction dialects under the same response:

```text
store.adjacency item.direction  ── raw pass-through ──> outbound / inbound
store.edges fallback           ── local literals ─────> outgoing / incoming
```

Both become `GraphProjectionAdjacencyCandidate(direction: str)`, and suggested expansions copy that value. The frontend card helper recognizes only `incoming`, `outgoing`, and `related`, so a healthy-looking `outbound` wire value becomes `null` in the card view model.

### Mandatory pre-edit inventory

Run and attach results before production changes:

```bash
git grep -n -E 'GraphProjectionAdjacencyCandidate|GraphProjectionSuggestedExpansion|GraphProjectionNodeView' -- \
  src/graph_memory \
  apps/live_control_server \
  apps/live-control-ui/src \
  tests

git grep -n -E 'direction[=:].*(outbound|inbound|outgoing|incoming|related)|"direction"' -- \
  src/graph_memory/projection \
  src/graph_memory/union_supergraph \
  apps/live_control_server/services \
  apps/live-control-ui/src/planSurface/graphPreview \
  apps/live-control-ui/src/graphObjectCard \
  tests

git grep -n -E 'RecapGraphProjection\.model_validate|load_reusable_projection_from_snapshot|build_recap_graph_projection' -- \
  apps/live_control_server \
  src/graph_memory \
  tests
```

The handback must classify every result as:

- raw store/lower-layer input;
- Union-compatible wire producer;
- reusable wire payload ingress;
- frontend wire type/fixture;
- defensive consumer;
- World Graph family;
- unrelated vocabulary occurrence.

## §3 Exact design and implementation contract

### A. Preserve separate wire families

Do not collapse or alias the Union snake_case models to the World camelCase models. The accepted architecture permits distinct endpoint schemas. This slice reuses mapping behavior, not the entire World model family.

### B. Define a closed Union-compatible Python type in `node_view.py`

Add a family-local type:

```python
from typing import Literal

GraphProjectionRelationshipDirection = Literal[
    "outgoing",
    "incoming",
    "related",
]
```

Use it for:

```python
class GraphProjectionAdjacencyCandidate(BaseModel):
    ...
    direction: GraphProjectionRelationshipDirection
```

`GraphProjectionSuggestedExpansion` inherits the same contract.

Do not import or alias `WorldGraphProjectionAdjacencyCandidate`. Do not change the World type.

### C. Reuse the accepted mapping table through a thin wrapper

In `node_view.py`, add a snake_case-family wrapper that delegates to the existing World helper without changing its file:

```python
class GraphProjectionDirectionError(ValueError):
    """Raw relationship direction cannot enter the closed snake_case wire."""


def normalize_graph_projection_relationship_direction(
    direction: str | None,
) -> GraphProjectionRelationshipDirection:
    try:
        normalized = normalize_world_graph_relationship_direction(direction)
    except WorldGraphDirectionError as exc:
        raise GraphProjectionDirectionError(
            f"Unsupported graph projection relationship direction: {direction!r}"
        ) from exc
    return cast(GraphProjectionRelationshipDirection, normalized)
```

Requirements:

- delegate to the existing World helper; do not copy its mapping dict;
- do not edit the World helper, error, type, or tests except to run them as regression;
- preserve its exact case sensitivity and whitespace behavior;
- use a family-specific error message/type so a failure is attributable to this wire boundary;
- a package-level export is optional and allowed only if a real caller/test needs it.

### D. Normalize in a `mode="before"` field validator

The normalization owner is the model field:

```python
@field_validator("direction", mode="before")
@classmethod
def _normalize_direction(cls, value: object) -> GraphProjectionRelationshipDirection:
    return normalize_graph_projection_relationship_direction(value)
```

The exact annotation may use `str | None` after a defensive runtime check, but behavior must be:

- `outbound` → `outgoing`;
- `outgoing` → `outgoing`;
- `inbound` → `incoming`;
- `incoming` → `incoming`;
- `related` → `related`;
- `None`, empty, or whitespace → `related` when presented directly to the model/normalizer;
- unknown non-empty or non-string → fail closed.

Why `mode="before"` is mandatory:

- a `Literal`-only field rejects legacy aliases before normalization;
- reusable persisted payloads may contain `outbound`/`inbound`;
- direct candidate constructors from the live builder also cross this validator;
- Gold and authored-overlay candidates remain accepted because their values are already closed.

Do not add a second mapping call in `_build_node_adjacency`, `_build_adjacency_candidate`, the adapter, Gold, or overlay services. One owner avoids source-dependent behavior.

### E. Preserve live builder semantics exactly

No production edit to `recap_projection.py` is expected. Specifically preserve:

- store adjacency is iterated first;
- edge IDs are deduplicated exactly as today;
- identity redirects and projectability filtering remain exact;
- source-side fallback remains `edge.direction or "outgoing"`;
- target-side fallback remains `"incoming"`;
- focus anchoring remains exact;
- candidate order remains exact;
- expansion ranking and rank reasons remain exact;
- suggested expansions copy the already-closed candidate direction;
- all non-direction candidate fields remain exact.

If implementation claims `recap_projection.py` must change, stop and explain why the model boundary cannot own the behavior. Do not add a second normalizer merely for visibility.

### F. Preserve reusable projection compatibility

The manifest-backed adapter can return:

```python
return RecapGraphProjection.model_validate(reusable)
```

The model validator must make a pre-change reusable payload containing legacy direction aliases readable and normalize it into the current closed wire contract.

Required test shape:

- create/stamp a reusable projection payload with at least one adjacency and suggested expansion using `outbound` and one using `inbound`;
- exercise `build_plan_union_supergraph_projection` through the reusable-snapshot branch;
- assert the returned model serializes `outgoing`/`incoming`;
- assert the source persisted fixture bytes/payload are not rewritten;
- assert every non-direction field remains exact.

Do not invalidate all old snapshots, mutate artifact files, or change snapshot dependency identity in this slice.

### G. Close the TypeScript snake_case contract

In `apps/live-control-ui/src/api/types.ts`, define:

```typescript
export type GraphProjectionRelationshipDirection =
  | "outgoing"
  | "incoming"
  | "related";
```

Use it for:

```typescript
export interface GraphProjectionAdjacencyCandidate {
  ...
  direction: GraphProjectionRelationshipDirection;
}
```

Add a compile-time proof analogous to, but independent from, the existing World proof:

```typescript
type _GraphProjectionDirectionRejectsOutbound = _ExpectTrue<
  "outbound" extends GraphProjectionRelationshipDirection ? false : true
>;
```

Also prove rejection of `inbound` and acceptance of the complete closed set.

Requirements:

- do not modify `WorldGraphRelationshipDirection` or its proof;
- do not make the Union type an alias of the World frontend type unless a real compile/import constraint requires it and the handback explains the coupling;
- do not leave `GraphProjectionAdjacencyCandidate.direction` as `string`;
- `GoldGraphProjectionResponse` inherits the narrowed node-view contract through the existing Union-compatible response family.

### H. Keep the defensive frontend consumer

`buildGraphObjectCardFromNodeView.ts::normalizeDirection` remains unchanged unless TypeScript requires a harmless annotation narrowing. It must continue to return `null` for an unexpected runtime value.

No frontend production code may translate:

```text
outbound -> outgoing
inbound  -> incoming
```

The backend/shared wire model owns that mapping.

Add or update a frontend test that takes the updated Union fixture through `buildGraphObjectCardFromNodeView` and proves every healthy relationship direction is non-null and semantically correct.

### I. Update the Union fixture, not raw fixtures

Change only the projection-level sample:

`apps/live-control-ui/src/planSurface/graphPreview/unionSupergraphFixture.ts`

Every adjacency and suggested-expansion `outbound` becomes `outgoing`. Add an `incoming` example only if it materially strengthens a consumer test without inventing unrelated graph facts; otherwise use a focused test-local node.

Do not rewrite raw Union store fixtures merely to make greps clean. The purpose is to prove raw aliases normalize at runtime.

### J. Unknown direction failure contract

The unit/model boundary must fail closed for unknown non-empty values. This slice does not authorize a new HTTP error schema or status code.

Required behavior:

- direct normalizer call raises `GraphProjectionDirectionError`;
- model construction/validation raises Pydantic `ValidationError` rooted in the direction field;
- no unknown value appears in serialized output;
- no unknown value becomes `related`.

If route-level testing requires defining a new public error response or status, stop and request an operator decision. A raw 500 under synthetic invalid data is not automatically a new contract to solve here; report current behavior honestly.

### K. No schema-version bump by default

The response field already exists and its intended consumer vocabulary is already `outgoing`/`incoming`/`related`. This is a contract hardening and legacy-alias normalization under the existing response shape.

Do not bump a schema/version unless an actual external consumer requires legacy values. Discovery of such a consumer is a stop condition with evidence.

## §4 Strict scope boundary

### Production allowlist

The expected production diff is limited to:

1. `src/graph_memory/projection/node_view.py`
2. `src/graph_memory/projection/__init__.py` — optional; only for a demonstrated export need
3. `apps/live-control-ui/src/api/types.ts`
4. `apps/live-control-ui/src/planSurface/graphPreview/unionSupergraphFixture.ts`

No production edit to `recap_projection.py`, the adapter, Gold service, overlay service, route, or card builder is expected.

### Test and characterization allowlist

1. `tests/fixtures/graph_memory/union_direction_characterization_v1.json`
2. `tests/test_graph_memory_projection_contract.py`
3. `tests/test_live_union_supergraph_projection_adapter.py`
4. `tests/test_live_union_supergraph_projection_api.py`
5. `tests/test_graph_memory_union_projection_identity_redirects.py`
6. `tests/test_graph_authoring_overlay_projection.py`
7. `tests/test_graph_authoring_overlay_projection_merge.py`
8. `tests/test_live_graph_gold_review_api.py`
9. `apps/live-control-ui/src/graphObjectCard/buildGraphObjectCardFromNodeView.test.ts`
10. `apps/live-control-ui/src/planSurface/graphPreview/UnionSupergraphRecapProjection.test.tsx`
11. `apps/live-control-ui/src/planSurface/graphPreview/recapNodePresentation.test.ts`
12. `apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.test.tsx`
13. `apps/live-control-ui/src/api/liveApi.test.ts` — only if the focused endpoint fixture is already owned here

A test file may remain untouched. Inclusion in the allowlist is permission for focused evidence, not a requirement to manufacture changes.

### Explicit production denylist

Do not edit:

- `src/graph_memory/projection/world_projection.py`
- `src/graph_memory/kernel/world_projection.py`
- `src/graph_memory/projection/world_recap_projection.py`
- `apps/live_control_server/services/world_graph_recap_projection.py`
- World Graph frontend adapters, models, fixtures, or tests
- `src/graph_memory/projection/recap_projection.py` unless a proven stop condition is escalated
- `apps/live_control_server/services/union_supergraph_projection_adapter.py`
- `apps/live_control_server/routes/graph_preview.py`
- `src/graph_memory/union_supergraph/model.py`
- `src/graph_memory/union_supergraph/preview_import.py`
- `src/graph_memory/union_supergraph/merge_reconciliation_apply.py`
- `src/graph_memory/kernel/contribution_merge.py`
- `src/graph_memory/candidate_graph_to_contribution.py`
- approved contribution bundles or graph data
- `apps/live_control_server/services/graph_gold_review.py`
- `apps/live_control_server/services/graph_authoring_overlay_projection.py`
- authored-overlay schema/models or `directed`/`undirected` logic
- `src/graph_memory/projection/markdown_mentions.py`
- known-entity mention extraction or mention fixtures
- `apps/live-control-ui/src/graphObjectCard/buildGraphObjectCardFromNodeView.ts` except a type-only annotation forced by compilation and documented in handback
- PR380B product migration paths, navigation, or screen redesign
- docs authority/decision files as part of implementation; post-merge doc-sync is separate

### Bounded-discovery rule

If a required compile/test fix needs a path outside the allowlist:

1. stop before editing it;
2. report exact path and symbol;
3. classify it as wire producer, consumer, raw storage, World family, or unrelated;
4. show why existing allowlisted code cannot satisfy the invariant;
5. propose the minimum expansion or split;
6. obtain operator approval.

Do not use “typecheck made me” as blanket scope permission.

## §5 Characterization-first contract

### First branch commit rule

The first branch commit must add only:

`tests/fixtures/graph_memory/union_direction_characterization_v1.json`

No production file, test file, script, generated cache, or unrelated fixture may be in that commit.

The fixture commit must precede the first production edit in Git history. Amending the fixture commit after production work invalidates provenance unless history is rebuilt honestly.

### Fixture metadata

The fixture root must include:

```json
{
  "schema": "dmb_union_direction_characterization_v1",
  "base_sha": "<actual unmodified generation SHA>",
  "fixture_parent_sha": "<same actual base SHA>",
  "generated_via": "graph_memory.projection.recap_projection.build_recap_graph_projection",
  "normalization_contract": {
    "outbound": "outgoing",
    "outgoing": "outgoing",
    "inbound": "incoming",
    "incoming": "incoming",
    "related": "related",
    "empty_or_whitespace": "related",
    "unknown_nonempty": "error"
  },
  "cases": []
}
```

`base_sha` is the code revision used to generate `base_projection`, not the fixture commit SHA.

### Case payload

Each case contains enough exact input to reconstruct the public projection, plus:

- `case_id`;
- `category`: `unchanged` or `normalized`;
- full Union store payload;
- focus/session ID;
- optional Markdown/sidecar/paragraph inputs only when needed to hold identity/evidence behavior constant;
- `base_projection`: complete `model_dump(mode="json")` output;
- `expected_direction_deltas`: exact JSON Pointer-like paths and expected base/head values;
- a short reason.

Example expected delta:

```json
{
  "path": "/node_views/pc_caelynn/adjacency/0/direction",
  "base": "outbound",
  "head": "outgoing"
}
```

Do not store direction-only output slices in place of the full projection.

### Minimum characterization matrix

At least 24 cases, including:

| Family | Minimum | Required coverage |
|---|---:|---|
| Store adjacency legacy aliases | 6 | `outbound`/`inbound` on focus and non-focus edges; adjacency plus expansion |
| Already-closed store adjacency | 4 | `outgoing`/`incoming`/`related` remain exact |
| Empty/whitespace store adjacency | 2 | empty and whitespace become `related` |
| Edge-walk fallback | 4 | adjacency index absent; source and target views; expansion inheritance |
| Source/target inverse | 3 | same canonical edge produces source `outgoing` and target `incoming` under normal raw `outbound` input |
| Identity redirect/rewire | 2 | survivor endpoint and merged-away filtering retain exact non-direction fields |
| Ordering/ranking | 2 | multiple edges preserve adjacency order, expansion rank, and rank reason |
| No-edge/empty node view | 1 | full payload unchanged |

At least:

- 8 cases must prove base `outbound`/`inbound` exists;
- 6 cases must be full-payload unchanged;
- 4 cases must have both adjacency and suggested-expansion direction leaves;
- 2 cases must exercise identity redirects;
- 1 case must use a real current fixture path through the public builder, with private prose omitted from the committed fixture if synthetic data proves the same contract.

Unknown non-empty values belong in focused unit/model tests, not in successful projection characterization.

### Full-payload replay rule

At head:

- `unchanged`: `head_projection == base_projection` exactly;
- `normalized`: recursively compare complete JSON values;
- collect every differing leaf path;
- assert the path set equals `expected_direction_deltas` exactly;
- assert every differing path ends with `/direction`;
- assert every base/head pair matches the accepted mapping;
- assert no list order, key presence, type, count, ID, rank, evidence, focus, identity diagnostic, mention, Markdown, or source-span value changes.

Never bless a new difference by refreshing the fixture at head. A new non-direction difference is a stop condition.

### Recursive diff helper requirements

The replay test should report actionable paths. It must distinguish:

- missing key vs null value;
- list length/order changes;
- scalar type changes;
- value changes.

A shallow top-level comparison or a grep for `outbound` is insufficient.

## §6 Behavior and adversarial matrix

### Normalizer matrix

| Input | Output | Notes |
|---|---|---|
| `"outbound"` | `"outgoing"` | Legacy alias |
| `"outgoing"` | `"outgoing"` | Idempotent |
| `"inbound"` | `"incoming"` | Legacy alias |
| `"incoming"` | `"incoming"` | Idempotent |
| `"related"` | `"related"` | Idempotent |
| `None` | `"related"` | Direct model/normalizer input |
| `""` | `"related"` | Direct/store-adjacency input |
| whitespace | `"related"` | Trimmed by accepted helper |
| `"OUTBOUND"` | error | Preserve accepted case sensitivity |
| `"sideways"` | error | Unknown non-empty fails closed |
| number/object/list | error | Non-string fails closed |

### Builder-path matrix

| Input route | Raw value | Expected wire | Other behavior |
|---|---|---|---|
| Store adjacency | `outbound` | `outgoing` | Exact candidate order/fields |
| Store adjacency | `inbound` | `incoming` | Exact candidate order/fields |
| Store adjacency | `related` | `related` | Full payload unchanged |
| Store adjacency | empty/whitespace | `related` | Only direction leaf changes |
| Edge fallback, source | `outbound` | `outgoing` | Preserve `edge.direction or outgoing` expression |
| Edge fallback, source | `outgoing` | `outgoing` | Full payload unchanged |
| Edge fallback, target | any normal directed edge | `incoming` | Preserve hardcoded target-relative direction |
| Suggested expansion | candidate `outgoing` | `outgoing` | Same edge/node, rank, reason |
| Suggested expansion | candidate `incoming` | `incoming` | Same edge/node, rank, reason |
| Reusable snapshot | `outbound`/`inbound` | `outgoing`/`incoming` | Source artifact remains immutable |
| Gold fixture | `outgoing`/`incoming` | unchanged | No Gold production edit |
| Authored overlay | `outgoing` | unchanged | No overlay production edit |

### Important edge-fallback preservation

Do not reinterpret lower-layer edge semantics. In particular:

- an empty string on the source-side edge fallback currently triggers `edge.direction or "outgoing"`; preserve that result as `outgoing`;
- whitespace is truthy, reaches the normalizer, and becomes `related` under the accepted helper;
- the target-side fallback remains `incoming`;
- do not replace direction with a new source/target derivation algorithm in this slice.

Characterize these cases explicitly so an apparent cleanup does not create semantic drift.

### Adversarial sequences

Tests must include:

1. store adjacency contains `outbound`, while the same edge would be found by fallback — store path wins, output `outgoing` once;
2. store adjacency contains `inbound`, fallback source logic would differ — existing first-path/dedup behavior remains exact;
3. adjacency index absent — fallback creates source `outgoing` and target `incoming`;
4. multiple equal-ranked edges — normalization does not reorder adjacency or expansions;
5. identity redirect changes adjacent node ID — direction normalization does not alter redirect counts/diagnostics;
6. merged-away edge is filtered — normalizer does not resurrect it;
7. reusable payload includes both legacy aliases — model validation normalizes without rebuilding;
8. reusable payload includes unknown non-empty — validation fails closed;
9. Gold projection constructs closed values — exact payload survives the narrowed model;
10. authored overlay appends `outgoing` relationship — exact payload survives the narrowed model;
11. frontend fixture through card builder — every healthy relationship direction remains non-null;
12. direct runtime object with unexpected value reaches defensive card helper in an isolated test — it still collapses to `null`, proving defense remains.

## §7 Verification plan and evidence ledger

All Python commands run from repository root using `uv run`. Frontend commands run from `apps/live-control-ui`.

| # | Guarantee | Owning boundary | Required evidence | Merge-blocking result |
|---|---|---|---|---|
| 1 | Fixture predates implementation | Git history | fixture-only commit before production commit | Mixed/amended provenance |
| 2 | Base dual vocabulary is real | public Union builder | full base payloads with legacy leaves | No measurable base defect |
| 3 | Mapping matches accepted World behavior | wrapper unit tests + World regression | complete matrix | Duplicate/divergent behavior |
| 4 | Unknown values fail closed | normalizer/model | scoped error and ValidationError | Pass-through or related coercion |
| 5 | Python type is closed | shared model | Literal annotation and validation | Direction remains open `str` |
| 6 | Live store path is normalized | Union projection | characterization replay | Legacy output remains |
| 7 | Edge fallback remains exact | Union projection | source/target/fallback matrix | Selection/default/order drift |
| 8 | Suggested expansions are closed | Union projection | recursive output walk | Legacy leaf remains |
| 9 | Reusable snapshots remain compatible | adapter | persisted legacy payload test | Rejection, raw output, or artifact mutation |
| 10 | Only direction leaves change | full payload | exact recursive path diff | Any non-direction drift |
| 11 | Identity/evidence behavior remains exact | Union identity tests | full payload/diagnostics assertions | Count, target, evidence, or ordering drift |
| 12 | Gold and overlay remain healthy | shared-model consumers | focused regression | Production edit or payload drift |
| 13 | TypeScript contract rejects aliases | API types | compile-time proof + typecheck | Direction remains `string` or aliases compile |
| 14 | Union fixture is closed | frontend fixture | source/typecheck test | `Outbound`/`inbound` remains in projection fixture |
| 15 | Object card receives non-null healthy directions | card builder | focused Vitest | Healthy Union relation becomes `null` |
| 16 | Defensive null-collapse remains | card builder | existing/adversarial test | Unknown runtime value silently accepted |
| 17 | Raw storage remains raw and untouched | diff boundary | exact path proof | Store/import/contribution edit |
| 18 | World Graph remains untouched | diff + regression | denylist and PR #416 suites | World production change/regression |
| 19 | Endpoint emits closed vocabulary | HTTP route | recursive response walk | Legacy/unknown wire value |
| 20 | No new baseline failures | all focused suites | base/head failure comparison | New failure or undocumented waiver |
| 21 | Diff is clean and bounded | Git/Ruff | allowlist/stat/check | Extra path or static error |

### Required commands

```bash
# Base, scope, and commit order
git fetch origin
BASE=$(git merge-base origin/main HEAD)
git rev-parse origin/main
git rev-parse "$BASE"
git diff --name-only "$BASE"...HEAD
git diff --stat "$BASE"...HEAD
git diff --check
git log --oneline --decorate "$BASE"..HEAD

# Direction and caller inventory — classify results; do not demand global absence
git grep -n -E 'GraphProjectionAdjacencyCandidate|GraphProjectionSuggestedExpansion|GraphProjectionNodeView' -- \
  src/graph_memory \
  apps/live_control_server \
  apps/live-control-ui/src \
  tests

git grep -n -E 'outbound|inbound|outgoing|incoming|related' -- \
  src/graph_memory/projection \
  src/graph_memory/union_supergraph \
  apps/live_control_server/services \
  apps/live-control-ui/src/api/types.ts \
  apps/live-control-ui/src/planSurface/graphPreview \
  apps/live-control-ui/src/graphObjectCard \
  tests

git grep -n -E 'RecapGraphProjection\.model_validate|load_reusable_projection_from_snapshot' -- \
  apps/live_control_server \
  src/graph_memory \
  tests

# Union projection and full-payload characterization
uv run pytest tests/test_graph_memory_projection_contract.py -q

# Union adapter, reusable snapshot, identity, and HTTP boundary
uv run pytest \
  tests/test_live_union_supergraph_projection_adapter.py \
  tests/test_graph_memory_union_projection_identity_redirects.py \
  tests/test_live_union_supergraph_projection_api.py \
  -q

# Shared-model consumer regressions: Gold and authored overlay
uv run pytest \
  tests/test_graph_authoring_overlay_projection.py \
  tests/test_graph_authoring_overlay_projection_merge.py \
  tests/test_live_graph_gold_review_api.py \
  -q

# Completed World Graph contract regression — production files remain untouched
uv run pytest \
  tests/test_graph_kernel_world_projection.py \
  tests/test_world_graph_recap_projection.py \
  -q -k "direction or adjacency or relationship or projection"

# Focused cross-boundary selection
uv run pytest \
  tests/test_graph_memory_projection_contract.py \
  tests/test_live_union_supergraph_projection_adapter.py \
  tests/test_graph_memory_union_projection_identity_redirects.py \
  tests/test_live_union_supergraph_projection_api.py \
  tests/test_graph_authoring_overlay_projection.py \
  tests/test_graph_authoring_overlay_projection_merge.py \
  tests/test_live_graph_gold_review_api.py \
  -q -k "direction or adjacency or suggested or projection or reusable or identity"

# Broader projection regression; baseline protocol applies
uv run pytest tests/ -q -k "union_supergraph and projection"

# Python static checks — omit unchanged optional files
uv run ruff check \
  src/graph_memory/projection/node_view.py \
  src/graph_memory/projection/__init__.py \
  tests/test_graph_memory_projection_contract.py \
  tests/test_live_union_supergraph_projection_adapter.py \
  tests/test_graph_memory_union_projection_identity_redirects.py \
  tests/test_live_union_supergraph_projection_api.py \
  tests/test_graph_authoring_overlay_projection.py \
  tests/test_graph_authoring_overlay_projection_merge.py \
  tests/test_live_graph_gold_review_api.py

# Frontend contract and focused consumers
cd apps/live-control-ui
npm test -- \
  src/graphObjectCard/buildGraphObjectCardFromNodeView.test.ts \
  src/planSurface/graphPreview/UnionSupergraphRecapProjection.test.tsx \
  src/planSurface/graphPreview/recapNodePresentation.test.ts \
  src/planSurface/graphPreview/RecapGraphModule.test.tsx
npm run typecheck
```

If an optional allowlisted file is unchanged or absent, omit it from the command and record that fact. Do not make an empty change merely to satisfy a copied command.

### Required exact assertions

At minimum, automated evidence must prove:

- fixture `base_sha` and `fixture_parent_sha` equal the actual pre-change generation base;
- fixture-only commit precedes all production edits;
- base fixture contains both legacy and already-closed direction leaves;
- `normalize_graph_projection_relationship_direction(outbound) == outgoing`;
- `outgoing` remains `outgoing`;
- `inbound` becomes `incoming`;
- `incoming` remains `incoming`;
- `related` remains `related`;
- `None`, empty, and whitespace become `related` at direct model/normalizer ingress;
- unknown non-empty and non-string inputs fail closed;
- Python field annotation is the closed `Literal` family;
- every serialized Union adjacency direction is closed;
- every serialized Union suggested-expansion direction is closed;
- a canonical source/target edge yields `outgoing`/`incoming` respectively;
- store-adjacency precedence and edge dedup remain exact;
- fallback source default and target `incoming` behavior remain exact;
- reusable legacy projection payload validates and serializes closed values;
- reusable source payload/artifact is not rewritten;
- recursive full-payload diff contains only expected direction paths;
- adjacency order, expansion order/rank/reason, node order, focus, evidence, mentions, Markdown, source spans, and identity diagnostics remain exact;
- Gold projection still emits only closed values with exact payload behavior;
- authored-overlay relationships still emit only closed values with exact payload behavior;
- TypeScript union-compatible direction rejects `outbound`/`inbound` at compile time;
- `unionSupergraphFixture.ts` contains no legacy direction values;
- healthy Union fixture relationships become non-null card directions;
- defensive unknown runtime direction still becomes `null` in the card helper;
- no frontend translation branch maps `outbound`/`inbound`;
- raw store models and raw producer files are absent from the production diff;
- World Graph production files are absent from the diff and focused tests remain baseline;
- endpoint valid responses contain no direction outside the closed set.

### Source guards

Add focused source/AST/type assertions only where they harden the contract without coupling tests to formatting. Required guards should prove:

- the mapping alias dict is not duplicated in `node_view.py`;
- the wrapper calls `normalize_world_graph_relationship_direction`;
- `GraphProjectionAdjacencyCandidate.direction` is not plain `str`;
- TypeScript `GraphProjectionAdjacencyCandidate.direction` is not plain `string`;
- no `outbound`/`inbound` translator is introduced in Union frontend production paths;
- denylisted World/raw-storage production paths are absent from the diff.

Do not assert that the entire repository contains no `outbound` or `inbound`.

### Endpoint proof

For a valid deterministic Union projection response, recursively walk:

```text
node_views.*.adjacency[*].direction
node_views.*.suggested_expansions[*].direction
```

Assert every value belongs to `{outgoing, incoming, related}`.

Also assert at least one relationship exists so a vacuous empty response cannot pass.

### Baseline failure protocol

PR #423 encountered four manifest-path API tests that failed identically on its base and head. That waiver does not automatically carry into this slice.

If any required command is nonzero:

1. run the exact command at the merge base in a clean worktree;
2. record base/head exit codes and counts separately;
3. compare exact failing test IDs and error classes/messages;
4. prove zero new failures;
5. never call a nonzero command green;
6. obtain an explicit operator waiver for this slice if a hard gate remains red;
7. record whether the failure is the same manifest-path quartet or a new failure.

A waiver from PR #416 or PR #423 is context, not authorization.

### Manual/dogfood proof

No new product screen is authorized. Manual proof is limited to the existing endpoint and existing object-card path.

Use a deterministic fixture or verified run containing:

- one source-side relationship originating from raw `outbound`;
- one target-side/inbound relationship;
- at least one suggested expansion;
- one non-focus relationship if available.

Request:

```http
GET /api/live/graph-preview/union-supergraph/projection
```

Record:

- request identity and store/run artifact;
- response status;
- exact relevant direction paths/values;
- confirmation no legacy value appears in the response;
- one returned node passed through the existing card builder with non-null direction.

Do not paste campaign-private prose when a synthetic fixture proves the same contract. Manual proof does not replace automated evidence.

## §8 Required implementation handback and PR-body ledger

The PR description must remain synchronized with the handoff and include:

- exact base SHA, head SHA, and merge-base SHA;
- fixture commit SHA and first production commit SHA, with ordering proof;
- actual changed-path list and any bounded-discovery exception;
- full producer/consumer classification;
- count of characterization cases by family and category;
- exact base legacy direction paths and head normalized values;
- recursive diff proof showing only direction leaves changed;
- exact normalizer location, wrapper behavior, and delegated World helper;
- proof the shared model covers live construction and reusable payload validation;
- Python and TypeScript closed-type proofs;
- Gold and authored-overlay regression results;
- frontend fixture/card results and confirmation no translator was added;
- every §7 command, exit code, counts, and provenance;
- baseline comparison and explicit operator waivers, if any;
- confirmation raw store/import/contribution paths are untouched;
- confirmation World Graph, mention, authoring-direction, and PR380B paths are untouched;
- stop conditions encountered;
- named successors still false.

Required contract summary:

```markdown
## Contract changes
- Python snake_case direction: str -> GraphProjectionRelationshipDirection
- TypeScript snake_case direction: string -> GraphProjectionRelationshipDirection
- Legacy aliases: outbound -> outgoing; inbound -> incoming
- Empty/whitespace model ingress: -> related
- Unknown non-empty: fail closed
- Normalization owner: GraphProjectionAdjacencyCandidate pre-validator
- Raw Union store fields: unchanged
- World Graph contract: unchanged
```

Required evidence table:

```markdown
| Guarantee | Command/proof | Exit | Result | Provenance |
|---|---|---:|---|---|
```

Do not say “all outbound was removed.” The correct statement is:

> Union projection wire output is closed; lower-layer Union store and contribution vocabulary remains raw by design.

## §9 Reviewer rubric

A reviewer should request changes if any answer below is “no.”

### Invariant and characterization

- Was the full-payload fixture committed before production edits?
- Does fixture provenance name the actual unmodified generation base?
- Does base evidence prove the dual vocabulary rather than assuming it?
- Are unchanged cases full-payload equal?
- Are normalized-case differences limited to the exact expected direction leaf paths?
- Are collection order, ranks, IDs, focus, evidence, identity diagnostics, mentions, Markdown, and source spans exact?

### Normalization ownership

- Is there one family-owned wrapper delegating to the accepted World helper?
- Is the alias mapping table not duplicated?
- Does a before-validator normalize both live candidate construction and reusable payload validation?
- Is the Python field a closed `Literal` rather than `str`?
- Do unknown non-empty and non-string values fail closed?
- Are `None`/empty/whitespace behaviors explicitly tested?

### Union behavior

- Do store-adjacency legacy aliases serialize closed values?
- Does the edge-walk fallback preserve existing source/target/default behavior?
- Do suggested expansions inherit closed directions?
- Does one edge produce coherent source `outgoing` and target `incoming` under normal raw input?
- Are adjacency deduplication, ordering, ranking, identity, evidence, and focus unchanged?

### Reusable payloads and shared producers

- Can a reusable pre-change projection with legacy aliases still be read and normalized?
- Is the persisted artifact left immutable?
- Do Gold Graph and authored-overlay producers remain healthy without production edits?
- Does the narrowed shared model reject unknown values from every producer?

### Frontend

- Is the TypeScript snake_case direction type closed?
- Is there compile-time proof rejecting `outbound` and `inbound`?
- Is the Union fixture updated to closed vocabulary?
- Does a healthy Union fixture produce non-null object-card directions?
- Does defensive null-collapse remain for unexpected runtime input?
- Was no `outbound`/`inbound` translator added?

### Scope and boundaries

- Are World Graph production files untouched?
- Are raw Union store, preview import, reconciliation, contribution, and graph-data files untouched?
- Are mention-linker and known-entity files untouched?
- Are authored `directed`/`undirected` contracts untouched?
- Is PR380B still false?
- Are routes and public error schemas unchanged unless an operator approved a stop-condition expansion?
- Is the changed-path list entirely within the allowlist or explicitly approved?

### Evidence honesty

- Are nonzero commands reported as nonzero?
- Are base/head failures compared by exact test ID and error class?
- Is any waiver explicit for this slice rather than inherited?
- Does endpoint proof include at least one direction value?
- Does the handback distinguish wire normalization from storage migration?

## §10 Dispatch summary

The implementation should be small even though the evidence is broad:

1. commit a full-payload base characterization fixture by itself;
2. add a closed Python direction type, delegated wrapper, and before-validator to `GraphProjectionAdjacencyCandidate`;
3. narrow the matching TypeScript snake_case direction type and add compile-time rejection proof;
4. update the Union projection fixture;
5. prove live builds, reusable snapshots, Gold, authored overlay, object cards, and endpoint output all satisfy the one closed contract;
6. demonstrate that only direction leaves changed and every raw/World/mention/product boundary stayed untouched.

The central design rule is:

> Normalize when data enters the shared Union-compatible projection wire model,
> not when a particular producer or frontend happens to notice the raw value.
