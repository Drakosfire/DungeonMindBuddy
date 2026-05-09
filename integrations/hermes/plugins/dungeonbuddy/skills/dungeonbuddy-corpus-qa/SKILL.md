---
name: dungeonbuddy-corpus-qa
description: Answer DungeonMindBuddy campaign and corpus questions using DungeonBuddy tools.
version: 0.1.0
author: DungeonMindBuddy
license: MIT
metadata:
  hermes:
    tags: [TTRPG, DungeonBuddy, corpus, canon, retrieval]
    requires_tools:
      - dungeon_search
---

# DungeonBuddy Corpus QA

## When to Use

Use this skill for questions about:

- campaign lore
- session recaps
- worldbuilding
- NPCs
- locations
- factions
- canon continuity
- planning notes
- contradictions or uncertainty in the campaign corpus

## Procedure

1. Do not answer from memory for campaign facts.
2. Call `dungeon_search` first.
3. Use `dungeon_get_document` for one or more high-value documents if excerpts are insufficient.
4. Answer only from retrieved evidence.
5. Distinguish:
   - confirmed evidence
   - likely inference
   - missing evidence
   - possible contradiction
6. Do not write canon or update memory unless the user explicitly asks and a DungeonBuddy write tool exists.

## Continuity Checks

When the user asks whether something conflicts with canon:

1. Call `dungeon_check_continuity`.
2. Report evidence candidates.
3. Say clearly that v0 is not final canon adjudication unless a reducer/canon tool is available.
4. Identify what future tool would be needed to decide.

## Output Style

Prefer:

- direct answer first
- supporting evidence second
- uncertainty third
- next useful query/tool suggestion only when helpful

Avoid:

- inventing lore
- treating Hermes memory as canon
- treating mock tool output as real
- silently merging planning notes into canon
