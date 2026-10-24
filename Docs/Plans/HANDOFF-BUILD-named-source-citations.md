# Build named source citations

ACTIVE serial PRIME slice on codex/build-named-citations, based on
origin/main a0437bc0de5b7659ff74d4a56803dbf4b2309864. Reuse buddy-context-loop;
no other open product implementation lane overlaps these paths. Existing API8000
and UI5202 remain owned by PRIME; retained database/corpus/drafts are protected.
Operator goal authorizes named citations and continuing evidence foundations.

## Capability and invariant
Fresh Build source-passage answers expose the host-verified source name in the
shared numbered citation tooltip and opened passage. Model output selects only
existing passage handles. Names are reconstructed from exact producing input,
which APP independently verifies against protected source-read captures. A name
never grants evidence authority. Keep existing receipt/claim/source reopening
checks. New frozen policy and completion variants distinguish this contract;
historical records retain their original shape and meaning. No automatic retry,
new cap, runtime fallback or edit to user sources. Source-read alias deduplication
is separately scoped: batch file loading already caches bytes; receipt identities
must not be collapsed into invented evidence or silently dropped support.

## Exclusive expected writes
- This handoff; HANDOFF-BUILD-world-context.md and Docs/Roadmaps/ROADMAP-demo.md
  for truthful predecessor settlement.
- src/application_state/agent_conversation/{types,source_writer_output,build_world_context,rules_authority_output,service}.py
- one APP migration to admit the named Build completion variant, retaining old checks.
- apps/live_control_server/{models/agent_turn,models/agent_source_passage,services/agent_turn_service,services/build_jev_harness,services/build_jev_runtime,services/build_jev_writer,services/agent_source_passages}.py as required.
- apps/live-control-ui/src/api/types.ts, shared/sourcePassageProtocol.ts,
  planSurface/components/{sourceCitationReads,BuildSourcePassageEvidence}.tsx/.ts
  and owning conversation rendering only where the closed variant requires it.
- tests/test_agent_build_jev_ordinary_harness.py only for mocked source-owner name metadata.
- Focused APP/SDK source/name tampering, mixed Rules, image, retained completion,
  migration and shared UI citation tests; no unrelated implementation.

## Failure critique and gates
Missing/blank/forged names, wrong source/range/body, old-policy output claiming
new fields, stale writer identity and cross-turn replay must fail at APP owner.
No migration rewrites prior turns. Test current and retained shapes; actual SDK/APP
fresh named completion and citation reopen; shared Plan/Play citation regressions.
Exact cumulative diff, independent Bugbot approval, PRIME merge, protected API/UI
delivery, ordinary synthetic two-source browser discussion/tooltip/open/reload
with saved sources unchanged. Keep private telemetry outside GitHub. Full goal
acceptance and repeated performance/quality remain open.
