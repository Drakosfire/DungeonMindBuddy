# Hermes Phase 0 — UI Cleanup Map

> **UI AUTHORITY (2026-08-01):** Shared bar ownership is
> [`ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md).
> Plan-local shells listed below are **transitional**; target is publication into shared hosts.

**Date:** 2026-07-15
**Status:** Evidence-backed cleanup gate; initial Plan-surface removal set approved
**Scope:** `apps/live-control-ui/`
**Product contract:** [`../Plans/PLAN-hermes-campaign-authoring-foundation-reset.md`](../Plans/PLAN-hermes-campaign-authoring-foundation-reset.md) §0D/§0E
**Re-anchor:** [`../Plans/REANCHOR-hermes-campaign-authoring-foundation-2026-07-15.md`](../Plans/REANCHOR-hermes-campaign-authoring-foundation-2026-07-15.md)

The target UI is conversation first, with draft review and promotion review as the
primary workflow. Evidence, revision, trace, and diagnostics remain available, but
behind inspection. This map distinguishes immediate chrome removal from changes that
need S1/S2 proof.

## Retained primary and S0 surfaces

Retain:

- `planSurface/PlanSurfaceShell.tsx` and `PlanSurfaceCanvas.tsx`;
- `planSurface/components/PlanAgentInteractionBar.tsx` as the free-form conversation
  surface;
- `agentInteraction/AgentInteractionProvider.tsx` and bounded thread continuity;
- `planSurface/components/agentInteractionHistory.ts`;
- `planSurface/reference/usePlanGraphReferenceResolver.ts`;
- `planSurface/components/WorldGraphQueryContextPanel.tsx`;
- graph citation/source-anchor reading in `PlanAgentInteractionBar.tsx` and
  `api/liveApi.ts`;
- `TraceDetailsPanel.tsx` as a secondary inspection surface;
- `/ingest` Graph Review and the v2 statblock workbench as secondary/domain adapters.

The retained evidence path must remain reachable after cleanup:

```text
Hermes answer
  → inspect graph references/trace
  → open admitted source anchor
  → verify revision and source-read result
```

## Approved immediate cleanup

### A. Remove the Plan backend picker

Remove the primary-form `plan-agent-backend-picker` fieldset from
`PlanAgentInteractionBar.tsx` and its dedicated CSS rules.

New Plan threads default to `hermes`. The `LiveQueryBackend` type, request field,
and `live` route remain as a compatibility adapter for existing persisted threads
and the separate `/surface` product path. This removes the product-mode decision
from the primary conversation without prematurely deleting the backend.

Verification:

- no backend radio controls render in the Plan ask form;
- a fresh Plan question uses `query_backend=hermes`;
- existing graph evidence and source-anchor actions still work;
- legacy persisted `live` threads do not crash during hydration.

### B. Remove the dead Plan toolbar component

Remove `planSurface/components/PlanToolBar.tsx`; the reference scan found no imports.
This is dead code removal, not a toolbar redesign.

### C. Retain trace/evidence controls as secondary compatibility surfaces

Do not remove `TraceDetailsPanel`, graph IDs, freshness data, packet review, or source
drawers in this pass. They are debugger-like when primary, but they still carry S0
inspection value. The next UI slice may collapse them behind a single “Inspect
evidence” disclosure after S1 proves answer-first presentation.

## Deferred cleanup candidates

| Surface | Recommendation now | Gate |
|---|---|---|
| `answerHeading` and grounding kickers | Keep contract labels until S1 answer review; then move behind support details | S1 answer-first dogfood |
| `RetrievalFreshnessPanel` and `ContextSufficiencyPanel` | Keep data; move into unified inspection drawer | S1 plus Live compatibility review |
| Always-visible graph/anchor IDs | Keep reachable; collapse from the history row | S0 evidence/source-read dogfood |
| Plan ingest proof drawer | Move to `/ingest` or operator-only dogfood mode | Verify no Plan bundle fetch is required for asking |
| `plan-agent-turns-v1` legacy mirror | Retain migration read path; remove only after storage migration test | Thread reload/isolation migration proof |
| Trace-on-by-default | Change default to off in a separate focused slice | Update dogfood checklist and trace tests |
| Plan statblock toolbox entry | Hide/quarantine, retain module/API | S2 draft/review/promotion proof |
| Plan graph-preview URL aliases | Quarantine dead links; retain `/ingest` Graph Review | Graph Review dogfood and route scan |
| `/surface` `ChatModule` | Retain as separate compatibility surface | Product decision and route migration |

## Stale or high-friction test inventory

Reference scans identified these tests as coupled to removed or deferred chrome:

- `planSurface/PlanSurfaceShell.test.tsx` — backend-radio interactions and legacy CLI
  trace fixtures;
- `planSurface/components/TraceDetailsPanel.test.tsx` — non-graph CLI prompt rendering;
- `planSurface/components/agentInteractionHistory.test.ts` — legacy CLI trace shape;
- `planSurface/dogfood/planDogfoodState.ts` — “Hermes tools → Trace On” wording;
- tests asserting `plan-agent-turns-v1` migration behavior — retain until the storage
  migration gate is complete, then rewrite around the single thread store.

These are not all immediate failures. They are maintenance signals that should not be
mistaken for product authority.

## UI verification gates

Focused Plan checks:

```text
cd apps/live-control-ui
npm test -- --run src/planSurface/PlanSurfaceShell.test.tsx src/planSurface/components/agentInteractionHistory.test.ts src/planSurface/components/TraceDetailsPanel.test.tsx
npm run typecheck
```

S0 evidence smoke:

1. Open `/plan`.
2. Ask a graph-backed question.
3. Open graph evidence.
4. Read an admitted source anchor.
5. Confirm revision/source-read diagnostics remain inspectable.

The cleanup must not make graph IDs or trace data the frontstage answer, but it also
must not make the retained S0 evidence boundary unreachable.
