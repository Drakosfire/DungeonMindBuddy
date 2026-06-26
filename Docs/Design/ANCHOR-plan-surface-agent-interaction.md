# Anchor — Plan Surface Agent Interaction

**Status:** Active anchor  
**Created:** 2026-06-21  
**Updated:** 2026-06-26  
**Scope:** Plan / Play / Build surfaces, app-level Agent Interaction Bar/Pane, recap-ingestion proof consumption, source-vocabulary adapter, graph-aligned consumer boundary

## Current State

The Plan Surface workstream now has two important landed lines of work on `main`:

1. `/plan` exists as the first intentional configured surface with recap ingestion and source-vocabulary proof plumbing.
2. Agent Interaction has been dogfooded locally on `/plan` through P3.1: conversation/thread core, citation trust surface, named local threads, thread-quality guardrails, retrieval-freshness decisions, and corpus-change signals for stored turns.

Current committed behavior includes:

- `/plan` remains the first intentional surface.
- Surface-local projection state still exists; the R10 app-level provider lift is not done.
- Recap ingestion can run through the UI and expose proof/impact metadata.
- R11's backend source-vocabulary adapter has landed: `IngestionSourceBundle` maps ingested corpus artifacts into `SourceArtifact -> SourceAnchor -> SourceUnit` without embedding corpus bodies.
- Hermes-backed Agent Interaction now includes local thread persistence, named thread switching, in-pane source reading, `retrieval_freshness`, and metadata-only citation freshness checks.
- P3.1 landed in PR #185, adding `/api/live/citation-freshness`, `citation_freshness.py`, `CorpusChangeSignalPanel`, and turn-level evidence snapshot metadata.

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

Related backlog item to keep in view:

- `Backlog.md` — `[IDEA] Plan surface dogfood — calm toolbar, busy canvas, branching slide graph`

## Canon Decisions

1. **Surface remains the top-level work abstraction.** `SurfaceConfig` composes Nav, Tool, Edit, and Canvas regions. `/plan` is the first concrete surface.
2. **Agent Interaction is app/user scoped.** `AgentInteractionProvider` belongs above routes/surfaces, alongside or inside `AppChrome`, not inside `/plan`.
3. **The durable interaction affordance is bottom-aligned.** The target is a persistent bottom Agent Interaction Bar plus expandable Agent Interaction Pane. The right-side `/plan` Tools drawer is transitional implementation state.
4. **Projection stays singular.** One projection registry and one adaptive container serve both tool launches and reference-chip/content projections. The Agent Interaction layer hoists that container above surfaces; it does not create a second projection path.
5. **Surfaces publish context; they do not own continuity.** `/plan`, future React `/play`, and later `/build` publish ambient context and projection availability into the provider.
6. **The provider stores pointers only.** It may persist pane state, active projection, recent runs, notifications, conversation/thread metadata, citation locators, retrieval/citation freshness metadata, and proof pointers. It must not store corpus bodies, normalized recap text, statblock content, graph internals, raw prompts, or unbounded source excerpts.
7. **Recap-ingestion proof flows through the source-vocabulary contract.** Agent Interaction consumes `IngestionSourceBundle` (`SourceArtifact` -> `SourceAnchor` -> `SourceUnit`) from `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`, not raw `_normalized/`, `_breadcrumbed/`, `.records_meta.jsonl`, or `corpus_impact` semantics.
8. **Taxonomy/ontology remains the derived-semantics owner.** It can later produce or enrich the same `SourceUnit` envelope; the Agent Interaction consumer should not change shape when graph-backed retrieval arrives.
9. **Graph summaries are not source evidence.** They may help navigation, display, and route selection, but source-backed claims must cite source-grounded units.
10. **Combat folds into Play.** Combat is not a route-level surface. The existing static command-board combat tracker and React combat/live-control modules become Play projections around the focused beat.
11. **Build stays named but nebulous.** Do not design Build until Plan and Play dogfood produce concrete durable world-object authoring pressure.
12. **Surfaces are the priority and the retrieval exercise.** Surface dogfood should keep pulling on retrieval through source chips, statblocks, roll tables, ingest proof, focused-beat context, citation freshness, and graph-compatible source envelopes instead of treating retrieval as a separate precondition for UI progress.

## Current Ladder

The active rung map lives in `Docs/Experiments/PLAN-SURFACE-LADDER-TRACKING.md`.

Important rungs for the next phase:

