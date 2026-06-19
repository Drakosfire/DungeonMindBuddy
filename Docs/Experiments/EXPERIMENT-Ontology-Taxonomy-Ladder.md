# Ontology & Taxonomy Ladder Workstream

Version: 0.2
Status: active operational anchor
Workstream: Graph Memory / Ontology / Taxonomy
Branch model: isolated ladder branch family
Relationship to other work: separate from Tiptap / Markdown backend workstream

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

## Ladder Order

### Rung 1: Baseline and Safety

- Freeze or document current retrieval behavior.
- Preserve known failure families.
- Keep smoke and branch checks working.
- Add no graph logic yet.

## Baseline Case Manifest

Rung 1 baseline cases are tracked in:

`evals/graph_memory_layer/baseline_cases.json`

Human-readable index:

`evals/graph_memory_layer/BASELINE-INDEX.md`

These cases define the graph-native failure families future ladder rungs must preserve, measure, or improve before promotion.

### Rung 2: Taxonomy Before Ontology

Define controlled vocabularies before defining graph edges. Initial vocabulary areas include:

- source kinds
- entity kinds
- route kinds
- evidence roles
- authority states
- visibility states
- truth states
- lifecycle states
- relationship predicate names
- planning lanes
- retrieval lanes

This gives the graph a language before it has machinery.

## Taxonomy Registry

Rung 2 taxonomy vocabulary is tracked in:

`evals/graph_memory_layer/taxonomy_registry.json`

Human-readable index:

`evals/graph_memory_layer/TAXONOMY-REGISTRY.md`

Validator:

`uv run python -m evals.graph_memory_layer.validate_taxonomy_registry`

The taxonomy registry defines controlled vocabulary only. It does not define ontology IR, graph node schemas, graph edge schemas, materialization, or retrieval behavior.

### Rung 3: Ontology IR

Define the internal model for nodes, edges, source refs, provenance, confidence, lifecycle state, and validation status. The model should be RDF-compatible in spirit, but not RDF-first.

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

### Rung 4: Validation Before Extraction

Define validation rules before LLM extraction. Examples:

- Every canonical edge needs provenance.
- Every source-supported claim needs a source anchor.
- Every route attachment points to a known route or explicit candidate.
- Every entity merge must preserve source support.
- Every inferred edge must be marked as inferred.
- No graph summary is admissible as source evidence.

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

### Rung 5: Deterministic Materialization

Materialize what already exists:

- session memory records
- routes
- breadcrumbs
- manifest records
- source documents
- sentence units
- evidence roles
- locations if already present
- party records if already present
- new hub candidates if already present

Do not ask an LLM to invent structure yet.

### Rung 6: Reporting and Debugging

Build graph reports before graph retrieval. Reports should show:

- node counts
- edge counts
- orphan routes
- units without routes
- routes without units
- high-degree hubs
- unknown taxonomy values
- source-support gaps
- unresolved hooks
- candidate entities
- validation failures

The first operator value should be visibility.

### Rung 7: Shadow Retrieval

Only after deterministic materialization and reporting exist should the graph propose retrieval expansions.

Graph-assisted retrieval must run in shadow mode and explain:

- what node caused an expansion
- what edge caused an expansion
- what source supports that edge
- what confidence/lifecycle state it has
- why it was admitted or rejected

### Rung 8: LLM Candidate Extraction

Only after deterministic structure works should LLMs propose entity candidates, alias candidates, relationship candidates, taxonomy additions, or ontology refinements.

LLMs propose. Validators and source anchors authorize.

### Rung 9: Promotion

Only after measured wins should any graph-assisted behavior be promoted into production retrieval. Promotion requires a report.

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

1. Freeze baseline reports: document known retrieval behavior and hard failure families; no graph logic.
2. Taxonomy registry v0: create controlled vocabulary definitions; no extraction or graph materialization.
3. Ontology IR schema: create `src/graph_memory/schema.py` for nodes, edges, provenance, source refs, and lifecycle states; no retrieval integration.
4. Validation rules: fail closed on missing source/provenance; no LLM extraction.
5. Deterministic materializer: read existing session-memory JSONL and manifest artifacts and emit a graph bundle; no production retrieval changes.
6. Graph report CLI: show graph coverage, orphan routes, source-support gaps, high-degree hubs, and taxonomy usage.
7. Shadow retrieval fixtures: compare current retrieval versus graph-expanded retrieval on hard cases; no production integration.
8. Promotion report: summarize measured wins, regressions, gates, and remaining risks before production behavior changes.

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
