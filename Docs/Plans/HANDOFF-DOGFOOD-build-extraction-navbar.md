# DOGFOOD: Build extraction navbar

Status ACTIVE, operator directly requested2026-10-14. Base00944a0b6a0db93767806f1b2d3cfd47dc435360;
branchcodex/build-extraction-navbar; isolated non-serving editor-mount-cleanliness checkout.
Topology serial one PR. Prior1170 merged00944; sourceCSS239a equivalent live accepted.
Open1163/MINDleases disjoint; no unmerged behavioral dependency.
Exclusive write set:
- apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx
- apps/live-control-ui/src/buildSurface/BuildSurfaceContext.tsx
- apps/live-control-ui/src/buildSurface/BuildIngestToolbar.tsx
- apps/live-control-ui/src/buildSurface/BuildSurfaceContext.test.tsx
- apps/live-control-ui/src/buildSurface/BuildIngestToolbar.test.tsx
- apps/live-control-ui/src/buildSurface/buildSurface.css
- this handoff

Move existing extraction UI into a collapsed Extraction disclosure on the source
navbar. Keep hooks mounted under original Canvas session; portal presentation into
an explicitly referenced navbar slot, preserving React context and request ownership.
No global DOM lookup, hook relocation outside provider, duplicate toolbars, lazy
mount/reset on disclosure, or source/extraction/publication behavior change.
Expanded disclosure flows/wraps inside nav, avoiding popup viewport clipping.
Existing profile/status/errors/refresh/retry/run/GraphReview actions remain inside.
No provider/extract/sourceSave/admission/retainedGraph writes for verification.
Verify navbar composition, single toolbar/context preservation, existing owning
selection/commands/tests; TypeScript/build/cumulativediff;390/647render acceptance.
Independent review before owned5202adoption; stable5876 untouched. No merge authority.

Implementation evidence: explicit navbar divref passed through Context; existing
Toolbar retains original hook/session ownership and portals its presentation.
Native details startsclosed; DOM staysmounted to preserve profile/status.Expanded
content flows/wraps inside navbar, no viewport-positioned popup.31owning tests pass
across Context/Toolbar/Selection/Page, appTypeScript and productionbuildpass.
RealCanvasprovider portal test mounts outside providerDOM but retains Reactsession,
asserts singletoolbar, closedinitial, profile retained through toggles, zero
launch/admission and portalcleanup on unmount. Navbar slot tested in actualContextHost.
Page tests emit React act warnings in navigation/retainedSave cases; all pass.
Cumulative7path diff inspected; no nonpresentation hook changes. Independentcode
review/rendered390/647 checks remain required; no deployment claimed yet.

Rendered6c546c: collapsed390/647 fits, nativeEnter/Space toggle keeps summary
focus and Tab enters profile; profile persists and one toolbar.Expanded390
FAILS: page493px; navbar row min-width:auto retains384.1875px mincontent inside
309px module. SameleasedCSS repair gives row min-width0/flex1. Previous rendered
head remainsHOLD; new exacthead review/390expanded acceptance required.
