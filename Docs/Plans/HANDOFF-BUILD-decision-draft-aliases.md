# Share identical draft bodies in decision context

SETTLED: PR #1693 merged at 9b0713e09410870b15d48f3264b51c2434935a1e;
reviewed head c2dcefe17ca58ca58e6537f6a2e567d05f4911a7. Independent Bugbot
verified 68 affected tests. API delivered; retained state preserved. Synthetic
comparison now fits unchanged admission allowance; live quality/latency remains open.
Successor: HANDOFF-BUILD-source-provider-admission.md.

Original serial PRIME implementation, branch codex/build-decision-draft-aliases,
base c3f90d09cf39218fdf56203ede2cca3260d6852b, existing buddy-context-loop checkout.
One capability/PR. Open hosted/Combat/Ingest lanes are disjoint. API8000/UI5202
owned by PRIME; no live model probes while operator dogfood continues.

Invariant: when assessment evidence or passages exactly equal the captured working
draft, send the complete body once and retain distinct evidence/receipt selectors.
Use an explicit reversible assessment alias marker and model-readable interpretation.
Host decoding must reconstruct the original parent decision exactly before its
existing authorization checks. No alias for unequal text; no source authority from
byte equality. Existing draft inclusion still binds exact captured input to APP.
Unknown aliases, text+alias ambiguity, changed bodies or selectors must fail; real
configured token admission remains in force. This is input projection only, no new
storage/schema or decision-model behavior selector.

Exclusive writes: this handoff; HANDOFF-BUILD-exact-saved-lines.md and
Docs/Roadmaps/ROADMAP-demo.md for predecessor settlement;
src/application_state/agent_conversation/build_draft_context.py;
apps/live_control_server/services/build_jev_assessment_codec.py;
tests/test_build_draft_context.py and tests/test_build_jev_assessment_codec.py.
Expand only for a verified owning input-proof dependency. No UI/corpus/dependency
or retained user-state mutation.

Prove codec roundtrip, exact bytes once, unequal source separation and tamper refusal;
actual SDK→APP saved comparison beyond the prior duplicate-input veto; exact writer
input and citation reopening; independently maintain a genuine capacity veto.
Run affected owner tests and independent exact cumulative Bugbot review. PRIME
merges, delivers API-only with retained-state/health proof on5202, and settles.
Live model quality, full authoring and roughly10-second benchmark remain open.
