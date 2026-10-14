# MIND: retain bounded provider failure diagnostics

Status: ACTIVE. Owner: PRIME, solo implementation.
Base: `c9f5c21f3b835f35660b85fbd2e9a38312c401d4`.
Branch: `codex/recap-provider-failure-diagnostics`; isolated non-serving checkout.
Topology: parallel-independent of #1142–#1145 and held #1139; disjoint paths and no unmerged behavioral dependency. Open PRs and leases rechecked. No ports, databases or provider calls leased.

Outcome: an owned inference worker retains exception type names and numeric HTTP statuses from a bounded internal exception chain in its failure receipt; the caller preserves those diagnostics in its inference ledger. GenerationEngine still owns inference IO and public safe failure messages. Do not record exception messages, request headers, response bodies, credentials or automatic retry guidance. Missing status remains unknown. Existing stopped-client, attempt accounting and worker cleanup behavior remain intact.

Exact write set:
- `src/graph_memory/extraction/_recap_inference_worker.py`
- `src/graph_memory/extraction/bounded_recap_execution.py`
- `tests/test_recap_inference_worker.py`
- this handoff

Verify synthetic chained provider errors through an actual spawned worker, cleanup and ledger retention; private messages/bodies must not leak. Cover absent status, malformed status and cyclic chains. Run neighboring bounded execution tests, Ruff and cumulative diff checks. Commit, push and open PR; independent review required before merge. This repairs future diagnostics, not the already-reaped Session 14 failure or selected-World coverage.
