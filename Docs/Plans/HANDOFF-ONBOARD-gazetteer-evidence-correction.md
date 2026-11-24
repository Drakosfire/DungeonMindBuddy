# ONBOARD: correct frozen Gazetteer evidence

Status: ACTIVE. The owner authorized Sizzek ingestion and asked that normal Buddy
workflows, not a separate demo interface, operate on the resulting World. The
existing Build Worldbuilding launch produced Sizzek's Izmati Prep run
`ad59d066-329e-5168-bc31-ee4344036b04` with 70 candidate nodes, 34 candidate
edges and five nonliteral quotes. The exact-run review correctly blocks it.
Existing quote-only correction rejects Gazetteer `1.10` and validates every
child with the unrelated Shepherd profile. Enable this exact existing Gazetteer
profile in the same frozen-span correction service, and validate its child with
its own registered profile. Do not weaken exact parent, World, source, span,
literal-quote, authorization, idempotency or immutable-parent checks. A corrected
candidate remains unpublished and semantic labels still require proper review.

Serial slice from fetched `origin/main`; branch
`codex/onboard-gazetteer-evidence-correction`. Write lease: this handoff,
`apps/live_control_server/services/exact_run_evidence_correction.py`, and
`tests/test_demo_derived_candidate_evidence_correction.py`. The older open hosted
authorization integration #3824 touches the Build review UI, so that UI is not
leased here; the existing correction API is the integration boundary. No schema,
shared benchmark database, provider or runtime state is leased for implementation.

Verify same-profile child qualification, literal rejection, foreign-profile and
cross-World rejection, identity/replay and parent immutability at the correction
service boundary, plus the affected backend contract at exact SHA and independent
Bugbot review. Merge only after required evidence. The live serving lineage is on
APP 0207 while current main is behind; reconcile the supported deployment path
before any production rollout, and preserve the current serving/rollback pins.
