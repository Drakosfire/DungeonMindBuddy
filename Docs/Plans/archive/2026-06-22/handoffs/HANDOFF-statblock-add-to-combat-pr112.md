# HANDOFF — Statblock Add to Combat PR112

**Created:** 2026-06-09  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/statblock-add-to-combat-pr112`  
**Depends on:** PR #111 / `36c8c8fbe01988fbe91f81166ab09ffa8072c74c` — Add read-only generated Statblock View  
**Primary designs:**
- `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`
- `Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md`
**Previous handoffs:**
- `Docs/Plans/HANDOFF-statblock-lifecycle-seam-pr1.md`
- `Docs/Plans/HANDOFF-statblock-lifecycle-command-smoke-pr2.md`
- `Docs/Plans/HANDOFF-statblock-workbench-readonly-pr3.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-workbench-draft-storage-pr107.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-corpus-promotion-preview-pr108.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-corpus-confirmed-write-pr109.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-retrieval-activation-pr110.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-view-readonly-pr111.md`
**Mode:** First combat mutation slice. Add corpus-backed generated statblocks to a live-session current combat state using `combat_defaults`. Do not build the full combat tracker rewrite yet.

---

## 0. Copyable task prompt

```markdown
You are implementing Statblock Add to Combat PR112 in `Drakosfire/DungeonMindBuddy`.

Read first:

- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-add-to-combat-pr112.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-view-readonly-pr111.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-retrieval-activation-pr110.md`
- `Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md`
- `apps/live_control_server/services/statblock_view.py`
- `apps/live_control_server/session_store.py`
- `evals/c2_live_prep/mireward-prep/saves/mireward-north-reach-gate-combat-state.json`

Goal: enable Add to Combat for corpus-backed generated statblocks.

PR111 added a read-only Statblock View. PR112 should add the first narrow combat mutation path:

- a file-backed current combat state under the live session directory;
- a server endpoint to add a generated statblock as one or more combat entities;
- UI affordances in Statblock View, and optionally Workbench, to add a corpus-backed generated statblock to current combat;
- a small current-combat roster/readback so the user can see that the entity was added.

Use `combat_defaults` from the stored artifact/detail response as the hydration contract. Do not parse markdown to derive AC/HP/actions.

Do not build the full combat tracker rewrite in this PR. Do not add turn advancement, damage/healing, conditions editing, sorting, initiative barrel UI, generation, corpus writes, retrieval activation, or planning-mode task flow. This slice only proves: corpus-backed generated statblock → live current combat entity.
```

---

## 1. Re-anchor

Current ladder:

```text
Producer API live ✅
Buddy v2 seam ✅
Lifecycle command facade ✅
Read-only Workbench ✅
Interactive mock Workbench ✅
Persistent non-corpus draft storage ✅
Corpus promotion preview ✅
Confirmed corpus write ✅
Retrieval activation/verification ✅
Statblock View ✅
Add to combat ❌
Planning Mode generation tasks ❌
```

PR #111 added:

```text
corpus-backed generated statblocks
→ list/read API
→ read-only Statblock View module
→ Add to Combat disabled
```

PR #112 should add:

```text
corpus-backed generated statblock detail
→ Add to Combat request
→ current combat state file
→ combat entity hydrated from combat_defaults
→ visible current-combat roster/readback
```

This PR introduces a combat mutation, but only the smallest safe one.

---

## 2. Product intent

The GM should be able to generate, store, promote, verify, view, and finally place a generated monster into the current combat.

Target user-visible flow:

```text
Open Statblock View
→ select a corpus-backed generated statblock
→ choose Add to current combat
→ choose team/count/name/initiative defaults
→ confirm Add
→ see result: entity/entities added to current combat
→ current combat roster shows the added entity with AC/HP/statblock link/provenance
```

This is the first time the lifecycle produces a table-usable combat entity.

---

## 3. Design boundary

### PR112 does

