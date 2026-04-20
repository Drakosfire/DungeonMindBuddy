---
name: npc-power-increase
description: Corpus-grounded workflow to raise an NPC’s power baseline (feel, presence, arc) without inventing stat lines in chat—research, attach the canonical statblock via load_context_markdown, then deliver evocative prose.
---

# NPC power increase (corpus-grounded)

Use this skill when the GM wants an NPC to **step up in baseline power** (challenge, table presence, narrative weight, how hard they are to ignore in a scene)—**not** when they only want a rules lookup or a full new statblock authored in the chat window.

## Outcomes

1. **Truth on disk:** the right hub files were opened; the **canonical mechanical statblock** for this NPC is attached to the turn context via `load_context_markdown` (not retyped from memory).
2. **Creative direction:** a **prose-only** artifact describing how the NPC should *feel* stronger—pressure, tempo, body language under stress, how allies lean on them, how enemies underestimate or fear them, what changes in the **fiction** of power. Avoid AC/HP/to-hit lines; those belong in the statblock file or a dedicated generator step later.

## Tools (DungeonMindBuddy planner)

| Tool | Role |
|------|------|
| `read_corpus_file` | Discovery: hub `README.md`, dossier, `timeline.md`, optional session recaps. Use literal paths from the tree or README lists—**no** `*` / `?` globs. |
| `load_context_markdown` | **Attach** the chosen `*_statblock_*.md` once the canonical row is clear. Same bytes as `read_corpus_file`, but signals “this sheet is the working baseline for the rest of this turn.” The tool response is prefixed `[context attached: …]` so traces stay legible. |
| `generate_statblock` | **Not part of this skill** unless the user explicitly asked for a **new** generated creature block. Power bumps on an **existing export** stay in corpus + prose. |

## Protocol

### 1. Orient (README first)

Open the NPC hub **`README.md`** (e.g. `Longmont Campaign/.../captain_lysandra_ironveil/README.md`). Use **Suggested reads** and any **Mechanical sheets (priority)** table. Treat the **highest-priority** statblock row as **canonical** unless the user asked for an older sheet (e.g. CR2 baseline for comparison).

### 2. Research (select context)

Use `read_corpus_file` on the smallest set that answers:

- **Who they are now** — dossier / character voice.
- **Where the table left them** — `timeline.md` and, if needed, the recap file the timeline row points to.
- **What “stronger” should respect** — red lines, relationships, rank stress, current arc.

Do **not** paste long dossier or timeline blocks into the **final user-visible answer**; summarize in your own words.

### 3. Attach the mechanical baseline

When you know which `*_statblock_*.md` is canonical for this bump:

- Call **`load_context_markdown`** once with that path.
- Do **not** paste the statblock body into the final message (retyping invites wrong CR, wrong numbers, or “already upgraded” fantasy stats).

Downstream systems can rely on **tool trace + corpus path** plus your prose brief.

### 4. Write the power-rise prose

Produce **creative, table-facing** description only, for example:

- How **initiative** and **spotlight** shift when this NPC enters a scene at the new tier.
- How **failure and success** both feel different at the table.
- **Sensory and social** signals of increased authority or danger (voice, spacing, who steps aside).
- How existing traits **scale in fiction** (command presence, fear, loyalty tests)—without listing game numbers.

End when the creative brief feels actionable for whoever will edit the real statblock or run the next session.

## Anti-patterns

- Pasting full statblocks or stat lines in chat “to be helpful.”
- Skipping the hub README and guessing paths from the global tree alone.
- Choosing a non-canonical archive sheet without the user asking for it.
- Emitting a **files used** bibliography in the final message (trace + eval reports already capture paths where needed).

## Runtime pipeline (target)

Aligns with **Docs/Plans/FLOW-npc-power-skill-pipeline.md**:

1. **User text in**  
2. **Intent check** — `classify_intent(user_line)` in `src/npc_statblock_pipeline/canonical_intent.py`  
3. **Select skill** — `route_user_line_to_skill(user_line)` in `src/agent/skill_pipeline.py` (today: `upgrade_request` → this skill id)  
4. **Research** — `read_corpus_file` (README, dossier, timeline, …)  
5. **Attach** — `load_context_markdown` on canonical `*_statblock_*.md`  
6. **Write prose** — power-rise description only in the final assistant message  
7. **Combine** — bundle `{user_line, intent, skill_id, tool_trace, prose}` for downstream generator / store (orchestrator TBD; Step 4 slice is the closest current consumer)

**Benchmark CLI:** set ``LYSANDRA_PLANNER_USER_MESSAGE`` to your ask (and omit ``LYSANDRA_PLANNER_STEP1_SCENARIO``); the harness uses ``scenario_key_for_user_line`` so upgrade prompts pick ``upgrade_prose`` gold (gates only — no extra instruction appendix). Pin a scenario with ``LYSANDRA_PLANNER_STEP1_SCENARIO=…`` when needed.

## See also (sibling skills)

- **`recap-write`** — write-enabled, structurer + light extractor. Use that skill when the GM hands you raw session notes and wants a numbered recap on disk; it writes the recap file and emits a structured follow-up payload (timeline-append candidates, new-hub proposals, plot artifacts, prep-pointer text, dismissed NPCs) for the GM to act on. If a recap implies a future power bump for an NPC ("she stepped into command and held the line"), finish the recap commit first, then start a separate turn with this skill (`npc-power-increase`) to write the *creative direction* for the bump. Neither skill ever edits `*_character_dossier.md`, `character_seed.md`, or `*_statblock*.md` — those are the static character/world bible. (NPC `timeline.md` row appends are reserved for the future per-NPC `recap-timeline-append` skill.)

## Related repo wiring

- Eval scenario **`upgrade_prose`** appends a short in-prompt summary of this protocol (`evals/lysandra_vertical_slice/step1_planner_trace.py`).
- Gold gates require `read_corpus_file` **and** `load_context_markdown` (`evals/lysandra_vertical_slice/gold/planner_step1_upgrade_prose.json`).
- Shared trace path extraction: `src/agent/corpus_path_tools.py` (`read_paths_from_tool_trace`).
