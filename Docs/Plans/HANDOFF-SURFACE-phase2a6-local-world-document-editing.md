# SURFACE: edit one local World document

Status: ACTIVE under Alan's explicit instruction to continue the Buddy front-door plan through PRIME-led merges. This is one stacked successor capability. Base is the exact reviewed code+handoff head `02d79ceb0e767a67872e4c8c83c2a539ce6829bf` on `codex/phase2a5-local-world-surface`; draft PR #2219 targets that branch. PR topology is #2213 → #2219. #2213 itself is still based on old #2210 `cd2bd138c9657487ba6ecf56f3c739ef1dc7b51d` and conflicts with corrected #2210 `9f0fe5be55c72ca52d6d5b8355944620288ee9d7`. This implementation may proceed against the pinned parent; it is not mergeable until PRIME reconciles the predecessor stack, then this slice is re-anchored, re-tested, and independently reviewed at the combined head. No deployment authority is implied.

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
- `apps/live-control-ui/src/localWorld/indexedDbLocalWorldRepository.browserHarness.ts`
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

- Full `src/localWorld` suite: 7 files, 74 tests passed on Node 22.23.0. Typecheck and production build passed. The build retains existing dynamic/static import notices and the >500 kB main-chunk warning.
- Adjacent App/chrome/navigation suites: 55 passed, 7 failed. The same 3 App and 4 navigation failures reproduced on exact pinned parent `02d79ceb0e767a67872e4c8c83c2a539ce6829bf`; hosted-route failures are jsdom relative `/api/live/...` fetch/URL and navigation limitations. This slice did not alter hosted routing or auth.
- Native Chrome checks used disposable `local-world-surface-test-<uuid>` IndexedDB databases. Verified create → real MarkdownEditorCore edit/autosave → Surface close/reopen → readback → package codec/ZIP decode. A second connection advanced the revision to create a note conflict; after reload, committed text was shown and explicit Recover → Reapply saved the candidate. Aborting after the World write request left both revision (2) and old committed note unchanged on second-connection readback; the attempted edit remained an unsaved draft with unload protection. No existing or disclosed user World was used or deleted.
- The task-owned screenshot is `/media/drakosfire/Projects/.codex/2026-11-07/task/phase2a6-native-surface.png`.
- Production bundle observation: the pinned Phase2A5 build artifact main entry was 596,490 raw / 169,704 gzip bytes. This build's main entry is 721,770 raw / 205,620 gzip (+125,280 raw / +35,916 gzip); `MarkdownEditorCore` is split as 83,770 raw / 24,830 gzip and is absent from the root's initial asset requests (main JS, CSS, launcher image only). It is requested after opening a notes document. ZIP remains separate at 174,500 raw / 73,490 gzip and is fetched only for export. These are measured artifact/request observations, not weak-device performance claims.
- Independent review held initial implementation head `1a12903c36677780dcad0c55b7f51753c0e43670` for an export consistency race: separate World/sidecar reads could encode an old local revision with newer notes. Corrected at `dc6073d0d514a0808ca61966b79379bf473ec993` by adding `readWorldExportSnapshot`, an atomic IndexedDB readonly transaction over the World and package-data stores, and switching user export to that snapshot. Independent exact-head review passed there: 72/72 localWorld suite, 54 native IndexedDB harness checks including concurrent export snapshot/write, TypeScript and cumulative diff.
- Root review held PR #2219 at `218a3045cd81b66de3b54039f46ad8cc13d9dbe9`: a persisted conflict could hide and overwrite a newer tab-local draft during recovery. Correction `c7414812eb7db5aee74752c37e5d8474a08da510` keeps tab and persisted candidates separate and previews stored candidates without writing into the one-slot tab draft. It added coexistence and delayed save → unmount/remount → newer edit → old conflict → recover regressions. Root's scoped independent review passed that finding, with reported 74/74 localWorld, typecheck and build checks.
- Root's next exact-head review held `c7414812eb7db5aee74752c37e5d8474a08da510`: when the pending tab draft exactly matched the persisted losing candidate, `Recover → Keep saved version` discarded the stored candidate but left the losing text editable. The correction captures candidate identity/text and the pending draft token, and clears only that exact captured matching draft after successful discard. A newly created same-text draft has a new token and remains unsaved and visible. Regressions cover matching candidate discard and same-text draft recreation during a delayed discard. Corrected focused editor suite passes 11/11; complete `src/localWorld` suite passes 76/76; TypeScript and production build pass. Independent exact-head review of this correction remains pending.
- Current remote snapshot checked after the dual-draft correction: main `1ef0248605082db40e62562693f2ec210ce2a9e4`; #2219 remains OPEN/DRAFT at `c7414812eb7db5aee74752c37e5d8474a08da510`, based on `codex/phase2a5-local-world-surface` at `02d79ceb0e767a67872e4c8c83c2a539ce6829bf`. #2213 remains OPEN/DRAFT/CONFLICTING and based on superseded #2210 head `cd2bd138c9657487ba6ecf56f3c739ef1dc7b51d`; #2219 cannot merge until PRIME reconciles and qualifies the predecessor stack. PRIME was notified of the new HOLD and remains the sole merge actor. No deployment is authorized by this handoff.
