# Graph Memory Materializer Report v0

## Purpose

The materializer report makes the synthetic deterministic graph materializer output inspectable before any real source surface is admitted to the Graph Memory / Ontology / Taxonomy ladder.

It answers what the materializer created, which taxonomy/provenance/source refs are present, and which validation issues are visible.

## Status

Report-only v0 for the synthetic fixture path.

This rung does not broaden materialization and does not change production behavior.

## What This Reports

- Graph bundle metadata: bundle ID, schema version, taxonomy registry version, and creator.
- Node and edge counts.
- Node kind distribution.
- Edge predicate-family distribution.
- Lifecycle-state distribution.
- Visibility-state distribution.
- Evidence-role distribution.
- Authority-state distribution.
- Provenance-ref and source-ref counts.
- Validation issue counts, severities, and codes.
- A compact per-record summary table.

## What This Does Not Report

This report does not inspect real campaign graph data, corpus files, session-memory JSONL, Markdown, Tiptap output, manifest/live-play records, generated reports in canonical corpus, or production retrieval behavior.

It does not infer entities, resolve aliases, add relationships, export RDF/JSON-LD/OWL/SPARQL, or call an LLM.

## Report Inputs

The report input is limited to:

- `evals/graph_memory_layer/examples/materializer_input_minimal.json`
- `evals/graph_memory_layer/taxonomy_registry.json`
- the deterministic synthetic fixture materializer
- the Ontology IR taxonomy validation rules

## Report Sections

The Markdown report includes:

- Summary
- Node Kinds
- Edge Predicate Families
- Lifecycle States
- Visibility States
- Evidence Roles
- Authority States
- Validation Issues
- Records

All count tables are rendered in deterministic key order, and record summaries are sorted by record type and record ID.

## Validation Behavior

The report CLI exits successfully when the materialized synthetic bundle has no `error` or `fatal` validation issues.

Informational validation issues remain visible. In v0, `diagnostic_only` evidence is expected to produce informational `non_admissible_evidence_role` issues so operators can see that the synthetic fixture is diagnostic-only and not answer-supporting evidence.

## Safety Boundaries

The report is synthetic-only and report-first. It must not:

- scan real data
- scan corpus files
- read session memory
- parse Markdown
- parse Tiptap output
- ingest manifest or live-play data
- change retrieval
- call LLMs
- write generated reports into canonical corpus

## Commands

Render the report:

```bash
uv run python -m evals.graph_memory_layer.report_materializer
```

Validate the report path:

```bash
uv run python -m evals.graph_memory_layer.validate_materializer_report
```

## Future Rungs

After this report-only rung is reviewed and merged, the next rung should define a real-structure materialization gate that chooses which single existing source family is safe to admit first.

That future gate should still avoid broad real-data materialization, graph retrieval, extraction, alias resolution, relationship inference, and production retrieval changes.
