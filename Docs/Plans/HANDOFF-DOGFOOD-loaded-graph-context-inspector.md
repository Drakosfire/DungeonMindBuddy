# DOGFOOD: inspect loaded graph from conversation context

Status: ACTIVE, directly authorized by the user on 2026-10-11: add navigation from What Buddy sees to a detailed view of the loaded graph.
Topology: serial successor to automatic-chat-reconciliation PR #1077, merged at 4a32c3bf0eaf2a4933667410415708c7bc59b551. Base is this fetched main merge; the cumulative delta contains only the graph inspector capability. PRIME reviewed the predecessor in comment 6115459103. The predecessor recovery code is inherited unchanged.
Branch/check-out: codex/loaded-graph-context-inspector, /tmp/buddy-automatic-chat-reconciliation.
Write lease: this handoff, apps/live-control-ui/src/graphLens/LoadedWorldGraphExplorer.tsx, its CSS and test, plus the additive import/mount in apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx. Merged recovery source is inherited unchanged; the conversation path is sequentially transferred for this additive inspector only.
Runtime: no launch, provider, database, graph write or deployment lease.

Invariant: inspect only the current shared verified World projection. This is not a claim that every graph node is loaded or that this projection is the evidence sent to a provider. The view explicitly separates loaded projection from per-question evidence. World switches reset the view; loading/unavailable projections remove old node content. A truncated projection is flagged. Opening/searching/following loaded adjacency performs no fetch or mutation.

Implementation: Explore loaded graph opens an accessible dialog with alias/name/kind search, summaries, sources and navigable loaded connections. Unloaded connection targets are labeled rather than inferred/fetched. Long lists have explicit Show more; small screens stack the browser and detail panes. Escape/Close restores launcher focus; diagnostic IDs are collapsed.

Verification: app TypeScript check passed. Full conversation consumer and inspector tests: 181 passed, including no-fetch exploration, alias search, connection navigation, unavailable-projection removal and managed-World reset. Diff check passed. No live Agent turn or operator state mutation.
