# HANDOFF — Play prototype table cockpit

**Status:** ACTIVE — implementation authorized by the user’s ongoing DOGFOOD and prototype-alignment goal.
**Base:** `main@12134e7cae37425131c1e74f170d85f48e21ac2c`
**Branch:** `codex/play-table-cockpit`
**Flow:** PLAY-SURFACE
**Topology:** serial; no overlapping Play UI implementation PR is open.

## Mission

Bring the current-moment Play surface closer to the table-tested prototype: a scene outline, a dominant readable scene card, and a record of choices and scene notes saved in this Run. Keep the current Run as the sole authority for current position, choices, and notes. The outline may inspect any scene in the admitted Playable without changing current position; only the explicit **Make current** action changes it.

## Product invariants

- The scene card remains the primary workspace, with its paper treatment and authored content preserved.
- The active Scene keeps its parent Beat’s authored prose, kind, and resolved/in-progress state available in a compact read-only disclosure. Inspecting a Scene in another Beat shows the authoritative Run Beat/Scene separately from the viewed Beat/Scene and that Beat’s context.
- Avoid repeating the current Beat/Scene in a separate status strip; the grouped outline marks the current position and the card names its Scene.
- The left outline groups all admitted Beats and their Scenes. It highlights the authoritative current Scene and separately indicates a transiently inspected Scene.
- The outline is the single scene navigator; do not add a duplicate scene-list launcher or inventory step. Selecting an outline Scene is inspection only. The card clearly identifies inspection and shows the authoritative current Beat/Scene. **Make current** is explicit and writes the target Scene’s Beat and ID through the existing progress CAS, preserving decisions, resolved Beats, and notes.
- The right **Recorded outcomes** panel is a read-only projection of selected options and non-empty Scene notes in the current Run. It must not imply append-only history or timestamps; selections represent the Run’s current saved direction. Selecting a referenced Scene in the panel opens it for inspection.
- Empty states distinguish “no choices recorded” and “no scene notes saved.”
- On narrow containers, the scene stays first and prominent. Outline and Recorded outcomes become compact, independently collapsible sections rather than stacked full-height rails.
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

No other paths are in the lease.

## Verification

- Unit/component tests prove Beat context remains available on active and cross-Beat inspection, inspection is transient across Beats, Make current uses exact Beat/Scene IDs and preserves unrelated Run progress, and the outcome panel reflects persisted choices/notes without writes.
- Run the focused current-moment cockpit tests and the UI production build.
- Render the story at desktop, tablet/narrow panel, and phone widths; inspect screenshots for clipping, scene-card prominence, and rail behavior.
- Review exact cumulative `main@12134e7` → PR head diff and report verification limits.
