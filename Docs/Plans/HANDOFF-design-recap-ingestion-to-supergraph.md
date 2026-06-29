---
document_id: dmb-handoff-design-recap-ingestion-to-supergraph
title: Handoff - Design Recap Ingestion Into Union Supergraph
status: ready_for_design_agent
version: 0.1
created_at: "2026-06-28"
branch_anchor: experiment/ontology-taxonomy-ladder
head_anchor: 5a9009e feat(plan): chip explorer with ranked suggested expansions
audience: designing_agent
source_role: dogfooding_agent
related_documents:
  - path: Docs/Plans/REPORT-recap-ingestion-dogfood-evaluation-v0.md
    role: prior_dogfood_evaluation
  - path: Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md
    role: architecture_roadmap
  - path: Docs/Design/GRAPH-MEMORY-UNION-SUPERGRAPH-PROJECTION.md
    role: projection_design_anchor
  - path: Docs/Design/GRAPH-MEMORY-CANDIDATE-GRAPH-PREVIEW-IR.md
    role: preview_ir_contract
  - path: Docs/Design/GRAPH-MEMORY-MULTI-PASS-EXTRACTION-CONTRACT.md
    role: extraction_contract
  - path: Docs/Design/GRAPH-MEMORY-LIVE-EXTRACTOR-PROMPT-HARNESS.md
    role: prompt_harness_record
  - path: Docs/Design/RESEARCH-graph-visualization-exploration.md
    role: graph_visualization_research
---

# Handoff - Design Recap Ingestion Into Union Supergraph

## 0. Mission For The Designing Agent

Design the next graph-memory dogfood slice: replace the current recap-ingestion toolbar's center of gravity with a streamlined flow that ingests a recap the system has never seen, extracts graph candidates with the multi-pass GPT mini workflow, imports the result into the union supergraph, and projects the newly added graph context through the recap chips.

The next dogfood handoff is ready only when the design is concrete enough to build this product loop:

```text
unknown recap
-> human-friendly ingest flow
-> normalized source with resolvable spans
-> multi-pass graph extraction
-> validated candidate graph
-> preview-only union-supergraph import
-> recap chips resolve to new/global graph nodes
-> GM can explore the result and trust the evidence
```

The user-facing bar is not "the CLI produced artifacts." The bar is:

```text
I can paste or select a new recap, the system confidently tells me what it understood, the supergraph grows in preview form, and the recap chips make that new memory visible and explorable.
```

## 1. Current State Hypothesis

The system has three working but not yet unified pieces.

First, `/plan` has a toolbar ingestion tool. `IngestionModule` calls `/api/live/recap-ingest` with command-style operations: `stage_preview`, `apply_normalize`, `build_frontmatter_seed`, `run_breadcrumb_ingest`, `materialize_session_memory`, `inspect_status`, and `reconcile_normalized_recap`. This is a deterministic recap/corpus/session-memory workflow. It is useful plumbing, but it is not yet graph ingestion.

Second, graph extraction exists as dogfood/eval infrastructure. `evals/graph_memory_layer/category_graph_model_study.py` runs category passes for actors, locations, collectives, objects, threads, beats, and edges, then writes `candidate_output.json`, `pass_outputs.json`, `pass_telemetry.json`, `validation_report.json`, `comparison_report.json`, and `run_summary.json`. This is the multi-pass GPT mini workflow the user is referring to, but it is still CLI/eval-shaped and has Session 22 assumptions.

Third, union-supergraph projection now has a real product-facing foothold. The latest landed work added ranked `suggested_expansions`, enriched evidence/adjacency fields, and an explicit chip explorer trail. The recap projection UI can now treat chips as graph-navigation entry points rather than metadata badges.

The missing design is the bridge:

```text
toolbar ingest operation
-> fresh live recap graph-extraction job
-> candidate graph validation
-> union-supergraph preview import
-> projection endpoint resolves this new run
-> chip explorer dogfoods the result
```

## 2. Why This Matters

Earlier dogfood concluded: "Nothing yet as a GM is useful here." The artifact wrapper and diagnostics proved safety boundaries, but not GM value.

