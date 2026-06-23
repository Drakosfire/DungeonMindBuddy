# Graph Memory Source Span Evidence Resolver Contract v0

## Purpose

This contract defines how recap-ingestion source references resolve into bounded, UI-usable evidence objects for future Graph Memory previews. A preview graph without resolvable evidence is a pretty but untrustworthy graph.

## Why This Comes Before Candidate Graph Preview

Candidate graph previews need source evidence before nodes, edges, beats, and proposed writes can be trusted. The resolver proves source refs can become snippets, structured field previews, source metadata, and highlight targets without runtime integration.

## Source Ref IDs Are Machine Keys

`source_ref_id` is a machine-readable key, not a GM-facing label. Product UI should render readable source context such as source label, snippet, and open-source affordance rather than raw IDs by default.

## Source Span Ref Shape

A source span ref names a `source_ref_id`, `source_artifact_id`, optional source anchor, source metadata, and either a text span or a structured field path. Text line numbers are 1-based and inclusive. Character offsets are 0-based inside the selected line range. Structured paths use dot-path notation such as `chunking.sentence_units`.

## Resolved Evidence Shape

Resolved evidence includes source identity, source metadata, evidence role, visibility state, `can_open_source`, `can_highlight_span`, a bounded `preview_snippet`, optional bounded `surrounding_context`, optional text coordinates, optional `structured_path`, optional `structured_value_preview`, and visible warnings.

## Text Span Resolution

Text span resolution selects the requested inclusive line range and optional character offsets from an explicitly supplied text artifact registry. It does not read corpus files, scan directories, or load runtime state.

## Structured Field Resolution

Structured field resolution walks a dot-path through an explicitly supplied structured artifact mapping. The resolver returns a bounded string preview of the selected value. Missing paths produce visible resolution issues.

## Bounded Snippet Policy

The resolver must return bounded snippets or structured field previews, not full raw source artifacts. Long snippets are clipped and surfaced with a `snippet_truncated` warning. Surrounding context is separately capped.

## Highlightability

Text spans are highlightable when their line and optional character coordinates are valid. Structured field refs are highlightable in the documented structured-field sense when their dot-path resolves. The frontend should rely on `can_open_source` and `can_highlight_span` before presenting a graph candidate as evidence-backed.

## Unresolvable Evidence

Ordinary unresolvable evidence should not crash the caller. Missing artifacts, source-ref mismatches, out-of-range spans, missing structured paths, ambiguous text-plus-structured refs, and non-highlightable refs return visible warnings with severity and code.

## Frontend Expectations

The frontend can use resolved evidence to open a source drawer, scroll to a source line or structured field, and highlight the support for a claim. Normal GM-facing UI should show labels and snippets; debug UI may expose raw source IDs.

## Relationship To Candidate Graph Preview

Candidate graph preview IR can require every candidate node, edge, beat, proposed write, ignored item, and deferred item to carry evidence refs that resolve through this contract.

## Relationship To Agent Interaction Chips

Future Agent Interaction chips should consume already-resolved, evidence-backed graph results. This contract only defines source evidence needed by those future chips; it does not implement chip payloads.

## What This Does Not Do

This contract does not extract entities, does not resolve aliases, does not infer relationships, does not promote facts, does not promote canon, does not connect `/plan`, and does not connect Agent Interaction.

## Deferred Work

Deferred work includes candidate graph preview IR, rich recap fixtures, hand-authored graph gold fixtures, extraction contracts, preview UX, query vocabulary, Agent Interaction chip payload contracts, and approval/write intent contracts.
