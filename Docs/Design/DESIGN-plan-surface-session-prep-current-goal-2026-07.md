# Design — Plan Surface Session-Prep Current Goal

**Status:** Current product checkpoint  
**Date:** 2026-07-10  
**Scope:** `/plan`, session preparation, graph-memory consumption, planning-oriented Agent Interaction, and the Tiptap/Markdown planning board  
**Architecture authority:** `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`  
**Post-dogfood graph-memory re-anchor:** `Docs/Design/DESIGN-plan-graph-memory-reanchor-after-dogfood-2026-07.md`  
**Graph Review authority:** `Docs/Design/DESIGN-graph-object-authoring-surface.md`  
**Graph Review evidence / pause point:** `Docs/Reports/SPIKE-CLOSEOUT-graph-review-authored-memory-2026-07.md`  
**Union Supergraph authority:** `Docs/Design/GRAPH-MEMORY-UNION-SUPERGRAPH-PROJECTION.md`  
**Source-vocabulary boundary:** `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`

---

## 1. Current decision

`/plan` is the session-prep cockpit. `/ingest` is the memory-ingestion, Graph Review, and authored-memory correction cockpit.

```text
/ingest teaches DungeonBuddy what campaign memory means.
/plan uses that memory to help the GM prepare.
/play uses that memory at the table.
```

The durable surface family remains **Plan / Play / Build**. Combat is an operational lane inside `/play`, not a fourth durable surface. Build remains named but intentionally unspecified until Plan and Play dogfood prove a concrete durable-authoring need.

## 2. Product promise

The GM can open `/plan`, see the campaign and session being prepared, write and revise one planning board, ask grounded questions, follow references, inspect game-facing object cards, and bring in relevant statblocks, roll tables, and source context without leaving the planning flow.

The immediate purpose is not to finish every planned surface abstraction. It is to dogfood one real upcoming session-prep loop.

## 3. What `/plan` is

- An editable Tiptap/Markdown planning board: the central work object for session prep.
- A clear campaign, prep-session, and relevant-memory/source context.
- Source-grounded retrieval and reference-chip navigation, with opaque reference locators resolved by the shared resolver.
- Game-facing selected-object cards that lead with useful identity, related objects, and source context rather than graph metadata.
- Planning projections for statblocks, roll tables, and related corpus content.
- Planning-oriented Agent Interaction that carries pointers, citations, freshness/proof state, and questions—not corpus bodies or graph internals.
- A lightweight memory-status or escalation affordance when preparation reveals that campaign memory needs correction.

The existing `/plan` route, local Tiptap canvas, SurfaceConfig/projection seams, reference resolver, edit-capability seam, and locally dogfooded Agent Interaction pieces are implementation scaffolding for this goal. Its North Gate / Session 23-oriented configuration and local/localStorage-heavy canvas are transitional dogfood state, not a session-independent product completion claim.

## 4. What `/plan` is not

`/plan` is not, by default:

- the Graph Review Workbench;
- a graph diagnostics or comparison surface;
- an identity-merge console;
- an Author Draft, authored-overlay, or event-log writing surface;
- a graph-gold fixture editor or general graph database editor;
- a recap-ingest wizard;
- the combat / at-table cockpit; or
- a player-facing graph explorer.

Graph summaries and object relationships can aid navigation in Plan, but claims remain grounded in source anchors and provenance. A graph summary is not source evidence.

## 5. Relationship to `/ingest`

`/ingest` owns the serious memory workflow:

```text
recap/source ingestion
  -> live graph projection and optional comparison
  -> prose-first Graph Review
  -> diagnostics when deliberately opened
  -> Author Draft / existing-object resolution
  -> reviewed authored overlay + event-log commit
  -> narrow selected-preview-union materialization for committed identity merges
```

That boundary stays true even while implementation modules temporarily live under `apps/live-control-ui/src/planSurface/graphReviewWorkbench/`. File placement is not product ownership.

Plan consumes the resulting reviewed graph/corpus memory through adapters and projections. It may show a lightweight status/read view or an **Open in Graph Review** escalation. It must not duplicate the correction cockpit merely because its components are reusable.

### Direct answers

| Question | Decision |
| --- | --- |
| Does Plan still include an ingest tool? | Only as a lightweight status, launch, or escalation affordance. Serious ingest, review, and correction belong to `/ingest`. |
| Does Plan use Graph Review selected-object cards? | Yes as the durable target shape. Extract a **neutral shared** graph-object card/view-model primitive from the `GraphReviewNodeGameCard` shape; do not import Graph Review workbench internals into `/plan`, and do not keep growing the index-shaped Plan `SelectedObjectCard` as the final UI. |
| Does Plan include Author Draft? | No, not in the default prep flow. Escalate to `/ingest` when memory is wrong. |
| Does Plan write graph memory? | Not in the next dogfood slice. Its future write target is planning Markdown through the edit capability and two-phase writer; graph-memory writes remain in `/ingest`. |
| Does Plan depend on Hermes? | Current prep-memory Q&A uses Hermes/live-query as a **transitional** seam. The target is a plan-scoped graph-memory query over the Union Supergraph. Until then, show citation, trace, and freshness limits honestly, including live-packet mismatch failures. |

## 6. Lessons Plan imports from Graph Review

- **Prose first:** the GM’s working text and source context lead; a graph dashboard does not.
- **Game-first cards:** selected-object identity, related objects, and relationship/source context lead; technical metadata stays behind Details.
- **`dmb-node` links:** durable inline links are useful navigation syntax, provided their targets resolve through the shared boundary.
- **Quiet defaults:** diagnostics are valuable for deliberate inspection, not default GM workflow.
- **Explicit loaded state:** campaign, session, source/run, and freshness should be visible enough to make the current context trustworthy.
- **Right-sized workspace:** complex correction work may use fullscreen or resizable surfaces without turning the planning board into a multi-panel dashboard.

