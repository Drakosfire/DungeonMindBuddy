# DOGFOOD — review source observations during Ingest

Status: ACTIVE  
Owner: DOGFOOD  
Base: `origin/main@b2c76cb6c83b3e4d9835376dd92956ab5f2b6f13`
Branch: `codex/ingest-source-observation-review`
Checkout: `/tmp/dmb-ingest-empty-welcome`
Topology: serial; assigned implementation PR #1235 remains the sole PR for this slice after merged #1191 and #1232/#1234.

## Objective

Make exact-run Worldbuilding source observations understandable and explicitly
reviewable in Graph Review. Show each candidate alongside its pinned source
evidence, let the operator choose node identity and observation/relationship
dispositions, and prepare an exact, revision-bound write plan for inspection.
Do not claim this fixes extraction/linking quality, rerun semantics, or live
ingestion acceptance; those remain separate Ingest-mandate work.

## Re-anchoring and evidence

- GitHub confirmed current `main` at
  `80dd7a2a54a2677953c1fa8443df156717d04861` on 2026-10-16, 13 commits beyond
  the PR's `b2c76cb6` base. Compare shows the intervening changes are in server
  graph-context code and tests; none touch this UI write lease. GitHub currently
  reports PR #1235 mergeable, so this bounded update retains the established
  base and commit ancestry.
- PR #1191 (Ingest local toolbar) is merged at that base. The current exact-run
  review endpoint already returns `source_observation` assertions for the
  Gazetteer 1.11 profile, and the worldbuilding prepare/confirm service and
  routes are present.
- Current UI types narrow assertion kinds to object/relationship, and the
  exact-run workbench has no decision surface for source observations.
- No open source-observation UI PR was found in GitHub search. The source
  producer/backend lease in `HANDOFF-BUILD-source-observations.md` is separate;
  this lease is UI-only and does not edit its files.

## Exclusive expected write set

- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/api/extractPromoteApi.ts`
- `apps/live-control-ui/src/api/extractPromoteApi.test.ts`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExactRunProjection.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorldbuildingObservationReview.tsx` (new)
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorldbuildingObservationReview.css` (new)
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorldbuildingObservationReview.test.tsx` (new)
- `Docs/Plans/HANDOFF-DOGFOOD-ingest-source-observation-review.md`

No backend, shared navigation, schema, source/candidate artifact, ingestion,
provider, database, serving configuration, external runtime, or 5202 writes.

## Invariants and failure cases

- Load and review only the exact run selected by the URL/handoff. Keep its run,
  source artifact/revision, source paragraphs, assertion IDs, and evidence
  bindings together; never substitute the catalog's latest run.
- Default every disposition to undecided. No assertion is silently accepted.
  An incomplete disposition set, invalid source evidence, or unavailable exact
  review blocks prepare.
- A source observation can be accepted only when its exact subject candidate
  has a create-new or bind-existing decision. A relationship can be accepted
  only when both endpoint nodes have accepted identity decisions. Rejection or
  deferral remains explicit and visible.
- Binding an existing node uses results from the selected managed World only.
  Pin the managed-to-native World ID and binding version, then pin the target
  lookup to the World Graph head revision returned with those results. If the
  binding or head changes, discard the stale binding and require a fresh lookup.
  Never ask the operator to trust an unvalidated raw node ID.
- Prepare sends every candidate disposition once, with the exact run ID and
  expected parent revision. Render the server-prepared effect and provenance;
  never infer a graph write from a successful prepare.
- Every asynchronous prepare result, error, and finalizer is scoped to the
  selected exact run, source artifact/revision, World binding, graph revision,
  and a monotonic request generation. A late response cannot repopulate an old
  plan after selection changes (including A→B→A), and an old finalizer cannot
  clear a newer request's pending state.
- The current API response model says `confirmable: false` with an
  inert-plan reason, despite a server confirm endpoint and native service
  tests. Respect that response: this UI slice must not show or invoke Confirm.
  Record the contract mismatch as a server-owned follow-up; do not repair it in
  this UI lease or imply that candidate decisions have been published.
- No automatic extraction, prepare, confirmation, publication, or candidate
  mutation occurs on load or when editing local dispositions.
- Preserve the existing recap promotion, first-world publication, source-only
  evidence viewing, and worldbuilding inspect-only routes. Route only the
  observation-capable exact Worldbuilding profile through this dedicated
  decision surface.

## Verification

- Unit and mounted Graph Review tests cover explicit decisions, missing subject
  decisions, relationship endpoint gates, stale target revision, evidence
  failure, exact run/source identity, inert prepare preview, and the absence of
  a confirm action when the server response is non-confirmable. Deferred-prepare
  regression tests cover old success, A→B→A World changes, and old failure or
  finalizer behavior while a newer request is pending.
- Run focused UI suites, `npm --prefix apps/live-control-ui run typecheck`, the
  production build, and `git diff --check`.
- Inspect the complete `origin/main`→HEAD diff and verify no leased backend or
  runtime paths changed.
- Use mocked exact-run and managed projection fixtures only. Do not prepare or
  confirm the preserved Elderwyld/F43 candidate, and do not claim rendered live
  ingestion or publication acceptance.

## Completion evidence

- 2026-10-16: focused UI verification passed — 74 tests across
  `extractPromoteApi.test.ts`, `GraphReviewWorldbuildingObservationReview.test.tsx`,
  `GraphReviewGenericRun.test.tsx`, and `GraphReviewWorkbenchModule.test.tsx`.
- `npm --prefix apps/live-control-ui run typecheck` passed.
- `npm --prefix apps/live-control-ui run build` passed. Vite emitted the
  existing large-chunk warning for the 2.38 MB application bundle.
- `git diff --check` passed. The exact-run route test confirms the Gazetteer
  1.11 source-observation run uses the dedicated decision panel and hides the
  duplicate assertion list. Component tests verify evidence binding, explicit
  identity/disposition gates, exact graph revision and managed-to-native World
  binding checks, and a non-publishing prepared-effects preview.
- All API responses and graph queries in tests are mocked. No real source
  candidate was prepared or confirmed, no World Graph was written, and live
  Ingest UI/publication acceptance remains outstanding.

## Completion

Implementation remains in draft PR #1235 on
`codex/ingest-source-observation-review`, now based on
`main@b2c76cb6c83b3e4d9835376dd92956ab5f2b6f13`. GitHub currently reports the
PR mergeable against latest `main@80dd7a2a54a2677953c1fa8443df156717d04861`.
The PR branch is authoritative for the current head SHA. Do not merge without
explicit merge authority. The server confirmation-contract mismatch and real
source-observation publication/readback remain open gates; live Ingest
acceptance is still outstanding.
