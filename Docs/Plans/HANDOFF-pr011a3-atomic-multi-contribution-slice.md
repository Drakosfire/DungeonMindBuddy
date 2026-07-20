# HANDOFF — PR011A3 slice 3: atomic multi-contribution + slice-qualified selection

**Status:** `DOING` (GitHub PR #375)  
**Base:** `main` (includes merged #369 promote-IR + #370 existing-object observation)  
**Branch:** `agent/pr011a3-atomic-multi-contribution`  
**Umbrella:** #367 (DO NOT MERGE fat tip `eb509dae`)  
**Successor:** #376 known-entity extraction (must stack **after** this PR; this PR must not import `known_entity_*`)

## §1 Mission

Land one sealed multi-slice promote (standing_context + source_extraction) as a **single** Kernel merge, with product-boundary selection that can independently control colliding cross-slice assertion IDs.

## §2 Invariant

Live A3 acceptance remains **PARTIAL / NOT_READY_FOR_CANONICAL_RECAP_BACKFILL** until a fresh prepare→confirm→exact committed revision reload is recorded. This slice does not claim full A3 acceptance.

## §3 Observable paths

- Prepare HTTP response validates review rows that include `sliceQualifiedId` / `contributionSliceId` / `dependsOnSliceQualifiedIds`.
- Graph Review selection Set keys, React keys, dependency cascade, and confirm `assertionIds` use slice-qualified selectors.
- Selecting both colliding semantic assertion IDs unions evidence provenance; standing-only / recap-only / both yield distinct `selection_digest` → distinct contribution identity.
- Selected assertions are ordered nodes (then mid) before edges before Kernel merge.
- Present but unreadable/malformed `registry_context_graph.json` sibling (or declared registry artifact) fails prepare closed — never silent recap-only.
- Extractor / preview runner do **not** import `known_entity_*` modules (owned by #376).

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/graph_memory/extract_identity_gate.py` | Provenance union; nodes-before-edges; slice-id selection_digest |
| Modify | `src/graph_memory/extract_promote_ops.py` | Pass sealed `contribution_slice_id` into multi-slice builder |
| Modify | `src/graph_memory/extract_promote_proposal.py` | Slice-qualified selectors / seal (prior commits) |
| Modify | `src/graph_memory/extract_promote_review_projection.py` | Emit qualified IDs (prior commits) |
| Modify | `src/graph_memory/standing_context_partition.py` | Standing vs recap partition |
| Modify | `src/graph_memory/party_context.py` | Standing registry context builder |
| Modify | `src/graph_memory/extraction/category_candidate_graph_extractor.py` | Standing partition only; **no** known-entity |
| Modify | `evals/graph_memory_layer/graph_preview_runner.py` | Registry artifact path; **no** known-entity sidecar |
| Modify | `apps/live_control_server/models/extract_promote.py` | Strict model accepts qualified fields |
| Modify | `apps/live_control_server/services/extract_promote.py` | Fail-closed registry sibling |
| Modify | `apps/live_control_server/services/promotable_ingest_run.py` | Fail-closed declared registry artifact |
| Modify | `apps/live-control-ui/src/api/types.ts` | TS qualified selection fields |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/extractPromoteSelectionUtils.ts` | Select by `sliceQualifiedId` |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/extractPromoteSelectionUtils.test.ts` | Cross-slice select A/B/both |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.tsx` | Key/toggle/confirm qualified |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx` | Sheet fixtures |
| Modify | `tests/test_extract_identity_gate.py` | Provenance union + edge order proofs |
| Modify | `tests/test_extract_promote_ops_atomic.py` | Atomic confirm path |
| Modify | `tests/test_extract_promote_proposal.py` | Qualified selector resolution |
| Modify | `tests/test_standing_context_partition.py` | Partition unit tests |
| Modify | `tests/test_graph_memory_party_context.py` | Party context unit tests |
| Modify | `tests/test_live_extract_promote_api.py` | HTTP prepare qualified fields + malformed registry |
| Create | `Docs/Plans/HANDOFF-pr011a3-atomic-multi-contribution-slice.md` | This handoff |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Point #375 / this handoff |

## §5 Files and capabilities explicitly out of scope

| Path / capability | Why |
|---|---|
| `src/graph_memory/extraction/known_entity_*.py` | Owned by PR #376 |
| Known-entity prompts, ledger injection, mention sidecars | #376 |
| Author Node / Plan hover / Recap chip UI | Other product slices |
| Fat tip `eb509dae` reconstitution | Read-only reference |
| Declaring A3 `PASS` / canonical recap backfill ready | Requires fresh dogfood after merge |

## §6 Implementation contract

```text
Input:
  Sealed multi-slice review package (standing_context + source_extraction)
  Operator selection as slice-qualified selectors

Output:
  ONE GraphContribution merged once
  Unioned evidence when both colliding assertions selected
  Nodes applied before edges

Invariant:
  No partial head advance across slices
  No silent drop of selected provenance
  No prepare success when declared/present registry is malformed
  No import of known_entity modules on this branch tip
```

## §7 Verification commands

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy-pr011a3-atomic

# Known-entity must stay absent on this tip
rg -n "known_entity|KnownEntity" \
  src/graph_memory/extraction/category_candidate_graph_extractor.py \
  evals/graph_memory_layer/graph_preview_runner.py \
  && echo FAIL || echo PASS_no_known_entity

PYTHONPATH=src:apps python -m pytest \
  tests/test_extract_identity_gate.py \
  tests/test_extract_promote_ops_atomic.py \
  tests/test_extract_promote_proposal.py \
  tests/test_standing_context_partition.py \
  tests/test_graph_memory_party_context.py \
  tests/test_live_extract_promote_api.py \
  -q

cd apps/live-control-ui && npm test -- --run \
  src/planSurface/graphReviewWorkbench/extractPromoteSelectionUtils.test.ts \
  src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx \
  src/api/extractPromoteApi.test.ts
```

**Author-local proof (2026-07-20):** 82 pytest passed (scoped command above); 18 UI tests passed (selection + sheet + API). No GitHub Actions run attached until push.

## §8 Remaining false capabilities

- Exact Session 25 prepare→confirm→committed-revision reload dogfood (A3 still PARTIAL).
- Known-entity extraction / registry ledger (#376).
- Standing-context sealed confirm path still must not claim full campaign backfill readiness.
