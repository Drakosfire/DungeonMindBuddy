# HANDOFF — Union Supergraph Projection Spike Checklist v0

> **COMPLETED — 2026-06-28T00:17:49Z.** The follow-on model-contract slice shipped via PR #199 (`eb0649146aa150bc25c21ffc66fffaa8c75dadda`). It adds typed union-supergraph DTO/load seams, preserves graph-level validation/report behavior, extends focused model tests, and records the model/load seam in the supergraph roadmap. Non-blocking follow-ups: decide whether typed node/edge state DTOs should replace `dict[str, Any]`, and add explicit alias-serialization assertions if DTOs become an interchange format. **Archived for historical reference; do not re-dispatch.**


Layout boundary: `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md` records that reusable graph-memory contracts live in `src/graph_memory`, deterministic contract fixtures live in `tests/fixtures/graph_memory`, and `evals/graph_memory_layer` remains evaluation/dogfood territory.

Status: planning checklist
Workstream: Graph Memory / Union Supergraph / Recap Projection
Mode: docs-only guardrail for the next implementation spike
Recommended next PR: `graph-memory: add union supergraph read model fixture v0`

## 1. User story

The next implementation spike must stay grounded in the Session 23 Caelynn global-node story:

```text
As GM reviewing Session 23,
when I hover a Caelynn pill,
I see the Session 23-relevant projection of global pc_caelynn.

When I click Caelynn,
I open global pc_caelynn.

The panel/view shows all known Caelynn context across the campaign/worldbuilding graph,
while clearly marking which facts and edges are anchored to Session 23.

From Caelynn, I can continue clicking adjacent nodes without being restricted to Session 23.
```

The target is not another session-local Session 23 graph snapshot. Recap projection is a session-scoped lens into a larger campaign/worldbuilding union supergraph.

## 2. Architecture anchor

Authoritative starting points:

- `Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md`
- `Docs/Design/GRAPH-MEMORY-UNION-SUPERGRAPH-PROJECTION.md`
- `Docs/Design/GRAPH-MEMORY-LIVE-EXTRACTOR-PROMPT-HARNESS.md`

Supporting context:

- `Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md`
- `Docs/Design/GRAPH-MEMORY-CANDIDATE-GRAPH-PREVIEW-IR.md`
- `Docs/Design/GRAPH-MEMORY-MULTI-PASS-EXTRACTION-CONTRACT.md`
- `Docs/Design/GRAPH-MEMORY-PREVIEW-GRAPH-UX-DESIGN-SPEC.md`
- `Docs/Design/GRAPH-MEMORY-QUERY-VOCABULARY-FIXTURE.md`

## 3. Existing bridge layer

Current bridge shape:

```text
recap artifact
→ registry record
→ optional graph run refs
→ recap projection payload
→ pills/hover/pin
```

Useful existing capabilities:

- recap artifact registry
- campaign/session selector
- graph-run selector
- recap-only fallback
- graph-aware markdown pill rendering
- node hover card
- node pin panel

Missing target capabilities:

- campaign/worldbuilding union supergraph store
- global node view
- all-of-node graph navigation
- source-domain metadata across artifact families
- session-focus overlays over global graph
- adjacency traversal beyond the current recap/session

Target shape:

```text
source artifacts
→ ingestion/extraction/materialization
→ reconciled global nodes and edges
→ campaign/worldbuilding union supergraph
→ session recap projection as focused lens
→ pills resolve to global nodes
→ click node opens all-of-node navigation
```

## 4. Non-goals

Do not use the next spike for:

- backend runtime graph engine implementation
- frontend graph navigation build-out
- schema migration
- production retrieval changes
- extractor prompt changes
- another selector-only UI pass
- another prompt harness as the main deliverable
- hand-authored Session 23 graph proof artifacts
- treating `category_graph_model_study` run dirs as the durable graph store

If code scope starts expanding beyond an inspectable read-model fixture and validator/report, stop and write a narrower follow-up handoff.

## 5. Spike decisions

Before writing code, the next implementation PR must answer:

1. **What is the v0 union supergraph storage shape?**
   - one JSON file?
   - split nodes/edges/evidence/source indexes?
   - file-backed now, DB later?
2. **What is a global node view payload?**
   - node
   - facts
   - edges
   - adjacent nodes
   - evidence
   - focus-session badges
3. **How does a recap projection resolve mentions?**
   - alias lookup against global nodes
   - route seeds as alias hints
   - extractor/materializer output as candidate assertion source
4. **How is Session 23 focus represented?**
   - `focus_session_id`
   - `anchored_to_focus_session` boolean
   - `session_ids` on evidence/edges
   - UI badge model
5. **How are source domains represented?**
   - recap
   - statblock
   - worldbuilding
   - npc_note
   - location_note
   - faction_note
   - item_note
   - session_memory
   - future_artifact
6. **What is the smallest proof of global navigation?**
   - Caelynn resolves to global `pc_caelynn`
   - at least one Session 23 edge can be represented
   - at least one non-Session-23 or non-recap edge/source can be represented
   - adjacency click-through is possible in contract, even if UI is minimal

## 6. First implementation spike shape

Recommended next code PR:

```text
graph-memory: add union supergraph read model fixture v0
```

Probable mission:

```text
Define a file-backed union supergraph fixture/read model and a validator/report that proves the graph can represent global nodes, source domains, evidence refs, focus-session overlays, and adjacency traversal without changing runtime behavior.
```

Likely files for that later PR, not this checklist PR:

```text
tests/fixtures/graph_memory/union_supergraph/longmont_c2_minimal_graph.json
src/graph_memory/union_supergraph/validate.py
src/graph_memory/union_supergraph/report.py
tests/test_graph_memory_union_supergraph.py
```

## 7. Acceptance criteria for the next code PR

The first implementation spike should prove:

- the graph is a campaign/worldbuilding union supergraph, not a session-local graph
- global `pc_caelynn` can carry facts, edges, aliases, evidence, and source domains
- Session 23 focus can be represented without splitting Caelynn identity
- at least one Session 23-specific edge/evidence item is distinguishable from broader graph context
- at least one non-Session-23 or non-recap source can contribute to the same global node or adjacency set
- a global node view payload can support all-of-node navigation and adjacent-node click-through in contract
- validation/reporting can run without live LLM calls, corpus mutation, canon promotion, or runtime behavior changes

## 8. Files to inspect

Before changing code, inspect the current bridge layer:

```text
apps/live_control_server/services/recap_artifacts.py
apps/live_control_server/services/graph_preview_surface.py
apps/live_control_server/routes/graph_preview.py

apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx
apps/live-control-ui/src/planSurface/graphPreview/RecapGraphProjection.tsx
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts

evals/graph_memory_layer/live_recap_ingest_run_bundle.py
evals/graph_memory_layer/live_extractor_prompt_harness.py
```

## 9. Tests to add/extend later

Likely test references for the later code PR:

```text
tests/test_recap_artifacts.py
tests/test_live_graph_preview_surface.py
tests/test_graph_memory_live_extractor_prompt_harness.py
apps/live-control-ui/src/planSurface/graphPreview/recapSessionLabels.test.ts
```

For the read-model fixture spike, prefer a new focused test such as:

```text
tests/test_graph_memory_union_supergraph.py
```

## 10. Safety boundaries

This checklist does not authorize:

- corpus mutation
- canon promotion
- approved memory writes
- production retrieval changes
- Agent Interaction integration
- opaque identity merging
- session-local graph as final architecture
- hand-authored Session 23 graph as proof
- `category_graph_model_study` as durable graph store
- live LLM calls in CI

The graph may become a read model. It is not approved canon.
