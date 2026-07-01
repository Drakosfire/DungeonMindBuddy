---
document_id: dmb-plan-graph-review-workbench-pr-stack
title: "PLAN — Graph Review Workbench PR stack"
document_class: plan
status: draft implementation plan
created_at: "2026-07-01"
last_updated_at: "2026-07-01"
related:
  - Docs/Design/DESIGN-graph-review-workbench-roadmap.md
  - apps/live-control-ui/src/planSurface/graphGoldReview/
  - apps/live-control-ui/src/planSurface/graphPreview/
  - apps/live-control-ui/src/planSurface/manualReview/
  - apps/live_control_server/routes/graph_preview.py
  - apps/live_control_server/services/graph_gold_review.py
  - apps/live_control_server/services/graph_ingest_run_registry.py
  - apps/live_control_server/services/graph_manual_review.py
---

# PLAN — Graph Review Workbench PR stack

## 1. Stack thesis

Build Graph Review Workbench as a sequence of reviewable PRs that each improve the product while reducing duplication.

The stack should avoid a big-bang rewrite. Each PR should either:

1. Introduce a shared contract.
2. Move an existing capability into a reusable component.
3. Add one new workbench mode.
4. Retire or hide an older duplicate surface after parity.

The early PRs intentionally keep old routes and tools alive. Cleanup happens as parity is reached, not before.

## 2. Branching model

Recommended long-running umbrella branch:

```text
feature/graph-review-workbench
```

Recommended PR branches:

```text
feature/grw-00-docs-and-boundary
feature/grw-01-lane-contracts
feature/grw-02-run-metadata
feature/grw-03-workbench-shell
feature/grw-04-projection-reader-extraction
feature/grw-05-single-lane-projection
feature/grw-06-contextual-deltas
feature/grw-07-pill-overlays-inspector
feature/grw-08-split-projection-view
feature/grw-09-provenance-adapters
feature/grw-10-variant-comparison
feature/grw-11-trends-and-regression-memory
feature/grw-12-surface-retirement
```

Use smaller branches if a PR starts mixing backend contracts, frontend rendering, and fixture changes.

## 3. PR sequencing overview

| PR | Name | Primary outcome | Risk |
|---|---|---|---|
| 00 | Docs and boundary | Align on read-only workbench goal | Low |
| 01 | Lane contracts | Shared lane vocabulary exists | Low-medium |
| 02 | Run metadata | Variant runs become legible | Medium |
| 03 | Workbench shell | New tool shell can select lanes and show current metrics | Medium |
| 04 | Projection reader extraction | Existing TipTap graph reader becomes reusable | Medium-high |
| 05 | Single-lane projection | Workbench can render one selected projection over source Markdown | Medium |
| 06 | Contextual deltas | Backend emits source/object delta annotations | High |
| 07 | Pill overlays and inspector | Inline graph pills show diff status | High |
| 08 | Split projection view | Gold/live or baseline/variant side-by-side review | Medium-high |
| 09 | Provenance adapters | Manual/Vocabulary Review becomes Workbench provenance | High |
| 10 | Variant comparison | Vocabulary/profile experiments become normal lanes | High |
| 11 | Trends and regression memory | Metrics become longitudinal smoke alarms | Medium |
| 12 | Surface retirement | Duplicate graph review surfaces are hidden/retired | Medium |

## 4. PR 00 — Docs and boundary

Suggested title:

```text
docs(graph): define Graph Review Workbench roadmap
```

Goal:

Capture the product thesis, read-only boundary, source hierarchy, and phased roadmap.

Expected changes:

- Add `Docs/Design/DESIGN-graph-review-workbench-roadmap.md`.
- Add this PR stack plan.
- Do not change runtime code.

Acceptance:

- The docs clearly say Graph Review Workbench is read-only.
- The docs identify Graph Gold Review, Graph Preview, and Manual/Vocabulary Review as source components for consolidation.
- The docs say Party Registry remains separate.
- The docs establish that graph ingestion should be reviewed as projected reading behavior over source text.

