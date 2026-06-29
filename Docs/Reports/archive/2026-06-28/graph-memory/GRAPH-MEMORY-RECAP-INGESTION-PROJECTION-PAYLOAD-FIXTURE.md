# Graph Memory Recap-Ingestion Projection Payload Fixture v0

## Purpose

This report documents an eval-only recap-ingestion projection payload fixture over the hardened explicit-input source artifact materializer output.

This fixture proves that hardened recap-ingestion source-unit output can be represented as a bounded projection-safe payload shape for future adapter design.

## What This Fixture Proves

The fixture proves that five gate-admitted recap-ingestion artifact families can be represented as bounded payload units with source-unit identity, `source_ref_id`, provenance linkage, display labels, non-evidence display summaries, semantic state envelopes, opaque source handles, diagnostics, and safety flags.

## What This Fixture Does Not Prove

This fixture is not a production adapter, not a `/plan` payload, not an Agent Interaction payload, not a runtime UI payload, and not a retrieval result.

This fixture does not scan corpus files, does not mutate corpus files, does not infer entities, does not resolve aliases, does not infer relationships, does not promote facts, and does not promote canon.

## Payload Shape

The static example fixture lives at `evals/graph_memory_layer/examples/recap_ingestion_projection_payload_minimal.json`. It contains five `payload_units`, one for each admitted recap-ingestion artifact family, and a diagnostic-only envelope declaring that the shape is not runtime behavior.

## Source Ref / Provenance Requirements

The fixture preserves `source_ref_id` and provenance-to-source-ref linkage, but `source_ref_id` remains diagnostic source structure and is not a public UI contract.

Every payload unit carries a `source_ref_id`, and every provenance record links to the same `source_ref_id`.

## Semantic State Envelope

Every payload unit preserves the source-unit semantic state envelope: `canon_state`, `lifecycle_state`, `evidence_role`, `authority_state`, and `visibility_state`.

## Opaque Source Handles

Source handles use an `opaque-source-handle` identifier and an explicit-input scheme value that avoids absolute paths, raw file names, raw fixture contents, and raw ingestion internals.

## Display Summary / Evidence Boundary

`display_summary` is not evidence.

Display labels and summaries are bounded presentation hints only. They do not replace source evidence, do not promote facts, and do not promote canon.

## Adapter Boundary

The fixture is a diagnostic projection payload fixture only. It is not the final surface adapter contract, does not create an adapter payload, and does not change production behavior.

## Relationship To Projection-Readiness

The validator first requires recap-ingestion projection-readiness to be `ready`. The fixture is accepted only after the materializer report and projection-readiness checks confirm source-ref coverage, provenance linkage, semantic envelope preservation, and surface-safety boundaries.

## Relationship To /plan And Agent Interaction

The fixture does not connect `/plan`, does not emit plan chips, does not emit plan cards, does not connect Agent Interaction, and does not define Agent Interaction payload fields.

## Deferred Work

Future work may add a carefully selected explicit real-artifact dogfood fixture outside runtime. Adapter design, graph retrieval, shadow retrieval, entity extraction, alias resolution, relationship inference, fact promotion, canon promotion, `/plan` integration, Agent Interaction integration, and runtime UI behavior remain deferred.
