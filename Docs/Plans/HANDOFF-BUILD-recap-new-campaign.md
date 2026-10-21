# BUILD — Recap extraction for a new campaign

ACTIVE serial slice under the operator's ingestion-in-Build goal. PRIME owns design, implementation and merge; Bugbot independently reviews the exact head. Base 58cdadcaf70e0bff5a6a8a54587f0f365f892fcc; branch codex/build-recap-new-campaign in the existing buddy-context-loop checkout. Held Plan Jev1546 and Worldbuilding review1235 are disjoint/read-only.

Invariant: a verified native World/campaign can extract its imported external Recap without a pre-existing local corpus/party registry. An absent local registry means no standing party identities; it must not select another campaign's corpus or suppress source-supported new actors. Explicit corpus mappings and malformed registries retain their validation. No provider, model, cap, native membership, source-admission or publication-policy changes.

The ordinary Build route freezes a known-identity snapshot before inference; both that snapshot and category extraction currently require a hardcoded campaign corpus mapping. A fresh campaign cannot reach extraction. Verify this at the Build launch boundary before repairing the optional identity enrichment.

Exclusive writes: this handoff; src/graph_memory/party_context.py; src/graph_memory/session_graph_context.py; src/graph_memory/extraction/known_entity_registry.py; tests/test_build_recap_launch.py; tests/test_graph_memory_party_context.py; tests/test_graph_memory_known_entity_registry.py; tests/test_graph_memory_session_graph_context.py. No edits to PR1235 source-observation review or held1546 paths. Topology serial; this independently useful Build slice is separate from held Plan activation.

Verification: existing disposable APP PostgreSQL fixture, owning Build launch/recovery test, identity snapshot and category pipeline, explicit registry regression and invalid session cases. No retained World writes or private provider calls. Inspect cumulative diff, commit/push/open PR, independent Bugbot, merge, guarded immutable API adoption preserving all retained rows/drafts. Real public-provider extraction and native acceptance remain subsequent end-to-end evidence, not implied by deterministic tests.
