# SURFACE: edit one local World document

Status: ACTIVE under Alan's explicit instruction to continue the Buddy front-door plan through PRIME-led merges. This is one stacked successor capability. Base is the exact reviewed code+handoff head `02d79ceb0e767a67872e4c8c83c2a539ce6829bf` on `codex/phase2a5-local-world-surface`; PR topology is #2213 → this successor draft (planned #2214). #2213 itself is still based on old #2210 `cd2bd138c9657487ba6ecf56f3c739ef1dc7b51d` and conflicts with corrected #2210 `9f0fe5be55c72ca52d6d5b8355944620288ee9d7`. This implementation may proceed against the pinned parent; it is not mergeable until PRIME reconciles the predecessor stack, then this slice is re-anchored, re-tested, and independently reviewed at the combined head. No deployment authority is implied.

Checkout: `/home/drakosfire/Projects/.codex/blank-surface-phase1-20261107/worktrees/DungeonMindBuddy-phase2a6-local-document-editing`.

## Product outcome and boundaries

On an already-open local World, a user can explicitly start or resume one editable **World notes** Markdown document in the existing Buddy Surface. Use shared `MarkdownEditorCore` for its editor UI. Persist the document body through a Buddy-owned asynchronous local authoring adapter; never pass a Buddy-local ID/revision through `useWorkspaceDocumentAuthoring` or hosted snapshot/prepare/commit APIs. Report local save only after IndexedDB transaction completion. Keep the current hosted auth gate and `SelectedWorldProvider` behavior unchanged; this is not guest entry. Do not add graph objects/edges, account adoption, model/provider calls, or a renderer.

The note is one bounded user-authored document per local World, stored as a normal bundled Markdown document in existing `LocalWorldPackageData.documents` / `bundledMembers`, so current validated package export carries it. Its reserved identity is `buddy-local-world-notes`, path `documents/buddy-world-notes.md`, media type `text/markdown`. Refuse a collision with incompatible imported content; do not overwrite or normalize it. Every body commit must preserve all other sidecar references/bytes and append a Buddy-local history event while incrementing `LocalWorldRecord.localRevision`.

Use the existing schema-v3 `packageData` and `conflicts` stores if the current source confirms they can hold this boundary without schema migration. The write transaction must atomically commit the World revision/history, the updated notes member and preserved sidecar; a stale expected revision must leave current state intact and retain the complete proposed sidecar in a conflict candidate. No check-then-write. A conflict is not saved. Retain its candidate through route remount/reload and require an explicit reapply or discard action. Do not add generic document-management APIs or a second truth ledger.

Set a concrete UTF-8 body-size bound (maximum 1 MiB) and validate before allocation/transaction. Reject unsupported or malformed UTF-8 without silently changing the body. Layout-only updates remain independent. No archive import or new package format is included.

## Exclusive write set

- `Docs/Plans/HANDOFF-SURFACE-phase2a6-local-world-document-editing.md`
- `apps/live-control-ui/src/localWorld/localWorldRepository.ts`
- `apps/live-control-ui/src/localWorld/localWorldRepository.test.ts`
- `apps/live-control-ui/src/localWorld/inMemoryLocalWorldRepository.ts`
- `apps/live-control-ui/src/localWorld/inMemoryLocalWorldRepository.test.ts`
- `apps/live-control-ui/src/localWorld/indexedDbLocalWorldRepository.ts`
- `apps/live-control-ui/src/localWorld/indexedDbLocalWorldRepository.test.ts`
- `apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldSurface.tsx`
- `apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldNotesEditor.tsx` (new)
- `apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldNotesEditor.test.tsx` (new)
- `apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldSurface.test.tsx`
- `apps/live-control-ui/src/localWorld/localWorldSurface/localWorldSurface.css`
- `apps/live-control-ui/src/localWorld/localWorldDocumentAuthoring.ts` (new, only if needed for the explicit async adapter)
- `apps/live-control-ui/src/localWorld/localWorldDocumentAuthoring.test.ts` (new, only if needed)
- `apps/live-control-ui/src/localWorld/localWorldSurface/localWorldSurface.browserHarness.tsx`
- `apps/live-control-ui/src/localWorld/localWorldSurface/localWorldSurface.browserHarness.html`
- `apps/live-control-ui/src/localWorld/localWorldSurface/localWorldSurface.browserHarness.css`