The current chip explorer changes that. We now have a plausible GM-facing projection surface:

- inline recap pills for graph mentions
- hover cards with planning context
- click-to-open explorer
- current-session versus prior-context evidence split
- ranked suggested expansions for graph crawling

That means the next meaningful dogfood is no longer a report. It is a first-time recap ingest that lands in the chip explorer.

## 3. Canonical Product Goal

Design toward this concrete dogfood story:

```text
As GM, I provide a recap the system has never seen.

The ingest flow stages and normalizes it without making unsafe canon claims.

The graph extractor runs multiple focused passes using GPT mini and source-span evidence.

The system validates the candidate graph, shows any hard failures in normal language,
and imports valid preview candidates into the union supergraph.

The recap projection then renders chips for the extracted nodes.

When I click a chip, I see a useful node explorer that proves:
  - this came from the new recap,
  - this has resolvable evidence,
  - this connects to existing graph context where identity is known,
  - this is still preview/candidate state unless explicitly approved.
```

The next dogfood handoff should not be emitted until the design can name the exact API operations, artifact records, status states, validation gates, projection resolution rules, and UI review moments needed to make that story real.

## 4. What Is Already Proven

### 4.1 Recap intake and deterministic materialization

Relevant files:

```text
apps/live-control-ui/src/modules/IngestionModule.tsx
apps/live-control-ui/src/api/recapIngestApi.ts
apps/live_control_server/routes/recap_ingest.py
src/live_play/recap_ingest_pipeline.py
src/live_play/recap_ingest_status.py
src/live_play/recap_stage_paths.py
```

Existing capability:

- raw recap text can be staged
- canonical recap preview can be assembled
- canonical recap can be applied with slug/title safety
- normalized recap can be created or reused
- duplicate normalized candidates can be detected and reconciled
- frontmatter seed and breadcrumb ingest are modeled as explicit stages
- session memory materialization is recognized as a planning-activation boundary

Design caution:

This flow contains some one-off dogfood scars, including Session 22 slug sanitization logic in the frontend. The designing agent should not preserve those as architecture.

### 4.2 Multi-pass graph extraction

Relevant files:

```text
evals/graph_memory_layer/run_category_graph_model_study.py
evals/graph_memory_layer/category_graph_model_study.py
evals/graph_memory_layer/live_recap_ingest_run_bundle.py
evals/graph_memory_layer/reconcile_live_candidate.py
src/graph_memory/candidate_graph_preview.py
src/graph_memory/identity_resolution.py
src/graph_memory/anchor_quotes.py
```

Existing capability:

- source-spanned run bundles can be created from normalized recaps
- prompts can use source packets with stable `source_span_ref_id` values
- category passes decompose extraction into smaller model jobs
- edge pass runs after node consolidation
- output can be reconciled into a canonical candidate envelope
- anchor quotes can be validated or repaired
- artifacts record pass telemetry and validation state

Design caution:

The runner is still proving-slice shaped. It is hardcoded around Session 22 in important paths and comparison behavior. It must become a reusable service-layer operation before it belongs behind the toolbar.

### 4.3 Union-supergraph projection and chip explorer

Relevant files:

```text
src/graph_memory/union_supergraph/model.py
src/graph_memory/union_supergraph/load.py
src/graph_memory/union_supergraph/validate.py
src/graph_memory/union_supergraph/preview_import.py
src/graph_memory/projection/recap_projection.py
src/graph_memory/projection/node_view.py
apps/live_control_server/services/union_supergraph_projection_adapter.py
apps/live_control_server/routes/graph_preview.py
apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx
apps/live-control-ui/src/planSurface/graphPreview/UnionSupergraphRecapProjection.tsx
apps/live-control-ui/src/planSurface/graphPreview/GraphNodePresentation.tsx
apps/live-control-ui/src/planSurface/graphPreview/recapNodePresentation.ts
```

Existing capability:

- candidate graph outputs can be converted into a preview-only `UnionSupergraphStore`
- projections expose node views, focus overlays, evidence badges, adjacency, and suggested expansions
- `/plan` can render a union-supergraph recap projection
- recap chips can open an explorer and crawl ranked adjacent nodes

Design caution:

