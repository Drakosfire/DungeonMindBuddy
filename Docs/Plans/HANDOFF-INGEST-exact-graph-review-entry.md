# INGEST: Open Graph Review for the exact processed run

**Status:** ACTIVE — PRIME authorized this bounded Graph Review entry repair on 2026-10-17.
**Base:** `origin/main@23ad40b84015213ffc9f3d1fa2420570fa71bd04`.
**Branch:** `codex/ingest-graph-review-entry`.
**Checkout:** `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy`; preserve the existing shared checkout and its unrelated dirty Combat/Ingest work. Build the commit from the pinned base with an alternate index; do not switch or stage the shared index.
**Topology:** parallel-independent from draft PR #1235. #1235 changes the downstream Graph Review projection for Worldbuilding source observations; this slice changes only the Ingest entry action and its test. Both use the already-existing exact-run URL contract, and this slice neither edits nor assumes the pending observation UI. PR #1327 Combat is on separate paths. The merged status-presentation PR #1324 is settled below.

## Mission

When Process produces a reviewable graph candidate, the Graph Review action must open the existing exact-run Graph Review for that same extraction, source artifact when known, campaign, session, and selected World. The handoff must not infer “latest,” silently remain on the recap page, or open a different session's run.

## Settled predecessor

`HANDOFF-INGEST-status-presentation.md` was completed by PR #1324 (`c3df3d8384a205b28ffbe6c2f5d88d7bd2c04ea8`), merged as `2b284ff96dea8bd42cf1e3dd6f3a647ab0a4f4f5`, and is present in the pinned base. Its historical evidence is retained; the label fix and rendered/persistence limitations are not reopened by this slice.

## Exclusive expected write set

- `Docs/Plans/HANDOFF-INGEST-exact-graph-review-entry.md` — this bounded contract and completion evidence.
- `Docs/Plans/HANDOFF-INGEST-status-presentation.md` — factual backward-looking settlement of PR #1324 only.
- `apps/live-control-ui/src/modules/IngestionModule.tsx` — construct the exact run handoff from the current hydrated Process result, navigate the mounted Ingest page into exact-run Graph Review, and keep the CTA unavailable when exact identity is missing.
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` — mounted component coverage for exact identity, selected campaign/session/World, route notification, and missing-run behavior.

No Graph Review module, API, server, schema, extraction, source, graph, database, retained data, runtime configuration, `dist`, environment, or port/5202 writes are authorized.

## Invariants and failure cases

- Derive the run ID only from `graphPreview.extraction_run_id` on a result that owns the currently selected campaign/session. Never read the run catalog's latest entry or reuse a stale `recapReviewRunId`.
- Include `campaign`, `session`, and `world` from the current selected Ingest context. Include `sourceArtifactId` only when it is supplied by the current exact-run projection for the same run; otherwise let the exact-run route load and verify the run's source identity.
- Remove unrelated exact-run identity parameters before adding the new handoff. Keep the existing world-scoped Ingest route and preserve a browser-back path to the recap.
- Notify the mounted route after history navigation so it switches from the Ingest composer to Graph Review. Preserve the run-catalog refresh event.
- If the current result lacks an exact run ID or does not own the selected session, Graph Review must be visibly unavailable and its handler must be inert. Do not route to an empty/default/latest Graph Review.
- This UI repair does not prove backend publication, candidate acceptance, or durable source behavior. It does not authorize processing the user's recap or changing the 5202 environment/data.

## Verification and completion

Implementation evidence:

- Added a regression proving a current `candidate_validation_ready` result opens Graph Review with the exact `extractionRunId`, source artifact from the matching exact projection, selected campaign/session/World, and route notification. The navigation uses browser history so Back returns to the recap; the catalog refresh event remains intact.
- Added a regression proving a candidate without an exact run ID has a disabled Graph Review action and an explicit explanation instead of a no-op navigation.
- Added an explicit Session 22 route to the existing Process test. Its source text is Session 22, so the selected target must be Session 22 rather than the default prior-session offset.
- `npm test -- --reporter=dot src/modules/IngestionModule.test.tsx`: **65 passed**. The suite retains its existing React `act(...)` warnings from the editable-source and empty-navigation tests.
- `npm run typecheck`: passed.
- `git diff --check origin/main` for the leased changes: passed.
- Fresh `git fetch origin main` confirmed `main@23ad40b84015213ffc9f3d1fa2420570fa71bd04`. The intervening #1338 changes are limited to Build/agent paths. PR #1235 remains open/draft with a disjoint Graph Review projection lease; its downstream exact-run UI is not changed here.
- All Process responses were synthetic mocks. The real recap, 5202, API servers, database, and retained artifacts were untouched. No build output, `/tmp`, new checkout, or environment copy was created.

The bounded code and tests are ready for the assigned review PR. Do not merge or move 5202 to this branch.
