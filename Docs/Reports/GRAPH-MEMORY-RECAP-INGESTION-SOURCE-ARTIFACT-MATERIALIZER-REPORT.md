# Graph Memory Recap-Ingestion Source Artifact Materializer Report v0

## Purpose

This report inspects explicit-input recap-ingestion materializer output. It does not change materializer behavior, does not implement projection-readiness, does not create adapter payloads, does not connect `/plan`, and does not change runtime behavior.

The purpose of v0 is to make the output from the recap-ingestion source artifact materializer easier to review before any later projection-readiness evaluation begins.

## What This Report Measures

The report measures artifact coverage, source anchors, source units, source refs, provenance records, diagnostics, semantic state coverage, and structural gaps over the existing materializer output.

It answers whether all admitted recap-ingestion source artifact families are represented and whether each materialized artifact has at least one anchor and at least one source unit.

## What This Report Does Not Do

This report does not implement projection-readiness, adapters, `/plan`, Agent Interaction, graph retrieval, shadow retrieval, corpus scanning, corpus mutation, entity extraction, alias resolution, relationship inference, fact promotion, canon promotion, LLM calls, or production behavior changes.

This report is not a production surface adapter contract.

## Summary Metrics

The summary metrics include:

- source artifacts
- source anchors
- source units
- source refs
- provenance records
- diagnostics
- issues

## Artifact Rows

Each artifact row records the admitted artifact id, artifact kind, source layer, artifact id, anchor count, unit count, evidence role, canon state, lifecycle state, authority state, visibility state, diagnostic count, and issue count.

## Semantic State Counts

The report counts semantic states for:

- evidence roles
- canon states
- lifecycle states
- authority states
- visibility states

Expected v0 states include `source_evidence`, `navigation_hint`, `not_evidence`, `diagnostic_only`, `played_canon`, `planning_scaffold`, and `candidate_extraction`.

## Structural Coverage

Structural coverage checks whether artifacts have anchors and units, units have source refs and provenance, units have canon states and display summaries, and `display_summary` is marked as non-evidence.

`display_summary` is not evidence.

The report also checks for absolute path leaks, full-text field leaks, adapter payload fields, forbidden unit kinds, missing stable `source_ref_id` coverage, and missing provenance-to-source-ref linkage.

## Issue Classification

Issue severity is classified as `info`, `warning`, or `error`.

Warnings cover readiness concerns that do not necessarily violate Materializer v0, such as missing stable `source_ref_id` coverage or missing provenance-to-source-ref linkage.

Errors cover boundary violations such as missing source refs, missing provenance, absolute path leakage, full text leakage, adapter payload leakage, or forbidden entity/projection/promotion unit kinds.

## Known v0 Gaps

The report is allowed to surface structural gaps, including missing stable `source_ref_id` coverage or missing provenance-to-source-ref linkage. Reporting a gap is not a failure to preserve campaign truth; it is the reason this rung exists before projection-readiness.

Current Materializer v0 output may have source refs and provenance records without stable `source_ref_id` linkage. The report surfaces that condition honestly instead of inventing readiness.

## Relationship To Materializer v0

The report analyzes output from `materialize_recap_ingestion_source_artifacts`. It does not create a new materializer and does not alter materializer runtime behavior.

The report reads the materializer schema `dmb_recap_ingestion_source_artifact_materialization_v0` and created-by value `recap_ingestion_source_artifact_materializer_v0` as diagnostic identity fields.

## Relationship To Projection-Readiness

This rung prepares measurement for a future projection-readiness rung, but it is no projection-readiness implementation. The next rung can decide whether materialized recap-ingestion artifacts are projection-ready.

## Relationship To /plan And Agent Interaction

The report does not connect `/plan`, does not create plan chips, does not create Agent Interaction payloads, and does not expose runtime UI payloads.

## Deferred Work

Deferred work includes projection-readiness evaluation, stable source-ref identifiers if needed, explicit provenance-to-source-ref linkage, adapter design, retrieval integration, entity extraction, alias resolution, relationship inference, fact promotion, and canon promotion.
