# HANDOFF — DOGFOOD-CONTINUITY: historical recap World projection v1

**Status:** READY FOR REVIEW (PR #689)
**Base revision:** `a692dbe2bd3dd53a385891ae4ed4c83668bd58ec` (`main` after DFC-3 / PR #687)
**Branch:** `agent/dogfood-continuity-historical-recap-projection-v1`
**PR:** #689 — `DOGFOOD-CONTINUITY: project durable historical recaps`
**Predecessor:** PR #688 historical exact-run source inspection spike (`65c1ddaf069de7446fd78e99526136d825b55bfd`); **unmerged and paused** — branch/worktree/review state untouched

## Cumulative scope

PR #689 **cumulatively incorporates and supersedes** the unmerged/paused PR #688 implementation on this branch. The #688 branch, worktree, commits, and review state remain **unmerged and untouched**; this successor PR is the single review surface for the combined capability.

Do **not** mark PR #689 or Stage 1 / STOP 1 complete in this handoff. STOP 1 remains closed until post-merge assembled human dogfood.

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

Cumulative PR #689 paths (31 files; one path per bullet — matches `git diff --name-only origin/main...HEAD`):

- `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-c1-c2-demo-readiness-survey-v1.md`
- `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-historical-recap-projection-v1.md`
- `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
- `Docs/Roadmaps/ROADMAP-con-ready.md`
- `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`
- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.test.ts`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.ts`
- `apps/live_control_server/models/historical_recap_inspection.py`
- `apps/live_control_server/models/historical_recap_projection.py`
- `apps/live_control_server/routes/graph_preview.py`
- `apps/live_control_server/services/graph_run_registry.py`
- `apps/live_control_server/services/historical_recap_source_adoption.py`
- `apps/live_control_server/services/historical_recap_world_projection.py`
- `src/application_state/migrations/versions/20260906_0006_source_content.py`
- `src/application_state/source/__init__.py`
- `src/application_state/source/repository.py`
- `src/application_state/source/service.py`
- `src/application_state/source/types.py`
- `tests/application_state/test_ingest_run_postgres.py`
- `tests/application_state/test_play_runtime_demolition.py`
- `tests/application_state/test_source_content_postgres.py`
- `tests/test_graph_preview_routes.py`
- `tests/test_graph_run_registry.py`
- `tests/test_historical_recap_source_adoption.py`
- `tests/test_historical_recap_world_projection.py`
- `tests/test_live_recap_ingest_graph_preview_api.py`

### Explicitly out of scope

- PR #688's branch, worktree, commits, or review state (paused/unmerged; do not modify)
- `src/prompts/*.py`
- historical candidate/gold graph storage and promotion paths
- DungeonMind graph writes or Buddy graph publication
- Threat/statblock redesign, Agent context, DFC-NAV1, Build/Play recovery, and
  VPC deployment
- corpus/eval gold fixtures and raw LLM artifacts

## Runtime/state ownership

- Tests use disposable APP-STATE databases and temporary historical roots; they
  never mutate an operator database or the paused #688 worktree.
- Runtime historical inspection reads APP-STATE source revisions and the
  governed DungeonMind World projection only; it does not write ExtractionRun,
  source, World, or promotion state.
- The explicit adoption command is the sole bounded source-authority write in
  this slice. It requires an exact run/component digest and does not mutate
  the run lifecycle, historical roots, or World Graph.
- Assembled dogfood uses the configured APP-STATE and API/UI processes. Any
  real witness adoption is recorded as an explicit operator action, separate
  from runtime reads.

## Verification

```text
uv run pytest -q \
  tests/application_state/test_source_content_postgres.py \
  tests/test_historical_recap_source_adoption.py \
  tests/test_historical_recap_world_projection.py \
  tests/test_graph_run_registry.py \
  tests/test_live_recap_ingest_graph_preview_api.py

pnpm --dir apps/live-control-ui exec vitest run \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx

pnpm --dir apps/live-control-ui exec tsc -b --force
```

The focused backend tests prove exact artifact/digest binding, explicit
filesystem adoption, current-World projection, and fail-closed source/World
boundaries. The frontend test proves:

- catalog-selected `validated`/`prepared` runs consume the graph-aware historical projection (not the promotion review package);
- canonical graph pills (`[Label](dmb-node:id)`) render and open the exact `GraphObjectProjectionCard`;
- exact-handoff (`extractionRunId=...`) loads for historical runs through historical projection only — `getExactRunReviewPackage` is not called and no promotion review error is shown.

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

## Assembled dogfood witness (2026-09-06)

The exact C2 Session 25 adoption was completed against Buddy APP-STATE:

- `run_id`: `graph-ingest:longmont-c2:session-25:20260808T005650Z`
- `run_status`: `validated`
- `source_artifact_id`: `artifact:recap:longmont-c2:session-25:fd38b5915b32`
- `source_revision_id`: `8ed1e034-23c6-4295-b2ff-05d5cdd643a9`
- `source_sha256`: `sha256:fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d`
- current World binding: `eldyrwild`

The successor `/ingest` UI loaded with that exact `extractionRunId`. The
historical projection route reached the governed DungeonMind adapter but
returned `503 authority_unavailable`; the direct diagnostic was that the local
PostgreSQL server has no `dungeonmind_cutover_live` database. The UI therefore
rendered the honest World-authority-unavailable boundary, with no
pill-capable projection, object-card click, or World snapshot identity to
record. This witness is blocked at current-World authority availability, not
at source adoption or exact-run resolution.
