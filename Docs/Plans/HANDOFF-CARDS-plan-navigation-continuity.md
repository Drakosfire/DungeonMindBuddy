# Plan Cards navigation and Document continuity

Status: SETTLED, 2026-10-19. PR #1458 merged at
`74a604ce3542fbb0501ac0baf2ff9a32cdfa42a5`; Architecture Review Cycle 1 PASS on
`d6936b0e6398b8d5168e7d0e4c4e1731fbd8ee6c`. PRIME completed desktop/narrow
5202 delivery and retained-state verification. All implementation/reviewer leases
and consumers are released. Direct focused-card editing is not authorized.

The following records the completed contract. Operator authorized implementation,
independent review, merge and 5202 delivery on 2026-10-19. Serial topology; PRIME
owned this lane. Design #1457
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

## Completed evidence and limits

Architecture independently ran 32 owning Plan tests and mounted in-memory probes
for removed-anchor fallback and stale navigation callbacks after A→B→A. Five
shared SceneCard fixture failures reproduced with the base modules because those
fixtures lack SurfaceContextProvider; they remain inherited failures. Bugbot found
no implementation defect; cumulative whitespace checks passed. PRIME reported a
passing production build and 80 Play cockpit/effective-content regressions. Its
legacy WorldPlanAgentReviewedEdit result was 18 failures/1 pass; only two
source-card failures were reported reproduced on main, with the remaining
conversation-control failures not claimed independently baseline-proven here.

PRIME's final browser verification covered cross-Beat navigation, canonical
Document return, draft text and media attributes through Cards/autosave, all
18 roster rows/three choices, keyboard selection, and desktop/narrow layouts.
Its final retained-state comparison passed for 12 protected responses, including
the real Plan, Run/content/notes and review 54 reflections. No API restart occurred.
The delivered UI index SHA256 is
`764494e1652c5895f35f6c7a1dcb66411284bc505c9dbf7eca6f714b75f9f92f`;
hashed assets were retained. Runtime evidence is PRIME-owned, not a second
Architecture runtime execution. See the
[review/delivery receipt](https://github.com/Drakosfire/DungeonMindBuddy/pull/1458#issuecomment-6275613202).

This closes bounded Plan navigation/Document continuity only. Direct focused-card
editing, dense-scene facets, structural editing, and broader J2/J5/shared-authoring
acceptance remain open and need their own bounded authorization.
