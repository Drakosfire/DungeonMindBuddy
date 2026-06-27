# Graph Memory Union Supergraph Projection Design v0

Date: 2026-06-27
Status: design anchor
Workstream: Graph Memory / Union Supergraph / Recap Projection
Branch anchor: `experiment/ontology-taxonomy-ladder`
Depends on: `aabdfe4` — `feat(plan): recap artifact registry and session selector`

## 0. Purpose

This document defines the current design target for graph-backed recap projection.

The product should not stop at session-local recap graphs. The target is a shared graph substrate where recap pills resolve to global campaign/worldbuilding nodes, and session projection is only a scoped lens over that larger graph.

Primary proof:

```text
While reviewing Session 23, hover Caelynn, see a useful Caelynn node description, click Caelynn, open global pc_caelynn, see Session 23-anchored evidence highlighted, and continue graph navigation across all reachable Caelynn edges from campaign and worldbuilding sources.
```

## 1. Core Design Statement

The graph being navigated is not a session graph.

It is the union of at least two conceptual supergraphs:

```text
Campaign supergraph
+ Worldbuilding supergraph
= unified campaign/world graph substrate
```

The physical implementation may be one file-backed store at v0. The conceptual model must already allow multiple source domains and future artifact families.

The recap reader is a projection over that graph.

A recap mention is not the node. A recap mention resolves to a global node.

## 2. User Stories

### 2.1 Session recap projection story

```text
As GM reviewing a specific session recap,
I want entity pills to be linked to global graph nodes,
so that the recap is an entry point into campaign memory rather than a closed session artifact.
```

### 2.2 Caelynn all-of-node story

```text
As GM reviewing Session 23,
when I click Caelynn,
I want to see all known Caelynn graph context across sessions and worldbuilding artifacts,
while still knowing which facts/edges are specifically anchored to Session 23.
```

### 2.3 Unbounded graph navigation story

```text
As GM exploring from Caelynn,
I want to follow edges to adjacent nodes without being restricted to the current session,
so that I can move naturally from a recap mention to the broader campaign/world context.
```

### 2.4 Multi-artifact ingestion story

```text
As the system ingests future artifacts,
recaps, statblocks, worldbuilding docs, NPC notes, locations, factions, items, session memory, and future artifact types should all contribute evidence-backed nodes and edges to the same graph substrate.
```

## 3. Non-Goals

This design does not authorize:

```text
canon promotion
approved memory writes
corpus mutation
production retrieval changes
Agent Interaction integration
opaque identity merging
hand-authored Session 23 graph proof
category_graph_model_study as the durable graph store
session-local projection snapshots as the long-term graph model
```

The v0 graph substrate may be file-backed and inspectable. That does not make it canon or approved memory.

## 4. Current System Context

The current bridge layer provides:

```text
recap artifact registry
campaign/session selector
graph-run selector
recap-only fallback
recap markdown pill rendering
node hover card
node pin panel
```

The current APIs can return a `RecapGraphPresentationResponse` with:

```text
markdown
nodes
links
```

That is sufficient to render pills and hover cards.

It is not sufficient to support all-of-node graph navigation, because it does not yet provide a global graph node view, adjacency, source-domain distinctions, or session-focus overlays.

## 5. Target Graph Model

### 5.1 One shared graph with scope metadata

Prefer one shared graph substrate with metadata over physically separate campaign/worldbuilding stores.

Reason:

```text
Caelynn, Mireward, Lysandra, factions, threats, items, and locations naturally straddle campaign events and worldbuilding docs. Separate stores would encourage duplicate identities and brittle merge behavior.
```

Use metadata to mark origin and scope.

### 5.2 Source domains

Every node/edge/fact/evidence record should be able to report source domain.

Initial source domains:

```text
recap
statblock
worldbuilding
npc_note
location_note
faction_note
item_note
session_memory
manual_seed
future_artifact
```

### 5.3 Session focus

A session recap projection should carry a focus session.

For Session 23:

```text
focus_session_id = session-23
```

The global node view should distinguish:

```text
anchored_to_focus_session = true
anchored_to_focus_session = false
```

This is a display/filtering concern, not a graph identity split.

## 6. Proposed File-Backed v0 Store

Use a file-backed store initially, but model it as a graph store/read model.

Suggested path:

```text
evals/graph_memory_layer/union_supergraph/longmont-c2/graph_store.json
```

Suggested schema:

```json
{
  "schema": "dmb_union_supergraph_store_v0",
  "version": "0.1",
  "campaign_id": "longmont-c2",
  "graph_id": "longmont-c2:union-supergraph",
  "graph_domains": ["campaign", "worldbuilding"],
  "source_domains": ["recap", "statblock", "worldbuilding", "session_memory"],
  "nodes": {},
  "edges": {},
  "evidence": {},
  "aliases": {},
  "source_artifacts": {},
  "diagnostics": {
    "canon_promotion": false,
    "corpus_mutation": false,
    "production_retrieval": false
  }
}
```

Use maps by ID for v0 so node/edge lookup is simple and deterministic.

## 7. Node Contract

Suggested node shape:

```json
{
  "node_id": "pc_caelynn",
  "label": "Caelynn",
  "kind": "pc",
  "role": "pc",
  "description": "Player character connected to the Mireward siege arc.",
  "aliases": ["Caelynn"],
  "source_domains": ["recap", "session_memory"],
  "first_seen_session_id": "session-1",
  "last_seen_session_id": "session-23",
  "evidence_ref_ids": ["evidence:session-23:caelynn:p014"],
  "state": {
    "memory_state": "graph_read_model",
    "canon_state": "not_canon_promotion",
    "approval_state": "not_approval_write"
  }
}
```

