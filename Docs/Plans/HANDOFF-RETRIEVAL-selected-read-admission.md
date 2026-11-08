# RETRIEVAL: consolidate selected-read admission validation

Status: ACTIVE. Root owns implementation and independent review; PRIME merges/delivers.
Topology: stacked on PR2255 exact06500fc553ade3e5f4e9337129e95decc1cb26b3.
Merge order:2255 then this slice; rebase onto adopted2255 before final delivery.
Branch:codex/retrieval-selected-read-admission, recorded-names-control checkout.
Exclusive expected writes: this handoff; src/application_state/agent_conversation/native_reads.py;
tests/application_state/test_native_plan_statements.py and test_surface_native_acquisition.py.
No service/schema/prompt/model/Core/Rules/Build producer edits. Parent Rules lease
remains separate; no parent source modifications. No ports/live state touched.

Hypothesis: shared transaction-private selected-record callbacks repeat full
prospective binding immediately enforced by the locked APP append owner. Remove
only those two shared checks, retaining typed duplicate-ID rejection. Legacy full
validation remains. The public binder is unchanged. Standalone shared callback
return no longer proves prospective execution; only locked APP append does.

Fixed controls: identical events, record materialization, selection/query checks,
pre-IO stored-turn validation, postcallback full binding before UPDATE and durable
readback. Typed reused IDs must remain ValidationError, never conflict/noop.
Independent design review: retrieval-current-admission-profile-v1/
prospective-check-minimum-guard-review.json conditional PASS on exact parent.

Validation: actual APP shared statement/assertion acquisition with reused same-
and cross-family IDs, unchanged durable rows on rejection; existing invalid-kind,
foreign-query/record, missing-grant, wrong-family and second-observation probes;
positive shared Plan/Build and legacy owner tests. Exact cumulative subagent review.
No paid writer calls or response quality grading. Parent baseline evidence retained.
Measure boundary savings separately; no whole-cycle speed claim from check count.
Stop if source/authority changes, new trust flag/cache or another callback family
is needed. No new harness or per-question scripts. Primary/evaluator originals
remain unchanged; disposable tests only on explicit evaluator55447.
