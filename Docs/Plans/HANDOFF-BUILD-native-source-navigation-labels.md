# BUILD: native source navigation labels

Status: DELIVERED. PR2142 merged at 6e51f7f3e79dc94512b51f2cbca0a74b7851f0c3;
reviewed head e737b188961465c6c4adbb25bb18308707ee2a45, all CI passed.
Delivered frozen runtime cf82d95fc76980789c1f3f95eba1be055e7e8de1. Write lease
released. The ordinary replay retained typed capacity failure (328176 >128000),
seven Jev calls and no writer call; labels alone did not solve retrieval capacity.

Historical lane: codex/native-source-navigation-labels in buddy-context-loop,
based on main f9db16c4fa3c038a6be7eba3dae7ff0c0da50eba. Parent PR2141 was merged
and delivered before this child, as runtime b8612ec782f606a49555296092104b1ec97e7a81.
No new checkout or dependencies. No continuing runtime lease.

Outcome: adopt the human native source inspector's existing source/revision-joined recap/page display metadata in model navigation choices instead of treating the first section label as the document name. Extract that one display owner for both consumers; remove the old private inspector-only implementation. Core source identity, eligibility, scope, authorization and immutable body remain unchanged. Labels neither admit sources nor establish campaign facts. Preserve exact revision joins; mark unavailable metadata and newer page labels honestly. Cache only presentation within this navigation instance, not source bodies/access/provenance across requests.

Write lease: this handoff; predecessor HANDOFF-BUILD-native-acquisition-observations.md backward-looking delivery settlement; services/native_source_display.py, native_source_inspection.py, corpus_source_navigation.py; tests/test_native_source_inspection.py and focused tests/test_native_source_navigation_labels.py; tests/test_native_reference_navigation.py constructor/context fixture adoption; UI WorldPlanAgentConversation.worldHistory.test.tsx existing correlated-history readiness assertion synchronization (no production UI change). Parent corpus_source_navigation.py lease is frozen at its exact committed head; this child consumes that head and owns successor changes in this checkout. Other active INGEST lanes and held REFERENCE2104 remain separate.

Validation: existing human inspection tests keep their native source-opening behavior; model choices show exact joined recap campaign/session names; foreign, changed and unavailable metadata cannot name or hide sources; source revision identity and read/citation admission stay native-owned. Verify one presentation lookup per navigation instance and no lookup before source search or an explicitly selected authored-source acquisition. Run provider-free ordinary acquisition/replay fixtures, inspect cumulative parent-to-child diff, get independent Bugbot review and CI. Retain original failure; do not claim this alone fixes latency, writer capacity, References or operator acceptance. No provider rerun until a qualified candidate is ready.

CI checkpoint: query suite identified projection fixtures bypassing NativeBodyNavigation.__init__; use its real trusted native context/constructor rather than adding runtime accommodation. Hosted UI reached its existing asynchronous Send readiness assertion before hydration settled; await that actual enabled state, without changing product guards or adding a timer. Preserve failed CI logs; re-review the cumulative head and rerun owning tests.
