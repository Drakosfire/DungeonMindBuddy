# Card reader arrows

Status: ACTIVE, 2026-10-19. PRIME owns the operator-requested simple back/next
arrows above the Plan/Play card. Serial branch codex/card-surface-arrows from
336115c4d, existing buddy-context-loop; open PR/lease scan found no overlap.
One shared presentation control, distinct existing navigation adapters. Plan uses
Contents order and existing navigatePlanScene, Cards only; stable mounted editor,
drafts and source/Document views unchanged. Play relocates its existing adjacent
scene controls from the surface navbar to the card reader, using openInspect only.
No Make Current, progress, note target or persistence write from arrow navigation.
First/last and missing scene disable unavailable directions; accessible keyboard
buttons, compact arrow glyphs and destination tooltips. No looping or new shortcuts.

Exclusive paths: this handoff; new shared/CardSceneNavigation.tsx, CSS and tests;
planSurface/PlanSurfacePage.tsx and owning tests; playSurface/currentMoment/
PlayCurrentMomentCockpit.tsx and tests. No schemas/backend, dependencies, storage,
other navbar redesign, card topology, new editor/writer or global arrow keys.

Verify shared boundary states and owning Plan/Play navigation/retained editor and
notes/no writes; production build; independent Architecture exact-head review;
rendered desktop/narrow on5202 with protected real Plan/Run/review responses exact.
UI-only guarded adoption from priorindex
674cadbe6f5990e3487785a95f032dddb8fed4c508f9206567b98834e558c5af;
retain hashed assets/rollback index; no API restart. Settle after merge.
