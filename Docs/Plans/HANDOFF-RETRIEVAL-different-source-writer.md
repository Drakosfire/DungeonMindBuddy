# RETRIEVAL: respect different-source requests

Status: ACTIVE under the user-owned over-retrieval objective. This slice is
parallel-independent of draft #4973 (`cdc300b6bf9eae414165f5dbeb6016d57f4a263d`):
the latter owns pending Build retrieval routing and its tests; this slice owns
response instruction composition and its focused tests. Neither requires the
other to compile or grants new reads. Both share one App clone, so verification
is serial. Branch `codex/retrieval-different-source-writer` starts at deployed
serving source `6bc8b1d07cce3df64e04d2def2108904244cba9f`.

Cases 582 and 586 asked for a different saved source after a named recap. Both
answers cited that recap again, although other labeled sections reached the
writer. Preserve explicit requests to use a different source when selecting
supplied citations, and state the gap if no different source is established.
Do not prevent reuse where requested, comparisons, or factual support from
multiple sources. This is a response-guidance experiment, not a host-enforced
identity check or a guarantee that a model will obey.

Write lease: this handoff; `src/application_state/agent_conversation/response_prompt.py`;
`tests/test_response_prompt.py`; and focused writer-assembly tests if needed.
The actual writer-assembly boundary test is in
`tests/test_plan_jev_response_assembly.py`. The existing
`test_build_status_guidance_reaches_the_actual_sdk_without_changing_plan_or_play`
fails its exact prompt expectation; loading the deployed-parent response prompt
with the otherwise unchanged files reproduced that same generic-limit mismatch.
It remains red, not part of the passing focused evidence.
Verify the actual composed prompt and manifest, absent-source and comparison
controls, original source/citation authorization, full audited provider wire,
and independent held-out behavior. Compare with the fixed fixture without
treating audit-paused wall time as latency. Preserve case 582/586 failures.
Exact-head independent review, re-anchored Actions deployment, signed-in app
verification and the overall negative-retrieval benchmark remain required.

Working-tree checks: four focused response-component, manifest, failure/control
guidance and actual Build writer request-assembly cases pass. An attempted
additional mocked asynchronous SDK check stalled and its exact process was
stopped; it is not passing evidence. These checks establish assembly,
not that a model obeys the guidance. Case 586 is the negative baseline; full
wire audit and answer/citation scoring remain required for any live replay.
