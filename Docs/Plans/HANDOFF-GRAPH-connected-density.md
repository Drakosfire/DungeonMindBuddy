# GRAPH: reveal loaded graph connections

Status: ACTIVE. Alan requested relationship-weighted bubbles, a connected-only default, truthful NPC/PC/item/event colors, recorded names instead of a hiding “Multiple” label, and circular presentation after the first experiment shipped. Root explicitly assigned bounded design and implementation authority, including necessary read-adapter/API files, on 2026-11-12. Implement one serial loaded-graph presentation PR; no 3D, identity correction, inferred roles/edges, data repair or live writes.

## Predecessor, source and ownership

The first full-bubble experiment merged as #2464 at 77175b77212b35b2c2d0a0507a4ef314dea23b22 and its exact tree was deployed to the local frontend after explicit positive user pan feedback. Fresh hosted qualification and independent review passed; inherited full-discovery failures and browser/performance limits remain recorded, not relabeled green.

Re-anchored current remote main d7b0b1a1796a0777c5d193ccbfaa037d7bf4cf66 on resumption, including #2467's backend event placement and #2466's disjoint PDF table work. That exact commit is already present locally; no denied network action was retried. Current AGENTS is unchanged. Reuse the clean existing worktree at /home/drakosfire/Projects/.codex/full-bubble-graph-20261111/worktrees/DungeonMindBuddy on codex/graph-connected-density-20261112. Task scratch/evidence stays under its existing Projects task root. Do not modify the running first-release artifacts.

All 56 current open PR file sets were rechecked. Only historical #2326 at unchanged b30833ede97cb4c79acf17a1fe55ff50446c7452 overlaps canvas paths already reconciled by the shipped graph predecessors. No dirty overlapping path was found in 84 readable registered worktrees. The older native demo and hosted-owner handoffs refer to merged predecessors #2330 (36fce5feb) and #2374 (1b5e87418), both ancestors of current main. Root's explicit successor assignment grants the narrow presentation/read-adapter lease below; existing owner/auth/publication contracts are retained unchanged. No active code owner or open PR overlaps the new read-adapter paths.

Implementation resumes after Alan's explicit instruction to continue bubble graph work. The graph-health investigation found the recent C1 evaluation dataset separate from the live graph; this presentation slice does not label legacy gaps as current ingestion regressions.

## Invariant and design

- Count distinct valid incident relationship IDs across the full loaded snapshot before focus, search or visibility filters. Count a self-loop once for its object; parallel/reverse distinct IDs each count. Missing-endpoint edges do not contribute.
- Native embedded overview hides objects with zero listed connections by default. Keep a reveal toggle/count, every ID in search/export/connection choices, and saved positions. Search focus and exact-receipt newly created nodes remain accessible, including recovery replay. Filtering is not truncation or deletion; retain partial-read warnings.
- Full-bubble area grows with log(1 + loaded relationship count), from radius 32 to the existing 56-unit maximum, saturating at 100 relationships. Preserve the stored-position meaning with a fixed 56-unit center offset. Edge anchors, loops, ports, hit tests, focus and Fit share the same radius. Do not size by focused degree.
- Automatic fallback presentation becomes a deterministic circular arrangement using multiple rings or a packed disk, not one overloaded ring. Preserve pins and prior World-local fallback positions across revisions. Keep all IDs finite within the existing coordinate domain, with graceful crowding at extreme sizes and no invented spacing guarantee for arbitrary user pins. Circular arrangement does not assert semantic distance.
- Add optional presentation metadata to the existing same-pin explorer response: deterministic recorded names and exact admitted classification terms. Preserve legacy native name/kind fields, auth/binding/revision checks, completeness accounting, payload bounds and all write/recovery contracts. No extra catalogue request or per-node request fan-out.
- Show meaningful recorded names without choosing an authoritative name, calling alternatives aliases, merging identities or altering assertions. Search includes all recorded names; full alternatives remain inspectable.
- Use distinct colors only for explicit supported classification terms. Generic character is not NPC or PC. Mixed/unknown classifications remain honestly represented. No inference from narrative, candidate hints, corpus path or absence of a role.

## Expected exclusive write lease

- Docs/Plans/HANDOFF-GRAPH-connected-density.md
- Docs/Plans/HANDOFF-GRAPH-full-bubble-overview.md (truthful predecessor settlement only)
- apps/live-control-ui/src/localWorld/worldGraphCanvas/graphProjection.ts
- apps/live-control-ui/src/localWorld/worldGraphCanvas/graphProjection.test.ts
- apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.tsx
- apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.test.tsx
- apps/live-control-ui/src/localWorld/worldGraphCanvas/worldGraphCanvas.css
- apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.tsx
- apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.test.tsx
- apps/live-control-ui/src/nativeGraphDemo/nativeGraphPresentation.ts
- apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemoApi.ts
- apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemoApi.test.ts
- apps/live-control-ui/src/nativeGraphDemo/managedNativeGraphApi.test.ts
- apps/live_control_server/services/native_graph_explorer.py
- tests/test_native_graph_explorer.py

No changes to authentication, profiles, semantic classification, ingestion, migrations, dependencies, Core, publication or user data. Return to root for an explicit lease change if another file is necessary.

## Failure cases and verification

Test parallel/reverse/self-loop/invalid edges, input reorder, subset focus, isolated search/reveal, all-isolate snapshots, verified creation/recovery reveal, World/revision/draft interruptions, preserved pins and centers, unequal-radius anchors/loops/hit tests, circular spacing/capacity, and camera/selection stability. Test multiple recorded names and same names on distinct IDs, legacy/malformed optional metadata, exact and mixed classification terms, contrast, same-pin read-only backend behavior, payload/auth/binding guards.

Reuse matching installed dependencies for iteration; source/lock/toolchain fingerprints remain explicit. Honor /tmp/dungeonmind-frontend-verification-1000.lock for all frontend tests/builds. No competing run, denied network retry or automatic dependency remediation. Required final evidence is affected frontend/backend contracts, type/build, exact-source hosted verifier/validate, meaningful integrated full discovery with inherited failures retained, independent cumulative review, and scoped user browser acceptance. Ordinary source diagnostics do not replace required fresh-install receipts.

## Retention and release

Reuse this existing worktree and task root; no new checkout is needed. Keep immutable predecessor receipts and rollback artifacts. Do not change running services or user data during implementation. Publication, merge and release remain guarded by the user's instructions and current repository policy; no test pass invents browser acceptance. Settlement of this handoff waits for actual completion.
