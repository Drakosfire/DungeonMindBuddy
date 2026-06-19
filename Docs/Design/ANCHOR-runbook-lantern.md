# ANCHOR — Runbook Lantern

**Anchor phrase:** `Runbook Lantern`  
**Created:** 2026-06-18  
**Project area:** DungeonBuddy / Command Board / Tiptap runbook / campaign memory  
**Use this when context drifts:** “Pull us back to the Runbook Lantern.”

---

## 0. One-line anchor

**The Runbook Lantern is the GM-facing light cast from DungeonBuddy’s deeper campaign memory: it illuminates only what matters for the current session, keeps the table moving, and never pretends to be the whole world, the canon store, or the live operational state.**

---

## 1. Why this anchor exists

The current work is easy to fragment into separate concerns:

- Markdown rendering.
- Tiptap authoring.
- Reference chips.
- Popovers.
- Corpus indexes.
- Combat seeds.
- Live Play pages.
- Session descriptors.
- Next-session generation.
- Long-term campaign memory.

The anchor prevents category drift.

When we say **Runbook Lantern**, we are pulling the project back to this core idea:

> DungeonBuddy preserves and reasons over the campaign world; the runbook projects the right slice of that world into a calm, playable, session-shaped command surface.

---

## 2. Source documents this anchor binds together

### 2.1 Executive architecture summary

`Docs/Design/dungeonbuddy_spec_architecture_v0_2.md`

DungeonBuddy is defined as a continuity-preserving campaign memory and planning system, not merely a chat assistant or retrieval wrapper. Its purpose is to maintain a durable, queryable, evolving model of a campaign world so a GM can prep, inspect canon, recover context, generate material, and update world state without re-pasting recaps or re-deriving relationships every time.

The architectural thesis is a tiered memory system with a memory controller over it, backed by temporal canon graph concepts and surfaced through compiled views such as indexes, profiles, evidence packs, and tools.

The important project-level claim:

```txt
DungeonBuddy owns durable campaign memory and controlled world evolution.
The runbook is one compiled view of that memory for a specific table workflow.
```

### 2.2 Session runbook command-surface design

`Docs/Plans/DESIGN-session-runbook-command-surface.md`

The runbook’s primary premise:

```txt
The session runbook is the table-facing projection of prep, not the prep database itself.
```

The runbook should read like a tight script and behave like a command surface. It is a calm, linear document that moves the GM from opening frame to scene beats, choices, consequences, likely combats, and fallback material. Important nouns and procedures can be clicked, expanded, rolled, launched, cited, or edited without losing the thread.

The important product-level claim:

```txt
The runbook owns session sequence and table-facing framing.
It does not own canonical truth, combat state, or source truth.
```

### 2.3 Runbook roadmap and session ingestion design

`Docs/Design/DESIGN-runbook-roadmap-and-session-ingestion.md`

The roadmap turns the runbook into a typed, tool-aware command surface through small contracts:

1. Runbook rendering and chip command surface.
2. Runbook authoring and safe write loop.
3. Session-data ingestion and dynamic next-session construction.

The key framing:

```txt
C2S23 Mireward is the starting point and proof model, not the hardcoded future product.
```

The important roadmap-level claim:

```txt
The current work should make proven C2S23 patterns reusable for future sessions, without letting the current session’s hardcoded state become the architecture.
```

---

## 3. The Runbook Lantern model

The anchor has three layers.

### Layer 1 — Memory below the lantern

This is DungeonBuddy’s deeper architecture:

- Campaign artifacts.
- Source files.
- Corpus/canon.
- Indexes.
- Profiles/dossiers.
- Evidence packs.
- Temporal facts.
- Relationships.
- Contradictions.
- Open loops.
- Human-reviewed promotions.

This layer answers:

```txt
What is true, where did it come from, how has it changed, and what evidence supports it?
```

### Layer 2 — The lantern lens

This is the session descriptor / planning selection layer:

