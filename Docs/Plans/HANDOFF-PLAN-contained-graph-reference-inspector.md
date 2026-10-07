---
pr_body_template: |
  ## Handoff pointer
  - Flow: PLAN
  - Handoff: `Docs/Plans/HANDOFF-PLAN-contained-graph-reference-inspector.md`
  - Assigned PR: #970
  - Base at repair dispatch: `a92371b7b2e727d1d45bef1c8e1d7a3d01b58193`

  ## Verification pointer
  - Exact repair head: current PR #970 head
  - Owning checks: handoff §5
  - Merge remains PRIME-owned.
---

# HANDOFF — Plan contained Graph reference peek

**Status:** ACTIVE — repair to assigned PR #970
**Owner:** Buddy Plan surface
**Branch:** `codex/plan-graph-reference-activation`
**Base:** `a92371b7b2e727d1d45bef1c8e1d7a3d01b58193`
**Topology:** serial; update #970 only

## Mission

When a GM activates a typed Graph reference in the Plan Document or Cards reader, show the exact selected-World object in a contained Peek. Keep the Reader visible beside the desktop sheet and keep navigation/context controls uncovered on mobile. Close or Escape returns to the originating reference and its reader position. A source passage can open only from the already-loaded complete-object response when its digest-pinned binding exactly matches the evidence row; Back returns to that object.

## UX contract

- Use an opaque, fixed desktop sheet at the right edge, 360–400px wide, below `--app-chrome-top` and above `--app-chrome-bottom`; keep the reference Reader visible at left.
- On mobile, use a full-width sheet within the Reader viewport with nav uncovered, pinned header/Close, and internal body scrolling.
- Focus Close when an object opens. Escape and Close dismiss only the Peek; restore the original reference focus with `preventScroll` and restore the saved Reader scroll position.
- Source Back returns to the same object. Fold technical source identifiers by default.
- Do not stack Edit or Agent panels; do not alter their drafts or conversation state. No Graph writes, source refetch, label inference, model call, or new schema.
- Missing or mismatched excerpt binding means no Read source action. Never fabricate a passage.

## Exclusive write lease

```text
Docs/Plans/HANDOFF-PLAN-contained-graph-reference-inspector.md
apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx
apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx
apps/live-control-ui/src/planSurface/components/WorldPlanGraphReferenceActivation.tsx
apps/live-control-ui/src/planSurface/components/WorldPlanGraphReferenceActivation.test.tsx
apps/live-control-ui/src/planSurface/components/WorldPlanGraphReferenceActivation.css
apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.tsx
apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.test.tsx
apps/live-control-ui/src/graphObjectCard/GraphObjectCard.tsx
apps/live-control-ui/src/graphObjectCard/GraphObjectCard.test.tsx
```

No AppChrome/global CSS, server, API, provider, or runtime mutation path is included. Keep the provider opt-in to Plan; non-Plan readers retain their current behavior.

## Verification

Run serial Node 24 owning checks for the activation provider, resolved-object source binding, GraphObjectCard source action, and mounted Plan Document/Cards workflow. Review the complete base-to-head diff, run `git diff --check`, and report any visual behavior not proven by source tests. DOGFOOD/PRIME own live runtime QC and merge.

## §5 Verification evidence

At the repair source head, the following serial Node 24 run passed: `vitest run src/planSurface/components/WorldPlanGraphReferenceActivation.test.tsx src/graphReference/ResolvedGraphObjectProjection.test.tsx src/graphObjectCard/GraphObjectCard.test.tsx src/planSurface/PlanSurfacePage.test.tsx -t "opens exact managed World Graph references from Document and Cards|WorldPlanGraphReferenceActivationProvider|ResolvedGraphObjectProjection partial completeness|GraphObjectCard" --maxWorkers=1 --minWorkers=1` — **40 passed, 59 skipped** across four files. `git diff --check` passed.

`tsc -b --pretty false` is blocked by the pre-existing `src/statblocks/publication/ThreatPublicationPanel.tsx(553,77): TS2503 Cannot find namespace 'JSX'` error. The targeted tests validate exact excerpt binding, no action for missing/mismatched excerpt, Plan-only recap action, source Back without refetch, stale-head hiding, close/Escape focus and scroll return, and the mounted Document/Cards flow. Browser layout, pointer reachability, and actual desktop/mobile panel geometry still require DOGFOOD/PRIME live QC; DOM tests prove only the Reader/Agent sibling boundary and preservation of mounted conversation content.

## Current evidence

The previous live witness showed the object body and passage but an uncontained, unreachable Close. Runtime state was restored after that witness; this source repair does not touch or restart it. Current source work is based on the fetched Buddy main recorded above.

## §6 Preview authorization — read-only UI witness

PRIME authorizes a temporary clean runtime source checkout at the following immutable UI-only candidate for the remaining desktop/mobile interaction witness:

```text
candidate commit: 5af3615472ec790b90feafe127b5fff510db4431
candidate parent: 1cddad85ce4b4f157cbcc1ee3d18e7ad3bf967ac
source reviewed:  PR #970 head 8489f19a55b947ad44a7316d41151e75be8dbbdb
```

The candidate overlays exactly these 13 reviewed UI source/test/style blobs from #970:

```text
apps/live-control-ui/src/graphObjectCard/GraphObjectCard.test.tsx
apps/live-control-ui/src/graphObjectCard/GraphObjectCard.tsx
apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.test.tsx
apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.tsx
apps/live-control-ui/src/markdownReader/ReadOnlyBodyContent.test.tsx
apps/live-control-ui/src/markdownReader/ReadOnlyBodyContent.tsx
apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx
apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx
apps/live-control-ui/src/planSurface/WorldPlanCardProjection.integration.test.tsx
apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.tsx
apps/live-control-ui/src/planSurface/components/WorldPlanGraphReferenceActivation.css
apps/live-control-ui/src/planSurface/components/WorldPlanGraphReferenceActivation.test.tsx
apps/live-control-ui/src/planSurface/components/WorldPlanGraphReferenceActivation.tsx
```

Every candidate blob for those 13 paths matches the source-reviewed PR #970 head exactly. All other paths, including backend and dependency trees, are byte-identical to deployed parent `1cddad85`; `apps/live_control_server/services/agent_turn_service.py` remains blob `e39e43febcdc0899f613ad9fce3c0d510f006f1d`. The candidate is isolated and clean. It supersedes the earlier candidate `ce3f49a334e3abb102b8a9644cc68e04cc22c5c4`. The temporary source checkout may be used only to inspect the existing Plan Reader's object Peek, pinned source passage, Back, Close, focus return, and scroll return on desktop and mobile, including the camelCase excerpt-ready response and clicked-origin focus return. After the witness, restore the runtime source checkout to `1cddad85ce4b4f157cbcc1ee3d18e7ad3bf967ac` and verify its saved hashes.

This witness is read-only. Do not restart services, invoke providers/models, send or retry a live Ask, edit/save a Plan, save a Run, or write registry/native graph state. The recovery turn is durably interrupted at revision 19; the independently reviewed recovery invariants and zero-live-turn state have been confirmed. This paragraph authorizes only the temporary source preview and UI readback described above. It does not authorize runtime changes, writes, or merge.
