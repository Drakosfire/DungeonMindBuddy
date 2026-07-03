# HANDOFF — Prime Design: Graph Review Workbench dogfood verdict, and a pivot to a Graph Review + Gold Authoring Workbench

**Created:** 2026-07-02
**Repo:** `Drakosfire/DungeonMindBuddy`
**Target base branch:** `main`
**Suggested next branch:** `codex/prime-design-graph-review-gold-authoring` (design) or a narrow implementation branch once the first slice is picked
**Mode:** Prime Design — this supersedes `HANDOFF-prime-design-graph-exploring-tool-consolidation.md`'s "merge three viewers" framing with a bigger, more specific target: a two-lane **prose-and-pill projection** for review, plus a **human-in-the-loop gold labeling tool** with LLM assist. Both share one rendering substrate. Read §3 before anything else — it is a real dogfood verdict on code that already shipped, not a hypothetical.
**From:** the dogfooding agent (Graph Review Workbench dogfood session, 2026-07-02)
**To:** the next Prime Design agent picking up Graph Memory review/authoring tooling

---

## 0. Copyable pickup prompt

```markdown
You are the next-phase Prime Design agent for DungeonMindBuddy's Graph Memory review/authoring tooling.

Read first (in this order):

1. This file: `Docs/Plans/HANDOFF-prime-design-graph-review-and-gold-authoring-workbench.md`
2. `Docs/Plans/HANDOFF-prime-design-graph-exploring-tool-consolidation.md` — the PRIOR handoff this one supersedes. Its §4 "what's duplicated vs distinct" analysis of Graph Preview / Graph Gold Review / Vocabulary Review is still valid background, but its outcome (PRs #245–#256, the "Graph Review Workbench") was dogfooded and found insufficient — see §3 of THIS document for why, before you re-derive the same lessons.
3. `Backlog.md` — search `## [DOING] Graph memory encounter/job extraction spike` — Follow-up 6 has the living, dated tracker entry for this exact pivot.
4. `evals/graph_memory_layer/examples/session_1_candidate_graph_gold/candidate_graph_gold.json` — read the whole file once. This is the target data shape: everything the authoring tool produces must be a human-editable instance of this schema, not a new parallel format.

Mission: design (and then build, in slices) a tool with two modes sharing one rendering substrate:

- **Review mode**: side-by-side markdown-with-pills projections of two graph sources (gold vs. a live run, or live-baseline vs. live-vocabulary-run, or any two), with hover/click cross-highlighting between matched nodes/edges — NOT metadata tables. A human should be able to look at two panes of prose and see, visually, what differs.
- **Author mode**: one of those same projection panes becomes writable. A human selects text to declare a node, clicks two nodes to draw and label an edge, and can ask the LLM to propose more nodes/edges/attributes given what's been declared so far — accepting, rejecting, or editing each proposal before anything is saved. This is a genuinely new capability: right now, gold fixtands are authored by an agent hand-writing JSON in a code editor. This tool replaces that with direct human authorship, LLM-assisted, with full provenance of what the LLM proposed vs. what the human decided.

