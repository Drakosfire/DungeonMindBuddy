# Ontology & Taxonomy Ladder Workstream

Version: 0.11
Status: active operational anchor — post-candidate-graph-preview-ir checkpoint
Workstream: Graph Memory / Ontology / Taxonomy
Branch model: isolated ladder branch family
Relationship to other work: separate from Tiptap / Markdown backend workstream

## Current Checkpoint

The workstream now has a contract proving that source refs can resolve to bounded source evidence objects with openability and highlightability flags. This enables the next candidate graph preview IR rung, because candidate nodes, edges, beats, and proposed writes can now require resolvable evidence refs.

The ladder has completed the safe foundation, first gated real-structure rungs, consumer-boundary rungs, and recap-ingestion source-family/materializer shape proofs and diagnostics:

1. Baseline case freeze
2. Taxonomy Registry v0
3. Ontology IR Schema v0
4. Ontology IR Validation Rules v0
5. Synthetic Deterministic Materializer v0
6. Materializer Report CLI v0
7. Real-Structure Materialization Gate v0
8. Session-Memory Sentence-Unit Materializer v0
9. Plan Surface Consumer Alignment
10. Shared Source Vocabulary Contract
11. Surface Vocabulary Boundary v0
12. Projection-Safe Source Unit Fixture v0
13. Projection-Readiness Report v0
14. Recap-Ingestion Source-Family Gate v0
15. Recap-Ingestion Source Artifact Fixture v0
16. Recap-Ingestion Source Artifact Materializer Gate v0
17. Recap-Ingestion Source Artifact Materializer v0
18. Recap-Ingestion Source Artifact Materializer Report v0
19. Projection-Readiness Over Materialized Recap-Ingestion Artifacts v0
20. Recap-Ingestion Source Ref / Provenance Linkage Hardening v0
21. Recap-Ingestion Projection Payload Fixture v0
22. Recap-Ingestion Explicit Real-Artifact Dogfood Fixture v0
23. Source Span Evidence Resolver Contract v0
24. Candidate Graph Preview IR v0

The project can now define graph vocabulary, represent graph records, validate graph records, reject unsafe graph bundles, materialize a tiny synthetic fixture, report materialized output, gate a first real source family, materialize explicit session-memory JSONL sentence/source-unit records into diagnostic candidate GraphBundles, define surface-safe shared source vocabulary, separate ontology-owned semantics from surface-owned interaction vocabulary, measure projection-readiness, gate recap-ingestion artifacts, prove a synthetic `SourceArtifact -> SourceAnchor -> SourceUnit` fixture for each gate-admitted recap-ingestion artifact family, decide that a future materializer may be implemented only under a strict explicit-input contract, implement the first real explicit-input recap-ingestion source artifact materializer, render richer diagnostic materializer reports, and evaluate projection-readiness over materialized recap-ingestion artifacts then harden stable source_ref_id coverage and explicit provenance-to-source-ref linkage so the default diagnostic fixture is source-ref/provenance ready, then dogfood the explicit-input materializer/projection-payload chain against one manually selected real-derived artifact bundle while preserving safety boundaries.

The default validator still uses tiny synthetic fixtures for baseline paths. No broad campaign/corpus materialization has begun; no graph output influences `/plan` or live retrieval yet; no LLM extraction, alias/entity/relationship inference, graph traversal, or corpus mutation has happened; and no production retrieval behavior has changed.

The next checkpoint is **Rich Recap Dogfood Fixture v0**.

The workstream now has a preview-only candidate graph object model with nodes, edges, beats, proposed writes, ignored/deferred items, semantic states, diagnostics, and evidence refs compatible with the source-span evidence resolver. The next backend rung should supply a richer recap dogfood fixture that can later be paired with a hand-authored gold candidate graph.

## Next Technical Checkpoint

The next technical checkpoint is `Rich Recap Dogfood Fixture v0`.

Candidate Graph Preview IR v0 is complete. The next PR should add richer dogfood recap inputs for later gold candidate graph pairing before adapter or `/plan` shadow work.

It must continue to block:

- real artifact directory scanning
- canonical corpus scanning
- corpus mutation
- `/plan` integration
- Agent Interaction integration
- graph retrieval
- shadow retrieval
- entity extraction
- alias resolution
- relationship inference
- fact promotion
- production behavior changes

