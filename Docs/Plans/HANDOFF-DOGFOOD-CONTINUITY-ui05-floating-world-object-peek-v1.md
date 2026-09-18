# HANDOFF — DOGFOOD-CONTINUITY: UI-05 floating world-object Peek inspector

**Created:** 2026-09-18  
**Status:** ACTIVE — one serial implementation lane may be opened from this handoff  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui05-floating-world-object-peek-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY / UI language / Stage 4 WOW`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design authority base:** `main@fd9a42501c8616d27fa1436a7b66fc6a6dfe3347` — UI-04 / #733 merged  
**Activation gate:** `none — satisfied` (predecessor #733 merged; unauthorized #734 closed without merge on HOLD head `a9b43ed7`)  
**Dispatch base rule:** fresh current `main` containing this checked-in handoff; record the exact implementation branch base at dispatch/review  
**PR topology:** `serial`  
**PR authorization:** open/update exactly one implementation PR for this handoff only; no successor/repair PRs  
**PR title:** `DOGFOOD-CONTINUITY: float world-object Peek as an independent inspector`  
**Proposed branch:** `dogfood-continuity/ui05-floating-world-object-peek-v1`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). UI language: [`Docs/Design/ui-language/DESIGN-interaction-layer-language.md`](../Design/ui-language/DESIGN-interaction-layer-language.md). Predecessor dismiss contract: [`HANDOFF-DOGFOOD-CONTINUITY-ui03-responsive-secondary-context-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-ui03-responsive-secondary-context-v1.md).

---

## §1 Mission and merge-ready invariant

**Mission:** On Ingest, the opened world-object Peek becomes a viewport-bounded independent inspector so the GM can scroll a long campaign-memory card without losing the single close control, and without resurrecting duplicate AppChrome dismiss chrome.

**Merge-ready invariant:** **On Ingest, an open world-object Peek occupies a remaining-viewport Peek region that does not scroll with the recap. The only world-object dismiss is the inspector identity control, and it remains reachable on desktop and at the existing 900px CENTER XOR SECONDARY layout. Close returns to the same recap without remount. Tools/Projection Back chrome is unchanged. No AppChrome duplicate Close strip, no guessed `--app-chrome-*` overlay math, no extraction or relationship-rollup work.**

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes — one floating Peek inspector + one reachable identity dismiss. |
| Most likely adversarial sequence | Long Peek → scroll relationships → × gone → GM trapped; or narrow XOR loses Back and local × scrolls away. |
| Will §7 actually detect that failure? | Yes — focused layout/dismiss tests plus desktop + narrow browser witnesses. |
| Easiest owning boundary to under-test | Workspace overflow ownership vs sticky-inside-pane identity row. |
| What PR topology is authorized, and why is it safe? | `serial` — one open implementation PR; #734 closed; UI-04 merged. |
| Fact that forces stop/split | Required path outside §4; resurrecting AppChrome Close strip; sticky Peek with guessed chrome offsets; extraction/rollup scope. |

---

## §2 Context, authority, lane, and PR topology

