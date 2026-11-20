# HANDOFF — Adopt safe provider-failure diagnostics for PDF statblocks

Status: ACTIVE; serial; one unstacked PR.
Base: `origin/main@a86fd68a43dd9924f7a36f0266caf0254437b21d`.
Branch: `codex/adopt-ge-safe-failure-diagnostics`.
Checkout: existing `/home/drakosfire/Projects/.codex/pdf-statblock-gen-diagnosis/DungeonMindBuddy`; preserve its untracked `.venv` symlink.

## Outcome

Pin GenerationEngine #39 at `ab511c8a35bd3a76aecb7cb5b9d8b549fcbbbc2f`.
It projects supported tagged unions for OpenAI and includes the safe HTTP status
and request ID diagnostics from #38. The public failure remains generic.

## Write lease

- `pyproject.toml`
- `uv.lock`
- This handoff.
- `HANDOFF-BUILD-pdf-region-gold-scorer.md` to settle merged #2489 and keep
  the retained-artifact baseline distinct from a fresh OCR run.
- `HANDOFF-BUILD-pdf-statblock-generation-diagnosis.md` to settle merged #2505
  and record the still-failing ordinary Build retry.

No provider configuration, source PDF, gold artifact, review-storage, frontend,
DungeonMind publication, or retained runtime data changes.

## Verification

- `uv lock --check` confirms the exact dependency pin and lock agree (152
  packages resolved).
- Inspect the complete base-to-head diff and confirm no other dependency moved.
- 23 focused extraction tests passed using the existing shared environment
  with the GenerationEngine source checkout on PYTHONPATH. The installed
  dependency in the delivery runtime still needs verification.
- Retry the retained Conks page-16 region on 5202 and verify the proposal,
  exact source region, and review controls. Preserve prior failed attempts.

## Dependencies and next boundary

GenerationEngine #38 supplied safe diagnostics. The preserved Conks attempt
returned HTTP 400 with `pdf_statblock_generation_provider_error`. A synthetic
comparison confirmed OpenAI rejects `oneOf`; #39 fixes that request shape.
DungeonMind owns source identity, admission, and publication.
