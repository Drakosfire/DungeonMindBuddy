# PROMPTS: native Build navigation host context

Status: ACTIVE. PRIME designs and implements this operator-prioritized slice.
Authority: semantic-only policy in AGENTS.md and the parent metadata audit handoff.

## Boundary and topology

Stacked on PR2192 exact7bac58ddd5b517391ecfcc901409677e7e2c18b4;
merge2192 first, rebase/retarget this slice on remote main, then review final head.
Branch codex/native-navigation-host-context in the existing buddy-context-loop checkout.
Open PR inventory checked: INGEST lanes own extraction/review, paused2191 owns
saved citation previews, held2172 owns Play integration. No overlapping paths.
No new environment, provider calls, runtime or database write lease.

Outcome: current native Build navigation emits semantic state only, retaining the
existing frozen accounting, exact SDK wire binding, scope/revision and replay checks
host-side. A closed V3 parent codec distinguishes current clean wire from retained
V1/V2 records. Historical reconstruction is read support, never a current fallback.
The reader fence changes no rows. Other phases/model roles remain unresolved.

## Exclusive expected write lease

- This handoff and HANDOFF-PROMPTS-host-metadata-removal.md (truthful sequencing).
- src/application_state/agent_conversation/jev_retrieval_contract.py
- src/application_state/agent_conversation/native_retrieval.py
- src/application_state/agent_conversation/build_decision_context.py
- apps/live_control_server/services/build_jev_accounting.py
- apps/live_control_server/services/build_jev_dispatch.py
- apps/live_control_server/services/plan_jev_dispatch.py
- src/application_state/migrations/versions/20261107_0125_native_navigation_context.py
- tests/test_jev_retrieval_contract.py
- tests/test_build_decision_context.py
- tests/test_surface_native_build_decision.py
- .github/workflows/world-ownership-core.yml (register accounting boundary tests in query suite only)

## Failure analysis and verification

Do not simply omit the prompt descriptor check: host accounting must still equal
its frozen execution policy before dispatch. Current wire must have no accounting
or phase keys; exact reconstruction rejects injected fields. A wrong host phase,
mode, digest, scope/revision or frozen descriptor must still fail. Historical wire
must reconstruct byte-for-byte. Preserve semantic guidance and unmodified source
text. No limit increases, global sanitizer, new provenance owner or arbitrary cap.

Verify serialized SDK packets, pure codecs/accounting and actual native Build
factory boundaries. Inspect cumulative parent-to-head diff, obtain independent
review and required CI before merge/delivery. Ordinary runtime proof follows the
protected reader-fence upgrade/restart; this document does not claim it passed.
