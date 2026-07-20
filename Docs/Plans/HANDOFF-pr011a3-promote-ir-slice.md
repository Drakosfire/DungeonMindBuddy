# HANDOFF — PR011A3 slice 1: promote-IR closeout

**Status:** `DOING` (GitHub PR #369)  
**Base:** `#366` merge `37c0a79d`  
**Branch:** `agent/pr011a3-promote-ir-closeout`  
**Umbrella:** #367 (DO NOT MERGE fat tip `eb509dae`)

## §1 Mission

Make Session-class extracts seal/prepare with typed `SemanticState` + promote-eligible `EvidenceRef`, and project promote-safe candidate IR so typed validation succeeds for **session-evidenced** graph objects.

## §2 Invariant

Live A3 acceptance remains **PARTIAL / NOT_READY_FOR_CANONICAL_RECAP_BACKFILL** until a fresh prepare→confirm→**exact committed revision reload** (+ Hermes retrieve if claimed) is recorded. Repair of a later head is not forward proof.

## §3 Observable paths

- Category assemble stamps typed SemanticState + promote EvidenceRef IR.
- `project_candidate_graph_for_promote` drops empty-evidence standing/party context anchors and reconciles retained beat node IDs against surviving nodes.
- `resolve_promotable_ingest_run` / `load_typed_candidate_graph` accept the resulting candidate graph.
- Default live `graph_preview_runner` constructs `OpenAICategoryGraphPassClient()` without fat-tip-only kwargs.

## §4 Files in scope (allowlist)

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Modify | `src/graph_memory/extraction/category_candidate_graph_extractor.py` | Typed SemanticState, EvidenceRef stamp, promote projection (drop empty-evidence anchors; reconcile beat node IDs) |
| Modify | `src/graph_memory/extraction/staged_edge_extraction.py` | Typed SemanticState on staged edges |
| Modify | `apps/live_control_server/services/promotable_ingest_run.py` | Fail-closed typed candidate load at resolve |
| Modify | `evals/graph_memory_layer/graph_preview_runner.py` | Live runner uses constructor available on this branch (no unused `reasoning_effort`) |
| Modify | `tests/test_category_extractor_default_semantic_state.py` | SemanticState contract |
| Modify | `tests/test_category_extractor_promote_evidence_refs.py` | EvidenceRef + promote projection + owning-path party→resolve |
| Modify | `tests/test_graph_memory_category_graph_preview_runner.py` | Runner regression |
| Modify | `tests/test_graph_memory_encounter_job_pass.py` | Encounter pass SemanticState |
| Modify | `tests/test_graph_memory_staged_edge_extraction.py` | Staged edge SemanticState |
| Modify | `tests/test_promotable_ingest_run.py` | Resolve fail-closed on bad IR |
| Modify | `tests/test_graph_memory_session_graph_context.py` | Party registry injects at consolidate; promote IR drops empty anchors |
| Create | `Docs/Plans/HANDOFF-pr011a3-promote-ir-slice.md` | This handoff |
| Modify | `Docs/Reports/PR011A3-SESSION25-DURABLE-MEMORY-DOGFOOD.md` | Honest PARTIAL / NOT_READY authority |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Split ledger pointer |

**Bounded discovery exception:** Not applicable — paths enumerated above.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| Standing_context + multi-slice confirm / atomic bundle | Successor #375 |
| Existing-object support-only observation rewrite | Successor #370 |
| C1 Model B migration, Plan lens, hover/cards, Author Node | Product slices outside promote-IR |
| Fat tip `eb509dae` / PR #367 as-merge | Preserved read-only reference only |
| `OpenAICategoryGraphPassClient(reasoning_effort=…)` fat-tip contract | Unrelated caller-facing scope |

Empty-evidence party/context anchors survive sanitize via `context_anchor` but are **dropped** at promote projection so this slice does not depend on standing-context partition. Party standing promotion is a successor capability.

## §6 Implementation contract

```text
Input:
  Category pass outputs + campaign party registry (consolidate) + span index

Output:
  Promote-eligible CandidateGraphPreview dict (session-evidenced nodes/edges/beats only)

Invariant:
  Typed validation / load_typed_candidate_graph succeeds without standing-context partition

Failure behavior:
  Empty-evidence standing anchors → dropped (not validation failure)
  Beat refs to dropped nodes → stripped from involved/unresolved lists
  Alias / non-typed SemanticState at resolve → run_not_promotable

Replay / idempotency:
  same candidate graph → same typed load
  retry after rewrite of out/ candidates → resolve uses disk artifact as-is
```

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command or manual scenario | Expected evidence |
|---|---|---|---|
| Typed SemanticState + EvidenceRef at assemble | category extractor unit | pytest promote-evidence module | green |
| Empty-evidence party anchors do not block typed load; beats reconciled | projector + validate | pytest party-anchor + beat cases | `report.issues == ()` |
| Real party registry → pipeline → persisted run → resolve | `resolve_promotable_ingest_run` | owning-path test in promote-evidence module | resolve returns run; typed load ok |
| Live runner constructs without reasoning_effort | graph_preview_runner | runner tests + import smoke | no TypeError; field absent |
| Focused allowlist integrity | git | `git diff --name-only 37c0a79d...HEAD` | only §4 paths |

```bash
python -m pytest \
  tests/test_category_extractor_default_semantic_state.py \
  tests/test_category_extractor_promote_evidence_refs.py \
  tests/test_graph_memory_category_graph_preview_runner.py \
  tests/test_graph_memory_encounter_job_pass.py \
  tests/test_graph_memory_staged_edge_extraction.py \
  tests/test_promotable_ingest_run.py \
  tests/test_graph_memory_session_graph_context.py \
  -q

git diff --check
git diff --stat 37c0a79d...HEAD -- \
  src/graph_memory/extraction/category_candidate_graph_extractor.py \
  src/graph_memory/extraction/staged_edge_extraction.py \
  apps/live_control_server/services/promotable_ingest_run.py \
  evals/graph_memory_layer/graph_preview_runner.py \
  tests/test_category_extractor_default_semantic_state.py \
  tests/test_category_extractor_promote_evidence_refs.py \
  tests/test_graph_memory_category_graph_preview_runner.py \
  tests/test_graph_memory_encounter_job_pass.py \
  tests/test_graph_memory_staged_edge_extraction.py \
  tests/test_promotable_ingest_run.py \
  tests/test_graph_memory_session_graph_context.py \
  Docs/Plans/HANDOFF-pr011a3-promote-ir-slice.md \
  Docs/Reports/PR011A3-SESSION25-DURABLE-MEMORY-DOGFOOD.md \
  Docs/Plans/PR-TRACKER-campaign-supergraph.md
git diff --name-only 37c0a79d...HEAD
```

### Minimal live proof

```text
Existing surface used: Session 24 waived dogfood (report)
Smallest scenario: prepare/confirm recorded; exact committed revision reload still blocked
Expected observation: PARTIAL / NOT_READY_FOR_CANONICAL_RECAP_BACKFILL
Evidence captured: Docs/Reports/PR011A3-SESSION25-DURABLE-MEMORY-DOGFOOD.md
```

## Dependencies

- Requires: PR011A2 / #366 on `main` (`37c0a79d`)
- Unblocks: #370, #375 (and downstream promote slices)

## Dogfood authority

[`Docs/Reports/PR011A3-SESSION25-DURABLE-MEMORY-DOGFOOD.md`](../Reports/PR011A3-SESSION25-DURABLE-MEMORY-DOGFOOD.md) — Session 25 waived → Session 24; terminal NOT_READY.
