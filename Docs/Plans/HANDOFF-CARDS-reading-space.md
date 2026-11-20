# Plan Cards reading space

Status: SETTLED, 2026-10-19. PR #1459 merged at
`24a07d1fb7e69ed784cdb61a83efe9e62a97ade2` after Architecture Review Cycle 1 PASS
on `aeec877f2c80784be44a4b237d2204a291af37cf`. PRIME completed the rendered and
retained-state delivery gate. Implementation/reviewer leases and consumers are
released; the historical contract below grants no continuing write/runtime lease.

Operator dogfood correction authorized this bounded serial slice after #1458.
PRIME owned branch codex/plan-cards-reading-space from
6365a9a35 in the existing buddy-context-loop checkout. No overlapping Cards PR.

Invariant: use the available Plan reading width, keep authored Beat content, and
remove the misleading prominent Agent-target control from the scene header.
The scene selector already provides the Beat title. Title-only Beat context need
not repeat it in a padded panel. Agent targeting remains available in details
with wording that distinguishes choosing a proposal target from direct editing.
Do not change document/Run state, save/navigation controllers, notes or Play.

Exclusive expected paths: this handoff;
apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.tsx and
WorldPlanCardProjection.css; its existing model/integration tests. No shared
renderer, backend, schema, dependency or lockfile changes.

Verify existing mounted Plan tests, production build and cumulative diff;
independent Architecture exact-head review; real Edge Cards at desktop/narrow
width, retained scene/content/notes. 5202 UI-only atomic delivery uses established
buddy-main-af6779d/ui-dist; prior index SHA
764494e1652c5895f35f6c7a1dcb66411284bc505c9dbf7eca6f714b75f9f92f.
Keep old assets/index for rollback. Finish as one reviewed implementation PR,
merge under standing authority, deliver and settle after merge.

## Completed evidence

Architecture independently reran all 32 owning Plan model/integration tests;
all passed. Cumulative whitespace checks passed and Bugbot found no issue.
PRIME reported the passing production build and actual 5202 delivery: Edge card
width increased from 594 to 1168 CSS pixels within the 1216-pixel reader; the
scene header has no Agent-target button or duplicate title-only Beat panel;
authored Beat bodies remain visible and the clarified Agent action is in details.
Scene identity survives Document/Cards switching. At CSS width 433 the page has
no horizontal overflow. All 12 protected responses, including notes and closing
reflections, matched their retained baselines. These browser/state checks are
PRIME-owned evidence, not a second Architecture runtime execution.

Delivered UI index SHA256:
`0142ebf13e2ef03f60af7e880ed06e20ecd41736cdef6c4571ae76f80d854440`.
This closes the bounded reading-space correction, not direct-card editing or the
broader Plan/Play acceptance journey.

## Successor discussion — not activated

The operator reports that the two navbar dropdowns confuse Plan selection with
scene selection, and proposes a vertical scrollable deck of card thumbnails.
Recommended next discussion: keep Plan selection in the navbar; use a scene/card
deck with readable titles, previews and selection highlighting, with a collapsible
drawer on narrow screens. Preserve the same scene, document/draft and save
identities through that presentation. This records feedback only; no capability,
implementation lease or amendment to the stable design is activated here.