## 7. Immediate implementation target: one real prep loop

PR314 proved the operator can exercise the current prep loop via `/plan?dogfood=1`. That checklist is a **measurement scaffold**, not the product destination. Future product changes are judged against the real prep loop below, not against checklist completeness.

The next `/plan` implementation slices succeed only if one GM can use `/plan` to prepare an actual upcoming session:

1. Resolve and display the current campaign, prep session, and relevant ingested memory/source context.
2. Load one planning document into a usable planning board.
3. Follow a reference chip or graph-node link to a game-facing selected-object card (target: shared graph-object card over Union Supergraph; corpus-index card remains transitional fallback).
4. Ask one grounded planning question and inspect its source/citation or freshness state (target: plan-scoped graph-memory query; current live-query/Hermes path is transitional).
5. Open relevant statblock, roll-table, or context projections from that flow.
6. Escalate memory correction to `/ingest`, rather than correcting graph memory inline.

This creates a falsifiable dogfood path. A feature that adds generic projection machinery but does not make one of these prep steps work does not meet this checkpoint’s goal.

Implementation order after this re-anchor is recorded in `Docs/Design/DESIGN-plan-graph-memory-reanchor-after-dogfood-2026-07.md` §7.

## 8. Non-goals for that slice

- New graph authoring or diagnostics inside `/plan`.
- New graph ontology/taxonomy registry or graph database UI.
- A generalized Build surface.
- Player-safe graph views.
- Broad combat migration.
- Source recap Markdown mutation from graph projections.
- Reopening graph-gold fixtures as the normal product authoring destination.

## 9. Boundaries and authorities

| Concern | Authority |
| --- | --- |
| `/plan` product goal and next dogfood target | This document |
| Post-PR314 transitional vs durable graph-memory path for Plan | `Docs/Design/DESIGN-plan-graph-memory-reanchor-after-dogfood-2026-07.md` |
| SurfaceConfig, resolver, projection, edit-capability, Tiptap canvas, and Agent Interaction target architecture | `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md` |
| Union Supergraph read model and projection lenses | `Docs/Design/GRAPH-MEMORY-UNION-SUPERGRAPH-PROJECTION.md` |
| Graph Review, authored overlay/event log, and selected preview-union identity materialization | `Docs/Design/DESIGN-graph-object-authoring-surface.md` |
| Current Graph Review pause point and proven safety invariants | `Docs/Reports/SPIKE-CLOSEOUT-graph-review-authored-memory-2026-07.md` |
| Source-facing envelope and evidence vocabulary | `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md` |
| Operator dogfood scaffold (`?dogfood=1`) | `Docs/Dogfood/PLAN-SURFACE-DOGFOOD-RUNBOOK.md` |
| Surface-rung / Agent Interaction implementation tracking | `Docs/Experiments/PLAN-SURFACE-LADDER-TRACKING.md` |

Older Command Board, graph-gold, and early Graph Review handoffs remain historical evidence unless an authority document above explicitly retains a decision from them. They must not override this product split.

## 10. Acceptance criteria for future `/plan` PRs

A `/plan` PR should state which step of the real prep loop it improves and satisfy the applicable criteria:

- The planning board remains central and is calmer than a graph-review/dashboard-first layout.
- Campaign/session/source state is explicit enough to judge what memory is being used.
- Reference and selected-object interactions resolve through source-grounded adapters and opaque locators; no surface-owned taxonomy or identity logic is introduced.
- Selected-object displays prioritize game utility and source context; diagnostics and raw graph metadata are opt-in.
- Agent Interaction remains pointers-only and exposes citations, trace/freshness, or an honest unavailable state.
- Statblock, roll-table, and related context projections use the shared resolver/registry rather than a parallel Plan-specific mechanism.
- Graph correction is routed to `/ingest`; the PR does not add Author Draft, overlay writes, event-log commits, or identity merging to the default Plan flow.
- Planning Markdown writes, when added, use the shared edit capability and its guarded two-phase write path.
- The PR has a concrete dogfood or test proof for the prep step it changes.

## 11. Consequence for the next implementation agent

Do not invent `/plan` from scratch and do not copy Graph Review into it.

Start from the existing route and seams. Make the planning board, context, reference-following, selected-object card, grounded question, and supporting statblock/roll-table access useful for one real prep session. When the discovered problem is that campaign memory is wrong, send the operator to `/ingest`.

## 12. Implementation checkpoint — landed through PR314 (2026-07)

Landed and dogfoodable:

- Session context descriptors (campaign, prep session, memory session, document identity, durable target path, local-draft status).
- One derived session-prep board; North Gate / eval runbooks stay off the normal `/plan` document model.
- Durable Markdown save for that board (operator-facing single Save; backend still uses guarded prepare/commit).
- Reference chips → Plan selected-object card + source preview (corpus-index backed; **transitional**).
- Prep-memory Q&A drawer (live-query / Hermes; **transitional**; can fail on live-packet session mismatch).
- Optional `/plan?dogfood=1` checklist, notes, report copy, and recovery runbook (**scaffold**, not product UI).

**Next code work** is not more checklist polish. Follow `Docs/Design/DESIGN-plan-graph-memory-reanchor-after-dogfood-2026-07.md` §7 as the default order (shared graph-object card → graph-aware resolver → plan-scoped graph-memory query → wire Q&A behind fallback → dogfood again), with dogfood allowed to pull Q&A ahead when live-packet blockage is the sharper prep-loop blocker.
