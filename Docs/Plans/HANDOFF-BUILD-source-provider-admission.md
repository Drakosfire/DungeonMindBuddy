# Resolve saved Build identity without an arbitrary body-size refusal

SETTLED: PR #1694 merged at 3b6556ea0ab01b810fc358aec5cc07e6bfc16f92;
reviewed head 0294f84c3e5634e130ad744e6ba734cef343408f. Independent Bugbot
repeated 52 owner tests and 2 mounted UI checks. API/UI delivered, retained state
preserved. Live quality acceptance remains open. Successor: HANDOFF-BUILD-admission-diagnostics.md.

Original serial PRIME implementation, branch codex/build-source-provider-admission,
base 9b0713e09410870b15d48f3264b51c2434935a1e, existing buddy-context-loop checkout.
One capability/PR; current hosted/Combat/Ingest lanes are disjoint.

The saved Build resolver loads the complete source to verify its digest, then
rejects bodies over 64 KiB before current-draft routing or provider admission.
This is unrelated to actual configured model capacity and can hide a short newer
draft behind a larger saved basis. Remove that fixed guard and dead constant and
current UI refusal-code branch. Preserve every identity/path/World/revision/hash,
kind, visibility and source-class validation. Do not truncate or substitute text.
Provider admission remains the actual capacity gate; historical turn diagnostics
remain readable without a compatibility execution path.

Exclusive writes: this handoff; predecessor HANDOFF-BUILD-decision-draft-aliases.md;
Docs/Roadmaps/ROADMAP-demo.md for settlement;
apps/live_control_server/routes/agent.py; services/agent_turn_service.py;
apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx;
apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx;
tests/test_agent_build_surface_context.py and tests/test_build_draft_context.py.
No schema/corpus/dependency or retained user-state mutation.

Reproduce the resolver refusal with an exact committed disposable source above the
old limit; then prove complete resolution plus wrong identity/hash refusal. Actual
SDK→APP tests cover short newer draft with large saved basis,
exact persisted snapshot/source preservation, and genuine decision-capacity refusal.
Focused UI recovery tests, typecheck/build; independent cumulative Bugbot review,
PRIME merge and protected joint API/UI delivery on 5202 with APP0061/native0017 and
all retained state preserved. No live model probes during operator dogfood.
Full live authoring/model/latency acceptance remains open.
