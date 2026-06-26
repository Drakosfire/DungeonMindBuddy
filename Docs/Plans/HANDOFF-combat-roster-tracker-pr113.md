# HANDOFF — Combat Roster / Tracker PR113

**Created:** 2026-06-10  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/combat-roster-tracker-pr113`  
**Depends on:** PR #112 / `e82e75e7fb1e07e6a287b0d0dc90454b009f2ae6` — Add generated statblocks to current combat  
**Primary designs:**
- `Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md`
- `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`
**Previous handoffs:**
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-add-to-combat-pr112.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-view-readonly-pr111.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-retrieval-activation-pr110.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-corpus-confirmed-write-pr109.md`

**Mode:** First real combat-control surface. Build a compact Combat Roster / Tracker module over `combat/current_combat.json`. Keep it focused on table operations: roster visibility, HP changes, notes/conditions/defeated state, initiative order, and turn pointer. Do not add generation, corpus writes, planning tasks, or terrain/map systems.

---

## 0. Copyable task prompt

```markdown
You are implementing Combat Roster / Tracker PR113 in `Drakosfire/DungeonMindBuddy`.

Read first:

- `Docs/Plans/HANDOFF-combat-roster-tracker-pr113.md`
- `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-statblock-add-to-combat-pr112.md`
- `Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md`
- `apps/live_control_server/services/combat_state.py`
- `apps/live-control-ui/src/surface/moduleRegistry.tsx`
- `apps/live-control-ui/src/surface/modules/StatblockViewModule.tsx`

Goal: build the first proper Combat Roster / Tracker module over the current combat state introduced in PR112.

PR112 proved generated statblocks can be added to `combat/current_combat.json`. PR113 should make that state usable during play:

- show current combat roster;
- show active/next actor;
- sort by initiative;
- advance/rewind turn pointer;
- apply damage/healing;
- edit HP/temp HP/initiative/notes/conditions/defeated;
- expose statblock path/artifact links as read-only drilldown affordances;
- persist all changes to `combat/current_combat.json` only.

Add a `CombatRosterModule` registered as optional and disabled-by-default in the live surface. Add focused backend endpoints for combat patch/delta/turn/sort operations. Use the existing `CombatEncounterState` / `CombatEntity` model from `combat_state.py`.

Do not generate statblocks. Do not write corpus. Do not activate retrieval. Do not add planning-mode tasks. Do not build terrain/map UI. Do not import the static Mireward combat page wholesale. This PR should productize the smallest durable live combat loop.
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
Add to combat ✅
Combat Roster / Tracker ❌
Planning Mode generation tasks ❌
```

PR #112 added:

```text
corpus-backed generated statblock detail
→ Add to Combat request
→ combat/current_combat.json
→ entity hydrated from combat_defaults
→ small readback inside Statblock View
```

PR #113 should add:

```text
combat/current_combat.json
→ dedicated Combat Roster module
→ HP/damage/heal/notes/conditions/defeated controls
→ initiative sort + active turn pointer
→ persisted current combat state
```

This is the first real live combat operation surface.

---

## 2. Product intent

The static Mireward combat tracker proved the shape that mattered: the GM needs a fast table-facing combat surface where HP, initiative, current actor, notes, and statblock links are always visible.

PR113 should not rewrite the whole static page. It should lift the useful operational loop into live-control architecture.

Target user-visible flow:

```text
Open command board
→ enable Combat Roster
→ see current combatants added by Statblock View
→ sort initiative
→ set active actor
→ advance turn
→ apply damage/heal
→ mark defeated
→ update notes/conditions
→ persist to combat/current_combat.json
```

This makes the generated-statblock pipeline usable at the table.

---

## 3. Design boundary

### PR113 does

- extend backend combat service with patch/delta/turn/sort operations;
- add focused live-control endpoints for combat state mutation;
- add a `CombatRosterModule` frontend surface;
- register the module as optional/disabled-by-default;
- show roster rows with visible AC/HP/init/team/conditions/notes/defeated/status;
- show active actor and next actor;
- support sort by initiative;
- support next/previous turn;
- support direct entity patch for initiative, HP, temp HP, notes, conditions, defeated;
- support damage/healing delta controls;
- persist only `combat/current_combat.json`;
- add focused backend/frontend tests.

