---
document_id: dmb-design-graph-review-workbench-roadmap
title: "DESIGN — Graph Review Workbench roadmap"
document_class: design
status: draft roadmap
created_at: "2026-07-01"
last_updated_at: "2026-07-01"
related:
  - Docs/Design/GRAPH-MEMORY-CONTEXTUAL-VOCABULARY-ROADMAP.md
  - Docs/Design/GUARDRAILS-Sentence-Grounded-Ingestion-Vision.md
  - Docs/Design/ANCHOR-plan-surface-agent-interaction.md
  - Docs/Experiments/PLAN-SURFACE-LADDER-TRACKING.md
  - apps/live-control-ui/src/planSurface/graphGoldReview/
  - apps/live-control-ui/src/planSurface/graphPreview/
  - apps/live-control-ui/src/planSurface/manualReview/
  - apps/live_control_server/services/graph_gold_review.py
  - apps/live_control_server/services/graph_ingest_run_registry.py
  - apps/live_control_server/services/graph_manual_review.py
---

# DESIGN — Graph Review Workbench roadmap

## 1. Thesis

Graph Review Workbench should evaluate graph ingestion as **projected reading behavior over canonical source text**, not as disconnected metrics over extracted objects.

The current graph dogfood surfaces are useful, but they split one review job across several tools:

- **Graph Gold Review** compares a gold graph fixture against one live ingestion run and reports scores, missed objects, extra objects, and evidence diffs.
- **Graph Preview / Union Supergraph projection** renders graph-node pills over recap Markdown and lets the reviewer inspect graph context in a reader-like surface.
- **Manual / Vocabulary Review** exposes extraction passes, prompt context, baseline-vs-assisted variants, node pills, edge pills, and evidence quotes from static review artifacts.

The long-term product should be one read-only workbench that can answer:

> What did this ingestion cause the GM-facing graph projection to look like, where is it supported in the source, and how does that differ from gold or another run?

Metrics remain useful, but they should become smoke alarms and navigation aids. The main surface should show the graph in context.

## 2. Product north star

The workbench centers on a source document, usually a normalized session recap, with graph projection lanes overlaid on the text.

A reviewer should be able to:

1. Select a campaign/session.
2. Select a gold graph lane.
3. Select one or more live or variant lanes.
4. Read the source Markdown with graph pills rendered inline.
5. See whether each pill is matched, missing, extra, changed, or comparator-uncertain.
6. Click a pill to inspect gold/live/variant evidence, node details, edge neighborhoods, and extraction provenance.
7. Open metrics only as a supporting health panel.

The ideal workflow is:

```text
Open Session 1
  → choose Gold v1
  → choose baseline live run
  → choose vocabulary/profile variant
  → read the recap with graph overlays
  → click suspicious pills
  → inspect evidence, edge deltas, and provenance
  → decide whether the problem is extraction, matching, vocabulary, source segmentation, or gold coverage
```

The tool should help answer human review questions before numeric questions:

- Did the graph understand the important event?
- Did it attach the right people, places, quests, jobs, encounters, and consequences?
- Did it invent nodes that the source does not support?
- Did it miss a relation that changes the GM's understanding?
- Did a variant actually improve the projection, or only move a metric?
- Is the comparator wrong because gold is under-specified or semantically close-but-not-identical?

## 3. Non-goals and safety boundary

Graph Review Workbench is read-only.

It must not:

- Promote graph candidates to canon.
- Write approved memory.
- Mutate corpus files.
- Replace the Party Registry, which remains a separate write-capable tool.
- Treat generated summaries as source evidence.
- Collapse source truth into projection truth.

The hierarchy stays:

```text
canonical source text
  → source anchors / source units
    → candidate graph projection
      → comparison annotations
        → metrics and reports
```

The workbench reviews graph behavior. It does not bless graph behavior.

## 4. Current-state inventory

### 4.1 Graph Gold Review

Current role:

- Select campaign/session.
- Select one live graph-ingest run manifest.
- Compare it to a gold fixture.
- Display node/edge scores, missed objects, extra objects, match pairs, and evidence diffs.

Strengths:

- Already knows the gold-vs-live review problem.
- Already has backend comparison machinery.
- Already has object indexes and match-pair concepts.
- Good base for the new workbench shell.

Limitations:

- Single live manifest at a time.
- Metrics and tables dominate the experience.
- Vocabulary ablation is currently session-specialized rather than generic variant comparison.
- Does not render the reviewed graph over the source text as the primary surface.

### 4.2 Graph Preview / Union Supergraph projection

Current role:

