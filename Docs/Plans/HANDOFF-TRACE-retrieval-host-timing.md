# TRACE: retrieval host timing

Status: ACTIVE. PRIME owns this bounded measurement slice under the reliable
retrieval goal. Base origin/main `351ca4327d12b773d039ff7877a7440856ff7f42`.
Branch `codex/retrieval-host-phase-timing`, existing buddy-context-loop checkout.
Topology: serial after merged/delivered #2153; no ingestion lane dependency.

## Outcome and invariant

Attribute host work in the existing turn trace before optimizing retrieval.
Record cumulative durations and call/error counts for candidate preparation,
decision dispatch, selection application, native source materialization, APP
execution appends and context-trace appends. Totals are inclusive and overlap;
they are not an additive critical-path breakdown. Ordinary chronological
activity is unchanged. This is observation, not authority or a new store.
Use fixed host-owned names and scalar measurements, with existing span retention
and explicit truncation reporting. No per-read span flood or operation caps.
Exceptions propagate unchanged; failed operations remain counted. Preserve all
locks, claim fencing, revisions, provider requests and grounding checks.

## Exclusive expected write set

- This handoff and settlement of HANDOFF-PLAY-retained-source-references.md.
- apps/live_control_server/services/agent_turn_trace.py, agent_turn_service.py,
  agent_context_trace_collector.py, corpus_source_navigation.py, plan_jev_driver.py.
- tests/test_agent_turn_trace.py, tests/test_agent_context_trace_collector.py,
  tests/test_native_reference_navigation.py and focused driver owning tests.

No schema, dependencies, ingestion, publication, model or UI changes. No write
lease on Core/APP data, sources or Run state. Live8000/5202 remain runtime051ac
until reviewed delivery. INGEST PR2156 owns ingestion_evaluation, not these paths.

## Verification and delivery

Deterministic-clock tests prove totals/counts, nested inclusive work, unchanged
failure propagation and metadata-only retention. Provider-free owning tests
exercise actual fence/collector/source/driver wiring and no-trace callers.
Inspect cumulative diff; obtain independent exact-head review and CI; merge and
deliver through the guarded runtime process preserving live ingestion extras
and retained data. Then use a qualified ordinary request for actual host timing.
Instrumentation alone does not establish speed improvement.

## Predecessor and remaining scope

PR2153 merged at351ca4327d12b773d039ff7877a7440856ff7f42 and delivered as
runtime051ac464e1cdc2c00177c05c8990be4f5dd43811. Play source filtering, exact
passage selection and same-tab reload passed. Live answer/citation dogfood awaits
the pending C2 provider-transfer question after automatic approval rejected it.
Play objects, other cross-surface dogfood and operator acceptance remain open.
