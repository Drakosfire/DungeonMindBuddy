# Graph Memory Projection-Safe Source Unit Fixture v0

## Purpose

This report records the eval-only projection-safe source unit fixture for the Graph Memory / Ontology / Taxonomy ladder.

The fixture answers whether a graph/source-unit-shaped record can be represented as a surface-safe payload while preserving source grounding, provenance, evidence role, lifecycle state, canon state, authority state, visibility state, and diagnostic boundaries.

This fixture proves shape compatibility only. It does not implement an adapter, does not connect `/plan` or Agent Interaction to graph memory, and does not change runtime behavior.

## What This Proves

The fixture proves that a tiny synthetic source-unit payload can carry the shared semantic envelope needed by Agent Interaction, `/plan`, and future DungeonMindBuddy surfaces without exposing graph internals as the public UI contract.

It also proves that projection-owned labels such as `projection_card` can sit beside ontology-owned fields without taking ownership of ontology semantics.

## What This Does Not Prove

This fixture does not prove graph retrieval quality, adapter behavior, Agent Interaction behavior, `/plan` consumption, shadow retrieval, entity extraction, alias resolution, relationship inference, corpus scanning, corpus mutation, or production behavior.

It does not copy full source text into a payload and does not validate any real campaign content.

## Fixture Shape

The fixture is stored at `evals/graph_memory_layer/examples/projection_safe_source_unit_minimal.json`.

It contains a synthetic `session_memory_unit` payload with:

- a stable projection `ref_id`
- a human-readable `label`
- a non-evidence `display_summary`
- a `source_anchor` with an opaque locator
- a `source_ref`
- a provenance chain
- the required lifecycle, canon, authority, visibility, and evidence-state fields
- diagnostic-only graph-node information under `diagnostics`

## Required Semantic Envelope

The projection-safe payload must carry `canon_state`, `lifecycle_state`, `evidence_role`, `authority_state`, `visibility_state`, `source_anchor`, `source_ref`, and `provenance`.

The fixture also requires `adapter_key`, `ref_id`, and `label` so future adapters or future surfaces can identify and display the payload without learning graph internals.

## Display Summary Is Not Evidence

`display_summary` is a UI/display convenience. It is never evidence.

A surface may render the summary, but the evidence role remains explicit in `evidence_role`. The validator rejects treating a display summary as source evidence or as an inferred evidence role.

## Opaque Locator Rules

Source grounding is represented through `source_anchor`, `source_ref`, and a locator object. The locator uses an opaque record identifier rather than an absolute filesystem path.

The fixture forbids raw ingestion internals such as `_normalized/`, `_breadcrumbed/`, `.records_meta.jsonl`, and `corpus_impact` as semantic payload content.

## Diagnostics Boundary

Graph node identifiers are diagnostic-only. If a graph node identifier appears, it must appear under `diagnostics` and must not become the public UI or adapter contract.

Validation codes and diagnostic notes are allowed inside `diagnostics` because they describe the fixture boundary rather than production behavior.

## Relationship To Agent Interaction

Agent Interaction can later use the same shared semantic envelope when it needs source-grounded, lifecycle-aware payloads. This fixture only proves that the envelope can be represented; it does not wire Agent Interaction to graph memory.

## Relationship To Future Graph Retrieval

Future graph retrieval or shadow retrieval can evaluate whether real source units are projection-ready. This fixture is intentionally static and synthetic so the ladder can validate the payload shape before retrieval, adapters, or corpus-scale reporting exist.

## Deferred Work

Deferred work includes projection-readiness reporting over materialized session-memory source units, adapter design, shadow retrieval evaluation, and any eventual `/plan` or Agent Interaction integration. Those future steps must remain separate from this shape-only fixture.
