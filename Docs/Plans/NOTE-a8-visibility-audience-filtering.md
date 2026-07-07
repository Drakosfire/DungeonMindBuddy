# A8 implementation note — visibility-aware audience filtering

Date: 2026-07-07  
Branch: `codex/graph-authoring-visibility-audience-filtering`

## What landed

- `apps/live_control_server/services/graph_authoring_visibility.py`
  - `GraphAudience` (`gm`, `table`, `player`, `character`)
  - `visibility_policy_visible_to_audience`
  - `assertion_visible_to_audience`
  - `filter_authored_assertions_for_audience`
  - `filter_authored_overlay_for_audience`
  - Projection extras helpers: `projection_node_visible_to_audience`, `projection_adjacency_visible_to_audience`
- Optional `audience` parameter on `apply_authored_overlay_to_graph_review_projection` (default `None` = current GM review behavior)
- `tests/test_graph_authoring_visibility.py` (31 cases)

## What this does not claim

- A7 dogfood was not a clean pass; this PR does not polish the authoring UX loop.
- No player UI, gold/eval export, identity merge, or prepare/commit semantic changes.
- Historical extracted graph data is out of scope; filtering targets authored overlay assertions first.

## Semantics (conservative defaults)

- Missing visibility policy → GM-private
- GM sees all visibility states
- Table/player see `table_known` and `player_visible`
- `hidden_until_revealed` visible to non-GM only when `reveal_state == "revealed"`
- `character_specific` requires matching `player_id` or `character_id` lists

## Verification

```bash
uv run pytest tests/test_graph_authoring_visibility.py \
  tests/test_graph_authoring_overlay_models.py \
  tests/test_graph_authoring_overlay_projection.py \
  tests/test_graph_object_authoring_prepare.py \
  tests/test_graph_object_authoring_commit.py \
  tests/test_graph_existing_object_resolver_cross_scope.py
```

Frontend unchanged for A8.