- **Conversational Agent Interaction P0-P3.1:** dogfooded locally on `/plan`; do not point new work back to P0.
- **R11 — ingestion-source-vocabulary-adapter:** backend adapter is landed; remaining work is UI consumption cleanup and contract hardening if a future branch reveals gaps.
- **R10 / P4 — agent-interaction-provider:** next likely code rung. Hoist Agent Interaction state to app scope, add provider hooks, let surfaces publish ambient context, and preserve current `/plan` visual UI during the lift.
- **Graph-aligned adapter planning:** sibling design work only. Future graph-backed retrieval should emit or enrich `SourceUnit` envelopes without exposing graph internals.
- **React `/play` migration:** follows R10 as the first second-surface proof.
- **R9 — integration verification and dogfood:** prove the whole system after R10/R11/R5/R6/R7/R8 converge.

Recommended migration remains **lift-then-replace**:

1. Put Agent Interaction thread/pane/projection state behind an app-level provider.
2. Keep the current `/plan` bar and pane visually stable while moving state ownership.
3. Let `/plan` publish planning context and available projections into the provider.
4. Preserve source-vocabulary proof and metadata-only freshness surfaces.
5. Only then prove `/play` as the next surface.

## Invariants

- Do not make Agent Interaction a unified mutable knowledge store.
- Do not let Agent Interaction consume raw ingestion internals as its semantic model.
- Do not let Agent Interaction consume graph internals as its retrieval or evidence model.
- Do not treat graph summaries as source evidence.
- Do not duplicate statblock generation logic.
- Do not remove terminal fallback paths for ingestion.
- Do not create a surface-owned category enum; resolve kind from corpus indexes/adapters.
- Do not build alias resolution, identity merge, relationship inference, graph materialization, or graph traversal in this surface workstream.
- Do not store corpus content in provider persistence; store pointers, summaries, locators, evidence snapshots, freshness metadata, and proof pointers only.
- Do not bypass corpus writer safety or two-phase commit.
- Do not make production retrieval behavior depend on graph output before shadow-mode evidence and promotion gates exist.

## Next Concrete Work

Before implementation, write a scoped handoff/PR slice for one of:

1. **R10.0 / P4.0 — App-level AgentInteractionProvider lift:** preserve current `/plan` UI while moving thread/pane/projection ownership above routes/surfaces. This is the recommended next code slice.
2. **Graph-aligned retrieval adapter planning:** design-only; future graph outputs must produce or enrich `SourceUnit` envelopes and remain evidence-safe. Do not implement runtime graph retrieval here.
3. **React Play migration slice:** fold combat/runbook/live-control behavior into a `/play` surface after R10 gives projections a shared host.

Recommended sequence: **docs re-anchor → R10/P4 provider lift → Play second-surface proof**. Graph retrieval remains a sibling ontology/taxonomy workstream consumed through adapters.

## Verification Targets

Docs-only re-anchor:

```bash
rg -n "Next slice to implement|Not done|P0|P1|P2|P3|P4|R10|retrieval_freshness|citation-freshness|CorpusChangeSignal|SourceArtifact|SourceAnchor|SourceUnit|ontology|taxonomy|graph" Docs/Design Docs/Experiments Docs/Plans

rg -n "AgentInteractionProvider|SourceArtifact|SourceAnchor|SourceUnit|retrieval_freshness|citation-freshness|evidence_snapshots|CorpusChangeSignalPanel" Docs/Design Docs/Experiments Docs/Plans
```

Minimum gates for runtime changes in this workstream:

```bash
cd apps/live-control-ui && npm run build
cd apps/live-control-ui && npm test -- --run src/planSurface
cd apps/live-control-ui && npm test -- --run src/modules/IngestionModule.test.tsx
uv run pytest tests/test_live_recap_ingest_api.py tests/test_live_recap_ingest_pipeline.py -q
```

Additional R10 gate:

- Provider tests prove app-level pane state, surface context publishing, bounded `localStorage` rehydrate, pointer-only persistence, and transient-context dropping.

Additional graph-adapter gate:

- Adapter tests prove graph-backed or graph-enriched retrieval emits `SourceUnit`-compatible envelopes, does not expose graph internals, and does not use graph summaries as evidence.

## Re-Anchor Procedure

When picking this workstream back up:

1. Read this anchor.
2. Read `ANCHOR-agent-interaction-hermes.md` for the post-P3 Agent Interaction state.
3. Read the source-vocabulary contract before changing proof/citation/freshness display shapes.
4. Confirm branch/PR state before marking a phase landed.
5. Choose the next rung. Default to R10/P4 provider lift unless explicitly waived.
6. Do not start graph retrieval, graph materialization, LLM extraction, alias merge, corpus writes, or Hermes long-term memory from this anchor.
