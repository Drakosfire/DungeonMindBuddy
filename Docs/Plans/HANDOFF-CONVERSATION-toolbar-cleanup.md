# Conversation toolbar cleanup

Status: ACTIVE. PRIME owns this serial UI-only slice from remote main8c90f30ed7323e558204b67f89348360a53f847a in the existing buddy-context-loop checkout. Operator requested a conversation symbol and @ References in the toolbar, completed activity out of the composer, and removal of the lingering post-switch refresh notice.

Predecessor: Conversations library UI PR2110 merged8c90f30ed7323e558204b67f89348360a53f847a; delivered preserving-live union3f1dd157b468b396b1c02b7963418b5fdadf91a6. Its UI lease is released and desktop/narrow checks passed. Earlier library handoff is settled by that merge and this successor; broader reference goal remains paused.

Invariant: one reference input/state owner, same exact selected references and native search; only its trigger moves. Keep live progress and failure recovery visible. Completed activity remains accessible in Conversation options. Remove only the redundant success notice; retain actual warnings, request/pointer guards and drafts. No history/backend/schema/provider/data changes.

Exclusive paths: this handoff and predecessor handoff; planSurface/components/WorldPlanAgentConversation.tsx and owning worldHistory/Play/Build tests and agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx as needed; surface/SurfaceGraphReferenceInput.tsx/.css/.test.tsx. UI5202 delivery only after exact review/CI and process/claim lease re-anchor. API8000, APP/Core and evaluator55447 excluded. Open ingestion PRs2111/2108 and paused2104 do not overlap these paths.

Validation: owning reference/World history/Build/Play tests, TypeScript/build, independent Bugbot cumulative review, preserved-live integration review, actual desktop/narrow reference-menu/activity/draft checks. Diagnose slow history with read-only measurements separately; a confirmed performance fix is a successor, not an expansion of this UI PR. No new dependencies/environments.
