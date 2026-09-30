# HANDOFF — DEMO: World PlayRun V2 backend

**Status:** ACTIVE — PRIME explicitly activated this serial Phase B lease
**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Base:** Buddy `main@6c6a8ab48d568c2827fca4ce019d701beb473166`, merge of Phase A PR #808
**Predecessor:** Phase A code head `cbab140772c37e4cc71401ffe174e06887943d4a`, final evidence head `ed09199b56206a0d3b7a6262380a1352ea567849`, merged as `6c6a8ab48d568c2827fca4ce019d701beb473166`
**Implementation branch:** `codex/demo-world-playruns-v2`
**Topology:** Serial, one Phase B implementation PR; Phase C is blocked until this PR merges and its owning witness passes
**PR title:** `DEMO: add World-owned PlayRun V2 backend`

PRIME explicitly activated this bounded Phase B lane after reviewing the
storage-reader audit and current open PR paths. The branch starts from the
exact authorized main commit above. The 16 paths listed below are an exclusive
write lease. If implementation needs another path, stop and return to PRIME
before editing it.

## Capability and owner invariant

Add a separate, explicitly versioned World PlayRun API family so a committed
World-owned Runbook can start, list, open, progress, rebase, and read/seal its
Run reference manifest. The Run's World is always resolved from its exact
pinned Runbook `WorkRevision.world_id`; the request's `world_id` is only an
expectation to check. The stored `play.run.world_id` is an indexed consistency
hint and never an authorization source. Responses return the World resolved
from the exact pin.

The V2 record/list discriminators are
`dmb_world_play_run_record_v2` and `dmb_world_play_runs_list_v2`. A V2 Run
record requires `world_id` and contains no Campaign identity. Preserve the Run
ID, exact Runbook artifact/revision/revision ID/SHA, independent
`run_revision`, timestamps, and progress. The manifest retains its own existing
schema discriminator; the World route version does not change the manifest's
payload grammar.

Keep campaign PlayRun V1 unchanged: same routes and response schemas, required
nonblank `campaign_id`, and campaign create/list/detail/progress/rebase,
manifest, and active-selection behavior. V1 list and every V1 by-ID operation
must exclude or reject World Runs before returning or mutating them. V1's
`play-active-run` setter remains campaign-only. V2 does not read or write the
global active-Run pointer; Play UI selection/resume is a later Phase C slice.

## Storage strategy and migration

Migration `20260930_0009_world_play_run_v2.py` adds nullable `world_id`, makes
`campaign_id` nullable, and adds a check requiring exactly one owner, plus an
index for World list queries. Existing rows keep their current `campaign_id`
and receive `world_id = NULL`; do not backfill ownership from string equality,
including `campaign_id == world_id`. No tagged locator or synthetic Campaign
is allowed.

Every World V2 operation resolves the exact pinned Runbook revision and checks
that the request, WorkObject, WorkRevision, and stored `world_id` hint agree.
The owner returned to the client comes from the resolved revision. A mismatch
fails closed before any dependent mutation. Campaign V1 list queries are
explicitly restricted to campaign-owned rows even when their campaign filter
is omitted. Unfiltered application-state Run inventory keeps its existing
campaign-only meaning for product continuity.

The existing `play.run_manifest` remains keyed by Run ID and retains its
artifact/revision/revision-ID/SHA binding; no separate World manifest store is
added. The global `play.active_run` row remains unchanged. Migration downgrade
must refuse while any World-owned Run rows remain, rather than losing or
relabeling them.

## ACTIVE exclusive write lease

Only these paths may be edited in this lane:

~~~text
src/application_state/migrations/versions/20260930_0009_world_play_run_v2.py
src/application_state/content/playable_admission.py
src/application_state/play/types.py
src/application_state/play/repository.py
src/application_state/play/service.py
apps/live_control_server/routes/play_runs.py
apps/live_control_server/services/play_run_registry.py
apps/live_control_server/services/play_run_rebase.py
apps/live_control_server/services/play_run_reference_manifest.py
tests/application_state/test_play_runtime_world_runs_migration.py
tests/application_state/test_play_runtime_world_runs_postgres.py
tests/test_world_play_runs_v2.py
tests/product_continuity/test_inventory_postgres.py
Docs/Plans/HANDOFF-DEMO-world-play-run-v2-backend.md
Docs/Plans/HANDOFF-DEMO-world-owned-play-runs.md
Docs/Roadmaps/ROADMAP-demo.md
~~~

The new V2 endpoints live in the already-registered
`apps/live_control_server/routes/play_runs.py` router. Do not edit
`apps/live_control_server/main.py`: open Rules PRs #763 and #765 touch that
shared router registry. The refreshed open Buddy PR inventory is #798, #781,
#763–#765, and #760–#761; none overlaps this lease. #781 is isolated to
semantic-action UI/proof. No other active DEMO implementation lane overlaps
these storage or route paths.

## Required API behavior

Use the accepted route family:

~~~text
GET  /api/live/world-play-runs/v2?world_id=W
GET  /api/live/world-play-runs/v2/{run_id}?world_id=W
PUT  /api/live/world-play-runs/v2/{run_id}?world_id=W
PUT  /api/live/world-play-runs/v2/{run_id}/progress?world_id=W
PUT  /api/live/world-play-runs/v2/{run_id}/rebase?world_id=W
GET  /api/live/world-play-runs/v2/{run_id}/reference-manifest?world_id=W
PUT  /api/live/world-play-runs/v2/{run_id}/reference-manifest?world_id=W
~~~

