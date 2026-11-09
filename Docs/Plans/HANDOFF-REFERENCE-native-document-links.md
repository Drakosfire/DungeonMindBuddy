# REFERENCE: native object links in Build documents

Status: SETTLED. #2280 merged at `34d8f65cc22e400e636910353f2972216dfe85ad` from reviewed source `fff54d027b28cc0ad3e52822dfd96a37b468627a`. UI `753dba8415c11aa9dffb3b84fe8598f426e51997` delivered on 5202; runtime lease released. Exact frozen UI tests (1,127), TypeScript/build, independent source/integration/recipe reviews, and read-only browser inspection passed. All retained APP/Core rows and session state were conserved. Browser inspection reached the native ooze and shared saved statblock editor without content writes. Embedded inspector layout overflow is owned separately by HANDOFF-REFERENCE-inspector-layout.md. PRIME owned this bounded References integration slice under the active goal. Base `eb0eb9a093b275e8e8282d6c749309f2bdd687a6`, branch `codex/reference-native-document-links`, existing buddy-context-loop checkout. One serial PR; no unmerged parent. Independent exact-head review and CI precede protected delivery. No deployment or database writes in implementation.

## Outcome and invariant

Build document Find existing object must read the same native entity/assertion Graph as the shared native inspector. Insert existing graph-node references and open existing native previews, including the shared statblock owner. A document link navigates a current object; it is not a historical evidence citation. Captured conversation references keep their exact pins. Never convert an old object-projection revision into a native pin.

Observed read-only evidence: managed Elderwyld binding3 has 1,404 native entities and 6,102 assertions while the obsolete managed object projection returns zero. No ingestion, publication or source mutation is needed to fix this UI path.

## Boundary and failure cases

Reuse NativeGraphInspection, NativeGraphObjectPreview, existing Markdown graph-node syntax and MarkdownCanvasSession Save. Require admitted document World identity, not campaign-slug equality. World-owned pages with null campaign remain usable. Missing World authority explains unavailability; no legacy Graph fallback. Preserve Rules, statblocks, work identity and Save independently of Graph availability.

Insertion is bound to the captured document, editor and World. Reject retained callbacks after document/World/editor replacement, conflict, destruction or unmount. Native reads use captured current pins and existing inspection checks. Late responses cannot open or mutate a replacement document. NodeViews pass source-editor identity to the existing runtime so nested read-only source editors cannot accidentally resolve links in a different document World. Preview failure stays visible and retryable. No application output limits or new provenance authority.

## Exclusive expected write lease

- This handoff.
- apps/live-control-ui/src/buildSurface/reference/* (native capability/publication/search; retire obsolete Build-only projection loader, lens, information channel and object projection plus their retired tests after caller audit).
- apps/live-control-ui/src/graphLens/NativeGraphInspection.tsx and its existing tests (explicit selection action label for insertion, preserving conversation default).
- apps/live-control-ui/src/api/nativeGraphInspection.ts (factor existing catalogue identity check, no transport change).
- apps/live-control-ui/src/graphReference/GraphNodeChipRuntime.tsx (forward editor-affinity handler without changing existing Plan activation).
- apps/live-control-ui/src/graphReference/types.ts (source-editor navigation identity only).
- apps/live-control-ui/src/tiptap/extensions/GraphNodeReferenceView.tsx and RunbookReferenceView.tsx (forward source editor).
- apps/live-control-ui/src/App.test.tsx and buildSurface/BuildSurfacePage.test.tsx (replace obsolete Graph fixtures while preserving route, saved-draft and stale Save guarantees).

Open PR2276 LocalWorld route and held Play2172 do not own these paths. ADVERSARY native Turn construction work names server types/native_context/native_execution, not UI paths. No schemas, dependencies, runtime ports, primary databases or retained content are leased for writes here.

## Validation and demolition

Prove native search, exact identity insertion, existing Markdown roundtrip/reload, actual node-view preview, no obsolete Graph request, null-campaign World pages, loading/errors and stale callback/read refusal. Preserve Save command tests, dirty drafts, document switch and nested reader isolation. Run affected UI tests and TypeScript/build. Review cumulative base-to-head diff and independent Bugbot judgment before merge. Retire only modules with no remaining exercised caller; do not demolish held Plan/Play owners. Controlled delivered browser verification uses read-only existing objects, with disposable fixtures for insertion/persistence. Keep live content unchanged.