### PR113 does not

- generate statblocks;
- add statblocks to combat beyond the existing PR112 endpoint;
- write corpus;
- activate retrieval;
- alter stored draft records;
- edit statblock markdown;
- build a map/terrain system;
- build a full encounter builder;
- import/export static combat state;
- implement multi-encounter management;
- implement encounter templates;
- build planning-mode task flow;
- redesign the entire command board.

---

## 4. Existing state contract to build on

Current combat state lives at:

```text
<live_session_dir>/combat/current_combat.json
```

Current models are in:

```text
apps/live_control_server/services/combat_state.py
```

Key shape:

```python
class CombatEncounterState(BaseModel):
    schema: Literal["dmb_combat_encounter_state_v1"]
    campaign_id: str
    session: int
    encounter_id: str
    title: str
    round: int
    active_turn_entity_id: str | None
    round_start_entity_id: str | None
    queue_model: Literal["circular_barrel_v1"]
    entities: list[CombatEntity]
    groups: list[dict[str, Any]]
    provenance: list[dict[str, Any]]
    updated_at: str
```

Entity shape:

```python
class CombatEntity(BaseModel):
    id: str
    name: str
    team: "pc" | "ally" | "enemy" | "neutral"
    order: int
    init: int | None
    ac: int | str | None
    hp: int | str | None
    max_hp: int | str | None
    temp_hp: int | None
    defeated: bool
    notes: str
    conditions: list[str]
    tags: list[str]
    statblock_path: str | None
    statblock_artifact_id: str | None
    statblock_title: str | None
    corpus_fingerprint: str | None
    source: "corpus" | "generated_pending" | "manual" | "imported"
    provenance: list[dict[str, Any]]
```

Do not change the schema name unless unavoidable. Add new optional fields only if needed.

---

## 5. Backend service extensions

Extend:

```text
apps/live_control_server/services/combat_state.py
```

### 5.1 New request/response models

Suggested models:

```python
class CombatEntityPatchRequest(BaseModel):
    name: str | None = None
    team: CombatTeam | None = None
    init: int | None = None
    ac: int | str | None = None
    hp: int | str | None = None
    max_hp: int | str | None = None
    temp_hp: int | None = Field(default=None, ge=0)
    defeated: bool | None = None
    notes: str | None = None
    conditions: list[str] | None = None
    tags: list[str] | None = None

class CombatEntityDeltaRequest(BaseModel):
    amount: int = Field(gt=0, le=999)
    mode: Literal["damage", "heal", "temp_hp"]
    note: str | None = None

class CombatTurnAdvanceRequest(BaseModel):
    direction: Literal["next", "previous"] = "next"

class CombatSortInitiativeRequest(BaseModel):
    descending: bool = True
    place_nulls_last: bool = True
    set_active_to_first: bool = True

class CombatOperationResponse(BaseModel):
    schema_version: Literal["dmb_combat_operation_v1"] = "dmb_combat_operation_v1"
    encounter: CombatEncounterState
    changed_entity_ids: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
```

Use Pydantic validation. Keep request models small.

### 5.2 Helper functions

Add helpers:

```python
def patch_combat_entity(
    *,
    base: Path,
    packet: dict[str, Any],
    entity_id: str,
    patch: CombatEntityPatchRequest,
) -> CombatOperationResponse: ...


def apply_combat_entity_delta(
    *,
    base: Path,
    packet: dict[str, Any],
    entity_id: str,
    delta: CombatEntityDeltaRequest,
) -> CombatOperationResponse: ...


def sort_combat_by_initiative(
    *,
    base: Path,
    packet: dict[str, Any],
    request: CombatSortInitiativeRequest,
) -> CombatOperationResponse: ...


def advance_combat_turn(
    *,
    base: Path,
    packet: dict[str, Any],
    request: CombatTurnAdvanceRequest,
) -> CombatOperationResponse: ...
```

