# RETRIEVAL: reuse the execution reconstructed by its binding owner

Status: ACTIVE under the user retrieval optimization goal and transferred backend ownership.
Branch: codex/admission-validated-execution.
Topology: stacked; exact parent #2214 head49819b22add7fc11c13bc2e0062d8bbc63ba8e62.
Merge/rebase order: #2214 first, then this successor; PRIME owns merge/delivery.
The overlapping service/test lease is explicitly a dependent successor, not a competing lane.

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
tests/application_state/test_surface_native_decisions.py.

Evidence: retrieval-admission-profile-v1 under the chat evidence root. Diagnostic
outcome/source appends take .467/.543s under profiler, with repeated binding and
row reconstruction. These are synthetic-prefix replays, not original cycle timings.

Hypothesis: returning and reusing the validated execution removes redundant parse
cost without changing canonical payloads or admission behavior. Fixed controls:
exact retained ledger/receipt/events, normal model configuration, unchanged corpus.
Accept local equivalence and negative-boundary checks plus measurable eliminated
work; retain full benchmark quality gate before any retrieval performance claim.
Stop if invalid mutation becomes accepted, errors change, rollback fails, Rules sees
an unvalidated provisional object, or persisted payload differs. No unchanged paid reruns.

Validation: canonical equality and independent reconstruction; mutated receipt/event
rejection before persistence; actual durable SDK/Rules authorization, replay and
negative tests; independent review of exact cumulative successor diff. Compare local
retained-state work first: six repetitions per source/outcome transition per arm,
exclude first as warmup; compare canonical payloads and report all five measured
samples. Diagnostic clone only, no provider. Then ordinary workflow only if justified
by results.
Resources: disposable evaluator test/diagnostic databases on55447 only. No primary,
live UI/API, native graph mutations or provider calls during local qualification.
