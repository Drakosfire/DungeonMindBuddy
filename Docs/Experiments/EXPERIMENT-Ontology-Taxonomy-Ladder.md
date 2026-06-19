# Ontology / Taxonomy Ladder Workstream

Version: 0.3-main-anchor  
Status: planning anchor on main  
Workstream: Graph Memory / Ontology / Taxonomy  
Active ladder branch: `experiment/ontology-taxonomy-ladder`  
Relationship to other work: separate from Tiptap / Markdown backend workstream

## Purpose

This document records the active Ontology / Taxonomy ladder workstream from `main`.

The detailed ladder work proceeds on:

`experiment/ontology-taxonomy-ladder`

`main` carries this anchor for planning visibility only. It should not be treated as a merge-back of the full ladder branch.

## Core Decision

Ontology and taxonomy work proceeds as an isolated ladder branch family, not as scattered changes on `main` and not as a wholesale corpus rewrite.

The ladder exists to mature graph memory, taxonomy, ontology, and source-grounded retrieval structure without destabilizing current retrieval, canonical corpus, or the Tiptap / Markdown backend workstream.

## Relationship to Tiptap

The Tiptap / Markdown backend workstream owns canonical authoring and document structure.

The Ontology / Taxonomy ladder owns derived semantics, controlled vocabulary, graph model, validation, reports, and later shadow retrieval.

The ontology ladder should avoid hardcoding assumptions that Tiptap may invalidate.

Use adapter-shaped thinking:

- Today: consume existing Markdown, session-memory JSONL, manifests, routes, breadcrumbs, and source paths.
- Later: consume Tiptap-backed canonical blocks through an adapter.

The stable abstraction is:

source artifact -> source anchor -> source unit -> derived semantic graph

## Ladder Order

1. Scaffold and branch safety
2. Ontology / Taxonomy ladder anchor
3. Baseline case freeze
4. Taxonomy Registry v0
5. Ontology IR schema
6. Validation rules
7. Deterministic materialization
8. Graph report CLI
9. Shadow retrieval fixtures
10. LLM candidate extraction
11. Promotion report

## Current Ladder State

The ladder branch has advanced past the initial anchor, baseline case surface, taxonomy registry, ontology IR schema, and validation-rule rungs. As of PR #151 review context, Rung 7 is an active real-structure gate rather than a materializer implementation.

The approved gate surface is policy and validation only. It grants permission for exactly one future materializer target, `session_memory_jsonl_sentence_units`, while continuing to forbid production retrieval changes, corpus mutation, LLM calls, extraction, alias resolution, relationship inference, promoted records, and production graph summaries as evidence.

This `main` document does not promote the full ladder branch. It records the operational direction and the latest reviewed gate boundary.

## Current Active Gate

PR #151 is mergeable as the Rung 7 gate because it limits the next implementation to one source family and keeps that family diagnostic-only by default.

The admitted family is constrained to an explicit session-memory JSONL fixture or configured path. It does not admit corpus, Live Play, activated manifest, Tiptap, Markdown, or retrieval surfaces as evidence. The only admitted evidence shapes are source document, source unit, explicit route, and evidence role shapes.

The gate continues to block campaign facts, identity merges, alias edges, inferred relationships, promoted claims, graph summaries as evidence, and any materializer behavior that reads real data during the gate PR itself.

## Next Rung

The next ladder rung is:

`graph-memory: add session-memory sentence-unit materializer v0`

That future materializer may target exactly the `session_memory_jsonl_sentence_units` source family admitted by the gate. It must remain deterministic, diagnostic, candidate-only, validation-first, and report-first. It must not change production retrieval behavior.

The nonblocking test-quality critique to carry forward: avoid tests that claim to inspect PR changed files by running `git diff --name-only HEAD` inside pytest. After a commit exists, that command only sees uncommitted working-tree changes and may be empty in CI/review checkouts. Future guard tests should assert against explicit forbidden repo paths or another stable fixture/list rather than making PR-diff claims from inside pytest.

## Non-Goals

This workstream is not:

- a full production Graph RAG rewrite
- a replacement for current retrieval
- a corpus migration
- a Tiptap backend implementation
- an LLM-driven auto-ontology generator
- permission to mutate campaign truth
- permission to change production retrieval modules early

## Non-Negotiables

Do not change production retrieval behavior before explicit promotion.

Do not mutate canonical corpus files.

Do not add LLM extraction yet.

Do not create ontology IR before taxonomy registry exists.

Do not admit graph summaries as source evidence.

Do not treat generated graph facts as campaign truth.

Do not collapse GM prep, rumor, candidate facts, and played truth into one bucket.

Do not merge aliases or identities without provenance and lifecycle state.

Do not let high-degree hubs flood context without measurement.

Do not start shadow retrieval until deterministic taxonomy, schema, validation, materialization, and reporting exist.

## Allowed Early Ladder Areas

On ladder branches, early work may touch:

- `Docs/Experiments/`
- `Docs/Design/`
- `Docs/Reports/`
- `evals/graph_memory_layer/`
- `tests/test_graph_memory_*.py`

Later schema rungs may introduce:

- `src/graph_memory/`

Production retrieval files and canonical corpus files remain off-limits until explicit promotion.

## Promotion Rule

Graph memory may only influence production retrieval after measured shadow-mode evidence shows:

- no source-grounding regression
- no clean-control regression
- no graph summaries used as source evidence
- no unsupported LLM-generated facts promoted
- no silent ontology mutation
- traceable source-backed expansion paths
- measurable improvement or clearer diagnostics on graph-native failure families

## Operating Rule

This workstream should be boring before it is powerful.

Name the concepts.

Validate the concepts.

Materialize existing structure.

Report what exists.

Only then use the graph to influence retrieval.