Add small error class if useful:

```python
class CombatStateError(Exception):
    status_code: int = 409
```

or use explicit errors:

```python
class CombatEntityNotFoundError(CombatStateError): status_code = 404
class CombatStateValidationError(CombatStateError): status_code = 422
```

---

## 6. Backend behavior rules

### 6.1 Patch entity

Patch only provided fields. Do not interpret omitted fields as null.

Rules:

- `conditions` replaces the full condition list;
- trim blank conditions and dedupe case-insensitively;
- `tags` replaces full tag list, but preserve system lineage tags unless intentionally overridden;
- if `hp <= 0`, do not automatically mark defeated unless you choose to add `auto_mark_defeated` later. For PR113, keep defeated explicit.

### 6.2 Damage/heal/temp HP delta

Use numeric values only when current HP values are numeric.

Rules:

- `damage`: subtract from temp HP first, then HP; clamp HP at 0;
- `heal`: add to HP; clamp at max HP when max HP is numeric;
- `temp_hp`: set temp HP to max(current temp HP, amount), following 5e-style temp HP replacement;
- if `hp` or `max_hp` are non-numeric strings, return 409 with safe message: `entity hp is not numeric`;
- append note text to entity notes only if request.note is present;
- do not auto-toggle defeated.

### 6.3 Initiative sort

Sort entities by:

```text
init descending
then team/order stable fallback
then existing order
```

Null initiative goes last when `place_nulls_last = true`.

After sorting:

- renumber contiguous `order` starting at 1;
- if `set_active_to_first`, set `active_turn_entity_id` and `round_start_entity_id` to first entity id;
- preserve round number.

### 6.4 Turn advance

Use the current `entities` array order as the circular barrel.

Rules:

- if no entities, active remains null;
- if active is null, set active to first entity for `next`, last for `previous`;
- next advances one slot, wrapping;
- previous rewinds one slot, wrapping;
- increment `round` only when advancing next from last to first;
- decrement `round` only when rewinding previous from first to last, clamped at 1;
- preserve defeated entities in the barrel for PR113. Skipping defeated can be a later option.

### 6.5 Persistence boundary

Every mutation writes only:

```text
<live_session_dir>/combat/current_combat.json
```

No event append in PR113 unless it is already trivial and schema-safe. Prefer no event append for this slice to keep mutation assertions clean.

Do not touch:

```text
live_packet.json
surface_layout.json
event_log.jsonl
job_queue.jsonl
statblock_drafts/
statblock_retrieval/
corpus/
```

---

## 7. Live-control endpoints

Existing from PR112:

```text
GET /api/live/combat/current
POST /api/live/statblocks/view/generated/{artifact_id}/combat/add
```

Add:

```text
PATCH /api/live/combat/current/entities/{entity_id}
POST /api/live/combat/current/entities/{entity_id}/delta
POST /api/live/combat/current/turn
POST /api/live/combat/current/sort-initiative
```

Optional if trivial:

```text
POST /api/live/combat/current/reset-empty
```

Recommendation: skip reset in PR113 unless tests/UI need it.

### 7.1 Error mapping

Recommended:

```text
404 entity not found
409 invalid operation for current state, e.g. non-numeric HP delta
422 request validation error
500 unexpected combat operation failure
```

Keep errors safe. No host absolute paths. No secret strings.

---

## 8. Frontend API/types

Update:

```text
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/liveApi.test.ts
```

Suggested TypeScript types:

```ts
export interface CombatEntityPatchRequest {
  name?: string | null;
  team?: CombatTeam | null;
  init?: number | null;
  ac?: number | string | null;
  hp?: number | string | null;
  max_hp?: number | string | null;
  temp_hp?: number | null;
  defeated?: boolean | null;
  notes?: string | null;
  conditions?: string[] | null;
  tags?: string[] | null;
}

export interface CombatEntityDeltaRequest {
  amount: number;
  mode: "damage" | "heal" | "temp_hp";
  note?: string | null;
}

export interface CombatTurnAdvanceRequest {
  direction: "next" | "previous";
}

export interface CombatSortInitiativeRequest {
  descending?: boolean;
  place_nulls_last?: boolean;
  set_active_to_first?: boolean;
}

export interface CombatOperationResponse {
  schema_version: "dmb_combat_operation_v1";
  encounter: CombatEncounterState;
  changed_entity_ids: string[];
  diagnostics: string[];
}
```

