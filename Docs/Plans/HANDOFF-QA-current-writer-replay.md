# QA: replay current native Plan writer requests

MERGED in #2387 at d043600202a3e0cc5d6b81f88d6eb5019ec7c3c9. Write lease released.
Branch codex/qa-current-writer-replay, non-serving QA checkout.

The ordinary Q16 turn completed on this base. Its retained writer request and
ledger pass identity verification, but offline preparation rejects the current
v2 selector format at a v1-only name check. Accept the two exact producer
format names so current and retained requests can be replayed with their
original strict schema. Keep exact wire, completion, evidence and route checks.

Exclusive writes are this handoff, HANDOFF-QA-native-writer-fixtures.md for
merged settlement, evals/buddy_benchmark/workflow.py and
tests/test_buddy_benchmark_workflow.py. No product writer or prompt edits.
#2386 owns Build writer routing and has no file overlap.

Verify both supported names and an unknown name in existing tests, exercise
offline SDK preparation with the retained actual Q16 v2 request and record
independent review and local exact-source verification before delivery.
Provider diagnostics and any prompt adoption follow separately.
