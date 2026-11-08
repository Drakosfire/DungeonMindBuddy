# SURFACE: bounded local World ZIP transport

Status: ACTIVE — one ZIP transport boundary around the validated package-core member-map codec. The corrected package-core prerequisite is Buddy PR #2207 exact head `381988b690ced4364bac3a71251cb668b5cc8260`, branch `codex/phase2a3-package-core`. This successor branch is `codex/phase2a3-zip-transport`, based exactly on that unmerged head; the intended draft PR base is `codex/phase2a3-package-core`. Merge/rebase order is #2207 first, then this transport successor. This is a stacked development lane, not product acceptance, integration, merge, deployment, or browser durability authorization.

Checkout: `/home/drakosfire/Projects/.codex/blank-surface-phase1-20261107/worktrees/DungeonMindBuddy-phase2a3-zip`.

## Exclusive write lease

- `Docs/Plans/HANDOFF-SURFACE-phase2a3-package-recovery.md` — settle the predecessor lease and record its reviewed exact head.
- `Docs/Plans/HANDOFF-SURFACE-phase2a3-zip-transport.md` — this bounded lease and final evidence.
- `apps/live-control-ui/package.json`
- `apps/live-control-ui/package-lock.json`
- `apps/live-control-ui/src/localWorld/localWorldPackageV1.ts` — only if a shared package-member path predicate is needed; do not change normalized package semantics.
- `apps/live-control-ui/src/localWorld/localWorldPackageZipV1.ts`
- `apps/live-control-ui/src/localWorld/localWorldPackageZipV1.test.ts`
- `apps/live-control-ui/src/localWorld/localWorldPackageZipV1.browserHarness.html`
- `apps/live-control-ui/src/localWorld/localWorldPackageZipV1.browserHarness.ts`

No IndexedDB/repository writes or restore, UI/editor wiring, account adoption, renderer, WorldKeeper/DM authority, model/provider call, external fetch, fixture/demo production data, merge, or deployment. Do not change paths outside this allowlist; return to the steward if another owner/path is required.

## Boundary and invariants

The transport accepts and returns the package-core normalized member map only. It must call the existing package encoder/parser so schema, identity references, canonical semantic digest, member hashes, source/fidelity declarations, layout separation, and byte/count limits stay owned by package core. It is not restore/import, collision resolution, a ZIP UI, or a claim that complete ZIP/assets v1 product support exists. It must preserve opaque asset/document bytes where package core supports them and never fetch external/missing locators.

Use a maintained ZIP library with browser support rather than custom decompression. Candidate: `@zip.js/zip.js` pinned to a reviewed exact version. Its random-access Blob reader avoids buffering a stream by default; strict entry parsing/filename validation rejects archive ambiguity; payload extraction will go to an application-owned bounded WritableStream that rejects once actual expanded bytes exceed per-member or aggregate limits. Before constructing its reader, perform a bounded ZIP32 metadata preflight over the fixed EOCD tail and central-directory extent; reject archive byte/count/declared-size/path/flag/method/overlap violations before inflation. Never claim a compression-ratio check alone prevents bombs, and never pass an unbounded convenience `Uint8ArrayWriter` to attacker-controlled entries.

Use a deliberately narrow interoperable profile: ZIP32 single-disk only; no ZIP64, encrypted entries, data descriptors, archive/member comments, extra fields, directory members, duplicate or case/NFC-colliding paths, non-UTF-8 names, unknown package paths, or unsupported methods. Permit STORE and DEFLATE only if the selected library can enforce all checks before payload allocation. Bound archive bytes, central-directory bytes, entry count, path lengths/depth, each declared expansion, total expansion, and actual streamed output. Validate local headers against central-directory records and reject overlaps/trailing or prefixed junk. ZIP writer output uses deterministic metadata and bounded member streams; ZIP32 limits remain explicit.

## Acceptance and evidence

