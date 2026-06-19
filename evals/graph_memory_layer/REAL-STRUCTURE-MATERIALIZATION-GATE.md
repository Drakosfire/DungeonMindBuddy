# Graph Memory Real-Structure Materialization Gate v0

## Purpose

This gate defines the first real existing source family that a future deterministic Graph Memory materializer may read. It is a policy and validation rung only: it does not read session memory, scan corpus files, parse Markdown or Tiptap output, ingest manifests, call LLMs, or emit real graph records.

## Status

Status: active gate.

The gate admits exactly one source family for the next materializer PR and keeps all other real source families deferred or blocked.

## Current Ladder State

The ladder already has baseline cases, a taxonomy registry, Ontology IR schema and validation rules, a synthetic deterministic materializer, and a synthetic materializer report CLI. Those pieces make synthetic GraphBundles inspectable before any real source surface is admitted.

The ladder has not yet materialized real campaign data, corpus files, session-memory JSONL, activated manifests, live-play manifests, Markdown, or Tiptap source documents.

## Gate Decision

The next materializer PR may target exactly one source family:

`session_memory_jsonl_sentence_units`

That future PR must remain deterministic, diagnostic, candidate-only, validation-first, and report-first. It must not change production retrieval behavior.

## Admitted Source Family

The admitted source family is session-memory JSONL sentence/source-unit records. The future materializer may only read an explicit session-memory JSONL fixture or configured path approved by that PR. It may not broaden into corpus scanning, live-play manifests, activated manifests, Tiptap output, Markdown parsing, or production retrieval modules.

## Why This Source Family First

- It is closer to explicit source-unit structure than raw Markdown or canonical corpus files.
- It can be represented diagnostically without entity extraction, alias resolution, relationship inference, or promoted facts.
- It avoids depending on assumptions about the future Tiptap canonical document model.
- It can produce useful coverage and validation reports before graph output influences retrieval.

## Deferred Source Families

Deferred source families are not admitted for the next materializer PR:

- `manifest_records`
- `markdown_source_documents`
- `tiptap_canonical_documents`

These surfaces need more reporting proof, source-model stability, or safety review before materialization.

## Blocked Source Families

Blocked source families are not admitted for the next materializer PR:

- `canonical_corpus_files`
- `live_play_records`

Canonical corpus mutation, broad corpus scanning, live-play ingestion, and activated runtime surfaces remain too risky for the first real-structure materializer.

## Allowed Future Materializer Behavior

A future materializer may emit only low-risk diagnostic graph structures from the admitted source family:

- source document or source file references
- source unit references
- route attachments when already explicit in the source structure
- evidence-role annotations when already explicit and source-grounded

Required record defaults are:

- lifecycle state: `candidate`
- visibility state: `internal_diagnostic`
- evidence role default: `diagnostic_only`

## Forbidden Future Materializer Behavior

The future materializer must not:

- materialize more than one source family
- scan canonical corpus files
- parse Markdown or Tiptap output
- read live-play or activated manifests
- import or change production retrieval modules
- perform LLM extraction or generation
- infer entities, aliases, relationships, or campaign facts
- emit promoted claims or promoted graph facts
- treat graph summaries as source evidence
- write to production data stores or canonical corpus files
- change current retrieval behavior

## Required Validation

Before and after future materialization, the future PR must run Ontology IR validation rules and fail on blocking validation issues. The gate itself is validated with:

```bash
uv run python -m evals.graph_memory_layer.validate_real_structure_gate
```

The validator asserts that exactly one source family is admitted, all global safety constraints are enabled, blocked and deferred families are not admitted, and the admitted source family has explicit allowed surfaces, forbidden surfaces, record shapes, defaults, and report requirements.

## Required Reporting

The future materializer must emit a report before any retrieval integration. Required reporting includes:

- node count
- edge count
- source refs
- provenance refs
- validation issue summary
- route/source-unit coverage when applicable

Reporting remains a prerequisite for retrieval experiments.

## Safety Boundaries

Core safety boundaries for this rung are:

- one source family at a time
- validation before admission
- reporting before retrieval
- diagnostic/candidate defaults
- no promoted graph facts
- no LLM extraction
- no alias or entity inference
- no relationship inference
- no production retrieval changes
- no canonical corpus mutation

## Next PR

The next PR should be:

`graph-memory: add session-memory sentence-unit materializer v0`

That PR may read only the admitted source family under this gate and must still avoid production retrieval changes, corpus mutation, LLM calls, entity extraction, alias resolution, relationship inference, and promoted records.