API helpers:

```ts
export async function patchCombatEntity(entityId: string, request: CombatEntityPatchRequest): Promise<CombatOperationResponse> { ... }
export async function applyCombatEntityDelta(entityId: string, request: CombatEntityDeltaRequest): Promise<CombatOperationResponse> { ... }
export async function advanceCombatTurn(request: CombatTurnAdvanceRequest): Promise<CombatOperationResponse> { ... }
export async function sortCombatInitiative(request: CombatSortInitiativeRequest = {}): Promise<CombatOperationResponse> { ... }
```

Use `encodeURIComponent(entityId)`.

---

## 9. Frontend module design

Add:

```text
apps/live-control-ui/src/surface/modules/CombatRosterModule.tsx
```

Register in:

```text
apps/live-control-ui/src/surface/moduleRegistry.tsx
src/live_play/session_bootstrap.py
```

Suggested module id:

```text
combat_roster
```

Catalog entry:

```json
{
  "module_id": "combat_roster",
  "title": "Combat Roster",
  "default_slot": "main",
  "required": false,
  "enabled_by_default": false,
  "description": "Live current-combat roster, HP controls, and turn pointer over combat/current_combat.json.",
  "config_schema": null
}
```

Layout entry should be disabled by default and near Statblock View:

```json
{"module_id":"combat_roster","slot":"main","order":4,"enabled":false,"collapsed":false,"size":"1fr","config":{}}
```

Do not remove the Statblock View readback. It is still useful, but the roster becomes the main combat-control surface.

---

## 10. Combat Roster UI behavior

### 10.1 Initial load

On mount:

```text
GET /api/live/combat/current
```

Show:

- loading state;
- error state;
- empty state: `No combatants yet. Add generated statblocks from Statblock View.`;
- refresh button.

### 10.2 Header / command row

Show:

```text
Current Combat
Round N
Active: <name or none>
Next: <name or none>
Entity count
```

Controls:

```text
Sort initiative
Previous turn
Next turn
Refresh
```

Sort initiative calls backend sort. Next/Previous call backend turn endpoint.

### 10.3 Roster table/cards

For each entity show:

- active marker;
- order;
- name;
- team;
- init;
- AC;
- HP / max HP;
- temp HP;
- defeated marker;
- conditions;
- notes;
- source/statblock path/artifact id compactly;
- controls.

Controls per row:

```text
Damage amount input + Damage button
Heal amount input + Heal button
Temp HP amount input + Temp HP button
Defeated checkbox
Notes textarea/save
Conditions comma-list input/save
Initiative input/save
```

Keep the controls compact. Do not over-polish.

### 10.4 Editing strategy

Prefer explicit per-row actions over autosave for PR113.

Example:

- local notes input changes without API call;
- click `Save notes/conditions` sends patch;
- click `Save init/HP` sends patch;
- damage/heal buttons send delta immediately.

On any successful operation:

```text
setEncounter(response.encounter)
show small success status
clear operation error
```

On failure:

```text
keep current encounter visible
show safe row/global error
```

### 10.5 Statblock drilldown affordance

If `entity.statblock_artifact_id` exists:

- show artifact id/title/path;
- optionally include a disabled or text-only hint:

```text
Open in Statblock View
```

Do not implement cross-module selection unless existing infrastructure makes it trivial. PR113 is about combat controls, not cross-surface routing.

---

## 11. Backend tests

Add:

```text
tests/test_combat_roster_operations.py
```

Use temp live session roots. You can seed `combat/current_combat.json` directly using `write_json(...)` with `CombatEncounterState` data.

### 11.1 Empty read remains clean

Existing PR112 test covers this. Keep or extend if needed.

### 11.2 Patch entity

Setup combat with one entity.

