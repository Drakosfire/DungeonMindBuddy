# REPORT — UI-05 floating world-object Peek inspector

**Status:** IMPLEMENTATION ACCEPTED / MERGED — post-merge human Stage 4 witness remains  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui05-floating-world-object-peek-v1.md`  
**Predecessor:** UI-04 / #733 merged at `fd9a42501c8616d27fa1436a7b66fc6a6dfe3347`  
**Closed without merge:** #734 HOLD head `a9b43ed7` (chrome singularity evidence only)  
**Date:** 2026-09-18

## Mission claimed

```text
UI-05 FLOATING WORLD-OBJECT PEEK = PASS (deterministic tests)
```

On Ingest, an open world-object Peek occupies a remaining-viewport Peek region that does not scroll with the recap. The only world-object dismiss is the inspector identity control (sticky inside Peek overflow). Tools/Projection keep `← Back`. No AppChrome `{label} Close` strip. No guessed `100vh - var(--app-chrome-*)` layout math.

## What changed

1. **Chrome singularity (from #734 evidence, re-implemented on this lease)**
   - Removed ingest `app-secondary-context-dismiss` from `AppChrome`.
   - Suppressed PeekRegion `← Back` for `world-object` only.
   - Optional `onDismiss` on `GraphObjectCard` identity row; loading/error keep a compact pane close until the card exists.

2. **Floating inspector layout**
   - `.app-shell` / `.app-shell-layout` / populated `.app-wrap` fill remaining viewport via flex + `min-height: 0`.
   - When Peek is populated, `.app-chrome-center` and `.app-peek-region` independently `overflow: auto`.
   - Identity header with dismiss uses `position: sticky; top: 0` inside the Peek scrollport (`graph-object-card__identity-header--sticky`).

## Deterministic evidence

Run from `apps/live-control-ui`:

```bash
./node_modules/.bin/vitest run \
  src/chrome/AppChrome.test.tsx \
  src/chrome/chromeBand.test.ts \
  src/surfaceInteraction/peekHost/PeekRegionProvider.test.tsx \
  src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx \
  src/graphObjectCard/GraphObjectCard.test.tsx \
  src/graphObjectCard/GraphObjectProjectionCard.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx
```

Result: **7 files / 69 tests passed** (2026-09-18).

## Browser layout witness

Served the Ingest shell class tree with real `styles.css` + `planSurface.css` under Vite `:5175` and measured computed layout after scrolling:

```json
{
  "centerOverflow": "auto",
  "peekOverflow": "auto",
  "stickyPosition": "sticky",
  "secondaryDismissPresent": false,
  "backPresent": false,
  "dismissVisibleInPeek": true,
  "centerScrollTop": 500,
  "peekScrollTopAfterCenterScroll": 800
}
```

Independent CENTER/PEEK scroll confirmed: after scrolling the Peek pane, scrolling the recap column left Peek scrollTop unchanged while × remained inside the Peek viewport.

- Long Grobnok-class Peek: scroll relationships; × remains visible; recap column scrolls independently.
- Narrow ≤900px: Peek replaces CENTER; no world-object `← Back`; × reachable; close restores recap reading position.
- Tools Peek still shows `← Back`.
- No ingest header `{label} Close` strip.

## Explicitly still false

```text
STAGE 4 / RECAP WOW = HOLD
DeepSeek extraction ablation = parked IDEA only
Predicate-family relationship rollup = parked IDEA only
```


---

## Merge disposition

PR #735 merged to `main`:

`586a3dcb53b481ef2cf21890872a3f1e8465a925`

Accepted implementation head:

`f69163a2f4bca22d00c432c6c6419cd1b024d44d`

Formal Review Cycle 1:

`APPROVE` — review `5251493236`

The UI-05 implementation claim is accepted. The post-merge operator witness remains the authority for whether Stage 4 / recap WOW is promoted from HOLD.

The next CON-READY design frontier is not more Peek chrome. It is Authoring v2: manual source-grounded graph adjudication, governed World publication, derived gold, and only then extraction/model ablation.