- add a minimal file-backed current combat state;
- add a read endpoint for current combat;
- add an Add Generated Statblock to Combat endpoint;
- hydrate combat entities from `combat_defaults` and corpus metadata;
- support adding one or more copies;
- persist the resulting combat state under the live session directory;
- optionally append a small audit event if existing event schema accepts it cleanly;
- enable Add to Combat in Statblock View;
- optionally enable the same action in Workbench when the draft has a corpus-backed/promoted artifact id;
- show current combat roster/readback somewhere visible.

### PR112 does not

- build the full CombatModule from the design doc;
- replace the static Mireward combat tracker;
- implement initiative sorting/turn advancement;
- implement damage/heal/conditions;
- generate statblocks;
- write corpus;
- activate retrieval;
- verify retrieval;
- update the base live packet;
- mutate markdown corpus;
- add combat terrain/map UI;
- add planning-mode task integration.

---

## 4. Combat state source of truth

There is not yet a first-class live-control combat state in the repo. The current proof shape is the static Mireward save:

```text
evals/c2_live_prep/mireward-prep/saves/mireward-north-reach-gate-combat-state.json
```

It proves the minimum useful fields:

```text
round
turn pointer / turnIndex compatibility
entities[]
  id
  name
  team
  order
  init
  hp
  maxHp
  notes
  defeated
  statblockPath
```

PR112 should introduce the live-session version in a deliberately small form.

Recommended state file:

```text
<live_session_dir>/combat/current_combat.json
```

Schema:

```json
{
  "schema": "dmb_combat_encounter_state_v1",
  "campaign_id": "longmont-c2",
  "session": 22,
  "encounter_id": "current-combat",
  "title": "Current Combat",
  "round": 1,
  "active_turn_entity_id": null,
  "round_start_entity_id": null,
  "queue_model": "circular_barrel_v1",
  "entities": [],
  "groups": [],
  "provenance": [],
  "updated_at": "2026-06-09T...Z"
}
```

Do not import or rewrite the static Mireward save in this PR. Use it as a shape reference only.

---

## 5. Backend service design

Add:

```text
apps/live_control_server/services/combat_state.py
```

or, if preferred for this slice:

```text
apps/live_control_server/services/statblock_combat.py
```

Preference: add both only if useful:

```text
combat_state.py             # generic current combat store/models
statblock_combat.py         # generated-statblock → combat entity mapping
```

Keep code small. A single `combat_state.py` is acceptable for PR112.

### 5.1 Models

Suggested models:

```python
CombatTeam = Literal["pc", "ally", "enemy", "neutral"]

class CombatEntity(BaseModel):
    id: str
    name: str
    team: CombatTeam = "enemy"
    order: int
    init: int | None = None
    ac: int | str | None = None
    hp: int | str | None = None
    max_hp: int | str | None = None
    temp_hp: int | None = None
    defeated: bool = False
    notes: str = ""
    conditions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    statblock_path: str | None = None
    statblock_artifact_id: str | None = None
    statblock_title: str | None = None
    corpus_fingerprint: str | None = None
    source: Literal["corpus", "generated_pending", "manual", "imported"] = "corpus"
    provenance: list[dict[str, Any]] = Field(default_factory=list)

class CombatEncounterState(BaseModel):
    schema: Literal["dmb_combat_encounter_state_v1"] = "dmb_combat_encounter_state_v1"
    campaign_id: str
    session: int
    encounter_id: str = "current-combat"
    title: str = "Current Combat"
    round: int = 1
    active_turn_entity_id: str | None = None
    round_start_entity_id: str | None = None
    queue_model: Literal["circular_barrel_v1"] = "circular_barrel_v1"
    entities: list[CombatEntity] = Field(default_factory=list)
    groups: list[dict[str, Any]] = Field(default_factory=list)
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: str

class AddGeneratedStatblockCombatRequest(BaseModel):
    team: CombatTeam = "enemy"
    count: int = Field(default=1, ge=1, le=20)
    name_override: str | None = None
    initiative: int | None = None
    insert_after_entity_id: str | None = None
    group_key: str | None = None
    notes: str | None = None
    hp_override: int | None = Field(default=None, ge=0)
    max_hp_override: int | None = Field(default=None, ge=0)

class AddGeneratedStatblockCombatResponse(BaseModel):
    schema_version: Literal["dmb_add_generated_statblock_to_combat_v1"] = "dmb_add_generated_statblock_to_combat_v1"
    added_entities: list[CombatEntity]
    encounter: CombatEncounterState
    diagnostics: list[str] = Field(default_factory=list)
```

