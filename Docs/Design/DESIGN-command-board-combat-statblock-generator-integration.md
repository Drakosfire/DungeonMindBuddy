# Design: Command board combat + StatblockGenerator integration

**Status:** Design proposal / implementation handoff  
**Captured:** 2026-06-07  
**Reference handoff:** `Handoff: command-board combat + statblock generator design pass`  
**Reference merge:** PR #102 / `17b162b` — Add Mireward combat command board tracker  
**Scope:** Main-branch design pass. Do not treat this as a rewrite directive.

---

## 1. Thesis

The Mireward combat tracker proved a specific product shape: the GM needs a **live operational command board** first, and deeper information second.

The next slice should not promote the static page wholesale. Instead, lift the useful pattern into the live-control architecture:

```text
combat row
→ statblock drilldown
→ generate / revise combatant
→ review
→ add to live initiative barrel
→ optional preview-safe corpus write
```

The important lesson is not the HTML implementation. It is the flow: **rows first, drilldown second, generation adjacent to the fight, writes previewed before commit.**

---

## 2. Grounding evidence from current repo

### 2.1 Dogfood backlog lesson

`Backlog.md` captures the key live-use finding: the combat tracker felt useful because it kept turn order, HP, active/next actor, statblocks, and state persistence in the GM's flow. It specifically recommends carrying forward statblock/entity drilldowns, HP/turn state in main view, a stable circular barrel with virtual markers, small live-use surfaces over generic dashboards, and import/export/local persistence.

### 2.2 Static combat tracker shape

`evals/c2_live_prep/mireward-prep/combat.html` currently provides the proof surface:

- active/current turn card;
- source links;
- toolbar for initiative sort, next turn, reset, export, import, reset-all;
- visible columns: Move, Entity, Init, AC, HP, Damage / Heal, Notes;
- linked statblocks from combat rows;
- floating previous/next controls;
- browser localStorage plus bootstrap from saved JSON.

This page is a strong interaction sketch, not the final architecture.

### 2.3 Static statblock drilldown baseline

`evals/c2_live_prep/mireward-prep/statblocks.html` proves the read-only drilldown model: a compact roster summary, quick-pick role cards, and expandable rendered statblock sections. It also shows that the GM wants statblocks available by table role, not only file path.

### 2.4 Combat state shape

`evals/c2_live_prep/mireward-prep/saves/mireward-north-reach-gate-combat-state.json` proves the minimum durable live state:

- schema id;
- export timestamp/source;
- round;
- turn pointer;
- ordered entities;
- per-entity id, name, team, order, initiative, hp, maxHp, notes, defeated flag, statblock path.

This is enough to smoke-test generation insertion.

### 2.5 Live-control direction

`Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` locks the larger architecture: the UI is a projection and interaction layer, the server owns projections/writes/audit/retrieval, and human panes plus agent tools should share typed commands/capabilities. The command endpoint is `POST /api/live/commands`.

The live packet catalog does not yet include a combat module. `apps/live-control-ui/src/surface/moduleRegistry.tsx` likewise has no combat module case; this is the clean seam for a first product lift.

### 2.6 Statblock generation boundary

`Docs/Design/DESIGN-lysandra-statblock-vertical-slice-benchmark.md` is explicit that the benchmark currently proves corpus-grounded retrieval/prose, not structured statblock JSON, legality checks, persistence, or a finished generator/store loop.

`Docs/Guides/FLOW-npc-power-skill-pipeline.md` defines the intended handoff shape: user text → intent → skill → research → attach → prose → combine. Its gap is the typed handoff object from planner/corpus context into generator/review/store.

`.cursor/skills/npc-power-increase/SKILL.md` is also explicit: research first, attach the canonical statblock with `load_context_markdown`, then produce prose. Generation is not part of that skill unless explicitly requested. Do not bypass this grounding step when integrating generation.

### 2.7 Writer safety boundary

`src/agent/corpus_writer.py` enforces two-phase preview/confirm writes and explicitly denies direct writes to dossier, seed, and `*_statblock*.md` paths in the current writer. Therefore, a statblock generator integration cannot simply call the existing corpus writer and write arbitrary statblock files. It needs either:

