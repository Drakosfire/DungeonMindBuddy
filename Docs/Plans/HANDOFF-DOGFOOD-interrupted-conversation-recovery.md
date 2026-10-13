# DOGFOOD: interrupted conversation recovery

Status: ACTIVE by explicit PRIME dispatch after read-only diagnosis. Base origin/main@c4a81c6661dd292c6adb9d314ce4d154d1e78352. Branch codex/buddy-interrupted-conversation-recovery; non-serving integration checkout. Topology parallel-independent with SERVER backend delivery repair; no backend/public contract dependency beyond existing verified V3 terminal history. One UI implementation PR. Serving5202 checkout untouched.

Invariant: exact idempotency, World/conversation/provenance/committed basis correlation of failed/interrupted Graph Ask clears only its client pending lock and uncertainty without reposting. Preserve saved recovery envelope/audit and newer drafts/requests. A503 alone does not establish terminal state. Wrong/ambiguous/stale correlations stay locked.

Exclusive write set: this handoff; apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx; apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx; apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx. No styles, runtime, provider, Graph, APP contract or backend edits.

Verification: mounted onePOST503→running→interrupted with different durable Turn ID and exact correlation, no reload, one transcript row, controls recovered, envelope retained; negative correlation and newer draft/pending cases; application TypeScript; cumulative diff; commit/push/open PR for PRIME independent review. No new live provider or acceptance run released.

Failure critique: client request ID differs from durable history ID. Same text cannot prove identity. Terminal receipt must match exact submitted basis; interrupted cannot masquerade as completed. Storage changes/errors and newer pending operations cannot be cleared by old history. Recovery metadata must remain available.
