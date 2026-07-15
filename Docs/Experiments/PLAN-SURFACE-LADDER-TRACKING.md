# Historical — Plan Surface Ladder Tracking

**Status:** Historical evidence only
**Original role:** Pre-World-Supergraph surface and Agent Interaction experiment tracking
**Superseded:** 2026-07-13

This experiment tracked the Plan/Play/Build surface ladder before the Campaign Supergraph roadmap became the sole implementation sequence. It no longer directs work and must not be used to place the app-level Agent Interaction provider lift ahead of graph retrieval or Hermes dogfood.

Current authority:

1. [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)
2. [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)
3. [`Docs/Design/ANCHOR-hermes-campaign-sensemaking-goal.md`](../Design/ANCHOR-hermes-campaign-sensemaking-goal.md)
4. [`Docs/Design/ANCHOR-plan-surface-agent-interaction.md`](../Design/ANCHOR-plan-surface-agent-interaction.md)

The active Agent Interaction sequence is:

```text
PR010A graph retrieval contract
  -> PR010B Hermes graph-retrieval dogfood
    -> PR011 app-level Agent Context + governed tool runtime
```

Surviving product lessons:

- Agent Interaction is not owned by `/plan`; an app-level provider remains the eventual target.
- Preserve the bottom Agent Interaction bar/pane interaction pattern.
- Plan and Play are consumer surfaces that publish ambient context.
- Plan remains the first dogfood surface; Play is the second-surface proof.
- Conversation continuity is non-canonical.
- The World Supergraph is the factual discovery plane, and source text is read only through graph-admitted anchors.

The original rung map and branch details remain available in Git history for archaeology.
