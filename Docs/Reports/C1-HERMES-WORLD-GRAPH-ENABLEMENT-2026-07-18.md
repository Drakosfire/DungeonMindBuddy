# Report — Campaign 1 on Hermes World Graph (2026-07-18)

## Verdict

`longmont-c1` is a first-class campaign scope on `worldId=eldyrwild`. Plan Hermes can request C1 world-graph context; projection filters by assertion/object `campaign_scope` rather than the legacy store campaign label.

## What changed

1. **Projection (Model B):** `_assert_campaign_scope` no longer 409s on `store.campaign_id != request.campaign_id`. Nodes/edges/attributes whose scope is a non-null string other than the request campaign are excluded. Node scope prefers the **active node assertion** over stale `node.state.campaign_scope`.
2. **Plan UI:** `WORLD_ID_BY_CAMPAIGN` maps `longmont-c1` → `eldyrwild`.
3. **Additive bundle:** `graph_data/approved_contribution_bundles/eldyrwild-longmont-c1-s1-s3-v1/`
   - Supersedes C2 QC roster so six `pc:*` nodes are world-owned (`campaign_scope=null`)
   - Adds `party:heroes-party` + curated C1S1–C1S3 events/locations
4. **Apply path:** `scripts/apply_eldyrwild_c1_additive_bundle.py` + `apps/live_control_server/services/c1_world_graph_additive_apply.py`

## Operator apply (existing C2 head)

```bash
python scripts/apply_eldyrwild_c1_additive_bundle.py status
python scripts/apply_eldyrwild_c1_additive_bundle.py apply --actor gm
```

Requires the C2 bootstrap head already present.

## Falsification

- `tests/test_c1_world_graph_additive_apply.py` — C1 vs C2 projection split; agent context `ready` for C1S3
- `tests/test_graph_kernel_world_projection.py` — foreign campaign filters rather than 409
- `apps/live-control-ui/.../planGraphContextRequest.test.ts` — C1 maps to eldyrwild

## Non-goals (still true)

URL `?campaign=` does not override Plan’s live-packet campaign. Full C1 corpus parity is not claimed — dogfood bed is curated S1–S3 density.