The node is global. Session references are attributes/evidence, not identity boundaries.

## 8. Edge Contract

Suggested edge shape:

```json
{
  "edge_id": "edge:pc_caelynn:participated_in:event_session_23_mireward_gate",
  "source_node_id": "pc_caelynn",
  "target_node_id": "event_session_23_mireward_gate",
  "predicate": "participated_in",
  "label": "participated in",
  "direction": "outbound",
  "source_domains": ["recap"],
  "session_ids": ["session-23"],
  "evidence_ref_ids": ["evidence:session-23:caelynn:p014"],
  "state": {
    "canon_state": "not_canon_promotion",
    "approval_state": "not_approval_write"
  }
}
```

Edges may be session-anchored, worldbuilding-anchored, or both.

## 9. Evidence Contract

Suggested evidence shape:

```json
{
  "evidence_ref_id": "evidence:session-23:caelynn:p014",
  "source_artifact_id": "source:longmont-c2:session-23:recap",
  "source_domain": "recap",
  "source_span_ref_id": "spref:session-23:p014",
  "session_id": "session-23",
  "evidence_role": "mention",
  "can_open_source": true,
  "can_highlight_span": true
}
```

Evidence should preserve the existing source-span/ref behavior. The union graph should not erase span-level provenance.

## 10. Source Artifact Contract

Suggested source artifact shape:

```json
{
  "source_artifact_id": "source:longmont-c2:session-23:recap",
  "source_domain": "recap",
  "campaign_id": "longmont-c2",
  "session_id": "session-23",
  "uri": ".../Session 23 ...md",
  "ingest_run_bundle_uri": ".../runs/live_recap_ingest/...",
  "source_span_index_uri": ".../source_span_index.json",
  "provenance_index_uri": ".../provenance_index.json",
  "source_sha256": "..."
}
```

Future source artifacts can represent statblocks, worldbuilding docs, NPC notes, location docs, and item/faction docs.

## 11. Recap Projection Contract

The recap projection should not build a session graph. It should build links into the union supergraph.

Suggested projection flow:

```text
load recap artifact record
load source recap + span index
load union supergraph
resolve mentions/aliases in this recap against global nodes
emit markdown dmb-node links
emit visible nodes referenced in this recap
emit focus_session_id
emit adjacency/global node summaries as needed
```

The response should indicate the graph source:

```json
{
  "graph_source": {
    "kind": "union_supergraph",
    "graph_uri": "evals/graph_memory_layer/union_supergraph/longmont-c2/graph_store.json",
    "focus_session_id": "session-23"
  }
}
```

## 12. Global Node View Contract

Clicking a pill should open a global node view, not a session-local record.

Suggested endpoint shape:

```text
GET /api/live/graph-preview/node?campaign_id=longmont-c2&node_id=pc_caelynn&focus_session_id=session-23
```

Suggested response:

```json
{
  "schema": "dmb_union_graph_node_view_v0",
  "node": {},
  "focus_session_id": "session-23",
  "facts": [],
  "edges": [],
  "adjacent_nodes": [],
  "evidence": {},
  "counts": {
    "focus_session_edge_count": 3,
    "all_edge_count": 18
  }
}
```

For v0, this can also be embedded in the recap presentation payload if that is simpler.

## 13. UI Behavior

The UI should support:

```text
hover pill → session-relevant global node summary
click pill → pin/open global node
pinned node panel → show all-of-node summary
session-focused badge → highlight Session 23 edges/facts
connected nodes list → allow click-through to adjacent global nodes
```

No force-directed graph visualization is required for v0.

No runtime graph query is required for v0.

## 14. Compatibility With Current Graph Runs

`category_graph_model_study` artifacts are useful dogfood/eval artifacts.

They are not the durable source of truth.

The new graph read model may ingest or convert outputs from existing extractor/materializer CLIs, but `/plan` should eventually prefer the union supergraph store over raw category study run dirs.

## 15. Next Implementation Slice

Recommended PR:

```text
graph-memory: add union supergraph projection contract v0
```

Acceptance target:

```text
Session 23 recap pills resolve into union graph nodes.
Caelynn resolves to global pc_caelynn.
Clicking Caelynn opens all-of-Caelynn node view.
Session 23-specific facts/edges are highlighted.
At least one non-Session-23 or non-recap edge/source can be represented by the same node contract, even if the fixture is small.
```

Do not satisfy this with a hand-authored session-local graph snapshot.

## 16. Open Design Questions

1. Should the v0 graph store be one JSON file or split into nodes/edges/evidence/source indexes?
2. Should global node view be a new endpoint or embedded in `RecapGraphPresentationResponse`?
3. What exact fields should represent source domains and focus-session anchoring?
4. How should route-seed/breadcrumb entities contribute aliases without becoming separate nodes?
5. When the same entity appears in recap and worldbuilding sources, what reconciliation confidence is required before merging?
6. How should the UI distinguish “Session 23 evidence” from “all Caelynn evidence” without hiding either?
7. How much of the existing extractor/materializer output should be converted into the union graph store in the first slice?

## 17. One-Sentence Orientation

Build the shared campaign/worldbuilding graph substrate that recap pills resolve into; Session 23 is only the focused entry point, and Caelynn must open as a global graph node with Session 23 evidence highlighted, not as a hand-authored session-local projection node.
