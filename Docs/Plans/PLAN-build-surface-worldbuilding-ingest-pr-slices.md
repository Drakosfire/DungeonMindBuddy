---
document_id: dmb-plan-build-surface-worldbuilding-ingest-pr-slices
title: Build Surface and Worldbuilding Ingest PR Slices
document_class: implementation_plan
status: draft
version: 0.1
branch: docs/build-surface-worldbuilding-ingest
roadmap: ROADMAP-build-surface-worldbuilding-ingest.md
created_at: "2026-07-22"
last_updated_at: "2026-07-22"
---

# Build Surface and Worldbuilding Ingest PR Slices

- **Status:** Branch-local PR design; logical slice IDs only
- **Roadmap:** [`ROADMAP-build-surface-worldbuilding-ingest.md`](ROADMAP-build-surface-worldbuilding-ingest.md)
- **Architecture:** [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
- **Publication boundary:** [`../Design/DESIGN-extract-promote-graph-review-bridge.md`](../Design/DESIGN-extract-promote-graph-review-bridge.md)

This document converts the Build/worldbuilding-ingest roadmap into reviewable
pull-request-sized slices. `BLD-*` identifiers are sequencing labels, not
GitHub PR numbers. A future tracker may assign actual PR numbers when this
branch-local workstream is adopted.

The slices are intentionally narrow around contracts and boundaries:

```text
BLD-00 docs
  → BLD-01 shared editor
      → BLD-02 source persistence
          → BLD-03 source artifact/run contracts
              ├→ BLD-04 generic extraction runtime ─┐
              └→ BLD-05 Build shell ────────────────┴→ BLD-06 extraction toolbar
                                                        → BLD-07 Graph Review handoff
                                                            → BLD-08 worldbuilding profile/pilot
                                                                → BLD-09 PDF/OCR pilot
```

BLD-04 and BLD-05 can be developed in parallel after BLD-03, but BLD-06 must
wait for both. BLD-08 is a content and integration proving slice, not a reason
to widen the runtime contract without tests.

## Handoff map

These handoffs use stable BLD slice identities rather than provisional GitHub
PR numbers. Assign the actual PR number when a stream opens the work.

| Slice | Handoff | Dispatch dependency |
|---|---:|---|---|
| BLD-01 | [`HANDOFF-bld01-shared-markdown-editor.md`](HANDOFF-bld01-shared-markdown-editor.md) | BLD-00 adopted |
| BLD-02 | [`HANDOFF-bld02-source-document-persistence.md`](HANDOFF-bld02-source-document-persistence.md) | BLD-01 |
| BLD-03 | [`HANDOFF-bld03-source-artifact-run-contracts.md`](HANDOFF-bld03-source-artifact-run-contracts.md) | BLD-02 |
| BLD-04 | [`HANDOFF-bld04-generic-extraction-runtime.md`](HANDOFF-bld04-generic-extraction-runtime.md) | BLD-03 |
| BLD-05 | [`HANDOFF-bld05-build-surface-shell.md`](HANDOFF-bld05-build-surface-shell.md) | BLD-01 + BLD-03 |
| BLD-06 | [`HANDOFF-bld06-build-extraction-toolbar.md`](HANDOFF-bld06-build-extraction-toolbar.md) | BLD-04 + BLD-05 |
| BLD-07 | [`HANDOFF-bld07-graph-review-generic-run-handoff.md`](HANDOFF-bld07-graph-review-generic-run-handoff.md) | BLD-06 + extract-promote bridge |
| BLD-08 | [`HANDOFF-bld08-worldbuilding-profile-pilot.md`](HANDOFF-bld08-worldbuilding-profile-pilot.md) | BLD-07 |
| BLD-09 | [`HANDOFF-bld09-pdf-ocr-lineage-pilot.md`](HANDOFF-bld09-pdf-ocr-lineage-pilot.md) | BLD-08 |

---

## Delivery rules

1. One slice should provide one independently testable capability.
2. No slice may change the active Campaign Supergraph sequencing tracker until
   this branch-local design is explicitly adopted.
3. The existing recap path remains a compatibility consumer throughout.
4. Build may create proposals and launch review; it may not commit graph heads.
5. Source writes and graph writes remain separate two-phase operations.
6. Do not edit corpus canon, eval gold, or raw ingestion artifacts as part of
   an implementation PR unless that content change is the named pilot.
7. Every slice includes focused tests and a stated command that proves its
   boundary.
8. A slice that broadens an LLM extraction call must use the Responses API
   structured-output contract and model policy; it must not add prompt-only
   JSON parsing.

---

## BLD-00 — Adopt the contracts and sequencing

- **Phase:** 0
- **Depends on:** none
- **Purpose:** Make the workstream executable without rediscovering product and
architecture decisions in each implementation PR.

### Scope

- This roadmap.
- This PR slice plan.
- A short source-artifact contract note or typed contract location if the
  implementation team requires a canonical import path.
- Explicit non-goals for Build, Ingest, Graph Review, and Plan.

### Out of scope

- Runtime behavior.
- Route or navigation changes.
- Corpus mutation.
- Eval-gold changes.
- Reordering the active Campaign Supergraph tracker.

### Acceptance

- The source artifact permits a worldbuilding source with no session.
- The run lifecycle is named: draft → prepared → extracted → validated →
  reviewable → promoted or rejected.
- Graph Review is the only governed publication owner.
- A future implementation PR can name exact files and tests without inventing
  a second world graph.

### Verification

```bash
git diff --check -- Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md \
  Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md
```

---

## BLD-01 — Extract the reusable Markdown editor

- **Phase:** 1
- **Depends on:** BLD-00
- **Purpose:** Make TipTap editor behavior reusable by Plan, Build, and future
source surfaces without changing Plan’s product behavior.

### Likely files

```text
apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx
apps/live-control-ui/src/tiptap/MarkdownEditorToolbar.tsx
apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.ts
apps/live-control-ui/src/tiptap/MarkdownEditor.tsx
apps/live-control-ui/src/tiptap/TiptapCalloutBridgeSpike.tsx
apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx
apps/live-control-ui/src/planSurface/components/*test*.tsx
apps/live-control-ui/src/tiptap/*test*.tsx
```

### Scope

- Extract common TipTap setup, local draft state, import/export, dirty state,
  and editor lifecycle callbacks.
- Make extensions and surface-specific toolbar tools injectable.
- Preserve callout and graph/runbook reference behavior.
- Convert the Spike and Plan canvas to consumers of the shared component.
- Keep source-specific save behavior in adapters/hooks.

### Out of scope

- `/build` route.
- Worldbuilding metadata.
- New graph extraction behavior.
- Expanding the Markdown writer allowlist.
- Tables, images, frontmatter, or arbitrary HTML support unless the current
  converter already supports them.

### Acceptance

- Plan and the Spike render through the shared editor.
- Existing Plan save semantics remain unchanged.
- The shared component has no Plan-session or runbook-path assumptions.
- Unsupported Markdown diagnostics remain visible to the caller.

### Verification

```bash
cd apps/live-control-ui
npm test -- --run src/planSurface/PlanSurfaceShell.test.tsx
npm test -- --run src/tiptap
npm run typecheck
npm run build
```

---

## BLD-02 — Generalize source-document persistence safely

- **Phase:** 2
- **Depends on:** BLD-01
- **Purpose:** Let Build save a source document through a server-owned, reviewable
  path policy instead of using Plan’s session-prep allowlist.

### Likely files

```text
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.ts
apps/live_control_server/services/workspace_document_registry.py
apps/live_control_server/routes/workspace_documents.py
apps/live_control_server/services/tiptap_markdown_write.py
tests/test_workspace_document_registry.py
tests/test_tiptap_markdown_write.py
```

### Scope

- Decide whether `WorkspaceDocumentRecord.kind` grows to include
  `worldbuilding` or whether a separately typed source-document registry is
  cleaner. Keep the public discriminator explicit.
- Add source-domain/document-class metadata.
- Add a server-owned safe target policy for approved worldbuilding roots.
- Preserve root containment, path normalization, backups, prepare/commit, and
  conflict detection.
- Return diagnostics for unsupported or lossy Markdown conversions.
- Keep Plan and runbook paths behaviorally compatible.

### Out of scope

- Arbitrary filesystem writes from the browser.
- Source extraction or graph mutation.
- Automatic canon promotion.
- Bulk corpus migration.

### Acceptance

- A worldbuilding source can be created and reopened by registry ID.
- Prepare/commit rejects unsafe paths and stale revisions.
- A source commit cannot silently discard unsupported Markdown structures.
- Existing plan/runbook tests remain green.

### Verification

```bash
uv run pytest tests/test_workspace_document_registry.py \
  tests/test_tiptap_markdown_write.py
cd apps/live-control-ui
npm test -- --run src/api
npm run typecheck
```

---

## BLD-03 — Introduce generic SourceArtifact and ExtractionRun contracts

- **Phase:** 3
- **Depends on:** BLD-02
- **Purpose:** Separate source identity and run identity from recap session
identity while preserving recap adapters.

### Likely files

```text
src/graph_memory/source_artifact.py
src/graph_memory/extraction_run.py
src/graph_memory/source_spans.py
src/graph_memory/provenance.py
src/graph_memory/extraction/graph_extraction_options.py
apps/live_control_server/services/source_artifact_registry.py
apps/live_control_server/services/graph_run_registry.py
apps/live_control_server/routes/graph_preview.py
apps/live_control_server/routes/workspace_documents.py
tests/test_source_artifact*.py
tests/test_graph_run_registry*.py
```

### Scope

- Define stable source-artifact identity, content digest, authority,
  visibility, temporal scope, optional campaign/session scope, and source
  lineage.
- Define a reviewable extraction-run manifest with source spans, provenance,
  candidate graph, diagnostics, validation report, and status.
- Allow `campaign_id` and `session_id` to be nullable where the source domain
  permits it.
- Add a recap adapter that maps current recap descriptors to the generic
  contract.
- Ensure all source paths are resolved server-side and remain root-contained.

### Out of scope

- Changing extraction prompts.
- Worldbuilding-specific category tuning.
- UI replacement of recap ingest.
- Graph-head mutation.

### Acceptance

- A source artifact with no session is valid.
- Existing recap preview runs still load through the adapter.
- Candidate assertions can point back to a source artifact and span.
- Run status is durable and queryable without parsing a filesystem path.

### Verification

```bash
uv run pytest tests/test_source_artifact*.py \
  tests/test_graph_run_registry*.py \
  tests/test_live_recap_ingest_graph_preview_api.py
```

---

## BLD-04 — Generalize extraction execution behind source adapters

- **Phase:** 3
- **Depends on:** BLD-03
- **Purpose:** Make extraction execution accept source artifacts and profiles
instead of requiring recap-shaped arguments.

### Likely files

```text
src/graph_memory/extraction/category_candidate_graph_extractor.py
src/graph_memory/extraction/graph_extraction_options.py
src/graph_memory/extraction/source_adapter.py
src/graph_memory/extraction/recap_source_adapter.py
src/graph_memory/extraction/worldbuilding_source_adapter.py
src/graph_memory/extraction/graph_preview_runner.py
apps/live_control_server/services/recap_graph_preview_ingest.py
apps/live_control_server/services/graph_preview_runner.py
tests/test_graph_preview_runner*.py
tests/test_category_candidate_graph_extractor*.py
```

### Scope

- Replace mandatory recap-session construction with a source-artifact
  descriptor plus an extraction profile.
- Keep recap extraction as an explicit adapter.
- Add worldbuilding source-span normalization for Markdown text.
- Preserve source anchors and provenance for every extracted assertion.
- Persist refusal/incomplete/schema diagnostics as explicit run failures.
- Resolve model IDs through model policy for any changed LLM path.

### Out of scope

- Tuning worldbuilding categories.
- PDF/OCR parsing.
- Graph Review UI.
- Direct graph publication.

### Acceptance

- Worldbuilding Markdown with `session_id = null` completes through extraction
  and validation.
- Recap behavior is regression-tested against a representative existing run.
- No adapter fabricates a session number to satisfy a legacy function.
- Structured extraction uses Responses API `text.format` with strict JSON
  schema where the runtime performs LLM extraction.

### Verification

```bash
uv run pytest tests/test_graph_preview_runner*.py \
  tests/test_category_candidate_graph_extractor*.py \
  tests/test_live_recap_ingest_graph_preview_api.py
```

---

## BLD-05 — Add the Build surface shell

- **Phase:** 4
- **Depends on:** BLD-03 and BLD-01
- **Purpose:** Create an editor-first `/build` surface that can author a
worldbuilding source even while extraction launch remains gated behind BLD-06.

### Likely files

```text
apps/live-control-ui/src/App.tsx
apps/live-control-ui/src/chrome/appChromeConfig.ts
apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx
apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx
apps/live-control-ui/src/buildSurface/buildSurfaceConfig.ts
apps/live-control-ui/src/styles.css
apps/live-control-ui/src/App.test.tsx
apps/live-control-ui/src/buildSurface/*test*.tsx
```

### Scope

- Add the `/build` route.
- Render the shared editor with source-document metadata.
- Provide new/open/save draft and save-source controls.
- Show source domain, document class, authority, visibility, and dirty/save
  state.
- Add the primary nav item only when the shell is functional and its route
  contract is tested.
- Keep the empty Play surface unchanged.

### Out of scope

- Extraction execution.
- Candidate graph rendering.
- Graph Review commit controls.
- PDF import.

### Acceptance

- Direct navigation to `/build` renders a real React surface.
- The Build surface has no Plan-session requirement.
- Source metadata is explicit and persists with the document record.
- App chrome remains consistent across Plan, Ingest, Play, and Build.

### Verification

```bash
cd apps/live-control-ui
npm test -- --run src/App.test.tsx src/buildSurface
npm run typecheck
npm run build
```

---

## BLD-06 — Add Build extraction toolbar and run handoff

- **Phase:** 4
- **Depends on:** BLD-04 and BLD-05
- **Purpose:** Let Build prepare a source artifact, launch extraction, show run
status, and open the selected run in Graph Review.

### Likely files

```text
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx
apps/live-control-ui/src/buildSurface/BuildIngestToolbar.tsx
apps/live-control-ui/src/buildSurface/useBuildExtraction.ts
apps/live-control-ui/src/buildSurface/*test*.tsx
apps/live_control_server/routes/graph_preview.py
apps/live_control_server/services/graph_run_registry.py
tests/test_graph_preview_routes.py
```

### Scope

- Add source-aware extraction options.
- Add prepare/extract/status API calls keyed by artifact/run ID.
- Show a compact lifecycle state and failures.
- Make **Open in Graph Review** the terminal action.
- Carry source artifact, run, and revision identifiers into the handoff.

### Out of scope

- Any Build-side merge or commit action.
- Automatically selecting all candidate assertions.
- A second review UI.
- Model/provider controls in the normal user-facing toolbar.

### Acceptance

- The toolbar cannot launch against an unsaved or stale source.
- A run is recoverable after page reload.
- Failure state includes a safe diagnostic and a run ID, not raw secrets or
  corpus payload logging.
- Opening Graph Review selects the exact run, not merely the latest run.

### Verification

```bash
uv run pytest tests/test_graph_preview_routes.py
cd apps/live-control-ui
npm test -- --run src/buildSurface
npm run typecheck
```

---

## BLD-07 — Generalize Graph Review run loading and publication handoff

- **Phase:** 6
- **Depends on:** BLD-06 and the existing extract-promote bridge
- **Purpose:** Make Graph Review consume generic recap and worldbuilding runs
  through one review and governed-publication path.

### Likely files

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchHeaderWithActivity.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewRunSelection.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
apps/live_control_server/routes/extract_promote.py
apps/live_control_server/services/extract_promote_ops.py
tests/test_extract_promote_ops_atomic.py
tests/test_live_extract_promote_api.py
```

### Scope

- Resolve selected runs by durable run ID and source-artifact ID.
- Display source domain, authority, temporal scope, and provenance.
- Preserve assertion-level selection and prepare/confirm semantics.
- Permit worldbuilding candidates with no session focus.
- Keep the same contribution and immutable World Graph head path.
- Add reload/durable-revision tests for the generic run.

### Out of scope

- Hermes-specific write paths.
- Automatic identity linking.
- Player-facing graph projection.
- Replacing the existing Graph Review workbench.

### Acceptance

- A worldbuilding run can be reviewed without a fake session lens.
- The final confirmation is revision-bound and explicit.
- A rejected or superseded proposal cannot advance the graph head.
- A successful commit is queryable at world focus and carries source evidence.

### Verification

```bash
uv run pytest tests/test_extract_promote_ops_atomic.py \
  tests/test_live_extract_promote_api.py
cd apps/live-control-ui
npm test -- --run src/planSurface/graphReviewWorkbench
npm run typecheck
```

---

## BLD-08 — Worldbuilding extraction profile and Shepherd’s Flock pilot

- **Phase:** 5
- **Depends on:** BLD-07
- **Purpose:** Prove that a bounded worldbuilding extraction profile works on
  real Markdown material without inventing session chronology.

### Scope

- Select a small Shepherd’s Flock source set.
- Deduplicate overlapping worldbuilding sources before extraction.
- Add bounded location, faction, NPC, creature/statblock-reference, and
  institution/governance extraction coverage.
- Run at least three repeat trials for any stochastic extraction comparison.
- Review candidates manually and record accepted/rejected reasons.
- Commit only the explicitly approved world graph contribution.
- Query the committed objects with world focus and no session ID.

### Out of scope

- Bulk ingestion of the entire corpus.
- Editing source canon as an incidental test setup.
- Treating benchmark output as durable graph truth.
- Broad ecology/resource extraction before a bounded profile exists.
- PDF/OCR parsing and page-level lineage.

### Acceptance

- Source artifact and span IDs are stable across reload.
- Candidates link to paragraph evidence.
- No session number is invented for evergreen lore.
- Duplicate source copies do not create duplicate durable identities.
- The resulting contribution is reviewable, auditable, and retractable under
  the existing graph contract.

### Verification

The exact pilot command should be recorded with the resulting run artifact, but
the minimum verification shape is:

```bash
uv run pytest tests/test_worldbuilding_extraction_profile.py \
  tests/test_worldbuilding_profile_pipeline.py
uv run python evals/graph_memory_layer/worldbuilding_profile_pilot.py \
  --trials 3
uv run pytest tests/test_extract_promote_ops_atomic.py \
  tests/test_live_extract_promote_api.py
```

Any live LLM pilot must keep full payload artifacts local, use the configured
DungeonMind environment loader, and report aggregate metrics plus run IDs
instead of pasting corpus text into review discussion.

---

## BLD-09 — PDF/OCR source lineage pilot

- **Phase:** 7
- **Depends on:** BLD-08
- **Purpose:** Prove that PDF-derived Markdown can enter the same
  source-artifact and review path without losing page provenance or creating
  duplicate identities.

### Scope

- Create a validated OCR/Markdown source artifact from one bounded PDF slice.
- Preserve PDF/page/OCR lineage in source spans and the run manifest.
- Reuse the existing RulesIngestion Mark III artifacts where possible.
- Pilot one mechanical/statblock source and review its graph candidates.
- Record aggregate outcomes and rejected candidates.

### Out of scope

- Raw PDF editing inside TipTap.
- Bulk PDF corpus ingestion.
- New mechanical rules semantics.
- Broad statblock authoring or combat integration.

### Acceptance

- PDF-derived candidates link to stable page evidence.
- OCR/Markdown validation failures are explicit and review-blocking.
- Duplicate PDF/Markdown copies do not create duplicate durable identities.
- The approved contribution uses the same Graph Review publication path as
  worldbuilding Markdown.

### Verification

The exact pilot command must be recorded with the resulting run artifact:

```bash
uv run pytest tests/test_source_artifact_pdf_lineage.py \
  tests/test_graph_run_registry_pdf_lineage.py \
  tests/test_extract_promote_ops_atomic.py \
  tests/test_live_extract_promote_api.py
uv run python evals/graph_memory_layer/pdf_lineage_pilot.py --trials 3
```

Any live LLM pilot must keep full payload artifacts local, use the configured
DungeonMind environment loader, and report aggregate metrics plus run IDs
instead of pasting corpus text into review discussion.

---

## Cross-slice file and ownership guardrails

### Do not combine casually

- Editor extraction and extraction-runtime generalization are separate review
  concerns.
- Source persistence and graph publication are separate write paths.
- Worldbuilding profile tuning and PDF/OCR ingestion are separate evidence
  questions.
- UI route work and durable graph contract work should not be hidden in one
  “Build surface” PR.

### Compatibility obligations

- Plan continues to save its current document type.
- Ingest Recap continues to load current recap runs.
- Graph Review continues to use the existing governed publication APIs.
- Build must remain unusable for direct graph publication.
- The empty Play surface remains an intentional stub until its own roadmap.

### Documentation follow-up when adopted

When this branch-local design is accepted for execution:

1. create the corresponding workstream checklist/tracker;
2. copy the `BLD-*` sequence into that tracker;
3. record the active phase and next verification command;
4. assign actual GitHub PR numbers only after slices are opened;
5. update the roadmap and tracker atomically after each accepted slice.