PATCH notes/conditions/init/defeated/hp/temp HP.

Assert:

- response 200;
- changed entity id included;
- fields updated;
- `updated_at` changed;
- only combat file changed.

### 11.3 Damage/heal/temp HP delta

Setup entity:

```text
hp=30 max_hp=40 temp_hp=5
```

Cases:

```text
damage 3 → temp_hp 2, hp 30
damage 10 → temp_hp 0, hp 22
heal 5 → hp 27
heal 999 → hp 40
temp_hp 6 → temp_hp 6
temp_hp 4 → temp_hp remains 6
```

Assert no auto-defeated unless explicitly patched.

### 11.4 Non-numeric HP delta rejected

Setup `hp="bloodied"`.

Damage/heal should return 409 and not mutate file.

### 11.5 Sort initiative

Setup mixed entities:

```text
init 18, 12, null, 20
```

Sort descending, null last.

Assert:

- order renumbered 1..n;
- active turn set to first when requested;
- round unchanged.

### 11.6 Turn advance / rewind

Setup three entities with active pointer.

Assert:

- next advances active;
- next from last wraps to first and increments round;
- previous rewinds;
- previous from first wraps to last and decrements round but not below 1;
- no entities case safe.

### 11.7 Entity not found / unsafe ID

Patch/delta unknown id returns 404.

If any path-like id is accepted as a route param, ensure it does not leak path behavior. Entity IDs are not file paths, so simple 404 is acceptable.

### 11.8 No unrelated mutation

For each mutation type, assert only:

```text
combat/current_combat.json
```

changes under the live session.

No changes to:

```text
live_packet.json
surface_layout.json
event_log.jsonl
job_queue.jsonl
statblock_drafts/
statblock_retrieval/
```

### 11.9 No secret exposure

Set fake env:

```text
DUNGEONBUDDY_INTERNAL_API_KEY=super-secret-test-key
DUNGEONMIND_SERVER_URL=https://example.invalid
```

Call read/patch/delta/turn/sort.

Assert responses do not contain:

```text
super-secret-test-key
DUNGEONBUDDY_INTERNAL_API_KEY
DUNGEONMIND_SERVER_URL
X-DungeonBuddy-Internal-Key
```

---

## 12. Frontend tests

Add:

```text
apps/live-control-ui/src/surface/modules/CombatRosterModule.test.tsx
```

Update:

```text
apps/live-control-ui/src/api/liveApi.test.ts
```

### 12.1 API helper tests

Assert:

- patch helper uses `PATCH /api/live/combat/current/entities/{id}`;
- delta helper uses `POST /api/live/combat/current/entities/{id}/delta`;
- turn helper uses `POST /api/live/combat/current/turn`;
- sort helper uses `POST /api/live/combat/current/sort-initiative`.

### 12.2 Module tests

Test cases:

1. Empty state renders.
2. Roster renders active/next actor and rows.
3. Sort initiative calls API and updates order.
4. Next turn calls API and updates active marker/round.
5. Damage/heal/temp HP controls call API and update HP readback.
6. Defeated checkbox or save button patches entity.
7. Notes/conditions save patches entity.
8. Operation failure keeps roster visible and shows safe error.
9. Module is registered in `moduleRegistry`.

No live network.

---

## 13. Manual smoke

Backend:

```bash
uv run uvicorn apps.live_control_server.main:app --reload
```

After PR112 has added entities:

```bash
curl -s http://127.0.0.1:8000/api/live/combat/current | jq

ENTITY_ID="<entity id>"

curl -s \
  -X POST \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:8000/api/live/combat/current/entities/${ENTITY_ID}/delta" \
  -d '{"mode":"damage","amount":7}' \
  | jq

curl -s \
  -X POST \
  -H "Content-Type: application/json" \
  http://127.0.0.1:8000/api/live/combat/current/sort-initiative \
  -d '{"descending":true,"place_nulls_last":true,"set_active_to_first":true}' \
  | jq

curl -s \
  -X POST \
  -H "Content-Type: application/json" \
  http://127.0.0.1:8000/api/live/combat/current/turn \
  -d '{"direction":"next"}' \
  | jq
```

