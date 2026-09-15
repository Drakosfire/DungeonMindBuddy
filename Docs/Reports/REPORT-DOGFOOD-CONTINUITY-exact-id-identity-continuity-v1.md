# REPORT — DOGFOOD-CONTINUITY exact-id identity continuity v1

**Status:** CODE complete — dogfood rerun pending  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-id-identity-continuity-v1.md`  
**Branch:** `dogfood-continuity/exact-id-identity-continuity-v1`

## Claim

```text
EXACT-ID IDENTITY CONTINUITY: implemented
```

`resolve_identity_against_context` now confirms same-kind parent objects when
`proposed_node_id` / `candidate_id` already names them, before label matching or
cross-kind alias blocking.

## Verification

```text
uv run pytest tests/test_exact_id_identity_continuity.py \
  tests/test_pc_identity_normalization.py \
  tests/test_cutover_native_governed_write.py -q
21 passed
```

Live acceptance DB probe after session-1:
`loc:rivers-edge-pub` / `loc:stone-bridge` → `resolved_existing`.

## Remains false

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = HOLD until fresh pristine --execute PASS
no weakening of true cross-kind collisions without durable id
```
