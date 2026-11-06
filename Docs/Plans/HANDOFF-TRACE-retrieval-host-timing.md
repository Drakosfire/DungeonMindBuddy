# TRACE: retrieval host timing

Status: MERGED and DELIVERED. PR2158 product63ed934b1f93331d8ee94be738b76b60052453fd
merged8f1d0f8745e879dd7dd106aa5020b5054bc3b4b5 after independent approval and all
seven CI checks. Independently approved integrated runtime44b5c416727a81ec270f9dc81af2420406df54c2
is healthy on8000 with the prior5202 UI unchanged. All retained Core/APP rows and
session files were conserved. The implementation write lease is released.
Actual host measurement remains open; instrumentation is not speed improvement.

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
passage selection and same-tab reload passed. Provider calls are authorized. Ordinary Play submission failed before durable
admission: its older Graph context differs from current native source authority.
The failure and original request are retained; native Play integration is open.
Play objects, other cross-surface dogfood and operator acceptance remain open.