Create/replay must bind only a current, clean, exact committed Runbook revision
whose WorkObject and WorkRevision are explicitly owned by the requested World.
Read/list/progress/rebase/manifest operations verify the Run's current exact
pin and World before exposing data or changing state. Rebase may move only to a
strictly newer exact revision owned by the same World, with matching digest and
admitted manifest/progress. Preserve CAS behavior for `run_revision`.

V1 must remain campaign-only on all paths: unfiltered list, create/replay,
detail/readiness, progress, rebase, manifest GET/seal, and active-Run setter.
The legacy Agent Play context remains V1 and campaign-bound; generic Agent Run
resolution and Play Agent conversation remain later work. World V2 does not
set the global active pointer.

## Owning-boundary witness

The tests must exercise the PostgreSQL-backed application-state and existing
campaign routes. Use a fresh PRIME-designated PostgreSQL 16 tmpfs target; the
test fixture creates and drops uniquely named databases. Do not use persistent
demo targets `54330`/`54331`, start a product server/provider, or load a corpus.
PRIME designated the fresh disposable target for this lane; the prior Phase A
container on port `55429` was removed.

The witness must prove:

- Upgrade from the pre-Phase-B schema preserves campaign rows with
  `world_id = NULL`, including a campaign string equal to a World ID. No
  historical ownership is inferred.
- Create/replay a World A Run from its exact World-owned Runbook revision;
  persist and return the exact revision/SHA and `world_id = A`; V2 records have
  no `campaign_id`. Replay with the same identity is idempotent.
- World A list/detail/progress/manifest operations succeed only after resolving
  and matching the exact pin. World B, a mismatched stored hint, wrong SHA,
  missing revision, or corrupted pin fails closed before mutation. A same-World
  newer exact rebase advances the binding and `run_revision`; stale CAS and
  cross-World rebase do not mutate the Run or manifest.
- Campaign V1 create/list/get/progress/rebase/manifest and active selection
  remain unchanged. Unfiltered V1 list and product-continuity inventory exclude
  World rows; V1 by-ID operations and active-set reject them. A World-owned
  Runbook still cannot start through V1.
- Migration downgrade refuses while World rows remain. Existing active-pointer
  storage and V1 API shape are unchanged.

Focused PostgreSQL suite (set `DMB_APPLICATION_STATE_TEST_DATABASE_URL` to the
PRIME-designated isolated admin target):

~~~sh
UV_CACHE_DIR=/tmp/dmb-uv-cache uv run pytest \
  tests/application_state/test_play_runtime_world_runs_migration.py \
  tests/application_state/test_play_runtime_world_runs_postgres.py \
  tests/application_state/test_play_runtime_rebase_transaction.py \
  tests/application_state/test_play_active_run_postgres.py \
  tests/test_world_play_runs_v2.py \
  tests/test_live_play_runs.py \
  tests/test_live_play_run_rebase.py \
  tests/test_live_play_run_progress.py \
  tests/test_live_play_run_reference_manifest.py \
  tests/test_live_play_active_run.py \
  tests/product_continuity/test_inventory_postgres.py
~~~

Also run scoped Ruff on changed Python paths, Python compilation, cumulative
`git diff --check`, and Alembic offline upgrade/downgrade rendering. The
migration witness must verify the single Alembic head and guarded downgrade.
PRIME designated disposable PostgreSQL 16 tmpfs container
`prime-demo-playrun-v2-pg-20260930` for this witness. The focused suite above
passed **75 tests** on 2026-09-30 against that target. The `uv run` invocation
shown above could not resolve dependencies from PyPI in this environment, so
the same test paths were executed as `rtk pytest -p no:cacheprovider` with the
existing project environment and without installing packages. Scoped Ruff
passed across all 13 changed Python files; in-memory Python compilation passed;
offline Alembic upgrade and guarded-downgrade rendering passed with one
migration head; and an OpenAPI check confirmed all seven World V2 operations
and the required `world_id` list parameter. Existing Pydantic `schema`-shadow
warnings appeared during app construction. The earlier Phase A 53/53 result
remains a separate predecessor witness and does not substitute for these Phase
B tests.

The implementation/test changes are committed at
`40a8bbc9` (`DEMO: add World-owned PlayRun V2 backend`) on the authorized
branch. This passing witness does not mean Phase B is merged; Phase C remains
blocked until the Phase B PR merges and its owning witness is accepted.

## Collision, predecessor, and handback

Phase A #808 merged as `6c6a8ab48d568c2827fca4ce019d701beb473166` after the
final `ed09199b56206a0d3b7a6262380a1352ea567849` head passed 53/53 owning-
boundary tests on an isolated PostgreSQL 16 tmpfs target. This establishes
World-owned Runbook revision identity only; it did not create a Run or change
PlayRun storage. The Phase B PR updates the roadmap and this design handoff to
record that predecessor truthfully.

Phase B is one serial PR from this exact base. Inspect the cumulative
base-to-head diff and the required owner checks before requesting PRIME review.
Do not start Phase C until Phase B is merged and its owning witness passes. The
later Phase C handoff migrates Play/context consumers and proves managed-World
Run create/list/select/reload/resume/progress/rebase; generic Agent Run
resolution remains a separate successor. This backend PR does not close J1–J6,
the rejected visual acceptance gate, J3 retrieval, or operator acceptance.