Tests:

- No runtime tests required.
- Markdown/frontmatter should follow repo conventions.

Cleanup:

- None yet.

## 5. PR 01 — Lane contracts

Suggested title:

```text
feat(graph-review): add lane contract types
```

Goal:

Introduce a shared concept of comparable review lanes without changing behavior.

Expected backend changes:

- Add backend models, likely in a new service module:

```text
apps/live_control_server/services/graph_review_lanes.py
```

- Define models for:
  - `GraphReviewLane`
  - `GraphReviewLaneRole`
  - `GraphReviewLaneSourceKind`
  - `GraphReviewLaneCounts`
  - `GraphReviewLaneMetadata`

Expected frontend changes:

- Add frontend types, likely in:

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/types.ts
```

or, if shared API contracts belong there:

```text
apps/live-control-ui/src/api/types.ts
```

- Do not render a new workbench yet unless it is only a stub.

Acceptance:

- Backend and frontend have aligned lane vocabulary.
- Gold fixtures, live manifests, manual review artifacts, and projection payloads can be represented as lane source kinds.
- No existing routes change behavior.

Tests:

- Add lightweight backend model tests if model validation is non-trivial.
- Typecheck frontend.

Cleanup:

- None beyond naming consistency.

Notes:

This PR should be intentionally boring. Its job is to give later PRs language.

## 6. PR 02 — Run metadata enrichment

Suggested title:

```text
feat(graph-review): expose graph ingest run metadata for lane selection
```

Goal:

Make live and variant runs distinguishable in the UI.

Expected backend changes:

- Extend `GraphIngestRunSummary` with optional metadata:
  - extraction profile
  - extraction mode
  - vocabulary flags / vocabulary mode
  - model/provider when present
  - runner options summary
  - diagnostics summary
  - preview-union availability
  - human-readable run label

- Source metadata from graph-ingest manifest diagnostics and source fields where available.

Expected frontend changes:

- Extend API types for graph-ingest run summaries.
- Render the new fields wherever existing run pickers display runs, if low-risk.

Acceptance:

- A reviewer can tell baseline, vocabulary, dynamic vocabulary, profile, and rerun variants apart when metadata exists.
- Missing metadata is tolerated and displayed as unknown, not as failure.
- Existing Graph Gold Review and Graph Preview still work.

Tests:

- Backend unit test for manifest summary with metadata present.
- Backend unit test for manifest summary with metadata absent.
- Frontend typecheck.

Cleanup:

- Avoid adding session-specific UI logic.
- Do not expand the session-23 vocabulary special case.

## 7. PR 03 — Workbench shell

Suggested title:

```text
feat(graph-review): add initial Workbench shell
```

Goal:

Create the first visible Graph Review Workbench tool while preserving Graph Gold Review.

Expected frontend changes:

- Add module folder:

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/
```

- Add:
  - `GraphReviewWorkbenchModule.tsx`
  - `GraphReviewLanePicker.tsx`
  - `GraphReviewRunCards.tsx`
  - `GraphReviewMetricPanel.tsx`

- Add a plan-surface tool entry for Graph Review Workbench.
- Reuse existing Graph Gold Review data where possible.
- Show campaign/session selection.
- Show gold lane selection.
- Show one live lane selection.
- Show lane metadata cards.
- Show existing scorecard/miss tables in a secondary metrics panel.

Expected backend changes:

- Either reuse existing gold-review endpoints or add a thin workbench endpoint that wraps them.
- Avoid introducing a second comparison implementation.

Acceptance:

- Workbench appears in the plan surface.
- A reviewer can select one campaign/session and one live run.
- Existing gold-vs-live metrics are visible.
- The Workbench does not write corpus or graph memory.
- Graph Gold Review still works.

Tests:

- Frontend typecheck.
- Add component smoke test if existing test setup supports it.
- Backend route tests only if a new endpoint is added.

Cleanup:

- Extract shared picker/card components if Graph Gold Review and Workbench would otherwise duplicate them.
- Do not remove old Graph Gold Review yet.

## 8. PR 04 — Projection reader extraction

Suggested title:

```text
refactor(graph-review): extract reusable projected source reader
```

Goal:

Turn the existing Union Supergraph recap projection reader into a generic, reusable read-only source projection component.

Expected frontend changes:

- Extract from Graph Preview into Workbench-friendly components:

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/projection/ProjectedSourceReader.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/projection/sourceSpanHighlighting.ts
```

- Extract or generalize graph-node runtime state.
- Keep `GraphNodeReferenceNode` behavior stable.
- Keep hover cards and explorer behavior stable.
- Keep Graph Preview working through a wrapper.

Acceptance:

- Graph Preview renders the same as before.
- The generic reader can render Markdown, node views, source spans, active node, and selected evidence span.
- Source-span highlighting behavior is preserved.

Tests:

- Frontend typecheck.
- Manual smoke: Graph Preview still opens a session projection.
- Manual smoke: selecting evidence still highlights the source paragraph.

Cleanup:

- Remove Graph Preview-specific names from generic utilities.
- Avoid creating a second Tiptap rendering implementation.

Risk:

Medium-high. This touches working UI. Keep the PR pure refactor where possible.

## 9. PR 05 — Single-lane projection in Workbench

Suggested title:

```text
feat(graph-review): render selected projection lane over source Markdown
```

Goal:

Make the Workbench show one selected live/projection lane in context.

Expected backend changes:

- Ensure the Workbench can load a projection payload for a selected lane.
- Reuse existing union-supergraph projection endpoint if possible.
- If needed, add a thin workbench projection endpoint that accepts a lane reference and returns projected source review payload.

Expected frontend changes:

- Render `ProjectedSourceReader` inside Workbench.
- Add a view switch:
  - Metrics
  - Projection
- Preserve node explorer behavior.
- Preserve evidence-span selection.

Acceptance:

- A reviewer can choose a run and read its graph projection over the source recap inside the Workbench.
- The current metrics panel remains available.
- No diff overlays yet.

Tests:

- Backend route test if new endpoint is introduced.
- Frontend typecheck.
- Manual smoke with a known run that has preview union materialized.

Cleanup:

- Reduce direct dependency from Workbench on Graph Preview-specific components.

## 10. PR 06 — Contextual delta backend

Suggested title:

```text
feat(graph-review): compute contextual graph deltas
```

Goal:

Teach the backend to return source/object deltas that can power pill overlays.

Expected backend changes:

- Add service:

```text
apps/live_control_server/services/graph_review_diff.py
```

- Emit deltas for:
  - matched node
  - gold-only node
  - live-only node
  - changed type
  - changed label
  - changed evidence
  - changed edge neighborhood
  - comparator uncertain

- Include source-span refs where available.
- Include lane object refs.
- Include comparator reason text when available.

Expected frontend changes:

- Add TypeScript types for deltas.
- Display raw deltas in a debug table or inspector scaffold.
- Do not attempt final pill overlay styling yet.

Acceptance:

- Workbench response includes contextual deltas for a gold/live comparison.
- Deltas include enough references to jump from table row to object/source span later.
- Existing score calculations remain unchanged unless intentionally refactored.

Tests:

- Backend fixture test for matched/missing/extra node deltas.
- Backend fixture test for changed edge neighborhood if feasible.
- Backend fixture test for missing source-span refs tolerated.

Cleanup:

- Reuse existing compare code. Do not fork the comparator unless necessary.

Risk:

High. This is the semantic core of the Workbench.

## 11. PR 07 — Pill overlays and lane-aware inspector

Suggested title:

```text
feat(graph-review): show graph diff status on projected pills
```

Goal:

Move the review experience from tables into the source text.

Expected frontend changes:

- Add lane-aware pill presentation.
- Show visual states for:
  - matched
  - gold-only
  - live-only
  - variant-only
  - changed type
  - changed evidence
  - changed edges
  - comparator uncertain

- Add lane-aware inspector for selected pill/node/edge/source span.
- Inspector should show:
  - gold expected object
  - live produced object
  - evidence quote(s)
  - source paragraph/source unit
  - edge neighborhood deltas
  - comparator explanation

Expected backend changes:

- Add any missing fields required by the inspector.

Acceptance:

- A reviewer can see missing/extra/matched graph behavior directly in the source Markdown.
- Clicking a pill explains the difference.
- Metrics rows can select or jump to relevant objects where refs exist.

Tests:

- Frontend typecheck.
- Component tests if available for status-label rendering.
- Manual smoke on a known gold/live session.

Cleanup:

- Move miss/extra tables further into supporting role.
- Keep object IDs visible only as debug details.

Risk:

High. This is where UX quality matters most.

## 12. PR 08 — Split projection view

Suggested title:

```text
feat(graph-review): add split projection comparison view
```

Goal:

Support messy comparisons where one overlay gets visually noisy.

Expected frontend changes:

- Add `ProjectedSourceSplitView.tsx`.
- Support two selected lanes:
  - gold vs live
  - live vs variant
  - baseline vs variant

- Synchronize scroll by source span ID or paragraph ordinal.
- Reuse the same inspector as overlay mode.

Expected backend changes:

- Ensure the Workbench can load two projection payloads together or in coordinated parallel calls.

Acceptance:

- A reviewer can switch from overlay mode to split mode.
- Selecting an object on either side opens the same inspector.
- Source paragraphs stay roughly synchronized by source span/ordinal.

Tests:

- Frontend typecheck.
- Manual smoke with a noisy run.

Cleanup:

- Do not duplicate reader internals.
- Split view should compose `ProjectedSourceReader`, not replace it.

## 13. PR 09 — Provenance adapters

Suggested title:

```text
feat(graph-review): surface extraction provenance in Workbench
```

Goal:

Fold Manual/Vocabulary Review value into the Workbench.

Expected backend changes:

- Add lane adapter for manual-review artifacts.
- Expose provenance data keyed by selected node/edge/evidence when possible.
- Include prompt context, pass name, variant name, and evidence quotes.

Expected frontend changes:

- Add provenance panel:

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/provenance/
```

