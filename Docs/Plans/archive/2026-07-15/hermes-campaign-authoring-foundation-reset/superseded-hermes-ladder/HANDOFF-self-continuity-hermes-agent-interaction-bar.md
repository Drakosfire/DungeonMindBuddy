# Historical handoff — Hermes Agent Interaction Bar

**Status:** Historical evidence only
**Original date:** 2026-06-22
**Superseded:** 2026-07-13

This handoff described the pre-World-Supergraph Hermes CLI/manifest-retrieval spike. It is no longer an implementation authority and must not be used to reintroduce:

- `hermes --oneshot` as the product runtime;
- manifest/corpus/lexical retrieval as a fallback plane;
- arbitrary Markdown reads;
- metadata-only thread continuity as the target state.

Current authority and active references:

1. [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)
2. [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](PR-TRACKER-campaign-supergraph.md)
3. [`Docs/Design/ANCHOR-agent-interaction-hermes.md`](../Design/ANCHOR-agent-interaction-hermes.md)
4. [`Docs/Design/UX-STORIES-agent-interaction-hermes.md`](../Design/UX-STORIES-agent-interaction-hermes.md)
5. [`.hermes.md`](../../.hermes.md)

The original implementation details remain available in Git history for archaeology. The surviving lessons have been consolidated into the active anchor: inspectable tool use, same-thread continuity, explicit memory boundaries, cite-or-abstain behavior, and Hermes as the actual agent runtime.
