# AGENT: Preserve incomplete response reason

ACTIVE PRIME solo; ARCHITECTURE independent review. Base
8f54acee7ffe980a5a00573eed03009895a05384; branch
codex/harness-incomplete-response-diagnostic; /tmp/prime-recap-mention-boundaries.
Parallel-independent of DOGFOOD UI/evidence-packaging leases; no runtime lease.

The preserved Thalia turn retrieved relevant knowledge then failed at guarded
Codex Responses finalization. Existing diagnostic retains incomplete status but
not incomplete_details.reason; abort precedes the SDK warning. Preserve a closed
reason enum across the owned Harness patch, strict worker result and parent log.
No raw provider text, retries, continuation, authority relaxation or model change.

Exclusive write set:
- This handoff
- patches/hermes-agent/0001-pre-dispatch-budget-veto.patch
- apps/live_control_server/services/hermes_graph_agent_contract.py
- apps/live_control_server/services/agent_turn_service.py (bounded log fields only)
- tests/test_hermes_graph_agent_contract.py
- tests/test_agent_turn_service.py (bounded diagnostic log assertion if needed)
- tests/hermes_patch/test_pre_dispatch_budget_veto.py (owning fixture assertions if needed)

One PR. Prepare exact pinned Harness source, test synthetic incomplete streams,
known/missing/unknown/private reasons and strict wire projection. Preserve
terminal outcome_unknown and no replay. Verify parent logging uses only sanitized
fields. No provider, serving, schema/corpus/World actions. Independent review
before merge; any runtime adoption requires a separate exact pinned handoff.

Author evidence: exact pinned-source prepare/verify passes (tree
0e67a85bc3cc8fe4bf258b37a67fbac588b455f6). Strict contract + offline patched
Harness suite:34 pass; two real-worker fixture failures reproduce unchanged on
accepted8f54 main under the same test runtime. Four parent-policy fixture cases
also reproduce on unchanged main before the modified log branch. No fixtures
were weakened to hide these failures. New bounded-reason tests and actual
synthetic incomplete-stream cases pass. Ruff/cumulative diff check pass.
Storage exhaustion interrupted a scratch clone; restored the untouched base patch,
removed only reproducible PRIME caches/archive tar, then regenerated/verified the
patch from exact pinned source. Serving runtimes/World data were untouched.
