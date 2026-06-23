# Anchor — Plan Surface Agent Interaction

**Status:** Active anchor  
**Created:** 2026-06-21  
**Scope:** Plan / Play / Build surfaces, app-level Agent Interaction Bar/Pane, recap-ingestion proof consumption, source-vocabulary adapter

## Current State

The workstream has a committed vertical slice for `/plan` recap ingestion and the first
read-only source-vocabulary adapter:

- `/plan` exists as the first intentional configured surface.
- Current implementation still has surface-local projection state and a transitional right-side Tools drawer.
- The ingestion workflow can run through the UI and expose proof/impact metadata.
- The latest committed checkpoint includes `eac1b8f feat(plan): add Hermes trace telemetry` on `main`.
- `cb0c953 feat(live): add ingestion source bundle` landed R11's backend adapter:
  `IngestionSourceBundle` maps ingested corpus artifacts into `SourceArtifact -> SourceAnchor -> SourceUnit`
  without embedding corpus bodies.
- Hermes CLI one-shot + preflight retrieval + Agent Interaction trace UI are on `main` (spike).
- Tier-1 plan-doc cleanup landed in `45d1e37 docs(plans): archive completed handoffs to 2026-06-22 batch`.
- **Next conversational Hermes UX** (threads, citations, tool parity): `Docs/Design/ANCHOR-agent-interaction-hermes.md` + `Docs/Design/UX-STORIES-agent-interaction-hermes.md`.

This anchor supersedes chat-history reconstruction. Start here, then read the canonical docs below.

## Canonical Sources

Read in this order:

1. `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`
2. `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`
3. `Docs/Experiments/PLAN-SURFACE-LADDER-TRACKING.md`
4. `Docs/Plans/HANDOFF-self-continuity-plan-toolbar-ingestion-design.md`
5. `Docs/Plans/HANDOFF-ontology-taxonomy-plan-surface-consumer-alignment.md`
6. `Docs/Design/DESIGN-play-mode-runbook-product-direction.md`

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
8. **Taxonomy/ontology remains the derived-semantics owner.** It can later produce or enrich the same `SourceUnit` envelope; the Agent Interaction consumer should not change shape when graph-backed retrieval arrives.
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

Before implementation, write a scoped handoff/PR slice for one of:

1. **P0 Hermes conversation (see `ANCHOR-agent-interaction-hermes.md`):** Hermes session continuity, full thread persist, parallel thread shell, trace toggle, in-pane citation reader.
2. **R10 lift step:** app-level `AgentInteractionProvider` that preserves the existing right drawer UI while moving projection state above `/plan`.
3. **React Play migration slice:** fold combat/runbook/live-control behavior into a `/play` surface after R10 gives projections a shared host.

Recommended sequence: **P0 Hermes conversation**, then **R10 lift step**, unless bar placement must lead for mechanical reasons. React `/play` follows as the first second-surface proof; Build waits.

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
2. Read the canonical sources listed above.
3. Run `git status --short --branch`.
4. Confirm whether local design edits are committed.
5. Choose the next rung (R11 or R10 lift step) and write the handoff/allowlist before implementation.
