# Current Plan/Play Cards only

Status: ACTIVE — Plan slice. Operator explicitly authorizes removing remaining
legacy card paths and migrating all18 older Plan integration cases, with no
backwards compatibility. Owner PRIME/Buddy UI. Base c39c54134e14b41ee551f6bbb58daf904bfae7b3;
branch codex/retire-legacy-card-paths, reused buddy-context-loop checkout.
Topology: two serial slices. Plan removal/test modernization first; Play v1 UI
rejection is BLOCKED until Plan review/merge/settlement. Open PRs and released
shared-layout lease inspected. Architecture read-only scope critique accepted.

## Active exclusive Plan write lease
- This handoff
- apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.tsx
- apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.css
- apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx
- apps/live-control-ui/src/planSurface/WorldPlanCardProjection.integration.test.tsx
- apps/live-control-ui/src/planSurface/WorldPlanCardProjection.model.test.ts
- apps/live-control-ui/src/shared/SceneCard.adapters.test.tsx
- apps/live-control-ui/src/shared/SceneCard.stories.tsx
- apps/live-control-ui/src/shared/Contents.tsx
- apps/live-control-ui/src/shared/Contents.css

## Plan contract
Remove recursive overview, metadata panels, Back-to-outline and duplicate navigation.
The surface owns scene identity; readonly projection requires a sceneId and owns no
cursor or default-focus effects. Card model admits only v2; unsupported/mixed/unknown
markers fail closed with Document access and stored source intact. Remove unused
Contents outline/showToggle API. The same model gates Ask/Edit target intersections:
preserve committed authority versus current draft identity, basis and scope fences.
No source data conversion, deletion, API, provider or schema changes.

Migrate all18 older cases to current boundaries while retaining2 newer regressions.
Readonly renderer owns fidelity/Graph activation/XSS/unsafe-link tests. Actual Plan
owner owns draft/editor/media/caret/undo, surface arrows/Contents, committed-vs-draft
Ask/Edit targeting, basis/document/World identity, Save/reopen, server draft, unknown
authority and uncertain-commit/no-retry cases. Undo is exercised in Document when
undoing edits outside the current card; bounded undo loops cannot hang on a filtered
transaction. Uncertain Agent authority is fenced by saveInFlight; no obsolete basis
metadata panel is reinstated. No test skips or test-name filter in completion gate.

## Blocked successor contract (no active Play source lease yet)
Reject Playable grammar v1 before ready/publication/active-pointer or progress writes;
remove v1Deck/RunbookTableDeck render path and supported-v1 UI tests, move neutral
RunbookMutationStatus to currentMoment owner. Valid API schema names are not Playable
grammar compatibility. Lower parser/source-reading APIs and persisted Runs are outside
this UI slice. Current v2 chooser/load/rebase/notes/CAS/Agent fences must remain tested.
Expected successor paths: PlaySurfacePage.tsx and tests, runbook/RunbookTableDeck.tsx
and tests, runbook/index.ts, currentMoment/playRunMutation.ts, current cockpit/tests/
stories and shared SceneCard.adapters.test.tsx. Activate after reanchor and Plan merge.

## Plan verification and delivery gates
All20 owning integration cases, model, adapters, Contents, shared layout/deck and
current Play cockpit:117 passed across7 files, no skipped cases. Production build
passed; known React act and Vite chunk warnings retained. Independently review exact
cumulative base-to-head before merge. Real5202 current v2 desktop/narrow navigation,
Document escape for unsupported-v1 fixture, and13 protected responses unchanged.
Guarded UI artifact adoption retains old assets; no API restart/provider calls.
Settle Plan after acceptance and activate successor with an exact reanchored base.
