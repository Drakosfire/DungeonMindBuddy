---
document_id: dmb-plan-command-board-combat-statblock-generator-roadmap
title: Command Board Combat + Statblock Generator Roadmap
document_class: plan
plan_kind: product_roadmap
status: active
version: 1.0
created_at: "2026-06-07T00:00:00Z"
last_updated_at: "2026-06-07T00:00:00Z"
related_design:
  - Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md
reference_merge:
  - "PR #102 / 17b162b — Add Mireward combat command board tracker"
---

# Command Board Combat + Statblock Generator Roadmap

## 0. Product destination

DungeonBuddy should support a live GM flow where the command board can:

1. run combat in a modern, maintainable **Combat Pane**;
2. drill from combat rows into compact **Statblock View**;
3. call an exposed **StatblockGenerator API** to generate or revise a statblock;
4. review/edit the generated draft without leaving the combat flow;
5. add accepted drafts directly to the initiative barrel as live combatants;
6. optionally promote reviewed statblocks into the corpus for long-term storage and cross-surface retrieval.

The critical path is not a full rewrite. The critical path is a thin vertical slice:

```text
load combat state
→ open statblock from row
→ generate reinforcement
→ review draft
→ add to circular initiative barrel
→ export/import state
→ later promote reviewed statblock to corpus
```

---

## 1. Strategic constraints

### Preserve from dogfood

- Rows first, drilldown second.
- Current/next turn visible.
- HP, AC, notes, and status visible without opening a modal.
- Statblocks one click away from combat rows.
- Grouped enemies reduce noise while preserving individual HP/dead state.
- Circular initiative barrel with virtual Top/Bottom of Round markers.
- Local/import/export survival for at-table interruptions.

### Do not repeat old mistakes

- Do not treat the static Mireward HTML page as the final product architecture.
- Do not physically move the active entity to the top of the data model.
- Do not compute round start from highest initiative after manual reorder.
- Do not make Top/Bottom markers a separate overlay with independent authority.
- Do not make generation write directly to arbitrary corpus paths.
- Do not replace StatblockGenerator before auditing its existing component/API shape.

### Product rule

**Fast combat acceptance and durable corpus ingestion are separate lifecycle steps.**

Combat can accept a generated draft quickly as live state. Corpus ingestion requires preview, confirmation, allowlisted paths, indexing, and retrieval smoke tests.

---

## 2. Track map

| Track | Purpose | Primary dependency | First useful output |
|---|---|---|---|
| **A. StatblockGenerator API** | Make generator consumable by DungeonBuddy | External repo audit | Stable generate/revise API |
| **B. Combat domain extraction** | Move static combat behavior into maintainable model/components | Current Mireward tracker | Tested initiative barrel + entity model |
| **C. Command Board Combat Pane** | Productize combat in live-control UI | Track B | Read-only CombatModule |
| **D. Statblock View** | Reusable statblock drilldown | Existing markdown statblocks | Compact/full statblock component |
| **E. Generator integration** | Let DungeonBuddy call generator | Tracks A + D | Generate variant from Statblock View |
| **F. Inline combat generation** | Generate/review/add combatants inside combat | Tracks B–E | Generate reinforcement vertical slice |
| **G. Terrain context** | Feed combat terrain pressure into generation | Track C | Compact terrain panel + generator context |
| **H. Corpus promotion** | Persist reviewed statblocks for retrieval | Tracks E/F + writer design | Preview-safe statblock ingest |

---

## 3. Project A — StatblockGenerator API readiness

**Goal:** StatblockGenerator has an exposed API DungeonBuddy can consume without depending on a full-screen generator app.

**Status:** Not started.

### Sprint A0 — Audit and contract

- [ ] **PR A0.1 — Audit StatblockGenerator + canvas library**
  - Identify current service/app/component boundaries.
  - Identify reusable generation core.
  - Identify canvas/rendering coupling.
  - Identify current request/response data shapes.
  - Output: audit doc in the generator/service repo or mirrored design note in Buddy.

- [ ] **PR A0.2 — API contract draft**
  - Define `generate`, `revise`, `parse`, `health/version` endpoints.
  - Define request/response schemas.
  - Include provenance, warnings, legality status, parsed combat defaults.
  - Output: contract fixtures usable by both repos.

- [ ] **PR A0.3 — Consumer fixture pack**
  - Add sample requests for:
    - generate from source statblock;
    - revise existing statblock;
    - quick combat reinforcement;
    - terrain-pressure generation.
  - Output: shared smoke fixtures.

### Sprint A1 — API shell

- [ ] **PR A1.1 — Expose generator endpoints**
  - `POST /api/statblocks/generate`
  - `POST /api/statblocks/revise`
  - `POST /api/statblocks/parse`
  - `GET /api/statblocks/health`

