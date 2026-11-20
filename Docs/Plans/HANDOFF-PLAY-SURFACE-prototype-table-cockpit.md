# HANDOFF — Play prototype table cockpit

**Status:** SETTLED — PR #1030 merged at `e21c5b3b36b314bf1926b590f09ee4394e854c5a` from reviewed head `122512fc698c3807c516a884f28675a0c6a27efc`.
**Base:** `main@dedb742fa7010eabf9cbed8df846426ca3f82032` (rebased for shared Scene card revision)
**Branch:** `codex/play-table-cockpit`
**Flow:** PLAY-SURFACE
**Topology:** serial; no overlapping Play UI implementation PR is open.

## Mission

Bring the current-moment Play surface closer to the table-tested prototype: a scene outline, a dominant readable scene card, and a record of choices and scene notes saved in this Run. Keep the current Run as the sole authority for current position, choices, and notes. The outline may inspect any scene in the admitted Playable without changing current position; only the explicit **Make current** action changes it.

The shared Scene card revision also uses one authored Scene and Choice renderer in Plan focus, Play current, and Play inspection. Plan reads its current document and preserves its Ask/Edit/Apply/Save callbacks. Play reads the admitted Run pin and preserves its existing choice, note, and Make Current CAS actions. Inspection shows Choices and any saved Scene note without providing an edit control. Source identity is exposed on each card as World/document/Scene/revision/work revision/digest/state attributes.

## Product invariants

- The scene card remains the primary workspace, with its paper treatment and authored content preserved.
- The active Scene keeps its parent Beat’s authored prose, kind, and resolved/not-marked-resolved state available in a compact read-only disclosure. Inspecting a Scene in another Beat shows the authoritative Run Beat/Scene separately from the viewed Beat/Scene and that Beat’s context.
- Avoid repeating the current Beat/Scene in a separate status strip; the grouped outline marks the current position and the card names its Scene.
- The left outline groups all admitted Beats and their Scenes. It highlights the authoritative current Scene and separately indicates a transiently inspected Scene.
- The outline is the single scene navigator; do not add a duplicate scene-list launcher or inventory step. Selecting an outline Scene is inspection only. The card clearly identifies inspection and shows the authoritative current Beat/Scene. **Make current** is explicit and writes the target Scene’s Beat and ID through the existing progress CAS, preserving decisions, resolved Beats, and notes.
- The right **Recorded outcomes** panel is a read-only projection of selected options and non-empty Scene notes in the current Run. It must not imply append-only history or timestamps; selections represent the Run’s current saved direction. Selecting a referenced Scene in the panel opens it for inspection.
- Keep the outline’s Beat grouping and mark the current Beat in that heading; do not repeat a separate current-Beat summary above the same outline. Keep the current Run position distinct from a temporarily viewed Scene.
- Compact inspection closes its overlay and moves focus to the inspected Scene heading. Escape returns to the authoritative current Scene and restores focus to a visible Scenes control, including when the outline itself is collapsed.
- Escape first dismisses an open compact overlay and restores focus to that overlay’s trigger without changing inspection or Run state. While a compact panel covers the canvas, the covered canvas is inert so Tab cannot reach obscured scene controls.
- Keep one **Saved choices & notes** panel title and a short cue that its contents are current Run state. Tighten only the Play-local dead space above the cockpit; do not change global AppChrome.
- Empty states distinguish “no choices recorded” and “no scene notes saved.”
- On narrow containers, the scene stays first and prominent. A compact Scenes / Run record control row remains immediately above it. Opening a panel overlays the scene area instead of pushing the scene and its controls down the page; only one panel is open at a time. Compact state follows the cockpit's available width, including when a wide browser contains a narrow Play pane; a user's panel toggle remains effective until the layout crosses the compact breakpoint.
- Do not add persistence, API/schema, Graph, agent, combat, or global navigation contracts. Do not change runtime/deployment state.

## Write lease

