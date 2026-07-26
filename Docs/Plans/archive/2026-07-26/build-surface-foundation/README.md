# Build surface foundation archive — 2026-07-26

This directory preserves the full historical Build/worldbuilding authoring workstream
documents that established the current product foundation. They are retained verbatim
for design lineage and review archaeology, but they are no longer active sequencing
authority.

Current authority:

- `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`
- `Docs/Plans/PLAN-shared-markdown-canvas-build-first.md`
- `Docs/Plans/HANDOFF-pr426-build-first-markdown-canvas.md`
  (a forwarding stub remains at the mistaken `HANDOFF-pr425-…` path)

The parent Surface composition authority remains
`Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`.

## Outcome map

| Historical document | Outcome |
|---|---|
| `ROADMAP-build-surface-worldbuilding-ingest.md` | Adopted as PR #382; foundational design now implemented through later BLD slices |
| `PLAN-build-surface-worldbuilding-ingest-pr-slices.md` | Historical BLD sequence and judgment ledger |
| `HANDOFF-bld01-shared-markdown-editor.md` | Shared editor landed in PR #383 |
| `HANDOFF-bld02-source-document-persistence.md` | Worldbuilding workspace persistence landed in PR #384 |
| `HANDOFF-bld03-source-artifact-run-contracts.md` | SourceArtifact/ExtractionRun contracts landed in PR #385 |
| `HANDOFF-bld04-generic-extraction-runtime.md` | Generic extraction runtime landed in PR #391 |
| `HANDOFF-bld05a-workspace-document-authoring-seam.md` | Shared authoring seam landed in PR #399 |
| `HANDOFF-bld05a-post-merge-authoring-hardening.md` | Lifecycle hardening landed in PR #401 |
| `HANDOFF-bld05-build-surface-shell.md` | Superseded draft #390; thin Build consumer shipped through #399/#401 |
| `HANDOFF-bld06-build-extraction-toolbar.md` | Exact Build extraction/handoff landed in PR #392 |
| `HANDOFF-bld07-graph-review-generic-run-handoff.md` | Exact-run Graph Review binding landed in PR #393 |
| `HANDOFF-bld08-worldbuilding-profile-pilot.md` | Bounded worldbuilding profile landed in PR #394 |
| `HANDOFF-bld10a-worldbuilding-write-plan-prepare.md` | Deterministic worldbuilding write-plan prepare landed in PR #411 |
| `HANDOFF-pr415-bld10b-worldbuilding-write-plan-confirm.md` | Verified write-plan commit landed in PR #415 |

## Intentionally not archived

- `HANDOFF-bld09-pdf-ocr-lineage-pilot.md` remains an independent active/open
  workstream.
- BLD-10c has not been dispatched.
- Current Build-first canvas/component work lives at the current authority paths above.

Short forwarding files remain at the former root paths so historical links do not
silently break.

## Navigability repair

Historical files were moved under this archive directory. Relative links that previously
targeted `Docs/Design/` via `../Design/...` from `Docs/Plans/` were rewritten to
`../../../../Design/...` so the archived copies remain navigable. Prefer navigability
over byte-identical Markdown when relocating design archaeology.
