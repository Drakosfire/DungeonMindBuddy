# REPORT — DOGFOOD-CONTINUITY: published-memory Graph Review browse authority v1

**Status:** OPEN — implementation on authorized serial PR #732  
**Handoff:** [`HANDOFF-DOGFOOD-CONTINUITY-published-memory-graph-review-browse-v1.md`](../Plans/HANDOFF-DOGFOOD-CONTINUITY-published-memory-graph-review-browse-v1.md)  
**Implementation branch:** `dogfood/graph-review-recap-campaign-session`  
**Base:** `main@b7a300cedd47a738b06054ac75a20bbd97568a2c`  
**Spike evidence:** `dd4db027994f326af4434d2c0dd74f18abbb2509` (Review Cycle 1 HOLD)  
**Authorized PR:** [#732](https://github.com/Drakosfire/DungeonMindBuddy/pull/732)

**Review Cycle 2 HOLD:** `00fc66a9b7ea8180c1f12f0fa701fb68c631a5b9` review `5243098493`  
**Review Cycle 3 HOLD:** `0d3b132992330605d6d9d35122568e51e5f427d0` review `5243376461`

```text
PUBLISHED-MEMORY GRAPH REVIEW BROWSE AUTHORITY = PASS
GRAPH REVIEW BROWSE/WRITE AUTHORITY SEPARATION = PASS
OPERATOR DOGFOOD                               = NOT_MEASURED
SEMANTIC COVERAGE                              = not measured
AGENT ANSWERABILITY                            = not measured
```

`OPERATOR DOGFOOD` stays `NOT_MEASURED` until the post-implementation human witness in handoff §8. Deterministic tests cover browse mount, catalog independence, mention complete-object, ingest campaign scope, world-union verification, and write-authority isolation.

---

## Spike disposition (`#732` / `dd4db027`)

| Spike idea | Verdict | Why |
|---|---|---|
| Catalog recap = `RecapGraphModule` (same published-memory reader as Plan Recap) | **kept** | Matches O1/O2 and the successful dogfood path |
| Campaign + Focus session pickers always visible; no ordinary Load recap ceremony | **kept** | Product requirement; restoring Load recap would reintroduce the failed workflow |
| Mention click → `useCompleteWorldObject` + PeekClaim | **kept** | Invariant D / O3; recap stubs have empty summaries |
| Ingest bare `?campaign=` is that campaign, not C1+C2 union | **kept** | Invariant C / O4 ingest half |
| World-scope verifier may omit campaign identity; campaign-scope stays strict | **kept** | O4; added campaign-empty fail-closed coverage |
| Drop vanished-run banner instead of blocking recap | **kept as symptom** | Browse must ignore leftover `run=` |
| `appliedSelection` / catalog restore as implicit `liveRun` | **discarded** | Review Cycle 1 HOLD #1: visible recap was treated as authorable catalog state |
| Gate Recap on `catalogEverSettled` | **discarded** | Review Cycle 1 HOLD #2 / Invariant B |
| Empty Author Node copy “open after a published recap is on screen” | **redesigned** | That copy implied recap visibility is write authority |
| Mass-delete Load recap files | **restored after Cycle 2 HOLD** | Handoff forbade cleanup deletions; files are back on the tree and unused by ordinary browse |

---

## Authority model implemented

```text
PublishedMemoryBrowseContext  !=  GraphReviewWriteAuthority
```

- Browse: URL/product `campaign` + `session`. Source is published World Graph recap. No ExtractionRun required.
- Write: exact-run handoff only in this slice (`kind: "exact_run"`). `explicit_authoring` exists in the type union and is never inferred from browse or persisted catalog runs.
- Ordinary `/ingest?campaign=&session=` mounts recap while the catalog is still loading.
- Invalid exact-run identity fails closed: exact-run error, no recap degrade, no Author Node.

Author Node in browse-only mode stays openable and states: **Authoring requires an explicit source/run context.** Prepare/confirm/write APIs are not invoked.

Ordinary browse no longer renders ExtractionRun catalog empty/error chrome. Catalog observation still exists for diagnostics/exact-run, but it is not part of `Campaign → Focus session → recap → objects`.

---

## Review Cycle 3 repairs

Formal HOLD `5243376461` on `0d3b132992330605d6d9d35122568e51e5f427d0`.

Reverted to `origin/main` (no behavioral need in this slice):

- `apps/live-control-ui/src/ingestSurface/useIngestRunCatalogInformation.ts` (comment-only)
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewAppliedSelection.ts` + test
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthorNodeDrawer.tsx`

`GraphReviewAuthorNodePanel` (leased) still accepts unused optional `onRequestLoad` so the restored Drawer API type-checks. Host does not pass it; ordinary browse still has no Load recap ceremony. Write isolation remains `liveRun={null}` on ordinary browse, not a persisted-selection change.

Cycle 3 HOLD named these adjacent files as required if retained. They stay in the PR; this report records the lease expansion (worker cannot edit the `main` HANDOFF):

- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewAuthority.ts` + `graphReviewAuthority.test.ts` — `PublishedMemoryBrowseContext != GraphReviewWriteAuthority`
- `apps/live-control-ui/src/App.test.tsx` — `/ingest` Campaign/Focus session and no catalog empty chrome

Restored `GraphReviewAuthorDraftWorkspace.test.tsx` without `describe.skip`. Workspace tests inject a write-ready projection fixture; Panel tests leave UnionSupergraph retired so a catalog `liveRun` does not open the workspace.

---

## Review Cycle 2 repairs

1. Restored from `origin/main` without re-wiring into ordinary browse:
   - `GraphReviewLanePicker.tsx`
   - `GraphReviewLoadBar.tsx` + test
   - `GraphReviewLoadLaneSummary.tsx`
   - `GraphReviewLoadSurface.tsx` + test
2. Removed workbench catalog empty/error copy from the published-memory surface.
   Stabilized empty/unavailable catalog snapshots so browse does not re-render-loop.
3. Adjacent test update outside the original §6 table: `apps/live-control-ui/src/App.test.tsx` — `/ingest` now asserts Campaign/Focus session and the absence of catalog empty chrome. Required to stop locking in the leak.

---

## Verification

Focused vitest (live-control-ui):

- `graphReviewAuthority.test.ts`
- `GraphReviewWorkbenchModule.test.tsx`
- `GraphReviewGenericRun.test.tsx`
- `RecapGraphModule.test.tsx`
- `sessionCampaignContext.test.ts`
- `useWorldGraphLensProjection.test.tsx`
- `verifyWorldGraphProjectionResponse.test.ts`
- `graphReviewAppliedSelection.test.ts`
- `GraphReviewAuthorDraftWorkspace.test.tsx` (workspace suite restored with write-ready fixture; Panel authority copy)
- `GraphReviewLoadSurface.test.tsx` / `GraphReviewLoadBar.test.tsx` (restored modules)
- `App.test.tsx` ingest route (catalog chrome must not appear)

All executed files: PASS.

---

## Not done here

- Human §8 dogfood witness (C2 latest useful session, mention/origin follow, C1 switch, refresh).
- New graph-writing workflow.
- Cleanup of remaining unused catalog/gold-compare internals inside the workbench module.
- Semantic gauntlet / Agent answerability.