The current union projection adapter still uses hardcoded dogfood sources for preview mode. It does not yet resolve "the graph run produced by the current toolbar ingest."

## 5. Dominant Design Problem

The dominant failure mode to design against is a split-brain pipeline:

```text
recap ingest creates canonical/session-memory artifacts
graph extractor creates eval artifacts
union-supergraph preview reads hardcoded artifacts
chips render a demo projection
```

That would make every piece "work" while the product loop remains fake.

The design must replace that with one traceable artifact lineage:

```text
input recap
-> normalized recap path / hash
-> source-span run bundle
-> graph extraction run
-> validation report
-> preview union-supergraph fragment/store
-> projection payload
-> chip explorer UI
```

The GM must be able to trust the lineage without reading JSON files.

## 6. Recommended Design Shape

### 6.1 Keep deterministic source preparation, but change the destination

Do not throw away the existing recap ingest flow. The source preparation stages are still valuable:

- raw text staging
- canonical recap preview
- apply/normalize
- duplicate detection
- staging-only guardrails
- safe path handling

But the flow should stop treating `materialize_session_memory` as the main success endpoint. For graph-memory dogfood, the main endpoint should become:

```text
graph_preview_ready_for_review
```

Session memory materialization may remain a parallel/legacy stage, but it should not be the primary proof that graph ingestion worked.

### 6.2 Introduce a graph ingest backend operation set

The designing agent should define explicit operations rather than hiding everything behind "run full ingest."

Candidate operations:

```text
inspect_status
stage_preview
apply_normalize
build_source_span_bundle
run_graph_extraction
validate_candidate_graph
build_supergraph_preview
load_projection
```

The operations may live behind the existing `/api/live/recap-ingest` endpoint initially or a new graph-specific endpoint. The design needs to decide that boundary.

If reusing `/api/live/recap-ingest`, the response schema must grow beyond `dmb_raw_recap_ingest_status_v1` or introduce a graph-specific nested status. Avoid stuffing graph extraction state into generic `states` strings without typed detail.

### 6.3 Promote the category runner from CLI to service seam

The multi-pass runner needs a reusable function with explicit inputs:

```text
campaign_id
session_id
normalized_recap_path
run_bundle_dir
model_id
output_dir
comparison_mode = none | gold_if_available
```

It must not assume Session 22, S22 gold, or `session_22_category_study` paths.

The design should separate:

- source bundle creation
- pass execution
- consolidation
- validation/reconciliation
- optional gold comparison
- artifact writing

Gold comparison is eval value. Live toolbar ingestion should not require gold.

### 6.4 Treat candidate graph as proposed memory, not truth

The first integrated flow should remain preview-only. A successful extraction creates a proposed graph fragment and/or preview union store. It does not approve memory, promote canon, mutate corpus beyond explicitly applied recap artifacts, or change production retrieval.

Required states to preserve:

```text
candidate_extraction
preview_import
needs_review
not_canon_promotion
approved_memory_write = false
corpus_mutation = false
production_retrieval = false
```

### 6.5 Make the union-supergraph preview resolver session-aware

The projection endpoint needs to resolve a graph source from artifact lineage, not hardcoded constants.

Target lookup options:

```text
campaign_id + session_id
artifact_id
graph_run_uri
preview_store_uri
```

The design should say whether graph extraction writes:

1. only `candidate_output.json`, then projection builds a preview store on demand; or
2. a persisted preview union-supergraph store artifact; or
3. both.

Recommendation: persist both candidate extraction artifacts and a preview union-supergraph store artifact for dogfood. The candidate output is the model/reconciliation artifact. The preview store is the product projection artifact.

## 7. Human-Friendly Confidence Requirements

The next flow must be human-friendly and confident without being overconfident.

It should tell the GM:

- what recap was ingested
- whether the source text matched the stored normalized recap
- what model ran
- which passes completed
- whether validation passed
- how many nodes/edges/beats/deferred/ignored items were found
- whether every displayed node/edge has resolvable evidence
- whether the result is preview-only or approved
- what the next recommended action is

It should not make the GM read:

