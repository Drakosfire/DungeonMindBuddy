# Graph Memory Recap-Ingestion Source Ref / Provenance Linkage Hardening v0

## Purpose

This hardening adds stable source_ref_id coverage and explicit provenance-to-source-ref linkage to recap-ingestion source artifact materializer output.

## What Changed

The recap-ingestion source artifact materializer now emits a deterministic `source_ref_id` in every source unit `source_ref` and repeats the same value in every provenance record attached to that unit.

## Source Ref ID Contract

The source_ref_id is a diagnostic source-structure identifier. It is not a public UI contract and does not make graph IDs surface-owned.

`source_ref_id` values are deterministic, opaque, do not include absolute paths, do not include raw file contents, and are unique per materialized source unit for the same explicit inputs.

## Provenance Linkage Contract

Every provenance record attached to a materialized source unit links back to the same `source_ref_id` carried by that unit's `source_ref`.

## What This Hardening Enables

After this hardening, source-ref/provenance projection-readiness checks can verify stable source-reference identity and explicit provenance linkage over diagnostic materializer output.

## What This Hardening Does Not Do

This hardening does not implement adapters, does not connect `/plan`, does not connect Agent Interaction, does not perform retrieval, does not scan corpus files, does not mutate corpus files, does not infer entities, does not resolve aliases, does not infer relationships, does not promote facts, and does not promote canon.

It also does not create a projection payload fixture, does not add frontend or runtime routes, does not perform shadow retrieval, does not call LLMs, and does not change production behavior.

## Projection-Readiness Impact

After this hardening, the default explicit-input materializer output should pass the source-ref/provenance projection-readiness checks. Projection-ready remains diagnostic and does not mean production-ready.

## Relationship To Materializer v0

Materializer v0 remains explicit-input only. The hardening updates the diagnostic output contract for source refs and provenance records without adding discovery, corpus scanning, corpus mutation, full-text emission, or adapter payloads.

## Relationship To Materializer Report v0

Materializer Report v0 keeps the `missing_source_ref_id` and `missing_provenance_source_ref_link` issue codes for regression detection, but the default fixture output should no longer emit them.

## Relationship To Projection-Readiness v0

Projection-readiness now reports source-ref/provenance linkage as ready for the default explicit-input fixture output while remaining a diagnostic source-structure report.

## Relationship To /plan And Agent Interaction

This hardening does not connect `/plan`, does not connect Agent Interaction, and does not make graph identifiers public UI or surface-owned contracts.

## Deferred Work

Deferred work includes a later projection-safe payload fixture, later adapter design, optional real-artifact dogfood under explicit gates, shadow retrieval evaluation, retrieval integration, entity extraction, alias resolution, relationship inference, fact promotion, and canon promotion.
