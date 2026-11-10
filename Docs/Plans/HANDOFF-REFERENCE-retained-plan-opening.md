# REFERENCE: preserve retained Plan opening admission

Status: ACTIVE bounded PRIME implementation. Base 73f2d42d755978a95ac1a8d7a253b8c9b852c2d6;
branch codex/plan-retained-opening-retry in the existing buddy-context-loop checkout.
Topology: serial, no unmerged parent. No new runtime, database, provider or external
resource lease. Original API/UI process hold and surviving database protections remain.

## Outcome and invariant

A retained SDK-admitted native Plan turn must retry through its frozen first SDK
wire and existing claim/read/writer owners. It must not be converted to a request-first
admission. Fresh requests still require the current policy. Request-first retained
turns still use their exact request manifest. No new historical receipt producer.

PR2322 preserved historical readers but made the harness unconditionally claim the
current request protocol. The service admits durable historical turns, so this
prevented an otherwise valid interrupted retry before its existing owners ran.
The query-and-answer qualification at the pinned base retained three HTTP failures
in test_native_plan_statements alongside seven unrelated fixture/assertion failures.

## Write lease and boundaries

Exclusive expected writes: apps/live_control_server/services/plan_jev_harness.py;
tests/test_native_plan_statements.py; this handoff. Current open PRs inspected:
2313/2262 Surface, 2308 Storage, 2302/2299/2298/2288 CI, 2225 composition,
2219 notes and historical ingestion PRs. No overlapping active harness lease found.
RETRIEVAL-opening-batch records its released implementation lease after PR2322;
PR2324 is merged and does not own these files. Coordination remains off.

Use the actual stored admission codec to select the existing continuation producer;
all identity, source/query, exact-wire, authorization and grounding checks remain at
their current owners. Do not recapture old work or replay an unknown provider result.

## Verification and delivery

Provider-free real HTTP interrupted retry with both historical native-policy and
current-policy SDK receipts: exact frozen query, native clause read/support,
citation opening, replay/history, changed request refusal and no fresh V1 acceptance.
Keep unavailable read and whole-clause variants. Exercise current combined-opening
owners. Run query-and-answer at an exact SHA; retain unrelated failures rather than
mask them. Hosted frontend/build qualification is also required by local policy;
no frontend changes or fresh discovered diagnostic needed for this backend slice.
Independent Bugbot review, cumulative diff, local exact-source evidence, then PRIME
merge under standing authority. Protected delivery still respects original process hold.
Fixture-only repairs are a separate serial slice, not absorbed here.
