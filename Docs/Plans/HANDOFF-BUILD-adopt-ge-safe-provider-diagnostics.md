# HANDOFF — Adopt safe provider-failure diagnostics for PDF statblocks

Status: ACTIVE; serial; one unstacked PR.
Base: `origin/main@a86fd68a43dd9924f7a36f0266caf0254437b21d`.
Branch: `codex/adopt-ge-safe-failure-diagnostics`.
Checkout: existing `/home/drakosfire/Projects/.codex/pdf-statblock-gen-diagnosis/DungeonMindBuddy`; preserve its untracked `.venv` symlink.

## Outcome

Adopt the already-merged GenerationEngine #38 source revision
`c0060ab1f4d12ff196f835eca0e88741387f5d80` in Buddy’s exact dependency pin and
lockfile. It logs safe HTTP status and provider request ID for OpenAI-compatible
4xx failures while retaining the generic public failure code/message.

This slice enables diagnosis of the retained PDF statblock provider failure. It
does not claim to repair the provider rejection, change OCR, add retries, expose
provider text/secrets, create review drafts on failure, or publish Graph facts.

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
- Run the focused statblock failure-code tests using the existing `.venv`
  symlink, without syncing or mutating its shared target. Its installed
  GenerationEngine source is `7c929082bfa9b8c5af9815e6429db5230d9caefe`, not
  #38; these tests validate Buddy's API behavior, not the newly pinned adapter.
- `tests/test_build_pdf_statblock_extraction.py`: 23 passed in 2.43s using the
  existing `.venv` symlink; no environment sync was performed. `uv lock
  --check` resolved 152 packages and `git diff --check` passed.
- After delivery, restart only the owned 5202 service if required and retry the
  same retained Conks page-16 region through ordinary Build. Confirm the safe
  log includes status/request ID, the public failure stays generic, and no
  review or Graph publication occurs. Preserve the attempt.

## Dependencies and next boundary

GenerationEngine #38 merged as `c0060ab1f4d12ff196f835eca0e88741387f5d80`;
Buddy currently pins #37 at `c6c575cec0bc13f20cad33a2e4c0554397d9a081`.
The prior #2505 retry still reports `pdf_statblock_generation_provider_error`.
Any fix to the actual rejection requires a separate, evidence-led successor
after the safe status diagnostic is captured. Source identity/admissibility and
publication remain owned by DungeonMind.
