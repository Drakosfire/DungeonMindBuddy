# Graph Memory Recap-Ingestion Source Artifact Materializer Gate v0

## Purpose

This gate determines whether the Graph Memory / Ontology / Taxonomy ladder is ready for a later PR to implement a real materializer for gate-admitted recap-ingestion source artifacts.

This gate allows a future PR to implement a real explicit-input materializer for gate-admitted recap-ingestion artifacts. It does not implement that materializer.

## Gate Decision

The decision is: allow a future explicit-input materializer only.

The future materializer may only operate inside the source-artifact, source-anchor, and source-unit contract described by the gate manifest. It remains diagnostic, candidate, ingested, or indexed source structure and does not promote narrative truth.

## Why This Gate Exists

The previous ladder rung proved with a synthetic fixture that each admitted recap-ingestion artifact family can be represented as `SourceArtifact -> SourceAnchor -> SourceUnit`. This gate adds the governance boundary needed before any later PR reads explicit recap-ingestion outputs.

## What A Future Materializer May Do

The future materializer may emit source artifacts, source anchors, source units, source refs, provenance, semantic-envelope states, and diagnostics. It must not emit entity facts, alias merges, relationship facts, promotion records, production adapter payloads, or runtime UI payloads.

## What A Future Materializer Must Not Do

A future materializer must not discover inputs, parse campaign truth, perform semantic extraction, create adapter payloads, or change runtime behavior. It must not implement `/plan` consumption, Agent Interaction consumption, graph retrieval, shadow retrieval, entity extraction, alias resolution, identity merges, relationship inference, fact promotion, canon promotion, corpus scanning, or corpus mutation.

## Explicit Input Policy

The future materializer must accept explicit inputs only. It must not scan directories, glob for recap artifacts, scan canonical corpus files, call runtime retrieval, query live play records, or use manifest context query.

The input contract is explicit file paths or a later explicitly supplied input bundle. Directory scanning, glob expansion, corpus scanning, manifest context query, live play query, runtime retrieval, and absolute path output remain forbidden.

## Output Policy

Future output must use a `SourceArtifact_SourceAnchor_SourceUnit_bundle` contract and include the full semantic envelope: source artifact, source anchor, source unit, source ref, provenance, evidence role, authority state, visibility state, lifecycle state, and canon state.

Full text output is not allowed. Graph IDs are not a public contract. Production adapter payloads are not allowed.

## Semantic Defaults

The future materializer must preserve defaults from the recap-ingestion source-family gate:

- `normalized_recap_markdown` remains played canon, ingested, source evidence, system derived, and GM private.
- `breadcrumbed_recap_markdown` remains played canon, indexed, navigation hint, system derived, and GM private.
- `frontmatter_seed_markdown` remains planning scaffold, candidate, not evidence, system derived, and internal diagnostic.
- `session_memory_jsonl_meta` remains candidate extraction, candidate, diagnostic only, system derived, and internal diagnostic.
- `corpus_impact_proof` remains diagnostic only, diagnostic, diagnostic only, diagnostic authority, and internal diagnostic.

## Source Artifact / Anchor / Unit Contract

The allowed output shape is source structure only. Admitted recap-ingestion artifacts may become `SourceArtifact` records with anchors and units when a later PR implements the materializer, but those outputs remain source-grounding structures rather than extracted campaign facts.

## Display Summary / Evidence Boundary

`display_summary` is not evidence. It may help inspect output, but it cannot satisfy source evidence requirements.

## Diagnostic And Proof Boundaries

`corpus_impact_proof` remains proof of ingestion behavior, not proof of narrative truth.

Diagnostic artifacts may explain source-processing behavior, but they do not become narrative evidence or played-canon claims.

## Relationship To Recap-Ingestion Source-Family Gate v0

This gate depends on the recap-ingestion source-family gate and preserves its admitted artifact IDs, semantic defaults, allowed shapes, and forbidden shapes. Any future materializer must keep those defaults unless a later gate explicitly permits an override.

## Relationship To Recap-Ingestion Source Artifact Fixture v0

This gate depends on the synthetic recap-ingestion source artifact fixture. The fixture proves that each admitted artifact family can be represented as `SourceArtifact -> SourceAnchor -> SourceUnit` without reading real recap outputs.

## Relationship To /plan And Agent Interaction

Graph-backed `/plan` and Agent Interaction consumption remain blocked until later gates explicitly promote measured materialized output into a surface adapter contract.

No runtime UI payloads, production adapter payloads, or Agent Interaction payloads are introduced by this gate.

## Deferred Work

Deferred work includes the real explicit-input recap-ingestion source artifact materializer, a materializer report, and projection-readiness reporting over measured materialized recap-ingestion artifacts.
