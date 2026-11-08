# STATBLOCK — popup portrait generation, selection and render

ACTIVE. PRIME owns one serial UI slice after merged/delivered #2235. Base
ed4f0b30799b9b1ce58ae67908e1bcd4bd1cbfc6, branch
codex/statblock-popup-portraits; reuse buddy-context-loop checkout/dependencies.
Live API6d5d9d3bd83ae6dc21100bea8a37f409c4a2e204/schema0131 and
UI8b22cacbbe50b099cc057cec67dc05407e28cfb2 are immutable. Implementation owns no
runtime write lease. Current image capabilities report generation/library/CDN
configured. No provider configuration or output-limit change.

## One capability and owner invariant

Generate/reopen an image inside the existing saved statblock popup, explicitly
Save it through the existing media owner, choose its UUID and save a new native
statblock revision through #2235. Shared StatblockRenderer presents that saved
revision's unphased portrait in default/campaign/full entry points. The image
choice and mechanics remain with the existing single editor/recovery owner; no
second object store, editor instance, generation pipeline or asset upload path.

Extend MediaImageWizard only for selection-only hosts and ready-image selection:
no page-placement/drag instructions in this host, no false Plan-image observations,
no implicit generation/upload. Keep its normal page placement behavior. Explicit
media Save retains its public-CDN disclosure. The statblock API remains authority
for image ownership/readiness and native binding; UI state is only an affordance.

The editor retains the selected UUID, not image bytes/URLs, with its exact-version
working draft. Preserve old V1 mechanics recovery through one-way adoption into
V2 recovery records; write only V2. New selection survives popup visibility,
remount and reload. Revert/keep-current clears only unsaved selection. Save and
unknown-outcome recovery retain the original UUID and operation identity; changing
sources cannot carry a previous version's choice. The studio may keep its local
prompt state while hidden; generated images/prompts already belong to APP media.

Prompt seed contains current human creature name and flavor only, never World,
draft/version IDs, receipts or other host metadata. Saved rendering resolves only
the native unphased portrait slot, never a token/alternate/phase fallback. Refuse
unsafe image URL schemes and present failed image loading without hiding mechanics.

## Bounded write lease and dependencies

Serial, no unmerged parent; #2235's UUID Save API is already delivered. Expected:
- apps/live-control-ui/src/media/MediaImageWizard.tsx and .test.tsx
- src/statblocks/revision/SavedMechanicsRevisionEditor.tsx/.test.tsx/.css
- src/statblocks/revision/savedMechanicsRevisionTypes.ts
- src/statblocks/render/StatblockRenderer.tsx/.test.tsx/.css
- .github/workflows/hosted-validation.yml (owning UI test cohort only)
- this handoff and truthful HANDOFF-STATBLOCK-owned-portrait-revision.md settlement.
UI src paths above are relative to apps/live-control-ui. No App/router, backend,
server schema, dependencies, generated contracts or Graph publication writes.
Open PRs checked: local-World2219/2213 have no media/statblock path overlap;
ADVERSARY2218 remains draft/held with backend-only ownership. Play2172/2104 holds
remain binding and are not resumed. No new checkout or environment.

## Failure critique and verification

A staged/unknown image must not become a selectable native portrait. Library and
generation completion remain available without repeating generation. Choosing
cannot save mechanics or move World/encounter associations. Preserve selected UUID
without embedding base64 in local recovery. Failed Save remains recoverable; late
source replies/choices must not overwrite a different source version. Hidden
studio and busy/pending mechanics must respect existing owner controls.

Test real chooser behavior with synthetic port, editor payload/recovery and legacy
recovery adoption, unchanged no-image Save, exact unknown recovery, source changes,
renderer roles/unsafe URL/error reset and shared campaign/default render. Run owning
UI tests and TypeScript/build, inspect cumulative diff, independent Bugbot review,
push/open one PR, CI, protected UI-only delivery and controlled browser verification.
No dogfooding/operator acceptance. Native node/conversation entry points, one shared
cross-host editing controller, real Corrupted Edge threat creation/association and
remaining held References work stay in the full objective for later slices.
