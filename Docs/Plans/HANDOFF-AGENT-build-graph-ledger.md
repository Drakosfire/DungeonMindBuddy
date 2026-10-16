# AGENT: governed Build Graph ledger

Status ACTIVE under the operator's Mirathorn lifecycle goal. PRIME implements;
ARCHITECTURE independently reviews. Base `990d229d6f131985b830fabc2a6598a5b12f61a5`.
Lane `codex/build-graph-ledger`, `/tmp/prime-recap-mention-boundaries`.
Topology serial producer prerequisite; one PR. Buddy consumer follows acceptance.

## Outcome and boundary

APP-STATE accepts, persists and validates genuine Build source/World Graph turns
through the existing governed execution ledger. Distinct Build intent, receipt
and completion variants preserve the saved source registry revision/hash and
managed/native World binding. Saved-source attribution is distinct from admitted
Graph claims. No invented Plan basis, duplicate broker, or trusted worker log.
Reuse shared Graph evidence validation; preserve existing Plan receipts and
fingerprints. Inspect and extend SQL constraints with a new migration rather
than assuming JSON storage accepts a new variant. Source attribution proves a
frozen identity, not semantic entailment; consumer must verify exact source bytes.

## Exclusive write lease

- This handoff.
- `src/application_state/agent_conversation/types.py`
- `src/application_state/agent_conversation/service.py`
- `src/application_state/agent_conversation/repository.py` only if serialization assumes Plan.
- `src/application_state/migrations/versions/20261016_0024_build_graph_turns.py`
- `tests/application_state/test_build_graph_turns.py`
- `tests/application_state/test_agent_conversation_service.py` and
  `tests/application_state/test_agent_conversation_postgres.py`: update only
  assertions of the current migration head from 0023 to 0024, discovered by
  the owning regression run. No weakening of lifecycle or migration assertions.

Current open PRs inspected: no active APP ledger overlap. DOGFOOD's Build Edit
clearance UI lease is disjoint. No dependency, browser, provider, corpus,
retained APP/native database, serving runtime, or 5202/5876 changes. Disposable
APP databases only; no migration of the serving database in this slice.

## Required evidence

Real disposable PostgreSQL upgraded from previous head: accept Build turn,
authorize provider and Graph/source read lifecycle, validate completion, reopen
through fresh service and replay without provider work. Reject mismatched source,
surface, World, frozen receipt, identity or digest; stale claims; invented Graph
citations; cross-variant Plan/Build completions; changed retry basis. Preserve
already committed lifecycle/trace after timeout. Prove existing Plan rows still
read and their fingerprints stay identical, plus fail-closed SQL constraints
for malformed Build variants. Inspect cumulative diff; independent review of
exact PR head before merge.

## Follow-through

This producer does not make ordinary Build questions work. The next Buddy
consumer must reuse parent provider authorization, Graph broker, protected trace
and verified source-read receipts with Build-specific assembly, then prove an
ordinary Mirathorn question and opened passage. Latency/usefulness and operator
inspection remain required. Never replay timed-out provider turn `5893388c…`.