Use snake_case in server models. Frontend can keep snake_case to avoid mapping churn.

### 5.2 Store helpers

Suggested helpers:

```python
COMBAT_REL_PATH = "combat/current_combat.json"

def combat_state_path(base: Path) -> Path: ...

def load_or_initialize_current_combat(*, base: Path, packet: dict[str, Any]) -> CombatEncounterState: ...

def write_current_combat(*, base: Path, encounter: CombatEncounterState) -> None: ...

def add_generated_statblock_to_combat(
    *,
    base: Path,
    root: Path,
    packet: dict[str, Any],
    artifact_id: str,
    request: AddGeneratedStatblockCombatRequest,
) -> AddGeneratedStatblockCombatResponse: ...
```

Use `write_json(...)` for atomic JSON writes.

---

## 6. Hydration rules

Use `read_generated_statblock(...)` from `statblock_view.py` as the source of truth.

Required preconditions:

- stored draft exists;
- artifact is corpus-promoted;
- corpus file exists;
- generated statblock detail can be read;
- `combat_defaults` present.

Do not require retrieval verified for PR112. A corpus-backed statblock can be added to combat even if retrieval activation is pending. However, include retrieval status in provenance so the GM can see whether it was verified.

### 6.1 Entity defaults

From detail:

```text
name = request.name_override or combat_defaults.name or detail.title
team = request.team or enemy
ac = combat_defaults.armor_class
hp = request.hp_override or combat_defaults.hit_points
max_hp = request.max_hp_override or combat_defaults.hit_points
init = request.initiative or null
notes = request.notes or generated default note
statblock_path = detail.corpus_display_path or corpus/eldyrwild-markdown/<corpus_relpath>
statblock_artifact_id = detail.artifact_id
statblock_title = detail.title
corpus_fingerprint = detail.corpus_file_fingerprint
tags include generated_statblock, corpus_backed, statblock_view
source = corpus
```

Default note suggestion:

```text
Added from generated Statblock View; review warnings: <count>; retrieval: <status or not activated>.
```

### 6.2 ID strategy

Generate stable-safe unique IDs, not title-only IDs.

Suggested:

```text
<slug(title)>-<short uuid>
```

For count > 1, names should be distinct:

```text
Obsidian Thornling A
Obsidian Thornling B
Obsidian Thornling C
```

IDs can be:

```text
obsidian-thornling-a-7f3a1c
obsidian-thornling-b-9c22aa
```

Do not overwrite existing entity IDs.

### 6.3 Order / insertion

For PR112 keep it simple:

- default append to end with increasing `order`;
- if `insert_after_entity_id` is provided and exists, insert after it and re-number all `order` fields;
- do not sort initiative automatically;
- preserve existing `active_turn_entity_id` if present.

### 6.4 Grouping

If `count > 1`, set `group_key` to request group key or generated group key:

```text
generated-<artifact_id>-<short uuid>
```

Add/update a simple group row:

```json
{
  "group_key": "generated-statblock-view-test-a1b2c3",
  "label": "Geomantic Drake Juvenile",
  "statblock_path": "corpus/eldyrwild-markdown/...",
  "member_ids": ["...", "..."],
  "collapsed": false
}
```

If count == 1, group is optional. Keep it absent unless useful.

---

## 7. Backend endpoints

Add in `apps/live_control_server/routes/live.py`:

### 7.1 Read current combat

```text
GET /api/live/combat/current
```

Response: `CombatEncounterState`.

This creates no file unless you choose lazy initialization. Preference: read returns initialized state but only writes when mutation occurs.

### 7.2 Add generated statblock to current combat

```text
POST /api/live/statblocks/view/generated/{artifact_id}/combat/add
```

Request: `AddGeneratedStatblockCombatRequest`.

Response: `AddGeneratedStatblockCombatResponse`.

This endpoint writes only:

```text
<live_session_dir>/combat/current_combat.json
```

Optional audit event:

If existing event schema accepts a small operational event cleanly, append one event row. If schema friction appears, skip event append in PR112 and document that `current_combat.json` is the mutation record for now.

Do not queue jobs.

### 7.3 Optional Workbench endpoint

Do not add a separate Workbench combat endpoint unless necessary. The Workbench can call the same generated statblock endpoint once it has a corpus-backed `artifact_id`.

---

## 8. Frontend API/types

Update:

```text
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/liveApi.test.ts
```

Suggested types:

```ts
export type CombatTeam = "pc" | "ally" | "enemy" | "neutral";

export interface CombatEntity {
  id: string;
  name: string;
  team: CombatTeam;
  order: number;
  init?: number | null;
  ac?: number | string | null;
  hp?: number | string | null;
  max_hp?: number | string | null;
  temp_hp?: number | null;
  defeated: boolean;
  notes: string;
  conditions: string[];
  tags: string[];
  statblock_path?: string | null;
  statblock_artifact_id?: string | null;
  statblock_title?: string | null;
  corpus_fingerprint?: string | null;
  source: "corpus" | "generated_pending" | "manual" | "imported";
  provenance: Array<Record<string, unknown>>;
}

export interface CombatEncounterState {
  schema: "dmb_combat_encounter_state_v1";
  campaign_id: string;
  session: number;
  encounter_id: string;
  title: string;
  round: number;
  active_turn_entity_id?: string | null;
  round_start_entity_id?: string | null;
  queue_model: "circular_barrel_v1";
  entities: CombatEntity[];
  groups: Array<Record<string, unknown>>;
  provenance: Array<Record<string, unknown>>;
  updated_at: string;
}

export interface AddGeneratedStatblockCombatRequest {
  team?: CombatTeam;
  count?: number;
  name_override?: string | null;
  initiative?: number | null;
  insert_after_entity_id?: string | null;
  group_key?: string | null;
  notes?: string | null;
  hp_override?: number | null;
  max_hp_override?: number | null;
}

export interface AddGeneratedStatblockCombatResponse {
  schema_version: "dmb_add_generated_statblock_to_combat_v1";
  added_entities: CombatEntity[];
  encounter: CombatEncounterState;
  diagnostics: string[];
}
```

API helpers:

```ts
export async function getCurrentCombat(): Promise<CombatEncounterState> { ... }

export async function addGeneratedStatblockToCombat(
  artifactId: string,
  request: AddGeneratedStatblockCombatRequest,
): Promise<AddGeneratedStatblockCombatResponse> { ... }
```

Use `encodeURIComponent(artifactId)`.

---

## 9. Frontend UI design

### 9.1 Statblock View

Update:

```text
apps/live-control-ui/src/surface/modules/StatblockViewModule.tsx
```

Change Add to current combat from disabled to enabled when detail is loaded.

Add a small Add panel:

```text
Add to current combat
Team: enemy/ally/neutral
Count: 1
Initiative: optional
Name override: optional
Notes: optional
[Add to current combat]
```

Keep this small. Do not build a full encounter form.

On success:

- show added entity names;
- show current combat entity count;
- optionally show latest added entity summary;
- refresh current combat readback if displayed.

On error:

- preserve selected statblock;
- show safe error.

### 9.2 Workbench optional bridge

Optional if low-cost:

- In Workbench, if the current artifact has `corpus_status === "promotion_confirmed"`, show a compact Add to Combat button that calls the same endpoint.
- If it does not have a corpus-backed artifact id, keep Add to Combat disabled with reason:

```text
Promote to corpus before adding to combat from Workbench.
```

If this adds too much UI complexity, skip Workbench and leave PR112 as Statblock View only. Statblock View is the intended consumer surface.

### 9.3 Minimal current combat readback

Add one of these:

Option A — inside Statblock View:

```text
Current combat snapshot
- Round
- Entity count
- Latest added entities
```

Option B — separate optional module:

```text
apps/live-control-ui/src/surface/modules/CombatRosterModule.tsx
module_id: combat_roster
```

Recommendation for PR112: **Option A**. A full Combat module should be PR113 or later.

Do not register a new combat module unless the implementation remains very small.

---

