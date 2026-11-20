# STATBLOCK — popup portrait generation, selection and render

SETTLED / write lease RELEASED. Source93731eae45499a8753ac434743c041342e9ac739
merged #2237 as194b49378e779be96913693c61fff0229cbd64bc. Delivered UI
5c02f027d15397f2b53ea4bb69e5cdb46f1fa8ce on5202; source cycle2 and integration/
recipe cycle1 APPROVE, all7CI checks,76source/91integration tests and build pass.
Actual owned-library selection, UUID-only local recovery, reload and390px checks
pass with no provider/upload/mechanics writes. API6d5d9d3/schema131/user rows and
session unchanged at activation; subsequent independent #2218 delivery moved API
to8008dc5 with UI unchanged and repeated portrait/citation checks passing.
Evidence: private runtime-evidence/q01-published-graph-authority/
statblock-popup-portrait-ui-resources.json and linked proofs. Earlier HOLD head,
malformed-reference finding and failed test wait remain retained. This is context,
not a live lease. Shared cross-host editing and real threat integration remain open.

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
