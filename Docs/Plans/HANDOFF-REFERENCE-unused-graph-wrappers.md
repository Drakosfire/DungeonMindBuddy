# REFERENCE: remove unused legacy graph client wrappers

Status: ACTIVE for the bounded client cleanup below. The user accepted the recommendation for a small unused-wrapper cleanup PR, separately from the larger caller and data-retention investigation: "Agreed, cleanup PR. Go". The coordinating root explicitly assigned design and scope coordination to this lane before implementation. No merge or deployment authority is granted.

## Authority and topology

- Base: current remote main `ec646dab173deb1ddc6075226a496b400afc8eb5`, independently read through the GitHub connector on 2026-11-11 and present unchanged as the local object. The current main policy explicitly permits a durable pinned branch handoff; no main-first handoff merge applies to this slice.
- Pin: the handoff-only commit containing this file, on local branch `codex/unused-graph-wrappers-20261111`. Record that exact commit in the implementation handback and resulting PR. Commit the handoff before editing product or test files.
- Checkout: `/home/drakosfire/Projects/.codex/unused-graph-wrappers-20261111/worktrees/DungeonMindBuddy`. The existing Projects parent is writable on filesystem UUID `48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8`. Do not touch the dirty primary checkout.
- Topology: parallel-independent of the specifically bounded concurrent lanes below. One cleanup implementation PR, titled `REFERENCE: remove unused legacy graph client wrappers`, opened as a draft. No additional process or retirement PR belongs to this lane.
- Runtime: source and local tests only. No shared service, port, database, provider, browser profile or retained-data ownership is allocated. Scratch, caches and verification outputs belong below the same task root on Projects, outside source when required by the verifier.
- Direct shell GitHub fetch was blocked by network policy. No retry or bypass is authorized by this handoff. The connector established the current remote source before local allocation; use permitted publication tooling or report the exact remaining blocker.

## Outcome and failure critique

Remove exactly three exported wrappers with no current production callers: `getGraphPreviewLatest`, `getRecapGraphPresentation` and `getGraphIngestRuns`. Also remove their now-unused private helper `recapGraphQueryString`, local `GraphIngestRunsQuery` interface, and the four now-unused imports `GraphPreviewSurfaceResponse`, `GraphIngestRunsResponse`, `RecapGraphPresentationResponse` and `RecapGraphQuery` from `liveApi.ts`.

Keep all shared type definitions in `api/types.ts`, backend routes, historical readers, stored data, manifests and registries unchanged. Retain neighboring `getRecapArtifacts`, `getLatestGraphIngestRun`, current native/World APIs, transport/authentication and session-retry behavior. This is dead client code removal, not backend or preview-union retirement and not evidence that historical data can be deleted.

The main failure risks are an overlooked dynamic or test caller, deleting a shared type/neighboring wrapper, weakening a retained navigation/no-legacy-request assertion, or silently carrying another lane's changes. Recheck symbol references across tracked production and test source before edits. Preserve negative no-legacy-IO coverage at the actual retained boundary where a deleted wrapper spy can no longer express it; do not merely drop meaningful behavior assertions or change unrelated fixtures to manufacture a green result. Newly discovered production callers or required paths outside the exact scope are a stop-and-return decision.

## Exclusive bounded write scope and disjoint seams

Only the following seven files may change, with the indicated limits:

1. `Docs/Plans/HANDOFF-REFERENCE-unused-graph-wrappers.md`: this bounded contract and truthful verification/result updates.
2. `apps/live-control-ui/src/api/liveApi.ts`: only the three named wrappers, helper, interface and four imports above. No other export, type, request body, URL, classifier or shared transport change.
3. `apps/live-control-ui/src/api/liveApi.test.ts`: only the obsolete `getGraphIngestRuns` import and its dedicated query-string test, plus a narrowly necessary replacement proving the removed API is absent. Do not edit credential/history fixtures, `emptyHistoryResponse`, session renewal, command responses or their assertions.
4. `apps/live-control-ui/src/App.test.tsx`: only obsolete `getGraphIngestRuns` module mock/setup and its no-call assertion or boundary-preserving replacement. No root-Surface test expectation changes.
5. `apps/live-control-ui/src/guidedTour/Navigation.integration.test.tsx`: only obsolete `getGraphIngestRuns` mock/setup and any necessary retained no-legacy-request boundary proof.
6. `apps/live-control-ui/src/test/appNavigation.test.tsx`: the same obsolete mock/setup limit.
7. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx`: only the obsolete `getGraphIngestRuns` spy in the W10 published-World-Graph case and a narrow equivalent actual-boundary assertion if needed. Keep the published World Graph, source, review and no-extract-promote assertions intact.

The coordinator explicitly declares these function/test seams disjoint from the concurrent scopes inspected on 2026-11-11. This does not transfer or alter their authority:

- Open #2104, head `d9a27a7c36d4cebf8daa6e2584a36ed021409819`: its `liveApi.ts` lease removes only `postPlanDocumentEditProposal` and `PlanDocumentEditProposalRequest`/`PlanDocumentEditProposalResponse` imports. Leave them intact here.
- Open #2087, head `687b26a2b83b5fe424801245b1cd199c1d183630`: its transport lease registers `/api/live/recap-name-review` in authorization and read-only renewal. Open stacked #2090, head `19355258583edc0a2109ada31a109d3d1b3fbd7e`, adds exact native prepare/confirm/support transport registrations. This cleanup edits none of those functions or strings.
- Open #2298: its `liveApi.test.ts` lease is the credential/history-envelope fixture repair batch. Its six fixture changes and new `emptyHistoryResponse` helper are separate from the obsolete runs query-string case; this cleanup neither adopts nor edits them. The CI lane's other source/test/workflow ownership stays unchanged.
- Open #2326, head `b30833ede97cb4c79acf17a1fe55ff50446c7452`: its `App.test.tsx` lease is only the root-Surface expectation update. This cleanup edits only obsolete API mock/setup/no-call references, not that test.
- #2330 and #2374 are merged and ancestors of this base. Their historical ACTIVE headers do not create a new unmerged transport lane. Preserve all current native graph and hosted ownership behavior.

All 49 current open Buddy PR changed-file lists were inspected. Only the five PRs above overlap the six intended source/test paths. Read-only inspection of registered existing worktrees found no dirty `liveApi.ts` diff mentioning the five removed symbols. The dirty primary checkout's unrelated HTML/JSON error-message edit remains untouched. Recheck relevant refs and seams before publication; a newly overlapping change requires coordination, not blind conflict resolution.

## Verification and completion

- Read the current owning instructions and relevant repository skills in this isolated checkout. The stale dirty primary checkout policy is not this lane's policy.
- Before edits, retain the five affected test-file baseline and confirm zero production callers for all removed symbols. Preserve exact failed IDs and source/environment details.
- Run the affected Vitest cohort, TypeScript and production build after cleanup. Honor the global frontend lock; never overlap another frontend run around it. Do not alter dependency locks, test discovery/classification, workflows or timeouts.
- Run the current repo-owned exact-SHA hosted verifier and validate its receipt. Run the full default-discovered diagnostic at a meaningful integrated checkpoint as required by current AGENTS.md, coordinating the shared lock. Retain inherited red failures as red with an honest baseline comparison; narrow checks are not full qualification.
- Review the exact cumulative base-to-head diff, verify only these seven paths changed, and obtain independent exact-head review. Recheck no retained API/type/backend/data behavior changed.
- Commit the intended cleanup, publish only its assigned branch and open one draft PR. Report the exact remote head, checks, preserved limits and any blocker. Do not merge, enable auto-merge, deploy, delete retained data or send instructions to external agents.
- Inventory retained task worktree/scratch/cache/evidence paths and their purpose. No deletion permission is granted; preserve unique work and report cleanup follow-up.
