# HANDOFF — BUILD selected PDF table candidate

Status: SETTLED — merged as PR #2466.
Reviewed head: `3e1d28e3844d311a049dabb4fcb7e483356d4cc4`.
Merge commit: `d7b0b1a1796a0777c5d193ccbfaa037d7bf4cf66`.
The source-located, review-only PDF table preview is now on main. The follow-up OCR/statblock workflow is separately scoped in `HANDOFF-BUILD-local-pdf-ocr-runtime.md`.

## Outcome

When an author selects and retains a PDF region in Build, show a review-only
table candidate when the PDF text layer and its run coordinates clearly encode
a roll-indexed table. Keep table headers, cell values, and the exact PDF page and
region together. Keep the statblock preview/import route hidden for table and
prose captures.

The checked case is the source-pinned `Male Villager Names` table on physical
page 18 of `Conks-Cons_PF_v21.pdf`. It has columns `1d12`, `Name`, and `Notes`;
all twelve names are in the existing source gold. The live PDF.js capture
returns duplicated title/header text but clean data rows. The selected region
is source-located and was not clipped.

## Exclusive write set

- This handoff.
- `apps/live-control-ui/src/buildSurface/BuildPdfPreview.tsx`.
- `apps/live-control-ui/src/buildSurface/PdfStatblockCandidate.tsx` and its
  existing test.
- New `apps/live-control-ui/src/buildSurface/parsePdfDiceTable.ts` and test.
- New `apps/live-control-ui/src/buildSurface/PdfTableCandidate.tsx` and test.

## Boundaries and proof

Use selected PDF.js text runs and their normalized page bounds to reconstruct
rows and columns. Deduplicate only exact coincident runs and repeated strings.
Do not infer blank cells from flattened text. If column positions, row grouping,
or source text are ambiguous, do not offer a structured table candidate. A
clipped capture cannot produce a candidate.

The preview is transient and review-only. No OCR/model/provider calls, new
admission route, durable table object, Graph publication, persisted extraction,
corpus edit, or change to the existing image/page capture flow. Extraction,
source identity/admission, and publication keep their current owners.

Validate the checked table against the existing Conks source gold and a
coordinate-level regression fixture. Confirm prose and a table capture do not
offer statblock fields or statblock import, while the existing Sheep statblock
tests remain intact. Run the repository's exact-source local frontend verifier
and the discovered diagnostic at the prescribed integrated checkpoint; retain
all inherited failures unchanged. Review the cumulative diff and obtain an
independent review before merge. No deployment or Graph write is part of this
lease.
