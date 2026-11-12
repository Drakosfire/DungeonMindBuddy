# HANDOFF — Build PDF OCR statblock candidate preview

Status: ACTIVE, serial, one unstacked PR.
Base: `origin/main@19d290d42dd5f1d7f82035a620b5a3ea93d145e4`.
Branch: `codex/pdf-ocr-statblock-candidate`.
Checkout: existing `pdf-review-handoff/DungeonMindBuddy`; do not create another lane.

## Outcome

When an author runs local OCR on a retained PDF crop in Build, show the existing statblock candidate preview if the OCR transcription contains one unambiguous supported statblock. Keep the exact retained source revision, page and region attached. Leave prose, image-only and ambiguous/multiple-statblock OCR as transcription only.

This is a review-only extraction preview. It does not construct a complete mechanics definition, save a statblock review, create a threat draft, validate mechanics, admit facts, publish to the Graph, or change DungeonMind authority. The existing manual JSON route remains until a later slice provides a safe incomplete/complete candidate-to-review contract.

## Write set

- This handoff.
- `apps/live-control-ui/src/buildSurface/BuildPdfPreview.tsx`.
- `apps/live-control-ui/src/buildSurface/BuildPdfCaptureReview.test.tsx`.

No backend route, schema, storage, OCR runner, statblock definition parser, other surface or runtime state changes.

## Behavior and proof

- Reuse the existing local OCR endpoint and `PdfStatblockCandidate` parser; do not add a model/provider pass or alter OCR output.
- Render the candidate from the exact OCR result under the submitted retained locator; the existing parser surfaces ambiguity and withholds field values unless it finds exactly one Armor Class and one Hit Points entry.
- Keep the page and source-revision label from the selected retained locator. Never infer or rewrite values.
- Test an OCR statblock through the exact component path, preserving the locator; test ordinary prose and image-only results produce no statblock candidate; test a mismatched region remains rejected.
- Run the focused Build PDF capture tests and affected UI typecheck/build if available. Preserve any pre-existing failures.

## Current verification

- Focused tests: `BuildPdfCaptureReview.test.tsx` and `PdfStatblockCandidate.test.tsx`, 14 passed.
- UI TypeScript project and production build: passed with existing dynamic-import and large-chunk warnings.
- Exact-SHA repository verifier and independent review are still required before merge.

## Dependencies and successor

This slice depends only on the merged OCR and statblock-preview paths. The successor is not active: completing a source-located editable mechanics candidate requires deciding how incomplete extracted fields are represented without fabricating mechanics or bypassing DungeonMind's native source/admission owners. Do not absorb that new durable contract here.