1. export-only / live-state-only acceptance for the first slice; or
2. a new deliberately scoped statblock write command with its own allowlist, preview, confirm token, README-index policy, and tests.

---

## 3. External StatblockGenerator audit status

The handoff requested opening the standalone StatblockGenerator project and its home-built canvas library before recommending component APIs.

I could not locate that external repository through the installed GitHub repository search or public web search during this pass. The only visible references in this repo point to DungeonMindServer / sibling services as the production location for CardGenerator, StatblockGenerator, RulesLawyer, and PlayerCharacterGenerator.

**Consequence:** this design avoids claims about existing StatblockGenerator component internals. It proposes an adapter boundary and requires a real external-repo audit before code extraction or rewrite decisions.

Implementation must not begin by rewriting StatblockGenerator. First action in a coding slice: open the actual sibling repo, identify existing component/service boundaries, then map them to the adapter below.

---

## 4. Product answer: where combat should live

Combat should become a first-class **live-control command-board module** with an optional static harness adapter.

Recommended shape:

```text
packages / shared module code
→ apps/live-control-ui CombatModule
→ optional eval static harness adapter for dogfood pages
```

Do not keep the static prep page as the long-term product. Also do not force the GM into a separate full-screen generator app. The combat module should host or launch narrow panels:

- Combat tracker;
- Statblock preview;
- Terrain / zone detail;
- Generate reinforcement;
- Review accepted combatant;
- Export / preview write.

The static prep harness can remain useful as a smoke-test and table backup, but product investment should move to `apps/live-control-ui`.

---

## 5. Component model

### 5.1 CombatTracker component

```ts
interface CombatTrackerProps {
  encounter: CombatEncounterState;
  terrain?: CombatTerrainState;
  onPatchEntity: (patch: CombatEntityPatch) => void;
  onAdvanceTurn: (direction: "next" | "previous") => void;
  onSortInitiative: () => void;
  onOpenStatblock: (entity: CombatEntity) => void;
  onGenerateCombatant: (seed: GenerateCombatantSeed) => void;
  onOpenTerrain?: (target?: TerrainZoneRef) => void;
}
```

Responsibilities:

- render rows first;
- show current turn and next turn;
- keep AC/HP/notes visible;
- preserve circular initiative barrel semantics;
- render grouped enemies without hiding individual HP/dead state;
- open statblocks from rows;
- launch generator from row or toolbar;
- surface terrain hazards without becoming a map editor.

Non-responsibilities:

- corpus research;
- LLM calls;
- corpus writes;
- canonical statblock selection;
- generator internals.

### 5.2 StatblockView component

```ts
interface StatblockViewProps {
  source: StatblockSource;
  mode: "compact" | "full";
  onGenerateVariant?: (seed: GenerateCombatantSeed) => void;
  onRevise?: (seed: ReviseStatblockSeed) => void;
}

interface StatblockSource {
  path?: string;
  markdown?: string;
  title?: string;
  provenance?: ProvenanceRef[];
}
```

Responsibilities:

- read/render current corpus markdown statblocks;
- present a compact combat-use layout;
- expose “generate variant” and “revise” actions beside the sheet;
- distinguish persisted corpus statblocks from pending drafts.

### 5.3 GeneratorReview component

```ts
interface GeneratorReviewProps {
  request: StatblockGenerationRequest;
  draft?: StatblockDraft;
  status: "idle" | "researching" | "generating" | "needs_review" | "accepted" | "rejected" | "error";
  onSubmitRequest: (request: StatblockGenerationRequest) => void;
  onEditDraft: (draft: StatblockDraft) => void;
  onAcceptToCombat: (draft: StatblockDraft, options: AddToCombatOptions) => void;
  onPreviewCorpusWrite?: (draft: StatblockDraft, options: CorpusWriteOptions) => void;
}
```

Responsibilities:

- collect generation intent from live combat context;
- display corpus/context provenance;
- show editable draft;
- accept into combat without requiring corpus write;
- optionally preview corpus markdown write through a dedicated safe command.

---

## 6. Data contracts

### 6.1 Combat encounter state

