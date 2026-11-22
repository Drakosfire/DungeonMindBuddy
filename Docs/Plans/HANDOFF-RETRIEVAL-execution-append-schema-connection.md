# Check the schema on the Graph append connection

ACTIVE. Serial Buddy latency slice on current main 7092e7bef after #4429.
Use the existing isolated checkout. Scope is the App State Graph execution
append transaction owner, its existing contracts, and this handoff.
No new schema or Core dependencies. The #4429 migration is in the base.

Move the existing exact-head check onto the owned append transaction using
the repository's established helper. Keep borrowed connections with their
caller. A failed schema check must precede the turn lock, mutation and
provider acknowledgment. Keep the current transaction, lease and rollback
boundaries and timing names.

The disposable D02/WF01 SQL preflight saved 2.74/2.69 ms per operation.
Evaluator replays on #4428 preserved exact packets and all 1,297 citations.
Their whole-cycle changes include unrelated timing variation. Qualify
wrong head and local owner contracts on current main's schema, then use the
existing frozen replay to verify exact Jev/writer bytes and citations.
Primary and working conversation remain outside this slice.
