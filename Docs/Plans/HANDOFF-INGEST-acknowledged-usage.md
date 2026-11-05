# INGEST: retain acknowledged usage when operation totals are unknown

Status: ACTIVE. Root adopts independent design
`2612b926ffa83ed1dab7087595a2dd5eefbbeb2bbe8d1391fda3e7db61c0f3e7`
under the user's ingestion implementation ownership.

## Invariant and evidence

Failed run `1fbe5e76-a7fb-480c-b7da-02b7dc776217` retained seven returned
attempts but operation-only accounting counted six. Independent diagnosis
`fd505dfcad4419200580bdbed283310718468ee1365bfd061438a79b8458dfdb`
establishes known cost at least $0.065849700, not $0.045056724. The operation's
complete cost and attempt/retry counts remain unknown.

Retain safe metrics from existing durable attempt evidence. Deduplicate returned
attempts, include their known lower bounds when the final operation receipt is
missing, including existing GE returned/refused/incomplete response statuses,
and prefer completed operation aggregates without counting callbacks
again. Preserve real zero, missing values and unknown remainder. Conflicting
evidence must not become a silently inflated or complete total. No synthesized
operation observation, historical receipt rewrite, schema, producer or retry.

## Ownership and topology

Branch: `codex/ingest-acknowledged-usage`. Exact parent: PR #2111 at
`73588e2aa7e1fbc537b7f887a4183dcb96521e7a`. Remote main
`8c90f30ed7323e558204b67f89348360a53f847a` and active PRs inspected.
Stacked order: #2093 → #2094 → #2079 → #2095 → #2108 → #2111 → accounting.
The deadline successor remains design-only until this exact reviewed head is
pinned. PRIME separately owns the GenerationEngine completion-status contract;
neither owner blocks this local implementation or shares this write lease.

Exclusive expected write set:

- `src/graph_memory/extraction/bounded_recap_execution.py`
- `apps/live_control_server/services/extraction_usage.py`
- `tests/test_bounded_recap_execution.py`
- `tests/test_extraction_usage.py`
- `Docs/Plans/HANDOFF-INGEST-acknowledged-usage.md`

No provider, evaluator/primary database, deadline, output allocation, migration,
UI or GenerationEngine write authority is granted by this slice. Existing
runtime and failed-run artifacts remain immutable. No Git merge authority.

## Verification and delivery

Exercise the durable callback-to-unknown-receipt seam and public usage reduction
with synthetic evidence: seven acknowledged versus six completed operations,
completed conformance aggregates, duplicate/conflicting identities, partial
metrics, missing costs and real zero. Old ledgers without enriched metrics stay
readable. Check no private response text enters safe telemetry. Review cumulative
parent-to-head diff, test, commit, push and open a stacked PR; use an independent
subagent review rather than PRIME review.

This fixes truthful accounting only. Deadline settlement, provider completion
classification, actual ingestion quality, cross-passage attribution and Session
6 publication remain unproven. The full ten-session common-build cohort,
worldbuilding and subsequent benchmarking goal remains active. Primary data
stays unchanged.
