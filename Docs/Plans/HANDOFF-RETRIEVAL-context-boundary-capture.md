# RETRIEVAL: capture response-ready context without generating a response

Status: ACTIVE under the user's revised retrieval/context-only goal. Root owns
design, implementation and verification; PRIME owns eventual merge/delivery.
Branch `codex/benchmark-context-boundary`, base
`64cb0b5c89f685505c7558207e4943e6cf76cac4`. One tooling PR, no product runtime
dependency. Topology: parallel-independent of2242 and frozen2244. Names validation
consumes this tooling after qualification; tooling itself works without names.

Outcome: extend the existing parameterized benchmark CLI with `capture-context`.
Run the same ordinary Plan discovery/retrieval/admission path. Intercept only
after the real `PlanJevWriter.authorize` succeeds, with exact SDK bytes, APP/Rules
authorization and prompt witness retained. Observe ready UTC/monotonic clocks
before artifact IO. Raise a dedicated stop through existing GE known_not_sent
and Plan interruption/cleanup. A separate lower writer transport denies all IO.
Do not manufacture a response, completion, alternate context producer or model
policy. Controller calls retain ordinary attempt/retry accounting.

Expected exclusive writes: `evals/buddy_benchmark/workflow.py`;
`evals/buddy_benchmark/context_capture.py`; `tests/test_buddy_benchmark_workflow.py`;
`tests/test_native_plan_assertions.py`; this handoff. Root transfers the latter
test path from its frozen names lane to this tooling slice. The names branch is
read-only until tooling integration/rebase; no concurrent write lease exists.
No PRIME statblock/UI source paths overlap. No new per-question scripts.

Design critique: retrieval-context-boundary-capture-v1/context-capture-design-review.json.
Use the complete class authorization seam, not its lower module helper: lifecycle
recording needs the writer's prepared/authorization fields already populated.
Preserve the actual failed HTTP/isolated interrupted turn separately from a
successful captured-context boundary. Zero IO, exact packet bindings, prompt
witness and known_not_sent must be independently verified; packet existence alone
does not establish success. Incomplete/unknown workers never restart automatically.

Validation: existing offline workflow suite and an actual ordinary Plan route
fixture with mocked controller, native reads, real SDK preparation and APP/Rules
admission, zero lower writing transport calls, interrupted turn and released claim.
Negative checks cover failed authorization, missed boundary/guard hit, repeated
authorization, packet mutation/misbinding, unsettled lifecycle and missing capture.
Ordinary response capture/reporting remains unchanged; context reports cannot
adopt response composition grades. A captured packet is not automatic semantic
success: reviewers map unchanged Gold requirements to supplied context, source
qualifications/chronology/uncertainty and inspectable citation selectors.

Timing: APP accepted_at to UTC observed immediately after full input authorization.
Retain monotonic_ns as the local observation; do not subtract different clock
domains or claim nanosecond wallclock accuracy. Qualify same-host DB/process clock
correlation, preserve precision, exclude artifact IO/cleanup and prose generation.
Report controller usage and actual billed cost or unknown; writer IO is zero and
response output is not requested. Do not call conservative bytes a token count.

Resources: mocked tests and disposable evaluator55447 databases only. No live/API
restart, primary or original evaluator writes, ingestion/publication or paid calls
for implementation verification. Preserve all historical response results (six
complete/nine partial) separately from retrieval context sufficiency. Full15
repeated context validation and the approximately four-second target remain open.
Stop/split for product hooks/flags, alternate producers, schema migration, writer
generation, source mutation or paths beyond this lease. Finish owning verification,
one independent cumulative review, commit/push and one bounded PR.
