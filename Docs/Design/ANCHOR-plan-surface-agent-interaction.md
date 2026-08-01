# Anchor — Plan Surface Agent Interaction

> **RE-ANCHOR (2026-08-01):** App-level projection host (**PR #441 / R10a**) and
> neutral **`graphReference`** (**PR #431 / MC-02a**) are **landed primitives**.
> Plan is a **characterized consumer** — not the shared API owner. Shared chrome
> authority:
> [`ARCHITECTURE-surface-interaction-layer.md`](ARCHITECTURE-surface-interaction-layer.md).
> Remaining provider/bar hoist sequencing:
> [`PLAN-surface-interaction-hoist-build-first.md`](../Plans/PLAN-surface-interaction-hoist-build-first.md).

**Status:** Active surface reference; not sequencing authority
**Re-anchored:** 2026-07-15 after the Hermes Campaign Authoring Foundation reset

Agent Interaction began as a Plan-local bottom bar/pane and remains dogfooded first on `/plan`. Its current architectural direction is now governed by:

1. [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)
2. [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)
3. [`Docs/Design/ANCHOR-hermes-campaign-sensemaking-goal.md`](ANCHOR-hermes-campaign-sensemaking-goal.md)
4. [`Docs/Design/ARCHITECTURE-hermes-campaign-authoring-foundation.md`](ARCHITECTURE-hermes-campaign-authoring-foundation.md)
5. [`Docs/Design/UX-STORIES-hermes-campaign-authoring-foundation.md`](UX-STORIES-hermes-campaign-authoring-foundation.md)

The Hermes documents above are the active reset surface. The old graph-only anchor
and Rung-based stories remain only as compatibility stubs pointing to the dated
archive.

## Current state

- PR008A migrated Plan object cards, references, relationship traversal, and diagnostics to the revision-pinned World Supergraph projection.
- PR008B attached deterministic World Graph query context to Agent Interaction.
- Named local threads, citations, source reading, freshness metadata, and inspectable traces exist.
- The current Hermes branch contains a bounded graph-agent turn and visible-prose
  continuity path; the branch is not yet the accepted `main` product path.
- App-level `AgentInteractionProvider` owns the **projection host** (R10a / #441 landed).
  Cross-surface Tool/Edit/Nav hoist and bottom bar/pane remainder are tracked under
  [`PLAN-surface-interaction-hoist-build-first.md`](../Plans/PLAN-surface-interaction-hoist-build-first.md).

## Surface role

Plan is a consumer surface. It publishes ambient context—world, campaign, focus, selected objects, active planning artifact—and hosts the first Agent Interaction dogfood. It does not own:

- graph storage or identity;
- retrieval semantics;
- source admission;
- campaign authority;
- Hermes memory policy;
- durable write rules.

## Immediate sequence

The next Interaction Layer work is **SI-01 characterize Plan contributions**, then
shared Tool/Edit host hoist (SI-02) — not a Plan-local provider rewrite.

```text
SI-01 characterize Plan publications
  -> SI-02 hoist shared Tool / Edit hosts
    -> SI-03 recompose Plan (characterized consumer)
      -> SI-04 Build World Reference Loop
```

Hermes/graph retrieval sequencing remains under Campaign Supergraph tracker. R10b
(bottom bar/pane + localStorage Phase A) is parallel, not a blocker for SI-01.

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

PR011 / R10b may complete Agent Interaction **chrome** (bottom bar/pane) while
preserving the R10a projection host. The provider must still treat:

- World Supergraph + source anchors as factual authority;
- Hermes/thread state as non-canonical continuity;
- surface context as transient hints;
- writes as typed preview/confirm operations.

This anchor no longer directs implementers to start with R10/P4. Historical ladder documents remain background only.
