# RETRIEVAL: omit unused execution from trace appends

Status: ACTIVE. Root owns design, implementation and independent review under
the retrieval optimization goal; PRIME owns merge/delivery only.
Base6712cf07d22383e72cd3085c41fec515267c8743, branch codex/trace-unused-ledger.
Topology: parallel-independent of delivery-only names PR2244. This steward
declaration supersedes the prior default serial sequencing for this independent
slice: no unmerged behavioral dependency, shared source lease, migration, port,
live runtime or mutable resource. Names owns native_graph_reads and its tests;
this slice owns only this handoff and context_trace_store.py. Other open Plan/UI,
ingestion and local-world lanes are disjoint. No extra capability is included.

Hypothesis: provider-call and context-decision observations never inspect the
execution ledger in append, so loading/decompressing that column is redundant.
Change one existing SELECT expression to CASE, omitting execution only for those
two exact concrete types. All other and future types retain execution. Keep the
same row lock, World/conversation/attempt/revision/lease fences, column positions,
idempotence, trace validators and durable write. In particular, authored-reference
validation remains before idempotent replay. No new producer, flag, cache,
fallback, model input, schema, event representation or batch persistence.

Evidence: retrieval-current-admission-profile-v1/trace-unused-ledger-projection.json
and trace-exact-case-projection.json. Ten fixed alternating paired SQL reads of
the retained2.17MB execution show full/omitted median12.33/.40ms for the exact
prospective CASE. All other selected columns match; execution-bearing queries
return the exact ledger; row conservation and rollback verified. This is local
fetch/decode evidence, not a whole-turn gain. The retained trace has53 of68
observations in the two eligible types, but that is not a fixed production ratio.
Independent design PASS: trace-unused-ledger-design-review.json in the same root.

Validation: run existing trace PostgreSQL, consumer, type, projection and collector
checks on disposable evaluator55447 only. Review cumulative base-to-head source
once independently. Verify exact store replay/append outputs and authorized ledger
paths remain unchanged using retained data without providers. No new stochastic
correction tests or paid QA for this plumbing change. Reject on any fence,
validation, idempotence, trace evidence or legitimate-type regression; retain
failures and do not add a compatibility path. No adoption on SQL timings alone.

Resources: isolated disposable test fixtures and existing rollback profiling
database; unique evidence directory. Primary/live/benchmark originals remain
unchanged. No provider, publication, migration of retained resources or writer
generation. Preserve all names/full15 context evidence and historical6complete/
9partial composition findings. The overall retrieval goal and four-second target
remain active; this slice does not claim either complete.

Owning verification:108 existing trace PostgreSQL/consumer/type/projection/
collector checks passed in12.78s. Three fixed actual-store replay samples per
retained family preserve exact returned trace JSON: provider-call median18.679
to5.776ms, context-decision18.390 to6.359ms, prompt-reference18.139 to18.397ms,
context-snapshot19.033 to18.771ms. Baseline then candidate order and warm fixture
limit timing interpretation; this is not a whole-turn gain. Both claim renewal
and reopening the historical closed trace occurred only inside rollback; original
turn and trace bytes were conserved. Fresh append and rejection behavior are
covered by the existing suite. Environment-unset and closed-fixture rejections
are retained, not counted as behavior regressions or erased by successful data.
Evidence: retrieval-trace-ledger-projection-v1/existing-tests.log and
retained-store-comparison.json. No paid calls or response-generation checks.
