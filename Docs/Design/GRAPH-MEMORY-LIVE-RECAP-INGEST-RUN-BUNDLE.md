# Graph Memory Live Recap Ingest Run Bundle v0

## Purpose

This PR adds explicit-input live recap ingestion only. It does not execute extraction or generate candidate graph memory.

## Why This Comes After Query Vocabulary Fixture

The query vocabulary fixture proved the questions and safety boundaries that later graph memory must serve. The live recap ingest run bundle now creates the source-spanned input seam needed before any gated live extractor can answer those questions.

## Re-Anchored Dogfood Goal

The workstream has re-anchored from static Agent Interaction planning toward first live recap dogfood.

## Explicit Input Boundary

The runner must process only the explicitly supplied input file and must not scan campaign folders or corpus directories.

## Source Inputs

The source is one operator-provided recap Markdown file. The checked-in sample uses a deterministic Session 23 fixture path.

## Run Bundle Outputs

The bundle emits `run_manifest.json`, `source_artifact.json`, `source_units.json`, `source_span_index.json`, `provenance_index.json`, `diagnostics.json`, and `recap_ingest_report.md`.

## Source Artifact Contract

The source artifact records campaign/session identity, source hash, child artifact paths, `raw_text_included: false`, and `memory_state: not_memory`. The run bundle is not campaign memory. It is source material prepared for future dogfood extraction.

## Source Unit Contract

Source units are deterministic heading/paragraph units with line ranges, character ranges, bounded previews, text hashes, and stable IDs.

## Source Span Index Contract

Every source unit receives a stable, line-addressable, openable, highlightable span ref for future extractor citations.

## Provenance Contract

Provenance records explicit-file input metadata and unit-level derivation from the input recap.

## Diagnostics Contract

Diagnostics assert explicit input only and deny LLM execution, extraction, candidate graph output, graph writes, query execution, corpus scan/mutation, `/plan`, Agent Interaction, and runtime changes.

## CLI Contract

The live CLI requires `--campaign-id`, `--session-id`, `--input`, and `--out`; rejects missing, directory, glob, and default corpus inputs; and writes normal runs only under `evals/graph_memory_layer/runs/live_recap_ingest/`.

## Checked-In Sample Run

The deterministic Session 23 sample lives under `evals/graph_memory_layer/examples/live_recap_ingest_run_bundle/session_23_sample/`.

## Manual Dogfood Run Directory

Manual ad hoc runs belong under `evals/graph_memory_layer/runs/live_recap_ingest/`, which is gitignored except for its `.gitignore` sentinel.

## Determinism Requirements

The sample run has no timestamps, no absolute local paths, no environment-specific paths, and stable source unit/span IDs.

## Readiness For Gated Live Extractor Dogfood

This run bundle is ready for a future gated live extractor dogfood harness only if source units, source span refs, provenance, and diagnostics validate.

## Why This Is Not Extraction

The runner performs mechanical markdown unitization only. It does not infer entities, relationships, beats, facts, canon, aliases, graph candidates, or writes.

## What This Does Not Do

No live model execution, live extraction, graph writes, approval persistence, graph retrieval, graph queries, corpus scanning, corpus mutation, /plan integration, Agent Interaction integration, fact promotion, canon promotion, production frontend routing, or runtime behavior changes are introduced by this PR.

## Deferred Work

Deferred work includes the live extractor prompt pack, no-CI-live-model dogfood harness, candidate graph generation, approval mechanics, graph retrieval, query execution, `/plan`, Agent Interaction, and production UI integration.
