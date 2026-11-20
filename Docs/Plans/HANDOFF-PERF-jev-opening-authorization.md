# PERF: Commit first Jev authorization and prompt evidence together

ACTIVE on user-authorized first-dispatch goal. Serial successor to merged
#4183, base ea9726ca8e9730f2cea0f7cb323bf190f0c7bf62, branch
codex/jev-opening-authorization. Isolated checkout and evidence under
Projects/.codex/jev-opening-authorization. No primary database writes for
qualification. Hosted comparison only after independent review and delivery.

Scope: the ordinary native Build opening authorization caller and its
trace collector, APP provider authorization and context trace store, this
handoff and existing owner tests. Reuse the current exact-payload, claim,
attempt and trace validators. Prepare the content-addressed body before
the APP transaction. Commit the authorization, exact prompt reference and
authorized observation together. SDK entry still requires its committed
sending acknowledgement. Later decisions and other surfaces are outside
the slice. No schema or payload codec change.

Failure cases: changed bytes, missing or closed trace, bad sequence, expired
or competing claim, duplicate attempt, capture capacity, and failed commit
must not cause provider dispatch. An unreferenced content-addressed blob is
acceptable on rollback. Authorization and its trace observations must both
be present or both absent. Keep observation ordering and exact reopening.

Verify provider-free ordinary Build owner contracts on exact head and fresh
disposable APP state, including concurrent sends and rollback. Compare
exact prepared bytes, authorization ledger, trace observations and cited
readback. Local checks and independent review precede hosted comparison.
