# Plan Cards navigation and Document continuity

Status: ACTIVE. Operator authorized implementation, independent review, merge and
5202 delivery on 2026-10-19. Serial topology; PRIME owns this lane. Design #1457
is merged at b7bf9976b. Base: b7bf9976b, branch
`codex/plan-cards-navigation-continuity`, existing buddy-context-loop checkout.

Invariant: one selected existing scene remains reachable across Cards and Document
without rewriting Markdown, recreating the mounted editor, changing its selection
or undo history, or mutating Play progress/notes. Navigation uses canonical current
draft scene IDs and is scoped to the current document/editor generation. A removed
anchor falls back visibly. Saved Agent targeting retains its existing rules.

Expected exclusive write lease: this handoff; DESIGN-plan-play-cards-navigation.md
and ROADMAP-demo.md for factual predecessor settlement; PlanSurfacePage.tsx;
components/WorldPlanCardProjection.tsx and its CSS; shared/SceneCard.tsx for optional
compact Plan header; Plan card model/integration tests. New narrowly scoped Plan
navigation helper/component/test files are included. No backend, schema, Run,
Graph, notes writer, dependency or lockfile changes. No overlapping open Cards
implementation was found. Architecture's design lease is complete.

Deliver compact scene selector, Previous/Next and outline access in the existing
surface navbar. Preserve scene focus across view switches and saved revisions.
Document scrolls to the selected canonical heading without moving the caret.
Keep the full document/editor and error/recovery paths. Direct card editing,
structural editing and dense scene facets remain later slices.

Verification: mounted Page/editor integration for cross-Beat traversal, view
continuity, draft/editor/selection/undo preservation, no writes on browsing,
identity replacement and removed anchors; existing Plan/Play regressions; production
build; independent exact-head review. Render real shared host at desktop/narrow
width on disposable material, check media and retained notes/state. UI-only
5202 delivery lease is the established buddy-main-af6779d/ui-dist, guarded by
current index SHA a1540ae2f65f9ebc9c328179dd13123da4cab1ec24936ff53224495a33c1888c.
Keep old hashed assets and recoverable index; no API/service/database restart.