## 10. Backend tests

Add:

```text
tests/test_statblock_add_to_combat.py
```

Use temp live session and temp corpus roots. Do not write to checked-in combat/state fixtures.

### 10.1 Read current combat initializes empty state

Call:

```text
GET /api/live/combat/current
```

Assert:

- schema `dmb_combat_encounter_state_v1`;
- campaign/session from live packet;
- entities empty if no file exists;
- no file written if following read-without-write preference.

### 10.2 Add generated statblock creates combat file

Setup:

- store draft;
- promote corpus file;
- optionally retrieval verify;
- call add endpoint.

Assert:

- status 200;
- `current_combat.json` exists;
- one entity added;
- entity name from `combat_defaults.name` or title;
- AC/HP/max_hp from `combat_defaults`;
- statblock path equals corpus display path;
- artifact id/fingerprint/provenance present;
- source is `corpus`;
- response encounter includes entity.

### 10.3 Add multiple copies

Request `count: 3`.

Assert:

- three entities added;
- names are distinct A/B/C;
- ids unique;
- order contiguous;
- group row created or omitted according to implementation; if created, member ids correct.

### 10.4 Insert after existing entity

Add first entity, then add second with `insert_after_entity_id` first id.

Assert order re-numbering is stable.

### 10.5 Overrides

Request:

```json
{
  "team": "ally",
  "initiative": 17,
  "hp_override": 42,
  "max_hp_override": 42,
  "notes": "Arrives from south gate."
}
```

Assert overrides appear.

### 10.6 Reject invalid states

Cases:

- unknown artifact id → 404;
- unsafe artifact id → 422;
- non-promoted draft → 409;
- missing corpus file → 409;
- count > 20 → 422;
- invalid team → 422.

### 10.7 No unrelated mutation

For add endpoint, assert only allowed files change:

```text
combat/current_combat.json
optional event_log.jsonl if implemented
```

No changes to:

```text
corpus markdown file
statblock draft record
retrieval overlay
surface_layout.json
live_packet.json
job_queue.jsonl
```

### 10.8 No secret exposure

Set fake env:

```text
DUNGEONBUDDY_INTERNAL_API_KEY=super-secret-test-key
DUNGEONMIND_SERVER_URL=https://example.invalid
```

Call read/add.

Assert responses do not contain:

```text
super-secret-test-key
DUNGEONBUDDY_INTERNAL_API_KEY
DUNGEONMIND_SERVER_URL
X-DungeonBuddy-Internal-Key
```

---

## 11. Frontend tests

Update:

```text
apps/live-control-ui/src/api/liveApi.test.ts
apps/live-control-ui/src/surface/modules/StatblockViewModule.test.tsx
```

### 11.1 API helper tests

Assert:

- `getCurrentCombat()` GETs `/api/live/combat/current`;
- `addGeneratedStatblockToCombat(id, request)` POSTs to encoded `/api/live/statblocks/view/generated/{artifact_id}/combat/add` with JSON body.

### 11.2 Statblock View tests

Add tests:

1. Add panel appears when detail loads.
2. Default Add call sends `{ team: "enemy", count: 1 }` or equivalent defaults.
3. Changing team/count/initiative/notes sends request payload.
4. Success shows added entity names and current combat count.
5. Failure keeps statblock detail visible and shows safe error.
6. Add to combat is not offered when no detail is selected.

No live network.

---

## 12. Manual smoke

Backend:

```bash
uv run uvicorn apps.live_control_server.main:app --reload
```

After creating a corpus-backed generated statblock through PR109/PR111 flow:

```bash
ARTIFACT_ID="<artifact id>"

curl -s http://127.0.0.1:8000/api/live/combat/current | jq

curl -s \
  -X POST \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:8000/api/live/statblocks/view/generated/${ARTIFACT_ID}/combat/add" \
  -d '{"team":"enemy","count":1,"initiative":null}' \
  | jq

curl -s http://127.0.0.1:8000/api/live/combat/current | jq
```

Frontend:

```bash
cd apps/live-control-ui
npm run dev
```

Verify:

```text
Enable Statblock View.
Select generated statblock.
Add to current combat.
Success message appears.
Current combat readback includes the new entity.
No corpus/statblock draft/retrieval metadata changes occur.
```

---

## 13. Testing commands

Suggested backend:

```bash
uv run pytest \
  tests/test_statblock_add_to_combat.py \
  tests/test_statblock_view.py \
  tests/test_live_session_bootstrap.py \
  -q
```

Suggested frontend:

```bash
cd apps/live-control-ui
npm test -- \
  src/surface/modules/StatblockViewModule.test.tsx \
  src/api/liveApi.test.ts
```

Typecheck:

```bash
cd apps/live-control-ui
npx tsc -p tsconfig.app.json --noEmit
```

Lint/format:

```bash
uv run ruff check \
  apps/live_control_server/services/combat_state.py \
  apps/live_control_server/services/statblock_view.py \
  apps/live_control_server/routes/live.py \
  tests/test_statblock_add_to_combat.py

git diff --check
```

If `npm run build` remains blocked by the known `@types/node` environment/config issue, document the caveat in the PR body.

---

## 14. Acceptance criteria

The PR is ready when:

- Current combat state model/service exists.
- `GET /api/live/combat/current` exists.
- `POST /api/live/statblocks/view/generated/{artifact_id}/combat/add` exists.
- Add endpoint uses `read_generated_statblock(...)` / stored detail, not markdown parsing.
- Entity hydration uses `combat_defaults` for AC/HP/name/action-related notes.
- Added entity includes corpus path, artifact id, title, fingerprint, source, and provenance.
- Add endpoint writes only current combat state, plus optional audit event if schema-safe.
- No corpus/statblock draft/retrieval overlay mutation occurs.
- Statblock View UI enables Add to Combat for loaded generated statblocks.
- UI shows success/error states and current combat readback.
- Full combat tracker behavior remains out of scope.
- Focused backend/frontend tests pass.

---

## 15. Suggested PR description

```markdown
### Motivation

PR #111 added a read-only corpus-backed Statblock View. This PR adds the first narrow combat mutation: adding a corpus-backed generated statblock to a live-session current combat state using the artifact's `combat_defaults`.

### Description

- Added a minimal file-backed current combat state under `combat/current_combat.json`.
- Added current combat read endpoint.
- Added Add Generated Statblock to Combat endpoint under `/api/live/statblocks/view/generated/{artifact_id}/combat/add`.
- Hydrated combat entities from `combat_defaults`, corpus metadata, artifact id, corpus fingerprint, and provenance.
- Supported count/team/initiative/name/HP/notes overrides with bounded validation.
- Updated Statblock View with an Add to current combat panel and current combat readback.
- Kept full combat tracker behavior, turn advancement, damage/healing, generation, corpus writes, retrieval activation, and planning-mode integration out of scope.
- Added backend/frontend tests proving correct entity hydration and narrow mutation boundaries.

### Testing

- `uv run pytest tests/test_statblock_add_to_combat.py tests/test_statblock_view.py tests/test_live_session_bootstrap.py -q`
- `cd apps/live-control-ui && npm test -- src/surface/modules/StatblockViewModule.test.tsx src/api/liveApi.test.ts`
- `cd apps/live-control-ui && npx tsc -p tsconfig.app.json --noEmit`
- `uv run ruff check apps/live_control_server/services/combat_state.py apps/live_control_server/services/statblock_view.py apps/live_control_server/routes/live.py tests/test_statblock_add_to_combat.py`
- `git diff --check`
```

---

## 16. Design reminder

This PR proves the final lifecycle handoff into combat state. It is not the full combat tracker.

The ladder after PR112 should be:

```text
API-backed ✅
Commandable ✅
Visible ✅
Interactive ✅
Persistent draft storage ✅
Corpus promotion preview ✅
Confirmed corpus write ✅
Retrieval activation/verification ✅
Statblock View ✅
Add to combat ⏭️ this PR
Planning-mode-integrated ❌
```

The next combat-focused PR after this should be a proper Combat Roster/Tracker module over `combat/current_combat.json`: initiative barrel, HP edits, damage/heal, conditions, notes, turn advancement, and statblock drilldown.
