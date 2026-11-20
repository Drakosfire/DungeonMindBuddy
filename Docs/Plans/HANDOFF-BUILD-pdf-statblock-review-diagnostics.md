# HANDOFF — Diagnose Build PDF statblock review failures

Status: SETTLED; UI diagnostic slice merged in PR #2500 as 691096d1d04f3d4397fdd75af35f39d58016cedb. API failure classification is continued in HANDOFF-BUILD-pdf-statblock-generation-diagnosis.md.
Base: `origin/main@ff90b31ea39623e070de5a98bd8a37292e5deb07` (fetched).
Branch: `codex/pdf-statblock-review-diagnostics-20261112`.
Checkout: existing `/home/drakosfire/Projects/.codex/pdf-gold-baseline/DungeonMindBuddy`; reuse it, do not create a worktree.

## Outcome

When Build cannot create a statblock review from selected retained-PDF regions, show a concise user-facing explanation and the safe stable server error code. Preserve specialized messages for incomplete extraction and invalid structured output. Do not display raw response bodies or server internals.

This diagnostic slice does not change API behavior, OCR, model execution, extraction validation, source data, review persistence, or DungeonMind admission/publication. Its purpose is to expose the existing owning-boundary failure so the next implementation decision is evidence-based.

## Write lease

- This handoff.
- `Docs/Plans/HANDOFF-BUILD-pdf-statblock-review-auth.md` to settle the merged predecessor.
- `apps/live-control-ui/src/buildSurface/StartPdfStatblockReview.tsx`.
- `apps/live-control-ui/src/buildSurface/StartPdfStatblockReview.test.tsx`.

No other product paths are in scope. Preserve exact selected source-region locators, the failed attempt, and all user data. Never publish a review as part of diagnostics.

## Verification

- Focused tests cover incomplete extraction, invalid output, unavailable OCR/generation, safe unknown error codes, conflict recovery, and success behavior.
- Run the repository-owned local frontend verifier at the exact commit for both `hosted` and `discovered` suites; retain exact base comparison for any discovered-suite failures.
- Re-run one ordinary Build review request on the same retained Conks PDF region that produced the generic error. Confirm the visible error identifies the actual server code and that no review is offered on failure.
- Independent exact-head review is required before merge.

## Dependencies and boundaries

Depends on merged PR #2495, which authorizes the UI request path. OCR-only reading of the selected region succeeded; structured review creation failed and the prior UI hid the specific response code. Buddy owns the Build presentation; the API owns OCR/generation and its error classification; DungeonMind continues to own source identity, admission and publication.
