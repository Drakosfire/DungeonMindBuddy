# REPORT — DOGFOOD-CONTINUITY exact-edge-id continuity v1

**Status:** CODE + dogfood proof that prior relationship_id_collision STOP is cleared  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-edge-id-continuity-v1.md`  
**Branch:** `dogfood-continuity/exact-edge-id-continuity-v1`  
**PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/726  
**Implementation head:** `1138df4ff75a52b9063e55776f0b88f7a4d77e7d`  
**Design authority base:** `68577114b3c8ec7e06bc0b0a8d382143fdc570ec`

## Claim

```text
EXACT-EDGE-ID CONTINUITY: implemented + dogfood-cleared prior STOP
```

Mutation context carries sealed parent relationships. Identity gating
classifies candidate edges by exact durable `relationship_id`:

- compatible endpoints + admitted predicate → confirm existing (omit CREATE)
- occupied incompatibly → `blocked_collision` reject
- free id → `created_new` as before

## Verification (zero-cost)

```text
uv run pytest tests/test_exact_edge_id_continuity.py -q
7 passed
```

```text
uv run ruff check \
  apps/live_control_server/models/world_graph_mutation_context.py \
  apps/live_control_server/integrations/dungeonmind/world_graph_writes.py \
  src/graph_memory/extract_identity_gate.py \
  tests/test_exact_edge_id_continuity.py
All checks passed!
```

## Dogfood proof (fresh pristine acceptance `--execute`)

Rerun head (acceptance harness + #723–#726): `3217d1dd25058766ee0c61f79d08a8d1558f0b16`  
Artifact: `out/graph_memory/current_corpus_admission_acceptance_v1/execute-2026-09-15T234947Z-77482c97`

| Observation | Evidence |
|---|---|
| Prior C1S6 `relationship_id_collision` cleared | `longmont-c1/session-6` sealed (`rev:b92b1da25bff8458ae323067ba00fba3`) |
| Full frozen corpus | 44/44 sessions sealed; `structural_acceptance=PASS` |
| Terminal head | `rev:ad49d3e180b270d551e2d0afe7dd987a` |
| No STOP | `stop: null`; model_calls=44 |

## Remains false

```text
SEMANTIC MODEL SELECTION = HOLD
no fuzzy edge matching / predicate remapping / ID regeneration
```
