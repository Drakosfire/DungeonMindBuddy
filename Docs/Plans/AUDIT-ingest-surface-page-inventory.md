# Audit — What's Actually On the `/ingest` Page

**Status:** Discussion draft, not a plan yet
**Date:** 2026-07-05
**Workstream:** Ingestion surface (`cursor/ingest-surface`)
**Related:** `Docs/Plans/ROADMAP-graph-review-gold-authoring-workbench.md`, `Docs/Plans/FOLLOWUP-raw-dmb-node-links-and-duplicate-projected-objects.md`

## 1. Why this doc exists

First slice of ingestion-surface work is "the page is way too much." Before cutting anything, this
is a straight inventory of every section currently rendered at `/ingest`, who it's for, and whether
it's always on screen or tucked away. The goal is to have a shared, accurate map before deciding
what moves behind the toolbox paradigm, what gets deleted, and what stays as the GM-facing core loop.

Render path: `MemoryIngestPage.tsx` → `AppChrome` (nav) → `GraphReviewWorkbenchModule.tsx`, which is
one continuously-scrolling stack — there is currently no toolbox/tab selection on this page at all.
Every section below renders unconditionally once its data is ready; nothing is opened on demand.

## 2. Full inventory, top to bottom

| # | Section | Component | Lines | Always visible? | Audience |
|---|---|---|---|---|---|
| 1 | Page header (title, campaign/session/route in a collapsed `<details>`) | `MemoryIngestPage.tsx` | — | Yes (details collapsed) | GM |
| 2 | Workbench header (kicker + h2 + lede paragraph) | `GraphReviewWorkbenchModule.tsx` | — | Yes | GM |
| 3 | "Advanced / Debug: Mock UX Scaffold" | `GraphReviewAuthoringWorkbenchModule.tsx` | 100 | Collapsed `<details>` (demoted in #273) | Dev only — entirely mock/fixture data, not real campaign data |
| 4 | Campaign picker + session tab pills + run picker | `GraphReviewLanePicker.tsx` | 107 | Yes | GM |
| 5 | Gold lane card + Live lane card, each with a counts line and a collapsed "Advanced details" (~10-20 metadata fields each) | `GraphReviewLaneCards.tsx` | 117 | Yes (summary line); details collapsed | GM sees summary; details are dev/diagnostic |
| 6 | Mode switch bar (Review / Author Draft toggle) | `GraphReviewLiveProjectionPanel.tsx` | inline | Yes | GM |
| 7 | "Gold vs Live" comparison summary strip (matched/gold-only/live-only counts) | same | inline | Yes | GM/dev |
| 8 | Two-lane projected prose (Gold Fixture pane + Live Run pane, clickable `dmb-node` pills) | `GraphReviewProjectionLane.tsx` (×2) | 347 | Yes | **GM — this is the core reading experience** |
| 9 | Selected-object dialog (opens on pill click): node card, relationship card, Author Draft actions, "Find existing object" resolver | `GraphReviewProjectedInteractionSurface.tsx` + `GraphReviewNodeGameCard.tsx` + `GraphReviewRelationshipCard.tsx` + `ExistingObjectResolverPanel.tsx` | 195+108+74+237 | On demand (click) | GM |
| 10 | Author Draft text-selection actions ("Stage node from selection") | inline in `GraphReviewLiveProjectionPanel.tsx` | inline | Only in Author Draft mode | GM (authoring) |
| 11 | Local staging tray (ephemeral list of staged proposals) | `GraphReviewLocalStagingTray.tsx` | 103 | Only in Author Draft mode | GM (authoring) |
| 12 | Prepare/Commit/Verify panel | `GraphReviewAuthoringPreparePreviewPanel.tsx` | 96 | Only in Author Draft mode | GM (authoring) |
| 13 | Delta inspector panel (details for whichever node is "selected for delta") | `GraphReviewDeltaInspectorPanel.tsx` | 180 | Yes, always rendered (empty state if nothing selected) | Dev/diagnostic |
| 14 | Source span rail (paragraph-by-paragraph delta highlighting) | `GraphReviewSourceSpanRail.tsx` | 69 | Yes | Dev/diagnostic |
| 15 | Source span inspector panel | `GraphReviewSourceSpanInspectorPanel.tsx` | 135 | Yes | Dev/diagnostic |
| 16 | Evidence split panel (gold vs. live evidence diff for a selected delta) | `GraphReviewEvidenceSplitPanel.tsx` | 166 | Yes | Dev/diagnostic |
| 17 | Variant lane panel (manual review bed + variant picker) | `GraphReviewVariantLanePanel.tsx` | 76 | Yes — **rendered twice** (once in the `projectionStatus === "ready"` branch, once in the `!== "ready"` branch) | Dev/diagnostic (manual test beds, not real campaign data) |
| 18 | Variant inventory panel (table of variant rows) | `GraphReviewVariantInventoryPanel.tsx` | 20 | Yes — also duplicated across both branches | Dev/diagnostic |
| 19 | Variant object inspector panel | `GraphReviewVariantObjectInspectorPanel.tsx` | 37 | Yes — also duplicated | Dev/diagnostic |
| 20 | Delta summary panel (bottom-of-page rollup of all deltas) | `GraphReviewDeltaSummaryPanel.tsx` | 79 | Yes | Dev/diagnostic |
| 21 | "Secondary metrics" / Gold-vs-live smoke alarms (scorecard + miss tables) | `GraphReviewMetricPanel.tsx` → `GraphGoldReviewScorecard` + `GraphGoldReviewMissTables` | 36 (+2 more files) | Yes | Dev/diagnostic |

That's **21 distinct sections**, 9 of which are unconditionally rendered diagnostic/dev panels
(#13–#21) stacked below the actual reading surface, plus one dev-only mock module (#3, now at
least collapsed) and duplicated variant panels (#17–#19 render twice depending on projection
status branch).

## 3. Grouping by role

**GM core loop (should be the whole page, most of the time):**
- Campaign/session/run pickers (#4)
- Lane summary cards, collapsed detail (#5)
- Two-lane projected prose (#8) — this is "read campaign prose," the actual point of the tool
- Selected-object dialog (#9) — click a pill, see what it is, optionally stage a correction
- Author Draft actions + staging tray + prepare/commit (#10–#12) — only when the GM has switched into authoring

**Diagnostic / dev-only, currently always-on (#13–#21):**
- Delta inspector, source span rail + inspector, evidence split, variant lane/inventory/inspector (×2), delta summary, secondary metrics scorecard
- None of these gate on Author Draft mode or a click — they render continuously underneath the prose, whether or not the GM asked for them
- Several exist purely to validate the *comparison machinery itself* (gold vs. live matching), not to help a GM read or author a session

**Dev-only mock/fixture:**
- The Mock UX Scaffold (#3) — already demoted to a collapsed `<details>` in #273, still ships mock data with no real campaign hookup

## 4. This isn't a new problem — the roadmap already said so

`Docs/Plans/ROADMAP-graph-review-gold-authoring-workbench.md` (dated 2026-07-02, written before this
page existed in its current form) already states the guardrails this page violates:

> - The right rail is collapsed by default.
> - Evidence/debug details are explicit drill-ins.
> - Keep scorecard as a thin summary strip.
> - "R11 — Remove or hide old surfaces... The normal toolbox exposes one Graph Review + Gold
>   Authoring Workbench, not several competing graph review destinations."

None of #13–#21 are currently drill-ins or collapsed. They're all just... there, all the time,
whether the projection loaded successfully or not (there are two nearly-identical always-on blocks
for the variant panels, one per branch of `projectionStatus`).

## 5. The toolbox paradigm already exists elsewhere in this codebase

`/plan` (`PlanToolBar.tsx`) already does what the user is asking for: a strip of tool buttons
("Recap workflow," "Graph-linked reader," "Graph evidence," "Workbench") that open **one focused
workflow beside the canvas at a time.** Copy from that component: *"Open focused workflows beside
the canvas. Tools stay out of the document until you choose them."*

`/ingest` does not use this pattern at all — everything is inline, all the time, in one scroll.

## 6. Open questions for discussion

1. **Is the diagnostic block (#13–#21) needed on `/ingest` at all**, or is it leftover machinery
   from validating the delta/comparison system during the Roadmap's R2/R3 milestones, that now
   belongs behind a single "Diagnostics" toolbox entry (or deleted if the comparison machinery is
   considered proven)?
2. **Should Author Draft (#10–#12) be its own toolbox tool** rather than an inline mode toggle that
   changes what's rendered under the same scroll?
3. **What does "GM opens `/ingest` and sees" look like in the target state?** E.g.: pick
   session/run → read two-lane prose → click objects → done, with everything else reachable via
   an explicit toolbox button rather than always mounted.
4. Do the duplicated variant panels (#17–#19 rendered in both projection branches) indicate the
   variant/manual-bed feature is dead weight, or does it need its own toolbox entry too?
5. Does the Mock UX Scaffold (#3) get deleted now that the real two-lane review path (#8-9) works,
   or does it still serve a purpose (e.g., as a fixture-only demo for testing pill interactions
   without live data)?

## 7. Decisions (2026-07-05)

| Question | Decision |
|---|---|
| Diagnostic block (#13–#21) | Collapse into **one "Diagnostics" toolbox entry**, opened on demand |
| Author Draft (#10–#12) | Becomes **its own toolbox tool**, opened explicitly, instead of an inline mode toggle on the main scroll |
| Mock UX Scaffold (#3) | **Delete** — real two-lane path works, mock is dead weight |
| Default `/ingest` landing view | Pickers + lane summary cards + two-lane prose only. Everything else is a toolbox click away. |

## 8. Reusable architecture: `/plan` already has the toolbox machinery

`/plan` implements exactly the drawer pattern this page needs, and it is directly reusable:

- `ProjectionProvider` / `useProjection()` (`projectionContext.tsx`) — tracks which tool is
  active, exposes `openTool(toolId)` / `close()`.
- `AdaptiveProjectionContainer` — renders a "Tools" toggle button, a slide-out drawer with a
  toolbox nav strip, and a body that renders whichever tool is active via `projectionRegistry`.
- `PlanToolBar` — the always-visible entry strip ("Open focused workflows beside the canvas.
  Tools stay out of the document until you choose them.").

`/ingest` (`MemoryIngestPage.tsx`) currently has **none** of this — it doesn't wrap its content in
`ProjectionProvider`, and `GraphReviewWorkbenchModule` doesn't render an `AdaptiveProjectionContainer`.
Standing up the same drawer pattern for `/ingest` (two tool entries: **Diagnostics**, **Author
Draft**) is the direct implementation path implied by the decisions above, rather than inventing a
new toolbox mechanism.

**Deletion follow-up before removing the Mock UX Scaffold:** confirm nothing else imports
`GraphReviewAuthoringStagingTray.tsx`, `GraphReviewWorkbenchLaneHeader.tsx`,
`GraphReviewWorkbenchModeStrip.tsx`, `GraphReviewRelationshipChips.tsx`, or
`graphReviewAuthoringMockData`/`graphReviewAuthoringState` before deleting them alongside
`GraphReviewAuthoringWorkbenchModule.tsx` — some of these (relationship chips, node/relationship
cards) are shared with the real review path and must stay.
