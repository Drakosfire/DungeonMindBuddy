# RETRIEVAL: reuse execution reconstructed by its binding owner

Status: DELIVERED; runtime lease RELEASED. PR2241 merged at
64cb0b5c89f685505c7558207e4943e6cf76cac4 and PRIME delivered API
3a852858510df0a4495ec32dce8ffe27d6c4b813 on schema133. Seven CI checks passed;
the protected restart conserved retained state with no provider/publication calls.
The historical implementation scope below is retained as evidence. Successor
authority lives in HANDOFF-RETRIEVAL-native-binding-reconstruction.md.
User authority was the retrieval goal and explicit plumbing clarification.
Root owns backend implementation; PRIME owns merge/delivery.
Branch codex/admission-validated-execution, replacement PR2241 on main
7bbdaa98dc8dbd73c1573a4a457c818d29d9a859. Topology: parallel-independent relative to frozen2223 (disjoint source/test/doc
writes, no unmerged behavioral dependency). Deliver2216 before resuming the
queued2223 names comparison so both arms can share the settled plumbing baseline. No2214 dependency. Original reviewed db7eda360 is retained
at codex-evidence/validated-execution-v1. Names source/clones remain preserved and
unexecuted; no labels or semantic behavior are included in this plumbing slice.

Outcome: return/reuse the fresh execution already reconstructed by the public
binding owner instead of constructing and discarding another copy first. Every
binding check, mutable component revalidation, Rules/CAS/claim fence and durable
return check remains. Only the validator's returned object reaches Rules or
persistence. Atomic grants and legacy execution construction remain unchanged.
No cache, alternative decoder, trusted-input flag, schema or prompt change.

Expected writes: this handoff;
src/application_state/agent_conversation/native_execution.py;
src/application_state/agent_conversation/service.py;
tests/application_state/test_surface_native_writers.py;
tests/test_native_direct_source_selection.py;
tests/test_surface_native_execution.py.
The five code/test paths are restored exactly from the previously reviewed diff.
Duplicate predecessor handoff settlement stays with2223, avoiding its write lease.
PRIME's native-creature/UI work has no overlapping runtime/test paths here.

Review/verification: reuse existing independent PASS for exact prior runtime diff
(db7eda360 versus194b49378), code-review-current-main.json in
retrieval-validated-execution-reaudit-v1. User explicitly directs no additional
review or paid answer-quality reruns for this piping cleanup. Run only existing
native execution/durable writer/direct-source compatibility checks at current133.
Keep reviewed negative mutation/callback safety tests; add no correction tests.
Verify restored runtime diff is byte-identical to the approved change. No fresh
stochastic QA, repeated performance study or new review cycle is a merge gate.

Evidence: prior all15 constructor canonical equivalence/mutation rejection and
paired complete synthetic append median471.749→302.286ms (35.9% lower) remain
scoped local evidence, not full retrieval latency. The prior8 ordinary captures,
9.8% authorization-proxy result and fact losses remain historical observations;
their stochastic QA disposition does not establish a plumbing-caused regression.
The user's later clarification supersedes that study's adoption gate for this
unchanged plumbing patch; it does not erase failures or weaken Gold/QA criteria.

Resources: fresh disposable evaluator55447 tests only. No primary/live/original
resource migrations, providers, publication, correction-child resume or ingestion.
No final answer/latency improvement is claimed. Original full15 sixcomplete/
ninepartial remains the quality baseline; semantic changes still require study.

Current compatibility result:113 existing native execution, durable Rules/writer
and direct-source checks pass on fresh133fixtures (14 inherited serializer
warnings). No new test or review cycle was requested. Runtime diff is byte-for-byte
identical to the previously approved change; evidence retained in
retrieval-validated-execution-restoration-v1/runtime-diff-equivalence.json and
compatibility-tests.log. No model-visible code was changed.