This is the load-bearing design problem: reconcile "read-only comparison" and "write-capable labeling" as ONE component family (shared `GraphProjectionReader`-style rendering, shared node/edge/evidence data model matching `candidate_graph_gold.json`), not two unrelated tools that happen to look similar.
```

---

## 1. Executive summary

On 2026-07-01, `HANDOFF-prime-design-graph-exploring-tool-consolidation.md` asked a Prime Design agent to merge Graph Preview + Graph Gold Review + Vocabulary Review into one "Graph Exploring" tool, extending Graph Gold Review as the base. That work shipped as 12 PRs (#245–#256, "Graph Review Workbench") building a two-lane shell, a delta-index engine, evidence-split inspectors, source-span overlays, and variant-lane pickers.

On 2026-07-02, the dogfooding agent (this document's author) ran a structured dogfood of that shipped Workbench with the user driving it directly. **Verdict: the consolidation succeeded at its stated goal (one tool, N-way comparison, vocabulary-aware) but failed the goal that actually matters.** Direct user quote after using it: *"It sucks and is not useful to a human... All this metadata is of little to no use to me for understanding as a human what the differences are."*

The concrete problem: every panel in the shipped Workbench is a **metadata artifact** — scorecards, miss tables, delta lists, object inspectors keyed by object IDs. None of them render the thing a human actually needs to compare: **the recap prose itself, with both graphs' pills overlaid on it, side by side.** That capability already exists — `GraphPreviewModule.tsx` (the *pre-consolidation* tool the Workbench was supposed to obsolete) is the only one of the four legacy tools that renders a true projected-markdown reader with hoverable pills — but it only ever shows one graph (the latest live run), never gold, and was never wired into the Workbench's two-lane shell.

**During the same conversation, the user reframed the goal further**, past "let me compare two projections" to **"let me directly author and correct the gold projection myself, with the LLM proposing metadata for spans and nodes I declare, so I stop needing an agent to hand-write `candidate_graph_gold.json`."** This is the bigger, more valuable target, and this handoff is written primarily to specify it in enough detail that a design/coding agent doesn't have to re-derive the shape from a one-paragraph idea.

---

## 2. Why this supersedes, rather than amends, the prior handoff

Read `HANDOFF-prime-design-graph-exploring-tool-consolidation.md` §4 (duplication analysis) — it is still accurate and still useful background on what each legacy tool actually did. What it got wrong, in hindsight, was the acceptance criterion: it defined success as "select and hold more than one live run at a time, show vocabulary provenance next to output, put gold + N runs side by side in one view" (§2 of that document) — all of which the Workbench delivers — without defining success in terms of **what a human visually needs to see to trust or distrust an extraction**. That gap is on this handoff's author (the same dogfooding agent), for guiding the prior design pass without insisting on a visual mock/walkthrough before 12 PRs' worth of metadata-panel work landed. Do not repeat that mistake here: before building author-mode UI, get eyes on a low-fidelity mock of the projection-with-pills-and-a-staging-tray interaction, not just a written spec.

---

## 3. The Workbench dogfood — skeptical findings (what's real, what's stale, what's missing)

The dogfooding agent read every file under `apps/live-control-ui/src/planSurface/graphReviewWorkbench/` (23 files) end to end and ran the tool live against `longmont-c2 / session-23` (a real gold+live session) before forming this verdict. Specific findings, so the next agent doesn't have to re-verify from scratch:

### 3.1 What's real and works

- `GraphReviewLiveProjectionPanel.tsx` correctly renders a live run's projection via `GraphProjectionReader`, fetching `UnionSupergraphProjectionResponse` from the existing `/union-supergraph/projection` endpoint. This is the one Workbench panel that does what the user actually wants — just only for the live side.
- `graphReviewDeltaUtils.ts::buildGraphReviewDeltaIndex()` is a genuinely well-built matching engine: it consumes the backend's `GoldReviewCompareResponse.match_pairs` (gold_id ↔ live_id ↔ score, one array per object kind) and `object_index` (gold/live object dictionaries), and produces a `GraphReviewDeltaIndex` of per-object deltas tagged `matched` / `gold_only` / `live_only` / `comparator_uncertain`, each carrying `sourceSpanRefIds` and `evidenceRefIds`. **This is the cross-lane linking mechanism the new design needs — it already exists and does not need to be rebuilt**, just consumed differently (drive lane-to-lane hover highlighting instead of feeding a delta table).
- `GraphReviewTwoLaneShell.tsx` is a real, working two-pane layout component (primary lane + reference lane). Structurally reusable as the review-mode skeleton.
- `GraphReviewLanePicker.tsx` correctly reuses `GraphGoldReviewSessionPicker`/`GraphGoldReviewRunPicker` for campaign/session/run selection — no need to rebuild this.
- All Workbench-related API calls in `apps/live-control-ui/src/api/liveApi.ts` are GET-only. The Workbench is, today, purely read-only end to end — confirmed by direct inspection, not assumption. This matters because author mode is a **new** write surface, not an extension of an existing one; treat it with the same care as Party Registry's write path (§6.4).

### 3.2 What's stale/misleading (fix regardless of the bigger pivot)

- `GraphReviewWorkbenchModule.tsx`'s introductory copy and `GraphReviewDeltaSummaryPanel.tsx`'s panel description both understate what's actually implemented (leftover placeholder language from early scaffold PRs, never updated as later PRs added real functionality). Low-risk copy fix, worth doing in the same pass as whatever ships next so the tool's own UI doesn't lie about its capability.
- `GraphReviewDeltaSummaryPanel.tsx` caps its list at 25 rows with no pagination — will silently truncate on any session with >25 deltas (routine for a full-session gold compare). Either paginate or make the cap configurable before relying on this panel for anything.
- `graphReviewReferenceLaneUtils.ts`'s "auto" reference-lane mode prefers a manual ablation variant over gold whenever both are available, with no visible toggle telling the user which one they're actually looking at — a silent footgun for exactly the kind of "am I comparing against gold or against a vocabulary variant" confusion this tool exists to prevent.

### 3.3 What's structurally missing — the actual blocker

**There is no gold-side projection.** `GraphReviewReferenceLanePanel.tsx` explicitly renders metadata, not projected source text — this was a conscious choice by the prior design pass, not an oversight, but it's the single biggest reason the tool "sucks" per the user's assessment. The reason it wasn't built: gold evidence resolution (`src/graph_memory/source_span.py::resolve_gold_evidence_refs()`) is designed to resolve **one evidence ref at a time**, on demand, to a `GoldReviewEvidenceResolvedRef` (`source_anchor_id`, `preview_snippet`, `paragraph_text`, `line_start`, `line_end`) — there is no bulk "give me the whole gold graph as a renderable document" endpoint analogous to `/union-supergraph/projection`. Building one is real but bounded work (§6.1) — most of the underlying data (evidence anchors, the gold's own normalized recap copy) already exists; what's missing is the assembly step.

**A related landmine, already found and worth stating explicitly so it isn't rediscovered the hard way:** the gold fixture's own copy of the normalized recap (`evals/graph_memory_layer/examples/session_1_recap_ingest/expected_normalized_recap.md`) and a live run's copy (`out/graph_memory/runs/.../normalized_recap_source.md`) have **drifted frontmatter**, which shifts line numbers between the two documents. Any design that tries to reuse gold's `line_start`/`line_end` against a *live* run's markdown will silently misalign. The fix is straightforward as long as it's designed in from the start: the gold projection must render the gold fixture's **own** copy of the recap markdown (never the live run's), and per-node/edge text anchoring must use text-snippet matching (`paragraph_text`/`preview_snippet` — already resolved fields) rather than raw line numbers, exactly the way `apps/live-control-ui/src/planSurface/graphProjectionReader/sourceSpanHighlight.ts` already does DOM-side text matching for the live lane. Two self-consistent documents, each internally anchored by text match, not by a shared coordinate system.

---

## 4. The pivot: from "review" to "review + author" — what the user actually asked for, verbatim

Quoting directly, because the shape of this request is unusual enough that paraphrasing risks losing the specific mechanics:

> "We need a gold crafting tool. Like a data labeling tool. Starts as a projection of the processed raw markdown recap. I can highlight a word, or phase, and layer on meta data of the type we are building. I can look at the gold projection and edit it, by clicking the highlighted bits. I can draw and label edges by clicking another node or word to become a node. And most important, I can pass these to the backend, to look at it in context, with my declaring it a type of node and we pass it to the LLM to construct and propose more metadata. FROM this, we can be mining my own data to further refine ingestion, and be improving the gold with my manual human review."

Unpacking this into concrete primitives (this is the part that needs to survive into implementation unchanged):

1. **Start from a projection of the recap markdown** — the same rendering substrate as review mode, not a new editor widget.
2. **Select text → declare a node.** Highlighting a word/phrase and tagging it with a node type is span-to-node authoring — the reverse of what review mode does (review mode takes existing nodes and shows their spans; author mode takes a span and mints a node).
3. **Click existing highlighted spans to edit them.** Nodes already declared (whether by the human or by a prior LLM proposal that was accepted) are click-to-edit, not just click-to-view.
4. **Draw edges by clicking two things.** Click node A, click node B (where "B" can be an already-declared node OR a fresh span that becomes a node in the same gesture), then label the edge (predicate).
5. **Send a declared node (with its type) to the LLM, in context, to get more proposed metadata back.** This is the AI-assist loop: human commits to one judgment call (this span is a `character` named X), LLM uses that seed plus surrounding context to propose things *it* thinks follow — more nodes, more edges, attributes.
6. **The result is not just an edited gold fixture — it's a mineable record of human-vs-LLM judgment**, intended to feed back into refining the ingestion pipeline itself (prompt tuning, taxonomy decisions, consolidation policy), not just to produce a better one-off gold file.

This is a genuinely different tool category than "diagnostic viewer." It is closer in spirit to Party Registry (write-capable, human-directed, backend-persisted) than to Graph Gold Review — except unlike Party Registry, it has an LLM actively participating in the loop, which none of this repo's existing write surfaces do.

---

## 5. Decisions already made in the design conversation (do not re-ask these)

The user answered two structured rounds of clarifying questions before requesting this handoff. Full answers, verbatim intent preserved:

**Round 1 — review-mode mechanics (answered, then partially superseded by Round 2's bigger reframe — kept here because they still constrain review mode specifically):**
No structured answers were given in round 1 (the user moved directly to the authoring idea instead) — the dogfooding agent's own defaults, stated and NOT objected to when restated in round 2's summary, are:
- Lane generality: **any-vs-any** (gold, live-baseline, live-vocab-run, or a gold-in-author-mode can occupy either lane), not hardcoded gold-left/live-right.
- Sync behavior on hover: **highlight-only**, with an explicit "jump to match" click/keyboard action rather than auto-scroll (avoid disorienting jumps).
- Unanchored objects (gold-only "missed" / live-only "extra"): **both** — inline distinct style (dashed/red = missed, amber = extra) in the prose itself, AND a compact unmatched list for scanning.
- Edge navigation: **purely text-anchored** — clicking an edge highlights/jumps to its endpoint spans in the prose; no separate node-link diagram view.
- Deprecation timing for the three legacy tools (Graph Preview, old Graph Gold Review tables, Vocabulary Review): **soft-deprecate** — leave reachable but labeled deprecated until the new tool has covered at least one real authoring session and one real review session.

**Round 2 — authoring-mode mechanics (explicitly answered by the user):**

| Question | Answer |
|---|---|
| Default entry state when opening the authoring tool | **Both, with a toggle** — "start blank" (raw markdown, zero nodes) vs. "start from run X" (seeded with a live run's proposals as a correction baseline) |
| What the LLM-assist action operates on | **Both modes** — a fast *per-seed expand* (one declared node/edge → LLM proposes locally-connected things) AND a heavier *whole-document reflow* (after seeding several anchors, re-run extraction using seeds as priors/constraints) |
| How to distinguish LLM proposals from confirmed human labels | **Confirm-gate only** — no persisted tri-state visual language in the saved document. Proposals sit in a staging tray pending accept/reject/edit; only accepted items ever become part of the saved graph. The document itself never shows "unconfirmed" state. |
| Fidelity of capturing labeling decisions for later mining | **Dedicated append-only event log** — richer than a before/after fixture diff. Every staging-tray decision (seed → LLM proposal → human accept/reject/edit → final value) gets logged separately from the gold fixture file itself. |
| Write-safety model for committing authored changes | **Reuse the two-phase pattern** already established by Party Registry (`prepare_party_registry_session_roster_write` / `commit_party_registry_session_roster_write` in `apps/live_control_server/services/party_registry_write.py` — prepare returns a diff + confirm token computed from a content+file-state hash; commit requires that token). Given authoring is many small incremental edits, batch this: edits accumulate client-side/in-session, and "save" triggers one prepare→diff→confirm→commit cycle against the fixture file, not one round-trip per node/edge. |
| Relationship between review mode and author mode | **One tool, shared substrate** — author mode is an "edit" toggle on whichever lane holds a gold-shaped object, using the same two-lane/projection component family as review mode. Not two separate tools that happen to share a rendering component. |

---

## 6. Target design

### 6.1 Shared substrate

Both modes render through the same component family: a markdown-with-pills projection reader (extend `GraphProjectionReader` / `apps/live-control-ui/src/planSurface/graphProjectionReader/`), fed by a payload shaped like `UnionSupergraphProjectionResponse` (`markdown`, `node_views` keyed by stable node id with `evidence_badges`, `mentions` with offset/text anchors into that markdown). Both modes place this reader inside `GraphReviewTwoLaneShell`'s two-pane layout. What differs between modes is (a) which endpoint populates a given lane's payload, and (b) whether that lane's reader is instantiated read-only or with edit affordances turned on.

**Design implication worth calling out explicitly:** because author mode needs stable node/edge IDs that survive edits, and needs text-span anchors that can be *created* (not just displayed), the projection payload contract should be designed edit-friendly from the start — even though write endpoints may land in a later implementation slice than the read-only projection endpoint. Retrofitting an edit-friendly ID/anchor scheme onto a read-only-only contract after the fact is the expensive path; design it in now.

### 6.2 Review mode

- **Lane sources**: gold (via the new gold-projection endpoint, §7.1), any live run (existing `/union-supergraph/projection`), or a manual ablation variant (existing manual-review data, reshaped into the same payload contract if feasible — check `graph_manual_review.py`'s response shape before assuming a 1:1 fit).
- **Cross-lane linking**: on hover/click of a pill in lane A, look up its `matched` counterpart via `buildGraphReviewDeltaIndex()` (already exists, §3.1) and highlight the paired pill in lane B. `gold_only`/`live_only` deltas get the inline dashed/amber treatment (§5, Round 1 answers) with no cross-lane counterpart, by definition.
- **Metrics/scorecard**: keep, but demote to a thin strip above the panes (reusing `GraphGoldReviewScorecard`), not the primary view.
- **Explicitly NOT changing**: the comparator engine itself (`compare_gold_review()`, `live_vs_gold_compare.py`) — this handoff is about presentation and authoring, not re-deriving match scores.

### 6.3 Author mode — the core of this handoff

**Entry point.** A lane in author mode starts either blank (raw/normalized markdown for a session, zero nodes) or seeded from an existing run/gold fixture (its nodes pre-populated as an editable starting point). Toggle, surfaced per-lane, not a global app setting.

**Primitive 1 — span → node.** User selects a text range in the rendered markdown. UI prompts for `node_type` (drawn from the existing type vocabulary in `src/graph_memory/candidate_graph_preview.py::NODE_TYPES` — including `landmark`, `quest`, `combat_encounter`, added in the 2026-07-01 C1S1 gold remediation) and a label. On confirm, this mints a node whose `evidence_refs[0]` is an anchor pointing at the selected span, in the same shape gold nodes already use (`source_ref_id`, `source_artifact_id`, `source_anchor_id`, `can_open_source: true`, `can_highlight_span: true` — see `candidate_graph_gold.json` lines 25–35 for the exact shape to match). **Design decision needed from the implementing agent:** minting a new `source_anchor_id` for a freshly-selected span (not previously cataloged in `source_span_seed_refs.json`) needs an anchor-registration step — either extend that catalog at authoring time, or move to a lighter-weight anchor scheme (e.g. store the literal selected text + an ordinal, resolved lazily) that doesn't require a pre-built catalog. The existing catalog approach was designed for known-in-advance gold fixtures, not live incremental authoring; do not assume it transfers unchanged.

**Primitive 2 — node/span → edge.** User clicks node A (existing or about to be minted), then clicks node B (existing, or a fresh span that becomes a node via Primitive 1 in the same gesture), then picks/confirms a predicate. **Open question for the design agent:** should the predicate picker constrain choices to a known-valid vocabulary for the (type_A, type_B) pair (consistent with the cross-class identity/consolidation policy work referenced in `Backlog.md`'s vocabulary-ablation entry), or allow free text always? Recommend starting permissive (free text with a suggested-list autocomplete from observed predicates) and tightening later once there's enough authored-edge volume to know what a validated vocabulary should even contain — do not block v1 on solving the predicate-taxonomy question.

**Primitive 3 — LLM-assist.** Two triggerable actions, both going through the Responses API structured-extraction path (`text.format` json_schema strict — non-negotiable per `.cursor/rules/responses-api-structured-extraction.mdc`; do not build a prompt-only-JSON path for this):
- *Per-seed expand*: input = the just-declared node/edge + a window of surrounding markdown context (reuse the same context-window logic the category extractors already use, e.g. `src/graph_memory/extraction/category_candidate_graph_extractor.py`'s per-pass context assembly, rather than inventing a new windowing heuristic). Output = a small set of proposed additional nodes/edges/attributes, schema-constrained.
- *Whole-doc reflow*: input = all currently-declared (human-authored + previously-accepted) nodes/edges as priors, plus the full document. Output = a fuller proposed node/edge set, using existing seeds as anchors/constraints rather than re-discovering them from scratch. This can plausibly reuse the existing category-pass extraction machinery with the human's seeds injected as a vocabulary/context packet (the same `ContextVocabularyPacket` mechanism already wired into the runtime path per Backlog Follow-up 5) rather than requiring a wholly new extraction pipeline — investigate this reuse path before building a parallel one.

Both actions land their output in a **staging tray**, never directly in the document. Each staged item is accept / reject / edit-then-accept. Nothing staged is visible in the projection itself until accepted (per the Round 2 "confirm-gate only" answer) — the rendered document only ever shows committed state.

**Save/commit.** Author-mode edits accumulate client-side across a session. A "save" action triggers one prepare→diff→confirm-token→commit cycle (§6.4) against the target gold fixture file — mirroring, not reimplementing, Party Registry's existing pattern.

**Authoring event log.** Every staging-tray resolution (not just saves) appends one record to a dedicated log, separate from the gold fixture:

```jsonc
{
  "schema": "dmb_graph_gold_authoring_event_v1",
  "event_id": "...",
  "campaign_id": "...",
  "session_id": "...",
  "timestamp": "...",
  "trigger": "per_seed_expand | whole_doc_reflow | manual",
  "seed": { "node_id": "...", "node_type": "...", "label": "...", "span_text": "..." },
  "llm_proposal": { /* raw schema-constrained model output, or null for a fully manual entry */ },
  "human_decision": "accept | reject | edit",
  "final_value": { /* what actually got committed, if accepted/edited */ }
}
```
This is the artifact that makes "mining my own data to further refine ingestion" possible later — it's what lets a future pass ask "where does the model's first guess systematically diverge from what the human actually keeps," which a plain fixture diff cannot answer (a diff only shows the *final* state, not what was offered and rejected along the way).

---

## 7. New backend contracts needed (concrete shapes, not yet built)

### 7.1 Gold projection endpoint

New endpoint, sibling to the existing `/union-supergraph/projection`, returning a payload shaped identically to `UnionSupergraphProjectionResponse` but sourced from a gold fixture:
- `markdown` = the gold fixture's own normalized recap copy (e.g. `expected_normalized_recap.md`) — never a live run's copy (§3.3 drift issue).
- `node_views` = one entry per gold node, `evidence_badges` built from `resolve_gold_evidence_refs()`'s existing per-anchor resolution (`source_span.py`), assembled in bulk instead of one-at-a-time.
- `mentions` = anchored via text-snippet matching (`paragraph_text`/`preview_snippet`, already produced by the existing resolver) against the gold markdown — reuse the matching strategy `sourceSpanHighlight.ts` already implements for the live side, applied to a second document.

### 7.2 LLM-assist actions

Two new structured-extraction call sites (per-seed expand, whole-doc reflow — §6.3 Primitive 3). Each needs:
- A JSON-schema module (follow the pattern of `src/graph_memory/extraction/category_candidate_graph_schema.py` or `src/agent/ingest_hints_output_schema.py` — manual JSON Schema, `strict: True`, every `properties` key in `required`, nullable types for anything optional).
- A new `MODEL_POLICY.json` `actions` entry per call site (e.g. `graph_gold_authoring_seed_expand`, `graph_gold_authoring_document_reflow`) — do not hardcode a model id. `graph_memory_category_extraction` (currently mapped to `fast_smart_mini`) is the closest existing precedent for tier; investigate whether the same tier is appropriate for these smaller, more targeted calls or whether per-seed expand can run on `cheapest`.
- Client construction via `load_dungeonmindbuddy_dotenv()` → `OpenAI()`, calling through the centralized `responses_create`/`responses_parse` helpers in `src/llm/api_client.py` — not a bespoke client instantiation.
- Explicit handling of `refusal`/`incomplete` responses as failures surfaced to the staging tray (e.g. "LLM assist failed: <reason>"), not silently defaulted to an empty proposal.

### 7.3 Authoring event log

Append-only, one file per authoring session (or per campaign/session-id, TBD by the design agent) under a path consistent with existing artifact conventions (likely alongside other `out/graph_memory/` or `evals/graph_memory_layer/artifacts/` output — git-ignored, per `.cursor/rules/corpus-pii-and-llm-payloads.mdc`, since it will contain corpus text snippets and LLM traces that must stay local).

### 7.4 Gold fixture write endpoints

Following Party Registry's exact pattern (`party_registry_write.py`):
- `prepare_graph_gold_authoring_write(...)` — takes the accumulated in-session edits, computes the resulting fixture content, returns a diff + a confirm token derived from `(target_relpath, new_content, current_file_state_token)` the same way `_confirm_token()` does today.
- `commit_graph_gold_authoring_write(...)` — requires that exact confirm token; rejects if the file changed underneath (same conflict-detection semantics as `PartyRegistryWriteConflictError`).
- Batched per §6.3 "Save" — one prepare/commit cycle per save action, not per node/edge.

---

## 8. Non-negotiables and guardrails carried forward + new ones

Carried forward from the prior handoff (still true, now spanning more surface area):
- The union supergraph (`src/graph_memory/union_supergraph/`) is the durable read model; `evals/graph_memory_layer/` is proof/dogfood machinery. Keep that boundary even as backend services consolidate further.
- Preview-only run artifacts under `out/graph_memory/runs/` are git-ignored/ephemeral by design — any UI touching them must handle a run disappearing between page loads gracefully.
- Vocabulary is not settled science — surface it as inspectable, don't editorialize a verdict into the UI.

New, specific to author mode:
- **This is the first write path in this tool family.** Every guardrail Party Registry already earned (two-phase confirm, conflict detection on stale file state, no silent overwrite) applies here with equal weight — gold fixtures are hand-curated evaluation ground truth; a silent bad write corrupts every recall number computed against it going forward.
- **Corpus PII discipline applies to the authoring event log and every LLM-assist call**, not just to the fixture file — per `.cursor/rules/corpus-pii-and-llm-payloads.mdc`, this data stays local (git-ignored artifacts, no external tool calls with corpus text as payload), and LLM-assist calls go through the already-configured DungeonMindBuddy OpenAI client, never an ad hoc one.
- **Structured-extraction rule applies to both new LLM-assist call sites without exception** — no "return JSON in the prompt" shortcut, even for what feels like a small/quick call.
- **Do not let author mode's write capability leak into review mode.** A lane that isn't explicitly toggled into edit mode must stay strictly read-only — the existing review-mode guarantee (§3.1, all-GET today) should remain true for any lane not actively being authored.

---

## 9. Worked acceptance test (use this to know when a slice is done)

Minimum viable review-mode slice: open `longmont-c1 / session-1`, put gold in the left lane and the `20260701T215207Z` live+vocabulary run (referenced in Backlog Follow-up 5) in the right lane, both rendered as prose-with-pills (not tables). Hover the gold node for "the rat-clearing job" (`quest` type) and see the live lane highlight its matched counterpart (or clearly show it as unmatched, if the label-similarity gap from Follow-up 5 still applies) — without leaving the projection view.

Minimum viable author-mode slice: open a blank projection for a short, real recap paragraph. Select a phrase, declare it a `character` node. Trigger per-seed LLM-assist. See ≥1 proposal land in a staging tray. Accept one, reject one. Save. Confirm the resulting `candidate_graph_gold.json`-shaped output contains exactly the accepted node(s) and nothing from the rejected proposal, and that an authoring-event-log entry exists recording both the accept and the reject with the LLM's original proposal preserved in the reject record too (not discarded).

---

## 10. Suggested sequencing for the next agent

1. Do the low-fidelity mock/walkthrough step this handoff's author skipped last time (§2) — sketch the two-lane-with-pills review view and the author-mode staging-tray interaction, get user sign-off on the *visual* shape, before writing the gold-projection endpoint.
2. Build the gold-projection endpoint (§7.1) and wire it into a lane of the existing `GraphReviewTwoLaneShell` — this alone (no authoring yet) directly fixes the dogfood's loudest complaint and is independently valuable.
3. Fix the two low-risk stale-copy/pagination items (§3.2) opportunistically in the same pass.
4. Decide the span-anchor minting scheme for freshly-authored spans (§6.3 Primitive 1's open question) — this blocks all of author mode and deserves its own explicit decision record before coding.
5. Build author mode's write path (§7.4) reusing Party Registry's pattern directly — resist the urge to design a "better" write pattern; consistency across this repo's two write surfaces has its own value.
6. Build the two LLM-assist actions (§7.2) last — they depend on the projection contract and the write path both being stable, and are the highest-uncertainty, most iteration-prone piece (prompt/schema tuning will need real dogfood cycles, same as every other extraction pass in this repo).
7. Only after author mode has been used for at least one real gold-authoring session: revisit soft-deprecating Graph Preview / old Graph Gold Review tables / Vocabulary Review (§5, Round 1 answer on deprecation timing).

---

## 11. Reference index (all paths repo-relative)

**This handoff's direct motivation:**
- `Docs/Plans/HANDOFF-prime-design-graph-exploring-tool-consolidation.md` — the superseded prior handoff (§4's duplication analysis is still valid background)
- `Backlog.md` → search `## [DOING] Graph memory encounter/job extraction spike` → Follow-up 6

