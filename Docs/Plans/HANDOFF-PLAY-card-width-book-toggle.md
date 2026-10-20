# Play card width and Contents toggle

Status: ACTIVE. User authorized the annotated Play width and book toggle fixes.
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
