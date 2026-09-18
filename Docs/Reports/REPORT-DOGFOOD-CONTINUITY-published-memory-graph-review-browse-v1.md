# REPORT — DOGFOOD-CONTINUITY: published-memory Graph Review browse authority v1

**Status:** OPEN — implementation on authorized serial PR #732  
**Handoff:** [`HANDOFF-DOGFOOD-CONTINUITY-published-memory-graph-review-browse-v1.md`](../Plans/HANDOFF-DOGFOOD-CONTINUITY-published-memory-graph-review-browse-v1.md)  
**Implementation branch:** `dogfood/graph-review-recap-campaign-session`  
**Base:** `main@b7a300cedd47a738b06054ac75a20bbd97568a2c`  
**Spike evidence:** `dd4db027994f326af4434d2c0dd74f18abbb2509` (Review Cycle 1 HOLD)  
**Authorized PR:** [#732](https://github.com/Drakosfire/DungeonMindBuddy/pull/732)

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
| Mass-delete Load recap files | **kept deletions already on the spike** | Ordinary Load recap *is* the ceremony O2 forbids; leftover unused catalog/run modules were not hunted |

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
- `GraphReviewAuthorDraftWorkspace.test.tsx` (Author Node panel authority copy; Union-preview workspace suite skipped as retired)

All executed files: PASS.

---

## Not done here

- Human §8 dogfood witness (C2 latest useful session, mention/origin follow, C1 switch, refresh).
- New graph-writing workflow.
- Cleanup of remaining unused catalog/gold-compare internals inside the workbench module.
- Semantic gauntlet / Agent answerability.
