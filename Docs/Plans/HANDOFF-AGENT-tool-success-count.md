# Report successful Graph tool invocations truthfully

Status: ACTIVE. PRIME owns the operator-authorized benchmark regression program.
Base167e74fca38f8066f49117a71f65896b679a81ae; branch codex/graph-tool-success-count,
existing buddy-context-loop checkout. Serial successor to merged/delivered PR1808.
HOSTED1802 is disjoint; Plan1807 remains paused. No retained state or provider calls
are required for implementation. Reuse current dependencies and checkout.

Observed regression: BENCHMARK's pinned Q01 checkpoint delivered a source-backed
answer after two successful operations but grounding.successful_tool_count was0.
The counter uses the legacy evidence-ID predicate: an overview has no mapped IDs,
and the batch-read summary has no top-level outcome. The counter therefore reports
evidence projection limitations as execution failure.

Invariant: count successful tool invocations, independently of accepted claims,
citations and delivery. Starts/errors/denied/unavailable/unknown results and foreign
or incomplete scope do not count. A known overview with a successful canonical
outcome counts without IDs. A known batch read counts once when all read summaries
are present, recognized, revision-correct and successful; it does not count once
per source. Incomplete/mixed-failure batches do not assert full success. The field
is observation only and must not influence classification, recovery or citations.
No new provenance ledger, evidence authority, runtime fallback or public field.

Expected write lease:
- this handoff
- Docs/Plans/HANDOFF-AGENT-graph-recovery-authority.md (predecessor settlement)
- apps/live_control_server/services/hermes_graph_query.py
- tests/test_live_query_hermes_graph.py

Verify actual Q01 captured-shape replay without providers, positive/negative batch
shapes, denied/error/unknown outcomes, exact scope/revision, and unchanged answer
acceptance. Inspect cumulative diff, obtain independent Bugbot review, commit/push
and open one PR. PRIME may merge after gates and deliver API8000 behind5202 with
protected state fingerprints, unchanged UI/schema, and ordinary reload. Preserve
original benchmark reports; new metrics apply only to new projections.

Critique: do not fix this by broadening the legacy evidence predicate, synthesizing
source citations, or changing answer acceptance. Cache-write cost accounting and
full typed benchmark capture are separate work.
