# HANDOFF — Build PDF source-linked statblock extraction

Status: SETTLED; implementation merged as `88f47a4093162e6a4f42b035b5f22ccfddd43ba1`. The original implementation lease ended at that merge. The post-merge route authorization correction is tracked in `HANDOFF-BUILD-pdf-statblock-review-auth.md`.
Base: `origin/main@71bcdf3bbd253ece509a5decdf4909de8bd7581f`.
Branch: `codex/pdf-statblock-source-extraction-20261112`.
Checkout: existing `/home/drakosfire/Projects/.codex/pdf-gold-baseline/DungeonMindBuddy`; reuse it, do not create a worktree.

## Outcome

From Build, collect one or more exact regions from a retained PDF. On explicit user action, Buddy reopens and verifies each region, runs the existing local DeepSeek OCR 2 path, then uses the configured Buddy structured-generation path to produce a complete `StatblockDefinitionV1Input`. If the model cannot produce a complete valid definition from the selected OCR text, return a clear failure and save nothing. If valid, save only a PDF statblock review draft linked to every exact source region and open the existing review UI. Do not create a creature draft, accept mechanics, or publish Graph facts in this slice.

The model receives OCR text and optional user guidance only. Do not send source IDs, hashes, page numbers, coordinates, receipts, counters or telemetry in prompts. Keep exact source identity, revision, pages and region coordinates in the host request and saved review.

## Write lease

- This handoff.
- `ci/test-classification.json` for the two provider-free test files owned by this slice.
- `apps/live-control-ui/src/buildSurface/BuildPdfPreview.tsx`.
- `apps/live-control-ui/src/buildSurface/StartPdfStatblockReview.tsx`.
- `apps/live-control-ui/src/buildSurface/StartPdfStatblockReview.test.tsx` and relevant PDF preview tests.
- `apps/live_control_server/routes/agent.py` only for the new endpoint.
- A new `apps/live_control_server/services/build_pdf_statblock_extraction.py`.
- Focused tests for the new extraction service and PDF source route.

Do not change DungeonMind contracts, statblock schema, migration/storage format, OCR runner, GenerationEngine, general statblock editor, ingestion/publishing authorities, or unrelated UI.

## Behavior and proof

- Require native Graph GM authorization and validate every exact retained region with the existing source-opening boundary before OCR.
- Use the existing local OCR worker sequentially for the selected regions. Do not accept browser-provided OCR text as proof of the selected source.
- Compose one structured request from transcription text plus optional author guidance. Require a complete strict statblock definition or a structured cannot-complete result; do not fill missing mechanics with defaults or inferred values.
- Persist only a complete definition as a review draft through the existing PDF review storage path, with the full authorized region list. Preserve explicit user review and existing DungeonMind validation/admission before publication.
- Add/remove selected regions across pages in Build and expose one clear action to generate a review. Keep existing text-only preview available.
- Provider-free tests must prove invalid/scope-mismatched regions, OCR failure, generation failure and incomplete output do not create a review; valid structured output saves the exact region list and can be opened in the existing review UI. Assert host metadata is absent from the model prompt. Test multiple regions and preserve page/region locators in the saved review.

## Verification and dependencies

- Focused backend route/service tests and focused Build PDF UI tests. Keep newly added and modified test files in the repository's test inventory; do not broaden this slice to classify unrelated pre-existing omissions.
- Local frontend verifier at the exact reviewed SHA; run the backend contract for the affected routes with disposable state only. No live provider or user database in tests.
- Independent exact-head Bugbot review before merge. Local OCR and model dogfood are separate evidence; do not claim them from mock tests.
- Depends on merged OCR2 routing, retained PDF region opening, and existing saved review, validation and acceptance path on `origin/main`.
