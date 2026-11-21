# Return one execution payload from the Plan session acknowledgement

ACTIVE under the Buddy Send-to-writer-ready goal. Serial lane
`codex/buddy-single-payload-ack`, base `db66ba382`. Own the Plan session
acknowledgement in `repository.py`, its existing database contract in
`test_surface_native_decisions.py`, and this handoff. Use disposable APP state.

Hypothesis: comparing PostgreSQL's exact JSONB wire bytes inside UPDATE
RETURNING removes one full execution payload from each successful response
and lowers acknowledgement time. Return the expected bytes and a boolean.
Keep the existing locked root/child reread, timestamps, fences, and transaction
boundaries. Refuse byte inequality, including SQL NULL versus JSON null.

Use the frozen Elderwyld D02, Q06 and WF01 captures first. Reuse the recorded
controller cohort for fixed question, source, provider, and writer settings.
Compare real transaction update, reread and commit timings and byte sizes in
isolated state. Require exact citation reopen, writer-package byte parity,
and unchanged stale-fence, trigger mutation and rollback behavior. Advance to
the full cohort only if matched small-cohort replays show a median total
acknowledgement reduction of at least 5%, with a positive median in at least
two cases. Retain negative evidence and remove the experiment if it fails.
