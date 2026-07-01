# HANDOFF — Prime Design: consolidate Graph Preview, Graph Gold Review, and Vocabulary Review into one Graph Exploring tool

**Created:** 2026-07-01
**Repo:** `Drakosfire/DungeonMindBuddy`
**Target base branch:** `main`
**Suggested next branch:** `codex/prime-design-graph-exploring-tool-consolidation` (design) or a narrow UI-implementation branch once a shape is picked
**Mode:** Prime Design — UI/data-model architecture decision. This is squarely a "decide the shape, don't pattern-match a merge" task: three tools built independently over several weeks have real, non-overlapping capabilities and real, wasteful duplication, and untangling which is which needs judgment, not a mechanical file merge.
**From:** the dogfooding agent (C1S1 encounter/job real-recap dogfood + gold remediation + vocabulary-wiring workstream)
**To:** the next Prime Design agent picking up Graph Memory review tooling

---

## 0. Copyable pickup prompt

```markdown
You are the next-phase Prime Design agent for DungeonMindBuddy's Graph Memory review tooling.

Read first (in this order):

1. This file: `Docs/Plans/HANDOFF-prime-design-graph-exploring-tool-consolidation.md`
2. `Docs/Reports/GRAPH-MEMORY-RUNTIME-ENCOUNTER-JOB-DOGFOOD-C1S1.md` — Addendum 3 specifically (the gold/baseline/vocabulary 3-way comparison that motivated this handoff; also read §9-§12 and Addendum 2 for why gold-comparison tooling matters)
3. `Docs/Plans/HANDOFF-prime-design-graph-memory-extraction-taxonomy.md` §5 — the prior handoff's inventory of two of these three tools, written when they were built; this handoff supersedes that inventory's "these are complementary, not redundant" framing (§4 below explains why that framing no longer holds)
4. `Backlog.md` — search `## [DOING] Graph memory encounter/job extraction spike` — Follow-up 5 has the living, dated tracker entry for this exact decision, including the user's already-given answers to the three scoping questions this handoff exists to unblock

Mission: decide the data model and component shape for a single "Graph Exploring" tool that replaces Graph Preview, Graph Gold Review, and Vocabulary Review (Manual Review) as one coherent surface — able to select and compare N graph-ingest runs (not just one) side by side, optionally against gold, with the vocabulary/prompt context that produced each run visible. Party Registry stays a separate tool (already decided, §3). Do not just concatenate the three tools' JSX into tabs — the real design work is reconciling their three different "what is a comparable unit" data models (§4.3) into one.

