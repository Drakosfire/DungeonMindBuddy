# A10c implementation note — node detail hierarchy

Date: 2026-07-07  
Branch: `codex/graph-review-node-detail-hierarchy`

## A10a dogfood finding addressed

C1S2 dogfood found Story 4 (useful node detail beats metadata) and Story 5 (evidence quiet by default) only **partially** met. Clicking an authored node surfaced **Authored overlay** metadata (label, aliases, visibility, source anchor, assertion ID) before the campaign summary and relationship chips.

## What changed

- `GraphReviewNodeGameCard` reorders content: identity header → campaign summary → alias/memory note → relationships → useful surfaces → review status (when comparison context exists) → collapsed Evidence / Source → collapsed Technical details.
- Authored nodes use **Authored memory** lane copy instead of **Authored overlay**.
- Aliases render as **Also known as**; source anchors as **Grounded from source phrase**.
- Assertion ID, graph scope, raw visibility, source domains, node ID, lane role, and delta ID moved into collapsed **Technical details**.
- **Evidence / Debug** renamed to **Evidence / Source** and stays collapsed by default.
- **No comparison status is available yet** is hidden from the primary card when no comparison context exists.
- `gameSummaryForNode` fallback copy reads as campaign memory, not implementation telemetry.
- Relationship empty state copy improved in `GraphReviewRelationshipChips`.

## What remains deferred

- Statblock/encounter retrieval, backend node enrichment, LLM summarization, player UI, visibility preview toggle, eval export UI, identity merge, relationship authoring redesign, global graph query, full authored assertion browser.

## Manual dogfood checklist

Target: `http://localhost:5173/ingest?campaign=longmont-c1&session=session-2`

1. Load C1S2 graph review and confirm authored overlay loads.
2. Confirm `gang` / `the group` authored mention renders in recap (A10b).
3. Click the mention and open the selected object card.
4. Confirm summary and relationships appear before technical metadata.
5. Confirm aliases/source phrase use friendly copy.
6. Confirm assertion ID is only visible after expanding **Technical details**.
7. Confirm **Evidence / Source** is collapsed by default.

## Verification

```bash
cd apps/live-control-ui
npm test -- --run GraphReviewNodeGameCard
npm test -- --run GraphReviewLiveProjectionPanel
npm test -- --run graphReviewSelectionUtils
```