- Show extraction pass.
- Show prompt context.
- Show baseline vs assisted variant.
- Show vocabulary packet influence when available.
- Link evidence quotes to source spans.

Acceptance:

- From a selected object, reviewer can inspect why/how it was produced when provenance exists.
- Missing provenance is displayed as unavailable, not as an error.
- Standalone Manual Review still works.

Tests:

- Backend adapter test with a known manual-review artifact.
- Frontend typecheck.
- Manual smoke on existing vocabulary/manual review artifact.

Cleanup:

- Identify Manual Review components that can be moved or wrapped.
- Do not retire Manual Review yet.

Risk:

High because static manual artifacts and live run lanes may not align cleanly.

## 14. PR 10 — Generic variant comparison

Suggested title:

```text
feat(graph-review): support baseline and variant lane comparison
```

Goal:

Make vocabulary/profile experiments normal lane comparisons instead of special cases.

Expected backend changes:

- Support comparing:
  - gold vs live
  - gold vs baseline vs variant
  - baseline vs variant
  - previous run vs current run

- Add improvement/regression summaries by lane.
- Generalize vocabulary-ablation data path into lane comparison if parity exists.

Expected frontend changes:

- Allow multiple comparison lanes.
- Add lane comparison summary:
  - improved
  - regressed
  - unchanged
  - ambiguous
  - comparator uncertain

- Show variant deltas in overlay and split modes.

Acceptance:

- Vocabulary-assisted and baseline runs can be compared without session-specific UI gates.
- A reviewer can understand what the variant changed in context.
- Existing session-23 vocabulary dogfood can be reproduced through generic lane comparison or remains available as a fixture until parity.

