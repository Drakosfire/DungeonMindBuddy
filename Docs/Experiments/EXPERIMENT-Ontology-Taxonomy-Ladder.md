# Ontology & Taxonomy Ladder Workstream

Version: 0.3
Status: active operational anchor — post-synthetic-materializer checkpoint
Workstream: Graph Memory / Ontology / Taxonomy
Branch model: isolated ladder branch family
Relationship to other work: separate from Tiptap / Markdown backend workstream

## Current Checkpoint

The ladder has completed the safe foundation rungs:

1. Baseline case freeze
2. Taxonomy Registry v0
3. Ontology IR Schema v0
4. Ontology IR Validation Rules v0
5. Synthetic Deterministic Materializer v0

The project can now define graph vocabulary, represent graph records, validate graph records, reject unsafe graph bundles, and materialize a tiny synthetic fixture into a validated Ontology IR GraphBundle.

The project has not yet materialized real campaign data, corpus data, session-memory JSONL, Markdown, Tiptap output, activated manifests, or live-play records.

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

Status: next.

### Rung 7: Real-Structure Materialization Gate

Before reading real existing structures, add an explicit gate review that defines which source surfaces may be consumed first.

Candidate surfaces may include session-memory JSONL, route metadata, breadcrumb records, manifest records, or source documents, but only one family should be admitted at a time.

Status: future.

### Rung 8: First Real-Structure Materializer

Materialize one approved real existing structure into graph records without changing production retrieval.

Status: future.

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
