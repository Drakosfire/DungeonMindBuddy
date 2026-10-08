# HANDOFF — responsive Play cockpit presentation

**Status:** ACTIVE — direct product-owner authorization in DOGFOOD thread.
**Workstream:** PLAY-SURFACE / responsive current-moment presentation
**Flow:** PLAY-SURFACE
**Base:** `origin/main@97b029896bb1b6f44cf1f6278788bbe06cdb4615`
**Branch / checkout:** `codex/play-responsive-cockpit` / `/home/drakosfire/.codex/worktrees/play-responsive-cockpit/DungeonMindBuddy`
**Topology:** serial — one implementation PR.
**PR title:** `PLAY-SURFACE: bring the current moment closer to the cockpit target`

## Mission and invariant

Bring the existing Play current-moment cockpit closer to the approved GM
prototype using its existing visual primitives, and make the active Scene
remain the first useful surface at narrow widths. At normal desktop width the
Scene should read as the primary authored card over quiet application chrome;
Beat Context and At a Glance remain present and immediately reachable. When
the available Play width narrows, the Scene moves ahead of the context rails,
all three areas fit the available width without horizontal overflow, and the
rails remain operable through their existing collapse controls.

**Merge-ready invariant:** At wide and narrow Play widths, a GM can identify
the exact active Scene immediately, read its complete authored content and
notes in a clear high-contrast card, and reach Beat Context / At a Glance
without those panels obscuring or pushing the Scene below the first viewport.
This changes presentation only; the same Run, current Beat/Scene, decisions,
notes and navigation actions remain authoritative and behave identically.

## Design basis and critique

- Approved hierarchy: `Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-gm-cockpit-target.md` — one central Scene workspace, with collapsible Beat Context and At a Glance.
- Existing shared visual language: `apps/live-control-ui/src/ui/tokens.css`, `SceneLensReader.css`, and `ui/primitives.css`. Use the paper/ink/sage/action palette already present; do not add a second token system.
- Existing Mobbin references inspected: [Airtable project detail](https://mobbin.com/screens/bef9ad34-4f77-41a0-a750-a5db43200733) and [Wrike task detail](https://mobbin.com/screens/64d7b97f-0137-451c-9a45-0a281274e2b6). Their work area stays dominant while navigation/detail remains secondary.
- Current defect: Play already collapses its three-column grid below 60rem, but preserves DOM order, so the expanded Beat rail appears before the central Scene and can dominate the narrow first view. The current Scene card also uses a dark raised panel instead of the paper-reader treatment already used elsewhere in Buddy.
- Pre-dispatch failure critique: CSS visual polish could make a desktop screenshot attractive while the Scene remains buried at the actual narrow container width (including when a conversation pane is open). Verification therefore must exercise narrow *available container width*, inspect overflow and focus/keyboard operation, and compare the central Scene hierarchy at desktop and narrow sizes.

## Exclusive write lease

Only these paths may be edited:

```text
Docs/Plans/HANDOFF-PLAY-SURFACE-responsive-cockpit-v1.md
apps/live-control-ui/src/playSurface/playSurface.css
apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx
apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.test.tsx
apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.stories.tsx
apps/live-control-ui/tests/ui-visual.pw.ts
apps/live-control-ui/tests/ui-visual-snapshots/play-cockpit-desktop.png
apps/live-control-ui/tests/ui-visual-snapshots/play-cockpit-narrow.png
```

No server, schema, persisted data, global app shell, shared token, generic
Agent, SceneLensReader, or Runbook authoring changes. Keep decisions, note
autosave, Run progress, scene inspection, and current-moment authority intact.
Do not restart or modify the operator runtime as part of this UI slice.

## Acceptance and verification

1. The central Scene uses existing paper/ink primitives and the established
   sage choice treatment; typography and spacing support quick table reading.
2. Responsive behavior is driven by available Play width, not only the overall
   browser viewport. The central Scene precedes supporting rails in the narrow
   composition. No horizontal scrolling occurs at 320, 390, 768, 960, or
   1280px available widths.
3. Beat Context and At a Glance remain reachable, keyboard-operable, and
   clearly secondary. The same expanded/collapsed controls work at all widths.
4. Existing current Scene, decision, scene-note, and inspection behavior
   remains unchanged. Preserve the exact Run and authored content.
5. Add a backend-free Ladle fixture that renders the actual cockpit component
   at desktop and narrow widths. Capture both widths and inspect them before
   handoff. Add focused tests for any new behavior and run cockpit/Play route
   tests, UI typecheck, and `git diff --check`.
6. Review the exact cumulative `97b029896..HEAD` diff against this lease.
   Record any inherited failures and do not claim live dogfood while 5202/API
   are unavailable.

Commit intended changes, push this branch, open one PR, attach it, and send the
exact head plus screenshot/test evidence to PRIME. PRIME retains review and
merge authority.

## Verification observation — 2026-10-08

- Current-moment cockpit + Play route tests: **68 passed**.
- UI TypeScript build: **passed**.
- Play visual test: **passed** at 320, 390, 768, 960, and 1280px; desktop and
  narrow screenshots captured and inspected. Keyboard collapse/reopen passed
  at 320px; no horizontal overflow or scene clipping found.
- Full visual contract: **9 passed, 1 failed**. The only failure is the
  existing Edit-drawer story test (`keeps Plan chrome stable while Edit docks`),
  which could not find `#app-edit-toolbox-drawer`. It failed again when run
  alone. The Edit drawer implementation/story is outside this lease; the
  failure is preserved here and is not represented as a proven baseline issue.
