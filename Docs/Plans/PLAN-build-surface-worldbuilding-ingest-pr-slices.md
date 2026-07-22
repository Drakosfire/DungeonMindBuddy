---
document_id: dmb-plan-build-surface-worldbuilding-ingest-pr-slices
title: Build Surface and Worldbuilding Ingest PR Slices
document_class: implementation_plan
status: proposed
version: 0.2
branch: docs/build-surface-worldbuilding-ingest
roadmap: ROADMAP-build-surface-worldbuilding-ingest.md
created_at: "2026-07-22"
last_updated_at: "2026-07-22"
---

# Build Surface and Worldbuilding Ingest PR Slices

- **Status:** Proposed sequence; logical slice IDs only.
- **Roadmap:** [`ROADMAP-build-surface-worldbuilding-ingest.md`](ROADMAP-build-surface-worldbuilding-ingest.md)
- **Architecture:** [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
- **Surface architecture:** [`../Design/ARCHITECTURE-plan-surface-toolbox.md`](../Design/ARCHITECTURE-plan-surface-toolbox.md)
- **Workspace identity:** [`../Design/CONTRACT-workspace-document-identity-v1.md`](../Design/CONTRACT-workspace-document-identity-v1.md)
- **Publication boundary:** [`../Design/DESIGN-extract-promote-graph-review-bridge.md`](../Design/DESIGN-extract-promote-graph-review-bridge.md)

`BLD-*` identifiers are stable sequencing labels, not GitHub PR numbers.

**PREPARED / DRAFT:** a slice may be implemented as a stacked draft PR against
the predecessor head before that predecessor merges.

**ACTIVE / MERGEABLE:** only after predecessor merge, tracker adoption, rebase
onto the immutable merge SHA, and handoff re-anchor. This plan’s merge authority
begins only after PR 382 merges and BLD-01 is promoted under that gate.

```text
BLD-00 docs adoption
  → BLD-01 shared editor
      → BLD-02 worldbuilding workspace persistence
          → BLD-03 canonical source/run contract graduation
              ├→ BLD-04 generic extraction runtime + profile protocol ─┐
              └→ BLD-05 configured Build surface ─────────────────────┴→ BLD-06 extraction controls
                                                                         → BLD-07 generic Graph Review binding
                                                                             → BLD-08 worldbuilding profile/pilot
                                                                                 → BLD-09 PDF/OCR lineage pilot
```

BLD-04 and BLD-05 may proceed in parallel after BLD-03. BLD-06 waits for both.

---

## 1. Delivery rules

1. Each slice delivers one independently useful capability and records why its
   changed layers share one invariant.
2. Handoffs may be **PREPARED / DRAFT** (stacked implementation against a
   predecessor head) before predecessors merge. They become
   **ACTIVE / MERGEABLE** only after the predecessor merge SHA is recorded,
   the branch is rebased onto that SHA, and the handoff is re-anchored.
   Draft implementation PRs must stay draft until that gate clears.
3. Workspace document IDs, SourceArtifact IDs, ExtractionRun IDs,
   GraphContribution IDs, proposal digests, and graph revisions remain distinct.
4. Existing contracts are graduated or adapted; no parallel source, evidence,
   span, run, projection, or promotion authority may be created.
5. Build reuses the shared Surface and Agent Interaction architecture.
6. Build may author sources and launch extraction; only Graph Review may prepare
   and confirm graph publication.
7. Source writes and graph writes remain separate revision-bound operations.
8. Recap ingest remains an explicit compatibility adapter and profile.
9. Exact run IDs replace latest-run inference on every Build/Graph Review path.
10. LLM extraction uses Responses API structured output and model policy; no
    prompt-only JSON parsing or hidden default profile is permitted.
11. Each acceptance guarantee names a command at the boundary that owns it.
12. No implementation PR may mutate corpus canon, eval gold, or raw source
    artifacts unless the pilot itself is the named capability.

---

## 2. Handoff map

| Slice | Handoff | Dispatch dependency |
|---|---|---|
| BLD-01 | [`HANDOFF-bld01-shared-markdown-editor.md`](HANDOFF-bld01-shared-markdown-editor.md) | BLD-00 adopted and tracker synced |
| BLD-02 | [`HANDOFF-bld02-source-document-persistence.md`](HANDOFF-bld02-source-document-persistence.md) | BLD-01 |
| BLD-03 | [`HANDOFF-bld03-source-artifact-run-contracts.md`](HANDOFF-bld03-source-artifact-run-contracts.md) | BLD-02 |
| BLD-04 | [`HANDOFF-bld04-generic-extraction-runtime.md`](HANDOFF-bld04-generic-extraction-runtime.md) | BLD-03 |
| BLD-05 | [`HANDOFF-bld05-build-surface-shell.md`](HANDOFF-bld05-build-surface-shell.md) | BLD-01 + BLD-02 + BLD-03 |
| BLD-06 | [`HANDOFF-bld06-build-extraction-toolbar.md`](HANDOFF-bld06-build-extraction-toolbar.md) | BLD-04 + BLD-05 |
| BLD-07 | [`HANDOFF-bld07-graph-review-generic-run-handoff.md`](HANDOFF-bld07-graph-review-generic-run-handoff.md) | BLD-06 + current extract-promote bridge |
| BLD-08 | [`HANDOFF-bld08-worldbuilding-profile-pilot.md`](HANDOFF-bld08-worldbuilding-profile-pilot.md) | BLD-07 |
| BLD-09 | [`HANDOFF-bld09-pdf-ocr-lineage-pilot.md`](HANDOFF-bld09-pdf-ocr-lineage-pilot.md) | BLD-08 |

---

## BLD-00 — Adopt contracts and sequencing

**Capability:** make the Build workstream executable without rediscovering
identity, Surface, profile, and publication decisions.

### Scope

- Adopt the roadmap and this slice plan.
- Record the distinct WorkspaceDocument → SourceArtifact revision lineage.
- Bind BLD work to established graph evidence/run packages.
- Bind Build to the shared Surface architecture.
- Bind generic extraction to a versioned profile protocol.
- Bind publication to existing `src/graph_memory/extract_promote_ops.py` and the
  Graph Review confirmation surface.

### Acceptance

- No implementation handoff remains ambiguous about identity ownership.
- No handoff names a duplicate or nonexistent graph authority.
- BLD-01 can be PREPARED as a stacked draft against this docs head and becomes
  ACTIVE/MERGEABLE only from the immutable BLD-00 merge SHA after rebase.
- BLD-02 through BLD-09 may be PREPARED as stacked drafts but remain
  non-mergeable until their predecessor gates clear.

### Verification

```bash
git diff --check -- Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md \
  Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md \
  Docs/Plans/HANDOFF-bld*.md
```

---

## BLD-01 — Extract the reusable Markdown editor

**Capability:** Plan and the TipTap bridge use one surface-neutral editor while
preserving their existing product behavior.

### Likely files

```text
apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx
apps/live-control-ui/src/tiptap/MarkdownEditorToolbar.tsx
apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.ts
apps/live-control-ui/src/tiptap/MarkdownEditor.tsx
apps/live-control-ui/src/tiptap/TiptapCalloutBridgeSpike.tsx
apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx
focused TipTap and Plan tests
```

### Scope

- Extract common TipTap setup, lifecycle, import/export, dirty state, and
  extension/tool injection.
- Keep document identity, persistence, and surface tools in adapters.
- Preserve callout and reference behavior.

### Out of scope

- Build route or source metadata.
- Writer allowlist changes.
- New Markdown syntax support.
- Graph extraction or publication.

### Acceptance / verification

```bash
cd apps/live-control-ui
npm test -- --run src/tiptap
npm test -- --run src/planSurface
npm run typecheck
npm run build
```

---

## BLD-02 — Persist worldbuilding workspace documents safely

**Capability:** a caller can create, classify, commit, reopen, discard, and
restore a `worldbuilding_source` workspace document through the existing
server-owned UUID registry and two-phase writer.

### Locked identity decision

- Extend the workspace document contract with explicit
  `kind: worldbuilding_source` and typed source metadata.
- Preserve opaque server-issued workspace UUID identity.
- Do not create a SourceArtifact during draft editing.
- A later committed revision creates a distinct SourceArtifact linked by
  `workspace_document_id + workspace_document_revision + content_sha256`.
- Update `CONTRACT-workspace-document-identity-v1.md` in this slice.

### Likely files

```text
Docs/Design/CONTRACT-workspace-document-identity-v1.md
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.ts
apps/live_control_server/services/workspace_document_registry.py
apps/live_control_server/routes/workspace_documents.py
apps/live_control_server/services/tiptap_markdown_write.py
tests/test_workspace_document_registry.py
tests/test_tiptap_markdown_write.py
apps/live-control-ui/src/api/liveApi.test.ts
```

### Scope

- Add explicit domain/class/authority/visibility metadata.
- Add server-owned safe target policy for approved worldbuilding roots.
- Preserve revision CAS, backup, root containment, discard/restore, and
  prepare/commit behavior.
- Block lossy Markdown commit.
- Keep plan/runbook behavior compatible.

### Out of scope

- SourceArtifact or ExtractionRun creation.
- Extraction and graph mutation.
- Arbitrary filesystem paths from the browser.

### Acceptance / verification

```bash
uv run pytest tests/test_workspace_document_registry.py \
  tests/test_tiptap_markdown_write.py
cd apps/live-control-ui
npm test -- --run src/api/liveApi.test.ts
npm run typecheck
```

---

## BLD-03 — Graduate canonical SourceArtifact and ExtractionRun contracts

**Capability:** a committed workspace revision can be represented by the
existing graph evidence authorities and participate in a source-domain-neutral,
durable exact-run contract while old recap manifests remain readable through an
explicit adapter.

### Existing authorities to evolve

```text
src/graph_memory/evidence/source_artifact.py
src/graph_memory/source_span.py
src/graph_memory/ingestion/graph_ingest_run.py
```

A canonical `src/graph_memory/ingestion/extraction_run.py` may be introduced.
If introduced, `graph_ingest_run.py` becomes the recap/legacy adapter or loader;
it may not remain a competing canonical run contract.

### Likely files

```text
src/graph_memory/evidence/source_artifact.py
src/graph_memory/evidence/__init__.py
src/graph_memory/source_span.py
src/graph_memory/ingestion/extraction_run.py
src/graph_memory/ingestion/graph_ingest_run.py
src/graph_memory/ingestion/__init__.py
apps/live_control_server/services/source_artifact_registry.py
apps/live_control_server/services/graph_run_registry.py
apps/live_control_server/routes/graph_preview.py
apps/live_control_server/routes/workspace_documents.py
focused source, span, run, registry, and recap-compatibility tests
```

### Scope

- Define immutable SourceArtifact revision lineage, digest, authority,
  visibility, optional campaign/session scope, and explicit workspace foreign
  keys.
- Define exact ExtractionRun identity, lifecycle, components, diagnostics,
  supersession, and reload behavior.
- Reuse/evolve the existing source-span/evidence contract.
- Adapt existing recap manifests without latest-run or path-derived identity.

### Out of scope

- Extraction execution or prompt changes.
- Build UI.
- Graph Review UI or graph-head mutation.
- New top-level `source_artifact.py`, `source_spans.py`, or `provenance.py`
  authorities.

### Acceptance / verification

```bash
uv run pytest tests/test_source_artifact.py \
  tests/test_extraction_run.py \
  tests/test_graph_run_registry.py \
  tests/test_live_recap_ingest_graph_preview_api.py
```

---

## BLD-04 — Generalize extraction execution and profile selection

**Capability:** recap and sessionless worldbuilding SourceArtifacts can run
through one production extraction controller using explicit source adapters and
versioned extraction profiles.

### Profile protocol decision

A profile owns or references enabled passes, pass instructions/templates,
structured-output schemas, vocabulary/context policy, domain defaults, and
post-validation. BLD-04 extracts current recap semantics into an explicit recap
profile without tuning them.

### Likely files

```text
src/graph_memory/extraction/extraction_profile.py
src/graph_memory/extraction/recap_extraction_profile.py
src/graph_memory/extraction/source_adapter.py
src/graph_memory/extraction/recap_source_adapter.py
src/graph_memory/extraction/worldbuilding_source_adapter.py
src/graph_memory/extraction/category_candidate_graph_extractor.py
src/graph_memory/extraction/graph_extraction_options.py
src/graph_memory/extraction/graph_preview_runner.py
apps/live_control_server/services/graph_preview_runner.py
apps/live_control_server/services/recap_graph_preview_ingest.py
focused adapter, profile, extractor, controller, and recap regression tests
```

### Scope

- Parameterize current extractor behavior through the profile protocol.
- Add recap and generic worldbuilding source adapters.
- Keep worldbuilding profile semantics minimal until BLD-08.
- Preserve source spans and explicit refusal/incomplete/schema/validation
  failures.
- Keep production code out of `evals/`.

### Out of scope

- Worldbuilding category tuning.
- PDF/OCR.
- Graph Review or publication.

### Acceptance / verification

```bash
uv run pytest tests/test_source_adapters.py \
  tests/test_extraction_profiles.py \
  tests/test_category_candidate_graph_extractor.py \
  tests/test_graph_preview_runner.py \
  tests/test_graph_memory_category_graph_preview_runner.py
```

---

## BLD-05 — Add Build as a configured shared Surface

**Capability:** `/build` provides source authoring through the shared Surface,
editor, AppChrome, theme, projection, and Agent Interaction architecture.

### Architecture constraint

`BuildSurfacePage` supplies Build configuration and adapters. Any
`BuildSurfaceShell` is a thin wrapper around the existing shared `SurfaceShell`.
No second projection registry, adaptive container, edit stack, navigation
system, theme system, or Agent Interaction provider may be created.

### Likely files

```text
apps/live-control-ui/src/App.tsx
apps/live-control-ui/src/chrome/appChromeConfig.ts
apps/live-control-ui/src/surfaces/* shared config/type files when required
apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx
apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx
apps/live-control-ui/src/buildSurface/buildSurfaceConfig.ts
apps/live-control-ui/src/buildSurface/*test*.tsx
apps/live-control-ui/src/App.test.tsx
shared styles/tokens only when required
```

### Scope

- Add `/build` and one primary navigation item.
- Reuse shared editor and source-document API.
- Show explicit source metadata, dirty/save/conflict state, and exact document
  reload.
- Preserve other surfaces and the single app-level continuity host.

### Out of scope

- Extraction controls.
- Candidate review or publication.
- New backend capability.

### Acceptance / verification

```bash
cd apps/live-control-ui
npm test -- --run src/App.test.tsx src/buildSurface src/planSurface
npm run typecheck
npm run build
```

---

## BLD-06 — Add Build extraction controls and exact-run handoff

**Capability:** Build can prepare a committed source revision, launch one exact
ExtractionRun, recover status after refresh, and open that exact run in Graph
Review.

### Scope

- Bind launch to document ID, committed revision/digest, SourceArtifact ID, and
  explicit profile.
- Recover exact run ID; never select “latest”.
- Show safe diagnostics and lifecycle.
- Make **Open in Graph Review** the terminal action.

### Out of scope

- Build-side prepare/confirm publication.
- A second review panel.
- Model/provider controls in ordinary UI.

### Acceptance / verification

```bash
uv run pytest tests/test_graph_preview_routes.py
cd apps/live-control-ui
npm test -- --run src/buildSurface
npm run typecheck
```

---

## BLD-07 — Bind generic runs to the existing Graph Review publication path

**Capability:** Graph Review loads exact recap or worldbuilding runs and uses
the existing revision-bound Kernel prepare/confirm path.

### Ownership constraint

Shared publication ops remain in:

```text
src/graph_memory/extract_promote_ops.py
```

The HTTP boundary remains:

```text
apps/live_control_server/routes/extract_promote.py
```

There is no `apps/live_control_server/services/extract_promote_ops.py` authority.
Any changes to Kernel contribution or identity semantics are a stop condition.

### Likely files

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/*
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
apps/live_control_server/routes/extract_promote.py
src/graph_memory/extract_promote_ops.py only if generic run binding cannot be expressed through existing input adapters
focused workbench, selection, route, atomicity, and exact-reload tests
```

### Scope

- Select exact run/source/revision IDs.
- Adapt generic evidence into the existing review package.
- Preserve assertion-level selection and explicit confirm.
- Permit null session focus.
- Reload the exact committed graph revision and distinguish commit success from
  read degradation.

### Out of scope

- New promotion service or write protocol.
- Automatic identity linking.
- Build commit controls.
- Hermes-specific writes.

### Acceptance / verification

```bash
uv run pytest tests/test_extract_promote_ops_atomic.py \
  tests/test_live_extract_promote_api.py
cd apps/live-control-ui
npm test -- --run src/planSurface/graphReviewWorkbench
npm run typecheck
```

---

## BLD-08 — Add a bounded worldbuilding extraction profile and pilot

**Capability:** an explicit versioned worldbuilding profile produces bounded,
source-evidenced Shepherd’s Flock candidates without fabricated chronology or
incidental taxonomy explosion.

### Scope

- Add a profile implementation through BLD-04’s protocol.
- Own worldbuilding pass/category bounds, instructions/templates, schema IDs,
  vocabulary policy, and post-validation.
- Cover bounded location, faction, NPC, creature/statblock-reference, and
  institution/governance extraction.
- Run at least three comparable trials.
- Record redacted aggregate findings and manually accepted/rejected reasons.
- Publish only through Graph Review.

### Likely files

```text
src/graph_memory/extraction/worldbuilding_extraction_profile.py
tests/test_worldbuilding_extraction_profile.py
tests/test_worldbuilding_profile_pipeline.py
evals/graph_memory_layer/worldbuilding_profile_pilot.py
evals/graph_memory_layer/fixtures/worldbuilding_profile_fixture.json
Docs/Reports/REPORT-build-worldbuilding-profile-pilot.md
```

If the profile protocol cannot express the required prompt/schema behavior,
stop and fix BLD-04’s contract rather than editing unrelated prompt files
opportunistically.

### Out of scope

- Bulk corpus ingestion.
- Ecology/resource expansion.
- PDF/OCR.
- Automatic promotion.

### Acceptance / verification

```bash
uv run pytest tests/test_worldbuilding_extraction_profile.py \
  tests/test_worldbuilding_profile_pipeline.py
uv run python evals/graph_memory_layer/worldbuilding_profile_pilot.py --trials 3
```

---

## BLD-09 — Prove PDF/OCR source lineage

**Capability:** one bounded PDF and its validated OCR/Markdown derivation enter
the same source/run/review path with stable page evidence and no duplicate
durable identity.

### Scope

- Register original PDF identity and a distinct derived OCR artifact.
- Preserve PDF/page/region lineage in spans and run components.
- Reuse existing RulesIngestion artifacts where reliable.
- Pilot one bounded mechanical/statblock source.
- Report redacted aggregate outcomes.

### Out of scope

- Raw PDF editing in TipTap.
- Bulk PDF ingestion.
- New mechanical semantics.
- Combat integration.

### Acceptance / verification

```bash
uv run pytest tests/test_source_artifact_pdf_lineage.py \
  tests/test_graph_run_registry_pdf_lineage.py \
  tests/test_extract_promote_ops_atomic.py \
  tests/test_live_extract_promote_api.py
uv run python evals/graph_memory_layer/pdf_lineage_pilot.py --trials 3
```

---

## 3. Cross-slice ownership guardrails

- Editor extraction and extraction-runtime graduation remain separate.
- Workspace persistence and immutable SourceArtifact creation remain distinct
  lifecycle transitions even when one API workflow connects them.
- Source persistence and graph publication remain separate write systems.
- Build route work does not create graph contracts.
- Profile tuning does not silently rewrite the generic runtime.
- PDF lineage does not widen into bulk ingestion.
- Plan continues to save its current document type.
- Recap ingest continues to load recap runs through explicit adapters/profiles.
- Graph Review continues to use the existing governed publication APIs.
- Build contains no graph prepare/confirm control.
- Play remains outside this workstream.

---

## 4. Adoption follow-up

After PR 382 merges:

1. update the active tracker with BLD-00 through BLD-09;
2. record the PR 382 merge SHA;
3. activate only BLD-01;
4. leave all successor handoffs DRAFT;
5. assign actual PR numbers when branches open;
6. sync tracker, judgment, and handoff status atomically after each merge.