This is a read-only diagnostic surface end to end (no corpus mutation, no canon promotion, no approved-memory writes) — that constraint does not change, it just needs to keep being true across three services' worth of consolidated code instead of one.
```

---

## 1. Executive summary — what this handoff is and why now

DungeonMindBuddy's Graph Memory workstream has accumulated **three separately-built, separately-shipped Plan-surface review tools** for inspecting graph-ingest extraction output, plus a fourth, categorically different tool (Party Registry) that happens to live in the same toolbox:

| Tool (Plan toolbox label) | Frontend | Backend service | Purpose |
|---|---|---|---|
| **Graph Preview** | `apps/live-control-ui/src/planSurface/graphPreview/` (2147 lines) | `apps/live_control_server/services/graph_preview_surface.py`, `graph_ingest_run_registry.py`, `recap_graph_preview_ingest.py` | Renders recap prose with clickable entity pills, backed by the union-supergraph projection of the latest ready run |
| **Graph Gold Review** | `apps/live-control-ui/src/planSurface/graphGoldReview/` (923 lines) | `apps/live_control_server/services/graph_gold_review.py` | Compares **one** live run against a hand-authored gold fixture: scorecard, miss tables, evidence diff, run picker |
| **Vocabulary Review** (labeled "Vocabulary Review" in the toolbox, code name `manualReview`) | `apps/live-control-ui/src/planSurface/manualReview/` (497 lines) | `apps/live_control_server/services/graph_manual_review.py` | Pass-by-pass, side-by-side comparison of a **static, precomputed** baseline-vs-vocabulary-assisted artifact, with prompt text shown alongside output |
| Party Registry (kept separate — not in scope here) | `apps/live-control-ui/src/modules/PartyRegistryModule.tsx` (448 lines) | party registry service (write path) | Edits per-session roster slugs. **Categorically different**: this is the only write-capable tool of the four. |

**Why this handoff exists now:** the dogfooding agent needed to run and compare **gold vs. baseline vs. baseline+vocabulary** for a real encounter/job-profile run (see §2), and discovered that none of the three read-only tools can do this today — each was built for a narrower comparison shape (one live run vs. gold; or two *static, precomputed* variants; or one rendered projection with no comparison at all). Getting an answer required raw Python one-liners against each tool's own backend service, not the tools themselves. That is the concrete symptom motivating consolidation, not merge-for-its-own-sake.

**Decisions already made** (by the user, in the conversation that produced this handoff — do not re-litigate these):

1. **Party Registry stays separate.** Do not fold the write-capable roster editor into the same surface as the three read-only diagnostic tools. Cross-link or embed a read-only roster-context panel in the new tool if useful, but the write path stays where it is.
2. **Extend Graph Gold Review as the base**, not a from-scratch rebuild. It already has the most complete primitives for this job: a run picker backed by real run discovery (`discover_graph_ingest_runs`), a gold-comparison scorecard, miss tables, and an evidence-diff drill-down. Vocabulary Review and Graph Preview should be folded *into* this shape, not the reverse.
3. **Scope is real, not trivial.** ~3500 lines of frontend across the three tools, three separate backend services with three different data models for "what am I looking at" (see §4.3). This is a multi-file, multi-service consolidation, not an afternoon's UI polish pass.

---

## 2. The concrete gap that surfaced this (worked example — use as your test case)

On 2026-07-01, after fixing a paragraph-segmentation bug (`_split_recap_paragraph_spans` in `evals/graph_memory_layer/graph_preview_runner.py` — a source file ending in a single trailing newline silently dropped its final paragraph from every extraction pass; now fixed) and wiring a static context vocabulary packet into the runtime `category_encounter_job_preview` profile (previously only reachable from the separate vocabulary-ablation harness, never from the real runtime path — see `GraphPreviewRunnerOptions.context_vocabulary_packet` / `enable_node_vocabulary_packet` / `enable_edge_vocabulary_packet`, now wired end-to-end), the dogfooding agent ran three C1S1 extractions and needed to compare them:

| Run | node_count | edge_count | merged_nodes | blocked_nodes | node_recall (vs gold `v1`) | edge_recall |
|---|---:|---:|---:|---:|---:|---:|
| gold (`v1` fixture) | 27 | 30 | — | — | reference | reference |
| baseline (no vocab) | 53 | 33 | 0 | 7 | 66.7% | 23.3% |
| baseline + vocabulary | 46 | 33 | 1 | 4 | 59.3% | 26.7% |

Full write-up: `Docs/Reports/GRAPH-MEMORY-RUNTIME-ENCOUNTER-JOB-DOGFOOD-C1S1.md` Addendum 3.

**What the agent actually had to do to produce this table:** write ad-hoc Python calling `compare_gold_review()` directly, twice, once per manifest path, then diff the `missing_gold_nodes`/`missing_gold_edges` sets by hand in a third script to see *which specific* nodes/edges vocabulary helped or hurt. None of the three existing tools can:

- select and hold **more than one** live run at a time for comparison (Graph Gold Review's run picker is single-select);
- show **which vocabulary packet** (if any) produced a given run, or its content, next to that run's output (Graph Gold Review has no vocabulary awareness at all outside a session-23-only special case, §4.2; Vocabulary Review shows vocabulary prompt text but only for its own separately-precomputed, LLM-call-triggering artifact, never for a run that went through the real runtime ingest path);
- put gold + N runs side by side in one view.

This is the shape the new tool needs to support natively. Treat "reproduce the table above, plus a node/edge-level diff between the two runs, inside the UI, no ad-hoc scripting" as your acceptance test.

---

## 3. Answers already given (do not re-ask these)

The user answered three scoping questions directly when this handoff was requested:

**Q: Should Party Registry (write-capable) merge into the same tool as the three read-only viewers?**
**A: No — keep Party Registry as its own tool.** Cross-link or embed a read-only roster-context panel in the new tool if it's useful context (e.g. showing which PCs are in the party anchor for a given run), but do not bring the write path in.

**Q: What should the merged tool be built on top of?**
**A: Extend Graph Gold Review as the base.** It already has a run picker, gold comparison, and an embedded (session-23-only) vocabulary-ablation view — the most complete starting primitive of the three.

**Q: Sequencing — design first, or run the dogfood comparison first?**
**A: Dogfood first (done, §2), design handed off now (this document).** The three-way run in §2 is meant to be concrete input to your design, not something you need to re-derive.

---

## 4. What's actually duplicated vs. genuinely distinct (read before designing)

This is the part that needs real judgment. A naive "put three tabs in one component" merge would keep the duplication and just relabel it. Walking the actual code (all three `*Module.tsx` files read in full as of this handoff):

### 4.1 Genuinely duplicated (collapse these)

- **Campaign/session picker + URL sync.** Graph Preview and Graph Gold Review both already share `ReviewCampaignPicker` (`apps/live-control-ui/src/planSurface/ReviewCampaignPicker.tsx`) and `sessionCampaignContext.ts` (`resolveInitialReviewCampaignId`, `syncReviewCampaignUrl`, `sessionsForReviewCampaign`) — this part is *already* de-duplicated between two of the three. Vocabulary Review doesn't use it at all (see 4.3 — it has no campaign/session concept, only opaque "beds").
- **Node/edge pill rendering.** Three independent implementations exist: Vocabulary Review's inline `NodePill`/`EdgePill` (in `ManualReviewModule.tsx`), Graph Gold Review's `GraphGoldReviewMissTables.tsx` + `GraphGoldEvidenceDiff.tsx`, and Graph Preview's `GraphNodePresentation.tsx` / `recapNodePresentation.ts`. All three render some variant of "label, type, confidence, description, anchor-quote evidence" for a node or edge. This should become one shared presentation component with mode variants (compact-pill vs. detailed-card), not three.
- **Loading/error status-enum plumbing.** Every module hand-rolls its own `"idle" | "loading" | "ready" | "error"` state machine per fetched resource (sessions, compare, evidence, vocab ablation, beds, bed detail — six separate instances across the three modules). A shared `useAsyncResource`-style hook would collapse this without changing behavior.
- **Run/bed discovery + selection.** Graph Gold Review's `GraphGoldReviewRunPicker` (backed by real `discover_graph_ingest_runs`) and Vocabulary Review's bed picker (backed by a static checked-in artifact) are solving the same UX problem — "pick the thing(s) I'm comparing" — with two different data sources and no shared component.

### 4.2 Partially duplicated, needs a decision

- **Vocabulary awareness is currently hardcoded to one session.** `graph_gold_review.py`'s `_VOCABULARY_ABLATION_BY_SESSION` dict hardcodes `"session-23": DEFAULT_VOCABULARY_ABLATION_ARTIFACT` and `GraphGoldReviewModule.tsx` gates the entire vocabulary-ablation panel behind `selectedSessionId === "session-23"`. This needs to become general — driven by the manifest's own `diagnostics.context_vocabulary_packet_id` / `enable_node_vocabulary_packet` / `enable_edge_vocabulary_packet` fields (now populated by every runtime run as of this handoff's wiring work, §2), not a session-id allowlist.
- **Evidence-diff rendering** (`GraphGoldEvidenceDiff.tsx`) and **manual-review's anchor-quote blockquotes** both render source-text evidence for a graph object, from two different response shapes (`GoldReviewEvidenceDiffResponse` vs. `ManualReviewNode.anchor_quotes`/`ManualReviewEdge.anchor_quotes`). Likely convergeable but check both response schemas carefully before assuming they're the same shape.

### 4.3 Genuinely distinct — do not naively merge away

This is the load-bearing design problem. **The three tools disagree on what "the thing being compared" fundamentally is:**

- **Graph Gold Review's unit of comparison is a *live run* (a `graph_ingest_run_manifest.json` on disk, discovered dynamically via `discover_graph_ingest_runs`, identified by `manifest_path`), compared against exactly one *gold fixture* keyed by `campaign_id`/`session_id`.** This model is dynamic and extensible — any new run that reaches `preview_union_store_ready` shows up automatically.
- **Vocabulary Review's unit of comparison is a *bed*** (`bed_id`, e.g. `c1s1-stonebridge`) — **a static, precomputed, checked-in JSON artifact** (`baseline_vs_edge_and_node_manual_review.json`) produced by a *separate offline script* (`run_vocabulary_ablation_expanded_beds_dogfood.py`) that bakes in exactly two named variants (`baseline`, `edge_and_node_packet`) per bed. This model is closed and manual — adding a third variant, or a new bed, means re-running that script and re-committing its output; it has no relationship to the live run registry at all, and (confirmed while investigating this exact gap in §2) it has no way to represent the encounter/job profile's passes, since the script that produces it never enables `enable_encounter_job_pass`/`enable_party_participation_attachment`/`enable_encounter_job_edge_guidance`.
- **Graph Preview's unit is *the latest ready run for a session*, with no comparison concept at all** — it renders one run's projection as prose+pills, full stop.

**The design work is picking (or inventing) one unified "comparable unit" abstraction that can represent all three of these without regressing any of them** — e.g., something like "a named comparison slot, which can be populated from either (a) a live run manifest path, discovered dynamically, or (b) a precomputed artifact variant, loaded statically" with N slots selectable at once, one of which can be pinned as "gold." Do not assume this is easy — reconciling "dynamically discovered filesystem run" with "static checked-in comparison artifact" under one selection UI is the crux of this handoff, not a footnote.

### 4.4 A related, not-yet-fixed gap surfaced by the same investigation

`GraphIngestRunSummary` / `discover_graph_ingest_runs`'s reuse-cache logic (`_latest_matching_run` in `recap_graph_preview_ingest.py`) does not currently account for vocabulary settings when deciding whether an existing run can be reused instead of re-extracting. Today this is masked because dogfood callers always pass `force_graph_run=True`, but if the new tool ever offers a "run this now" action from the UI without forcing, it could silently return a cached no-vocabulary run when the user asked for a vocabulary-assisted one. Worth fixing as part of this work if the new tool exposes any run-triggering affordance (vs. purely browsing existing runs, which is lower-risk and may be sufficient for v1).

---

## 5. Non-negotiables and guardrails to carry forward

- **Read-only, no writes.** All three source tools are diagnostic-only: no corpus mutation, no canon promotion, no approved-memory writes, no `agent_interaction_connected`/`runtime_projection_connected` side effects. The consolidated tool inherits this exactly — Party Registry staying separate (§3) is precisely what keeps this true; do not let a "unified" impulse pull write affordances back in.
- **The union supergraph** (`src/graph_memory/union_supergraph/`) is the durable graph-memory read model; `evals/graph_memory_layer/` is proof/dogfood machinery. Don't let UI consolidation motivate moving durable contract logic into `evals/` or vice versa — the backend-service consolidation (three services → some smaller number) should respect this boundary, not just chase frontend convenience.
- **Preview-only run artifacts under `out/graph_memory/runs/` and `evals/graph_memory_layer/artifacts/graph_ingest_runs/` are git-ignored / semi-ephemeral by design.** Any new "compare N runs" UI must handle a run disappearing between page loads gracefully (this already bit the existing tools' error-state handling — preserve that discipline).
- **Vocabulary is not settled science.** Per `Docs/Plans/HANDOFF-prime-design-graph-memory-extraction-taxonomy.md` §3 and reconfirmed in §2's worked example: vocabulary helps structural consolidation and spatial-containment edges, hurts label-identity stability, and is a wash on aggregate recall. The new tool's job is to make this trade-off *visible and inspectable per-run*, not to editorialize a verdict on vocabulary into the UI.
- **`graph_extraction_profile` and `graph_extraction_profile_options` are already in every manifest's `diagnostics` block** (profile name + 4 boolean flags), and as of this handoff's wiring work, so are `context_vocabulary_packet_id` / `enable_node_vocabulary_packet` / `enable_edge_vocabulary_packet`. Design the new tool's run-summary display around these existing, already-populated fields rather than inventing a new metadata channel.

---

## 6. Suggested first tasks for the next agent

1. Read §4.3 twice. Do not start component work until you have an explicit written answer to "what is the unified comparable-unit data model" — this is the one decision that, if wrong, forces a rewrite.
2. Reproduce the §2 worked example inside the current Graph Gold Review tool as a baseline "how bad is the gap really" check: try to select two runs (`out/graph_memory/runs/longmont-c1/session-1/20260701T204317Z/` and `.../20260701T215207Z/`, both `preview_union_store_ready`, both still on disk as of this handoff) and gold at once. Confirm it cannot be done today (expected), so you have a concrete before/after to demo.
3. Decide whether the "bed" (Vocabulary Review) and "run" (Graph Gold Review) concepts merge into one registry-backed model (harder, but removes the static-artifact special case permanently) or coexist as two selectable *sources* feeding into the same comparison-slot UI (easier, ships faster, defers the harder unification). Write the decision down with what it costs to change later.
4. Fix the session-23 hardcoding in `graph_gold_review.py`'s `_VOCABULARY_ABLATION_BY_SESSION` (§4.2) as an early, low-risk slice regardless of the bigger decision — it's already a known wart independent of consolidation.
5. Scope backend service consolidation separately from frontend consolidation — `graph_preview_surface.py`, `graph_gold_review.py`, and `graph_manual_review.py` can plausibly merge into fewer services with a shared response-model vocabulary, but this can land after or alongside the frontend work, not necessarily before.
6. Before removing any of the three existing tools/routes, confirm nothing outside the Plan surface depends on their specific endpoints (`grep` for `/manual-review/`, `/gold-review/`, `graph-preview` route usages outside `apps/live-control-ui/src/planSurface/`).
7. Write a narrow implementation handoff for the first accepted slice, following this repo's `HANDOFF-pr<N>-<slug>.md` convention if it goes through the external-agent-pr-loop, or a plain `HANDOFF-<slug>.md` if implemented in-session (see `AGENTS.md`).

---

## 7. Reference index (all paths repo-relative)

**This handoff's direct motivation:**
- `Docs/Reports/GRAPH-MEMORY-RUNTIME-ENCOUNTER-JOB-DOGFOOD-C1S1.md` — Addendum 3 (the 3-way run, §2 above)
- `Backlog.md` → search `## [DOING] Graph memory encounter/job extraction spike` → Follow-up 5