- [ ] **PR A1.2 — Validate schemas + errors**
  - Typed validation errors.
  - Provider/model errors.
  - Grounding-insufficient warnings.
  - Stable response envelope.

- [ ] **PR A1.3 — Add provenance/review metadata**
  - Source refs.
  - Generation mode.
  - Model/provider metadata.
  - Review warnings.
  - Legality status: `unchecked | passed | warnings | failed`.

### Sprint A2 — Generator modularization

- [ ] **PR A2.1 — Extract callable generation core**
  - Existing app can still use it.
  - API uses same core.
  - Avoid UI-only generation logic.

- [ ] **PR A2.2 — Parse combat summary from markdown**
  - Name, AC, HP/max HP, CR, size/type, key actions, tags.
  - Return defaults that DungeonBuddy can insert into combat.

- [ ] **PR A2.3 — Draft lifecycle**
  - Generated → edited → accepted/rejected.
  - Acceptance means “ready for consumer,” not corpus write.

**Exit gate A:** DungeonBuddy can call a real or mocked generator API and receive draft markdown + parsed combat defaults + provenance.

---

## 4. Project B — Combat domain extraction

**Goal:** Lift the proven static combat behavior into a tested, reusable domain model.

**Status:** Not started.

### Sprint B1 — Combat model

- [ ] **PR B1.1 — Combat state types + migration**
  - Define `CombatEncounterState`, `CombatEntity`, `CombatGroup`.
  - Import existing Mireward save shape.
  - Normalize `turnIndex` to `activeTurnEntityId` internally.
  - Preserve compatibility with existing exported JSON.

- [ ] **PR B1.2 — Initiative barrel module**
  - Sort baseline by initiative.
  - Manual reorder mutates stable barrel.
  - Active turn is pointer-based.
  - Top/Bottom of Round are virtual queue nodes.
  - Dead combatants skipped.
  - Tests cover round wrap and manual reorder.

- [ ] **PR B1.3 — Group/dead bucket logic**
  - Group by shared statblock path.
  - Preserve individual HP and defeated state.
  - Collapse all-dead groups automatically.
  - Dead bucket skipped in turn rotation.

**Exit gate B:** Existing Mireward combat state imports into the new model and preserves active turn, groups, HP, dead bucket, statblock paths, and round markers.

---

## 5. Project C — Command Board Combat Pane

**Goal:** Move combat from static proof page into the live-control command board as a product module.

**Status:** Not started.

### Sprint C1 — Read-only module

- [ ] **PR C1.1 — Register CombatModule**
  - Add `combat` to live packet catalog / surface layout where appropriate.
  - Add module registry entry in live-control UI.
  - Keep scope read-only.

- [ ] **PR C1.2 — Render combat projection**
  - Current turn.
  - Next turn.
  - Round state.
  - HP/AC/notes.
  - Grouped enemy rows.
  - Dead bucket.
  - Statblock links.

- [ ] **PR C1.3 — Import/export compatibility smoke**
  - Start from `mireward-north-reach-gate-combat-state.json`.
  - Render same core information in CombatModule.
  - Export remains readable by the static harness or a compatibility importer.

### Sprint C2 — Interactive live state

- [ ] **PR C2.1 — Local combat edits in module**
  - Damage/heal.
  - Notes.
  - Defeated/revive.
  - Set active turn.
  - Next/previous turn.

- [ ] **PR C2.2 — Persistence decision**
  - Choose one for v1:
    - local-only in browser;
    - live packet artifact;
    - server-backed command state.
  - Document why.

- [ ] **PR C2.3 — First live command, if ready**
  - Introduce `update_combat_state` or narrower commands only if command bus ownership is clear.
  - Otherwise keep C2 local and defer server writes.

**Exit gate C:** GM can run an imported combat in the command board without using the static page.

---

## 6. Project D — Reusable Statblock View

**Goal:** Make statblock viewing a reusable command-board component rather than a static page.

**Status:** Not started.

### Sprint D1 — Viewer component

- [ ] **PR D1.1 — `StatblockView` component**
  - Compact mode for combat use.
  - Full mode for full markdown.
  - Render persisted corpus markdown.

- [ ] **PR D1.2 — Combat row drilldown**
  - Clicking a combat row opens statblock without leaving combat.
  - Use Inspector Pane, side panel, or inline drawer.
  - Keep current combat context visible.

- [ ] **PR D1.3 — Pending draft rendering**
  - Render markdown that is not yet a corpus file.
  - Clearly label `pending/generated` vs `corpus/persisted`.

**Exit gate D:** Statblocks can be viewed from command-board combat rows and from standalone statblock contexts.

---

## 7. Project E — DungeonBuddy generator adapter

**Goal:** DungeonBuddy can call StatblockGenerator through a thin, typed adapter.