Tests:

- Backend fixture test for baseline vs variant summary.
- Frontend typecheck.
- Manual smoke reproducing the known vocabulary dogfood comparison.

Cleanup:

- Remove or deprecate special-purpose vocabulary-ablation endpoint/UI only after parity.

Risk:

High. This should not be attempted before PR 06/07 are stable.

## 15. PR 11 — Trends and regression memory

Suggested title:

```text
feat(graph-review): add run history trend view
```

Goal:

Make metrics useful as longitudinal smoke alarms, not the primary review surface.

Expected backend changes:

- Add run history aggregation for selected campaign/session/profile families.
- Emit trend points for:
  - node recall
  - edge recall
  - overproduction
  - evidence coverage
  - comparator warnings
  - vocabulary/profile impact

Expected frontend changes:

- Add Run History / Trends panel.
- Let trend points deep-link to contextual review where possible.

Acceptance:

- A reviewer can see whether a change improved or regressed graph behavior over time.
- Trend points link to concrete run/lane selections.
- Metrics remain secondary to contextual review.

Tests:

- Backend aggregation tests over small fake run history.
- Frontend typecheck.

Cleanup:

- Formalize any fixture schema versions needed for stable trend tests.

## 16. PR 12 — Surface retirement and registry cleanup

Suggested title:

```text
refactor(graph-review): retire duplicate graph review surfaces
```

Goal:

Remove duplicated product surfaces after Workbench parity.

Expected changes:

- Hide or retire standalone Graph Gold Review if Workbench covers it.
- Hide or retire standalone Manual/Vocabulary Review if Workbench provenance covers it.
- Decide whether Graph Preview remains a GM planning reader or becomes a Workbench mode.
- Update plan-surface registry.
- Remove duplicate API wrappers.
- Remove duplicate pickers.
- Remove duplicate source-span highlighting code.
- Remove duplicate graph pill rendering code.

Acceptance:

- Graph Review Workbench covers gold-vs-live review.
- Graph Review Workbench covers baseline-vs-variant review.
- Graph Review Workbench covers provenance inspection where static artifacts are available.
- Party Registry remains separate.
- No write-capable behavior is introduced into Workbench.

Tests:

- Frontend typecheck.
- Backend tests still pass.
- Manual smoke for Workbench modes that replace old tools.

Cleanup:

- This is the cleanup PR. Do not merge until parity is real.

Risk:

Medium. The risk is not code complexity; it is retiring too early.

## 17. Suggested execution rhythm

Recommended grouping:

```text
Foundation stack:
  PR 00 docs
  PR 01 lane contracts
  PR 02 run metadata
  PR 03 workbench shell

Projection stack:
  PR 04 projection reader extraction
  PR 05 single-lane projection

Diff stack:
  PR 06 contextual deltas
  PR 07 pill overlays and inspector
  PR 08 split projection view

Expansion stack:
  PR 09 provenance adapters
  PR 10 generic variant comparison
  PR 11 trends

Consolidation stack:
  PR 12 retirement and cleanup
```

Do not start the retirement PR until the Workbench is boring to use for the old jobs.

## 18. Suggested PR review checklist

Every PR should answer:

- Does this preserve read-only behavior?
- Does this make source evidence clearer?
- Does this reduce or contain duplication?
- Does this avoid hardcoding one session or one dogfood case?
- Does this preserve old tools until parity?
- Does this make future lane comparison easier?
- Does this make metrics more navigable to source context?

## 19. First implementation target

The first code PR after docs should be PR 01 + maybe the smallest safe part of PR 02 if the codebase makes that natural.

Recommended initial acceptance target:

```text
A reviewer can identify graph review lanes in shared backend/frontend types, and graph-ingest run summaries expose enough metadata for the future Workbench picker to distinguish baseline, vocabulary, and profile variants when that metadata exists.
```

Avoid starting with TipTap overlay work. The lane and run metadata foundation will make the UI work much easier and safer.
