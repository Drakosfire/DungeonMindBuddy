# Plan Surface Ladder Tracking

Version: 0.3
Status: active architecture tracking; `/plan` next target is one real session-prep dogfood loop
Workstream: Surfaces / SurfaceConfig / Projection
Trunk branch: `experiment/plan-surface-ladder`
Sibling workstream: `experiment/ontology-taxonomy-ladder` (derived semantics; consume via adapter only)

## Purpose

Track the Surfaces ladder: `/plan` is the first intentional route composed from `SurfaceConfig` + `SurfaceShell` (NavBar, ToolBar, EditBar, SurfaceCanvas). Conversational Agent Interaction P0-P3.1 has been dogfooded locally in `/plan`; R10 remains the rung that hoists Agent Interaction into an app-level provider. The immediate Plan target is one real session-prep loop, not a second Graph Review cockpit. React `/play` is the second-surface proof after R10/P4. Both surfaces publish context and projections into the app-level agent interaction layer.

Canon decision (2026-06-22): **Command Board is now the Plan / Play / Build surface family.** Combat folds into React `/play` as operational cockpit projections rather than remaining a separate `combat` surface or static command-board product shell. Build stays named but intentionally undesigned until Plan and Play dogfood produce concrete durable-object authoring requirements.

Surface work is the product priority and should keep exercising retrieval. Plan exercises retrieval through reviewed graph/corpus memory, source bundles, statblocks, roll tables, planning-context reference chips, and Agent Interaction. Ingest / Graph Review owns heavy ingestion, graph review, diagnostics, and authored-memory correction; Plan may show lightweight status or escalation but its default path is session preparation. Play exercises retrieval through focused-beat overlays, combat rows, statblock drilldowns, rules/roll-table chips, and source/citation handles.

Canon decision (2026-06-21): **Agent interaction is not a `/plan` sub-state.** `AgentInteractionProvider` belongs above routes/surfaces, alongside or inside `AppChrome`, and owns the user's interaction continuity across projects and surfaces. Individual surfaces publish current context and available projections; they do not own the agent conversation, proof trail, open/minimized pane state, or cross-project interaction history.

The old right-side `/plan` Tools drawer is implementation state only. The target pattern is a persistent bottom **Agent Interaction Bar** plus expandable **Agent Interaction Pane**. The pane renders registered projections such as chat/ask, statblock workbench, reference inspectors, lightweight memory status, and corpus-impact proof views. `/plan` contributes planning context and plan-specific projections; Graph Review diagnostics and Author Draft remain `/ingest` responsibilities.

Source-vocabulary boundary: recap ingestion proof/memory projections must go through `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`. The backend read adapter emits `IngestionSourceBundle` (`SourceArtifact` -> `SourceAnchor` -> `SourceUnit`) from current recap-ingest status/artifacts. Agent Interaction consumes that bundle; future taxonomy/ontology graph-backed retrieval may later produce or enrich the same `SourceUnit` envelope through adapters. Graph summaries are navigational display material, not source evidence.

Composition target:

```text
AppChrome
  AgentInteractionProvider
    Route / Surface
      PlanSurfaceShell
      PlaySurfaceShell
      BuildSurfaceShell (future, unnamed shape)

  AgentInteractionBar
  AgentInteractionPane
```

State ownership:

- `AgentInteractionProvider` owns conversation/thread pointers, pane open/minimized state, active projection, recent tool runs, notifications, and proof-trail pointers.
- Surfaces publish ambient context: campaign/session, selected document block, selected reference, active event/job, corpus root/project id, and available projection registrations.
- Project/corpus writes remain scoped to explicit tool flows and backend APIs; the provider stores pointers, summaries, thread metadata, citation locators, evidence snapshots, source-line hashes/status metadata, retrieval decision metadata, and proof pointers — not canonical corpus payloads, raw prompts, graph internals, or graph summaries as evidence.
- First persistence may be browser-local, but the design target is user-level continuity outside any one project repo.


## Agent Interaction local dogfood status

| Phase | Status | Notes |
|-------|--------|-------|
| **P0 — conversational core** | Landed locally | Thread/turn model, same-thread follow-up, local persistence, trace toggle, Hermes session seam. |
| **P1 — citation trust surface** | Landed locally | Answer-first UI, citation cards, Open source action, in-pane source reader. |
| **P1.1 — source reader hardening** | Landed locally | Source endpoint OpenAPI/test coverage, allowlist, safe read-only lookup. |
| **P2.0 — named threads** | Landed locally | Thread index, create/rename/switch/delete, per-thread active state. |
| **P2.1 — thread quality** | Landed locally | Long-thread suggestion with explicit Start new thread / Keep going and persistence. |
| **P3.0 — retrieval freshness** | Landed locally | `retrieval_freshness` response object and trust panel. |
| **P3.1 — corpus change signal** | Landed locally | `/api/live/citation-freshness`, `CorpusChangeSignalPanel`, evidence snapshots, metadata-only source-currentness checks. |
| **P4 / R10 — provider lift** | Future / next likely code rung | Move Agent Interaction state ownership above routes/surfaces while preserving current `/plan` UX. |

