# HANDOFF — DOGFOOD-CONTINUITY: historical recap World projection v1

**Status:** READY FOR REVIEW
**Base revision:** `65c1ddaf069de7446fd78e99526136d825b55bfd` (PR #688 head)
**Branch:** `agent/dogfood-continuity-historical-recap-projection-v1`
**Predecessor:** PR #688 historical exact-run source inspection spike; intentionally not merged or modified

## Capability

One exact `validated` / `prepared` recap run can be rendered as a read-only,
graph-aware document whose Markdown is owned by Buddy APP-STATE and whose pills
resolve to the current governed DungeonMind World snapshot.

Inspection remains separate from promotion. This slice does not widen
`EXACT_REVIEWABLE_STATUSES`, alter prepare/confirm behavior, re-ingest old
recaps, or write the World Graph.

## Frozen decisions

- `ingest.run` remains lifecycle and exact-run identity authority.
- `source.artifact` stores source identity/scope; `source.revision` stores the
  exact immutable UTF-8 Markdown and digest.
- Historical projection reads APP-STATE source content only. Filesystem source
  bytes are usable only through the explicit one-time adoption boundary.
- Historical pills represent current DungeonMind World identities, not
  stranded historical candidate nodes.
- A missing durable source, missing World binding, or unavailable DungeonMind
  projection fails closed. No pill-less fallback is returned by the projection
  route.

## §4 write lease

### Backend

- `src/application_state/migrations/versions/20260906_0006_source_content.py`
- `src/application_state/source/`
- `apps/live_control_server/models/historical_recap_projection.py`
- `apps/live_control_server/services/historical_recap_world_projection.py`
- `apps/live_control_server/services/historical_recap_source_adoption.py`
- `apps/live_control_server/services/graph_run_registry.py`
- `apps/live_control_server/routes/graph_preview.py`

### Frontend

- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`

### Tests

- `tests/application_state/test_source_content_postgres.py`
- `tests/application_state/test_ingest_run_postgres.py`
- `tests/application_state/test_play_runtime_demolition.py`
- `tests/test_historical_recap_source_adoption.py`
- `tests/test_historical_recap_world_projection.py`
- `tests/test_graph_preview_routes.py`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx`

### Explicitly out of scope

- PR #688’s branch, worktree, commits, or review state
- `src/prompts/*.py`
- historical candidate/gold graph storage and promotion paths
- DungeonMind graph writes or Buddy graph publication
- Threat/statblock redesign, Agent context, DFC-NAV1, Build/Play recovery, and
  VPC deployment
- corpus/eval gold fixtures and raw LLM artifacts

## Verification

```text
uv run pytest -q \
  tests/application_state/test_source_content_postgres.py \
  tests/test_historical_recap_source_adoption.py \
  tests/test_historical_recap_world_projection.py

pnpm --dir apps/live-control-ui exec vitest run \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx
```

The focused backend tests prove exact artifact/digest binding, explicit
filesystem adoption, current-World projection, and fail-closed source/World
boundaries. The frontend test proves the historical workbench consumes the
graph-aware projection rather than the source-only inspection payload.

## Current migration/adoption operation

After applying APP-STATE migrations, an operator adopts one exact historical
run with:

```text
uv run python -m apps.live_control_server.services.historical_recap_source_adoption \
  --run-id <exact-run-id> \
  --world-id <current-world-id>
```

The command verifies the recorded URI and digest, writes no run lifecycle
state, and never becomes a runtime filesystem fallback.
