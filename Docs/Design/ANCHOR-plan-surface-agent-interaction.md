# Anchor — Plan Surface Agent Interaction

**Status:** Active surface reference; not sequencing authority
**Re-anchored:** 2026-07-13 after PR008A/PR008B

Agent Interaction began as a Plan-local bottom bar/pane and remains dogfooded first on `/plan`. Its current architectural direction is now governed by:

1. [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)
2. [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)
3. [`Docs/Design/ANCHOR-agent-interaction-hermes.md`](ANCHOR-agent-interaction-hermes.md)
4. [`Docs/Design/UX-STORIES-agent-interaction-hermes.md`](UX-STORIES-agent-interaction-hermes.md)

## Current state

- PR008A migrated Plan object cards, references, relationship traversal, and diagnostics to the revision-pinned World Supergraph projection.
- PR008B attached deterministic World Graph query context to Agent Interaction.
- Named local threads, citations, source reading, freshness metadata, and inspectable traces exist.
- The actual Hermes agent/session loop does not yet consume graph retrieval.
- App-level `AgentInteractionProvider` and cross-surface continuity remain future work.

## Surface role

Plan is a consumer surface. It publishes ambient context—world, campaign, focus, selected objects, active planning artifact—and hosts the first Agent Interaction dogfood. It does not own:

- graph storage or identity;
- retrieval semantics;
- source admission;
- campaign authority;
- Hermes memory policy;
- durable write rules.

## Immediate sequence

The next Agent Interaction work is not the provider hoist. The active sequence is:

```text
PR010A graph retrieval contract
  -> PR010B Hermes graph-retrieval dogfood on /plan
    -> PR011 app-level context and governed tool runtime
```

The provider lift belongs in PR011, after the Hermes read-only conversation shape and graph-only retrieval boundary have been dogfooded successfully. React `/play` remains a parallel surface migration under PR009.

## Retrieval invariant

Plan/Hermes factual discovery uses the World Supergraph only. Source documents are opened only through graph-admitted source anchors. There is no product fallback to manifests, corpus indexes, arbitrary Markdown search, or ambient chat memory.

A graph miss is rendered as a coverage gap and routed back toward ingestion/Graph Review—not hidden by a second retrieval plane.

## UI invariants

- Preserve the bottom Agent Interaction bar/pane pattern.
- Keep the answer primary and diagnostics collapsible.
- Connected objects are useful game information and should be clickable; revision and evidence mechanics are metadata.
- Store thread/session/source pointers, not corpus bodies or graph internals, in client persistence.
- Extend the existing surface for PR010B; do not redesign the entire Plan shell.
- Plan remains read-only for graph authority until PR011 governed tools.

## Future provider lift

PR011 may hoist Agent Interaction ownership into `AppChrome` so Plan and Play share thread/session continuity. The provider must still treat:

- World Supergraph + source anchors as factual authority;
- Hermes/thread state as non-canonical continuity;
- surface context as transient hints;
- writes as typed preview/confirm operations.

This anchor no longer directs implementers to start with R10/P4. Historical ladder documents remain background only.
