# INGEST: review an exact candidate-description extent

Status: ACTIVE. ADV owns design and implementation under the user's ingestion-quality goal. Independent subagent review is required; PRIME coordinates merge and delivery only.

## Lane and outcome

Serial successor to allocation PR #2068, merged and delivered at `1da4f8f60793103298ae2f2fadd1f30bd379c32f`. Base is that fetched remote main; branch `codex/review-description-extents`, checkout `/home/drakosfire/Projects/.codex/249d/DungeonMindBuddy`. Open #2069, #1868, #1855 and #1853 write sets were inspected and do not overlap this lease. No unmerged behavioral dependency or merge authority is allocated.

Retain a supported, unmodified contiguous part of an immutable candidate node description when the entire description cannot be accepted. Use the existing summary literal, reviewed source evidence, identity choice and WK/Core publication path. This is a review-granularity capability, not a new producer, model, representation, inference pass or source-statement substitute.

The demonstrated case is retained Session 7 run `a9439d7c-5a07-4429-aa64-159a677ed0ca`: the initial Inn no-vacancy clause exists in actual model output but was lost when its mixed description was held. Independent published coverage is 85/89 complete, three absent, one partial. This capability can recover that one clause without inference or rewriting. The other incomplete details occur only in raw model beats and remain a separate problem. Full Sessions 1–10, worldbuilding and benchmark requirements remain unchanged.

## Contract and failure cases

- Add a separate strict description-extent selector variant. Do not add serialized defaults to the existing whole-field selector: old recap/worldbuilding signed envelopes and committed recovery must remain valid.
- Exactly one description choice per record remains the existing rule. Whole plus extent, duplicate extents and multiple disjoint extents are rejected by the existing duplicate `(field, index)` check. No new overlap machinery.
- The new variant requires nonempty, proper UTF-8 byte bounds and an expected slice SHA256. The owner checks against the saved candidate's actual description under its already verified digest. Reject full-field ranges (use the existing selector), bad bounds, split Unicode, whitespace-only text and digest drift. Never trim, rewrite, join, summarize or fall back.
- Node descriptions only. No clipping labels, types, actions or source-owned beat summaries. Preserve the settled source-excerpt invariant from `HANDOFF-INGEST-extractive-beat-summaries.md`.
- Literal presence does not prove entailment. The explicit reviewer still chooses source support, identity, uncertainty and qualifications from the complete context. No sentence heuristic or semantic regex filter.
- The preparation owner derives native provenance: run/revision, actual candidate digest, record/field, byte extent and actual slice digest. Store it in the existing registered world-context metadata. Reserve the owner key against caller spoofing; preserve other caller metadata. Do not rely only on operator strings or audit files.
- Inventory must distinguish the selected extent from acceptance of the whole description, leave the whole field unselected and identify its held remaining byte ranges.
- This shared native selector contract applies to recap and worldbuilding candidate APIs; verify both without claiming worldbuilding corpus acceptance. No frontend native-prepare authoring consumer was found during independent design review. Backend API scope only; no new UI workflow is claimed.

Independent design critique `independent-description-slice-design-critique-v1.json` (durable chat evidence), SHA256 `10f97036bdf5b7ecd48cd7d1074afc5e88ee73d11f2971103f4c8f8a78bc77ce`, supports the narrower one-extent design. The native-provenance and inventory gates above are adopted before activation.

## Exclusive expected write lease

- `apps/live_control_server/models/native_recap_preparation.py`: additive strict selector variant and node-only validation.
- `apps/live_control_server/services/native_recap_preparation.py`: exact byte resolution, owner provenance, honest inventory; preserve existing source and commit owners.
- `tests/test_native_recap_preparation.py`: boundary, normalization, signature, recovery and disposable PostgreSQL tests in the existing CI-discovered owner suite. No shared workflow edits.
- `tests/fixtures/native_review_envelopes_before_description_extents.json`: synthetic pre-change wire/signature fixtures.
- `Docs/Plans/HANDOFF-INGEST-recap-reasoning-effort.md`: truthful settlement of the merged predecessor.
- This handoff.

If another runtime capability, public contract or path is needed, checkpoint and split or revise this lease before editing. No Core/WK changes, migration, dependency/lockfile change, inference prompt, provider call, primary/evaluator write or runtime delivery belongs to implementation. Tests may use disposable PostgreSQL fixture databases on 54329 (APP) and a temporary `dmb-description-extent-test-pg` pgvector container on 55449 (Core). The temporary container uses pgvector/pgvector:0.8.6-pg16 (Docker pulled the tag because no local tag was available) and is removed after proof. Never primary 54331, dogfood 54330 or retained evaluator 55447.

## Validation and delivery

Capture synthetic legacy normalization/signatures before editing the model. Verify strict malformed selectors, UTF-8 boundaries and exact bytes, one-extent uniqueness, protected source-excerpt behavior, reserved provenance, source/run/candidate/identity gates, old whole-field semantics and recap/worldbuilding committed recovery. Prove the added literal and owner-derived metadata through ordinary prepare/confirm and real persistence. Inspect the cumulative base-to-head diff, lint, commit, push and open one PR; obtain independent exact-head review. Merge remains separate authority.

After reviewed delivery or an exact pinned isolated handoff, reuse the unchanged actual Session 7 run and the already published Inn identity. Select only the retained true prefix, with explicit source-relative metadata. Confirm through the ordinary owner, preserving all prior graph contents and the original whole-field failure. No new model call. Independently verify the added literal, source opening, native provenance and Gold improvement. This is not full Gold or whole-goal completion.

Validation: 165 owning boundary tests passed; the additional disposable pgvector prepare/confirm/fresh-readback test passed separately (166 total). Ruff and diff whitespace checks passed. Preceding fixture/network/migration setup failures are retained in durable chat evidence. Temporary test container removed; no primary or retained evaluator effects.