- `Docs/Plans/HANDOFF-PLAY-SURFACE-prototype-table-cockpit.md`
- `apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx`
- `apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.test.tsx`
- `apps/live-control-ui/src/playSurface/currentMoment/currentMomentModel.ts` (remove the obsolete duplicate scene-inventory workspace state)
- `apps/live-control-ui/src/playSurface/currentMoment/breachDogfoodFixture.ts` (test fixture only: provide a real second-Beat Scene for cross-Beat interaction coverage)
- `apps/live-control-ui/src/playSurface/currentMoment/PlayCockpitPanels.tsx` (new reusable outline and outcomes projections)
- `apps/live-control-ui/src/playSurface/playSurface.css`
- `apps/live-control-ui/tests/ui-visual.pw.ts` and `apps/live-control-ui/tests/ui-visual-snapshots/play-cockpit-desktop.png`, `apps/live-control-ui/tests/ui-visual-snapshots/play-cockpit-narrow.png`, `apps/live-control-ui/tests/ui-visual-snapshots/play-cockpit-app-shell-desktop.png`, `apps/live-control-ui/tests/ui-visual-snapshots/play-cockpit-app-shell-narrow.png` (responsive evidence)
- `apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.stories.tsx` only if visual QA needs a dedicated fixture.
- `apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.tsx` and `.css` (focused Scene adapter and style only)
- `apps/live-control-ui/src/shared/SceneCard.tsx`, `sceneCard.css`, and `SceneCard.adapters.test.tsx` (smallest shared card and synthetic adapter evidence)
- `apps/live-control-ui/src/shared/SceneCard.stories.tsx` and `apps/live-control-ui/tests/ui-visual-snapshots/scene-card-plan-focus-narrow.png`, `scene-card-play-inspect-narrow.png` (bounded 320px browser witness)

No host, controller, API, schema, Graph, provider, or runtime path is in the lease.

## Verification

- Unit/component tests prove Beat context remains available on active and cross-Beat inspection, inspection is transient across Beats, Make current uses exact Beat/Scene IDs and preserves unrelated Run progress, and the outcome panel reflects persisted choices/notes without writes.
- Run the focused current-moment cockpit tests and the UI production build.
- Render the story at desktop, tablet/narrow panel, and phone widths; inspect screenshots for clipping, scene-card prominence, and rail behavior. At compact widths, verify the Scenes / Run record controls stay above the scene, each panel overlays without displacing it, and switching panels closes the previous one. Also hold the viewport wide while constraining the Play container below 60rem, and verify the panels collapse and expand from the container width while preserving a manual toggle within the same layout mode.
- Component suite: 59 passed, including compact panel Escape dismissal/focus restoration, scene inspection focus, and no-progress-write behavior.
- TypeScript project build and Vite production build pass with the existing large-chunk advisory.
- Focused Chromium Play layout suite: 3 passed, covering responsive desktop/mobile widths, the full App Play route, keyboard traversal over an open panel without reaching the inert covered canvas, Escape dismissal/focus restoration, and compact inspect → Back focus restoration. Desktop and 390px screenshots were refreshed and visually inspected.
- The last full UI visual run had 12 passing tests and one unrelated Edit-dock fixture failure because `#app-edit-toolbox-drawer` is absent from the rendered fixture; the full visual file was not rerun for this compact overlay follow-up.
- Reviewer follow-up verified one outline current-Beat marker and one concise Run-record title/caveat. No runtime, operator Run, or deployment changed.
- Review exact cumulative `main@12134e7` → PR head diff and report verification limits.

## Shared Scene card revision — 2026-10-09

- Rebased the existing PR branch onto `main@dedb742fa`; retained the PR #1030 cockpit interaction and responsive work.
- Shared card renders the authored Scene and associated Choices in Plan focus, Play current, and read-only Play inspection. The current Run position remains distinct from the inspected Scene; only Make Current writes the position.
- Synthetic Conks, Sheep, and Session29 fixtures exercise both adapters at a 320px container, including a long Sheep title, source identity, Choice content, inspected Choice and note visibility, and no inspection write. Session29 also asserts the exact Make Current CAS payload while preserving selections, notes, and resolved Beats.
- Architecture review follow-up: the focused Plan card labels its article from its rendered title; dirty draft cards identify the World/document/Scene and draft state but leave revision/digest unset so saved-basis values are not mistaken for a digest of rendered draft content. The saved basis remains visible in Plan basis details.
- DOGFOOD fidelity follow-up: every authored Play option body has a read-only expandable preview in current and inspection, including selected options. V1 focused Plan Scenes show their child Beat title and body with the exact Scene association. The card visibly distinguishes Saved Plan, draft Plan, and Run-pinned Playable; draft Ask remains tied to the saved Plan until Save.
- Focused Plan, Play, and shared-adapter component suites: **79 passed**. UI TypeScript and Vite production builds pass (Vite retains the existing large-chunk advisory). Three targeted Chromium visual checks pass: existing desktop/narrow Play layout plus a synthetic 320px Plan focus with long title and Play inspection with option details. Six snapshots were refreshed and inspected; browser bounds checks show no card-internal or document overflow, and inspection generated zero writes. The broad visual file was not rerun; its inherited Edit-dock fixture failure remains the verification limit above.
- This is backend-free UI evidence. No live dogfood, operator runtime, or provider behavior is claimed.

## Settlement — 2026-10-09

PR #1030 is merged; its implementation write lease is closed. The focused
component and browser evidence above establishes the shared Scene/Choice card
presentation only. Selected-World integration, connected J5 use, durable Run
outcomes and operator acceptance remain open under separate gates.
