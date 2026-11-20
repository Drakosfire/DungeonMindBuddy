# Build composer recovery

Status: SETTLED — merged PR #1290 at 2850ad248470d2965ac0dc6fd8acf5bcd5e59267.
Independent ARCHITECTURE PASS at fddb2dca5f7577a36557094c9b74a964d6afe4b6.
10 focused tests, typecheck, production build and diff check pass.
5202 serves the reviewed UI; live Send enabled for the preserved operator table
request. No operator table request was submitted by PRIME. API/5876 unchanged.
The older Ask resolved during operator interaction; its initial absence was a
point-in-time diagnostic. Runtime Agent write-tool awareness remains a separate gap.
Base: 3ea8bd1dce89aa369d3108b6e3d33a220afca640.
Branch: codex/build-send-recovery; checkout /tmp/prime-recap-mention-boundaries.

Outcome: unblock the Build composer after a completed saved request without
replaying a provider call, preserving the operator's unsent table request.
Inspect the live recovery mismatch, keep uncertain read-only Ask recovery separate from Build writing proposals, and prove
that uncertain or mismatched requests remain held. Include natural table-writing
instructions in the existing Build proposal route where necessary.

Exclusive write set: this handoff;
apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx;
apps/live-control-ui/src/buildSurface/BuildCompose.integration.test.tsx.
No Ingest edits, API/schema/Graph writes, provider calls, or automatic page save.
Temporary 5202 diagnostics may expose the exact pending request without replay.
Final 5202 UI asset replacement is authorized after independent review; preserve and
restore the visible composer draft. API and 5876 stay unchanged.

Verification: mounted regression at the conversation boundary, typecheck/build,
exact diff review by ARCHITECTURE, then live enabled composer. Open one PR.

Live finding: pending client request 957de60a… has no APP receipt. Do not discard, replay,
or call it completed; preserve its recovery envelope. Build proposals use their
own idempotent reservation and exact page basis, and may proceed independently
when no current dispatch is active. Graph Ask retains its existing hold.