- Round-trip codec-produced member maps through ZIP and back, including package-core records produced from the real local repository create/edit/layout APIs and binary attachments supported by the codec.
- Reject unknown package versions, malformed archive structure, traversal/absolute/backslash/duplicate/colliding paths, encryption, unsupported flags/methods, ZIP64/multi-disk, mismatched local/central headers, overlap, dishonest/oversized lengths, excessive count/depth/size, truncated payloads, and malformed payload package data. Verify failures do not invoke repository writes or fetch locators.
- Demonstrate extraction stops at actual per-entry and aggregate byte limits; document any library parser allocation that happens before this guard and constrain preflight accordingly.
- Preserve mutable-input isolation across asynchronous ZIP operations; output bytes/member maps do not alias caller buffers.
- Run focused ZIP tests, all `src/localWorld` tests, TypeScript, production build, cumulative diff checks, and independent exact base-to-head review. Browser evidence must exercise the transport in a real supported browser if runtime APIs differ; label the matrix and limits accurately.

## Limits

No package restore/write atomicity, conflict/fork UI, reload guarantee from this ZIP layer, quota/private-mode/crash/eviction behavior, cross-tab behavior, supported-browser matrix, account adoption, provenance receipt, graph semantics, or product “Saved” state is established here. Tests use generated test packages only. No World is modified by ZIP decode. Content package validation and archive transport do not by themselves establish recoverability in browser storage.

## Current implementation evidence (2026-11-08)

Dependency selected: `@zip.js/zip.js` pinned to 2.24.0 (BSD-3-Clause). It supplies seekable Blob readers, strict archive parsing, CRC and overlap checks, ZIP writing, and WritableStream extraction; this slice keeps policy and hard size limits in Buddy. Writer emits ZIP32 STORE entries without timestamp extras; reader accepts STORE/DEFLATE under the narrow profile. No ZIP parser/decompressor is hand-written. The archive file is capped at 17 MiB; central-directory metadata at 77,312 bytes; 256 entries; 256-byte UTF-8 path length; 16 path segments; per-member and total expanded lengths are bounded by the package core’s 4/8/16 MiB limits. ZIP64, multi-disk, encryption, descriptor flags, unknown methods, extras/comments, directories, path traversal, duplicate/case-fold collisions, gaps/overlaps and non-ASCII names without UTF-8 marking fail closed.

`npm test -- --run src/localWorld` passes 32/32; `npm run typecheck` passes; `npm run build` passes. The build retains the existing `connectedPageApi` dynamic/static import warning and >500 kB main-chunk warning; the optional transport is not imported by the product UI, and a production asset scan found no zip.js code in the application bundle. `npm ls @zip.js/zip.js --depth=0` confirms the pinned version. In the native browser harness, a unique IndexedDB database produced a real revision-zero World record, the package core encoded it, ZIP encode/decode returned the same identity as a validated staged member map, and the harness deleted its disposable database. This single browser run does not establish a support matrix or storage durability.

Hostile tests reject an oversized archive, encryption, ZIP64 markers, STORE entries with DEFLATE-level flags, unsupported package paths, traversal, case-colliding names, invalid package version, declared expansion above the package ceiling, and DEFLATE output that contradicts a near-limit declared size. In the understated-output case, zip.js itself reports invalid uncompressed size before the application sink cap is observed. The application sink independently counts actual emitted bytes and enforces per-member/aggregate ceilings, but this test does not prove that the sink—not the library—terminated the mismatch case. No reliance is placed on unbounded eager extraction. Package decode has no repository dependency/write path and no URL fetch call.

Independent exact cumulative base-to-head review PASS found no blocker after STORE-flag correction. The reviewer could not rerun Vitest because its read-only checkout returned EROFS while Vite created a temporary file; the author-run test, typecheck, build, and native-browser results above remain the execution evidence. Final commit/head and remote draft PR refs are recorded after publication.

## Re-anchor

The prior package-core PR #2207 remains OPEN/DRAFT at the exact prerequisite head above and is not merged. Independent exact-head review passed the corrected revision-0 seed, own-property/canonicalization, real-repository round-trip, native Chrome and Node 22.23.0 test evidence. The default suite failure previously reported on Node 21.6.2 was not reproduced on the supported default runtime and is not an outstanding blocker. Recheck remote refs and open PR/path collisions before publication. The coordinating steward retains product acceptance, serial integration and merge decisions; no merge/deploy authority is inferred here.
