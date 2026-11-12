# GRAPH: readable node explorer

Status: ACTIVE. User approved execution of the Lysandra node-explorer design on 2026-11-12. Root explicitly assigned bounded design, handoff and implementation to the node-explorer coordinator. Serial successor to merged #2506 (19424706b). Base fetched main 2096e2059; branch codex/graph-node-explorer-20261112. One implementation PR, merge separate.

## Lane and ownership

Checkout /home/drakosfire/Projects/.codex/graph-node-explorer-20261112/DungeonMindBuddy; scratch/cache/verification siblings on verified Projects UUID 48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8. Private writable dependencies, no /tmp allocations. Retain lane and evidence until release/cleanup is authorized. No live 5202/8000 runtime or World/auth changes. Reuse stable offline 5248 preview after ownership check.

Current open ingestion 2501/2494/2472/2471 and retrieval2462 do not own this UI. Historical2326 ownership was adopted by merged2504; this successor adopts the below native UI paths. Shared NativeGraphObjectDetails remains unchanged for other surfaces. Cursor-zoom predecessor is settled here; its implementation merged19424706b. No canvas edits in this slice.

## Invariant and critique

Replace the graph-only assertion dump with readable identity, grouped directional connections and separately labeled source summaries. Preserve all admitted assertions, source provenance, qualification and revision scope. Compact display name is only a presentation choice from recorded labels, not canonicalization or inferred current rank. Counts distinguish records from distinct neighbors. Exact inverse parent/child assertions may coalesce only with equivalent evidence and all qualifications; otherwise retain separate rows. No invented biography, current location, ownership, ally/friend or chronology. Episode anchors describe source context, not fictional time. Partial reads and hosted source limitations remain visible; on-demand citations keep the existing pinned source API and hosted prohibition. Neighbor navigation uses existing graph selection and focus; respect pending authoring guards. Mobile, keyboard disclosures, loading/error and stale-selection protection remain intact.

## Exclusive write set

- This handoff and HANDOFF-GRAPH-cursor-zoom.md (backward-looking settlement only).
- apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.tsx and .test.tsx (inspector integration/navigation).
- apps/live-control-ui/src/nativeGraphDemo/GraphNodeExplorer.tsx, .test.tsx and graphNodeExplorer.ts, .test.ts (new presentation only).
- apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemo.css.
- apps/live-control-ui/src/App.guestEntry.test.tsx (existing inspector expectations only if necessary).

Coordinator owns integration/component/styles/handoff; delegated model worker exclusively owns graphNodeExplorer.ts and graphNodeExplorer.test.ts. No API, backend, shared inspection, graph layout, dependencies, ingestion or durable data edits.

## Verification

Focused presentation and actual NativeGraphDemo integration tests; strict type/build; cumulative diff review by independent worker; final exact-head hosted qualification and discovered diagnostic with inherited failures explicitly red and identity comparison. Preserve unknown and missing-reference cases, predicate direction, coalescing evidence distinctions, disabled hosted sources, scope/navigation/loading and no semantic writes. No browser/merge/deployment claims without evidence. Commit/push/open draft PR after checks, report blockers and preview truthfully.

## User dogfood amendment (same slice, before merge)

User reviewed the retained5248 preview and requested small sticky explorer-local controls, initially collapsed relationship groups with distinct node counts, readable Campaign/Session labels, and a single component owning the explorer. Keep all admitted records/provenance. GraphNodeExplorer now owns its entire frame, identity, control navbar, loading/errors and dossier; NativeGraphDemo only supplies state/callbacks. Narrow known longmont-cN/session-N display mappings preserve unknown fallback and exact raw metadata. Audit found four general-purpose runtime renderers, two specialized inspectors and one story-only study. This slice does not delete/migrate other callers: the two native renderers share contracts and are the first future consolidation candidates; older projection renderers require explicit adapters. Scope styles to the native panel to avoid the old reader's same-name class.

## Shared primitive amendment (authorized 2026-11-12)

The owner approved continuing the shared subject/projection design. Coordinator
adopts this bounded extension in the same serial PR, reanchored on fetched
125cdb658. The existing graph dossier and native inspector begin sharing a pinned
read projection and evidence loader, not a forced universal UI. Existing modal,
statblock and navigation hosts retain their contracts. Recap prose and unadmitted
candidate renderers remain separate pending explicit adapters. No new persistence,
network fan-out, inferred edit authority or rename/delete actions are introduced.

Additional exclusive paths: graphLens/nativeObjectProjection.ts and its tests,
graphLens/nativeObjectEvidence.ts, graphLens/nodeExplorerModel.ts,
graphLens/NativeGraphObjectDetails.tsx. The earlier exclusion of shared inspection
is superseded only for these paths. Native dossier source evidence is consolidated
with the existing native inspector; graph-specific chrome remains in its host.
The subject key includes World, native binding, revision and scope. Projection
construction must reject a mismatched pin before exposing records. Evidence uses
that same pin and is loaded only on demand. Source/citation identity must include
all pin fields, not merely World and revision. Read projection never grants writes.
