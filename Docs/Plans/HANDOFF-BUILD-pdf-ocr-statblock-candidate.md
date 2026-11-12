# HANDOFF — Build PDF OCR statblock candidate preview

Status: ACTIVE, serial, one unstacked PR.
Base: `origin/main@19d290d42dd5f1d7f82035a620b5a3ea93d145e4`.
Branch: `codex/pdf-ocr-statblock-candidate`.
Checkout: existing `pdf-review-handoff/DungeonMindBuddy`; do not create another lane.

## Outcome

When an author runs local OCR on a retained PDF crop in Build, show the existing statblock candidate preview only when OCR contains a recognizable creature type, exactly one Armor Class and Hit Points, and a complete six-score row in statblock order. Keep the exact retained source revision, page and region attached. Leave prose, image-only, isolated labels and multiple-statblock OCR as transcription only or unassociated candidate details.

This is a review-only extraction preview. It does not construct a complete mechanics definition, save a statblock review, create a threat draft, validate mechanics, admit facts, publish to the Graph, or change DungeonMind authority. The existing manual JSON route remains until a later slice provides a safe incomplete/complete candidate-to-review contract.

## Write set

- This handoff.
- `apps/live-control-ui/src/buildSurface/BuildPdfPreview.tsx` and `PdfStatblockCandidate.tsx`.
- `apps/live-control-ui/src/buildSurface/BuildPdfCaptureReview.test.tsx` and `PdfStatblockCandidate.test.tsx`.

No backend route, schema, storage, OCR runner, statblock definition parser, other surface or runtime state changes.

## Behavior and proof

- Reuse the existing local OCR endpoint and `PdfStatblockCandidate` parser; do not add a model/provider pass or alter OCR output.
- Render the candidate from the exact OCR result under the submitted retained locator only when the capture has the standard creature-type, Armor Class, Hit Points and six-score structure. Keep isolated or multiple labels as transcription only or an unassociated candidate; never combine them into one statblock.
- Keep the page and source-revision label from the selected retained locator. Never infer or rewrite values.
- Test an OCR statblock through the exact component path, preserving the locator; test ordinary prose, image-only results and isolated AC/HP labels produce no associated candidate; test a mismatched region remains rejected.
- Run the focused Build PDF capture tests and affected UI typecheck/build if available. Preserve any pre-existing failures.

## Current verification

- Independent review cycle 1 found a false-positive risk from associating unrelated Armor Class and Hit Points labels. The candidate preview now requires a creature-type line, exactly one AC and HP, and a complete six-score row before it offers or associates extracted fields.
- Focused tests: `BuildPdfCaptureReview.test.tsx` and `PdfStatblockCandidate.test.tsx`, 16 passed after the review fix.
- Exact hosted verification before the review fix passed at `d6c551d573796c85cb33fa5f99b0a2627f3b5aac`: build exit 0; hosted contract test invocation exit 0; evidence validated. Final exact-SHA verification and a new independent review are still required.
- The discovered-suite diagnostic was red on the pre-review candidate and exact base: 164 failed identities shared, zero candidate-only, build exit 0, cleanup complete. Candidate had 7,670 discovered cases; base had 7,667. Evidence retained under `/home/drakosfire/Projects/.codex/pdf-review-handoff/verify-discovered-d6c551d` and `/home/drakosfire/Projects/.codex/pdf-review-handoff/verify-discovered-main-19d290d`.

## Dependencies and successor

This slice depends only on the merged OCR and statblock-preview paths. The successor is not active: completing a source-located editable mechanics candidate requires deciding how incomplete extracted fields are represented without fabricating mechanics or bypassing DungeonMind's native source/admission owners. Do not absorb that new durable contract here.