## Core Decision

Ontology and taxonomy work should proceed as an isolated ladder branch family, not as scattered changes on `main` and not as a wholesale corpus rewrite.

The ladder exists to mature graph memory, taxonomy, ontology, and source-grounded retrieval structure without destabilizing the current retrieval system, canonical corpus, or Tiptap / Markdown backend workstream.

Operating frame:

- Build the ontology/taxonomy ladder as a separate experiment track.
- Keep it scaffolded, measurable, and source-grounded.
- Do not mutate canonical corpus semantics yet.
- Do not depend on Tiptap work being complete, and do not fight it.
- Treat ontology/taxonomy as a derived structure that can later consume the stable canonical document model once Tiptap lands.

## Why This Workstream Exists

DungeonBuddy already has proto-graph properties:

- source-grounded sentence units
- session memory JSONL
- route-indexed records
- breadcrumb normalization
- manifest-backed retrieval
- evidence-role distinctions
- session and campaign scoped recall
- route and hub concepts
- citation-grounded corpus architecture

Those structures are currently implicit. Routes, hubs, source spans, entities, and evidence roles behave like graph features, but they are not yet represented as a formal, inspectable, queryable ontology/taxonomy layer.

The ontology/taxonomy ladder should make that implicit structure explicit by answering:

- What are the stable concept types in DungeonBuddy?
- What are the controlled vocabularies?
- What are the allowed relationship predicates?
- What kinds of source truth exist?
- What is an entity, route, hub, session unit, location, threat, hook, or fact?
- What can be inferred, what must be source-supported, and what is merely proposed?
- How do we validate graph memory before allowing it to influence retrieval?

## Non-Goals

This workstream is not:

- a full production Graph RAG rewrite
- a replacement for current retrieval
- a corpus migration
- a Tiptap backend implementation
- an LLM-driven auto-ontology generator
- permission to mutate campaign truth
- a reason to change production retrieval modules early

In particular, early ladder work must not change `src/agent/session_memory_query.py`, `src/agent/planner_retrieval_router.py`, `src/live_play/manifest_context_query.py`, or canonical corpus files.

The ladder begins by describing and validating structure before it tries to influence retrieval.

## Plan Surface Consumer Alignment

`/plan` is now the first named future consumer for graph-memory derived structures.

The ladder remains isolated and must not be pulled into UI implementation or production retrieval. The alignment goal is to ensure the graph-memory model can later serve `/plan` through adapters without forcing `/plan` to own taxonomy, ontology, aliasing, evidence policy, lifecycle semantics, or graph traversal.

The expected adapter vocabulary is:

`source artifact -> source anchor -> source unit`

The UI should not become graph-aware. The UI should ask for source-backed, lifecycle-aware units through a stable adapter. `/plan` should consume those units without learning graph internals.

`/plan` remains the first named future consumer, but graph-backed `/plan` consumption is still blocked until materialized source artifacts are measured, reported, and explicitly promoted through later gates.

The current live-index path remains the fallback until graph-assisted retrieval is measured in shadow mode and explicitly promoted.


### Surface Vocabulary Boundary v0

Before building adapter code or graph-backed surface integration, the ladder defines which concepts must be shared globally and which remain surface-owned.

Boundary manifest:

`evals/graph_memory_layer/surface_vocabulary_boundary.json`

Validator:

`uv run python -m evals.graph_memory_layer.validate_surface_vocabulary_boundary`

Report:

`Docs/Reports/GRAPH-MEMORY-SURFACE-VOCABULARY-BOUNDARY.md`

Decision: DungeonMindBuddy should share a semantic envelope across graph memory and surfaces, not force one shared UI/ontology vocabulary. Surfaces keep interaction vocabulary such as chips, projections, drawers, and tool workflows. Graph Memory owns provenance, lifecycle, evidence role, authority, visibility, validation, and source-grounding semantics.


### Projection-Safe Source Unit Fixture v0

Before implementing adapters or graph-backed surface consumption, the ladder validates a tiny projection-safe source-unit fixture.

Fixture:

`evals/graph_memory_layer/examples/projection_safe_source_unit_minimal.json`

Validator:

`uv run python -m evals.graph_memory_layer.validate_projection_safe_source_unit`

Report:

