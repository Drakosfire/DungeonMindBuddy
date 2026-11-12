# HANDOFF — BUILD local PDF OCR runtime configuration

Status: ACTIVE, serial, one unstacked PR.
Base: `origin/main@20367596680f8a20a478d78ceb6351d90027bb9a`.
Branch: `codex/real-document-ocr-workflow-20261112`.
Checkout: existing `DungeonMindBuddy` checkout; no additional worktree.

## Outcome

Make the existing local DeepSeek OCR 2 worker available to ordinary Build PDF
region capture when Buddy is launched with `./run`. Resolve the worker, pinned
local cache snapshot, and Python environment from the existing project layout;
allow explicit local overrides. Missing or invalid local assets leave OCR
unconfigured and fail closed. No external model calls or network model download.

This PR also settles the merged predecessor `HANDOFF-BUILD-pdf-region-table-candidate.md` (#2466).

## Exclusive write set

- This handoff.
- `Docs/Plans/HANDOFF-BUILD-pdf-region-table-candidate.md` (settle merged predecessor only).
- `run`.
- `scripts/local_pdf_ocr_env.sh`.
- `tests/test_local_pdf_ocr_launcher.py`.

## Boundaries and proof

The existing `/api/live/build/pdf-ocr` endpoint and GenerationEngine OCR 2 worker
remain the execution owners. The launcher only supplies their existing local
configuration. Preserve `local_files_only`; do not add OCR providers, new model
selection, ingestion, candidate persistence, Graph admission, or publication.

Verify exact local asset discovery, explicit overrides, and safe refusal when
cache references are invalid. The existing worker was run locally against the
two-page retained MeatMindNode PDF; both pages completed. The first page
recognized the statblock title and hit-point/ability fields, but the exact
"Armor Class" label was not recognized. The second page recognized the core
body, magic-resistance and lair-action headings. This is an initial smoke
observation, not the five-example scored baseline; rendered page captures were
temporary and have been removed. No Graph writes or source changes occurred.
Review the complete diff and obtain independent review before merge.

## Next serial slices

1. Measure the five source-pinned Conks/Sheep regions against the current OCR
   baseline, keeping classification, transcription, structure, and source
   location separate.
2. Add source-located, review-only multi-region/page statblock assembly for the
   retained Elderwyld Meat Mind source.
3. Exercise native DungeonMind review/admission/publication and cited Buddy
   retrieval after the candidate is accurate. These slices are not authorized
   by this runtime-configuration lease.
