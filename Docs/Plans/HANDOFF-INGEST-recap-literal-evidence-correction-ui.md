# INGEST: recap literal quote correction UI

Status: DELIVERED / lease closed — PR #1395 merged as `661d96c2e82e09b8c0f6cd8a8eebb2d88a62ea7f`, reviewed head `2e72df70302549993193d0d73ba4536e16f96223` (ARCHITECTURE Cycle2 PASS). The exact rebuilt UI was adopted on5202 with older browser assets retained and no operator-tab reload or API restart. No DEMO implementation delegation is active.
Base: fetched `origin/main@a2778b5a18d9f20985d8ded96f8b9cf4a6ed2a50`.
Branch: `codex/ingest-recap-quote-correction-ui`.
Checkout: reused `/home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy` with existing dependencies. ROOT owns this serial source lane; DOGFOOD's quote-integrity helper/runner/tests are parallel-independent. PRIME owns review/merge/delivery after independent exact-head review. No new checkout or environment.

## One capability

A GM can locally preview literal anchor-quote replacements on an exact recap candidate, then explicitly save a new immutable candidate through the existing recap evidence-correction endpoint. The original remains unchanged. This is quote correction only; no description, identity, relation, semantic decision, World ownership/association, prepare, acceptance or publication capability is enabled.

Keep sourceReviewOnly as the World authority fence throughout navigation, pending/error and parent→child loading/reload. Add separate recap correction eligibility from the exact REVIEWABLE `recap_category_v1@1.0` run and matching invalid-evidence review package with frozen source/span/candidate identity. Existing worldbuilding behavior remains unchanged. The existing GM route remains final authority.

Use existing `POST /api/live/extract-promote/runs/{id}/recap-evidence-corrections`, request schema `dmb_exact_run_evidence_correction_request_v1`, response `dmb_recap_evidence_correction_response_v1`; no backend contract change. Add a separate authenticated adapter and only this endpoint's anchored authorization matcher, preserving CSRF/session/destination/redirect checks. Do not add it to automatic mutation retry eligibility.

Preview shows original/replacement and exact source paragraph without POST. Do not suggest or apply a quote automatically. Empty/unchanged inputs cannot submit; do not reject normalization-equivalent quotes with a stricter browser matcher. At explicit submit freeze exact request bytes and full operation scope (parent/source/span/candidate pins, World/navigation generation). A synchronous lock prevents double dispatch. Navigation and A→B→A fence POST and child GET completion/error/finalizers. Ambiguous outcomes retain a deliberate exact-body retry handle; edits never alter that retry. No automatic mutation retry or claimed rollback.

Validate response shape/parent/candidate/digests/state, then GET exact child and review package and prove parent/source/span/candidate identity before switching the visible route. Never select latest. Keep recovery when validation/GET fails. Display the child's current semantic state; an idempotent retry may return held/accepted/rejected, not necessarily newly held. No wording treats quote correction as semantic acceptance.

## Exclusive eleven-path lease

- `Docs/Plans/HANDOFF-INGEST-recap-literal-evidence-correction-ui.md`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/api/extractPromoteApi.ts`
- `apps/live-control-ui/src/api/extractPromoteApi.test.ts`
- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/api/liveApi.evidenceReads.test.ts`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExactRunProjection.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx`
- `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx`
- `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.test.tsx`

No backend, CSS, dependency or operator-correction contract paths. First commit is this handoff only. Return any necessary scope expansion before editing. PR #1235 remains preserved at `ffc2276ae9b3e7feac220a1cfff2ea18ced5a414`; PRIME placed an explicit execution/merge/adoption hold and withdrew its six overlapping UI path reservations in the PR body on 2026-10-17. It must re-anchor and obtain fresh review after this serial slice; no old-stack cherry-pick or completion claim.

## Owning verification and delivery

Mounted API/UI checks prove zero POST on load/edit/preview, one explicit submit despite rapid duplicate actions, immutable manual retry after uncertain response, newer draft isolation, stale POST/child GET A→B→A, mismatched parent/source/span/candidate/package rejection, child GET failure, current held/accepted/rejected rendering, source-only ownership/publication fences across child/reload, and unchanged worldbuilding controls. Adapter/transport tests cover exact payload/route, auth+CSRF, narrow path matching and redirect refusal with no automatic correction replay. Existing real-backend correction tests must pass on the standard disposable54329 fixture; mocks alone do not establish child lifecycle readiness.

Inspect cumulative diff, typecheck/build with existing dependencies, commit/push/open one PR, independent exact-head review, then deliver on5202 with retained drafts/runs/Graph and no extra preview servers. A live correction POST is a separate operator action after an explicit preview; no live correction, new extraction/provider call, semantic acceptance or publication is authorized by implementation tests. Existing Session29 candidate remains immutable and inspectable.

## Settlement

Four owning UI/API suites pass (104 tests), TypeScript and pinned production build pass; 13 unchanged real-backend correction lifecycle tests pass on disposable PostgreSQL. Independent review found and verified repairs for departed-surface completion and same-parent/different-request recovery receipts. The browser digest matches the existing server canonical request bytes, including Unicode target ordering and quote bytes.

The saved Session29 parent `feb54858-4f22-449f-a59b-82555618f47f` rendered the new correction form on5202. A local-only preview displayed the exact old/new quote and enabled explicit Save while exposing no World prepare action. No live correction POST, child creation, semantic acceptance or publication was performed. Actual operator Save and verified child readback remain a separate dogfood acceptance step; delivery does not establish full Ingestion or semantic readiness. Existing identity/location/relation holds remain.

The eleven-path implementation lease is closed. PR #1235 remains held at its prior head until separately re-anchored and freshly reviewed; closing this lease does not activate its older work. DOGFOOD retains the independent host quote-integrity slice. Private rollout/build evidence is at the established `jev-evidence-loop-20261016` state location, not a runtime configuration dependency.
