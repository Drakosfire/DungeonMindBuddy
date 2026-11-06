# BUILD: direct native source selection

Status: MERGED AND DELIVERED through PR2147, reviewed head90925c17cb8a036fbf29fb50a2c099021ab93477, merge55ee914218d176da70354fe8ee14e3d3dccef175. Runtime a4a54743fa908b31f41351f7a8440da1e4b116f0 passed protected activation and retained-state conservation. The qualified replay remains interrupted before the writer; catalogue delivery is not goal completion.

Historical implementation scope: PRIME owned one serial PR on codex/native-direct-source-selection,
base origin/main 6e51f7f3e79dc94512b51f2cbca0a74b7851f0c3, in the existing
buddy-context-loop checkout. PR2142 is merged and delivered as runtime cf82d95fc769.
No runtime/database write lease is active for this implementation.

Outcome: allow the current shared native controller to explicitly choose an admitted full source from
existing source metadata before a corpus-wide content scan. Keep content search
available. Metadata is navigation, not evidence or fact-publication authority.
Core owns original membership, refreshed access and immutable bytes. The retained
parent selection and exact source revision must close the actual read, optional
writer selection, producing input and citations. Never impersonate a human reference.

Write lease: this handoff; predecessor HANDOFF-BUILD-native-source-navigation-labels.md
backward-looking settlement; native_corpus.py, native_reads.py, types.py,
native_execution.py, native_retrieval.py, jev_retrieval_contract.py, service.py in src/application_state/agent_conversation;
apps/live_control_server/integrations/dungeonmind/native_corpus_source.py;
apps/live_control_server/services/corpus_source_navigation.py, plan_jev_driver.py;
new no-op reader fence 20261106_0118; focused direct-source tests, tests/test_surface_native_build_ordinary.py and tests/test_agent_native_corpus_sources.py fixture adoption/current HTTP checks, and existing
native navigation fixtures where the new offered choice changes expectations.
Other INGEST PRs2144/2145 do not overlap these paths. Held REFERENCE2104 stays held.

Validation: no body IO for metadata choices; selected-only acquisition; exact
original World/revision/hash plus refreshed Core access; stale/revoked/foreign
reads fail closed; typed unavailable results; pending reads block dispatch;
full-document exposure explicit; writer relevance selection and citation/reload
use the existing body owner; historical event decoding unchanged. Verify actual
SDK navigation bypasses broad search for direct choices and still supports fallback.
Review exact cumulative diff, independent Bugbot and CI before delivery. The
reader fence belongs with the stored event codecs. Do not change provider roles,
limits or claim that catalogue navigation alone completes retrieval/References.
One qualified ordinary replay follows reviewed delivery, with original failure
and source/database conservation retained. No fresh ingestion or publication.

Historical PlanSource/PlanNative event codecs remain unchanged. Direct choices are offered only by the current SurfaceNative owner; no extension of historical database event whitelists.

Implementation note: direct selection remains available after lexical search,
without offering an equivalent second full-document address. Acquired extents
are compared by exact source pair/hash and interval, including across refreshed
source epochs. Existing sections remain offered when not already covered.
Core freshness is factored from the existing selected-body reader, not duplicated.

CI validation amendment: saved-page-readers completed all427 tests successfully
in1772.17s, but its30-minute job deadline canceled the process after pytest's
summary and failed the aggregate gate. Retain that terminal log and allow45minutes
for this measured suite only; other groups remain30minutes. No test removal,
retrieval-budget change or runtime behavior change. This required validation
repair remains with the owning source-choice tests in this PR.

Explicit workflow split lease: PR2147 owns the matrix timeout-minutes value and its new direct-source test selector
in .github/workflows/world-ownership-core.yml. Inspected open INGEST2087 head
687b26a2b83b5fe424801245b1cd199c1d183630 (frozen code, external-call hold) owns its
three ingestion test selectors; held REFERENCE2104 owns its four query selectors.
Neither concurrent hunk is changed or activated. Their holds remain intact.

CI coverage closure: include tests/test_native_direct_source_selection.py in the
existing saved-page-reader group, alongside native source access and body writer
selection. The new file's negative grants, advanced epochs, actual SDK input,
ordinary Build inclusion/exclusion, source reopening and mixed-search cases must
remain in the normal owning regression gate. No existing selector is removed.


Qualified replay99351a42-364e-42a6-b77c-aaa326388d78:61.756s,8Jev calls,
6retrieval decisions,35body reads (22direct),18selected source units, no writer
call. The228909 conservative estimate exceeded128000. All19 navigation failures
were sections already covered by full reads in the same selected batch. Original
failure, Core state, saved pages and Runs remain unchanged. Private evidence:
q01-published-graph-authority/direct-source-replay-comparison.json and
 direct-source-replay-batch-coverage-audit.json under the established runtime evidence root.
Next bounded slice recognizes this exact same-batch fulfillment; capacity accounting,
retrieval efficiency and Play References remain separate unfinished goal work.