Frontend:

```bash
cd apps/live-control-ui
npm run dev
```

Verify:

```text
Enable Combat Roster.
Roster loads current combatants.
Sort initiative works.
Next/Previous turn updates active actor.
Damage/heal/temp HP update HP.
Notes/conditions/defeated changes persist after refresh.
No corpus/statblock/retrieval files change.
```

---

## 14. Testing commands

Suggested backend:

```bash
uv run pytest \
  tests/test_combat_roster_operations.py \
  tests/test_statblock_add_to_combat.py \
  tests/test_live_session_bootstrap.py \
  -q
```

Suggested frontend:

```bash
cd apps/live-control-ui
npm test -- \
  src/surface/modules/CombatRosterModule.test.tsx \
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
  apps/live_control_server/routes/live.py \
  tests/test_combat_roster_operations.py \
  tests/test_statblock_add_to_combat.py \
  src/live_play/session_bootstrap.py

git diff --check
```

If `npm run build` remains blocked by the known `@types/node` environment/config issue, document the caveat in the PR body.

---

## 15. Acceptance criteria

The PR is ready when:

- Combat operation request/response models exist.
- Patch entity endpoint exists.
- Damage/heal/temp HP endpoint exists.
- Initiative sort endpoint exists.
- Turn advance endpoint exists.
- All operations persist to `combat/current_combat.json` only.
- HP delta rules handle temp HP and max HP clamping.
- Sort renumbers orders and sets active pointer when requested.
- Turn pointer wraps and round increments/decrements safely.
- `CombatRosterModule` exists and is registered as optional/disabled-by-default.
- Roster displays current combatants, active/next actor, HP/AC/init/team/conditions/notes/defeated.
- Roster controls call backend and update visible state.
- Statblock View remains a statblock consumer/add surface, not the tracker.
- Tests prove no unrelated mutation and no secret exposure.
- Focused backend/frontend tests pass.

---

## 16. Suggested PR description

```markdown
### Motivation

PR #112 added generated statblocks to a file-backed current combat state. This PR turns that state into a useful table-facing surface by adding a compact Combat Roster module with HP, initiative, notes, conditions, defeated state, and turn controls.

### Description

- Extended `combat_state.py` with combat patch, delta, sort, and turn operation models/helpers.
- Added live-control endpoints for patching entities, applying damage/heal/temp HP, sorting initiative, and advancing/rewinding turns.
- Added `CombatRosterModule` as an optional live surface module.
- Registered `combat_roster` in module registry and bootstrap catalog/layout.
- Added roster UI for active/next actor, entity rows, HP controls, notes/conditions/defeated edits, sort initiative, and turn navigation.
- Kept generation, corpus writes, retrieval activation, terrain, and planning-mode tasks out of scope.
- Added backend/frontend tests for operation behavior, persistence boundaries, and UI interactions.

### Testing

- `uv run pytest tests/test_combat_roster_operations.py tests/test_statblock_add_to_combat.py tests/test_live_session_bootstrap.py -q`
- `cd apps/live-control-ui && npm test -- src/surface/modules/CombatRosterModule.test.tsx src/api/liveApi.test.ts`
- `cd apps/live-control-ui && npx tsc -p tsconfig.app.json --noEmit`
- `uv run ruff check apps/live_control_server/services/combat_state.py apps/live_control_server/routes/live.py tests/test_combat_roster_operations.py tests/test_statblock_add_to_combat.py src/live_play/session_bootstrap.py`
- `git diff --check`
```

---

## 17. Design reminder

This PR is the first proper combat-control surface. It is not the whole combat system.

The ladder after PR113 should be:

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
Add to combat ✅
Combat Roster / Tracker ⏭️ this PR
Planning-mode-integrated ❌
```

A good next slice after PR113 would be one of:

```text
PR114 — Statblock drilldown from Combat Roster rows
PR114 alt — Combat import/export/static-save bridge
PR114 alt — Planning Mode generated combatant task flow
```

Do not let PR113 grow into all three.
