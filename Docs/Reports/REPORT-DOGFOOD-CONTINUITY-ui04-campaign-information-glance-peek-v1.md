# REPORT — UI-04 campaign-information glance + peek v1

**Status:** implementation evidence, Stage 4 still human-gated  
**Date:** 2026-09-18  
**Branch:** `dogfood-continuity/ui04-campaign-information-glance-peek-v1`  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui04-campaign-information-glance-peek-v1.md`  
**Base:** `main@0dfc00783f55503c02dce280d73ac4e4cc4cf527`

## Claims

```text
RECAP FOCUS-SESSION CONTINUITY = PASS
UI-04 CAMPAIGN-INFORMATION GLANCE/PEEK = PASS (deterministic tests)
STAGE 4 / RECAP WOW = not claimed — human witness still required
```

This slice does **not** claim semantic coverage, kind quality, mention/pill recall, Agent answerability, or authoring UX.

## Gate 0

- Shared World Graph lens URL sync no longer rewrites `/ingest?session=session-27` into Plan-qualified `longmont-c2:27`.
- Recap browsing recovers `session-N` if a qualified lens value is already in the URL, then repairs the recap identity before the recap request.
- Interactive C2 → C1 campaign switch waits for the target campaign's numeric recap artifacts and loads that campaign's default/latest session. It does not issue C1/`session-26`.
- Explicit missing hard links still fail closed (`session-99` remains requested and surfaces `recap_markdown_unavailable`).

## Glance / Peek

- Ordinary recap pills keep one interactive treatment. Role/kind palettes no longer imply trustworthy ontology.
- Glance scan is label, quiet type, summary, then one focus fact. `Why it matters here` and redundant `this session` are gone.
- Recap Peek identity is the object label. Redundant `World Object` chrome and primary `Continue in Build` are gone.
- Relationship copy is subject-aware (`Ogonob possesses Misty Step.`) and incoming edges reverse. `session_recap` is not ordinary-row copy.
- Raw excerpts stay behind the recap `Source` disclosure. Summary is visually clamped; stored bytes are preserved.
- Plan/default card grammar is unchanged unless `mode="campaign-memory"`.

## Evidence

Leased vitest, all passed:

```text
src/graphLens/sessionCampaignContext.test.ts
src/planSurface/graphPreview/RecapGraphModule.test.tsx
src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx
src/graphReference/GraphNodeHoverToken.test.tsx
src/graphReference/nodeGlancePresentation.test.ts
src/graphObjectCard/graphObjectDisplay.test.ts
src/graphObjectCard/GraphObjectCard.test.tsx
src/graphObjectCard/GraphObjectProjectionCard.test.tsx
```

Adjacent lens protection also passed (`GraphLoadPanel`, `WorldGraphLensContext`, `useWorldGraphLensProjection`).

## Remaining false

Hybrid monsters/Swarms may still have the wrong kind. Missing PC/swarm pills, Ogonob enrichment, Thalia duplicates, 7A1, and highlight-text → Agent authoring remain successors / parked. Manual C2 Session 27 + C1 Cultists/Dustwalker witness is still required before Stage 4 WOW can be recorded.
