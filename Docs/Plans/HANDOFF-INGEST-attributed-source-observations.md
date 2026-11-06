# INGEST: retain attributed source observations

Status: ACTIVE. Root adopts this bounded policy clarification under the user's ingestion implementation authorization.

## Lane and topology

Branch `codex/ingest-attributed-source-observations`, base PR #2124 at `c237a9a8c4181f2dfe4c11055f8a38f59153f4ac`. Stacked: merge/rebase #2124 first, then this PR. Remote main/open PRs re-anchored; PRIME's #2125 storage lane is independent of these three paths. No merge/deployment authority implied.

## Scope and evidence

Replace the existing final rhetoric/presentation paragraph of `_RECAP_SOURCE_FAITHFULNESS`; do not append a second rule. Current guidance explicitly rejects literalized figurative attributes but expressly retains only table observations. The distinction is underspecified, not proven causally responsible for model omissions. Retain material narrator/character comparisons as attributed observations without asserting literal mechanics. Preserve uncertainty when presentation could be table material, world material or both.

Design critique: `c1-source-faithfulness-attributed-rhetoric-policy-design-critique-v1.json`, SHA256 `e048532a84bac4ebf8d35552f5b8408252be48ef71bb05b5fa737e4692690074`. Actual admitted-input/producer evidence: `c1s05-s07-common-build-independent-semantic-owner-analysis-v1.json`, SHA256 `0b3483a34ce7a4f005cb3cf5d33d3981b27785cbf36279a9891ed194a422953a`.

Expected writes:
- `src/graph_memory/extraction/recap_extraction_profile.py`
- `tests/test_recap_source_faithfulness_profile.py`
- This handoff.

The shared policy reaches recap nodes, beats, edges and recap preview/encounter prompts. It is not actor-only. Keep Worldbuilding, schemas, source-authority partition, object ignored/deferred policy, inference allocation/retries, producer topology and quote guards unchanged. No corpus-specific names, examples or answer hints in production instructions. No chronology-resolution claim.

## Validation and delivery

Synthetic contrast cases cover attributed comparison, metaphor, boast, rhetorical question, explicit table handout, explicit in-world object, and unresolved/both presentation. Verify actual rendered policy/source delivery, unchanged wire schemas and unrelated instructions, recap preview propagation and Worldbuilding exclusion. Tests establish prompt contracts, not model compliance. Fresh Session 7 and full-corpus Gold/precision checks must establish quality. Preserve all historical failures; do not manufacture claims or relax Gold.

Inspect cumulative diff, independent subagent review, commit/push/open one PR. Live cohort 28770, frozen runtimes, databases and primary data remain untouched.
