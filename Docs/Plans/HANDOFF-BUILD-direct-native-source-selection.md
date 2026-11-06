# BUILD: direct native source selection

Status: ACTIVE. PRIME owns one serial PR on codex/native-direct-source-selection,
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
new no-op reader fence 20261106_0118; focused direct-source tests, tests/test_surface_native_build_ordinary.py fixture adoption, and existing
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