```ts
interface CombatEncounterState {
  schema: "dmb_combat_encounter_state_v1";
  campaignId: string;
  session: number;
  encounterId: string;
  title: string;
  round: number;
  activeTurnEntityId: string | null;
  roundStartEntityId: string | null;
  queueModel: "circular_barrel_v1";
  entities: CombatEntity[];
  groups: CombatGroup[];
  terrain?: CombatTerrainState;
  provenance: ProvenanceRef[];
  updatedAt: string;
}

interface CombatEntity {
  id: string;
  name: string;
  team: "pc" | "ally" | "enemy" | "neutral";
  order: number;
  init: number | null;
  ac: number | null;
  hp: number | null;
  maxHp: number | null;
  tempHp?: number | null;
  defeated: boolean;
  notes: string;
  conditions: string[];
  tags: string[];
  statblockPath?: string | null;
  pendingStatblockMarkdown?: string | null;
  groupKey?: string | null;
  source: "corpus" | "generated_pending" | "manual" | "imported";
}

interface CombatGroup {
  groupKey: string;
  label: string;
  statblockPath?: string | null;
  memberIds: string[];
  collapsed: boolean;
}
```

Key correction from the static harness: active turn should be an id pointer, not an array position. The static save currently uses `turnIndex`; product state should preserve index compatibility on import but normalize to `activeTurnEntityId` for safer reorder/generation behavior.

### 6.2 Generate combatant request

```ts
interface StatblockGenerationRequest {
  schema: "dmb_statblock_generation_request_v1";
  mode: "generate_from_context" | "revise_existing" | "quick_combatant";
  encounterContext: EncounterContext;
  desired: DesiredStatblockShape;
  sourceRefs: StatblockSourceRef[];
  corpusContextBundle?: CorpusContextBundle;
  addToCombatAfterAccept: boolean;
  requestedBy: "human_ui" | "agent";
}

interface EncounterContext {
  campaignId: string;
  session: number;
  encounterId: string;
  sceneSummary: string;
  activeClocks: string[];
  currentRound?: number;
  currentPressure?: string[];
  terrain?: CombatTerrainState;
  existingCombatantSummary: ExistingCombatantSummary[];
}

interface DesiredStatblockShape {
  displayNameHint: string;
  role: "bruiser" | "skirmisher" | "controller" | "artillery" | "support" | "hazard" | "minion" | "boss" | "siege";
  targetCr?: number | null;
  challengeBand?: "trivial" | "easy" | "medium" | "hard" | "deadly" | "clock_monster";
  faction?: string | null;
  constraints: string[];
  mustFeelLike: string[];
  mustNotDo: string[];
}

interface StatblockSourceRef {
  kind: "corpus_statblock" | "combat_entity" | "planning_doc" | "terrain";
  path?: string;
  entityId?: string;
  label: string;
  reason: string;
}
```

### 6.3 Generator output

```ts
interface StatblockDraft {
  schema: "dmb_statblock_draft_v1";
  draftId: string;
  title: string;
  markdown: string;
  parsed: ParsedStatblockSummary;
  combatEntityDefaults: CombatEntityDefaults;
  provenance: ProvenanceRef[];
  reviewWarnings: ReviewWarning[];
  legalityStatus: "unchecked" | "passed" | "warnings" | "failed";
}

interface ParsedStatblockSummary {
  name: string;
  size?: string;
  type?: string;
  alignment?: string;
  ac?: number;
  hp?: number;
  hitDice?: string;
  speed?: string;
  cr?: string;
  keyActions: string[];
}

interface CombatEntityDefaults {
  name: string;
  team: "enemy" | "ally" | "neutral";
  ac: number | null;
  hp: number | null;
  maxHp: number | null;
  tags: string[];
  notes: string;
  statblockPath?: string | null;
  pendingStatblockMarkdown?: string | null;
}
```

### 6.4 Add-to-combat command

Use live-state lane first, not corpus write:

```ts
interface AddGeneratedCombatantPayload {
  encounterId: string;
  draft: StatblockDraft;
  entity: CombatEntityDefaults & {
    id: string;
    init: number | null;
    groupKey?: string | null;
    insertAfterEntityId?: string | null;
  };
}
```

Command:

```text
command_type: add_combat_entity // new
lane: live_state_pin
```

This command does not need a corpus write to be useful. That keeps the first slice narrow and avoids colliding with current statblock write restrictions.

---

