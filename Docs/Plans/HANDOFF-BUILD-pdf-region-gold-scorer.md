# HANDOFF — reproduce the selected PDF region gold baseline

Status: ACTIVE, serial, one unstacked PR.
Base: `origin/main@8bcff4db28f022f66cbb1a89fcfd09f383d36dfc` (re-fetched and confirmed).
Branch: `codex/reproduce-pdf-region-gold-baseline-20261112`.
Checkout: existing `DungeonMindBuddy` checkout; no additional worktree.

## Outcome

Run the repository's offline scorer against the retained five-region OCR 2
artifacts. Report classification, transcription, structure, and source location
separately. Keep the existing page-artifact input supported. Missing or
unavailable evidence must remain explicit; OCR region markers are not a typed,
reviewed candidate.

## Exclusive write set

- This handoff.
- `Docs/Plans/HANDOFF-BUILD-local-pdf-ocr-runtime.md` (settle merged #2487 and
  point to this successor).
- `evals/document_extraction_gold/score_ocr2_artifacts.py`.
- `tests/test_document_extraction_gold_scorer.py`.

## Boundaries and validation

This is offline evaluation only. It makes no provider calls, changes no source
PDFs or gold values, and does not create or publish Graph facts. The source
identity and page/region coordinates are compared with the pinned gold. When
`run.json` is present beside region artifacts, its input PDF hash must also
match; the report records the run model ID and snapshot. Field value presence
does not prove label binding or a valid statblock structure. Map visual coverage
remains unscored.

The retained run is the 2026-11-12 v3 region run, using DeepSeek OCR 2 snapshot
`aaa02f3811945a91062062994c5c4a3f4c0af2b0` and the manifest SHA recorded in
`run.json`. The old v2 report is preserved. The new scorer reports a normalized
exact prose match and 76/76 tokens; v2 reports 77/77. This denominator
discrepancy remains visible until its original tokenizer is recovered. Other
region results reproduce the retained conclusions: Conks statblock values
16/18 with no typed structure, table 10/12 exact rows with its header matched,
Sheep map emitted only an `image` marker (visual features unscored), and Sheep
statblock values 16/16 with no typed structure. All five source hashes, page
indexes, and region coordinates match the gold manifest.

Five focused scorer checks pass, including rejection of a mismatched run-manifest
source hash. The retained v3 run passes all source, page, region, and run-manifest
identity checks without provider calls. Focused commands:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p test_document_extraction_gold_scorer.py -v
PYTHONDONTWRITEBYTECODE=1 python3 -B evals/document_extraction_gold/score_ocr2_artifacts.py \
  --artifact-root conks=<retained-v3-region-run> \
  --artifact-root sheep=<retained-v3-region-run>
```

The local shell currently has no visible CUDA GPU. This slice scores retained
outputs only and does not claim a fresh OCR execution.

## Successor boundary

After this slice, the next independent capability is an ordinary Build path
from selected OCR region to the existing editable statblock review. Preserve
exact source locations, expose missing fields for author completion, and keep
DungeonMind's explicit review/admission as the only publication path. Do not
build that UI handoff in this slice.