- Render recap Markdown through Tiptap.
- Replace graph references with inline graph-node pills.
- Maintain active node state.
- Show hover cards and an explorer panel.
- Highlight source spans when evidence is selected.

Strengths:

- This is the strongest existing UX primitive for the desired workbench.
- It reviews graph behavior as a reading experience.
- It already connects projected graph nodes back to source paragraphs.

Limitations:

- Oriented around one projection payload, usually latest preview/union projection.
- Not lane-aware.
- Does not express gold/live/variant diff state on each pill.
- Component names and copy are tied to Graph Preview / Union Supergraph rather than a generic review reader.

### 4.3 Manual / Vocabulary Review

Current role:

- Read static manual-review artifacts.
- Show prompt context and pass variants.
- Render baseline/assisted node and edge pills.
- Expose evidence quotes and connected edges.

Strengths:

- Good provenance model.
- Good pass-level inspection shape.
- Useful for vocabulary and prompt debugging.

Limitations:

- Reads static artifacts, not live run registry entries.
- Structurally separate from gold-vs-live review.
- Does not render the final graph projection over source Markdown.

## 5. Core abstraction: review lanes

The workbench should introduce a shared lane concept before trying to solve every UI problem.

A lane is a comparable source of graph projection behavior.

Candidate lane roles:

```ts
type GraphReviewLaneRole =
  | "gold"
  | "live"
  | "variant"
  | "reference";
```

Candidate lane source kinds:

```ts
type GraphReviewLaneSourceKind =
  | "gold_fixture"
  | "graph_ingest_run"
  | "manual_review_variant"
  | "projection_payload";
```

Draft lane shape:

```ts
type GraphReviewLane = {
  laneId: string;
  role: GraphReviewLaneRole;
  sourceKind: GraphReviewLaneSourceKind;
  label: string;
  campaignId: string;
  sessionId: string;

  manifestPath?: string;
  artifactPath?: string;
  goldPath?: string;
  previewUnionPath?: string;

  status: "available" | "missing_projection" | "failed" | "stale" | "unknown";

  counts: {
    nodes: number;
    edges: number;
    beats?: number;
    evidenceRefs?: number;
  };

  metadata: {
    runId?: string;
    generatedAt?: string;
    modelId?: string;
    extractionProfile?: string;
    extractionMode?: string;
    vocabularyMode?: "none" | "node" | "edge" | "node_and_edge" | "dynamic" | "unknown";
    runnerOptions?: Record<string, unknown>;
    diagnostics?: Record<string, unknown>;
  };
};
```

The lane abstraction lets the UI compare gold vs live today and gold vs baseline vs vocabulary later without inventing new tools for every variant.

## 6. Core abstraction: projected source review

The workbench should standardize one projected-source payload shape.

Draft shape:

```ts
type GraphReviewProjection = {
  lane: GraphReviewLane;
  markdown: string;
  sourceSpans: RecapProjectionSourceSpan[];
  nodeViews: Record<string, GraphProjectionNodeView>;
  mentions: GraphProjectionMention[];
};
```

The source document is the review surface. Graph objects are presented as annotations on the source, not as detached rows.

The first version can use the existing projection format from the union-supergraph recap reader, but the reader should be extracted under generic names so it can render gold/live/variant lanes.

## 7. Core abstraction: contextual deltas

Object-level comparison is not enough. The workbench needs deltas anchored to source context.

Draft shape:

```ts
type GraphReviewDeltaStatus =
  | "matched"
  | "gold_only"
  | "live_only"
  | "variant_only"
  | "changed_type"
  | "changed_label"
  | "changed_evidence"
  | "changed_edges"
  | "comparator_uncertain";

type GraphReviewDelta = {
  deltaId: string;
  objectKind: "node" | "edge" | "mention" | "source_span";
  status: GraphReviewDeltaStatus;
  sourceSpanRefId?: string;
  laneObjectRefs: Record<string, string | null>;
  summary: string;
  comparatorReason?: string;
};
```

The source-span dimension is the key. A useful review does not only ask whether two node IDs matched. It asks what each lane saw in a paragraph and how that affected the projected reading experience.

## 8. Primary views

### 8.1 Context Projection Diff

This should be the default view.

It renders one source document with lane-aware graph pills inline.

Each pill can show status:

- matched in gold/live
- gold-only / missing from live
- live-only / overproduced
- variant-only
- type changed
- label changed
- evidence changed
- edge neighborhood changed
- comparator uncertain

Clicking a pill opens a lane-aware inspector.

### 8.2 Split Projection View

