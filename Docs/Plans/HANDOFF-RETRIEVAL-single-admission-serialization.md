# RETRIEVAL: serialize admitted history once

Status: ACTIVE under the operator's bounded selection/admission fix request.
One serial implementation PR, branch `codex/admission-single-serialization`,
base fetched main `63a8dd3f58ed2c50d1bcc11faf1d0d41dcd41bea`.
PRIME remains the merge/delivery actor. No primary or live runtime lease.

## Outcome and exclusive expected write set

Remove the discarded first serialization of execution history in the existing
APP append owner. Keep the replacement event serialization and every model,
context, claim, revision, duplicate-event and transaction check unchanged.

- `src/application_state/agent_conversation/service.py`: only the two execution
  dump expressions whose `events` field is immediately replaced.
- `tests/application_state/test_surface_native_writers.py`: owning durable
  acquisition preparation and atomic writer admission test, exact old/new payload
  equality and no discarded event dump. Existing replay/stale/integrity cases run.
- This handoff.

No selection changes, skipped validation, new representation/cache, batch ledger,
schema migration, fallback, provider policy, ingestion, publication or Gold edit.
No overlapping PRIME product source lease exists per the explicit transfer.
The first acquisition fixture selected for regression coverage has unrelated
failures; the same boundary assertion moves to the passing atomic writer test.
No acquisition fixture repair is included in the slice.

## Evidence and acceptance

Retained full15 traces show selection application and admission dominate host
work. The append owner currently dumps old events and then unconditionally
overwrites them with a second dump of the prospective event list. Excluding
`events` from the first dump must produce the identical serialized value.
Local retained-state preflight found roughly 2–6ms savings per dump, not seconds;
this is confirmed redundant work removal, not a claim to solve the four-second
cycle or explain composition omissions. Do not skip owning validators for speed.

Verify equality on representative large retained executions and durable APP
acquisition/writer behavior in disposable test databases. Independent subagent
review is required. Retain stale/mutated event and replay refusal behavior.

Compare using the consolidated workflow on Q01/Q04 passing controls, Q09 route
partial and Q15 broad synthesis. Reuse their frozen `6b9/schema129` captures.
To isolate this change from #2211, pin an experimental ref derived from `6b9`
with only this same change (tests/docs may accompany it); new clones remain at
schema129. This is a pinned experimental code ref, not a competing runtime path
or extra implementation PR. Current-main tests separately verify schema130.
Keep corpus/dependencies/request template/provider policy fixed and original
evidence/Gold immutable. No per-question scripts or unchanged paid reruns.

Acceptance requires identical admission payloads and safeguards, plus no material
coverage/citation/attribution regression in the bounded ordinary comparison.
Report local CPU savings separately from end-to-end timing. One observation with
stochastic acquisition cannot establish a latency speedup; retain inconclusive
or adverse results and do not repeat unchanged until successful.

## Resources and delivery

Evidence lives in the established external benchmark evidence workspace.
Test databases and comparison clones use evaluator55447 only. No writes to
retained source databases, primary APP/Core, API8000 or UI5202. New comparison
clones and output directories must be independently qualified and pinned before
dispatch. Existing provider/corpus authorization applies to the bounded runs.
Finish tests, cumulative review, commit/push/open one PR; send exact reviewed head
to PRIME. No merge or delivery is authorized in this lane.
