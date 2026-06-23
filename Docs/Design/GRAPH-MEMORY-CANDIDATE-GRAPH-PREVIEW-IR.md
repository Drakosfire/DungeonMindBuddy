# Graph Memory Candidate Graph Preview IR v0

## Purpose

Candidate Graph Preview IR v0 defines a pure, preview-only object model for recap-derived graph candidates. The candidate graph preview is a proposed memory diff, not committed graph memory.

## Why This Comes After Source Span Evidence Resolver

The source-span evidence resolver established bounded source refs that can be opened and highlighted. This IR uses those refs without embedding raw source text.

## Preview Is Not Truth

A preview is an inspectable proposal. It lets a GM review what the system may later ask to write, while keeping facts and canon unchanged.

## Candidate Graph Preview Shape

The shape includes candidate nodes, edges, session beats, proposed writes, ignored items, deferred items, semantic states, diagnostics, and evidence refs.

## Candidate Nodes

Nodes represent named entities and recap-important concepts such as groups, locations, warnings, clues, and threads.

## Unnamed-But-Important Nodes

A candidate graph preview must support unnamed-but-important nodes, not only named entities.

## Candidate Edges

Edges represent preview-only relationships between candidate nodes. Edge labels should be GM-readable, while relationship types may remain machine-oriented.

## Session Beats

Session beats are first-class preview records with ordering, summaries, involved nodes, unresolved thread refs, and evidence refs.

## Proposed Writes

Proposed writes preserve intent such as creating a node or edge, but they remain pending in v0. Preview approval is out of scope for v0. The IR preserves write intent but performs no writes.

## Ignored And Deferred Items

Ignored items show restraint when a recap detail should not become canon. Deferred items preserve uncertainty for later review without promoting it.

## Evidence Requirements

Every meaningful candidate node, edge, beat, and proposed write should carry resolvable evidence refs. Refs point to resolver-compatible source artifacts and anchors instead of copying full source text.

## Semantic State Requirements

Semantic state envelopes describe canon, lifecycle, evidence, authority, and visibility state. No candidate graph object may use a promoted lifecycle in v0.

## Diagnostics

Diagnostics assert that the fixture is preview-only and that extraction, LLM use, runtime wiring, `/plan`, Agent Interaction, corpus scanning, corpus mutation, fact promotion, and canon promotion are not active.

## Frontend Expectations

A future frontend can inspect labels, confidence, warnings, evidence counts, and openable/highlightable refs to answer whether the system understood a recap.

## Relationship To Future Extraction

Future extraction may populate this shape, but this contract does not extract entities or infer relationships from source text.

## Relationship To Future Approval

Future approval can consume proposed writes. Approval and graph memory writes are intentionally absent from v0.

## Relationship To Future Query Vocabulary

Future query vocabulary can read committed graph memory after approval. This IR does not implement query execution.

## Relationship To Agent Interaction Chips

Future Agent Interaction chips may display candidate graph preview summaries. This IR does not connect Agent Interaction.

## What This Does Not Do

This contract does not extract entities, does not resolve aliases, does not infer relationships from source text, does not promote facts, does not promote canon, does not connect `/plan`, and does not connect Agent Interaction.

## Deferred Work

Deferred work includes richer dogfood recap fixtures, hand-authored gold candidate graphs, extraction harnesses, approval mechanics, graph writes, query demos, and UI presentation.