`Docs/Reports/GRAPH-MEMORY-PROJECTION-SAFE-SOURCE-UNIT.md`

This proves shape compatibility only. It requires `source_anchor`, `source_ref`, `provenance`, `evidence_role`, `authority_state`, `visibility_state`, `lifecycle_state`, and `canon_state`. It does not implement `/plan`, Agent Interaction, adapters, graph retrieval, shadow retrieval, or production behavior.

### Projection-Readiness Report v0

After proving one static projection-safe source-unit fixture, the ladder reports whether materialized session-memory source-unit records are projection-ready.

Validator:

`uv run python -m evals.graph_memory_layer.validate_projection_readiness_report`

Report CLI:

`uv run python -m evals.graph_memory_layer.report_projection_readiness`

Human-readable report:

`Docs/Reports/GRAPH-MEMORY-PROJECTION-READINESS-REPORT.md`

This measures readiness only. It does not implement adapters, `/plan`, Agent Interaction, graph retrieval, shadow retrieval, corpus scanning, corpus mutation, or production behavior.

### Recap-Ingestion Source-Family Gate v0

After measuring projection-readiness over current session-memory source-unit output, the ladder gates whether recap-ingestion artifacts may be admitted as future source artifacts, anchors, and units.

Gate manifest:

`evals/graph_memory_layer/recap_ingestion_source_family_gate.json`

Validator:

`uv run python -m evals.graph_memory_layer.validate_recap_ingestion_source_family_gate`

Human-readable report:

`Docs/Reports/GRAPH-MEMORY-RECAP-INGESTION-SOURCE-FAMILY-GATE.md`

This gate admits explicit recap-ingestion artifacts only as source artifacts, anchors, units, diagnostics, and proof metadata. It does not materialize them, implement adapters, connect `/plan`, connect Agent Interaction, scan corpus files, mutate corpus files, infer entities, resolve aliases, infer relationships, promote facts, or change production behavior.

### Recap-Ingestion Source Artifact Fixture v0

After gating the recap-ingestion source family, the ladder adds a tiny synthetic fixture proving that each admitted artifact family can be represented as `SourceArtifact -> SourceAnchor -> SourceUnit`.

Fixture:

`evals/graph_memory_layer/examples/recap_ingestion_source_artifacts_minimal.json`

Validator:

`uv run python -m evals.graph_memory_layer.validate_recap_ingestion_source_artifact_fixture`

Human-readable report:

`Docs/Reports/GRAPH-MEMORY-RECAP-INGESTION-SOURCE-ARTIFACT-FIXTURE.md`

This proves shape compatibility only. It does not read real recap-ingestion outputs, implement a materializer, implement adapters, connect `/plan`, connect Agent Interaction, scan corpus files, mutate corpus files, infer entities, resolve aliases, infer relationships, promote facts, or change production behavior.

### Recap-Ingestion Source Artifact Materializer Gate v0

After proving the synthetic recap-ingestion source artifact fixture, the ladder gates whether a real explicit-input materializer may be implemented for admitted recap-ingestion artifacts.

Gate manifest:

`evals/graph_memory_layer/recap_ingestion_source_artifact_materializer_gate.json`

Validator:

`uv run python -m evals.graph_memory_layer.validate_recap_ingestion_source_artifact_materializer_gate`

Human-readable report:

`Docs/Reports/GRAPH-MEMORY-RECAP-INGESTION-SOURCE-ARTIFACT-MATERIALIZER-GATE.md`

This gate allows a future PR to implement a real explicit-input materializer. It does not implement that materializer. It continues to block directory scanning, corpus scanning, corpus mutation, `/plan`, Agent Interaction, graph retrieval, shadow retrieval, entity extraction, alias resolution, relationship inference, fact promotion, canon promotion, adapter output, runtime UI payloads, and production behavior changes.

### Recap-Ingestion Source Artifact Materializer v0

After gating the materializer, the ladder implements a real explicit-input materializer for admitted recap-ingestion artifacts.

Module:

`src/graph_memory/recap_ingestion_materialize.py`

Validator:

`uv run python -m evals.graph_memory_layer.validate_recap_ingestion_source_artifact_materializer`

Report CLI:

`uv run python -m evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer`

Human-readable report:

`Docs/Reports/GRAPH-MEMORY-RECAP-INGESTION-SOURCE-ARTIFACT-MATERIALIZER.md`

This materializer reads explicitly supplied artifact inputs only and emits diagnostic source artifacts, anchors, units, source refs, provenance, semantic-envelope states, and diagnostics. It does not discover files, scan directories, scan corpus files, mutate corpus files, implement adapters, connect `/plan`, connect Agent Interaction, infer entities, resolve aliases, infer relationships, promote facts, promote canon, or change production behavior.

### Recap-Ingestion Source Artifact Materializer Report v0

After implementing the explicit-input recap-ingestion source artifact materializer, the ladder adds a richer diagnostic report over materializer output.

Report analyzer:

`src/graph_memory/recap_ingestion_materializer_report.py`

Validator:

`uv run python -m evals.graph_memory_layer.validate_recap_ingestion_source_artifact_materializer_report`

Report CLI:

`uv run python -m evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer_diagnostics`

Human-readable report:

`Docs/Reports/GRAPH-MEMORY-RECAP-INGESTION-SOURCE-ARTIFACT-MATERIALIZER-REPORT.md`

This report summarizes artifact coverage, source anchors, source units, source refs, provenance, semantic state counts, structural coverage, and known gaps. It does not implement projection-readiness, adapters, `/plan`, Agent Interaction, graph retrieval, shadow retrieval, corpus scanning, corpus mutation, entity extraction, alias resolution, relationship inference, fact promotion, canon promotion, or production behavior changes.

### Projection-Readiness Over Materialized Recap-Ingestion Artifacts v0

After reporting over explicit-input recap-ingestion source artifact materializer output, the ladder evaluates whether that output is structurally ready for a later projection payload fixture.

Analyzer:

`src/graph_memory/recap_ingestion_projection_readiness.py`

Validator:

`uv run python -m evals.graph_memory_layer.validate_recap_ingestion_projection_readiness`

Report CLI:

`uv run python -m evals.graph_memory_layer.report_recap_ingestion_projection_readiness`

Human-readable report:

`Docs/Reports/GRAPH-MEMORY-RECAP-INGESTION-PROJECTION-READINESS.md`

This report evaluates projection-readiness only. It does not implement a projection adapter, does not connect `/plan`, does not connect Agent Interaction, does not perform graph retrieval, does not scan or mutate corpus files, does not infer entities, does not resolve aliases, does not infer relationships, does not promote facts, does not promote canon, and does not change production behavior.

The expected v0 outcome was `blocked` before source-ref/provenance hardening because materializer output lacked stable `source_ref_id` coverage and provenance-to-source-ref linkage.

### Recap-Ingestion Source Ref / Provenance Linkage Hardening v0

After projection-readiness reported blocked source-ref/provenance checks, the ladder hardens recap-ingestion source artifact materializer output with stable `source_ref_id` coverage and explicit provenance-to-source-ref linkage.

Materializer:

`src/graph_memory/recap_ingestion_materialize.py`

Readiness analyzer:

`src/graph_memory/recap_ingestion_projection_readiness.py`

Validator:

`uv run python -m evals.graph_memory_layer.validate_recap_ingestion_projection_readiness`

Human-readable report:

`Docs/Reports/GRAPH-MEMORY-RECAP-INGESTION-SOURCE-REF-PROVENANCE-LINKAGE-HARDENING.md`

This hardening moves the default explicit-input materializer output from blocked to ready for source-ref/provenance projection-readiness checks. It does not implement adapters, does not connect `/plan`, does not connect Agent Interaction, does not perform graph retrieval, does not scan or mutate corpus files, does not infer entities, does not resolve aliases, does not infer relationships, does not promote facts, does not promote canon, and does not change production behavior.

### Recap-Ingestion Projection Payload Fixture v0

After source-ref/provenance hardening moved projection-readiness checks to ready, the ladder adds a tiny diagnostic projection payload fixture over hardened recap-ingestion source-unit output.

Fixture:

`evals/graph_memory_layer/examples/recap_ingestion_projection_payload_minimal.json`

Validator:

`uv run python -m evals.graph_memory_layer.validate_recap_ingestion_projection_payload_fixture`

Report CLI:

`uv run python -m evals.graph_memory_layer.report_recap_ingestion_projection_payload_fixture`

Human-readable report:

`Docs/Reports/GRAPH-MEMORY-RECAP-INGESTION-PROJECTION-PAYLOAD-FIXTURE.md`

This fixture proves that hardened diagnostic source-unit output can be represented as a bounded projection-safe payload shape for future adapter design. It does not implement adapters, does not connect `/plan`, does not connect Agent Interaction, does not perform graph retrieval, does not scan or mutate corpus files, does not infer entities, does not resolve aliases, does not infer relationships, does not promote facts, does not promote canon, and does not change production behavior.

### Recap-Ingestion Explicit Real-Artifact Dogfood Fixture v0

After proving a projection-safe payload fixture over synthetic explicit inputs, the ladder tests the same explicit-input/materializer/projection-payload chain against one manually selected real or real-derived recap-ingestion artifact bundle.

Dogfood fixture:

`evals/graph_memory_layer/examples/recap_ingestion_real_artifact_dogfood/`

Manifest:

`evals/graph_memory_layer/examples/recap_ingestion_real_artifact_dogfood/dogfood_manifest.json`

Validator:

`uv run python -m evals.graph_memory_layer.validate_recap_ingestion_explicit_real_artifact_dogfood`

Report CLI:

`uv run python -m evals.graph_memory_layer.report_recap_ingestion_explicit_real_artifact_dogfood`

Human-readable report:

`Docs/Reports/GRAPH-MEMORY-RECAP-INGESTION-EXPLICIT-REAL-ARTIFACT-DOGFOOD.md`

This dogfood fixture tests whether the existing explicit-input recap-ingestion materializer and projection payload chain survives one realistic artifact bundle while preserving source identity, provenance linkage, semantic states, opaque handles, display/evidence boundaries, and safety boundaries. It does not scan directories, scan canonical corpus files, mutate corpus files, implement adapters, connect `/plan`, connect Agent Interaction, perform retrieval, infer entities, resolve aliases, infer relationships, promote facts, promote canon, or change production behavior.

| Concern | Owned by `/plan` | Owned by ontology ladder | Adapter contract |
|---|---|---|---|
| Projection UI | Yes | No | Receives projection-ready source units |
| Reference chips | Yes | No | Chips carry opaque handles, not graph internals |
| Taxonomy vocabulary | No | Yes | Adapter maps graph terms to projection kinds |
| Alias resolution | No | Yes, later | Adapter may expose candidates separately from matches |
| Lifecycle semantics | Display only | Yes | Adapter returns lifecycle/provenance fields |
| Source evidence | Display/cite | Yes | Adapter returns source anchors and evidence roles |
| Graph traversal | No | Later shadow mode | Adapter returns bounded expansions with explanations |
| Current fallback | Yes | No | Live-index fallback remains valid |

## Branch Model

Durable ladder root branch:

```text
experiment/ontology-taxonomy-ladder
```

All ontology/taxonomy PRs should branch from this root branch.

Stacked branch naming:

```text
graph-exp/01-freeze-baseline-reports
graph-exp/02-taxonomy-registry-v0
graph-exp/03-ontology-ir-schema
graph-exp/04-source-authority-model
graph-exp/05-graph-node-edge-vocabulary
graph-exp/06-validation-rules
graph-exp/07-materialize-current-structure
graph-exp/08-graph-report-cli
graph-exp/09-shadow-retrieval-fixtures
graph-exp/10-promotion-report
```

The root branch isolates this workstream from unrelated active work. Each PR should be small enough to review and should preserve the ladder rule: later rungs may depend on earlier rungs, but no rung should require production retrieval changes to be useful.

## Relationship to Tiptap / Markdown Backend Work

The Tiptap workstream owns canonical editing and document structure.

The ontology/taxonomy ladder owns derived semantics, controlled vocabulary, graph model, validation, and retrieval topology.

These tracks should not compete. The ontology ladder should avoid assumptions that Tiptap may invalidate, including future canonical block models, editor schemas, or document storage details.

Use adapter-shaped thinking:

- Today: consume existing Markdown, breadcrumb records, session-memory JSONL, manifests, and route metadata.
- Later: consume Tiptap-backed canonical block/document structures through an adapter.

Stable abstraction names:

- `SourceDocument`
- `SourceSection`
- `SourceBlock` or `SentenceUnit`
- `SourceAnchor`
- `Route`
- `Entity`
- `EvidenceRole`
- `AuthorityState`
- `VisibilityState`
- `GraphNode`
- `GraphEdge`
- `GraphBundle`

Tiptap may change how `SourceDocument` and `SourceBlock` are produced. It should not change the ontology layer's need for source identity, provenance, evidence roles, and graph relationships.

## Updated Ladder Order

### Rung 1: Baseline and Safety

Freeze known graph-native failure families and preserve smoke checks.

Status: complete.

## Baseline Case Manifest

Rung 1 baseline cases are tracked in:

`evals/graph_memory_layer/baseline_cases.json`

Human-readable index:

`evals/graph_memory_layer/BASELINE-INDEX.md`

These cases define the graph-native failure families future ladder rungs must preserve, measure, or improve before promotion.

### Rung 2: Taxonomy Registry v0

Define controlled vocabulary before ontology machinery.

Status: complete.

## Taxonomy Registry

Rung 2 taxonomy vocabulary is tracked in:

`evals/graph_memory_layer/taxonomy_registry.json`

Human-readable index:

`evals/graph_memory_layer/TAXONOMY-REGISTRY.md`

Validator:

`uv run python -m evals.graph_memory_layer.validate_taxonomy_registry`

The taxonomy registry defines controlled vocabulary only. It does not define ontology IR, graph node schemas, graph edge schemas, materialization, or retrieval behavior.

### Rung 3: Ontology IR Schema v0

Define schema-only graph-memory records: taxonomy refs, source refs, provenance refs, graph nodes, graph edges, validation status, and graph bundles.

Status: complete.

## Ontology IR Schema

Rung 3 ontology IR schema is tracked in:

`src/graph_memory/ontology_ir.py`

Human-readable schema guide:

`evals/graph_memory_layer/ONTOLOGY-IR-SCHEMA.md`

Synthetic example bundle:

`evals/graph_memory_layer/examples/ontology_ir_minimal_bundle.json`

Validator:

`uv run python -m evals.graph_memory_layer.validate_ontology_ir`

This schema defines graph-memory record shapes only. It does not materialize real campaign data, perform extraction, resolve aliases, export RDF, or affect production retrieval.

### Rung 4: Ontology IR Validation Rules v0

Validate graph bundles against taxonomy refs, source-grounding expectations, evidence/admissibility rules, authority boundaries, visibility boundaries, lifecycle/promotion constraints, and endpoint integrity.

Status: complete.

## Ontology IR Validation Rules

Rung 4 validation rules are tracked in:

`src/graph_memory/validation_rules.py`

Human-readable guide:

`evals/graph_memory_layer/ONTOLOGY-IR-VALIDATION-RULES.md`

Synthetic invalid fixture:

`evals/graph_memory_layer/examples/ontology_ir_invalid_bundle.json`

Validator:

`uv run python -m evals.graph_memory_layer.validate_ontology_ir_rules`

These rules validate Ontology IR bundles against taxonomy references, evidence/admissibility guardrails, authority boundaries, visibility boundaries, lifecycle/promotion constraints, and source-grounding expectations. They do not materialize graph data, extract entities, scan corpus files, call LLMs, or affect production retrieval.

### Rung 5: Synthetic Deterministic Materializer v0

Convert a tiny synthetic fixture into a validated Ontology IR GraphBundle.

Status: complete.

## Deterministic Materializer

Rung 5 deterministic materializer is tracked in:

`src/graph_memory/materialize.py`

Synthetic input fixture:

`evals/graph_memory_layer/examples/materializer_input_minimal.json`

Human-readable guide:

`evals/graph_memory_layer/MATERIALIZER.md`

Validator:

`uv run python -m evals.graph_memory_layer.validate_materializer`

This materializer converts a tiny synthetic fixture into a validated Ontology IR GraphBundle. It does not materialize campaign data, scan corpus files, read session memory, parse Markdown, infer entities, resolve aliases, call LLMs, or affect production retrieval.

### Rung 6: Materializer Report CLI v0

Build a deterministic report over the synthetic materialized bundle.

The report should show node counts, edge counts, provenance paths, validation issue counts, taxonomy usage, and source-grounding shape.

Status: implemented in report CLI v0.

## Materializer Report CLI

