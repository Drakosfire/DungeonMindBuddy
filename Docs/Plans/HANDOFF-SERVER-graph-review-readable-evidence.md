# Graph Review source-readable evidence
Status: MERGED. PRIME independently accepted PR #1116 at reviewed head `313e972c` (review `6138825453`); Buddy main merge `ec1da1b7872fe6d4f9fee0b501510a5137677eea`. Implementation lease released. Runtime rollout remains separate.
Base: re-anchor remote Buddy main (last accepted e5136705fb574aab4910113cc58034088df65734). Pin Core exact merge d81ed4e126c55ef8df57804c9ab7128b7499c7a1, accepted PR117 head a8346d9, CI38348352077 success, independent58-test PG boundary proof.
Finding: /tmp/source-readable-graph-review-preparation-20261012.md SHA256 8f43470145a37e79909416edb36e8ad8229f506776a14ad88d0dd19f1a143f3c.
Witness: /tmp/source-readable-graph-review-witness-20261012.py SHA256 3d483c27c34bd4b3bd621be5680c6ca2e378deb61e97454f29a0f1bf15b8da39. PRIME independently reran this against current47bc: both source types prepare EXPRESSIBLE, no accepted evidence span, recap incorrectly worldbuilding, can_open_source true from locator alone. This proves prepare/translation failure; no claim that bad inputs passed Core publication.

User outcome: New source-backed Graph Review contributions retain evidence pointing to exact readable source passages. A file registration alone cannot masquerade as a readable citation.
Owner: SERVER, Sol low initially. Escalate bounded contract/concurrency issues to PRIME instead of repeated cheap attempts. Isolated nonlive lane; keep current serving checkout stable.

Exact write lease:
- apps/live_control_server/services/graph_object_authoring_prepare.py (includes translator)
- apps/live_control_server/services/graph_object_authoring_commit.py
- apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
- apps/live_control_server/integrations/dungeonmind/contribution_mapping.py
- pyproject.toml (Core pin only)
- uv.lock (corresponding locked Core update only)
- tests/test_graph_object_authoring_prepare.py
- tests/test_graph_object_authoring_commit.py
- tests/test_graph_object_authoring_published_recap_write.py (fixture update to real verified spans, same publication behavior)
- tests/test_cutover_graph_review_authoring_continuity.py (fixture-only verified source selections and pinned passage readback; preserve existing publication assertions)
- tests/test_graph_review_source_readable_evidence.py (new if needed)
- tests/test_graph_review_typed_evidence_mapping.py (new if needed)
- Docs/Plans/HANDOFF-SERVER-graph-review-readable-evidence.md
Additional paths require PRIME amendment before editing; name existing helper needed and actual reason. Reuse source registry/span indices/readers and admitted source APIs. No new Core contract or obsolete-format decoder.

Requirements:
1. Resolve each source-backed accepted assertion to an explicit verified source span, immutable artifact/revision/digest and current scope/visibility. Selected text offsets alone are not authority. Missing/unresolvable/mismatched spans prevent confirmation with useful repair guidance, without guessing whole-file passages.
2. Preserve per-assertion evidence identity and verified span through contribution translation and sealed digest. At confirm re-prove exact source/body/index inputs; drift blocks publication before writes. Correctly derive worldbuilding vs session_recap source domain from admitted source, not selector guesses or hardcoding.
3. Source opening capability follows verified span/readability, never mere locator presence. Preserve native evidence mapping and existing opener contracts.
4. One disposable worldbuilding and one recap contribution must pass real prepare/confirm publication boundary to child revision and pinned read_source_anchor exact passage. Fail closed for missing span/body, wrong digest/scope and prepare→confirm drift. Pure helper tests alone cannot establish published readability.
5. Preserve existing authored knowledge and unrelated authoring paths. No retained DB/corpus/registry writes, migration, provider calls, live restart or broad backfill under this lease. Disposable isolated fixtures/databases only.
6. Finish focused verification, cumulative diff review, commit/push/one PR with exact head and evidence. PRIME independent review/merge; rollout separate. No full-World readiness claim.

