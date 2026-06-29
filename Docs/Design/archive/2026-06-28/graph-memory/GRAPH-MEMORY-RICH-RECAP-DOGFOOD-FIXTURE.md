# Graph Memory Rich Recap Dogfood Fixture v0

## Purpose

This fixture is source material for future graph-preview dogfood, not extracted graph output. The purpose of this fixture is to be rich enough that a future hand-authored gold candidate graph can be meaningful.

## Why This Comes After Candidate Graph Preview IR

Candidate Graph Preview IR can now describe future preview objects and evidence refs, so the workstream needs richer source material to judge whether that preview shape is useful.

## Why The Previous Fixture Was Too Thin

The previous dogfood source fixture was useful for explicit-path safety and projection shape, but it was too small to exercise named entities, unnamed-important concepts, session beats, unresolved threads, ignored details, deferred details, and ambiguity together.

## Fixture Contents

The fixture contains five explicit recap-ingestion artifacts: normalized recap markdown, breadcrumbed recap markdown, frontmatter seed markdown, session memory metadata, and corpus impact proof JSON.

## Declared Richness Requirements

The fixture intentionally includes named entities, unnamed-important concepts, session beats, relationships, unresolved threads, ignored details, deferred details, and ambiguity.

## Source Span Coverage

The fixture includes valid source span refs covering text spans and structured JSON paths so source evidence can be opened and highlighted without copying full raw source artifacts.

## Relationship To Source Span Evidence Resolver

The source span refs use the source-span evidence resolver contract and focus on valid, inspectable evidence coverage rather than invalid-ref behavior.

## Relationship To Candidate Graph Preview IR

This fixture does not produce Candidate Graph Preview IR output. It provides source material that a later preview or gold fixture can cite.

## Relationship To Future Gold Candidate Graph

The next backend rung should define a hand-authored gold candidate graph preview for this rich recap using Candidate Graph Preview IR v0 and Source Span Evidence Resolver Contract v0.

## What This Does Not Do

This PR does not extract entities, does not infer relationships, does not produce a candidate graph preview, does not produce a gold graph, does not write graph memory, does not approve writes, does not promote facts, does not promote canon, does not connect `/plan`, and does not connect Agent Interaction.

## Deferred Work

Deferred work includes hand-authoring the expected candidate graph preview, judging graph usefulness, and deciding whether future extraction should target these fixture relationships.
