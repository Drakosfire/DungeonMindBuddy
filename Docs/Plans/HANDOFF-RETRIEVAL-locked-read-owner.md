# RETRIEVAL: consolidate locked native-read input validation

Status: DELIVERED. PRIME reports both2251/2252 delivered in API b1603d4163e1d419ab2bc80dd8d3f675929662f3; schema134. Historical activation and verification details follow.
Base375be185b0414361f7afae676029365cd8ce0a61; branch codex/locked-native-read-owner.
Topology: parallel-independent of2251 presentation/fence delivery; no unmerged
behavior dependency, overlapping write lease, schema, runtime port or database.
Expected writes: this handoff; src/application_state/agent_conversation/native_reads.py;
tests/test_native_direct_source_selection.py. Parked2225 is not activated or a
dependency; its obsolete stacked source is not imported. No provider/legacy
producer or public/durable contract is added.

Hypothesis: the shared-native private read producer repeats full context binding
already established by fresh repo.lock_turn -> typed Turn, in the same synchronous
locked APP transaction before any materializer callback. Retire that private
standalone full-revalidation guarantee; keep the public validate_execution_binding,
legacy Plan validation, actual owner identity/source checks, prospective event
validation, post-callback full binding and durable readback validation.

Production callers are eight read helpers and four authored-reference helpers,
all fixed closures under service._append_native_read_materialization with event=None.
Optional event/proof callbacks are inactive on this path. The first shared owner
already checks request identity, so its later identical private identity call is
also removed. No trusted flag, snapshot cache, alternative producer or IO batching.
The service and repository remain the authority; helpers only produce candidates.

Failure analysis: malformed stored receipt/execution must fail in the actual
repository before read IO, and callback mutation must fail before persistence.
Stale revision/attempt/lease, replay, scope, per-source durable prefix, callback
failure and exact source evidence remain unchanged. A malicious monkeypatch that
replaces lock_turn with a corrupt post-validation return violates the new explicit
repository-return contract; do not claim universal standalone-helper equivalence
or silently count that fake boundary as actual stored-corruption proof.

Evidence: retrieval-current-admission-profile-v1 shows four full binding checks
227–277ms within446–477ms synthetic append profiles. Exact intervals/callers and
independent design are in transaction-internal-owner-design-review.json. This is
not a whole-turn savings estimate. Public frame/proof checks outside this locked
producer remain unchanged. Root caller inventory: retrieval-locked-read-owner-design-v1.

Acceptance: existing direct-source/native execution/corpus owner checks plus real
persisted-corruption preIO and callback-mutation prewrite tests. Compare fixed
baseline/candidate actual source append profiles with exact canonical output and
rollback conservation; use existing tooling, no paid/response QA. Reject on any
real preIO/persistence/fence or legacy regression; do not add a fallback. Preserve
all failed evidence. Obtain one exact cumulative independent code review.

Resources: disposable evaluator55447 fixtures and retained rollback profiling
database only; no primary/live/original benchmark writes, migrations or provider
calls. Preserve all15 QA contexts, two candidate repetitions and historical6/9
composition findings. The goal/four-second target remains active and unproven.

Owning verification:188 direct-source/native-execution/corpus/durable-writer
checks pass with14 inherited serializer warnings in74.77s. The first186pass/two
failure run used corruption rejected by SQL shape constraints before the intended
repository boundary. Corrected cases persist well-shaped invalid provenance or
source-authority commitments, then prove actual repository rejection with zero
read callbacks and unchanged corrupted rows. Both receipt/execution callback
mutation cases prove zero writes and unchanged original execution. Preserve the
initial failure log; no constraint was disabled to manufacture the test.

Three fixed alternating baseline/candidate actual source-append profiles use the
existing borrowed-transaction helper and exact retained Core result. All six
complete execution records are canonically identical and original rows conserved
by rollback. Full binding calls4 to3; median profiled append480.657 to422.245ms
(approximately12.2% lower). Samples vary: candidate301.013/422.245/482.205ms
versus baseline471.392/515.818/480.657ms, with one paired candidate slightly slower.
Profiler overhead, warm/order effects and one synthetic ledger prevent statistical
or whole-cycle claims. No unchanged paid/controller/response rerun was performed.
Evidence: retrieval-locked-read-owner-v1/corrected-owner-tests.log,
sampling-plan.json and matched-append-profile-results.json. Independent exact-head
review remains required before delivery.
