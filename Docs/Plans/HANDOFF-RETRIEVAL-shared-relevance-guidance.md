# RETRIEVAL: share candidate relevance guidance once

Status: ACTIVE design/implementation under user retrieval goal. Root owns backend; PRIME merge/delivery. Serial after rejected/closed2232, exact base671c79d04f165f2eb7a70b13758f1ed5623482aa, branch codex/shared-relevance-guidance. Open PRs/PRIME active UI2231 checked, no overlapping active backend lease; frozen unadopted experiments remain untouched. No dependency on them. No runtime restart or primary/live write lease.

## Evidence, hypothesis and changed variable
Actual38retained TypeSafe controller requests repeat the same relevance rule in each normal candidate question. Offline exact same candidate/criteria projection saves166725of834155serialized bytes, median20.27%. Evidence retrieval-shared-relevance-v1/retained-duplication-audit.json; independent design critique supports bounded experiment, not latency/adoption claim. Shared state exists already. Move only that static suffix once into existing relevance_guidance, keep candidate-specific label/kind/stem plus Apply relevance_guidance. Keyword/fallback instructions, candidates/order, section/full-source/Build/focus/dialogue guidance, independent votes and selected-handle authority remain unchanged. No pass, cap, ranking, evidence text, source grants, model or SDK change.

Exact historical request reconstruction requires closed current NativeRetrievalDecisionInputV2 and NativeBuildRetrievalDecisionInputV4 codecs; old nativePlanV1/BuildV2/V3 remain exact historical readers, not executable fallback. New producers emit only new codecs; unknown/hybrid bodies fail. BuildV4 retains V3 host-only phase/accounting and V2 authoring relevance. Reader fence131 is no-op data migration protecting decoder capability; primary unchanged.

## Exclusive expected writes
src/application_state/agent_conversation/jev_retrieval_contract.py;
src/application_state/agent_conversation/native_retrieval.py;
apps/live_control_server/services/plan_jev_dispatch.py;
src/application_state/migrations/versions/20261108_0131_shared_relevance_guidance.py;
tests/test_jev_retrieval_contract.py; tests/test_build_decision_context.py;
tests/application_state/test_surface_native_decisions.py; tests/test_native_object_retrieval.py;
this handoff, including truthful rejected predecessor settlement. The unmerged2232 handoff is retained on its pinned branch; do not resurrect it on adopted main.
No other source paths. Existing owner suites run unchanged. External evidence retained in established workspace.

## Validation and stopping
Independent cumulative exact-head review. Empty/single/mixed keyword catalogs; exact normal-candidate stem/criteria/order, keyword/fallback byte parity, full qualifiers and closed host metadata; old codecs actualSDKbody exact; new producer/parse/admission mismatch negatives. Owning actual Core/APP/SDK dispatch, selected Rules path, read/citation and replay tests. No historical evidence rewrite. Keep failed tests/results.
After offline gates, separately pin prospective paired current adopted-base/candidate comparison through consolidated workflow; same corpus/ordinary settings and question controls, isolated schema131 candidate only, no per-question scripts. Do not dispatch before qualified protocol/pins. Measure payload, reported tokens, billed cost when available, controller rounds and accepted-to-writer-authorization proxy separately. Reject authority/citation/covered-fact regression or no demonstrated benefit; no unchanged paid reruns until passing. Promising results require predeclared repeated full15 validation, not default adoption from byte savings.
Frozen6complete/9partial baseline, Gold and original failures remain unchanged. Four-second target is outstanding. Missing instrumentation remains unknown.

## Rejected predecessor settlement
PR2232 closed at c2c6a46d0605b38c2e259adef27f1c4913c8037d. All8ordinary captures completed, protectedsourceAPP/native rows conserved. CandidateQ14 promoted planning to played events against passingcontrol; Q09/Q15 lost supportedcontrolfacts. Neither temporal case reduced expansion-dependent rounds. Reject adoption, no unchangedrerun/full15/merge/delivery. Historicalcode/evidence retained at temporal-source-hints-v1/final-disposition.json; no active runtime/default/lease remains.

## Implemented verification, not adoption
104 contract/accounting/object checks pass, including8catalog/surface combinations,3historical exactSDK envelope hashes generated independently from671c79d04, current Plan/Build producers and closed codec/body mismatch tests.127actual Core/APP/SDK/reference/ordinaryBuild checks pass with115inherited synthetic binding warnings. Added actual currentPlanV2 test passes within13decision-module checks: nonempty normalcatalog, exactmockSDKwire, durableAPPadmission, actualCorestatement/assertionreads, reload/idempotentreplay and hybridoldparent/newbody refusal. This adds1distinctcase to the earlier127 (232distinct checks across cohorts); the13decision rerun overlaps12previouscases. Test-only failed ordering assertion corrected by appending shared rule after existingBuild/focus guidance, preserving their order. No paid calls.
Actual builder independently reconstructs all38retainedhistoricalrequestbodies exactly before newprojection; combined834155→667430serializedbytes. Retainedcontrols can be reused: b0995acc and671c79d04 have identical667backend/APP/benchmarkGit entries, latermergeUI/docs/CIonly. Freshcandidateclone/source/provider/dependencyqualification still required. Evidence retrieval-shared-relevance-v1/{actual-builder-retained-parity,control-reuse-qualification}.json and ownerlogs. Byte savings are not measured provider/wholecycle gains; finalexact-headreview/PR and prospectivecomparison remain pending.