Rung 6 materializer report CLI is tracked in:

`src/graph_memory/report.py`

Report CLI:

`uv run python -m evals.graph_memory_layer.report_materializer`

Validator:

`uv run python -m evals.graph_memory_layer.validate_materializer_report`

Human-readable guide:

`evals/graph_memory_layer/MATERIALIZER-REPORT.md`

This report makes the synthetic materialized GraphBundle inspectable before any real source surface is admitted. It reports node counts, edge counts, taxonomy usage, lifecycle states, visibility states, evidence roles, provenance refs, source refs, and validation issue summaries. It does not broaden materialization, scan real data, call LLMs, or affect production retrieval.

### Rung 7: Real-Structure Materialization Gate

Before reading real existing structures, add an explicit gate review that defines which source surfaces may be consumed first.

Candidate surfaces may include session-memory JSONL, route metadata, breadcrumb records, manifest records, or source documents, but only one family should be admitted at a time.

Status: active gate.

## Real-Structure Materialization Gate

Rung 7 real-structure materialization gate is tracked in:

`evals/graph_memory_layer/real_structure_materialization_gate.json`

Human-readable guide:

`evals/graph_memory_layer/REAL-STRUCTURE-MATERIALIZATION-GATE.md`

Validator:

`uv run python -m evals.graph_memory_layer.validate_real_structure_gate`

The gate admits exactly one source family for the next materializer PR: `session_memory_jsonl_sentence_units`.

This gate does not materialize real data. It defines the constraints a future materializer must obey before reading any real existing structure. It keeps production retrieval, corpus mutation, LLM extraction, alias resolution, relationship inference, and promoted records forbidden.

### Rung 8: Session-Memory Sentence-Unit Materializer v0

Materialize explicit session-memory JSONL sentence/source-unit records into a diagnostic candidate GraphBundle without changing production retrieval.

Status: complete.

## Session-Memory Sentence-Unit Materializer

Rung 8 session-memory sentence-unit materializer is tracked in:

`src/graph_memory/session_memory_materialize.py`

Validator:

`uv run python -m evals.graph_memory_layer.validate_session_memory_materializer`

This materializer consumes only explicit session-memory JSONL records admitted by the real-structure gate. It emits source-document/source-unit graph records for diagnostics and candidate reporting only. It does not scan broad campaign/corpus files, parse Markdown or Tiptap output, infer aliases/entities/relationships, call LLMs, mutate corpus files, influence `/plan`, or change production retrieval.

### Rung 9: Graph Report Over Real Existing Structure

Report coverage, orphan records, source-support gaps, taxonomy usage, route/entity coverage, and validation issues over the first real-structure materializer output.

Status: future.

### Rung 10: Shadow Retrieval Fixtures

Only after deterministic materialization and reporting exist should graph-assisted retrieval be tested in shadow mode.

Status: future.

### Rung 11: LLM Candidate Extraction

Only after deterministic graph structure, validation, reports, and shadow retrieval fixtures exist should LLMs propose candidate entities, aliases, relationships, taxonomy additions, or ontology refinements.

Status: future.

### Rung 12: Promotion Report

Only after measured wins and no source-grounding regression should any graph-assisted behavior be considered for production retrieval.

Status: future.

## Allowed and Forbidden Areas

Early ontology/taxonomy work may touch:

- `Docs/Experiments/`
- `Docs/Design/`
- `Docs/Reports/`
- `evals/graph_memory_layer/`
- `src/graph_memory/`
- `tests/test_graph_memory_*.py`

Early ontology/taxonomy work should not touch:

- `src/agent/session_memory_query.py`
- `src/agent/planner_retrieval_router.py`
- `src/live_play/manifest_context_query.py`
- `src/session_memory/capture.py`
- `src/session_memory/breadcrumb_normalize.py`
- `evals/sentence_routing_retrieval_falsification/`
- canonical `corpus/` files

Exceptions require explicit PR description and rationale.

## First PR Scope

The first ladder PR establishes the ladder root and baseline direction. It should be docs-only except for branch-policy documentation.

Suggested PR:

- Title: `graph-memory: establish ontology taxonomy ladder`
- Base branch: `experiment/ontology-taxonomy-ladder`
- Head branch: `graph-exp/01-ontology-taxonomy-ladder-anchor`