## 7. Corpus write/export path

The first integration should support three acceptance levels:

1. **Accept to combat only** — add live entity with pending markdown stored in encounter state.
2. **Export markdown / JSON** — download or copy draft without writing to corpus.
3. **Preview corpus write** — future dedicated command, not current generic writer.

A safe future statblock write command should be explicit:

```text
command_type: preview_statblock_write
lane: prep_note or canon_patch, depending target
```

Required safety gates:

- allowlist only statblock target folders selected by the generator workflow;
- dry-run preview returns full markdown and unified diff;
- confirm token required for commit;
- write result includes file state before/after;
- README/index update is separate, explicit, and previewed;
- generated statblock frontmatter records `source_class`, generator id, input source refs, and review status;
- no arbitrary path writes from the UI.

This is a new writer surface. Do not bypass `src/agent/corpus_writer.py` by adding a generic “write any statblock” hole.

---

## 8. Terrain data shape

Terrain should be combat-state data with optional links to location dossiers or prep artifacts. Keep it compact; do not build a map editor yet.

```ts
interface CombatTerrainState {
  schema: "dmb_combat_terrain_v1";
  encounterId: string;
  summary: string;
  zones: TerrainZone[];
  hazards: TerrainHazard[];
  interactables: TerrainInteractable[];
  dynamicChanges: TerrainChange[];
  sourceRefs: ProvenanceRef[];
}

interface TerrainZone {
  id: string;
  label: string;
  tags: string[]; // choke, high_ground, cover, exposed, difficult, civilian_dense
  description: string;
  mechanics: string[];
}

interface TerrainHazard {
  id: string;
  label: string;
  zoneIds: string[];
  trigger: string;
  effect: string;
  status: "inactive" | "active" | "resolved";
}

interface TerrainInteractable {
  id: string;
  label: string;
  zoneIds: string[];
  actions: string[];
  currentState: string;
}

interface TerrainChange {
  id: string;
  round?: number;
  source: string;
  description: string;
  mechanicalImpact: string;
}
```

Minimum North Reach Gate terrain fixture:

- **North gate throat:** choke, breach pressure, rope lines.
- **Cure line:** civilian-dense, fragile helpers, signal-sensitive.
- **Road bend:** incoming monsters, visibility break.
- **Bell / Shrine line:** morale signal, later target.
- **Cart jam:** movable cover, obstruction, crush risk.

Terrain panel should show a one-screen operational card and allow drilldown. It should also feed generator context: “make a reinforcement that pressures the cart jam without another flier.”

---

## 9. Grounding and generation flow

The generator must be corpus-grounded by process, not by hidden prompt magic.

Recommended flow:

```text
GM clicks Generate combatant
→ UI builds lightweight request from combat + terrain
→ server classifies intent / generation mode
→ retrieval step discovers source statblocks/planning docs
→ context bundle is attached
→ generator produces draft markdown + parsed combat fields
→ review panel shows draft + provenance + warnings
→ GM accepts to combat
→ optional export / preview corpus write
```

For “generate variant from this statblock,” the clicked row supplies a seed reference, but the server should still read the statblock path and include that read in provenance.

For “quick combatant,” use encounter/terrain context, but still retrieve at least one faction/statblock reference when a faction is named. If no grounding source is found, the generator must show `grounding_status: insufficient` and require explicit GM override before accepting to corpus. Accept-to-combat can be more permissive because it is live state, not canon.

---

## 10. Proposed next implementation slice

### Slice name

**Generate reinforcement from combat tracker.**

### User flow

1. GM opens combat module from live-control command board.
2. GM clicks **Generate combatant** from toolbar or enemy group row.
3. Inline generator panel opens with:
   - encounter context;
   - desired CR/role/pressure;
   - optional source statblock ref;
   - terrain pressure selector;
   - checkbox: add to fight after accept.
4. Server returns a draft statblock and combat entity defaults.
5. GM edits/accepts.
6. Accepted draft adds one entity to the circular barrel without changing corpus.
7. GM exports state.

### Why this slice

It tests the highest-value loop without solving the whole command board:

- combat state import/projection;
- row → statblock → generator flow;
- generator → reviewed entity → initiative barrel insertion;
- grouped enemy behavior with generated reinforcement;
- terrain context passing;
- export survival.

