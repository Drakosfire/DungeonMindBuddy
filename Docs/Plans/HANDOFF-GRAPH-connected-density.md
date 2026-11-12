# GRAPH: reveal loaded graph connections

Status: ACTIVE. Alan requested relationship-weighted bubbles, a connected-only default, truthful NPC/PC/item/event colors, recorded names instead of a hiding “Multiple” label, and circular presentation after the first experiment shipped. Root explicitly assigned bounded design and implementation authority, including necessary read-adapter/API files, on 2026-11-12. Implement one serial loaded-graph presentation PR; no 3D, identity correction, inferred roles/edges, data repair or live writes.

## Predecessor, source and ownership

The first full-bubble experiment merged as #2464 at 77175b77212b35b2c2d0a0507a4ef314dea23b22 and its exact tree was deployed to the local frontend after explicit positive user pan feedback. Fresh hosted qualification and independent review passed; inherited full-discovery failures and browser/performance limits remain recorded, not relabeled green.

Re-anchored current remote main 2ea388f9bf3075f0c646333b358904f8138bce11 after visual feedback, including the disjoint PDF source-gold update. Relevant open PR heads are unchanged from the 56-file-set check. That exact commit is already present locally; no denied network action was retried. Current AGENTS is unchanged. Reuse the clean existing worktree at /home/drakosfire/Projects/.codex/full-bubble-graph-20261111/worktrees/DungeonMindBuddy on codex/graph-connected-density-20261112. Task scratch/evidence stays under its existing Projects task root. Do not modify the running first-release artifacts.

All 56 current open PR file sets were rechecked. Only historical #2326 at unchanged b30833ede97cb4c79acf17a1fe55ff50446c7452 overlaps canvas paths already reconciled by the shipped graph predecessors. No dirty overlapping path was found in 84 readable registered worktrees. The older native demo and hosted-owner handoffs refer to merged predecessors #2330 (36fce5feb) and #2374 (1b5e87418), both ancestors of current main. Root's explicit successor assignment grants the narrow presentation/read-adapter lease below; existing owner/auth/publication contracts are retained unchanged. No active code owner or open PR overlaps the new read-adapter paths.

Implementation resumes after Alan's explicit instruction to continue bubble graph work. The graph-health investigation found the recent C1 evaluation dataset separate from the live graph; this presentation slice does not label legacy gaps as current ingestion regressions.

## Invariant and design

- Count distinct valid incident relationship IDs across the full loaded snapshot before focus, search or visibility filters. Count a self-loop once for its object; parallel/reverse distinct IDs each count. Missing-endpoint edges do not contribute.
- Native embedded overview hides objects with zero listed connections by default. Keep a reveal toggle/count, every ID in search/export/connection choices, and saved positions. Search focus and exact-receipt newly created nodes remain accessible, including recovery replay. Filtering is not truncation or deletion; retain partial-read warnings.
- Full-bubble size reflects full loaded incident degree with a stronger bounded visual hierarchy. A shared radius calculation drives layout, bubbles, edge anchors, loops, ports, hit tests, focus and Fit. Preserve stored-position meaning with a fixed 56-unit center offset even when radius exceeds that offset. Do not size by focused degree.
- After feedback that the ring overview was crowded and unparseable, unpinned bubbles should pack around larger real connected hubs with radius-aware collision separation and bounded settling. Saved/manual pins remain fixed; unpinned positions may adapt to changed topology, radius or an intentionally moved pin. Pan, zoom, selection and visibility filters must not trigger rearrangement; unchanged layout inputs stay stable across revision refresh. Keep all IDs finite in the existing coordinate domain, handle crowded pins and large datasets honestly, and avoid continuous jitter or unbounded simulation. Neighborhood structure uses only real edges, not inferred identities or semantic distance.
- Quiet overview edges and progressively emphasize selected/focused relationships, preserving all underlying strokes/identities and explicit counts. Keep important hubs readable while zoomed out; offer an accessible all-relationships view. No data is removed. Respect reduced motion for any short settling transition.
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
- apps/live-control-ui/src/App.guestEntry.test.tsx (narrow explicit isolate-reveal integration actions; retain auth/World/account/draft/stale-response assertions)
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

