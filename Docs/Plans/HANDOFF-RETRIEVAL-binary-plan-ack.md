# RETRIEVAL: use binary results for the Plan storage acknowledgement

ACTIVE under the Buddy Send-to-writer latency goal. Serial slice from
`70a679836b4499fc2ac762a86428205c03752c53`, branch
`codex/binary-plan-ack`, isolated checkout `buddy-binary-plan-ack`.
No unmerged behavioral dependency. Root owns the slice. Expected writes
are this handoff and the Plan acknowledgement/image cursors in
`src/application_state/agent_conversation/repository.py`.

PostgreSQL text result transport hex-encodes the large bytea values that
the Plan ACK and locked image already compare. Request binary result
transport for those two cursors. Preserve the SQL, actual and expected
byte comparisons, guarded reread, child checks, transaction and recovery
boundaries. No pool, schema changes, or alternate runtime path.

Disposable evaluator only. Existing replay inputs and artifacts are
under Projects in `core-scope-pilot.Ikt8NV`. Validate exact writer and
citation parity on retained D02, Q06 and WF01, the existing PostgreSQL
session integrity cases including rollback and stale claims, then the
frozen 31 cases. Obtain independent exact-head review. The screening
threshold is a 10% D02 write/ACK reduction and 500 ms writer-ready
improvement. Confirm timing variability explicitly before delivery.
