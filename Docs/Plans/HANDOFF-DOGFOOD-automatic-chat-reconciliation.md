# DOGFOOD: automatic chat reconciliation

Status: ACTIVE; direct user authorization to implement automatic reconciliation without resending (2026-10-11).
Base: origin/main b37515998f30ea50742274254faa8a2832ef6116.
Branch/check-out: codex/automatic-chat-reconciliation, /tmp/buddy-automatic-chat-reconciliation.
Topology: serial, one implementation PR. Open PRs inspected; no active chat-recovery overlap identified.

Write lease: this handoff, apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx, apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx.
Runtime: no server, provider call, database, deployment or port ownership change.

Invariant: pending Plan Graph Asks trigger history GETs only; never resend an Ask or infer failure from absence. Preserve exact existing V3 correlation, receipt, provenance and storage compare checks. Bounded exponential-backoff reads resume on reconnect/focus; pause while hidden/offline and stop when exact history confirms completion or terminal failure. Clean up on surface/World changes and unmount. Remove obsolete uncertain notices after verified settlement and hide the empty-transcript prompt while a submitted message is visible.

Failure cases: unavailable/invalid history, missing or mismatched receipt, changed storage and unknown provider execution remain unresolved. Missing history cannot authorize a replay. Terminal failures retain their inspection evidence. The additional requested graph-inspection navigation is a separate successor capability.

Verification: full mounted World conversation consumer suite, 178 tests passed; TypeScript app check passes using a private /tmp build-info file. Added recovery/no-repost, polling-stop, reconnect/preserved-storage and empty-transcript regressions. No real Agent request was sent.
