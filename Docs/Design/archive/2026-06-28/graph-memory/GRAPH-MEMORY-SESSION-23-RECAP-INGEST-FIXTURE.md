# Graph Memory Session 23 Recap Ingest Fixture v0

## Purpose

This PR bridges Graph Memory to the existing recap-ingest spine instead of creating a parallel graph-memory-only normalization path.

## Why This Comes Before Session 23 Gold Graph

This fixture exists so the later hand-authored Session 23 candidate graph gold fixture can point to stable, meaningful source spans.

## Relationship To Existing Recap Ingest Workflow

The expected normalized recap fixture must be produced mechanically by existing recap ingest helpers, not by editorial rewrite.

## Raw Source Boundary

The saved raw Session 23 recap is raw source input, not canonical graph memory.

## Mechanical Normalization

The fixture uses `src.agent.recap_ingest_helpers.assemble_recap` to produce the normalized recap deterministically.

## Paragraph And Source-Line Provenance

The paragraph index preserves source-line provenance from the raw recap and bounded paragraph previews for review.

## Source Span Seed Refs

Source span seed refs resolve against the normalized recap and check expected phrases so refs are meaningful evidence, not headings.

## Why This Is Not Graph Extraction

No entities, relationships, nodes, edges, or candidate graph output are produced.

## Why This Is Not Corpus Mutation

The fixture reads only an explicit raw fixture path and checked-in fixture artifacts. It does not write corpus files.

## Future Use By Gold Candidate Graph

The next backend rung should hand-author Session 23 Candidate Graph Preview gold data against this normalized/source-span surface.

## Future Use By Multi-Pass Extraction

Later extraction contracts can compare their output against a manually authored gold graph after that gold graph exists.

## What This Does Not Do

This PR does not call an LLM, does not run the live planner, does not write corpus files, does not extract entities, does not infer relationships, does not produce a candidate graph, does not produce a gold graph, does not promote facts, does not promote canon, does not connect `/plan`, and does not connect Agent Interaction.

## Deferred Work

Deferred work includes the Session 23 Hand-Authored Candidate Graph Gold Fixture v0 and later multi-pass extraction evaluation.
