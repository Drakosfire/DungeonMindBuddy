# Graph Memory Recap-Ingestion Source-Family Gate v0

## Purpose

This report records the admission gate for the `recap_ingestion_source_artifacts` source family before any recap-ingestion materializer, adapter, projection, runtime consumption, or UI integration exists.

The gate answers whether current recap-ingestion outputs may later be represented as `SourceArtifact -> SourceAnchor -> SourceUnit` structures without treating ingestion artifacts as campaign truth.

## Gate Decision

This gate admits explicit recap-ingestion artifacts as future source artifacts, anchors, and units only. It does not admit extracted campaign facts, identity merges, alias relationships, relationship inference, graph traversal, runtime consumption, `/plan` integration, Agent Interaction integration, or corpus mutation.

The active decision is `admit_explicit_recap_ingestion_artifacts_as_source_artifacts_only`.

## What Is Admitted

The gate admits these artifact families for future explicit-input-only materialization work:

- normalized recap markdown as a source artifact, document anchor, or explicitly anchored section unit;
- breadcrumbed recap markdown as a source artifact, breadcrumb anchor, or reference/navigation unit;
- frontmatter seed markdown as a source artifact, frontmatter-field anchor, or candidate seed unit;
- session-memory JSONL/meta as a source artifact, metadata anchor, or diagnostic source unit;
- `corpus_impact` proof metadata as a source artifact, proof anchor, or diagnostic proof unit.

## What Is Not Admitted

This gate does not admit a recap-ingestion materializer, adapter implementation, runtime UI payload, graph retrieval path, shadow retrieval path, `/plan` behavior, Agent Interaction behavior, prompt change, corpus scan, corpus mutation, entity extraction, alias resolution, relationship inference, fact promotion, or canon promotion.

It also blocks unrelated source families such as canonical corpus scans, live play records, manifest context queries, runtime retrieval results, and Tiptap documents.

## Artifact Default Semantics

| Artifact | Canon | Lifecycle | Evidence | Authority | Visibility |
|---|---|---|---|---|---|
| normalized recap markdown | `played_canon` | `ingested` | `source_evidence` | `system_derived` | `gm_private` |
| breadcrumbed recap markdown | `played_canon` | `indexed` | `navigation_hint` | `system_derived` | `gm_private` |
| frontmatter seed markdown | `planning_scaffold` | `candidate` | `not_evidence` | `system_derived` | `internal_diagnostic` |
| session-memory JSONL/meta | `candidate_extraction` | `candidate` | `diagnostic_only` | `system_derived` | `internal_diagnostic` |
| `corpus_impact` proof metadata | `diagnostic_only` | `diagnostic` | `diagnostic_only` | `diagnostic` | `internal_diagnostic` |

Frontmatter seed output is planning scaffold or candidate extraction metadata, not played canon by default.

Breadcrumbed recap output is navigation/reference structure by default. It must not become blanket source evidence unless a specific source anchor supports the claim.

Normalized recap markdown may be treated as source evidence for the recap artifact or anchored recap sections, but not as permission to infer entities, aliases, relationships, or promoted facts.

## Source Artifact / Anchor / Unit Boundary

The boundary is shape-first and explicit-input-only:

- `SourceArtifact` may identify an admitted recap-ingestion artifact family.
- `SourceAnchor` may identify an explicit document, breadcrumb, frontmatter field, metadata field, or proof locator.
- `SourceUnit` may be created later only when an explicit materializer maps a specific admitted artifact and anchor into a bounded source/proof/diagnostic unit.

Raw `_normalized/`, `_breadcrumbed/`, `.records_meta.jsonl`, and `corpus_impact` implementation details remain opaque locators. They must not become downstream semantic model names.

## Diagnostic And Proof Metadata

`corpus_impact` is proof of ingestion behavior, not proof of narrative truth.

Session-memory JSONL/meta and `corpus_impact` proof metadata remain diagnostic-only unless a later gate and materializer define stricter source anchoring rules. Diagnostic metadata can explain how ingestion behaved, but it cannot prove what happened in the campaign narrative.

## Forbidden Collapses

This gate forbids these collapses:

- normalized recap markdown into extracted entity, alias, relationship, or promotion facts;
- breadcrumbed recap markdown into blanket source evidence;
- frontmatter seed markdown into played canon facts;
- session-memory metadata into promoted graph memory;
- `corpus_impact` proof metadata into narrative evidence;
- display summaries into evidence;
- raw ingestion internals into semantic vocabulary;
- source-family admission into runtime consumption.

## Relationship To Projection-Readiness Report v0

Projection-Readiness Report v0 measured whether current materialized session-memory source-unit output has enough shared semantic envelope fields for future projection-safe payloads.

This gate comes after that measurement and broadens the question from one current session-memory output shape to multiple recap-ingestion artifact families. It still does not build projections, adapters, graph traversal, or runtime consumption.

## Relationship To Agent Interaction And /plan

This gate does not change Agent Interaction, `/plan`, live-control runtime behavior, UI behavior, planner retrieval routing, prompts, or production retrieval. The manifest and validator are eval-only governance artifacts.

No adapter/runtime/UI changes are made or authorized by this gate.

## Deferred Work

Deferred work includes:

- `recap_ingestion_source_artifact_fixture_v0`;
- `recap_ingestion_source_artifact_materializer_v0`;
- projection-readiness reporting over recap-ingestion artifacts.

Those future steps must continue to avoid real artifact directory scanning, corpus scanning, corpus mutation, runtime consumption, `/plan` integration, Agent Interaction integration, entity extraction, alias resolution, relationship inference, and fact promotion unless explicitly gated by a later PR.
