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
