# REFERENCE: require the Build basis for selected references

Status: ACTIVE, PRIME-owned serial repair from verified main
7953f83c434fc5fe4f1cc0b7f71a065a4721576e on
codex/reference-build-admission-basis, existing buddy-context-loop checkout.
No unmerged parent or runtime lease. Recovery, coordination-off and2104 holds stay.

## Confirmed defect and owning boundary

AgentTurnRequest currently admits Build authored references with primary_work=None
and client_work_state none/new_unsaved. Its error text already promises a current
Build page, but that presence check is missing. The ordinary composer always
supplies a saved Build locator. _governed_build_turn requires that locator; an
orphan-reference request instead becomes generic SubmittedTurnIntentV1, which
has no authored-reference field. Do not claim a live/provider reproduction: the
confirmed check is model admission plus source tracing, with synthetic input.

Require primary_work at the existing authored-Build-reference API validation
boundary. Existing primary-work validation already ensures Build kind, exact
revision/digest and matching saved-work state; do not duplicate those checks or
move Core identity/source admissibility into the API model. Both retained-v1 and
current-v2 reference inputs remain valid with their existing pinned Build basis.
A malformed request must fail before route execution, not silently lose selection.

## Exclusive write lease and non-goals

- apps/live_control_server/models/agent_turn.py: only the existing
  build_authored_references validation clause.
- tests/test_agent_turn_route.py: additive provider-free real-router admission
  regressions and a small synthetic payload helper.
- This handoff.

No service/harness, schema/migration, frontend, CI manifest, historical receipt,
retry codec, provider wire, publication, data or storage changes. Keep generic
Graph-only requests without selected Build references unchanged. This is not a
retirement of build_authored_references.py or a complete audit of every classic
request shape. Current CI/Surface/RETRIEVAL2317 paths do not overlap this lease.

## Verification and delivery

First retain failing HTTP regressions on the original model: both reference
families with none/new_unsaved work must not reach the real route's dispatch
function. Stub that function only to observe dispatch without any provider/DB.
Positive pinned saved_clean/saved_dirty requests must retain exact references and
select the governed Build predicate. Do not weaken or rewrite existing tests.
Then run affected route/reference tests and the existing query-and-answer backend
contract on the exact clean source using existing locked dependencies and owned
disposable test databases only. Keep inherited failures and source pins; diagnose
any new failure at its owner. Inspect cumulative diff, obtain independent exact-
head review, commit/push/open the owning PR and merge under standing authority
when gates pass. Source merge does not lift the runtime recovery hold or prove
ordinary live delivery. No operator database or provider is a fixture.
