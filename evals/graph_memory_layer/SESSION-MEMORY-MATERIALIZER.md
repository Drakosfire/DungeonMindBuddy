# Graph Memory Session-Memory Sentence-Unit Materializer v0

## Purpose

This rung proves that explicit session-memory JSONL sentence/source-unit records can be converted into a diagnostic candidate `GraphBundle`, validated, and reported without broad source ingestion.

## Status

This is a v0, validation-first, report-first materializer for the Ontology / Taxonomy ladder. It is not a production retrieval feature.

## Gate

The validator loads `evals/graph_memory_layer/real_structure_materialization_gate.json` and requires the admitted source family to be `session_memory_jsonl_sentence_units`.

## Input Shape

Input is line-delimited JSON with `dmb_session_memory_record_v1` records containing explicit sentence/source-unit fields such as `campaign_id`, `session_number`, `source_recap_path`, `unit_id`, line range, text hash, text, and optional `routes`.

## What This Materializes

- One `source_document` node for each distinct source recap path.
- One `source_unit` node for each JSONL record.
- One `source_derivation` edge from the source document to each source unit.
- Candidate/internal/diagnostic provenance and source refs for all records.

## What This Does Not Materialize

It does not materialize route nodes, entity nodes, alias edges, inferred relationships, promoted facts, graph retrieval state, shadow retrieval state, graph storage, or canonical corpus files.

## GraphBundle Shape

The bundle uses schema version `0.1`, taxonomy registry version `0.1`, and `created_by` value `session_memory_sentence_unit_materializer_v0`. Node properties are scalar only and do not store full `lexical_plain` text.

## Provenance and Source Refs

All emitted records use `authority_state/system_derived`, `evidence_role/diagnostic_only`, and `visibility_state/internal_diagnostic`. Source refs point to the explicit session-memory record path, line range, and unit anchor.

## Route Handling

Routes are counted for coverage only. They are not converted into graph nodes or edges in this rung.

## Validation

The validator checks gate compliance, taxonomy validation, expected graph counts, candidate/internal/diagnostic defaults, provenance refs, source refs, and absence of route/entity/alias/inferred graph records.

## Reporting

The report CLI prints the shared Graph Memory materializer report plus a session-memory coverage section for input records, source documents, source units, records with routes, and route mention counts.

## Safety Boundaries

The default path is the synthetic fixture under `evals/graph_memory_layer/examples/`. Optional CLI input must be an explicit JSONL path. There is no corpus scanning, globbing, manifest ingestion, Markdown parsing, Tiptap parsing, production retrieval import, entity extraction, alias resolution, relationship inference, or LLM call.

## Commands

```bash
uv run python -m evals.graph_memory_layer.validate_session_memory_materializer
uv run python -m evals.graph_memory_layer.report_session_memory_materializer
uv run python -m evals.graph_memory_layer.report_session_memory_materializer --input evals/graph_memory_layer/examples/session_memory_sentence_units_minimal.jsonl
```

## Future Rungs

Future rungs may deepen coverage reporting before any route nodes, entity nodes, graph retrieval, shadow retrieval, or broader source ingestion is introduced.
