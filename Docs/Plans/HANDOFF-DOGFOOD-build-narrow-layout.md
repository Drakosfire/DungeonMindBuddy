# DOGFOOD: Build narrow layout

Status SETTLED/SUPERSEDED after the narrow-layout CSS was carried into PR #1183,
merged at `990d229d6f131985b830fabc2a6598a5b12f61a5`. The recorded narrow
acceptance limits remain historical; this settlement does not claim broader proof.
PRIME transferred the old CSS exclusivity to the successor
`HANDOFF-DOGFOOD-build-edit-clearance.md`; this handoff now grants no write authority.
Base97dff3f0bf7941ed9ca4e4f1845947cfd73acbe4; branchcodex/build-narrow-layout;
checkout /home/drakosfire/.codex/worktrees/editor-mount-cleanliness/DungeonMindBuddy.
Topology serial one independent PR; existing open1163 and MIND1139/1142–1149
leases checked, disjoint source/test paths and no behavioral dependency.
Exclusive write set: this handoff and
apps/live-control-ui/src/buildSurface/buildSurface.css.
Test write set empty: CSS-only repair verified at actual browser layout boundary;
run existing BuildGazetteerSelection, reader and editor-clean tests unchanged.
No mirror CSS-string test. Amend lease before other paths are edited.

Invariant: 390px Build content and controls fit viewport without horizontal
page scrolling/clipping; preserve647px layout, readable45-section outline,
anchor/duplicate heading navigation, clean Edit mount and saved source reopen.
Likely cause: flex child app-wrap has auto width and min-content contribution
from native select355px plus toolbar/outer padding=424px. Verify rendered repair;
no global overflow:hidden that clips content. OffscreenTools remains out of scope
unless same root sizing repair resolves it. No new independent capability.
No Markdown/editor/extraction/publication semantics, source/retainedGraph/provider,
dependencies, sharedshell or other stylesheet edits. No sourceSave/model call.
Runtime lease existing owned5202/8000/7860 only, stable5876 untouched; serving
foundation97dff source is read-only. Implementation separate branch. Independent
ARCH code review before runtime adoption unless PRIME explicitly authorizes
bounded preview. OpeningPR included, merge belongsPRIME.
Proof: actual390/647 browser widths, no horizontaloverflow, controls fit,
outline/navigation/Editclean, exact savedsource rev2/SHA70444f40… before==after,
existing owningtests, appTypeScript/build, cumulative main→head diff, PR review.
Rendered reproduction receipt: buddy-foundation-97dff3f0/adoption/foundation-rendered-receipt.json;
DOGFOODvisualizations/mirathorn-narrow-97df.png and narrow-top-97df.png.

Code evidence: Build-only app-wrap takes100% of available width with min-width0;
profile label wraps with explicit gap and select max-width100%/min-width0.
No hidden overflow suppression, sharedshell edit or Tools feature change.
29 existing owning cases pass (3selection,15reader,11editor-fidelity), app
TypeScript and production build pass. Exact cumulative diff is2leasedpaths.
Actual390/647 candidate layout acceptance remains pending independent code
review/ownedruntime replacement. Reproduction metrics are baseline, not fix proof.


## Lease settlement — 2026-10-15

The narrow layout work was included in the merged Build authoring PR #1183 at
`990d229d6f131985b830fabc2a6598a5b12f61a5`. Its old implementation lease is
closed. The new desktop Edit-clearance defect is separate; its scope and proof are
recorded in `HANDOFF-DOGFOOD-build-edit-clearance.md`. Historical viewport and
source evidence above are preserved without upgrading their claims.
