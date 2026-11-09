# RETRIEVAL: single trace-payload transmission

Status: ACTIVE. Root owns this bounded retrieval implementation.

## Authority, ownership and topology

Base: `659ca54894231cf51444afcd3dfd2576f29906d8` (after re-anchoring from the
initial `50bb2f979320e0ee6bdbe52f01d1eaa86afa329b` implementation base).
Branch: `codex/retrieval-trace-single-write`, recorded-names-control checkout.
PRIME owns merge and delivery.

Topology: initially **parallel-independent** of #2269 at
`011b1eabb5235bff006572337de1ce6565b412bc`. The earlier design-only serial gate is
superseded explicitly: the two changes have no unmerged behavioral dependency.
That PR owns internal work-context reconstruction; this slice owns only trace
storage. Separate test clones and output directories isolate execution state.
Open PRs and the merged Plan work were inspected before activation; there is no
overlapping expected write set. Do not absorb Plan or ingestion changes.

Predecessor settlement: PRIME subsequently merged #2269 at the base above after
its exact-head independent PASS and seven green CI checks. No live activation
has been claimed. This branch now rebases onto that verified merge; the
trace-store owner was unchanged by #2269. The former independent topology has
therefore settled into an ordinary main-based successor.

Expected write lease:

- This handoff.
- `Docs/Plans/HANDOFF-RETRIEVAL-work-context-reconstruction.md` (truthful predecessor settlement only).
- `src/application_state/agent_conversation/context_trace_store.py`.
- `tests/application_state/test_agent_conversation_context_trace_postgres.py`.

## Hypothesis and changed variable

Send a trace payload to PostgreSQL once, using one materialized candidate and
exact JSONB text-byte measurement, a size-guarded update, and a returned byte
count. Remove the separate sizing query and duplicate payload encoding/transfer.
This is a local storage simplification, not a claimed four-second solution.

Keep the existing reserve calculation, error text, trace identity predicate,
caller locks, transaction, trace-prefix durability and missing-row behavior.
Oversized candidates must not update any row, including a no-op update. JSON
remains necessary at this storage boundary. No new representation, database
function, cache, batching, fallback or capacity limit is introduced.

## Qualified boundary

The private helper runs in existing writable trace-owner transactions. Migration
0022 defines no statement-level triggers or RLS; isolated retained-table catalog
inspection confirms only internal row-level FK triggers and UPDATE permission.
A zero-row UPDATE statement still acquires statement-level locks and requires
write privilege. Do not claim equivalence for arbitrary read-only callers or
operator-added statement triggers; neither is a supported helper contract.
Verify these preconditions in the disposable owner tests. No live changes.

## Acceptance and stopping rule

- Existing trace capacity, terminal, claim and source-prefix tests pass.
- Exact PostgreSQL byte limits, including Unicode/escaping, remain authoritative.
- Oversized rejection leaves payload and row xmin unchanged, even when caught
  inside a transaction; missing rows retain the old no-op/error behavior.
- One bound payload and one SQL execution replace two transmissions per save.
- Compare old/new saves locally using retained trace payloads in disposable
  state; do not infer a whole-cycle or billed-cost improvement.
- Obtain independent cumulative-diff review, then commit, push and open one PR.

Fix at this owner or reject if the single statement cannot retain these
properties. No new paid calls, ingestion, publication, migrations, primary-data
writes or dogfood changes are included.