No lockfiles/dependencies, schema upgrade, global routing/auth/selected-World changes, hosted API, server or owner-repository changes, unrelated shared editor changes, graph renderer, account adoption, provider calls, existing user database edits, or production data/runtime changes. If a new store/schema or a path outside the allowlist proves necessary, stop and report the smallest owning seam before editing it.

## Acceptance and evidence

- An empty World displays an explicit Start writing action; mounting/opening never creates a document or mutates storage automatically.
- Starting notes and editing/reloading/reopening preserves the same local World identity, title, note bytes, history and revision. Markdown uses the shared `MarkdownEditorCore` behind a lazy import. YAML frontmatter is preserved byte-for-byte while editing the body; parser-warning constructs such as imported task-list Markdown render read-only with their original package bytes intact. A recovered conflict is a read-only preview until explicit Reapply; then it is the current saved note and can be edited.
- Package export after editing decodes to the same note bytes plus every pre-existing attachment/source reference and byte. Same-named distinct Worlds remain independent.
- Edits capture world ID, expected local revision and body before any await. Concurrent same-revision saves have one winner; the other complete body and sidecar are retained as a conflict candidate. Neither stale success nor error may clear or display over a newer draft. The conflict candidate survives unmount/remount/reload; reapply/discard is explicit.
- Inject IndexedDB transaction abort/error and malformed/oversize body cases; committed body, history, sidecar and exported package remain unchanged and UI never says Saved. Test repeated input, pending navigation, and response ordering.
- No hosted snapshot/prepare/commit call, global auth relaxation, model/provider call, graph retrieval or local-to-hosted ID alias occurs on this local note flow.
- Use a uniquely named disposable IndexedDB database. Test the native browser route for start → type/edit → transaction saved → reload/reopen → export → codec decode, plus conflict, failure and restored attachment preservation. No disclosed browser World may be deleted or altered.
- Run focused repository/editor tests, complete `src/localWorld` suite, typecheck/build, exact cumulative diff inspection, and independent exact-head review. Reproduce the seven inherited hosted-route/jsdom failures at the pinned parent before labeling any cohort failure inherited.

## Deferred

Anonymous guest entry remains a separate route/auth boundary slice. This handoff does not prove public unauthenticated safety. General multi-document lifecycle, import collision/fork UI, full history/provenance semantics, graph node/relationship authoring, local account adoption, real quota/private-mode/crash/eviction durability, cross-browser guarantees and weak-device performance remain unclaimed.

## Current implementation evidence (2026-11-08)

- Full `src/localWorld` suite: 7 files, 71 tests passed on Node 22.23.0. Typecheck and production build passed. The build retains existing dynamic/static import notices and the >500 kB main-chunk warning.
- Adjacent App/chrome/navigation suites: 55 passed, 7 failed. The same 3 App and 4 navigation failures reproduced on exact pinned parent `02d79ceb0e767a67872e4c8c83c2a539ce6829bf`; hosted-route failures are jsdom relative `/api/live/...` fetch/URL and navigation limitations. This slice did not alter hosted routing or auth.
- Native Chrome checks used disposable `local-world-surface-test-<uuid>` IndexedDB databases. Verified create → real MarkdownEditorCore edit/autosave → Surface close/reopen → readback → package codec/ZIP decode. A second connection advanced the revision to create a note conflict; after reload, committed text was shown and explicit Recover → Reapply saved the candidate. Aborting after the World write request left both revision (2) and old committed note unchanged on second-connection readback; the attempted edit remained an unsaved draft with unload protection. No existing or disclosed user World was used or deleted.
- The task-owned screenshot is `/media/drakosfire/Projects/.codex/2026-11-07/task/phase2a6-native-surface.png`.
- Production bundle observation: the pinned Phase2A5 build artifact main entry was 596,490 raw / 169,704 gzip bytes. This build's main entry is 721,550 raw / 205,620 gzip (+125,060 raw / +35,916 gzip); `MarkdownEditorCore` is split as 83,770 raw / 24,830 gzip and is absent from the root's initial asset requests (main JS, CSS, launcher image only). It is requested after opening a notes document. ZIP remains separate at 174,500 raw / 73,490 gzip and is fetched only for export. These are measured artifact/request observations, not weak-device performance claims.
- Independent review of the latest working tree passed conflict-preview, metadata, stale-draft and remount checks; exact committed-head review is pending. Earlier review results against mutable trees are superseded.
- Predecessor #2213 remains open/draft and conflicts with corrected #2210. This successor must be re-anchored, tested and independently reviewed on the composed stack before PRIME-led serial merge. No merge or deployment is authorized by this handoff.