The P3 trust surfaces are adapter-compatible with graph-backed retrieval because they store pointers, citation locators, evidence snapshots, source-line hashes/status metadata, and retrieval decision metadata — not graph internals, corpus bodies, raw prompts, or graph summaries as evidence.

`experiment/ontology-taxonomy-ladder` remains a sibling derived-semantics workstream. Future graph-backed retrieval must be consumed through adapters that emit or enrich source-grounded envelopes; no production retrieval behavior should depend on graph output until shadow-mode evidence and promotion gates exist.

## Branch Contract

Root experiment branch:

`experiment/plan-surface-ladder`

Stacked PR branches:

`surface-exp/<number>-<short-name>`

## Naming note

This document references two ladder vocabularies:

- **Agent Interaction P-rungs** describe the local `/plan` conversational dogfood ladder:
  - AI-P0 conversational core
  - AI-P1 citation trust surface
  - AI-P1.1 source reader hardening
  - AI-P2 thread management
  - AI-P3 retrieval freshness / corpus change signal

- **Surface ladder rungs** describe broader Plan / Play / Build surface architecture:
  - R10 agent-interaction-provider
  - R11 ingestion-source-vocabulary-adapter
  - Surface-P1 react-play-combat-runbook-surface

When writing new handoffs, qualify ambiguous `P1` references as `AI-P1` or `Surface-P1`.

## Rung Map

| Rung | Slug | Depends on |
|------|------|------------|
| R0 | ladder-scaffold | — |
| R1 | surface-shell-plan-route | R0 |
| L1 | shared-reference-resolver | R0 |
| L2 | derived-views-adapter | R0 |
| L3 | edit-capability | R0 |
| R2 | projection-registry | R1 |
| R8 | surface-theme | R1 |
| R6 | ingestion-tool-mount | R2 |
| R7 | statblock-tool-mount | R2 |
| R5 | reference-projection | R2, L1, L2, L3 |
| R10 | agent-interaction-provider | R2, R5, R6, R7 |
| R11 | ingestion-source-vocabulary-adapter | R2, R6 |
| Surface-P1 | react-play-combat-runbook-surface | R10, R5, R7 |
| R9 | integration-verification | R5, R6, R7, R8, R10, R11 |

## Defensible Rubric (every PR)

- **Testing:** unit + seam test at owning boundary; §7 command named in handoff.
- **Security:** two-phase writer + allowlist for corpus writes; validate `refId` before path use; no secrets/PII in artifacts.
- **Simplicity:** one app-level agent interaction provider, one projection registry, one edit capability, one resolver, one source-vocabulary contract, one theme; resolve kinds, don't declare enums.
- **Composability:** leaf modules usable without shell; typed contracts; allowlist-scoped diffs.

## Handoffs

See `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-pr*-plan-surface-*.md` for early ladder dispatch packages (archived); active tracking is this file.

## Consolidated Roadmap Notes

- `/plan` remains first: dogfood one calm session-prep loop with one planning board, explicit campaign/session/source state, reference-following into game-facing object cards, grounded Agent Interaction, and statblock/roll-table/context access. Keep the toolbar/projection win, but send graph correction to `/ingest` rather than rebuilding its review gates in Plan.
- `/ingest` is the Graph Review / authored-memory cockpit: it owns serious recap ingestion, prose-first graph review, diagnostics, Author Draft, existing-object resolution, authored overlay/event-log commits, and selected preview-union identity materialization.
- `/play` is the second-surface proof after R10/P4: migrate combat/runbook/live-control behavior into React while preserving focused-beat return semantics. Static Mireward command-board pages and `/surface` modules are migration evidence, not final architecture.
- Build remains a named placeholder. Do not create Build rungs until Plan/Play dogfood names specific durable world-object authoring needs.
- Retire or demote roadmaps that treat Command Board, Live Control, Combat, and Plan Surface as separate products. They now describe lanes inside this surface ladder.

## Verification (integration)

```bash
cd apps/live-control-ui && npm run build && npm test -- --run src/planSurface
uv run pytest tests/test_live_recap_ingest_api.py -q
```
