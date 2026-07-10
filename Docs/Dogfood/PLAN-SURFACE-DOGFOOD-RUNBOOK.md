# /plan Dogfood Runbook

## Purpose

Use `/plan` for a real prep pass and capture feedback on the current prep cockpit.

## Preconditions

- PR #313 merged (prep memory Q&A drawer, selected-object cards, source preview, durable Markdown save).
- Dev server can run.
- Corpus/source data exists for the target campaign.
- You know the campaign/session route you want to prep.

## Start

1. Start the backend and frontend dev servers.
2. Open `/plan` with dogfood mode enabled, preserving campaign/session params when needed:

   ```text
   /plan?campaign=longmont-c2&session=22&dogfood=1
   ```

3. Confirm the header shows the expected campaign, prep session, and memory session.
4. Use the **Dogfood checklist** panel to track your pass (optional but recommended).

## Real content pass

1. Add real prep notes to the Tiptap board.
2. Add scene beats and unresolved threads.
3. Add reference chips where relevant (e.g. NPCs, locations, roll tables).
4. Click **Preview Markdown save** and review the diff.
5. Click **Commit Markdown save** after confirming the preview.

## Recovery pass

1. Reload the browser tab.
2. Confirm board content remains (local draft and/or durable Markdown).
3. Stop the dev server.
4. Restart the dev server.
5. Reopen `/plan?...&dogfood=1` with the same campaign/session params.
6. Confirm durable content and/or local draft recovery.

## Memory inspection pass

1. Click a reference chip on the board.
2. Inspect the selected-object card in the right rail.
3. Use **Show source preview** from the card.
4. Open the prep memory drawer and ask real questions, for example:
   - What should I remember about this session?
   - What unresolved threads matter?
   - What threats should I prep?
5. Open a supporting source from the prep-memory answer citations.

## Feedback capture

1. Fill **Dogfood notes** in the checklist panel as you go.
2. Check off checklist items that you completed.
3. Click **Copy dogfood report**.
4. Paste the report into chat, a handoff, or an issue.

**Reset dogfood checklist** clears only checklist state and notes. It does **not** change the prep board.

## What to look for

- Did the page feel like prep or like metadata?
- Did save/recovery feel trustworthy?
- Were source previews useful?
- Did prep-memory answers cite enough?
- Were ungrounded answers clearly marked?
- What did you expect DungeonBuddy to surface automatically?
- What felt too graph-y or diagnostic-heavy?

## Suggested end-to-end sequence

```text
1. Start dev server.
2. Open /plan with ?dogfood=1.
3. Add real Session Prep content.
4. Preview Markdown save.
5. Commit Markdown save.
6. Reload tab.
7. Confirm content remains.
8. Stop dev server.
9. Restart dev server.
10. Reopen /plan?dogfood=1.
11. Confirm content recovers.
12. Click a reference chip.
13. Inspect selected-object card.
14. Show source preview.
15. Ask prep memory two real questions.
16. Open supporting source.
17. Fill dogfood notes.
18. Copy dogfood report.
```

## What this unlocks

Dogfood reports should drive the next slice — not a predetermined roadmap. Common outcomes:

- Page feels empty → compact prep packet.
- Save/recovery feels shaky → save/recovery polish.
- Memory answers are weak → retrieval/query UX polish.
- Selected cards feel shallow → richer selected-object details.
- UI feels too metadata-heavy → hide/collapse more diagnostics.
