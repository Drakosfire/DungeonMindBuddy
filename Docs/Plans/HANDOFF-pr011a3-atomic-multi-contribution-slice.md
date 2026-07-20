# HANDOFF — PR011A3 slice 3: atomic multi-contribution + slice-qualified selection

**Status:** `DOING` (GitHub PR #375)  
**Base:** `main` (includes merged #369 promote-IR + #370 existing-object observation)  
**Branch:** `agent/pr011a3-atomic-multi-contribution`  
**Umbrella:** #367 (DO NOT MERGE fat tip `eb509dae`)  
**Successor:** #376 known-entity extraction (must stack **after** this PR; this PR must not import `known_entity_*`)

## §1 Mission

Land one sealed multi-slice promote (standing_context + source_extraction) as a **single** Kernel merge, with product-boundary selection that can independently control colliding cross-slice assertion IDs, and with selected provenance that survives Kernel materialization.

## §2 Invariant

Live A3 acceptance remains **PARTIAL / NOT_READY_FOR_CANONICAL_RECAP_BACKFILL** until a fresh prepare→confirm→exact committed revision reload is recorded. This slice does not claim full A3 acceptance.

## §3 Observable paths

- Prepare HTTP response validates review rows that include `sliceQualifiedId` / `contributionSliceId` / `dependsOnSliceQualifiedIds`.
- Graph Review selection Set keys, React keys, dependency cascade, and confirm `assertionIds` use slice-qualified selectors.
- Selecting both colliding semantic assertion IDs unions top-level refs **and** embedded `value.evidence` / `value.source_artifacts` / `value.source_domains`; merge + projection retain both sources.
- Selected assertions are ordered nodes (then mid) before edges before Kernel merge.
- Present registry sibling **or** manifest-declared registry artifact (any in-run filename) must be typed CandidateGraphPreview IR with ≥1 node and a **nonblank campaign_id equal to the run campaign** — wrong-schema `{}`, empty nodes, blank campaign, or foreign campaign fail closed.
- `PromotableIngestRun.registry_context_graph_path` retains the declared artifact path; product prepare loads that path (sibling filename is only a fallback when undeclared).
- Extractor / preview runner do **not** import `known_entity_*` modules (owned by #376).

## §4 Files in scope (allowlist)

Exact `git diff --name-only origin/main...HEAD` inventory for this PR (**36 paths** after round-3). Do **not** list inherited slice-2 (#370) files that are already on `main`.

| Action | Path | Purpose |
|---|---|---|
| Modify | `Backlog-DONE.md` | Carry-forward backlog archive notes |
| Modify | `Backlog.md` | Carry-forward backlog notes from reconstitution |
| Create | `Docs/Plans/HANDOFF-pr011a3-atomic-multi-contribution-slice.md` | This handoff |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Point #375 / this handoff |
| Modify | `apps/live-control-ui/src/api/types.ts` | TS qualified selection fields |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx` | Sheet fixtures |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.tsx` | Key/toggle/confirm qualified |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/extractPromoteSelectionUtils.test.ts` | Cross-slice select A/B/both |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/extractPromoteSelectionUtils.ts` | Select by `sliceQualifiedId` |
| Modify | `apps/live_control_server/models/extract_promote.py` | Strict model accepts qualified selection fields |
| Modify | `apps/live_control_server/services/extract_promote.py` | Use resolved registry path; require campaign_id |
| Modify | `apps/live_control_server/services/promotable_ingest_run.py` | Retain declared registry path; require campaign_id |
| Modify | `evals/graph_memory_layer/graph_preview_runner.py` | Registry artifact path; no known-entity sidecar |
| Modify | `src/graph_memory/candidate_graph_preview.py` | Candidate IR support for multi-slice gate |
| Modify | `src/graph_memory/candidate_graph_to_contribution.py` | `source_kind` + mapper for standing/recap |
| Modify | `src/graph_memory/candidate_semantic_promote_matrix.py` | Promote matrix support for standing |
| Modify | `src/graph_memory/evidence/source_domain.py` | Source-domain policy for dual provenance |
| Modify | `src/graph_memory/extract_identity_gate.py` | Provenance union (embedded); nodes-before-edges; slice digest |
| Modify | `src/graph_memory/extract_promote_ops.py` | Multi-slice prepare/confirm; required standing campaign |
| Modify | `src/graph_memory/extract_promote_proposal.py` | Slice-qualified selectors / seal |
| Modify | `src/graph_memory/extract_promote_review_projection.py` | Emit qualified IDs |
| Modify | `src/graph_memory/extraction/category_candidate_graph_extractor.py` | Standing partition only; no known-entity |
| Modify | `src/graph_memory/ingestion/graph_ingest_run.py` | Registry artifact kind wiring |
| Modify | `src/graph_memory/kernel/contribution_models.py` | Contribution model support |
| Modify | `src/graph_memory/party_context.py` | Standing registry context builder |
| Modify | `src/graph_memory/session_graph_context.py` | Party/session context for standing |
| Modify | `src/graph_memory/standing_context_partition.py` | Standing vs recap partition |
| Modify | `tests/test_candidate_graph_to_contribution.py` | Mapper / typed load |
| Modify | `tests/test_extract_identity_gate.py` | Provenance merge+project; edge order |
| Modify | `tests/test_extract_promote_ops_atomic.py` | Atomic confirm path |
| Modify | `tests/test_extract_promote_proposal.py` | Qualified selector resolution |
| Modify | `tests/test_graph_memory_candidate_graph_preview.py` | Candidate IR |
| Modify | `tests/test_graph_memory_party_context.py` | Party context |
| Modify | `tests/test_live_extract_promote_api.py` | Declared-path + blank-campaign registry fail-closed |
| Modify | `tests/test_promotable_ingest_run.py` | Declared path retained; blank campaign rejected at resolve |
| Modify | `tests/test_standing_context_partition.py` | Partition unit tests |

**Bounded discovery exception:** Not applicable — paths enumerated above match `origin/main...HEAD` after round-3 (36).

## §5 Files and capabilities explicitly out of scope

| Path / capability | Why |
|---|---|
| `src/graph_memory/extraction/known_entity_*.py` | Owned by PR #376 |
| Known-entity prompts, ledger injection, mention sidecars | #376 |
| Author Node / Plan hover / Recap chip UI | Other product slices |
| Fat tip `eb509dae` reconstitution | Read-only reference |
| Declaring A3 `PASS` / canonical recap backfill ready | Requires fresh dogfood after merge |
| Slice-2 (#370) observation / repair / session_ids files | Already on `main`; not re-owned here |

## §6 Implementation contract

```text
Input:
  Sealed multi-slice review package (standing_context + source_extraction)
  Operator selection as slice-qualified selectors
  Optional present registry_context_graph sibling OR manifest-declared registry artifact

Output:
  ONE GraphContribution merged once
  Unioned evidence_ref_ids + embedded evidence/source_artifacts/source_domains
  Nodes applied before edges
  Prepare refuses malformed/blank-campaign/wrong-campaign/empty registry graphs
  Declared registry path retained and loaded by prepare

Invariant:
  No partial head advance across slices
  No silent drop of selected provenance at Kernel materialization
  No prepare success when declared/present registry is invalid, unscoped, or mistyped
  No silent omit of a valid declared registry under a non-sibling filename
  No import of known_entity modules on this branch tip
```

## §7 Verification commands

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy-pr011a3-atomic

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
  tests/test_promotable_ingest_run.py \
  -q

cd apps/live-control-ui && npm test -- --run \
  src/planSurface/graphReviewWorkbench/extractPromoteSelectionUtils.test.ts \
  src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx \
  src/api/extractPromoteApi.test.ts
```

**Author-local proof:** 102 pytest passed (scoped command above, including `test_promotable_ingest_run.py`).

## §8 Remaining false capabilities

- Exact Session 25 prepare→confirm→committed-revision reload dogfood (A3 still PARTIAL).
- Known-entity extraction / registry ledger (#376).
- Standing-context sealed confirm path still must not claim full campaign backfill readiness.