| Field | Required content |
|---|---|
| Parent authority | UI language series; UI-03 persistent dismiss; UI-04 campaign-memory Peek |
| Design authority base | `main@fd9a42501c8616d27fa1436a7b66fc6a6dfe3347` |
| Activation gate | `none — satisfied` |
| Dispatch base rule | fresh current `main` containing this handoff |
| Predecessor contract | #733 / UI-04 merged; #734 closed without merge (HOLD `5250110858` on `a9b43ed7`) |
| Exact input consumed | Existing Peek claim/portal + campaign-memory GraphObjectCard |
| Named successor | Stage 4 human WOW re-witness after this chrome lands; parked Backlog IDEA items remain false |
| What remains false | DeepSeek extraction ablation; predicate-family relationship rollup; AppChrome Close resurrection |
| Explicit non-goals | Graph Review shell rewrite; semantic extraction; Tools/Projection IA redesign |
| PR topology | `serial` |
| Authorized PR action | open/update exactly this assigned PR without asking; no additional PRs |
| Open implementation PRs in workstream at dispatch | none (#734 closed) |
| Stack parent + merge/rebase order | not applicable |
| Branch / isolated checkout | `dogfood-continuity/ui05-floating-world-object-peek-v1` + isolated worktree |
| Parallel lanes / collision hotspots | none expected; central `styles.css` / Peek host are this lease |
| Runtime/state ownership | local Vite only; no shared `out/` / DB requirement |
| State-authority sync set after merge | this handoff status; `STEWARDS-ANCHOR-con-ready.md` (+ design-agent copy); UI-language series pointer |

### Why this slice exists

Post-#733 dogfood still saw duplicate close chrome. Unauthorized #734 removed the AppChrome `{label} Close` strip and the world-object Peek `← Back` bar, placing × on the graph-card identity row. That chrome singularity is desirable, but the panel remained page-flow static, so × scrolls away on long Peeks — exactly the UI-03 defect.

Operator direction: **the node viewer should float; it should not sit in document flow.**

“Float” means a real Peek layout region with its own scroll, not a new `position: fixed` overlay and not a draggable widget.

Evidence-only head for chrome singularity (do not merge #734): `a9b43ed7fb7af4d8f96fc87eee20b43d9cb23e7d`.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior (#733 main) | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Desktop Ingest world-object Peek | Static page-flow Peek + AppChrome Close strip | Viewport-bounded Peek pane; recap scrolls independently; one identity-row × sticky inside Peek | Yes | `styles.css` + GraphObjectCard |
| Long Peek scroll | Local × leaves viewport; AppChrome Close remains | Identity × remains reachable inside Peek overflow; no AppChrome Close | Yes | sticky identity header |
| Narrow 900px XOR | CENTER hidden; Peek nav sticky Back | Same XOR; world-object has no Back bar; identity × sticky at top of Peek pane | Yes | PeekRegion + CSS |
| Tools / Projection Peek | Back bar present | Unchanged Back bar | Yes | PeekRegionProvider |
| Close world-object | Returns to recap | Same mounted recap / prior reading position | Yes | AppChrome UI-03 restore |
| Loading/error before card | AppChrome Close available | Compact close on Peek pane until card exists | Yes | WorldGraphRecapProjection |

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| Open long object → scroll relationships | × still visible in Peek viewport | vitest + browser |
| Scroll recap while Peek open | Peek pane position/content does not ride recap scroll | browser |
| Narrow open → scroll → close | × reachable; close restores recap reading position | vitest + browser |
| Open Tools while world-object mounted | Tools wins; Back visible; world-object remounted when Tools dismisses | existing Peek arbitration tests |

---

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| MODIFY | `apps/live-control-ui/src/styles.css` | Remaining-viewport workspace; independent center/Peek overflow; no guessed chrome math |
| MODIFY | `apps/live-control-ui/src/planSurface/planSurface.css` | Sticky identity dismiss styling inside Peek overflow |
| MODIFY | `apps/live-control-ui/src/graphObjectCard/GraphObjectCard.tsx` | Optional `onDismiss` on identity row; sticky identity header when dismiss present |
| MODIFY | `apps/live-control-ui/src/graphObjectCard/GraphObjectCard.test.tsx` | Identity dismiss present |
| MODIFY | `apps/live-control-ui/src/graphObjectCard/GraphObjectProjectionCard.tsx` | Pass dismiss props |
| MODIFY | `apps/live-control-ui/src/graphObjectCard/GraphObjectProjectionCard.test.tsx` | Campaign-memory dismiss placement |
| MODIFY | `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.tsx` | Card dismiss + loading/error compact close; no empty World Object header |
| MODIFY | `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx` | Recap Peek dismiss witness |
| MODIFY | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.tsx` | Same dismiss composition for Graph Review historical recap Peek |
| MODIFY | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx` | Close affordance label update if needed |
| MODIFY | `apps/live-control-ui/src/surfaceInteraction/peekHost/PeekRegionProvider.tsx` | Suppress world-object `← Back` bar only; keep Tools/Projection |
| MODIFY | `apps/live-control-ui/src/surfaceInteraction/peekHost/PeekRegionProvider.test.tsx` | World-object has no Back; Tools still has Back |
| MODIFY | `apps/live-control-ui/src/chrome/AppChrome.tsx` | Remove ingest AppChrome `{label} Close` strip |
| MODIFY | `apps/live-control-ui/src/chrome/AppChrome.test.tsx` | Prove no secondary-context-dismiss; Peek dismiss path still works |
| CREATE | `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-ui05-floating-world-object-peek-v1.md` | Durable evidence / handback |
| MODIFY after merge (sync) | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui05-floating-world-object-peek-v1.md` | Status / review facts |
| MODIFY after merge (sync) | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Point frontier past UI-05 |
| MODIFY after merge (sync) | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` | Mirror |
| MODIFY after merge (sync) | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md` | Series pointer |

**Bounded discovery exception:** not applicable — paths above are sufficient.

---

## Steward lease expansion during Review Cycle 1

The implementation added one focused CSS falsification test outside the original §4 table:

| Action | Path | Purpose |
|---|---|---|
| MODIFY | `apps/live-control-ui/src/chrome/chromeBand.test.ts` | prove remaining-viewport CENTER/PEEK overflow, absence of guessed `100vh - ...` math, removal of legacy secondary dismiss chrome, and sticky world-object identity dismiss |

This is test-only authority. It does not expand the production lease beyond §4.

---

## §5 Explicitly out of scope / collision boundary

| Path / topic | Why |
|---|---|
| `src/graph_memory/extraction/**` | Parked DeepSeek ablation IDEA only |
| Predicate-family relationship rollup | Parked IDEA only |
| Restoring `app-secondary-context-dismiss` as the primary fix | Reintroduces duplicate chrome |
| Sticky whole Peek with `--app-chrome-top` / guessed `max-height` | UI-03 forbidden repair |
| Graph Review catalog rewrite / Play paint | Separate workstreams |
| Opening a second PR while this one is open | Serial topology |

---

## §6 Implementation contract

```text
Input:
  winning PeekClaim (world-object | tools | projection)
  campaign-memory GraphObjectProjectionCard content

Output:
  Ingest workspace with independent CENTER and PEEK scroll panes when Peek is populated
  singular world-object dismiss on sticky identity row (or compact loading/error close)

Invariant:
  same §1 invariant

Failure behavior:
  loading/error before card → compact close remains on Peek pane
  no card dismiss without onDismiss prop for non-Peek consumers

Replay / idempotency:
  open → scroll → close → reopen same object → same inspector grammar

Trust boundary:
  Verifies: layout/dismiss reachability only
  Does not claim: Stage 4 WOW PASS, extraction quality, relationship grouping
```

### Layout contract (required)

When Peek is populated on Ingest desktop:

```text
NAV stays in document flow (never covered)
CENTER overflow:auto   |   PEEK overflow:auto
recap scrolls here     |   node viewer scrolls here
                       |   identity + × sticky top:0 inside Peek
```

Height comes from remaining viewport via flex/`min-height: 0` composition under the existing header. **Do not** use `100vh - var(--app-chrome-top)`.

Narrow (`max-width: 900px`) keeps CENTER XOR SECONDARY. Identity × is sticky at `top: 0` inside the Peek pane.

Reusable from closed #734 evidence head (re-implement on this lease, do not reopen #734):

- no AppChrome secondary-context dismiss strip
- no world-object PeekRegion `← Back` bar
- GraphObjectCard optional `onDismiss` / `dismissLabel`

---

## §7 Required regressions / falsification

1. Desktop: open a long campaign-memory Peek; scroll the relationship list; identity × remains visible in the Peek viewport.
2. Desktop: scroll the recap column while Peek is open; Peek pane does not ride the recap scroll.
3. Narrow 900px: Peek replaces CENTER; no world-object `← Back`; identity × reachable; close restores prior recap reading position.
4. Tools Peek still shows `← Back`.
5. No `data-testid="secondary-context-dismiss"` on Ingest.
6. Close returns to the same mounted recap (UI-03 preserve).
7. Plan/default GraphObjectCard without `onDismiss` unchanged.
8. Vitest for AppChrome, PeekRegionProvider, WorldGraphRecapProjection, GraphObjectCard, GraphReviewWorkbenchModule.

Manual dogfood: Grobnok-class / long relationship Peek on C2 recap; confirm one dismiss treatment only.

---

## §8 Acceptance

Implementation may claim after deterministic tests + browser witnesses:

```text
UI-05 FLOATING WORLD-OBJECT PEEK = PASS
```

Does **not** establish:

```text
STAGE 4 / RECAP WOW = PASS
SEMANTIC COVERAGE = PASS
RELATIONSHIP ROLLUP = PASS
```

---

## §9 Worker dispatch

When dispatched, the implementation worker must:

1. start from current `main` containing this ACTIVE handoff;
2. open exactly one PR using the proposed branch/title;
3. implement remaining-viewport independent Peek scroll + sticky identity dismiss;
4. stop on any required production path outside §4;
5. leave Backlog IDEA extraction/rollup entries untouched as authorization.