This view renders two projections side by side.

Use it when a single overlay gets too noisy.

Example:

```text
Gold projection             Live projection
---------------             ---------------
source paragraph 1           source paragraph 1
source paragraph 2           source paragraph 2
```

Scroll synchronization should use source span IDs or paragraph ordinals, not pixel position.

### 8.3 Graph Delta Inspector

This is the click-through panel for a selected pill, node, edge, or source paragraph.

It should show:

- Gold expected object.
- Live produced object.
- Variant produced object, when present.
- Evidence quote(s).
- Source paragraph / source unit.
- Node type and label differences.
- Edge neighborhood differences.
- Comparator explanation.
- Gold coverage warning, when the comparator suggests the gold fixture may be under-specified.

### 8.4 Provenance / Extraction Passes

This panel answers why a lane produced an object.

It should show:

- Extraction pass.
- Prompt context.
- Baseline vs assisted variant, when available.
- Vocabulary packet influence, when available.
- Evidence quotes.
- Connected edges.

This should grow out of Manual Review, but it should live inside the Workbench rather than as a separate destination.

### 8.5 Metrics / Run Health

Metrics should remain available but be demoted.

Useful data:

- Node recall.
- Edge recall.
- Extra nodes/edges.
- Missed nodes/edges.
- Evidence coverage.
- Comparator warnings.
- Vocabulary impact.
- Run status and diagnostics.

Every metric row should deep-link into source-context review when possible.

## 9. Roadmap

### Phase 0 — Name the destination and freeze the boundary

Goal: make the target explicit before building more UI.

Tasks:

- [ ] Add this design doc.
- [ ] Treat Graph Review Workbench as the destination product name.
- [ ] Document read-only boundary: no corpus mutation, no canon promotion, no approved-memory writes.
- [ ] Identify Graph Gold Review, Graph Preview, and Manual Review as source components for consolidation.
- [ ] Keep Party Registry separate because it is write-capable.

Cleanup:

- [ ] Avoid creating a fourth permanent graph review surface without a retirement path for the older surfaces.

### Phase 1 — Introduce the lane model

Goal: make gold/live/variant/reference comparable without forcing all sources into one fake storage model.

Tasks:

- [ ] Add backend lane models.
- [ ] Add frontend lane types.
- [ ] Represent gold fixtures, graph-ingest manifests, and manual-review variants as lanes.
- [ ] Add lane metadata cards to the UI.
- [ ] Keep current gold comparison behavior working while the lane shell is introduced.

Cleanup:

- [ ] Stop treating gold compare, latest preview, and manual beds as unrelated product concepts in the UI layer.
- [ ] Keep source-specific loaders behind lane adapters.

### Phase 2 — Enrich run discovery

Goal: make run/variant selection trustworthy.

Tasks:

- [ ] Extend graph-ingest run summaries with extraction profile.
- [ ] Expose vocabulary flags / vocabulary mode.
- [ ] Expose model/provider when available.
- [ ] Expose runner options and diagnostics summary.
- [ ] Expose preview-union availability.
- [ ] Add human-readable run labels.

Cleanup:

- [ ] Remove session-specific vocabulary-ablation UI gates.
- [ ] Replace hardcoded session-23 vocabulary behavior with generic “available variants for this session.”

### Phase 3 — Build the first Workbench shell

Goal: reframe Graph Gold Review into a lane-aware review shell.

Tasks:

- [ ] Create `graphReviewWorkbench/` frontend module folder.
- [ ] Add campaign/session selection.
- [ ] Add gold lane selector.
- [ ] Add live/variant lane selector.
- [ ] Render run metadata cards.
- [ ] Move scorecards/miss tables into a secondary metrics panel.
- [ ] Preserve existing Graph Gold Review routes until Workbench parity is reached.

Cleanup:

- [ ] Extract shared run picker logic.
- [ ] Extract scorecard/miss table components from Graph Gold Review if they remain useful.
- [ ] Make old Graph Gold Review a compatibility wrapper or hidden route once the Workbench shell is stable.

### Phase 4 — Extract the contextual projection reader

Goal: reuse the strongest existing product surface: graph pills over Markdown.

Tasks:

- [ ] Extract a generic `ProjectedSourceReader` from the Union Supergraph recap projection.
- [ ] Extract source-span highlighting helpers.
- [ ] Extract generic graph-node runtime state.
- [ ] Extract or generalize graph-node pill rendering.
- [ ] Make the reader accept lane-aware projection annotations.

Cleanup:

- [ ] Remove Graph Preview-specific naming from generic projection reader code.
- [ ] Keep Union Supergraph / Graph Preview as a wrapper around the generic reader where needed.
- [ ] Consolidate duplicate source-span matching logic.

### Phase 5 — Add contextual diff overlays

Goal: make the source text show what changed.

Tasks:

- [ ] Add pill status annotations: matched, gold-only, live-only, variant-only, changed type, changed evidence, changed edges, comparator uncertain.
- [ ] Add lane badges on inline graph pills.
- [ ] Add source-span-level delta annotations.
- [ ] Add click-through from metrics/tables to source spans.
- [ ] Add a lane-aware inspector for selected pills.

Cleanup:

- [ ] Demote giant miss tables to navigation aids.
- [ ] Keep object IDs visible for debugging, but do not make them the primary review language.

### Phase 6 — Add split projection mode

Goal: support messy comparisons where a single overlay becomes too noisy.

Tasks:

- [ ] Add two-lane split projection view.
- [ ] Synchronize scrolling by source span or paragraph ordinal.
- [ ] Reuse the same inspector for both sides.
- [ ] Allow gold vs live, live vs variant, and baseline vs variant split modes.

Cleanup:

- [ ] Reuse the same projection reader internals for overlay and split mode.
- [ ] Avoid introducing a second independent source rendering path.

### Phase 7 — Fold in Manual / Vocabulary Review provenance

Goal: make pass and prompt inspection available inside the Workbench.

Tasks:

- [ ] Add provenance panel for selected node/edge/pill.
- [ ] Show extraction pass and prompt context when available.
- [ ] Show baseline vs assisted variants when available.
- [ ] Show vocabulary packet influence when available.
- [ ] Link evidence quotes back to source spans.

Cleanup:

- [ ] Move useful Manual Review components into Workbench provenance components.
- [ ] Hide or retire standalone Manual Review after parity.
- [ ] Keep static manual-review artifacts as fixtures/tests rather than a separate product surface.

### Phase 8 — Make variant comparison first-class

Goal: make vocabulary and profile experiments normal lanes.

Tasks:

- [ ] Support gold vs latest live.
- [ ] Support gold vs selected live run.
- [ ] Support baseline vs vocabulary.
- [ ] Support baseline vs profile variant.
- [ ] Support previous run vs current run.
- [ ] Support gold vs multiple candidate runs.
- [ ] Add improvement/regression summary by lane.

Cleanup:

- [ ] Remove special-purpose vocabulary-ablation endpoint/UI once generic lane comparison covers it.
- [ ] Keep curated vocabulary dogfood artifacts only as named examples or tests.

### Phase 9 — Add trend and regression memory

Goal: make metrics useful as longitudinal smoke alarms.

Tasks:

- [ ] Add run history view.
- [ ] Show node recall trend.
- [ ] Show edge recall trend.
- [ ] Show overproduction trend.
- [ ] Show evidence coverage trend.
- [ ] Show comparator warning trend.
- [ ] Show vocabulary/profile impact trend.
- [ ] Deep-link every trend point into contextual review when possible.

Cleanup:

- [ ] Formalize fixture schema versions.
- [ ] Keep report artifacts and UI review artifacts aligned.

### Phase 10 — Retire old surfaces

Goal: simplify the plan surface once the Workbench owns the review workflow.

Tasks:

- [ ] Keep Graph Review Workbench.
- [ ] Keep Party Registry separate.
- [ ] Retire or hide standalone Graph Gold Review.
- [ ] Retire or hide standalone Manual / Vocabulary Review.
- [ ] Decide whether Graph Preview remains as a distinct GM planning reader or becomes a Workbench mode.

Cleanup:

- [ ] Remove duplicate API wrappers.
- [ ] Remove duplicate pickers.
- [ ] Remove duplicate source-span highlighting code.
- [ ] Remove duplicate graph pill rendering code.
- [ ] Update plan-surface registry after parity.

## 10. Milestones

### Milestone A — Gold vs Live Contextual Review

Definition:

For one campaign/session, select a gold fixture and one live manifest. The tool renders the source recap with inline graph pills and visual statuses for matched, missing, and extra nodes. Clicking a pill opens a lane-aware inspector with gold/live evidence and edge neighborhood.

Why this matters:

This is the point where the tool stops being an eval report and becomes a graph debugging instrument.

### Milestone B — Baseline vs Variant

Definition:

Select a baseline live run and one variant run, such as vocabulary or an extraction profile. Compare both against the same gold lane and show changed nodes/edges in context.

Why this matters:

Vocabulary and profile experiments become visible as reading-behavior changes instead of metric-only deltas.

### Milestone C — Provenance

Definition:

For any selected node/edge/pill, show extraction pass, prompt context, evidence quote, and vocabulary influence when available.

Why this matters:

Reviewers can distinguish extraction failure, prompt failure, vocabulary contamination, segmentation failure, comparator failure, and gold under-encoding.

### Milestone D — Consolidation

Definition:

Graph Gold Review, Graph Preview, and Manual / Vocabulary Review are either retired or turned into wrappers/modes of the Workbench.

Why this matters:

The repo stops accumulating parallel graph review surfaces.

## 11. Suggested module shape

Frontend:

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/
  GraphReviewWorkbenchModule.tsx
  GraphReviewLanePicker.tsx
  GraphReviewRunCards.tsx
  GraphReviewMetricPanel.tsx
  GraphReviewDiffTable.tsx
  GraphReviewDiffInspector.tsx

  projection/
    ProjectedSourceReader.tsx
    ProjectedSourceSplitView.tsx
    LaneAwareGraphNodeReferenceNode.ts
    LaneAwareGraphNodeReferenceView.tsx
    sourceSpanHighlighting.ts

  diff/
    graphReviewDiffTypes.ts
    graphReviewDeltaLabels.ts
    graphReviewPresentation.ts

  provenance/
    ExtractionPassPanel.tsx
    PromptContextPanel.tsx
    EvidenceTracePanel.tsx
```

Backend:

```text
apps/live_control_server/routes/graph_review.py

apps/live_control_server/services/
  graph_review_workbench.py
  graph_review_lanes.py
  graph_review_projection.py
  graph_review_diff.py
```

Shared contracts should eventually move toward reusable graph-memory contract modules if they become runtime-independent enough.

## 12. Implementation notes

### 12.1 Prefer adapters over forced unification

Do not force live manifests, gold fixtures, and manual-review beds into the same storage model immediately.

Instead:

```text
gold fixture loader         → lane adapter
live manifest registry      → lane adapter
manual review artifact      → lane adapter
projection payload loader    → lane adapter
```

The UI receives lanes. The backend can still use different loaders internally.

### 12.2 Keep metrics, but demote them

The current scorecard is useful for regression scanning. It should not be deleted.

But the default question should become:

> Where in the source did this behavior appear, and what did each lane do with it?

Not:

> What is the score?

### 12.3 Treat comparator uncertainty as a first-class result

A mismatch can mean many things:

- The live graph is wrong.
- The gold graph is under-specified.
- The comparator is too strict.
- The labels differ but the semantic object is close.
- The source segmentation prevented fair recall.
- The extractor emitted an acceptable alternate structure.

The UI should surface uncertainty rather than hiding it behind pass/fail counts.

### 12.4 Keep source evidence stronger than display summaries

Projection summaries, labels, and hover text are useful display affordances. They are not evidence.

Evidence-backed claims need source anchors/source units so the review surface can explain itself.

### 12.5 Preserve old tools until parity

Do not remove Graph Gold Review, Graph Preview, or Manual Review just because the Workbench folder exists.

Retirement should happen only after equivalent workbench modes exist.

## 13. First implementation slice

Recommended first PR scope:

1. Add backend/frontend `GraphReviewLane` types.
2. Extend graph-ingest run summaries with enough metadata to identify variants.
3. Create `GraphReviewWorkbenchModule` shell.
4. Reuse the existing gold compare endpoint or add a thin workbench endpoint that wraps it.
5. Show campaign/session selection, gold lane, live lane, run cards, and existing metrics.
6. Leave contextual overlay for the next PR.

Acceptance:

- A reviewer can open one session in Graph Review Workbench.
- A reviewer can select gold + one live manifest.
- The UI shows run identity, counts, extraction/profile/vocabulary metadata where available.
- Existing node/edge compare information is still visible.
- The new shell does not write corpus or graph memory.
- Existing Graph Gold Review continues to work.

Recommended second PR scope:

1. Extract `ProjectedSourceReader` from the Union Supergraph recap projection.
2. Render one selected lane's projection over source Markdown inside the Workbench.
3. Preserve graph-node pill hover/explorer behavior.
4. Preserve evidence-span highlighting.

Recommended third PR scope:

1. Add gold/live delta annotations to projected pills.
2. Add lane-aware inspector.
3. Make metric rows jump to source spans or selected objects.

## 14. Guiding sentence

Graph Review Workbench helps us evaluate graph ingestion as projected reading behavior over canonical source text, not as disconnected metrics over extracted objects.
