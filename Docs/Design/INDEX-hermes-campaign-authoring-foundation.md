# Active Hermes Campaign Authoring Foundation Documents

**Status:** Phase 1 product re-anchor accepted; initial Phase 0 cleanup slice complete; S1 gate rejected pending repair
**Created:** 2026-07-15  
**Sequencing authority:** [`PLAN-hermes-campaign-authoring-foundation-reset.md`](../Plans/PLAN-hermes-campaign-authoring-foundation-reset.md)

This is the small active Hermes design set for the campaign sensemaking and authoring
reset. The product direction is accepted; new creative primitives remain gated by
the remaining Phase 0 evidence and S1 acceptance.

## Active set

| Role | Document | Purpose |
|---|---|---|
| Goal | [`ANCHOR-hermes-campaign-sensemaking-goal.md`](ANCHOR-hermes-campaign-sensemaking-goal.md) | North-star experience and product principles |
| Plan | [`PLAN-hermes-campaign-authoring-foundation-reset.md`](../Plans/PLAN-hermes-campaign-authoring-foundation-reset.md) | Phase 0–5 reset plan and exit criteria |
| Architecture | [`ARCHITECTURE-hermes-campaign-authoring-foundation.md`](ARCHITECTURE-hermes-campaign-authoring-foundation.md) | Retrieval, authoring, draft, and promotion boundaries |
| Stories | [`UX-STORIES-hermes-campaign-authoring-foundation.md`](UX-STORIES-hermes-campaign-authoring-foundation.md) | User and agent behavior contracts |
| Evaluation | [`EVAL-hermes-campaign-authoring-foundation.md`](EVAL-hermes-campaign-authoring-foundation.md) | Archive, re-anchor, sensemaking, and statblock gates |
| Re-anchor record | [`../Plans/REANCHOR-hermes-campaign-authoring-foundation-2026-07-15.md`](../Plans/REANCHOR-hermes-campaign-authoring-foundation-2026-07-15.md) | Accepted decisions, current state, and remaining Phase 0 gate |
| Checklist | Not created yet | Created when construction begins |

## Phase 0 gate artifacts

- [`../Reports/HERMES-PHASE-0-CODE-DEMOLITION-MAP.md`](../Reports/HERMES-PHASE-0-CODE-DEMOLITION-MAP.md)
- [`../Reports/HERMES-PHASE-0-UI-CLEANUP-MAP.md`](../Reports/HERMES-PHASE-0-UI-CLEANUP-MAP.md)
- [`../Reports/HERMES-PHASE-0-REFERENCE-SCAN.md`](../Reports/HERMES-PHASE-0-REFERENCE-SCAN.md)
- [`../Reports/HERMES-S1-LATEST-RECAP-DOGFOOD-2026-07-15.md`](../Reports/HERMES-S1-LATEST-RECAP-DOGFOOD-2026-07-15.md)

## Active references outside this set

These remain implementation or infrastructure references, not competing Hermes
product authorities:

- `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
- `Docs/Design/CONTRACT-graph-kernel-boundary.md`
- `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
- `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
- `Docs/Design/ANCHOR-plan-surface-agent-interaction.md`
- `Docs/Dogfood/PLAN-SURFACE-DOGFOOD-RUNBOOK.md`
- `Docs/Design/DESIGN-graph-object-authoring-surface.md`
- `.hermes.md` as runtime policy

These references are reconciled by the re-anchor record and Phase 0 reports. The
Campaign Supergraph roadmap and tracker remain sequencing authority for graph
infrastructure; the Hermes reset plan governs the authoring/product gate. Neither
authorizes new creative primitives before the remaining Phase 0 gate and S1.

## Archive boundary

The superseded Hermes ladder, old graph-only anchor/story pair, and July 14
world-graph design-reset sandbox are archived under:

[`../Plans/archive/2026-07-15/hermes-campaign-authoring-foundation-reset/`](../Plans/archive/2026-07-15/hermes-campaign-authoring-foundation-reset/)

The original `.cursor/plans/hermes_graph_dogfood_4f95fo9e.plan.md` remains untouched.
Its completed work is historical input and is not sequencing authority for this reset.

## Phase 0 limitations

The document archive, product re-anchor, initial low-risk code/UI cleanup slice,
and UI failure triage are complete. The reports record retained adapters and
deferred cleanup. The deterministic S1 resolver is green, but the real
Plan/Hermes dogfood rejected the S1 read-only acceptance; the route must be
repaired and rerun before new authoring primitives are built.