## Core prerequisite decision
Architecture decision /tmp/decision-graph-review-typed-source-span-20261012.md SHA256 0fca3edad16c73470d0a292ea7a9f8fa6ac16b913047699cbfbd791da8631eb6 is accepted. Current GraphContributionV2 accepts v1 EvidenceRef only; its opaque locator cannot substitute for explicit source_span_ref_id. MIND owns one versioned typed-evidence review/publication prerequisite. After its independent review and merge, PRIME will pin Core and amend Buddy mapping, lock and native review adapter write paths. Serving runtime remains47bc; new Buddy main e513 contains the merged observations UI.

## Activated consumer requirements
Use governed Contribution/Review V3 for new source-backed Graph Review writes. Preserve the reviewed typed EvidenceRefV2 span and immutable evidence identity in a new digest domain, with URI/locator independent. Existing initialization/recap extraction callers outside this slice keep their current contracts; no decoder or old-world backfill. Source text/paragraph ordinal may only be hints for a unique exact span in verified registered bytes/index; missing or ambiguous matches fail before confirmation. No fuzzy search or first-match guess. Inspect the preserved uncommitted prepare-verifier WIP before reuse; it is not accepted evidence. Create/update dependencies in a NONLIVE environment only; serving47bc stays untouched.


## Implementation evidence — 2026-10-12

- Exact intended Buddy base: `e5136705fb574aab4910113cc58034088df65734` (`origin/main` after fetch). Implementation code commit: `86d5b02aac8f189459cb5053ed7966c92f5180b9`. The final PR head adds only this evidence handoff.
- Core pin: merged `d81ed4e126c55ef8df57804c9ab7128b7499c7a1` in both `pyproject.toml` and `uv.lock`. Nonlive test interpreter imported `contribution_review_v3.py` and `evidence.py` from an exact `git archive` of that Core commit, ahead of the read-only locked Buddy interpreter. `uv lock --check --offline`: 145 packages resolved.
- Fresh Graph Review prepare and confirm each verify registered source bytes, scope, status, visibility, revision digest and one exact indexed worldbuilding span or digest-bound recap paragraph. The contribution seals per-assertion evidence identity, span/body/index digests and correct source domain; confirm compares the reconstructed contribution digest before publication. Missing/ambiguous selections, missing index, wrong scope, changed body and prepare→confirm drift fail closed in focused tests.
- The fresh Graph Review source kind maps to Core `GraphContributionV3` / `EvidenceRefV2` with a typed `source_span_ref_id`, readable capability and distinct `:dmv3:` evidence-binding digest. Its publication uses V3 intent, receipt, capability rule and finalization. Other source kinds retain their V2 path; no legacy evidence decoder was added.
- Focused local tests: 58 passed, 1 integration case deselected for separate PostgreSQL run. Ruff check on all changed Python files passed. `git diff --check` passed.
- Owned disposable `pgvector/pgvector:pg16` PostgreSQL container, fresh migrated Core DB and disposable application-state DB: 4 passed (`test_cutover_graph_review_authoring_continuity.py` two tests; `test_graph_object_authoring_published_recap_write.py::test_published_recap_write_uses_setting_world_for_campaign_scope`; `test_cutover_worldbuilding_authority_port.py::test_publication_provenance_keeps_threat_strings_and_splits_worldbuilding`). Container was removed in `finally`. The worldbuilding child pinned read matches registered indexed line-span bytes and whole source digest. The recap child pinned read matches the exact paragraph and source digest. The existing worldbuilding V2 policy provenance test still passes.
- Cumulative diff inspected against the exact base: only the amended lease paths. No serving checkout, retained database/corpus/registry, provider or live runtime was written. No merge or rollout performed.
- Unrelated existing overlap/merge-prepare tests without any source selector fail `source_unresolved` on the untouched prior checkout as well; this slice did not modify those out-of-lease fixtures. No full-World readiness claim.

Acceptance witness for PRIME: independently review the exact PR head, confirm the Core pin and source-kind V3 dispatch, and rerun the two disposable child/pinned-read boundaries. The implementation meets this handoff's bounded acceptance conditions subject to PRIME review.