**Prior related handoff (two of the three tools inventoried when first built):**
- `Docs/Plans/HANDOFF-prime-design-graph-memory-extraction-taxonomy.md` §5 (Manual Review + Graph Gold Review "as built" writeup — treat as historical context, this handoff's §4 supersedes its "complementary, not redundant" framing)

**Frontend (all three tools in scope, read each `*Module.tsx` in full before designing):**
- `apps/live-control-ui/src/planSurface/graphPreview/` (`GraphPreviewModule.tsx`, `GraphIngestProjectionPanel.tsx`, `UnionSupergraphRecapProjection.tsx`, `GraphNodePresentation.tsx`, `recapNodePresentation.ts`, `recapMarkdown.ts`, `recapGraphNodeRuntime.ts`, `recapSessionLabels.ts`, `graphPreviewUtils.ts`)
- `apps/live-control-ui/src/planSurface/graphGoldReview/` (`GraphGoldReviewModule.tsx`, `GraphGoldReviewRunPicker.tsx`, `GraphGoldReviewSessionPicker.tsx`, `GraphGoldReviewScorecard.tsx`, `GraphGoldReviewMissTables.tsx`, `GraphGoldEvidenceDiff.tsx`, `GraphGoldReviewVocabularyAblation.tsx`, `graphGoldReviewUtils.ts`)
- `apps/live-control-ui/src/planSurface/manualReview/` (`ManualReviewModule.tsx`, `manualReviewPasses.ts`)
- Shared already: `apps/live-control-ui/src/planSurface/ReviewCampaignPicker.tsx`, `apps/live-control-ui/src/planSurface/sessionCampaignContext.ts`
- Out of scope, kept separate (§3): `apps/live-control-ui/src/modules/PartyRegistryModule.tsx`
- Toolbox registration: `apps/live-control-ui/src/planSurface/config/planSurfaceConfig.ts` (the `tools` array with `graph-preview` / `graph-gold-review` / `manual-review` / `party-registry` entries)

**Backend (all endpoints currently under one router, `/api/live/graph-preview`, in `apps/live_control_server/routes/graph_preview.py`):**
- `graph_preview_surface.py`, `graph_ingest_run_registry.py`, `recap_graph_preview_ingest.py`, `recap_artifacts.py` — Graph Preview + run registry + union-supergraph projection endpoints (`/artifacts`, `/runs`, `/latest`, `/graph-ingest/runs`, `/graph-ingest/latest`, `/union-supergraph/projection`, `/recap`)
- `graph_gold_review.py` — Graph Gold Review endpoints (`/gold-review/sessions`, `/gold-review/compare`, `/gold-review/evidence`, `/gold-review/vocabulary-ablation`)
- `graph_manual_review.py` — Vocabulary Review endpoints (`/manual-review/beds`, `/manual-review/beds/{bed_id}`)

**Runtime extraction path (now vocabulary-aware end to end, as of this handoff):**
- `evals/graph_memory_layer/graph_preview_runner.py` — `GraphPreviewRunnerOptions` (now has `context_vocabulary_packet`/`enable_node_vocabulary_packet`/`enable_edge_vocabulary_packet`), `category_options_for_graph_extraction_profile`
- `apps/live_control_server/services/recap_graph_preview_ingest.py` — `build_recap_graph_preview_bundle`, `materialize_recap_preview_supergraph` (both now accept the same three vocabulary params)
- `src/graph_memory/extraction/category_candidate_graph_extractor.py` — `CategoryGraphExtractionOptions` (the underlying, already-capable extractor options this handoff's wiring finally made reachable from the real runtime path)
- `evals/graph_memory_layer/run_encounter_job_dogfood.py` — CLI wrapper, now with `--enable-vocabulary-packet` (reuses `BED_CONFIGS["c1s1-stonebridge"]` from the ablation script) and `--materialize-preview-union`
- `evals/graph_memory_layer/run_vocabulary_ablation_expanded_beds_dogfood.py` — the separate offline harness that produces Vocabulary Review's static artifact (`BED_CONFIGS`, `_build_c1s1_packet`)

**Gold fixtures (session-1 is `v1` as of 2026-07-01 gold remediation — see Backlog Follow-up 3):**
- `evals/graph_memory_layer/examples/session_1_candidate_graph_gold/`
- `evals/graph_memory_layer/live_vs_gold_compare.py` — `compare_parts`, `parts_from_raw_graph` (the comparator engine both Graph Gold Review and this handoff's ad-hoc 3-way comparison call directly)

**Uncommitted at handoff time:** the vocabulary-wiring changes described in §2/§4.4 (`evals/graph_memory_layer/graph_preview_runner.py`, `apps/live_control_server/services/recap_graph_preview_ingest.py`, `evals/graph_memory_layer/run_encounter_job_dogfood.py`, `tests/test_graph_memory_category_graph_preview_runner.py`, `Backlog.md`, the dogfood report) are staged in the working tree on `main`, not yet committed. Confirm with the user whether to commit them before or as part of picking up this handoff — they are a prerequisite (the manifest `diagnostics` fields referenced throughout §4-§5 only exist after these changes land).

**Current `main` tip at handoff time (before the uncommitted changes above):** `e7da9b7`.
