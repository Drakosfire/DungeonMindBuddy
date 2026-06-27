# Anchor — Plan Surface Agent Interaction

**Status:** Active anchor
**Created:** 2026-06-21
**Scope:** Plan / Play / Build surfaces, app-level Agent Interaction Bar/Pane, recap-ingestion proof consumption, source-vocabulary adapter

## Current State

The workstream has completed a local `/plan` Agent Interaction dogfood ladder through **P3.1** while keeping state ownership surface-local. `/plan` is still the first intentional surface and the proving ground, but it is not the architectural owner of Agent Interaction continuity.

Current aligned state:

- `/plan` exists as the first intentional configured surface.
- Agent Interaction has been proven locally on `/plan` through P3.1: conversational core, citation trust, source reader hardening, named threads, thread quality guardrails, retrieval freshness, and corpus change signal.
- Surface-local projection/thread state still exists; the R10 app-level provider lift is **not done**.
- The current implementation preserves the bottom Agent Interaction Bar/Pane pattern in `/plan`.
- Recap ingestion proof and source-grounded retrieval boundaries flow through `SourceArtifact -> SourceAnchor -> SourceUnit`.
- Graph/ontology remains sibling derived-semantics infrastructure; Agent Interaction consumes source-vocabulary envelopes rather than graph internals.
- **R10 / P4** is the next likely code rung: lift Agent Interaction state ownership above routes/surfaces while preserving the current `/plan` UX.
- React `/play` follows R10/P4 as the second-surface proof.

This anchor supersedes chat-history reconstruction. Start here, then read the canonical docs below.

## Canonical Sources

Read in this order:

1. `Docs/Design/ANCHOR-agent-interaction-hermes.md`
2. `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`
3. `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`
4. `Docs/Experiments/PLAN-SURFACE-LADDER-TRACKING.md`
5. `Docs/Plans/HANDOFF-ontology-taxonomy-plan-surface-consumer-alignment.md`
6. `Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md`
7. `Docs/Design/ANCHOR-dungeonBuddy-graph-retrieval.md`
8. `Docs/Design/DESIGN-play-mode-runbook-product-direction.md`

Historical/background handoff: `Docs/Plans/HANDOFF-self-continuity-plan-toolbar-ingestion-design.md`. It is useful for implementation context, but the anchors above are the current roadmap authority.

Related backlog item to keep in view:

- `Backlog.md` — `[IDEA] Plan surface dogfood — calm toolbar, busy canvas, branching slide graph`

## Canon Decisions

1. **Surface remains the top-level work abstraction.** `SurfaceConfig` composes Nav, Tool, Edit, and Canvas regions. `/plan` is the first concrete surface.
2. **Agent Interaction is app/user scoped.** `AgentInteractionProvider` belongs above routes/surfaces, alongside or inside `AppChrome`, not inside `/plan`.
3. **The durable interaction affordance is bottom-aligned.** The target is a persistent bottom Agent Interaction Bar plus expandable Agent Interaction Pane. The right-side `/plan` Tools drawer is transitional implementation state.
4. **Projection stays singular.** One projection registry and one adaptive container serve both tool launches and reference-chip/content projections. The Agent Interaction layer hoists that container above surfaces; it does not create a second projection path.
5. **Surfaces publish context; they do not own continuity.** `/plan`, the future React `/play`, and later `/build` publish ambient context and projection availability into the provider.
6. **The provider stores pointers only.** It may persist pane state, active projection, recent runs, notifications, and proof pointers. It must not store corpus bodies, normalized recap text, statblock content, or graph internals.
7. **Recap-ingestion proof flows through the source-vocabulary contract.** Agent Interaction consumes `IngestionSourceBundle` (`SourceArtifact` -> `SourceAnchor` -> `SourceUnit`) from `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`, not raw `_normalized/`, `_breadcrumbed/`, `.records_meta.jsonl`, or `corpus_impact` semantics.
8. **Taxonomy/ontology remains the derived-semantics owner.** It can later produce or enrich the same `SourceUnit` envelope; the Agent Interaction consumer should not change shape when graph-backed retrieval arrives. Graph summaries are navigational display material, not source evidence.
9. **Combat folds into Play.** Combat is not a route-level surface. The existing static command-board combat tracker and React combat/live-control modules become Play projections around the focused beat.
10. **Build stays named but nebulous.** Do not design Build until Plan and Play dogfood produce concrete durable world-object authoring pressure.
11. **Surfaces are the priority and the retrieval exercise.** Surface dogfood should keep pulling on retrieval through source chips, statblocks, roll tables, ingest proof, and focused-beat context instead of treating retrieval as a separate precondition for UI progress.

