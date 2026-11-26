# Pending Build page-target barrier

ACTIVE, serial, DOGFOOD. Base: serving revision `a5bda8bdf311d28066c4f80aec7a88cd7c2581b1`; branch `codex/pending-page-target-barrier` in the existing dogfood-lore-review checkout. User authorized reviewed fixes and production delivery for the over-retrieval goal. No benchmark database or provider is needed for this slice.

The signed-in Shepherd naming replay selected anchored current-page work without a captured page-writing target. Its admitted resolution recorded `current_page_target_absent`, but neither source preparation nor the source-free terminal handled that state, so native retrieval failed without a source settlement. Allow the validated anchored missing-target barrier to reach its existing writer contract without source acquisition. Preserve validation of the frozen response contract, acknowledgement, citation authority and source-required paths; do not fabricate a target or change the user's page.

Exclusive expected writes: this handoff, `src/application_state/agent_conversation/build_source_free.py`, and focused tests in `tests/test_build_source_free_protocol.py`. Check the main Build harness and writer boundary, including wrong scope, forged barriers and existing source-required cases. Independently review the exact head before merging. Deployment follows the current Actions runbook and must use the then-current serving parent.

This slice repairs the crash, not the controller's mistaken choice of a page-write destination for a naming request, and does not establish the benchmark or the larger goal complete.
