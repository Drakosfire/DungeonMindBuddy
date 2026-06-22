# Graph Memory Recap-Ingestion Explicit Real-Artifact Dogfood v0

## Purpose

This dogfood fixture tests the explicit-input recap-ingestion materializer and projection payload chain against one manually selected real or real-derived artifact bundle.

## What This Dogfood Tests

It tests whether a manually curated dogfood bundle can move through the explicit-input loader, materializer, materializer report, projection-readiness analyzer, and in-memory projection payload builder.

## What This Dogfood Does Not Test

This is not directory scanning, not corpus scanning, not runtime ingestion, not a production adapter, not a `/plan` payload, not an Agent Interaction payload, and not a retrieval result.

## Explicit Input Manifest

The dogfood bundle is admitted through `evals/graph_memory_layer/examples/recap_ingestion_real_artifact_dogfood/dogfood_manifest.json` using `explicit_paths_only` and exactly five manifest-listed relative file paths.

## Materializer Chain

The validator builds `RecapIngestionMaterializerInput` values only from manifest entries and then runs the existing recap-ingestion source artifact materializer.

## Projection Payload Chain

The dogfood validator builds a projection-safe payload shape in memory from the dogfood materialization. The fixture may contain dogfood input text, but reports and projection payloads must not copy full raw file contents.

## Safety Boundaries

This dogfood does not infer entities, does not resolve aliases, does not infer relationships, does not promote facts, and does not promote canon.

## Observed Results

A successful dogfood run means the shape and safety boundaries survived one realistic explicit artifact bundle. It does not prove production usefulness yet.

## Known Limitations

The bundle is a single redacted fixture and is too small to evaluate usefulness, recall, precision, graph traversal, adapter ergonomics, or player-facing behavior.

## Relationship To Projection Payload Fixture v0

The previous projection payload fixture used tiny synthetic explicit inputs. This dogfood reuses the same bounded payload expectations against a more realistic explicitly supplied bundle.

## Relationship To /plan And Agent Interaction

This report records no `/plan` integration and no Agent Interaction integration. It does not change runtime behavior.

## Deferred Work

The next rung should add a recap-ingestion dogfood evaluation report that analyzes usefulness, noisy output, missing affordances, and failure modes before any adapter or shadow-mode planning.
