# RETRIEVAL: one selected-record transition owner

Status: MERGED as fff6c97095eb23827d4f3d83b839f29da229e483 (PR2301).
Root owned this bounded design/implementation under the continuing
six-second context-ready retrieval goal. Base5d63a5c742e60a3e5338847f3fecc02f12a9efc7
(merged2297), branch codex/retrieval-record-transitions. Serial;2297 settled after
explicit user approval.2300 Plan capture,2298/2299/2288 CI and existing surface
lanes checked disjoint. No PRIME dependency. Merge remains separate authority.

## Outcome and scope

Replace native_plan_statements.validate_selected_record_events' historical scan
body with one pure grouped transition fold used by full recovery and later
incremental validation. Compact immutable indexes retain provider/outcome,
selection, grants/observations, attempted families and pending object closure;
no mutable query, grant, observed support or event models are retained.

Keep actual source/producer/Rules authority, query validation, read support
validation, exact quotations, attribution and current APP locks/commit boundaries
at their owners. Reuse validate_record_reads and object_record_ids rather than
inventing another support/closure implementation. The fold grants no IO and is
not an accepted APP prefix. Full recovery still replays the same predicate.

Critical design/failure matrix is pinned in
retrieval-append-critical-path-v1/selected-record-failure-matrix-v1.json.
Historical profiler observed30ms inclusive across three selected-record checks
within one246ms cold synthetic append; support checks overlap that timing.
Warm synthetic append measured202ms. Do not extrapolate these samples or add
nested spans. This owner transfer is a prerequisite, not a latency claim.

## Exclusive expected writes

- This handoff and predecessor HANDOFF-RETRIEVAL-provider-transitions.md settlement.
- src/application_state/agent_conversation/native_record_execution.py (pure owner).
- src/application_state/agent_conversation/native_plan_statements.py: delegate only
  validate_selected_record_events; support/query/read-model bodies stay unchanged.
- tests/test_native_object_retrieval.py: existing classified owning suite, oracle
  and prefix/group/negative parity coverage; reuse existing fixtures.

No schema, APP service/repository, runtime dispatch, prompt, Core, Rules, writer,
UI, CI configuration, new test filename, dependencies or primary changes.
Stop/split before another owner/contract is absorbed.

## Invariants and qualification

Preserve typed query-version semantics, exact selected operation/provider/query,
object union/attempted closures, unavailable attempts, both family grants,
observation settlement, support/digest/subject/discovery bindings and historical
writer inclusion. Global event IDs/provider lifecycle and shared writer exposure
stay separate existing owners; do not silently strengthen this standalone
predicate into a different global validator. Source-only paths must not eagerly
hash unavailable queries. Partial valid grant groups need not yet be settled.

One transition fold replaces the old production loop, with its exact predicate
pinned TEST-ONLY as differential oracle. Compare every accepted prefix, grouping
and malformed/refusal cases using existing native fixtures. Read-only replay all
fifteen retained query/execution pairs; no new paid calls or writer grading.
Actual APP reuse and the later15context comparison remain required; no pure
state, forged state constructor or serialized export conveys authority.

Indexes are immutable values for the predicate's typed inputs. The query is
supplied fresh per group and is not cached/bound as an APP capability here.
Copy/index cost, repeated query digest and full-recovery scans remain explicit;
this is not constant-time host reconstruction.

Inspect cumulative diff, independent subagent review, required existing CI.
Deliver one bounded PR. No whole-goal completion without actual context-ready
latency and preserved quality across all15questions.

## Qualified owning behavior

Final focused suites135pass. Existing Core/APP statement/assertion/native suites
283pass with63existing serializer-fixture warnings. Read-only actual baseline
qualification passes15query/execution pairs,677prefixes, every two-group split,
and38forged grant/support/subject/episode refusals. Original query/execution
bytes stay unchanged. This is not a freshly timed15context acceptance cohort.

Working independent review found eager malformed-handle errors and mutable
operation/outcome aliases. The state now stores only the semantic predicates
needed by this owner (response-received and select-candidates), frozen handle
membership, and an immutable deferred TypeError message for malformed JSON
handles. Legacy error timing is preserved without retaining mutable containers.
Tests cover None/numeric/nested-list/dict handles and list operation/outcome.

The immutable-state contract covers protocol UUID/string identities and ordinary
JSON data, as enforced by existing model/provider owners; it is not a capability
for arbitrary custom Python objects. Query/policy/producer authority remains
external and fresh. Independent working review passes43record/object tests; bind
the complete cumulative diff to an exact head before delivery.

Evidence root: retrieval-record-transitions-v1. Frozen test oracle matches the
original AST apart from its name, qualified imports and one unused import binding.
No APP cache, stored-prefix bypass, schema, provider request or timing behavior is
activated. Group advance still reconstructs query dictionaries and copies indexes;
its future reuse and actual response-ready measurement remain required.

## Dependent dispatch topology

Root adopts an explicit STACKED successor in HANDOFF-RETRIEVAL-plan-session.md,
pinned to this PR2301head768efb710. This supersedes the serial dispatch gate for
that one bounded child only.2301remains OPEN and unmerged; no authority to merge
is inferred. Merge/rebase order remains2301then the refreshed integration child.
Implementation continues under the portable child contract without editing this
parent PR's reviewed source head.

## Consumption settlement

PR2301 merged under the user's standing full merge rights. PR2304 has rebased
onto its settled main; its adoption remains separately unproven. The earlier
stack dispatch supersession below is historical process evidence, not an open
parent gate. No latency or writer-output claim is attached to this pure fold.
