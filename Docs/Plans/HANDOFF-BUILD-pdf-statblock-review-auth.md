# HANDOFF — Authorize Build PDF statblock review requests

Status: ACTIVE; serial; one unstacked PR.
Base: `origin/main@a88934e4b57c35c88a4927fd7f952b51314a8f19` (re-anchored).
Branch: `codex/pdf-statblock-review-auth-20261112`.
Checkout: existing `/home/drakosfire/Projects/.codex/pdf-gold-baseline/DungeonMindBuddy`; reuse it, do not create a worktree.

## Outcome

The Build PDF statblock review endpoint already exists on main. Its server route requires native Graph GM authorization, but the UI transport does not classify `POST /api/live/agent/worlds/{world}/build-pdf-sources/statblock-reviews/{review}/from-regions` as protected, so it omits local-session CSRF and receives a pre-handler 403. Add the exact route to the client authorization matcher so normal Build review requests can reach the existing endpoint.

On a trusted local-session rejection only, refresh the session and replay the same request once. Permit this only for the exact UUID review route with a nonempty region list and string instruction. Do not replay after uncertain network failures. Keep server-side GM authorization and exact source-region verification unchanged.

## Write lease

- This handoff.
- `Docs/Plans/HANDOFF-BUILD-pdf-statblock-source-extraction.md` to mark the delivered implementation lease settled and link this successor.
- `apps/live-control-ui/src/api/liveApi.ts` for the exact native Graph authorization route and trusted pre-dispatch retry predicate.
- `apps/live-control-ui/src/api/liveApi.evidenceReads.test.ts` for protected-route, near-miss, CSRF-recovery and exact-body assertions.

Do not change the server endpoint, OCR/extraction behavior, source data, review storage, DungeonMind admission, or publication.

## Verification

Provider-free verification completed against this candidate:

- `npm run test -- --run src/api/liveApi.evidenceReads.test.ts src/buildSurface/StartPdfStatblockReview.test.tsx src/buildSurface/BuildPdfStatblockReview.test.tsx` — 119 passed.
- `npm run typecheck` — passed.
- `npm run build` — passed; existing chunk/dynamic-import warnings remain.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q tests/test_build_pdf_statblock_extraction.py tests/application_state/test_pdf_statblock_review.py` — 10 passed.

No OCR/model provider call, database mutation, review creation, or Graph publication was performed by this authorization fix.
