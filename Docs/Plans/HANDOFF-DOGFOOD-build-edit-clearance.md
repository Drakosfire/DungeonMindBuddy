# DOGFOOD: Build Edit paper clearance

Status ACTIVE. User approved the scoped rendered repair; PRIME explicitly
transferred the merged #1183 Build authoring and Build narrow-layout leases on
2026-10-15. Current Buddy `main` is `990d229d6f131985b830fabc2a6598a5b12f61a5`.
Implementation branch: `codex/build-edit-clearance`, based directly on that
main commit, in `/tmp/buddy-build-edit-clearance`.

Topology is serial and independent: one new PR for this post-#1183 presentation
repair. Open PR inspection found no overlapping Build UI implementation PR.
ARCHITECTURE reviews the exact completed head; PRIME owns merge. No runtime
replacement or user-data write is part of this lease.

## User-visible defect and invariant

With Edit open at desktop width, the fixed left command-board drawer overlaps the
paper projection and hides its left text. Build currently leaves the paper at
full width while the shared Edit host uses `--app-edit-host-dock-width`. At
narrow widths, the shared host and Build CSS turn Edit into a bottom sheet.

Opening Edit must leave the complete paper text readable and reachable at
1280×720 and 390×844, with no horizontal page overflow and no text hidden under
the left drawer. At desktop, Build reserves the actual left dock width and
reflows the paper into the remaining content area. At narrow width, the paper
remains horizontally full-width and its vertical scroll can reach content past
the bottom-sheet overlap. Closing Edit restores the original full-width paper
layout.

Preserve source bytes, selected source, editor mount/focus, dirty state, Save/CAS,
undo/redo, source navigation, graph references, shared conversation, Tools,
Plan/Play, and global/shared hosts. Do not edit shared styles, routes, APIs,
source data, runtime configuration, or other surfaces. The preview may be read
for rendered acceptance; 5202 and 5876 remain untouched.

## Exclusive write lease

This branch owns only these paths:

- `Docs/Plans/HANDOFF-DOGFOOD-build-edit-clearance.md` (this contract)
- `Docs/Plans/HANDOFF-DOGFOOD-build-authoring-workspace.md` (settle merged #1183)
- `Docs/Plans/HANDOFF-DOGFOOD-build-narrow-layout.md` (settle superseded lease)
- `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx`
- `apps/live-control-ui/src/buildSurface/buildSurface.css`
- `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx`

The two predecessor handoffs are included solely for truthful backward-looking
settlement. PRIME transferred their relevant exclusivity; old implementation
leases end with this pinned successor. The shell component is authorized only if
a Build-local marker or scroll-boundary adjustment is necessary. Keep any code
change to Build-local layout rules; no shared host or global stylesheet changes.

## Verification and evidence

- Add an owning browser-geometry regression in `BuildSurfaceShell.test.tsx` that
  proves Edit-open paper bounds begin outside the desktop drawer and narrow
  document content can scroll beyond the bottom sheet, while closed layout is
  unchanged. Avoid CSS-string-only assertions as the geometry proof.
- Integrated rendered acceptance used the merged #1183 Build source on the
  existing preview for baseline and a disposable branch-built Vite preview on
  5208 for after. Opened/closed Edit and scrolled the paper only; no source edits,
  saves, or Buddy messages were made. The exact Mirathorn source loaded in the
  candidate preview. The graph badge showed `Needs attention` there, so graph
  readiness was not part of this layout acceptance.
- Baseline desktop screenshot: `/tmp/build-1183-merged-workspace.jpg` (1280×720),
  showing the 380px Edit drawer covering the paper's left text. Candidate desktop
  screenshot: `/tmp/build-edit-clearance-after-desktop.png` (1280×720); measured
  drawer x=0..380 and paper frame x=416..1244, with the paper text beginning at
  x=504. Candidate narrow screenshot:
  `/tmp/build-edit-clearance-after-narrow.png` (390×844); drawer y=489.5..844,
  paper's final paragraph bottom y=335.2 after scroll, and document scroll width
  390px. The existing preview's viewport override did not change its screenshot
  dimensions, so no saved narrow baseline image is claimed.
- Run the owning Build shell tests, UI typecheck/build, and `git diff --check`;
  inspect the exact cumulative main-to-head diff.
- Preserve failure output and explicitly state any preview/auth/backend limits.
  Do not send or replay a Buddy question as part of layout verification.

The supplied 1280×720 screenshot is the reported baseline: drawer x=0..380
covers the paper's left text column. The starting source is the merged #1183
paper/editor UI at main@`990d229`; no source change is expected to be needed.

## Acceptance evidence — 2026-10-15

The branch-built 5208 preview verified the actual Build shell and loaded source
at both target sizes. On desktop, the paper frame starts 36px to the right of
the 380px drawer; on narrow, its last paragraph is reachable above the bottom
sheet without page-width overflow. `BuildSurfaceShell.test.tsx` passed 30/30 with
`BUILD_LAYOUT_CHROMIUM_PATH=/usr/bin/google-chrome`; `npm run typecheck`,
`npm run build`, and `git diff --check` passed. Build emitted its existing
large-chunk advisory. The Vite development server could not start because the
container reached its file-watcher limit; the production preview worked and was
stopped after screenshots were captured. Existing 5207 state was restored with
Edit closed. 5202 and 5876 were not touched.
