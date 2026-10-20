# Play card width and Contents toggle

Status: COMPLETED; exclusive source lease released. User authorized the annotated Play width and book toggle fixes.
Owner: PRIME / Buddy UI. Topology: serial, one PR.
Base: 4fd2086fd1641b7936e01bf474c13db9ac651cf1.
Branch: codex/play-card-width-book-toggle; reused buddy-context-loop checkout.

## Exclusive expected paths
- This handoff
- apps/live-control-ui/src/playSurface/playSurface.css
- apps/live-control-ui/src/playSurface/currentMoment/PlayCockpitPanels.tsx

The old shell-width-v1 handoff describes a historical October 8 merged slice;
its stale ACTIVE label does not allocate this current lane. Open PRs inspected:
no current overlapping implementation. Preserve other rails and all Run behavior.

## Invariant and verification
Play card body fills available inner width without changing responsive rails.
Contents has a compact book symbol with accessible Expand/Collapse Contents names,
expanded state and controlled region retained. Do not rotate or elongate the icon.
Verify production build and actual 5202 desktop/narrow geometry and toggle behavior.
Review exact cumulative base-to-head before merge. UI-only adoption on established
5202 dist, retaining old assets; no API restart, provider calls or stored data edits.
Protect existing Run, review, notes, Plan and active selection by read-only snapshots.
Independent Architecture review, merge and postmerge settlement are required.

## Settlement — 2026-10-19
Architecture Cycle 1 approved bd547dcfbe4bd34f2004bdc7c6ad8feac2f32291;
PR #1473 merged as ffe8078f8d4ad646fa8a470c5a76133f7899faa7.
Production build and 68 focused cockpit tests passed (also independently rerun).
5202 UI index SHA256: 16ccb8e19a9470588d232eb9aca6a19ac61a468c950fd8a23cd1a81309122097.
Real desktop body/callouts grew from 736px to 984px, filling the inner card.
Collapsed book button remains within rail bounds; keyboard expansion works.
Narrow body and callout widths both 670px, no horizontal page overflow; Contents
opens via the navbar and the book keyboard control closes it. All 13 protected
responses, including active selection, notes and review, stayed exactly unchanged.
No API restart or provider call. Temporary QA tab closed; viewport override reset.
