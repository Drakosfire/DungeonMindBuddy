---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: UI language design series / DOGFOOD-CONTINUITY
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui03-responsive-secondary-context-v1.md`
  - Suggested branch: `dogfood-continuity/ui03-responsive-secondary-context-v1`

  ## Verification pointer
  - Delivery: implemented on PR #702 by explicit product-owner direction
  - Design anchor: PR #702 code head `901efcf17635bddf48aa06c2e5a606bf3fad84df`
  - Implementation anchor: exact PR #702 head `9adb37eb1277ea2aa45249f9b784b9bf64ded552`
  - Verification: HANDOFF §7; exact-head desktop + 390×844 C2S25 browser witnesses required

  UI-03 is the responsive secondary-context successor discovered by post-#700 dogfood.
  It is not useful-open-Ask composition and it does not redesign Author Node/Tools inventory.
---

# HANDOFF — DOGFOOD-CONTINUITY: UI-03 responsive secondary-context navigation

**Created:** 2026-09-11  
**Status:** MERGED — PR #702 at `92a50db8bd41d632e54e5bbbd265738f546e0a5b`
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui03-responsive-secondary-context-v1.md`  
**Conversation/workstream:** UI language design series / C1-C2 demo-readiness  
**Flow / owner:** `DOGFOOD-CONTINUITY` / shared Peek + AppChrome responsive composition  
**Direction:** DESIGN → CODE → REVIEW  
**Design anchor:** PR #702 code head `901efcf17635bddf48aa06c2e5a606bf3fad84df` on PR #701 merge base `d515904c2bf4d196be70efc7419dc8485e991515`  
**Implementation base:** PR #702 exact head `9adb37eb1277ea2aa45249f9b784b9bf64ded552`, by explicit product-owner override of the former post-merge queue
**Implementation branch / PR:** `dogfood-continuity/ui02-agent-dock-artwork-v1` / #702
**Merged head / review:** `90a755429aba3673089a0d24325a5db7ece8c5c8`; 1 formal review cycle (HOLD; no approving disposition recorded before merge)

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). UI language: [`Docs/Design/ui-language/DESIGN-interaction-layer-language.md`](../Design/ui-language/DESIGN-interaction-layer-language.md). Shell ownership: [`Docs/Design/ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md).

---

## §0 Why this slice exists

Post-#700 operator dogfood on C2S25 accepted the desktop Peek grammar and rejected the narrow implementation assumption.

Accepted observations:

```text
DESKTOP
- Session 25 feels good.
- World object opens in a right secondary column without covering the recap.
- Tools may replace the World object in that same column.
- Recap remains present.
- Defect: the object's local × scrolls away with a long panel.

390×844
- CENTER then stacked PEEK does not work.
- Secondary context should replace the main work while narrow.
- Back / × returns to the recap.
- The parent recap must not be recreated just because presentation changes.
```

The same dogfood also found other real work that **does not belong in UI-03**: Session 23 historical source adoption, hover/glance quality, World status campaign mismatch, object Details/Advanced hierarchy, object-load latency, and rebuilding Author Node / contextual authoring. Those remain separately routed.

PR #701 made Agent presence cheap/truthful. PR #702 gives the collapsed Agent dock its supplied visual identity. UI-03 does not reopen either decision.

---

## §1 Mission and merge-ready invariant

**Mission:** Secondary context uses the same semantic claims and owner state at every viewport size, while AppChrome presents those claims appropriately for the available space: beside the current work on desktop, or temporarily in place of the current work on narrow screens.

**Merge-ready invariant:** **On Ingest, opening a World object, Tools, or an Ingest Projection never navigates away from or remounts the loaded historical recap. At desktop widths the exact recap remains visible beside one winning secondary context. At the existing narrow breakpoint, the winning secondary context becomes the main visible work instead of stacking below the recap; Back/Close dismisses only the winning claim through its existing semantic owner, and when no secondary claim remains the exact recap returns at its prior reading position. The active secondary context always has a reachable dismiss path without guessed chrome-height offsets or a new fixed overlay contract.**

One semantic stack, two presentations:

```text
WIDE
NAV / CONTEXT
CENTER                           SECONDARY
loaded recap                     winning claim
                                 World object | Tools | Projection

NARROW
NAV
CENTER
loaded recap
   ↓ open secondary context
SECONDARY MODE
winning claim
← Back / Close
   ↓ last claim closes
CENTER
same mounted recap, prior reading position
```

Existing claim priority remains presentation arbitration only:

```text
projection > tools > world-object
```

UI-03 must not reinterpret this as World authority, retrieval priority, or persistence.

### Critical ownership rule

The shared shell may know **which claim is winning**, its display label, and how to request dismissal. It must not take semantic ownership of the underlying state.

```text
World object close  → existing Ingest active-node owner clears selection
Tools close         → existing ToolHost closes itself
Projection close    → existing ProjectionHost / adapter closes projection

Peek/AppChrome      → presents active claim and calls owner-provided dismiss
                    → never directly edits those owners' domain state
```

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern desktop + narrow? | **Yes.** Semantic claims/priority/state are unchanged; only shell presentation changes by viewport. |
| Most likely adversarial sequence | C2S25 → scroll recap → Karsemine → Show all → Tools → Diagnostics → Close Diagnostics → Karsemine returns → Back/Close Karsemine → exact recap returns at saved reading position. |
| Most likely desktop failure | User scrolls a long secondary panel and the only dismiss control is back at the panel top. |
| Most likely narrow failure | CSS merely stacks SECONDARY after CENTER, or hiding CENTER destroys/loses the original reading position. |
| Easiest architecture mistake | Put responsive state into World/Tool/Projection owners instead of letting the shell present the already-existing claim state. |
| Fact that forces stop/split | Need to redesign Tools inventory/Author Node, move Agent Ask into Peek, change Surface Interaction publication schemas, add durable state, or create a new route/navigation model. |

---

## §2 Context, authority, and re-anchor requirements

### Truth at design time

```text
main                          d515904c2bf4d196be70efc7419dc8485e991515
#701                          MERGED — truthful Agent presence / compact dock
#702                          MERGED — Agent artwork + UI-03 responsive secondary context
#702 merge / head             92a50db8bd41d632e54e5bbbd265738f546e0a5b / 90a755429aba3673089a0d24325a5db7ece8c5c8
UI-01 / #700                  MERGED — Ingest shared Peek first consumer
UI-02 / #701                  MERGED — unavailable Agent absent, compact real dock
UI-03                         MERGED IN #702 — responsive secondary context
7A1                           DESIGN READY / QUEUED; remains false here
Stage 4                       NOT DONE
```

### Dispatch gate

Do **not** implement UI-03 from the design anchor SHA above.

After #702 merges:

1. fetch current `main`;
2. record the exact #702 merge commit and accepted head;
3. verify #702 remained artwork-only plus this successor handoff;
4. verify no parallel PR has changed Peek/AppChrome/ToolHost/ProjectionHost/Ingest Graph Review;
5. branch UI-03 from that exact merged state.

If #702 or another merged PR materially changes the Peek contract, responsive breakpoint, ToolHost/ProjectionHost presentation, or AppChrome header, stop and rebrief before implementation.

### Current predecessor shape

On the design anchor:

- `AppChrome` composes Ingest as `CENTER + PeekRegionSlot` only.
- `PeekRegionProvider` knows active claim kinds and winner priority, but not a claim label or owner-provided dismiss callback.
- `PeekClaim` portals the winning content into one shared slot while lower-priority active claims remain mounted and hidden.
- `GraphReviewHistoricalRecapProjection` owns World-object selection and the current local `×` callback.
- `ToolHost` owns open/close semantics and uses Peek only when the active publication is Ingest.
- `ProjectionHost` owns projection close semantics and uses Peek when its adapter selects `placement="peek"`.
- desktop CSS presents populated Peek as a second grid column.
- the existing `@media (max-width: 900px)` collapses that grid to one column, causing the rejected CENTER-then-PEEK stack.
- AppChrome header is sticky on desktop and static at the narrow breakpoint.

No server input or durable-state change is required.

---

## §3 Product / interaction decisions

### 3.1 Desktop remains CENTER + SECONDARY

Do not undo the part of #700 dogfood that worked.

Required:

- loaded recap remains visible;
- secondary context remains the right column;
- Tools / Projection may replace the visible World object according to current arbitration;
- lower-priority active context remains mounted;
- the user gains one **persistent/reachable** way to dismiss the winning secondary context while scrolled.

The existing local close buttons may remain. UI-03 adds the shell-level guarantee that the user is never forced to scroll back to a secondary panel's beginning just to leave it.

Preferred composition:

- the active Peek claim publishes a short label plus `onDismiss` callback into the existing transient Peek context;
- desktop AppChrome exposes a compact secondary-context Close control in existing cheap chrome that remains visible with the sticky header;
- do not make the whole Peek sticky again and do not resurrect guessed `top` / `max-height` viewport math.

If a different implementation gives a genuinely persistent dismiss path without a fixed overlay or guessed chrome heights, it is acceptable; record the reason in handback.

### 3.2 Narrow becomes CENTER XOR SECONDARY

At the existing narrow breakpoint (`max-width: 900px` on the predecessor), a populated secondary context must **not** appear underneath the recap.

Required visible rule:

```text
no winning claim      → CENTER visible, SECONDARY hidden/collapsed
winning claim exists  → CENTER visually replaced, SECONDARY visible as main work
```

Important: **visually replaced is not semantically unmounted.** The loaded recap component remains mounted so local state, loaded data, disclosure state, and source identity do not restart.

The implementation may use shell classes/data attributes plus CSS to switch presentation. It must not conditional-render a fresh recap instance on return.

### 3.3 Narrow Back / Close

Narrow secondary mode requires an obvious top-level return affordance such as:

```text
← Back to recap        World object
```

or equivalent compact wording.

Because the ordinary AppChrome header is static at the existing narrow breakpoint, the narrow secondary control itself may be sticky at `top: 0` **inside the narrow secondary view**. That does not require a guessed nav/header offset: the ordinary nav can scroll away, then the secondary Back control becomes the top control.

Do not solve this with another global fixed drawer or by guessing `--app-chrome-top`.

### 3.4 Claim metadata is transient presentation data

UI-03 may extend the shared Peek claim contract with transient presentation metadata, for example:

```ts
kind
active
label
onDismiss
```

The provider may expose the winning descriptor to AppChrome / the Peek slot.

Rules:

- the provider must not call `setActiveNodeId`, ToolHost state setters, or Projection state directly;
- `onDismiss` delegates to the current semantic owner;
- closing the winner lets normal registration/arbitration reveal any still-active lower-priority claim;
- no new durable/global domain store;
- route/surface unmount still cleans claims through React lifecycle.

### 3.5 Reading-position preservation on narrow

The parent recap's **reading position is part of the return contract**.

On the first narrow transition from no secondary claim → any secondary claim:

- capture the current parent reading position;
- do not overwrite that snapshot as winner priority changes among World object / Tools / Projection.

While secondary mode remains active:

- winner changes stay in secondary mode;
- closing Projection back to an underlying World object does **not** restore CENTER yet.

When the final claim closes:

- CENTER becomes visible again;
- restore the captured recap reading position after layout settles.

This state is ephemeral shell/UI state only. Do not persist it to APP-STATE.

If the implementation can preserve the exact reading position without explicit `window.scrollY` bookkeeping, that is acceptable, but §7 must prove it.

### 3.6 Tools launcher is not redesigned here

The dogfood note that toolbars have no obvious narrow-screen home is valid, but the same operator pass also concluded the current Ingest Tools/Author Node concept needs a product redesign:

```text
highlight → create a node
highlight → run an Agent workflow
```

UI-03 therefore owns **what happens once an existing Tool secondary context is opened**, not the future Author Node / contextual-action product.

Do not revive or elaborate the old generic drawer to solve this handoff.

If the current ToolHost launcher becomes literally unusable under UI-03, stop and report a narrow launcher collision. Do not silently invent a new toolbar/navigation contract.

---

## §4 Files in scope — write lease

Expected implementation paths:

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/surfaceInteraction/peekHost/PeekRegionProvider.tsx` | expose winning transient presentation descriptor; preserve arbitration/mounted-state behavior; owner-provided dismiss |
| Modify | `apps/live-control-ui/src/surfaceInteraction/peekHost/PeekRegionProvider.test.tsx` | prove priority, label/dismiss delegation, lower-claim mounted state, winner fallback |
| Modify if exports change | `apps/live-control-ui/src/surfaceInteraction/peekHost/index.ts` | export bounded active-claim/shell presentation API |
| Modify | `apps/live-control-ui/src/chrome/AppChrome.tsx` | present desktop persistent Close; mark narrow CENTER-vs-SECONDARY mode; coordinate return-position lifecycle |
| Modify | `apps/live-control-ui/src/chrome/AppChrome.test.tsx` | prove nav remains outside work region, active secondary shell state, owner dismissal plumbing, CENTER remains mounted |
| Create or modify if a focused helper is warranted | `apps/live-control-ui/src/chrome/responsiveSecondaryContext.ts` / `.test.ts` | narrow breakpoint/reading-position bookkeeping only; no domain state |
| Modify | `apps/live-control-ui/src/styles.css` | retain desktop two-column Peek; replace narrow stacked rule with CENTER XOR SECONDARY; style narrow sticky Back without guessed chrome offset |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.tsx` | give World-object Peek claim label + existing close callback; do not redesign card contents |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx` | C2S25 owner-path regression including retained object state and no refetch |
| Modify | `apps/live-control-ui/src/surfaceInteraction/toolHost/ToolHost.tsx` | give Ingest Tools claim label + existing dismiss callback only |
| Modify | `apps/live-control-ui/src/surfaceInteraction/toolHost/ToolHost.test.tsx` | prove Ingest claim delegates close; non-Ingest legacy behavior unchanged |
| Modify | `apps/live-control-ui/src/surfaceInteraction/projection/ProjectionHost.tsx` | give Peek Projection label + existing `onClose` callback only |
| Modify | `apps/live-control-ui/src/surfaceInteraction/projection/ProjectionHost.test.tsx` | prove Peek dismiss delegates `onClose`; legacy placement unchanged |
| Modify after implementation | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui03-responsive-secondary-context-v1.md` | exact base/head, evidence, review handback |
| Modify after implementation | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md` | backward-looking #701/#702 predecessor truth + UI-03 active |
| Modify after implementation | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | current slice only; Stage 4 remains not done |
| Modify after implementation | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | current forcing function only |

### Bounded discovery exception

```text
Directories:
  apps/live-control-ui/src/chrome/
  apps/live-control-ui/src/surfaceInteraction/peekHost/
Maximum additional production paths:
  2
Allowed purpose:
  a focused responsive-shell helper or presentation component only
Decision rule:
  only if extracting AppChrome/Peek responsive bookkeeping materially keeps
  semantic ownership clearer than adding it inline
```

A required change to server code, APP-STATE, World, Surface Interaction publication types, Agent provider/storage, Plan Agent request code, or graph retrieval is a stop report.

---

## §5 Explicitly out of scope / successor ledger

| Concern | Disposition |
|---|---|
| PR #702 Agent artwork / 80×80 collapsed control | predecessor; leave unchanged |
| Useful open-Ask composition (Ask as Peek/center mode) | later Agent UI slice; **not UI-03** |
| 7A1 contextual Ask on loaded Ingest recap | queued; do not dispatch here |
| Rebuild Author Node / contextual authoring | separate product slice: selection/highlight → create node or Agent workflow |
| Move/redesign global Tools launcher | separate unless UI-03 causes a literal usability regression; stop rather than absorb |
| Hover/glance information + styling | separate successor |
| Combine object Details + Advanced | separate object-presentation successor |
| Complete-object latency | performance/retrieval successor |
| Session 23 APP-STATE historical source adoption | existing source-adoption lane |
| World graph corner-chip campaign mismatch | existing generic-lens/status lane |
| Play parchment/current-moment paint | later UI series |
| Combat integration | separate Play capability |
| Load/Unload lock semantics | separate capability |

Do not rename useful-open-Ask work as UI-03. **UI-03 is responsive secondary-context navigation.**

---

## §6 Implementation contract

### Input

```text
Existing Peek claim lifecycle:
  world-object | tools | projection

Existing winner priority:
  projection > tools > world-object

New transient claim presentation metadata:
  short label
  owner-provided dismiss callback

Existing breakpoint:
  max-width: 900px
```

### Output

```text
WIDE + no claim
  CENTER only

WIDE + winning claim
  CENTER | SECONDARY
  persistent/reachable dismiss path
  parent remains visible/mounted

NARROW + no claim
  CENTER only

NARROW + winning claim
  SECONDARY is the main visible work
  CENTER remains mounted but is not simultaneously presented below/above it
  Back/Close delegates to winner owner

NARROW + winner changes
  remain in SECONDARY mode
  do not overwrite saved CENTER reading position

NARROW + final claim closes
  CENTER becomes visible
  restore original reading position
```

### Failure behavior

```text
claim owner unmounts
→ registration cleanup removes claim
→ winner recomputes normally

winner dismiss callback changes owner state
→ provider waits for normal owner rerender/unregister
→ provider does not force-remove semantic state

higher-priority claim closes while lower claim remains
→ lower claim becomes winner
→ remain in secondary mode

last claim closes
→ secondary mode exits
→ narrow CENTER return contract fires once
```

### Trust boundary

Peek/AppChrome may trust claim registration as “this secondary context currently exists.” It must not independently infer whether a World object, tool, or projection should exist from URLs, campaign query params, or domain payloads.

---

## §7 Evidence required to merge

### Focused automated evidence

At minimum, from `apps/live-control-ui`:

```bash
npx vitest run \
  src/surfaceInteraction/peekHost/PeekRegionProvider.test.tsx \
  src/chrome/AppChrome.test.tsx \
  src/surfaceInteraction/toolHost/ToolHost.test.tsx \
  src/surfaceInteraction/projection/ProjectionHost.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx \
  --testTimeout 15000

npm run build
```

If a new focused responsive helper/test exists, include it explicitly in the command.

Repository root:

```bash
git diff --check
git diff --name-only <exact-#702-merge-base>...HEAD
```

### Required guarantees

| Guarantee | Evidence |
|---|---|
| winner descriptor includes label + owner dismiss without taking domain ownership | Peek provider tests |
| lower-priority active claim stays mounted across winner changes | Peek provider existing + strengthened regression |
| desktop CENTER remains mounted/visible with populated SECONDARY | AppChrome + browser |
| desktop has a dismiss action reachable after scrolling long secondary content | exact-head browser |
| narrow populated SECONDARY does not stack after CENTER | CSS structural proof + exact-head 390×844 browser |
| narrow CENTER component is not remounted | integration instrumentation / stable sentinel state |
| narrow final Back/Close returns to the prior recap reading position | focused scroll restoration test + browser |
| narrow Projection → underlying World object stays in secondary mode | C2S25 adversarial integration/browser |
| complete World object does not refetch merely because responsive presentation/winner changes | C2S25 request-count assertion |
| ToolHost non-Ingest presentation remains current legacy behavior | ToolHost regression |
| ProjectionHost non-Peek placement remains current legacy behavior | ProjectionHost regression |
| #702 Agent artwork/behavior unchanged | diff inspection + smoke |
| 7A1/open Ask/Author Node redesign remain false | diff inspection |

### Exact-head browser witness A — desktop

Use the exact implementation head and canonical C2S25 runtime authorities.

Open:

```text
/ingest?campaign=longmont-c2&session=session-25
```

Walk:

1. load Session 25;
2. scroll recap to a recognizable non-top position;
3. open Karsemine;
4. confirm recap remains visible beside the World object;
5. expand enough object content to create a long secondary panel (`Show all` where applicable);
6. scroll far enough that the object's original local header/× would ordinarily be off-screen;
7. confirm a shell-level Close/Back path remains reachable without returning to the object's beginning;
8. open Tools if a real current tool inventory is present;
9. launch Diagnostics;
10. close Diagnostics;
11. confirm Karsemine returns without a new complete-object request;
12. dismiss Karsemine;
13. recap remains the loaded Session 25 parent.

Do not manufacture a fake Tool inventory in product code merely to complete step 8. If current canonical C2S25 has no useful Tools inventory, record that fact and prove Tools/Projection ownership with focused tests plus any real available projection path.

### Exact-head browser witness B — narrow `390×844`

Open the same C2S25 state.

Required observations:

1. recap initially occupies the work area;
2. scroll to a recognizable position in the recap;
3. open Karsemine;
4. **recap is not stacked above Karsemine and Karsemine is not stacked below it**;
5. World object is the main visible work;
6. obvious Back/Close control is reachable while the object is long/scrolled;
7. Back/Close returns to the recap;
8. recap returns to the prior recognizable reading position rather than the top;
9. no horizontal overflow;
10. Nav remains usable before entering secondary mode;
11. #702 Agent artwork does not overlap Ingest because Ask remains unavailable there.

If Tools/Diagnostics are available in this state, additionally walk:

```text
Karsemine → Tools → Diagnostics → Close Diagnostics → Karsemine → Back → recap
```

Required: CENTER does not flash/reappear between secondary winners, and only the final close returns to the recap.

### Runtime/state authority

Follow the current canonical dogfood runtime at dispatch time. Re-anchor ports/authority from the then-current handoff if they have changed. Do not start a disposable World authority or write to canonical World/APP-STATE as part of UI-03 verification.

---

## §8 Required review handback

### Implementation handback

The product owner explicitly directed UI-03 to be implemented on the still-open PR #702. That instruction superseded the original “after #702 merge” sequencing assumption without changing the UI-03 capability boundary. Implementation began from exact #702 head `9adb37eb1277ea2aa45249f9b784b9bf64ded552`.

- Shared Peek claims now publish a presentation label and owner-provided dismiss callback while retaining `projection > tools > world-object` arbitration and mounted lower-priority claims.
- Desktop keeps CENTER + SECONDARY and exposes the winning context's Close action in the existing sticky AppChrome header. No new guessed chrome offset or viewport overlay contract was introduced.
- At the existing narrow breakpoint, CSS presents CENTER XOR SECONDARY while leaving CENTER mounted. The secondary-local Back control is sticky at `top: 0` inside normal flow.
- AppChrome records the actual scrolled descendant inside CENTER before secondary mode and restores that element on final close. This was strengthened after browser dogfood showed that the historical recap scrolls inside `.recap-reader-document`, not the window.
- World object, ToolHost, and ProjectionHost remain the semantic owners of close behavior. Winner changes do not return to CENTER until the last active claim closes.
- Focused evidence from `apps/live-control-ui`: 5 files / 68 tests passed with the exact §7 Vitest command; `npm run build` passed. The inherited Vite large-chunk warning remains, including the 1.44 MB Agent artwork asset.
- Desktop browser witness: the recap and populated secondary context remained side-by-side; the AppChrome Close remained reachable after scrolling a long World object; Tools → Diagnostics → close restored the still-mounted World object; final Close restored the recap.
- `390×844` browser witness: the recap remained mounted but hidden; Karsemine → Tools → Diagnostics → Karsemine stayed in secondary mode; final Back restored the recap's internal reader position; Agent chrome was absent and no horizontal overflow appeared.
- Successor ledger remains false: open Ask composition, 7A1, Author Node redesign, hover redesign, object IA cleanup, source adoption, generic-lens repair, and Combat were not absorbed.

Record:

1. Review Cycle number and exact PR/head;
2. exact #702 merge base used for implementation;
3. §1 invariant disposition;
4. desktop CENTER + SECONDARY behavior;
5. exact persistent desktop dismiss mechanism and why it avoids guessed chrome offsets;
6. narrow CENTER XOR SECONDARY mechanism;
7. narrow reading-position preservation mechanism;
8. winner-change behavior across World object / Tools / Projection;
9. owner-dismiss delegation proof;
10. complete-object request-count / remount evidence;
11. desktop browser observations;
12. `390×844` browser observations;
13. actual changed paths vs §4;
14. test/build provenance;
15. successor ledger: open Ask composition false, 7A1 false, Author Node redesign false, hover false, object IA false;
16. prior review findings on re-review.

---

## §9 Acceptance rubric

- [x] Implementation used exact PR #702 head `9adb37eb…` by explicit product-owner override of the former post-merge requirement.
- [x] Desktop preserves the accepted #700 CENTER + right SECONDARY grammar.
- [x] Desktop winning secondary context has a dismiss path reachable after scrolling long content.
- [x] No new guessed `top`, `bottom`, viewport-height, or z-index arbitration contract is introduced to solve Peek dismissal.
- [x] Narrow secondary context replaces CENTER rather than stacking with it.
- [x] Narrow CENTER remains mounted while secondary mode is active.
- [x] Narrow final close returns the exact loaded recap at its prior reading position.
- [x] Winner changes among World object / Tools / Projection do not prematurely restore CENTER.
- [x] Peek provider delegates dismissal to semantic owners rather than mutating owner state.
- [x] Existing priority remains `projection > tools > world-object`.
- [x] Lower-priority active context remains mounted while hidden.
- [x] C2S25 complete-object data does not refetch because of responsive presentation changes.
- [x] Non-Ingest ToolHost / Projection behavior remains unchanged.
- [x] PR #702 Agent artwork/interaction remains unchanged.
- [x] No Ask-on-Ingest, open-Ask Peek migration, Author Node redesign, hover redesign, object IA redesign, source-adoption repair, generic-lens repair, or Combat work is absorbed.
- [x] Stage 4 remains NOT DONE unless a separate human STOP later says otherwise.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- #702 merges with material shell/Peek changes not represented here;
- preserving recap reading position requires durable APP-STATE changes;
- worker begins routing secondary context through URLs/navigation instead of current owner state;
- worker needs a new Surface Interaction publication/domain schema merely for responsive presentation;
- worker moves Agent Ask into Peek/secondary mode;
- worker redesigns Tools inventory / Author Node to make the responsive witness possible;
- worker adds another fixed viewport drawer or guessed chrome-height contract;
- UI-03 cannot keep the recap mounted on narrow without a larger AppChrome architecture rewrite;
- a required production path falls outside §4/bounded discovery;
- head introduces a build/test failure not present on the exact #702 merge base.

Report:

```text
Stop condition:
Invariant clause affected:
Why UI-03 cannot absorb it:
Required evidence now missing:
Affected paths / ownership layers:
Recommended rebrief / successor:
State-authority update needed:
```