---

## 11. Implementation plan

### PR A — extract static combat model into shared domain

Files likely touched:

```text
apps/live-control-ui/src/combat/types.ts
apps/live-control-ui/src/combat/initiativeBarrel.ts
apps/live-control-ui/src/combat/grouping.ts
apps/live-control-ui/src/combat/importStaticMirewardState.ts
apps/live-control-ui/src/combat/*.test.ts
```

Goals:

- normalize static `turnIndex` saves into `activeTurnEntityId`;
- preserve circular barrel behavior;
- preserve virtual Top/Bottom markers as queue nodes;
- preserve grouped enemy and dead bucket semantics;
- test against `mireward-north-reach-gate-combat-state.json`.

### PR B — add read-only CombatModule to live-control UI

Files likely touched:

```text
apps/live-control-ui/src/surface/moduleRegistry.tsx
apps/live-control-ui/src/surface/modules/CombatModule.tsx
apps/live-control-ui/src/surface/modules/CombatModule.test.tsx
evals/c2_live_prep/live/session_23/live_packet.json
evals/c2_live_prep/live/session_23/surface_layout.json
```

Goals:

- display imported encounter state;
- show active turn, next turn, HP/AC/notes;
- open statblock target in InspectorPane or inline preview;
- no generation yet.

### PR C — terrain panel data and rendering

Goals:

- add `CombatTerrainState` fixture for North Reach Gate;
- render compact terrain panel;
- allow selecting terrain pressures for generator request later.

### PR D — generator request/review UI with mock backend

Goals:

- define `StatblockGenerationRequest` / `StatblockDraft` contracts;
- mock generator response in UI tests;
- accept draft to combat local state;
- export modified combat state.

### PR E — real generator adapter after external audit

Prerequisite: open actual StatblockGenerator repo and canvas library.

Goals:

- map real generator service/component to `StatblockGenerationRequest`;
- preserve corpus-grounding bundle;
- parse returned markdown into combat defaults;
- no corpus write yet.

### PR F — safe corpus preview/export, if needed

Goals:

- add dedicated statblock write preview command;
- enforce allowlist and confirm token;
- optionally update README/index through separate preview command.

---

## 12. Verification requirements

Any implementation plan following this design must prove:

1. **Combat state import smoke:** Load `mireward-north-reach-gate-combat-state.json`, preserve round, active actor, HP, dead bucket, groups, and statblock paths.
2. **Initiative barrel regression:** Sorting creates baseline order; manual reorder persists; active turn remains pointer-based; Top/Bottom of Round markers render as queue nodes.
3. **Statblock drilldown:** Clicking a combat row opens the linked markdown statblock without leaving combat context.
4. **Generate reinforcement smoke:** Generate one reinforcement from an existing enemy group, accept it, insert it into the barrel, and export state.
5. **Terrain payload smoke:** Generation request includes at least one terrain pressure from the terrain panel.
6. **Safety smoke:** Accept-to-combat works without corpus write. Corpus write, if exposed, is preview-only unless confirmed through a dedicated command.
7. **Architecture note:** The PR must state what remains in the static prep harness versus what moved into live-control product.

---

## 13. Non-goals

- Do not build a general corpus browser.
- Do not make statblock generation write directly to arbitrary files.
- Do not replace StatblockGenerator before auditing it.
- Do not require the GM to leave combat context to generate/review a combatant.
- Do not turn terrain into a full map editor.
- Do not move all static prep harness functionality at once.

---

## 14. Open questions

1. Where is the actual standalone StatblockGenerator repo / canvas library, and what API or component boundary already exists?
2. Should generated pending statblock markdown live inside combat state, a temp artifact, or a job output artifact before corpus acceptance?
3. Should `add_combat_entity` be a live command immediately, or should the first UI slice keep local-only state like the static harness?
4. Is combat encounter state a new live packet artifact, a projection over event log, or both?
5. Should grouped generated reinforcements inherit the source group key or create a new group?
6. Should legality checks be blocking for corpus write but warning-only for live combat insertion?
7. What is the exact statblock write allowlist policy for generated monsters: Shepherd's Flock hub, campaign prep folder, or a generated-drafts folder first?
