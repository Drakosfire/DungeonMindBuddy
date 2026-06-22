# Graph Memory Recap-Ingestion Source Artifact Materializer v0

## Purpose

This report documents the first explicit-input recap-ingestion source artifact materializer for the Graph Memory / Ontology / Taxonomy ladder.

## What This Materializer Does

This materializer reads explicitly supplied recap-ingestion artifact inputs and emits diagnostic source artifacts, anchors, units, source refs, provenance, semantic-envelope states, and diagnostics.

## What This Materializer Does Not Do

This materializer does not discover files, scan directories, glob for recap artifacts, scan canonical corpus files, mutate corpus files, query runtime retrieval, connect `/plan`, connect Agent Interaction, create adapter payloads, infer entities, resolve aliases, infer relationships, promote facts, or promote canon.

## Explicit Input Contract

Callers must provide explicit `RecapIngestionMaterializerInput` records. The materializer accepts file paths only for gate-admitted artifact IDs and rejects empty inputs, unknown IDs, duplicate IDs, directories, and non-file paths. It has no directory, glob, discovery, corpus, live-play, or runtime-retrieval entry point.

## Output Contract

The output schema is `dmb_recap_ingestion_source_artifact_materialization_v0`. It emits a diagnostic bundle of `SourceArtifact -> SourceAnchor -> SourceUnit` records, source refs, provenance records, semantic-envelope states, and diagnostics. The output is not a production surface adapter contract.

## Artifact Family Semantics

The admitted family is `recap_ingestion_source_artifacts`. The admitted artifact IDs are `normalized_recap_markdown`, `breadcrumbed_recap_markdown`, `frontmatter_seed_markdown`, `session_memory_jsonl_meta`, and `corpus_impact_proof`, with defaults loaded from the source-family and materializer gates.

## Source Artifact / Anchor / Unit Rules

Each explicit input yields one source artifact, at least one source anchor, and at least one source unit. Units point to local anchors and include source refs, provenance, canon state, lifecycle state, evidence role, authority state, visibility state, and diagnostics.

## Display Summary / Evidence Boundary

`display_summary` is not evidence. Display summaries are generated from artifact type and file-name-level context rather than raw recap text.

## Diagnostic And Proof Boundaries

Diagnostic artifacts remain diagnostic or candidate outputs. `corpus_impact_proof` remains proof of ingestion behavior, not proof of narrative truth.

## Relationship To Materializer Gate v0

The materializer honors `evals/graph_memory_layer/recap_ingestion_source_family_gate.json` and `evals/graph_memory_layer/recap_ingestion_source_artifact_materializer_gate.json`. It preserves explicit input only, no adapter output, no runtime consumption, no corpus scanning, no corpus mutation, and no promotion.

## Relationship To Projection-Readiness Reporting

This rung emits inspectable materializer output. Projection-readiness over materialized recap-ingestion artifacts is deferred to a later rung and must remain diagnostic until separately gated.

## Relationship To /plan And Agent Interaction

The materializer does not connect `/plan`, Agent Interaction, graph retrieval, shadow retrieval, frontend runtime routes, or production behavior. Any future surface use must go through later gates and adapters.

## Deferred Work

Deferred work includes richer materializer reporting, projection-readiness over materialized recap-ingestion artifacts, adapter design, shadow retrieval evaluation, and any future promotion gate. Entity extraction, alias resolution, relationship inference, fact promotion, and canon promotion remain out of scope.
