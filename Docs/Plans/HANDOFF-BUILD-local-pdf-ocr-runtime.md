# HANDOFF — BUILD local PDF OCR runtime configuration

Status: SETTLED — merged as PR #2487.
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

The launcher configuration is delivered. A later fresh worker attempt in the
current shell failed with `DeepSeek OCR 2 requires a visible CUDA GPU`; the
shell currently cannot communicate with the NVIDIA driver. Keep the earlier
MeatMindNode smoke report as historical evidence, not proof that OCR can be
re-run in this shell. The retained five-region crop run remains available for
offline scoring without provider calls.

## Successor

The next serial slice is pinned in
`HANDOFF-BUILD-pdf-region-gold-scorer.md`. It reproduces the five-region
baseline offline; it does not add a new OCR run, review flow, or publication
behavior.