**Status:** Not started.

### Sprint E1 — Client and mocks

- [ ] **PR E1.1 — Add StatblockGenerator client**
  - Base URL config.
  - Generate/revise/parse calls.
  - Error normalization.
  - Response validation.

- [ ] **PR E1.2 — Mock provider**
  - Fixture drafts for UI development.
  - Toggle real/mock provider in local dev.

- [ ] **PR E1.3 — Provenance/warnings display**
  - Show source refs.
  - Show grounding status.
  - Show legality/review warnings.
  - Distinguish “usable live” from “safe to promote.”

**Exit gate E:** DungeonBuddy can request a draft statblock through mock or real adapter and render the reviewed result.

---

## 8. Project F — Generation from Statblock View

**Goal:** Land the first constrained generation UX before inline combat generation.

**Status:** Not started.

### Sprint F1 — Generate/revise from statblock

- [ ] **PR F1.1 — Generate Variant action**
  - Available from persisted statblock view.
  - Seeds source path and basic context.
  - Uses generator adapter.

- [ ] **PR F1.2 — Revise Existing action**
  - Supports “make tougher,” “make weaker scout,” “make siege variant,” etc.
  - Output is a draft.

- [ ] **PR F1.3 — Review/edit draft**
  - Editable markdown.
  - Parsed combat defaults.
  - Provenance and warnings.

- [ ] **PR F1.4 — Accept as pending statblock**
  - No corpus write.
  - Draft can be copied/exported or used to seed combat entity.

**Exit gate F:** User can generate a variant from a statblock, review it, and keep it as a pending draft.

---

## 9. Project G — Inline combat generator

**Goal:** Generate/review/add a combatant without leaving the Combat Pane.

**Status:** Not started.

### Sprint G1 — Reinforcement vertical slice

- [ ] **PR G1.1 — Generate Combatant entry points**
  - Toolbar button.
  - Enemy group row action.
  - Statblock drilldown action.

- [ ] **PR G1.2 — Inline generator pop-up**
  - Role.
  - CR/challenge band.
  - Pressure target.
  - Source statblock ref.
  - Terrain pressure.
  - Add-to-fight after accept.

- [ ] **PR G1.3 — Accept to combat**
  - Add entity to barrel.
  - Preserve pending markdown.
  - Use parsed AC/HP/defaults.
  - Assign team/group/tags.

- [ ] **PR G1.4 — Reinforcement smoke test**
  - Load Mireward saved state.
  - Generate one reinforcement from an existing group.
  - Accept it.
  - Advance turn.
  - Export/re-import.
  - Verify generated entity and draft survive.

**Exit gate G:** The core loop works: generate a reinforcement inline, review, add to initiative, keep running combat.

---

## 10. Project H — Terrain context

**Goal:** Give generation enough battlefield context without building a map editor.

**Status:** Not started.

### Sprint H1 — Compact terrain panel

- [ ] **PR H1.1 — Terrain data shape**
  - Zones.
  - Hazards.
  - Interactables.
  - Dynamic changes.
  - Source refs.

- [ ] **PR H1.2 — Combat terrain panel**
  - Compact operational cards.
  - No map editor.
  - Clear mechanical hooks.

- [ ] **PR H1.3 — Terrain-to-generator payload**
  - Select one or more terrain pressures.
  - Include in generation request.
  - Smoke test that generated draft references pressure appropriately.

**Exit gate H:** Combat generation can intentionally target terrain pressure like gate throat, cure line, cart jam, bell line, or road bend.

---

## 11. Project I — Corpus promotion and retrieval

**Goal:** Reviewed generated statblocks can become long-term corpus artifacts and then be retrieved across surfaces.

**Status:** Not started.

### Lifecycle

```text
generated_draft
→ live_pending
→ reviewed
→ promoted_to_corpus
→ indexed/retrievable
```

### Sprint I1 — Export and draft artifacts

- [ ] **PR I1.1 — Export draft markdown/JSON**
  - Download/copy generated draft.
  - No corpus write.

- [ ] **PR I1.2 — Generated draft artifact lane**
  - Store drafts as live/prep artifacts.
  - Preserve provenance.
  - Mark not-canon / not-promoted.

### Sprint I2 — Preview-safe corpus write

- [ ] **PR I2.1 — Dedicated statblock write preview command**
  - New command, not generic arbitrary write.
  - Allowlisted target folders.
  - Dry-run diff.
  - Confirm token.
  - File-state conflict handling.

- [ ] **PR I2.2 — Statblock frontmatter policy**
  - Required metadata:
    - generated source;
    - campaign/session if applicable;
    - source refs;
    - review status;
    - generator version;
    - promotion timestamp.

