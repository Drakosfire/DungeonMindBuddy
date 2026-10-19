# Card reader arrows

Status: COMPLETED / SETTLED, 2026-10-19. No active write lease or successor
authorization remains. PRIME implemented the operator-requested simple back/next
arrows above the Plan/Play card. Serial branch codex/card-surface-arrows from
336115c4d, existing buddy-context-loop; open PR/lease scan found no overlap.
One shared presentation control, distinct existing navigation adapters. Plan uses
Contents order and existing navigatePlanScene, Cards only; stable mounted editor,
drafts and source/Document views unchanged. Play relocates its existing adjacent
scene controls from the surface navbar to the card reader, using openInspect only.
No Make Current, progress, note target or persistence write from arrow navigation.
First/last and missing scene disable unavailable directions; accessible keyboard
buttons, compact arrow glyphs and destination tooltips. No looping or new shortcuts.

Historical implementation paths (released): this handoff; new shared/CardSceneNavigation.tsx, CSS and tests;
planSurface/PlanSurfacePage.tsx and owning tests; playSurface/currentMoment/
PlayCurrentMomentCockpit.tsx and tests. No schemas/backend, dependencies, storage,
other navbar redesign, card topology, new editor/writer or global arrow keys.

Verify shared boundary states and owning Plan/Play navigation/retained editor and
notes/no writes; production build; independent Architecture exact-head review;
rendered desktop/narrow on5202 with protected real Plan/Run/review responses exact.
UI-only guarded adoption from priorindex
674cadbe6f5990e3487785a95f032dddb8fed4c508f9206567b98834e558c5af;
retain hashed assets/rollback index; no API restart. Settle after merge.

## Completion evidence

- Buddy PR #1465 merged at `879bcee66b01cff5fcb81cc87f413f590e5c505c`.
  Accepted implementation head: `95aa0154ab0dd62987c2024a03c5b5822c61df56`.
- One formal Architecture review cycle: source APPROVE on that exact head.
  Bugbot independently found no concrete blockers. Architecture independently
  passed 74 distinct tests: five owning Plan tests, one shared adjacency test
  and all 68 Play cockpit tests. The diff check passed and the reviewed checkout
  was clean. PRIME separately reported the production build passing; Architecture
  did not rerun it.
- PRIME reported rendered 5202 acceptance on the actual Plan: Previous was
  disabled at the first scene; Next opened First sight in agreement with Contents;
  Next was disabled at the last scene. Enter activated Next and Space activated
  Previous. At 433px width, 36-by-36-pixel arrows fit without horizontal overflow.
- PRIME reported Play Next inspected First sight while current scene and Notes
  remained Journey; Previous returned to Current and was disabled at the first
  scene. Narrow Play fitted as well. All 11 protected records and the real Run
  review remained exact after pointer browsing; keyboard navigation was also
  presentation-only. These are PRIME's browser/runtime observations, distinct
  from Architecture's source and mocked-test review.
- Serving UI index:
  `b1586c0c597f8e2036f786697b80ad19ff8cb924ce7533c08445ce1ec0bff638`.
  PRIME reported QA tabs closed and viewport reset, and retains final read-only
  serving/protected-state checks. This settlement authorizes no successor,
  additional PR or runtime operation.
