# Persist active Plan event checkpoints

ACTIVE. User authorized Buddy retrieval latency experiments, implementation,
review, and delivery. Serial on Buddy main fa507694bf5cc8b7ec28184804a2d70c3437b227.
The isolated lane is codex/plan-event-checkpoints. Dependencies are merged
through #4424, using the locked Core pin. The isolated evaluator on 32768
supplies disposable cloned databases. Primary data and the working
conversation stay out of the lane.

The write set covers the App State migration, repository and Plan session
storage owner, context trace reader, existing App State contracts for those
boundaries, and this handoff. Event-only persistence begins after the
existing read-only Plan session qualification. It ends atomically at the
writer frontier or terminal transition. The existing turn remains the
authority. The suffix contains only new events from the existing checkpoint
transactions. No event group, provider permission, or evaluation input changes.

A reader must see an exact committed revision, ordered contiguous suffix,
and matching attempt and base size, or refuse. Explicit failure, expired
authorization, retry, renewal, and writer handoff must each settle or maintain
these coordinates under the root lock. Rollback must restore both parts.
Trace authorization must inspect the same committed attempt. Verify mixed
worker rollout fencing before activation.

Run local PostgreSQL owner contracts on disposable fixtures. First compare
D02 and WF01 through the existing retained browser replay with writer off.
Require byte-exact Jev and writer packets, exact source reopening, matching
checkpoint groups and at least 500 ms median storage improvement per case.
Then qualify the full frozen 31-case benchmark, verify context and citations,
and obtain independent exact-head review. Reuse valid retained controls.