- raw `source_span_ref_id` values as the primary trust surface
- JSON artifact paths as the main success message
- internal pass dumps unless they open advanced details
- generic "ready" states without saying ready for what

## 8. UI / UX Target

The toolbar should become one guided ingestion process, not a row of equal peer buttons.

The shape should be:

```text
1. Source
   Paste/select recap, title/slug, show markdown preview.

2. Save Source
   Stage/apply/normalize with diff and duplicate guardrails.

3. Extract Graph
   Run source-span bundle + multi-pass extraction with progress by pass.

4. Review Understanding
   Show summary: nodes, edges, beats, ignored/deferred, validation warnings.

5. Explore Projection
   Open the recap chip projection backed by the just-created preview supergraph.

6. Decide Later
   Leave as preview / defer approval. Do not design canon promotion as part of this slice unless explicitly scoped later.
```

The "Review Understanding" and "Explore Projection" steps are the product proof. The dogfood should make the GM feel:

```text
Yes, that is the session I wrote, and I can see why the system believes each part.
```

## 9. Evidence And Trust Contract

Every meaningful graph object that appears in the UI needs evidence that can be opened and highlighted.

Minimum evidence contract:

```text
source_artifact_id
source_span_ref_id
line_start / line_end or equivalent span metadata
anchor_quotes or anchor_quote_matches when available
recap_source_path or resolvable source URI
session_id
```

The UI does not need to make opaque IDs human-readable. It needs to turn them into actions:

```text
Open source
Highlight exact paragraph/span
Show why this node or edge exists
```

The designing agent should explicitly define the v0 source-opening behavior for the toolbar/chip explorer. If exact highlight UI is too much for the next implementation, the design should still require the backend to prove resolvability and expose the data.

## 10. Status And Artifact Contract To Design

Define a graph-ingest status object that is strong enough for a live UI.

Suggested top-level fields:

```text
schema
campaign_id
session_id
status
source
steps[]
artifacts
health
warnings[]
errors[]
next_actions[]
projection
```

Suggested `steps[]` shape:

```text
id
label
state = locked | ready | running | complete | failed | skipped
started_at
completed_at
summary
artifact_refs[]
```

Suggested artifact refs:

```text
normalized_recap_path
run_bundle_uri
candidate_output_uri
validation_report_uri
pass_telemetry_uri
preview_union_store_uri
projection_url or projection_query
```

Suggested health fields:

```text
canonical_ir_valid
preview_import_valid
node_count
edge_count
beat_count
ignored_count
deferred_count
evidence_ref_count
resolvable_evidence_ref_count
model_id
estimated_cost_usd
```

## 11. Open Design Decisions

The designing agent should answer these before implementation handoff:

1. **Endpoint boundary:** extend `/api/live/recap-ingest` or create `/api/live/graph-ingest`?
2. **Execution model:** synchronous request, foreground long request, local job registry, or fire-and-poll?
3. **Artifact lineage:** how does a normalized recap become linked to a graph run and preview union store?
4. **Registry update:** should `recap_artifacts.py` own graph run refs for live ingests, or should graph ingest have a sibling registry?
5. **Projection resolution:** should the union projection endpoint load by `session_id`, `graph_run_uri`, `preview_store_uri`, or `artifact_id`?
6. **Comparison mode:** how is gold comparison disabled for fresh unknown recaps while preserving validation?
7. **Model policy:** which model role should resolve the GPT mini extractor model, and how does it use `MODEL_POLICY.json` instead of hardcoded strings?
8. **Pass progress:** what is the minimum progress detail the UI needs to feel alive and debuggable?
9. **Evidence opening:** what is the smallest end-to-end source span open/highlight proof?
10. **Approval boundary:** what review state is stored now if canon promotion remains out of scope?
11. **Failure recovery:** what can the GM retry: one pass, full extraction, source normalization, preview import?
12. **Duplicate/staging guardrails:** how do existing recap-ingest duplicate and staging-only protections carry into graph ingest?

## 12. Non-Goals For The Next Design

Do not design the next slice as:

- a full graph database migration
- approved graph memory writes
- production retrieval activation
- Agent Interaction answer generation
- a general graph visualization canvas
- a new prompt benchmark report only
- a static demo over hardcoded Session 22/23 artifacts
- a replacement for all breadcrumb/session-memory machinery

