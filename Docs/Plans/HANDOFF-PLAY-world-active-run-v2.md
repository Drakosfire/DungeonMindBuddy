---
pr_body_template: |
  ## Handoff pointer
  - Workstream: PLAY / World active Run selection
  - Flow: PLAY
  - Handoff: `Docs/Plans/HANDOFF-PLAY-world-active-run-v2.md`
  - Base: `b41fc3898729acfe3518bceb0c03ab93f149e4f0`
  - Branch: `codex/play-world-active-run-v2`

  ## Verification pointer
  - Accepted producer head: `63af78136448b6a5aa44e7230bfce784af049dc7`.
  - Assembled PR head: `f5f47acd836ce2cd658343e707dd320de1d26c9a`.
  - PR #952 merge: `b234cf407da7ef7bd6fc58e541106066e90e5229`.
  - Final producer and consumer evidence are recorded in §§4.1 and 5.
---

# HANDOFF — World-scoped active Play Run V2

**Status:** MERGED / HISTORICAL — PR #952 merged at `b234cf407da7ef7bd6fc58e541106066e90e5229`; production QC remains open under ROOT.
**Owner:** APP-STATE / Buddy Play Runtime.
**Implementation base:** `b41fc3898729acfe3518bceb0c03ab93f149e4f0` (after merged #951).
**Accepted producer head:** `63af78136448b6a5aa44e7230bfce784af049dc7`.
**Assembled PR head:** `f5f47acd836ce2cd658343e707dd320de1d26c9a`.
**Merge commit:** `b234cf407da7ef7bd6fc58e541106066e90e5229` (PR #952).
**Additional main predecessor:** PR #953 merged at `9952737a0a31937f43e0dd52818671374af5b8a4`.
**Topology:** serial; one combined producer+consumer capability PR. The consumer was assembled only after independent acceptance of the producer head.

## 1. Mission and invariant

Allow a World Play surface to select and resume its exact World-owned Play Run through the existing singleton `play.active_run` pointer. A pointer to a campaign Run or a Run owned by another World projects as empty for the requested World. A failed selection never overwrites the existing pointer. Reads do not heal or mutate state.

Keep the campaign V1 API and owner fence. V1 reads project an empty state while the shared pointer references a World Run; V1 writes continue to reject World Runs. Do not add a table, migration, fallback selection, or implicit Run creation.

## 2. API contract

Add static routes before `/world-play-runs/v2/{run_id}`:

```text
GET /api/live/world-play-runs/v2/active?world_id=<canonical-world-id>
PUT /api/live/world-play-runs/v2/active?world_id=<canonical-world-id>
Content-Type: application/json
{"run_id":"<canonical-uuid>"}
```

The strict response shape is:

```json
{
  "schema_version": "dmb_world_play_active_run_v2",
  "world_id": "<world-id>",
  "run_id": null,
  "selected_at": null
}
```

For a selection, both `run_id` and `selected_at` are present. GET returns the null pair when the singleton pointer is empty, points to a campaign Run, or points to a different World. If it points to a Run in the requested World, validate exact owner, pinned revision and sealed manifest before returning it. Integrity failures remain errors. PUT validates the exact World owner and readable aggregate before changing the singleton pointer; selecting the same Run is idempotent and preserves `selected_at`.

## 3. Storage and compatibility

Reuse the current single-row `play.active_run` store. Derive World ownership from the exact `play.run` row and pinned committed revision. Do not alter Run progress, source pins, manifest, active-pointer schema, or migrations. V1 campaign selection remains available and campaign-owned Run data keeps its existing response shape.

## 4. Exclusive producer write lease

The completed implementation lane modified only:

1. `src/application_state/play/service.py`
2. `tests/application_state/test_play_active_run_postgres.py`
3. `apps/live_control_server/services/play_active_run.py`
4. `apps/live_control_server/routes/play_runs.py`
5. `tests/test_world_play_runs_v2.py`
6. `Docs/Plans/HANDOFF-PLAY-world-active-run-v2.md`

No migration or other path was changed. This implementation write lease closed when PR #952 merged.

## 4.1 Accepted consumer lease and assembly

After independent acceptance of producer head `63af78136448b6a5aa44e7230bfce784af049dc7` (based on `b41fc3898729acfe3518bceb0c03ab93f149e4f0`), the bounded consumer was assembled onto the same PR branch. Its exclusive five-path lease was:

1. `apps/live-control-ui/src/api/types.ts`
2. `apps/live-control-ui/src/api/liveApi.ts`
3. `apps/live-control-ui/src/api/liveApi.test.ts`
4. `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`
5. `apps/live-control-ui/src/playSurface/PlaySurfacePage.test.tsx`

The World surface uses only the World-scoped v2 active pointer. An empty, malformed, or wrong-World selection remains at the explicit chooser. Reentry validates the active state and exact World Run detail before navigation, then suppresses the subsequent read-time active-pointer write. An explicitly selected exact World Run writes the v2 pointer only after normal admission reaches READY. Campaign mode retains the campaign-only v1 GET/PUT path.

The active-Run deduplication repair is at exact consumer commit `72e2b0bd70fb387c211563b943294f3b9752043a`. `liveApi.test.ts` + `PlaySurfacePage.test.tsx`: 139 passed, including A→external B→reentry B→explicit A, failed A selection→explicit retry, late stale A failure while B is selected, and same-Run progress re-admission without a duplicate PUT. Reentry still performs no PUT. `git diff --check` passed. Typecheck retains the known baseline `ThreatPublicationPanel.tsx:553` `TS2503: Cannot find namespace 'JSX'`; the consumer paths add no type errors. The cumulative base-to-head diff remains 11 paths: five producer implementation files, this handoff, and the five consumer paths. Producer implementation/test blobs remain unchanged from accepted head `63af78136448b6a5aa44e7230bfce784af049dc7`.

PR #952 was independently accepted and merged at `b234cf407da7ef7bd6fc58e541106066e90e5229`. The merged implementation branch writer lease is closed. PR #953's layout repair, merged at `9952737a0a31937f43e0dd52818671374af5b8a4`, is also present in current `main` at `b234cf407da7ef7bd6fc58e541106066e90e5229`.

## 5. Acceptance evidence

- Select a World Run, read it back for the same World, and preserve timestamp on idempotent selection.
- A mismatched-World GET returns empty and leaves the singleton row unchanged.
- A mismatched-World PUT rejects without replacing the existing selection.
- Corrupt pinned aggregate integrity blocks selection without changing the pointer; same-owner GET reports integrity failure.
- V1 GET projects empty for a selected World Run; V1 PUT continues to reject it; campaign legacy selection remains intact.
- Route tests prove `/active` is registered before the dynamic `{run_id}` route and strict request/response validation rejects malformed fields and partial-null pairs.
- Focused owning-boundary PostgreSQL suites, Ruff, and cumulative `git diff --check` pass.

## 6. Operational limits

Use only the disposable PostgreSQL 16 test container `dmb-world-active-run-v2-test-pg16` on `127.0.0.1:54329`. Never touch the operator databases on ports 54330/54331. Do not restart listeners or mutate operator Runs. ROOT owns any runtime restart. Session28 Apply remains held pending its separate trusted human reply.

## 7. Post-merge settlement

At current `main` `b234cf407da7ef7bd6fc58e541106066e90e5229`, the producer and accepted UI consumer are merged and their slice write leases are closed. ROOT owns deployment of the matching stable runtime and the remaining production QC. This handoff records no production-QC pass, rollout completion, or operator Run mutation. Session28 Apply remains held pending trusted human approval.
