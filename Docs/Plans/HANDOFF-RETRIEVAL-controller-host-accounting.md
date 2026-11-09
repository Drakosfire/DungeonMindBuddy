# RETRIEVAL: separate controller host accounting

Status: ACTIVE. Root owns design/implementation under the six-second retrieval
goal. Serial topology; predecessor PR2285 merged1128c3eb605d69fe93d75da2fe2c3085bb4eae1c
with explicit user approval. Branch codex/retrieval-controller-host-accounting,
base f5ba0f84da66f2121914c9ceb0324061f28987a2; no unmerged dependency.

Expected writes: this handoff; truthful predecessor settlement in
HANDOFF-RETRIEVAL-repository-native-codec.md; apps/live_control_server/services/
plan_jev_dispatch.py; existing tests/test_plan_jev_dispatch.py. Other open UI,
held composition and ingestion lanes do not own these runtime/test paths.

Outcome: extend the existing AgentTurnTraceBuilder.measure_host_work primitive
with fixed controller_round, controller_authorization,
controller_lifecycle_acknowledgement and controller_selection_acknowledgement
regions. No new store, observation codec, prompt field, provider, request policy,
execution authority, retry or fallback. Wrap existing bodies without reordering.

Accounting invariant: controller duration currently includes preparation, host
APP authorization, SDK dispatch lifecycle and selection acknowledgement. It is
NOT pure inference/network latency. Inner three host regions do not overlap each
other inside one round. Existing execution_append and trace_append measurements
nest within them; never add nested totals. The round-minus-inner residual still
contains preparation, SDK validation and other unmeasured work, not pure network.

Qualification: source/AST equivalence after removing the measurement wrappers;
actual method return/refusal/exception identity with and without trace; fixed
span names/count/errors and normal trace retention. Existing deterministic trace
owner and actual PostgreSQL fake-SDK dispatch tests. No paid runs for the wiring
checks. Independent cumulative review before any new measured capture. Reuse the
consolidated capture-context workflow if a fresh request is required to expose
previously unmeasured regions; no writer execution or quality grading.

Evidence and resources: retained captures/accepted baseline are unchanged; owned
isolated55447 test databases only. Temporary disk exhaustion occurred before any
implementation;947 regenerable pyc files (~18.9MB) removed from owned archives,
no sources/evidence/environments deleted. User restored capacity;1.3GB available
and disposable write probe passed. Check capacity before new data-heavy work.

Stopping rule: instrumentation is not a speed improvement or six-second success.
Use measured accounting to choose one material owning-boundary change; retain
failures and do not repeat unchanged paid captures to seek a passing number.

## Initial qualification

Four original method ASTs match the pinned parent exactly after removing only the
trace lookup/measurement scope. Actual fake-SDK dispatch checks both traced and
untraced paths, exact wire state and durable event ordering; inner counts1/2/1 and
round count1. Error/refusal checks preserve original exception object identity.
Existing dispatch+trace owner suite45pass,4existing schema-shadow warnings. No
paid requests were made by these tests. Independent review remains in progress;
accounting evidence is not a speed improvement. Evidence retained in
retrieval-controller-host-accounting-v1.

## Settlement

User authorized merge; PR2287 merged as18b992193b103b1e0a05490855bd8af620bed835.
Independent code review,45 owner tests and seven CI checks passed. Measured
cohort retained14 passing contexts and Q13 provider timeout without replay.
Controller-round median4617.903ms includes disjoint inner host work median
3169.322ms; residual1493.836ms is not pure provider latency. Instrumentation
is delivered, not a speedup. The next bounded native-storage owner slice
consumes this accounting; original evidence and baseline remain unchanged.