Those may come later. The immediate dogfood goal is narrower and stronger: one never-seen recap becomes a preview supergraph projection visible through chips.

## 13. Suggested Next Dogfood Milestone

The next dogfood handoff should be created when the designing agent can specify this exact build slice:

```text
Fresh Recap -> Preview Supergraph -> Chip Projection
```

Acceptance criteria for that future implementation slice:

- A recap not already present in the graph artifact registry can be ingested from the toolbar.
- The flow creates or reuses a normalized recap with clear title/slug safety.
- The flow creates a source-span run bundle for that recap.
- The flow runs the multi-pass graph extractor with a GPT mini model selected through policy.
- The flow validates the candidate graph without requiring gold comparison.
- The flow writes durable local artifacts for candidate output, telemetry, validation, and preview union-supergraph store.
- The flow exposes a status response understandable in the toolbar.
- The union projection endpoint can load the preview store for that new recap/session.
- The recap projection renders graph chips from that newly generated graph context.
- Clicking chips opens the explorer with evidence badges and suggested expansions.
- The UI clearly marks the result as preview/candidate, not approved canon.
- At least one node or edge evidence item can be opened or proven resolvable back to the source recap span.

## 14. Files The Designing Agent Should Inspect First

Read in this order:

```text
Docs/Plans/REPORT-recap-ingestion-dogfood-evaluation-v0.md
Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md
Docs/Design/GRAPH-MEMORY-UNION-SUPERGRAPH-PROJECTION.md
Docs/Design/GRAPH-MEMORY-CANDIDATE-GRAPH-PREVIEW-IR.md
Docs/Design/GRAPH-MEMORY-MULTI-PASS-EXTRACTION-CONTRACT.md
Docs/Design/GRAPH-MEMORY-LIVE-EXTRACTOR-PROMPT-HARNESS.md

apps/live-control-ui/src/modules/IngestionModule.tsx
apps/live_control_server/routes/recap_ingest.py
src/live_play/recap_ingest_pipeline.py

evals/graph_memory_layer/run_category_graph_model_study.py
evals/graph_memory_layer/category_graph_model_study.py
evals/graph_memory_layer/live_recap_ingest_run_bundle.py
evals/graph_memory_layer/reconcile_live_candidate.py

src/graph_memory/union_supergraph/preview_import.py
src/graph_memory/projection/recap_projection.py
apps/live_control_server/services/union_supergraph_projection_adapter.py
apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx
apps/live-control-ui/src/planSurface/graphPreview/UnionSupergraphRecapProjection.tsx
apps/live-control-ui/src/planSurface/graphPreview/GraphNodePresentation.tsx
```

## 15. Verification The Future Implementation Handoff Should Require

The designing agent does not need to run these now, but the implementation handoff should include focused tests around:

```text
tests/test_live_recap_ingest_pipeline.py
tests/test_graph_memory_category_graph_model_study.py
tests/test_graph_memory_reconcile_anchor_quotes.py
tests/test_graph_memory_preview_union_supergraph_import.py
tests/test_graph_memory_projection_contract.py
tests/test_live_union_supergraph_projection_adapter.py
tests/test_live_union_supergraph_projection_api.py
apps/live-control-ui/src/planSurface/graphPreview/UnionSupergraphRecapProjection.test.tsx
```

Add new tests for:

- non-S22 graph extraction input parameterization
- graph ingest status schema
- candidate output without gold comparison
- preview union store artifact resolution by session/run
- toolbar state transitions for graph extraction
- projection loading from a newly generated preview store

## 16. Final Framing For The Designing Agent

The work is not "make the CLI available from the UI."

The work is:

```text
Turn recap ingestion into a trustworthy graph-memory product loop.
```

The CLI is evidence that the extractor can work. The toolbar is evidence that the GM can start an ingest. The chip explorer is evidence that the projection can become useful. The next design must connect those into one coherent dogfood path.

When the next implementation agent receives a handoff, they should be able to build a slice where a recap the system has never seen becomes a preview supergraph and the chips prove it.
