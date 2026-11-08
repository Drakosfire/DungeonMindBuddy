# RETRIEVAL: reuse the execution reconstructed by its binding owner

Status: ACTIVE under the user retrieval optimization goal and transferred backend ownership.
Branch: codex/admission-validated-execution.
Topology: serial; existing PR2216 isolated on fetched main
 194b49378e779be96913693c61fff0229cbd64bc. No PR2214 dependency.
Measured baseline d4f10895; subsequent2237 merge changes no backend/test lease paths.
PRIME owns merge/delivery. Inspected open PRs have no other active overlapping lease.

Outcome: remove the discarded first native execution parse while retaining every
prewrite binding check, mutable receipt revalidation, error class and durable check.
The existing binding owner returns its freshly reconstructed execution. A provisional
model_copy must only enter that validator; only its returned object may reach Rules
admission or persistence. No cache, alternate acceptance path or schema change.
Legacy construction remains unchanged. Do not remove the middle binding check:
a retained adversarial counterexample proves that changes acceptance behavior.

Expected writes: this handoff; src/application_state/agent_conversation/native_execution.py;
src/application_state/agent_conversation/service.py;
tests/test_surface_native_execution.py;
tests/application_state/test_surface_native_writers.py;
tests/test_native_direct_source_selection.py;
Docs/Plans/HANDOFF-RETRIEVAL-direct-source-grants.md.

Evidence: retrieval-admission-profile-v1 under the chat evidence root. Diagnostic
outcome/source appends take .467/.543s under profiler, with repeated binding and
row reconstruction. These are synthetic-prefix replays, not original cycle timings.

Hypothesis: returning and reusing the validated execution removes redundant parse
cost without changing canonical payloads or admission behavior. Fixed controls:
exact retained ledger/receipt/events, normal model configuration, unchanged corpus.
Accept canonical equality and mutation/rollback/CAS/Rules/replay checks before
performance adoption. Existing all15 constructor promise gate records36.7% median
constructor reduction; not full transaction or ordinary QA evidence.

Actual APP performance protocol: same retained large source-observation prefix,
receipt and callback; exact main service versus candidate, owned profiling clone.
One warmup per arm and three alternating timed pairs; gc.collect and resets outside
timing. Compare exact execution/receipt and freshness. Require at least10% median
full-append reduction for material local improvement; report all samples. Stop on
acceptance/error/payload/rollback changes or insufficient gain; preserve rejected or
inconclusive outcomes, no unchanged reruns. Add callback-mutated locked-receipt
regression, returned fresh-model and actual durable writer mutation checks.
Independent cumulative exact-head review required. No decoder/cache/bypass or
legacy serialization changes. Preserve atomic grants. Adjacent exact-V1 unavailable
assertion test predicate deferred. Baseline6complete/9partial remains unchanged.

Resources: disposable evaluator test/diagnostic databases on55447 only. No primary,
live UI/API, native graph mutations or provider calls during local qualification.

Qualification result:113 targeted native execution/writer/direct-source checks pass
(14 inherited serializer fixture warnings). Callback receipt mutation rejects before
update and leaves the durable snapshot unchanged. Paired full source-observation
append medians:main471.749ms, candidate302.286ms,35.9% lower. All three measured
candidate samples300.395–302.758ms versus456.959–481.499ms baseline; exact
execution/receipt equality and freshness pass. This is synthetic isolated retained
callback transaction evidence, not ordinary source IO, cycle latency or QA proof.
Evidence:retrieval-validated-execution-reaudit-v1/full-append-comparison.json,
full-append-diagnostic.py and owner-tests.log. Independent provisional review found
no correctness blocker; final committed-head review remains required.
