# REPORT — DOGFOOD-CONTINUITY exact-edge-id continuity v1

**Status:** CODE complete — dogfood rerun pending  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-edge-id-continuity-v1.md`  
**Branch:** `dogfood-continuity/exact-edge-id-continuity-v1`

## Claim

```text
EXACT-EDGE-ID CONTINUITY: implemented
```

Mutation context now carries sealed parent relationships. Identity gating
classifies candidate edges by exact durable `relationship_id`:

- compatible endpoints + admitted predicate → confirm existing (omit CREATE)
- occupied incompatibly → `blocked_collision` reject
- free id → `created_new` as before

## Verification

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

## Predecessor handback (not yet durable acceptance REPORT)

C1S6 stochastic STOP: `relationship_id_collision` on
`edge:node:torbin:located_in:loc:hempholm`. C1S1–S8 best depth remains
observational until a pristine full `--execute` clears the frozen corpus.

## Remains false

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = HOLD until fresh pristine --execute PASS
no fuzzy edge matching / predicate remapping / ID regeneration
```
