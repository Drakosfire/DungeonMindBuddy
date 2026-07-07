# NOTE — A10e Authoring Surface Layout + Quiet Source Details

**Date:** 2026-07-07  
**PR anchor:** A10e / PR 290  
**Depends on:** A10b (alias prose grounding), A10c (node detail hierarchy), A10d (form clarity)

## A10a findings addressed

- **Authoring selected-source panel was metadata-heavy:** graph id, lane role, source artifact, and paragraph appeared as primary fields before the GM could understand what they selected.
- **Prepare/commit panel required scroll:** staged drafts and write controls were separated vertically with a long developer metadata slab in between.
- **Evidence/debug details were quiet, but authoring details were not:** write safety existed but implementation paths/tokens/digests dominated the primary prepare/commit flow.
- **Commit success buried the next action:** overlay/event-log paths appeared before refresh guidance.

## Changes

### Selected-source metadata demotion

- Primary view shows selected phrase, readable context (or fallback copy), and draft-only lede.
- Technical fields (selection kind, campaign/session, lane role, graph id, source artifact, paragraph) moved into collapsed **Source details**.

### Staged memory / prepare-commit layout

- Staging tray and prepare/commit panel wrapped in **Review staged memory** section with clearer lede copy.
- Empty state uses generic staged-memory language for objects, links, and relationships.
- Prepare button label updated to **Prepare staged memory** and sits directly under staged proposal cards.

### Prepare/commit hierarchy

- Prepare preview primary view shows assertion counts and a safety summary sentence.
- No-mutation guarantees, overlay path, event log path, overlay token, and digest moved into collapsed **Write safety details** / **Technical write details**.
- Commit success primary view prioritizes **Refresh graph review** as the next action.
- Overlay/event-log/backup/token/count details moved into collapsed **Write details**.

## What remains deferred

- Sticky/fixed prepare-commit rail
- Backend write behavior changes
- Authored overlay schema changes
- Player-facing UI and audience preview toggle
- LLM assist and identity merge
- Eval export UI and graph visualization

## Manual dogfood checklist (C1S2)

Target: `http://localhost:5173/ingest?campaign=longmont-c1&session=session-2`

1. Open graph review for C1S2.
2. Highlight “gang” and open graph authoring.
3. Confirm selected-source area shows the phrase and readable context first.
4. Confirm graph id/source artifact/lane/paragraph are hidden in Source details.
5. Link “gang” to “the group” or stage another safe draft.
6. Confirm staged memory tray uses generic memory language, not object-only language.
7. Confirm Prepare staged memory is near the staged draft review.
8. Prepare write.
9. Confirm primary prepare preview shows counts and safety summary, not paths/tokens/digests.
10. Expand write details and confirm paths/tokens/no-mutation guarantees remain available.
11. Commit.
12. Confirm success copy points to Refresh graph review first.
13. Confirm overlay/event log/backup/token details are collapsed.
14. Refresh graph review and confirm authored memory appears.

**Pass condition:** A GM can move from selected phrase to staged draft to prepare/commit without reading implementation metadata unless they choose to expand details.
