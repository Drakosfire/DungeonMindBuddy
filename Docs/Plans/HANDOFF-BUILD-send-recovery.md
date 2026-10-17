# Build composer recovery

Status: ACTIVE — PRIME operator-directed repair, serial.
Base: 3ea8bd1dce89aa369d3108b6e3d33a220afca640.
Branch: codex/build-send-recovery; checkout /tmp/prime-recap-mention-boundaries.

Outcome: unblock the Build composer after a completed saved request without
replaying a provider call, preserving the operator's unsent table request.
Inspect the live recovery mismatch, repair exact terminal correlation, and prove
that uncertain or mismatched requests remain held. Include natural table-writing
instructions in the existing Build proposal route where necessary.

Exclusive write set: this handoff;
apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx;
apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx.
No Ingest edits, API/schema/Graph writes, provider calls, or automatic page save.
5202 UI asset replacement is authorized after independent review; preserve and
restore the visible composer draft. API and 5876 stay unchanged.

Verification: mounted regression at the conversation boundary, typecheck/build,
exact diff review by ARCHITECTURE, then live enabled composer. Open one PR.
