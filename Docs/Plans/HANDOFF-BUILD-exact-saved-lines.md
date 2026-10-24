# Exact saved line ranges without a fixed paragraph limit

ACTIVE serial PRIME implementation, branch codex/build-exact-saved-lines,
base 7fe760d87e3f1c2297211e76e15897cd9af80eb3, existing buddy-context-loop checkout.
One useful capability/PR; open hosted/Combat/Ingest lanes are disjoint.

Failure: Build catalog construction refuses any saved line over12000 characters,
before routing can use the already captured working draft. Explicit saved comparison
also uses that inherited per-read maximum. The exact source owner can already
prove arbitrary complete line ranges; truncation or silently omitting lines is wrong.

Contract: new explicit draft-context policy variants freeze the exact saved source
character count. Saved-line authorizations may use that count rather than the
unrelated Graph passage limit. Actual provider envelope/token admission remains the
capacity gate. Existing saved-read event shape retains exact range/hash/source and
authorized-size checks; historical policies retain their frozen read allowance.
Catalog grouping may target small ranges for efficiency but one long line remains
complete and selectable. No source truncation, new arbitrary cap, legacy execution
path or implicit World authority. Prove saved source count at the APP read boundary.

Exclusive writes: this handoff; predecessor HANDOFF-BUILD-proposal-exact-save.md;
Docs/Roadmaps/ROADMAP-demo.md for settlement;
apps/live_control_server/services/build_jev_harness.py, build_jev_driver.py,
agent_turn_service.py; src/application_state/agent_conversation/types.py, service.py;
tests/test_build_draft_context.py and owning saved-section tests if required.
Also owns apps/live_control_server/models/agent_turn.py saved-section response;
apps/live-control-ui/src/planSurface/components/BuildSavedSectionEvidence.tsx and
apps/live-control-ui/src/planSurface/BuildSavedSectionEvidence.test.tsx, so reopening
an admitted long excerpt does not reimpose the removed size limit.
No schema/corpus/dependency or retained user-state mutations.

Verify real SDK→APP current-draft answer and explicit saved comparison for a long
single line; exact text once, source provenance, reopen and digest/range/count tamper
refusal. Real configured token admission must still veto oversized provider input.
Independent exact-head Bugbot review, PRIME merge and protected joint API/UI delivery
on8000/5202. Preserve APP0061/native0017 and all retained state.
Live model probes remain stopped; full live authoring/performance acceptance open.
