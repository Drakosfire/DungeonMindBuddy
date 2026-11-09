# REFERENCE: contain the shared native object inspector

Status: SETTLED. #2282 merged at `534ff9c70499d6dc847c949465e95a32e1012467` from reviewed source `8ba79e1c05438246320cee6d992989313dc0d4e2`. UI `3e718e047f2f706287c2297fa89e293d88961523` delivered on 5202; lease released. Exact frozen tests (27), TypeScript/build, independent source/composition/recipe review, all seven CI checks and wide/narrow live rendering passed. Retained APP/Core rows and session state unchanged. PRIME owned one serial independently reviewable PR from `398d01a540bba5c4a53d99d65e3af34eb13b6c8e`, branch `codex/reference-inspector-layout`, existing buddy-context-loop checkout. No unmerged parent. Independent review and CI precede protected delivery.

## Outcome and boundary

NativeGraphInspection must own its reusable layout rather than depending on the Graph dialog wrapper. Long labels and exact IDs must stay inside the results column in Build and conversation embeddings. Preserve accessible identity, existing selection actions and native detail/statblock owners. Use available component width for narrow layout; do not invent another picker or transport.

## Exclusive write lease

- This handoff.
- apps/live-control-ui/src/graphLens/NativeGraphInspection.tsx and NativeGraphInspection.css.
- apps/live-control-ui/src/surface/SurfaceGraphReferenceInput.css: migrate the existing compact embedding selector and preserve flex button widths. Required consumer correction found in independent review, within the same layout outcome.
- Docs/Plans/HANDOFF-REFERENCE-native-document-links.md: truthful backward-looking settlement of delivered #2280.

No API, schema, dependency or content changes. Open LocalWorld and held Play work remain outside this slice. Runtime activation requires a separate pinned lease and reviewed delivery recipe. Coordination with ADVERSARY remains off.

## Verification

Run existing native inspection and embedding tests, TypeScript and production build. Inspect the cumulative diff and obtain independent review. Verify long labels, IDs and object details at wide and narrow component widths in the rendered UI before claiming delivery. Preserve unsaved documents and inspect existing objects read-only.

## Predecessor

#2280 source `fff54d027b28cc0ad3e52822dfd96a37b468627a`, merge `34d8f65cc22e400e636910353f2972216dfe85ad`, delivered UI `753dba8415c11aa9dffb3b84fe8598f426e51997`. Read-only delivered inspection reached the existing native ooze statblock through the shared editor; full APP/Core row and session conservation verified. The screenshot exposed result-label overflow in the embedded inspector, which this slice owns.