## Scoped visual feedback

Alan said the zoomed-out first density preview looked good and asked whether sizes reflected connections. That is not blanket acceptance. He then requested that bubbles move and adapt around the biggest bubble and called the 26% overview at 942×932 crowded and unparseable. He further asked for much bigger, closer bubbles like other bubble charts. The next checkpoint uses area proportional to loaded incident degree (capped at 40), tight radius-aware spacing, responsive packing and edge clutter reduction; preserve the prior preview/evidence separately. Alan subsequently approved this preview and shipping; draft PR #2475 was created. Release qualification and runtime verification remain separate gates.

## Qualification follow-up

The exact packed candidate hosted contract passed. Full discovery remains red and is not waived. Eleven App guest integration tests still selected the intentionally hidden sole isolated fixture object; root authorized a narrow test-action update to explicitly reveal it while preserving all original security, switching, draft, inspection and stale-response assertions. The 58 current PR file sets were checked: only unchanged historical #2262/#2313/#2326 overlap this test, their branches remain untouched, and no dirty overlap was found among 85 registered worktrees. This successor lease is bounded to the test actions, not App routing or auth behavior.

Independent review approved three explicit projection coverage substitutions for the user-requested adaptive layout: disconnected objects still retain identities/real edges and separate placement; fixed saved pins plus radius-aware separation replace freezing unpinned positions across additions; unchanged geometry inputs remain stable while topology/radius changes intentionally recompute unpinned packing. Original removed occurrence names stay recorded in the retained comparison evidence. No test disappears silently and the failing full-discovery receipt is not rewritten.


## Main re-anchor after qualification guard

On 2026-11-12 the final user verifier stopped before allocation/install because
main advanced. The user's fetch supplied main
`6b50ae999f6f963cde680c57f4541d7820153204`; this lane integrates that exact
commit without changing graph product code or approved preview behavior. The
seven intervening PDF/OCR commits touch 24 paths, including frontend tests, so
the earlier discovered baseline is not relabeled current or reused as an
unchanged full-suite comparison. Manifest, lockfile, verifier, CI contract and
AGENTS.md inputs are unchanged.

A fresh GitHub read also observes `d9d4985e52c4c280a55f887ebfab43b4c9cad964`
with generated `_pytest` workspace cleanup. That commit was not fetched into
this executor; connector reads were used only to inspect the change, not to
reconstruct Git objects or bypass the denied direct network operation. No graph
file overlaps occur in the fetched main integration. Current open PR heads and
new/changed file sets were checked; historical overlapping graph PR heads are
unchanged, and no dirty overlap was found among 90 registered worktrees.

Alan explicitly approved the packed preview and shipping. PR #2475 exists;
its source is published. Fresh qualification of this integrated candidate and
independent review remain required. The earlier test-only repair and its red
receipts are retained. Stable preview remains at 5248 with its approved product
artifact; no runtime, authentication, or World data is changed by this re-anchor.

### Completed fetch follow-up

Alan's subsequent authorized fetch supplied
`78c46c64b246b229f4efe8b1726dc171ee26a94b`. Integrate it without graph
product edits. This includes the previously unavailable cleanup commits and
#2492's newline-free Hugging Face reference fix. Frontend source, dependency
manifests, verifier, CI contracts and AGENTS are unchanged from the tested
6b50 integration. Its installed-dependency diagnostic passed 247 tests and a
production build; that is not fresh-install qualification. Prior running UI
and prepared backend overlay use pinned launchers, not the new main `./run`;
no live launcher or GPU inference was exercised here. Final qualification
must use the updated baseline rather than declaring the earlier PDF-changing
baseline equivalent.