- [ ] **PR I2.3 — README/index update preview**
  - Separate preview from statblock file write.
  - Explicit confirmation.
  - No silent hub mutation.

### Sprint I3 — Retrieval integration

- [ ] **PR I3.1 — Re-index after promotion**
  - Promoted statblock appears in statblock hub/index.
  - Retrieval can discover it.

- [ ] **PR I3.2 — Cross-surface retrieval smoke**
  - Generate → review → promote → index → retrieve in Statblock View.
  - Add promoted statblock to Combat Pane as corpus-backed entity.

**Exit gate I:** Generated statblocks can safely become corpus-backed, indexed, and reusable across DungeonBuddy surfaces.

---

## 12. Recommended phase order

### Phase 1 — Prove contracts and preserve combat semantics

- A0: StatblockGenerator audit + API contract.
- B1: Combat model + initiative barrel extraction.

**Why first:** Prevents building UI on imaginary generator internals and protects the initiative model that made dogfooding useful.

### Phase 2 — Move combat into the command board

- C1: Read-only CombatModule.
- D1: StatblockView.

**Why second:** Gives the command board the core at-table value before generation complexity.

### Phase 3 — Add generator consumption safely

- A1/A2 enough for API.
- E1: DungeonBuddy adapter.
- F1: Generate/revise from Statblock View.

**Why third:** Statblock View is a constrained generation context and easier to reason about than live combat.

### Phase 4 — Land the inline combat generator

- G1: Generate reinforcement vertical slice.
- H1: Terrain context, if needed for useful prompts.

**Why fourth:** This is the highest-value workflow, but it depends on the model, view, and adapter being real.

### Phase 5 — Promote to corpus

- I1/I2/I3: export, draft lane, preview-safe corpus write, indexing, retrieval smoke.

**Why fifth:** Durable corpus mutation should follow proven live utility, not precede it.

---

## 13. Short-form PR stack

Use this list when choosing the next concrete work item:

1. [ ] Audit StatblockGenerator + canvas library.
2. [ ] Draft shared API contract + fixtures.
3. [ ] Extract combat state and initiative barrel model.
4. [ ] Import existing Mireward saved combat state into new model.
5. [ ] Add read-only CombatModule to live-control UI.
6. [ ] Add reusable StatblockView component.
7. [ ] Add DungeonBuddy StatblockGenerator client with mock provider.
8. [ ] Generate Variant from Statblock View.
9. [ ] Review/edit/accept pending statblock draft.
10. [ ] Inline Generate Combatant pop-up in Combat Pane.
11. [ ] Accept generated combatant into circular barrel.
12. [ ] Add compact Terrain Panel and terrain-to-generator context.
13. [ ] Export generated draft/state.
14. [ ] Add generated draft artifact lane.
15. [ ] Add preview-safe statblock corpus write command.
16. [ ] Add README/index update preview.
17. [ ] Add promote → index → retrieve smoke test.

---

## 14. Definitions of done

### Combat Pane v1 done

- Existing Mireward state renders in command board.
- Current turn and next turn visible.
- HP/AC/notes editable or at least visible.
- Grouped enemies work.
- Dead bucket works.
- Top/Bottom markers behave as queue nodes.
- Statblock drilldown works without leaving combat.

### Generator API v1 done

- DungeonBuddy can call generate/revise.
- Response includes markdown, parsed combat defaults, warnings, provenance, and version metadata.
- Mock and real providers share the same adapter contract.

### Inline generator v1 done

- GM can launch generation from combat.
- Draft appears in review UI.
- Accepted draft becomes a combat entity.
- Export/re-import preserves the generated entity and pending statblock.

### Corpus promotion v1 done

- Reviewed draft can be previewed as corpus write.
- Write is allowlisted and confirm-token gated.
- README/index update is separately previewed.
- Promoted statblock becomes retrievable and usable from Statblock View and Combat Pane.

---

## 15. Open decisions

1. Where exactly does the real StatblockGenerator API live: DungeonMindServer, standalone repo, or new service boundary?
2. Does Combat Pane v1 persist through local state first or server command state first?
3. Should generated pending statblock markdown live inside combat state, a live artifact, or both?
4. What corpus folder should promoted generated statblocks use by default?
5. Are legality checks blocking for corpus promotion or only warnings?
6. Does README/index update happen in the same review flow or as a second explicit action?
7. What is the smallest useful terrain fixture for the next combat-heavy session?

---

## 16. Immediate next recommended action

Start with **PR A0.1 + PR A0.2** in the StatblockGenerator/DungeonMindServer side and **PR B1.1 + PR B1.2** in DungeonBuddy.

These two tracks can run in parallel and meet cleanly:

```text
StatblockGenerator contract exists
+
Combat barrel model exists
=
DungeonBuddy can safely build the command-board generator UX
```