This PR defines the ladder model, branch model, non-goals, rung order, relationship to Tiptap, allowed folders, forbidden folders, promotion gates, and next PR sequence.

## Next PR Sequence

1. Materializer Report CLI v0: report the synthetic materialized bundle, validation summary, node/edge counts, source refs, provenance refs, and taxonomy usage.
2. Real-Structure Materialization Gate: decide which existing source family can be safely materialized first.
3. First Real-Structure Materializer: materialize one approved source family without production retrieval changes.
4. Graph Report Over Real Structure: show coverage, gaps, validation issues, and source-grounding paths.
5. Shadow Retrieval Fixtures: compare current retrieval with graph-expanded retrieval on hard cases, still no production integration.
6. LLM Candidate Extraction: allow LLMs to propose candidates only after deterministic structure and reporting are proven.
7. Promotion Report: summarize measured wins, regressions, gates, and remaining risks before production behavior changes.

## Pause Decision

The ladder should pause after Synthetic Deterministic Materializer v0 and re-anchor before widening materialization.

Reason:

The project now has enough machinery to create graph records, but not enough operator visibility to safely broaden inputs.

The next rung should be reporting, not broader materialization.

A materializer report should make visible:

- graph bundle ID
- schema version
- taxonomy registry version
- node count
- edge count
- node kinds
- edge predicate families
- provenance refs
- source refs
- validation issue counts
- validation severities
- non-admissible evidence roles
- candidate/promoted lifecycle distribution
- visibility distribution

Do not start real campaign/corpus/session-memory materialization until reporting exists.

## Promotion Gates

The ontology/taxonomy ladder may only promote beyond shadow mode if it proves:

- no source-grounding regression
- no production retrieval behavior changes before explicit promotion
- no graph summaries treated as source evidence
- no LLM-generated facts promoted without validation
- no silent ontology mutation
- better or equal behavior on C1S2 clean control
- measured improvement on at least one graph-native failure family
- improved debug visibility for why context is included

Graph-native failure families include:

- location hierarchy
- alias/identity bridge
- roster/party identity
- unresolved hook resurfacing
- session-scoped final-beat retrieval

## Operating Rule

This workstream should be boring before it is powerful.

The first success is not that the graph answers questions. The first success is that we can name concepts, validate concepts, materialize existing structure, inspect the graph, prove where the graph would help, and reject unsafe graph claims.

Only then should graph memory influence retrieval.

## Updated Working Decision

The project now has two parallel but separate paths:

- Tiptap / Markdown backend work defines the future canonical editing and document model.
- Ontology / Taxonomy ladder work defines the future semantic and graph model.

The ontology ladder should not wait passively, but it should avoid irreversible corpus assumptions. Proceed with docs, taxonomy, schema, validation, deterministic materialization, and reports. Delay wholesale corpus rework until the canonical document model is stable.

## Session-Memory Sentence-Unit Materializer

Rung 8 session-memory sentence-unit materializer is tracked in:

`src/graph_memory/session_memory_materialize.py`

Synthetic session-memory fixture:

`evals/graph_memory_layer/examples/session_memory_sentence_units_minimal.jsonl`

Validator:

`uv run python -m evals.graph_memory_layer.validate_session_memory_materializer`

Report CLI:

`uv run python -m evals.graph_memory_layer.report_session_memory_materializer`

Human-readable guide:

`evals/graph_memory_layer/SESSION-MEMORY-MATERIALIZER.md`

This materializer consumes only explicit session-memory JSONL sentence/source-unit records. The default validator uses a tiny synthetic fixture. It emits candidate/internal/diagnostic source-document and source-unit graph records with provenance and source refs. It does not scan corpus files, parse Markdown/Tiptap output, read manifests, infer entities, resolve aliases, emit promoted facts, call LLMs, or affect production retrieval.


## Candidate Graph Preview IR v0

The workstream now has a preview-only candidate graph object model with nodes, edges, beats, proposed writes, ignored/deferred items, semantic states, diagnostics, and evidence refs compatible with the source-span evidence resolver. The next backend rung should supply a richer recap dogfood fixture that can later be paired with a hand-authored gold candidate graph.

Next backend PR: Rich Recap Dogfood Fixture v0.
Current checkpoint: post-candidate-graph-preview-ir checkpoint.
