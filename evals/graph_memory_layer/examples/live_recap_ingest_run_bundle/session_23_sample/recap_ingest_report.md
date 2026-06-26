# Live Recap Ingest Run Bundle — Session 23 Sample

## Purpose

Create a deterministic source-spanned dogfood run bundle from one explicitly supplied recap file.

## Boundary

This is a live recap ingest run bundle.
It was created from an explicit input file.
It does not call an LLM.
It does not execute extraction.
It does not generate a candidate graph.
It does not write graph memory.
It does not execute graph queries.
It does not connect /plan.
It does not connect Agent Interaction.
It does not scan or mutate corpus.
It does not promote facts or canon.
It does not change runtime behavior.

## Input Summary

- Run ID: `graph-memory:live-recap-ingest:session-23:sample-v0`
- Campaign: `longmont-c2`
- Session: `session-23`
- Input path record: `evals/graph_memory_layer/examples/session_23_recap_ingest/expected_normalized_recap.md`
- Input SHA-256: `afdd17e47b4cc1e8e1d5a7b3128ef6aec7fa83eed372648d502acfcd0395ea16`
- Input bytes: 9538
- Input lines: 38

## Source Artifact Summary

- Source artifact: `source-artifact:longmont-c2:session-23:live-recap-v0`
- Source type: `recap_markdown`
- Memory state: `not_memory`
- Approval state: `not_applicable`

## Source Units

- Total units: 14
- Paragraph units: 14
- Heading units: 0

## Source Span Index

- Source span refs: 14
- Stable IDs: true
- Line addressable: true
- Openable and highlightable: true

## Provenance

Every source unit is derived from the explicit input file and records line range plus text hash.

## Diagnostics

- Status: `ready`
- Warnings: 0
- Hard failures: 0

## Readiness For Live Extractor Dogfood

This run is ready to be used as input to a future gated live extractor dogfood harness if all source units and source span refs validate.

## What This Does Not Do

It does not call an LLM, execute extraction, generate candidate graph memory, write graph memory, execute graph retrieval or queries, connect /plan, connect Agent Interaction, scan or mutate corpus, promote facts, promote canon, or change runtime behavior.
