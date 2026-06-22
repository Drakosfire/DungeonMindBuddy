# Graph Memory Projection-Readiness Report v0

## Purpose

This report measures whether materialized graph/source-unit records are ready to become projection-safe surface payloads. It does not implement a projection adapter and does not produce runtime UI payloads.

## What This Measures

Projection-readiness reporting measures whether materialized session-memory source-unit records have enough source grounding, provenance, lifecycle, canon, evidence, authority, and visibility metadata to become projection-safe surface payloads in a future adapter.

## What This Does Not Do

This report does not implement adapters, touch `/plan`, change Agent Interaction, change frontend or runtime behavior, add graph retrieval, shadow retrieval, entity extraction, alias resolution, relationship inference, corpus scanning, corpus mutation, prompt changes, or production retrieval changes.

## Required Semantic Envelope

The report checks these semantic-envelope fields for each materialized source-unit record:

```text
adapter_key
ref_id
label
source_anchor
source_ref
provenance
evidence_role
authority_state
visibility_state
lifecycle_state
canon_state
```

## Readiness States

- `ready`: all required fields can be derived safely from the materialized graph record without invented semantics.
- `degraded`: a surface-safe payload could be displayed only as diagnostic or partial, with missing optional display fields or weak labels.
- `blocked`: required semantic-envelope fields are missing or unsafe.

## Missing Field Policy

Missing required fields are reported as gaps. The report does not silently invent semantic state. In particular, `canon_state` must be present in materialized graph/source-unit records or reported missing; the report does not upgrade diagnostic records into canon.

## Display Summary / Evidence Boundary

Display labels or future display summaries are not evidence. The readiness report may diagnose whether a display summary would be safe, but `display_summary` is not counted as evidence and cannot satisfy `source_ref`, `source_anchor`, `provenance`, or `evidence_role` requirements.

## Diagnostics Boundary

Graph node IDs may appear only as diagnostic/report row identifiers. The report does not expose full text fields such as `lexical_plain`, raw Markdown bodies, JSONL bodies, or raw ingestion internals such as normalized or breadcrumbed corpus paths.

## Relationship To Projection-Safe Source Unit Fixture v0

Projection-Safe Source Unit Fixture v0 proved that one static, synthetic, projection-safe source-unit-shaped payload can satisfy the surface vocabulary boundary. Projection-Readiness Report v0 instead measures real materialized session-memory source-unit records and reports which required fields are ready, degraded, or blocked before any future adapter exists.

## Relationship To Agent Interaction and /plan

This report is eval-only and report-only. It does not connect Agent Interaction, does not serve `/plan`, does not change live-control UI behavior, and does not create runtime UI payloads.

## Deferred Work

Deferred work includes any actual projection adapter, `/plan` integration, Agent Interaction integration, graph-backed retrieval, shadow retrieval, recap-ingestion source-family admission, entity extraction, alias resolution, relationship inference, corpus scanning, corpus mutation, and production behavior changes.