## Current Ladder

The active rung map lives in `Docs/Experiments/PLAN-SURFACE-LADDER-TRACKING.md`.

Important rungs for the next phase:

- **R11 — ingestion-source-vocabulary-adapter:** backend adapter is landed in `cb0c953`; remaining work is UI consumption cleanup and contract hardening if the branch reveals gaps.
- **R10 — agent-interaction-provider:** hoist projection state to app scope, add bottom Bar/Pane in `AppChrome`, add surface -> provider context publishing, add bounded `localStorage` Phase A rehydrate.
- **R9 — integration verification and dogfood:** prove the whole system after R10/R11/R5/R6/R7/R8 converge.

Recommended migration remains **lift-then-replace**.

1. Lift projection state behind the existing right drawer with minimal UI change.
2. Replace the drawer with the bottom Agent Interaction Bar/Pane.
3. Wire ingestion proof to consume `IngestionSourceBundle`.

## Invariants

- Do not make Agent Interaction a unified mutable knowledge store.
- Do not let Agent Interaction consume raw ingestion internals as its semantic model.
- Do not duplicate statblock generation logic.
- Do not remove terminal fallback paths for ingestion.
- Do not create a surface-owned category enum; resolve kind from corpus indexes/adapters.
- Do not build alias resolution, identity merge, relationship inference, or graph traversal in this surface workstream.
- Do not store corpus content in provider persistence; store pointers and summaries only.
- Do not bypass corpus writer safety or two-phase commit.

## Next Concrete Work

P0-P3.1 conversational Agent Interaction work has landed locally in `/plan`; do not restart at P0. The next likely code slice is:

1. **R10 / P4 provider lift:** add an app-level `AgentInteractionProvider` above routes/surfaces, preserve the current `/plan` UX, and move continuity ownership out of the surface-local implementation.
2. **React `/play` second-surface proof:** after R10/P4, fold combat/runbook/live-control behavior into a `/play` surface that publishes context to the shared provider.
3. **Later work:** operator tool parity, write-preview flows, Hermes non-canon memory integration, and graph-backed retrieval adapters.

Recommended sequence: **R10/P4 provider lift**, then React `/play` as the first second-surface proof. Build waits. Runtime graph retrieval is not part of this surface PR sequence.

## Verification Targets

Minimum gates for this workstream:

- `cd apps/live-control-ui && npm run build`
- `cd apps/live-control-ui && npm test -- --run src/planSurface`
- `cd apps/live-control-ui && npm test -- --run src/modules/IngestionModule.test.tsx`
- `uv run pytest tests/test_live_recap_ingest_api.py tests/test_live_recap_ingest_pipeline.py -q`

Additional R11 gate:

- Adapter tests prove current recap-ingest status/artifacts map to `IngestionSourceBundle` without copying full corpus bodies, leaking absolute paths, or mislabeling diagnostic metadata as source evidence.

Additional R10 gate:

- Provider tests prove app-level pane state, surface context publishing, bounded `localStorage` rehydrate, and transient-context dropping.

## Re-Anchor Procedure

When picking this workstream back up:

1. Read this anchor.
2. Read `Docs/Design/ANCHOR-agent-interaction-hermes.md` for the post-P3.1 Agent Interaction state.
3. Read `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md` before changing proof, citation, freshness, or retrieval display shapes.
4. Confirm branch and PR state before marking any phase landed.
5. Default the next code slice to **R10 / P4 provider lift** unless explicitly waived.
6. Do not restart at P0.
7. Do not start runtime graph retrieval, graph materialization, LLM extraction, alias merge, corpus writes, operator tool parity, React `/play`, or Hermes long-term memory from this anchor.