**Workbench (dogfooded, findings in §3 of this document):**
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/` — all 23 files (`GraphReviewWorkbenchModule.tsx`, `GraphReviewTwoLaneShell.tsx`, `GraphReviewLiveProjectionPanel.tsx`, `GraphReviewReferenceLanePanel.tsx`, `graphReviewReferenceLaneUtils.ts`, `GraphReviewDeltaSummaryPanel.tsx`, `graphReviewDeltaUtils.ts`, `graphReviewDeltaTypes.ts`, `GraphReviewMetricPanel.tsx`, `GraphReviewLanePicker.tsx`, `graphReviewSourceSpanOverlayUtils.ts`, plus evidence-split/variant-lane/source-span-rail panels)
- `apps/live-control-ui/src/planSurface/graphProjectionReader/sourceSpanHighlight.ts` — the DOM text-matching utility to reuse for gold-side anchoring
- `apps/live-control-ui/src/planSurface/graphPreview/GraphPreviewModule.tsx`, `GraphIngestProjectionPanel.tsx` — the pre-consolidation tool that already does true prose+pill projection (one graph only, no comparison)
- `apps/live-control-ui/src/api/types.ts` — `UnionSupergraphProjectionResponse`, `GraphProjectionNodeView`, `GoldReviewCompareResponse`, `GoldReviewObjectIndexEntry`, `GoldReviewEvidenceResolvedRef` (all read in full while researching this handoff)
- `apps/live-control-ui/src/api/liveApi.ts` — confirms all current Workbench endpoints are GET-only

**Backend (existing, to extend):**
- `apps/live_control_server/services/graph_gold_review.py` — `compare_gold_review()`, `build_gold_review_evidence_diff()`, `_resolve_evidence_refs()`
- `src/graph_memory/source_span.py` — `resolve_gold_evidence_refs()`, `ResolvedEvidence`/`EvidenceResolutionReport` shapes
- `apps/live_control_server/services/party_registry_write.py` — the two-phase write pattern to replicate (`prepare_party_registry_session_roster_write`, `commit_party_registry_session_roster_write`, `_confirm_token`, `PartyRegistryWriteConflictError`)
- `apps/live_control_server/routes/graph_preview.py` — current router housing all graph-preview/gold-review/manual-review endpoints; new endpoints likely land here or in a new sibling router

**Gold fixture format (the target data shape for everything author mode produces):**
- `evals/graph_memory_layer/examples/session_1_candidate_graph_gold/candidate_graph_gold.json` — read in full; node/edge/evidence_refs/semantic_state shape
- `evals/graph_memory_layer/examples/session_1_recap_ingest/source_span_seed_refs.json` — existing anchor catalog (built for known-in-advance fixtures; §6.3 Primitive 1 flags why this needs rethinking for live authoring)
- `evals/graph_memory_layer/examples/session_1_recap_ingest/expected_normalized_recap.md` — gold's own recap copy (the drift issue in §3.3)
- `src/graph_memory/candidate_graph_preview.py::NODE_TYPES` — current node-type vocabulary (includes `landmark`/`quest`/`combat_encounter` post-2026-07-01 remediation)
- `src/graph_memory/identity_resolution.py` — cross-class consolidation policy (relevant to the predicate-vocabulary open question in §6.3 Primitive 2)

**Structured extraction / model policy (governs §7.2's new LLM-assist calls):**
- `.cursor/rules/responses-api-structured-extraction.mdc` — canonical examples: `src/agent/ingest_hints_output_schema.py`, `src/live_play/live_turn_classification_schema.py`, `src/graph_memory/extraction/category_candidate_graph_schema.py`, `src/llm/api_client.py`
- `MODEL_POLICY.json` (repo root, `/home/drakosfire/Projects/DungeonOverMind/MODEL_POLICY.json`) — existing `graph_memory_category_extraction` action (→ `fast_smart_mini`) as the closest tier precedent
- `src/bootstrap_env.py::load_dungeonmindbuddy_dotenv()` — required before any new OpenAI client construction

**PII/write-safety guardrails specific to this handoff:**
- `.cursor/rules/corpus-pii-and-llm-payloads.mdc` — applies to the new authoring event log (§7.3) and both LLM-assist call sites
- `.cursor/rules/dungeonbuddy-git-workflow.mdc` — single-branch-friendly; no need for heavy PR ceremony on this repo

**Current `main` tip at handoff time:** `5fa8c23` (the vocabulary-wiring + 3-way comparison commit from Backlog Follow-up 5, on top of the Workbench PRs #245–#256).