- What session is being built or run?
- Which sources matter now?
- Which NPCs, locations, statblocks, roll tables, citations, items, and actions are in scope?
- Which runbook file is the table-facing projection?
- Which combat/clocks/tool seeds initialize operational state?
- Which material is ready, draft, locked, or reference-only?

This layer answers:

```txt
What slice of the campaign should be visible for this session?
```

### Layer 3 — Light at the table

This is the GM-facing runbook and Live Play command surface:

- Opening frame.
- Read-aloud.
- GM notes.
- Scene beats.
- Choices and consequences.
- Typed reference chips.
- Contextual tools.
- Launchable combat/actions.
- Fallback material.
- Minimal provenance, collapsed unless needed.

This layer answers:

```txt
What does the GM need next, without losing the thread?
```

---

## 4. Durable separation

The Runbook Lantern depends on this separation staying intact:

```txt
Tiptap JSON = local editable working-board state
Exported Markdown = derived artifact
Backend API = intentional file materialization boundary
Prep Markdown file = durable table-facing runbook artifact
Corpus/canon = separate authority boundary
Operational JSON = live combat/clocks/tools state
```

If a future PR blurs these lines, invoke the anchor.

Examples:

- If combat HP starts living in prose, invoke Runbook Lantern.
- If Tiptap becomes canon by accident, invoke Runbook Lantern.
- If the Live Play page becomes a giant source dashboard, invoke Runbook Lantern.
- If reference chips start mutating corpus directly, invoke Runbook Lantern.
- If session descriptor work starts trying to become a world database, invoke Runbook Lantern.
- If next-session generation writes canon without review, invoke Runbook Lantern.

---

## 5. Practical rule of thumb

When deciding whether a feature belongs in the runbook, ask:

```txt
Does this help the GM run the next few minutes at the table?
```

If yes, it may belong in the lantern light.

If it answers “what is canonically true?” it belongs behind a typed reference.

If it answers “what is currently happening in combat or clocks?” it belongs in operational state.

If it answers “what should be in scope for this session?” it belongs in the session descriptor.

If it answers “how does the campaign world evolve over time?” it belongs in DungeonBuddy memory/canon systems.

---

## 6. How to use this anchor in future work

Use the phrase:

```txt
Runbook Lantern
```

When this anchor is invoked, reload these assumptions:

1. DungeonBuddy is a continuity-preserving campaign memory and planning system.
2. The runbook is a compiled table-facing projection, not the database.
3. The roadmap should proceed by small contracts.
4. C2S23 is proof material, not permanent hardcoded architecture.
5. Session descriptor is the stable bridge from campaign memory to next-session command surface.
6. Reference chips are doorways into source/canon/tools, not canon themselves.
7. Operational live state must remain separate from prose and canon.
8. The GM-facing surface should stay calm, linear, and playable.

---

## 7. Compact restatement for handoffs

Use this paragraph in future handoffs when context needs to be restored:

> Anchor: **Runbook Lantern**. DungeonBuddy is the durable campaign-memory and planning system; the session runbook is the GM-facing light cast from that memory for one session. It should read like a linear script and behave like a typed command surface, while keeping canon/reference data, editable runbook prose, session descriptors, and operational live state separate. C2S23 is proof material, not the hardcoded future architecture. Build small contracts that make the next session easier to construct and run without turning the runbook into a dashboard, database, or hidden canon mutation surface.

---

## 8. Current roadmap relation

The active work should continue in this order unless deliberately changed:

1. Typed Markdown reference chips.
2. Tiptap inline reference chip spike.
3. Reference chip popover shell.
4. API-backed resolver v1.
5. Tiptap-authored runbook dogfood.
6. Tiptap document descriptors.
7. Minimal Markdown-to-Tiptap import.
8. Block save-state badges.
9. Replace one real Markdown surface.
10. Reusable Tiptap runbook editor.
11. Session descriptor manifest.
12. Unified typed reference index.
13. Session operational seeds.
14. Next-session builder spike.
15. Dynamic Live Play page from session descriptor.

The roadmap should be judged against the anchor: every step should either improve the lantern, clarify the lens, or preserve the memory underneath.
