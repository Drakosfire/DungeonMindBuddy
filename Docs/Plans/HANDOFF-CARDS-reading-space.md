# Plan Cards reading space

Status: ACTIVE, 2026-10-19. Operator dogfood correction authorizes this bounded
serial slice after #1458. PRIME owns branch codex/plan-cards-reading-space from
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
