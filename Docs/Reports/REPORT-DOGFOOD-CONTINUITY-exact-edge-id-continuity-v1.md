# REPORT — DOGFOOD-CONTINUITY exact-edge-id continuity v1

**Status:** CODE + reverse-endpoint fix after Review Cycle 1 HOLD; dogfood PASS retained on prior combined head  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-edge-id-continuity-v1.md`  
**Branch:** `dogfood-continuity/exact-edge-id-continuity-v1`  
**PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/726  
**Design authority base:** `68577114b3c8ec7e06bc0b0a8d382143fdc570ec`

## Claim

```text
EXACT-EDGE-ID CONTINUITY: implemented
  + reverse-endpoint admitted mapping normalized before parent compare
  + prior C1S6 relationship_id_collision dogfood-cleared on combined head
```

Mutation context carries sealed parent relationships. Identity gating
classifies candidate edges by the **derived durable write relationship id**
(`value.edge_id` / DM `relationship_id`), not extractor-local
`CandidateEdge.edge_id`:

- compatible published endpoints + admitted predicate → confirm existing
- occupied incompatibly → `blocked_collision` reject
- free id → `created_new` as before
- admitted `reverse_endpoints` (e.g. `belongs_to` → `dnd5e:owns`) normalize
  candidate orientation before compare

## Verification (zero-cost)

```text
uv run pytest tests/test_exact_edge_id_continuity.py -q
10 passed
```

## Review Cycle 1

HOLD on `289ae015…` (`5217509706`) for reverse-endpoint misclassification and
steward handoff-on-main gap. Addressed in this head.

## Dogfood proof (combined pristine execute; pre-dates reverse-endpoint fix)

Rerun head: `3217d1dd25058766ee0c61f79d08a8d1558f0b16`  
Artifact: `out/graph_memory/current_corpus_admission_acceptance_v1/execute-2026-09-15T234947Z-77482c97`  
44/44 sealed; `structural_acceptance=PASS`; C1S6 collision class cleared.

## Remains false

```text
SEMANTIC MODEL SELECTION = HOLD
no fuzzy edge matching / predicate remapping beyond admitted write mapping
```
