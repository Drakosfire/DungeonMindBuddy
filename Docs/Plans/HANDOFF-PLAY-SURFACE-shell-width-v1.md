# HANDOFF — Play cockpit fills available shell width

**Status:** ACTIVE — authorized by the user's standing DOGFOOD/UX objective to create targeted UX PRs.
**Workstream:** PLAY-SURFACE / current-moment shell sizing
**Flow:** PLAY-SURFACE
**Base:** `origin/main@7a6a5e1200f8a5d5a603fb55e8191f5c248521b1`
**Branch / checkout:** `codex/play-cockpit-shell-width` / `/tmp/dmb-play-cockpit-shell-width`
**Topology:** serial — one implementation PR.
**PR title:** `PLAY-SURFACE: use available width for the cockpit`

## Mission and invariant

Make the existing Play shell occupy the width its parent gives it, so the current Scene, Beat Context, and At a Glance arrange according to real available space. The active Scene stays the primary workspace. At wide widths the supporting rails sit beside it; as the Play container narrows, the Scene comes first and the rails follow. No authored content, Run state, or interaction behavior changes.

**Merge-ready invariant:** In the full App route at a 1280px browser width, the Play shell uses nearly all available horizontal space and the three-column cockpit is visible. At 960px and below, the container switches to a Scene-first stacked composition without horizontal overflow. The assertions measure the full App shell, not only an isolated cockpit component.

## Evidence and design basis

- Current main includes PR #1028, which adds paper/ink Scene styling and container-responsive cockpit ordering.
- Historical observation recorded when this handoff was authored: a read-only 1280px visit to 5202 showed the warm Scene card, with `.app-wrap` at **809px** and the cockpit at **721px**. It indicated the shell-width defect, but is no longer current dogfood evidence.
- Computed layout evidence: `.app-shell-layout` is a column flex container; `.app-wrap` had `width:auto` plus auto horizontal margins, so as a flex item it shrink-wrapped to about 809px despite its 1440px maximum. Existing full-App visual assertions checked the Scene width and overflow but did not assert that the wrapper filled available space.
- Approved hierarchy: `Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-gm-cockpit-target.md` — central Scene workspace with immediately reachable, secondary Beat Context and At a Glance.
- Mobbin reference inspected: [Asana task detail](https://mobbin.com/screens/afea59a1-d470-437b-b8a2-712a8f83cf01). It keeps the working item legible while secondary information remains contained in a companion pane; this slice uses that hierarchy as a reference without copying its product styling.

## Exclusive write lease

Only these paths may be edited:

```text
Docs/Plans/HANDOFF-PLAY-SURFACE-shell-width-v1.md
Docs/Plans/HANDOFF-PLAY-SURFACE-responsive-cockpit-v1.md
apps/live-control-ui/src/playSurface/playSurface.css
apps/live-control-ui/tests/ui-visual.pw.ts
apps/live-control-ui/tests/ui-visual-snapshots/play-cockpit-app-shell-desktop.png
```

No app-shell, global token, shared navigation, Agent, API, server, schema, database, or Run behavior changes. Do not change Play content or mutate the operator Run.

## Acceptance and verification

1. Play's `.app-wrap` has an explicit full-width flex-item contract with the existing max-width and mobile gutter behavior preserved.
2. The full-App visual route asserts that `.app-wrap` uses the available width at desktop and remains within mobile gutters. At 1280px it must be at least 90% of the browser width and the cockpit must use three columns; at 960px and below it remains Scene-first and stacked. Exercise 1280, 960, 768, 390, and 320px.
3. No horizontal overflow at 1280, 960, 768, 390, or 320px. The scene remains visible and readable, rails remain keyboard-operable.
4. Update and inspect the full-App desktop snapshot; leave narrow behavior intact unless a verified regression requires correction.
5. Run the owning Play visual route, focused cockpit tests, UI typecheck, and `git diff --check`. Review the exact cumulative `7a6a5e12..HEAD` diff against this lease.
6. Do not claim live dogfood for this unmerged branch. On 2026-10-08, read-only inspection of the active Run `4c57c533-660c-4c65-b8f8-46fadad8030b` at 5202 showed the older dark Scene card, not the paper treatment in #1028. The read-only runtime checkout at `/home/drakosfire/.local/state/dungeonmindbuddy/runtime` is `70a7ca08684829b0bfa6b89f273225c61c939f83`; neither #1028 nor this PR is verified as loaded in the live process. The process-to-checkout association has not been re-established. Do not restart, update, or mutate the operator runtime or Run under this UI lease.

Commit intended changes, push this branch, open one PR, attach it, and send PRIME the exact head plus screenshot/test evidence. PRIME retains review and merge authority.

## Verification observation — 2026-10-08

- Full-App Play visual route: **passed** at 1280, 960, 768, 390, and 320px. The desktop fixture shows three columns; 960px and below use the Scene-first stack; no horizontal overflow was found.
- Updated desktop full-App screenshot captured and inspected. Narrow screenshot and behavior remained stable.
- Focused Play cockpit tests: **53 passed**.
- UI TypeScript typecheck: **passed**.
- Ladle production build: **passed**.
- `git diff --check`: **passed**.
- The screenshot fixture uses a synthetic Run and rejects every mutation except its intercepted in-memory active-Run selection; no persistent Run or operator data was changed.

## Current live-state correction — 2026-10-08

- The current 5202 page for the active Run still renders the older dark Scene card. The browser shows World Ready and the active Run content, but this visual inspection does not prove which checkout or frontend bundle served it.
- The read-only runtime checkout resolves to `70a7ca08684829b0bfa6b89f273225c61c939f83`. Current 5202 dogfood therefore does not verify the merged #1028 paper styling or this unmerged width fix. The previous “main-plus-dogfood” statement is stale and withdrawn.
- No runtime process, persistent Run, or database was changed during this inspection.
