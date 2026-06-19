# Graph Memory Deterministic Materializer v0

## Purpose

The deterministic materializer proves that a tiny, explicit, synthetic source-unit fixture can be transformed into a validated Ontology IR `GraphBundle` without extraction, inference, or model calls.

## Status

This is v0 for the Ontology / Taxonomy ladder. It is fixture-only and diagnostic-only.

## What This Materializes

- One synthetic source document node.
- One synthetic source unit node.
- One explicit source-derivation edge from the document to the unit.
- Provenance and source refs for each materialized record.

## What This Does Not Materialize

This does not materialize campaign data, scan corpus files, read session memory, parse Markdown, read Tiptap output, extract entities, resolve aliases, infer relationships, call LLMs, or affect retrieval.

## Synthetic Fixture Input

The only fixture for this rung is:

`evals/graph_memory_layer/examples/materializer_input_minimal.json`

The fixture is deliberately not an Ontology IR bundle. It uses a small source-document/source-unit shape so the materializer performs a visible deterministic transformation.

## Materialized GraphBundle Shape

The materialized bundle uses schema version `0.1`, taxonomy registry version `0.1`, and `created_by: deterministic_graph_materializer_v0`.

All records are synthetic, `candidate`, `internal_diagnostic`, and grounded with `diagnostic_only` provenance.

## Validation

Run:

```bash
uv run python -m evals.graph_memory_layer.validate_materializer
```

The validator materializes the fixture and validates the resulting bundle with `validate_bundle_against_taxonomy`.

## Safety Boundaries

The materializer consumes only an explicit fixture path. It does not discover files automatically and does not read real campaign source artifacts, corpus files, session-memory JSONL, Markdown, Tiptap output, manifests, or live-play data.

## Future Rungs

Future rungs may add deterministic reports and later real-structure materialization after review. Real campaign or corpus materialization should not begin until reports can show materialized records, validation issues, and provenance paths.
