# Graph Memory Recap-Ingestion Source Artifact Fixture v0

## Purpose

This report documents the synthetic recap-ingestion source artifact fixture for the Graph Memory / Ontology / Taxonomy ladder.

This fixture proves shape compatibility only. It does not read real recap-ingestion outputs, does not implement a materializer, does not implement an adapter, does not connect `/plan` or Agent Interaction, and does not change runtime behavior.

## What This Fixture Proves

Each artifact family is represented as `SourceArtifact -> SourceAnchor -> SourceUnit`.

The fixture proves that the gate-admitted recap-ingestion artifact families can carry source artifact identity, source anchors, source units, source refs, provenance, and semantic envelope defaults without collapsing into entity facts, relationship facts, alias merges, or promotion records.

## What This Fixture Does Not Prove

This fixture does not prove that any real recap-ingestion output can be read, parsed, converted, or materialized. It does not scan corpus files, mutate corpus files, infer entities, resolve aliases, infer relationships, promote facts, authorize canon promotion, or provide runtime retrieval behavior.

## Fixture Shape

The fixture lives at `evals/graph_memory_layer/examples/recap_ingestion_source_artifacts_minimal.json` and uses opaque `synthetic://` locators. Each entry contains one source artifact, at least one source anchor, at least one source unit, a source ref, provenance, semantic defaults, and forbidden interpretations.

## Artifact Families Represented

The fixture includes one synthetic entry for each gate-admitted artifact family:

- `normalized_recap_markdown`
- `breadcrumbed_recap_markdown`
- `frontmatter_seed_markdown`
- `session_memory_jsonl_meta`
- `corpus_impact_proof`

## Semantic Defaults

The fixture preserves the gate manifest defaults for canon, lifecycle, evidence, authority, and visibility state. Artifact defaults and source-unit defaults match unless a future validator explicitly permits a narrow override.

## Source Artifact / Anchor / Unit Rules

Source artifacts identify the synthetic admitted family. Source anchors identify document, section, breadcrumb, frontmatter, metadata, or proof positions inside the opaque synthetic artifact. Source units reference anchors in the same artifact and include source refs plus provenance.

The normalized recap fixture entry may carry `source_evidence` only for the source artifact or explicit anchored section unit. It does not authorize entity extraction, alias resolution, relationship inference, fact promotion, or canon promotion.

## Display Summary Is Not Evidence

`display_summary` is a display convenience. It is not evidence.

Display summaries may help humans inspect a fixture entry, but they do not satisfy source evidence requirements and must not be treated as narrative truth.

## Diagnostic And Proof Boundaries

`corpus_impact_proof` is proof of ingestion behavior, not proof of narrative truth.

Frontmatter seed entries remain planning scaffold candidates, not played canon. Session-memory metadata remains diagnostic/candidate metadata, not promoted graph memory. Breadcrumbed recap entries are navigation hints, not blanket source evidence.

## Relationship To Recap-Ingestion Source-Family Gate v0

The fixture is validated against `evals/graph_memory_layer/recap_ingestion_source_family_gate.json`. If a fixture artifact is not gate-admitted or does not preserve the gate defaults, the validator blocks it.

## Relationship To Future Materializer Work

A future materializer gate may decide whether explicit recap-ingestion artifacts can be materialized from real inputs. This fixture does not make that decision and does not implement the materializer.

## Deferred Work

Deferred work includes a future recap-ingestion source artifact materializer gate, any later explicit-input materializer, projection-readiness checks over materialized recap-ingestion artifacts, and adapter work only after separate approval.
