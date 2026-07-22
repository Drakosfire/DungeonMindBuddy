# HANDOFF — SBW15 Exact-revision combat adapter

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — dispatch after `SBW10` merges and current combat persistence/export contracts are re-anchored.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw15-exact-revision-combat-adapter.md`  
**Workstream:** `SBW15`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch one runtime capability: derive a deterministic seed from one exact statblock revision and create mutable combatant instances in the existing tracker. Do not redesign Play, automate rules, update revisions, write graph truth, or change mechanics from combat state.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Derive typed `CombatantSeedV1` from exact revision | No alone; required adapter | Yes | No | Include |
| Add one or multiple mutable instances to current combat | Yes | Yes | Yes | Include |
| Persist exact locator + bounded operational snapshot | No; required reload/export correctness | Yes | Yes | Include |
| Full statblock drilldown | No; reuse `SBW10` | No | Yes | Include integration |
| Full Play surface migration | Yes | Yes | Broad | Successor Campaign Supergraph Play migration |
| Rules automation | Yes | Yes | Broad | Exclude |

**Selected capability:** the GM can add an exact accepted revision to the existing combat tracker and continue operating if the mechanics service is temporarily unavailable after insertion.

## §1 Mission

A GM can add one exact statblock revision to current combat as one or more mutable combatant instances so live HP, initiative, conditions, and notes remain operational while mechanics identity stays immutable.

**Invariant**

```text
Each combatant instance stores an exact immutable mechanics locator and bounded seed snapshot; runtime mutations change only combat state and can never change the statblock revision, graph binding, or definition digest.
```

**Mission falsification test**

```text
This is not one slice if implementation must also migrate the entire Play surface, automate attacks/effects, upgrade active combatants, edit mechanics, or publish graph state.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §12; current combat tracker/state contracts; tracker `SBW15`; `SBW10` exact projection |
| Repository rules | `AGENTS.md`; runtime state separate from mechanics/graph; external-agent PR loop |
| Base revision | Actual merged SHA containing `SBW10` and current combat tracker |
| Predecessor contract | Exact `StatblockRevisionResourceV1`; shared `combatMinimums` proof if still current; `CombatEncounterState` save/load/export; legacy `addGeneratedStatblockToCombat` path |
| Exact input consumed | Exact statblock/revision/digest and optional Threat/binding context; insertion options |
| Named successor | Play projection migration consumes this adapter |
| What remains false | No rules execution, active revision upgrade, encounter builder redesign, or graph write |
| Explicit non-goals | Play rewrite, automated actions, media, graph, mechanics edit, corpus lookup, migration of every historical save beyond explicit compatibility policy |

Read in order:

1. integration design §12
2. current `combat_state.py`, combat routes/UI/tests, save/load/export contracts
3. merged `SBW10` exact Threat Sheet/read projection
4. generated statblock definition/revision types and existing `combatMinimums`
5. legacy generated-statblock combat add route/service for demolition inventory

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Add exact revision | Artifact/corpus-backed generated statblock | Resolve exact revision and derive seed | Yes | adapter/service |
| Add count >1 | Legacy supports copies | Create independent instances sharing exact locator/snapshot | Yes | service |
| Override name/HP/init/team | Legacy supports options | Apply only runtime overrides; preserve seed provenance | Yes | service |
| Save current combat | Existing JSON state | Locator/snapshot round-trip | Yes | combat store |
| Load/export combat | Existing save/export | Exact locator + snapshot retained | Yes | store/API |
| Server unavailable after insertion | Legacy corpus may work | Row remains operational from snapshot; drilldown unavailable honestly | Yes | tracker/UI |
| Server unavailable before insertion | Could use artifact/corpus | Block insertion unless caller supplies already-verified seed under explicit same-request contract | Yes | service |
| Full drilldown | Corpus artifact view | Reuse exact Threat Sheet/statblock resolver | Yes | UI |
| HP/conditions/notes mutation | Existing runtime state | Must not alter locator/digest/snapshot identity fields | Yes | mutation service |
| Revision append/Threat binding upgrade | New revision may exist | Existing combatant remains pinned | Yes | non-mutation proof |
| Legacy add-generated path | Active | Replaced for normal exact-revision path; delete if no named consumer | Yes | demolition |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/combatant_seed.py` | strict deterministic seed/snapshot/locator contract |
| Create | `apps/live_control_server/services/statblock_combat_adapter.py` | exact revision → seed derivation |
| Modify | `apps/live_control_server/services/combat_state.py` | versioned entity locator/snapshot fields and exact-revision insertion |
| Modify | current combat routes | add exact-revision endpoint; retain mutation APIs |
| Create | `tests/test_statblock_combat_adapter.py` | derivation/error proof |
| Modify/Create | focused combat state/save/load/export tests | persistence/non-mutation/compatibility proof |
| Modify | `apps/live-control-ui/src/api/types.ts`, `liveApi.ts`, `liveApi.test.ts` | exact insertion contract |
| Modify | current combat tracker components | add action/result/drilldown locator handling |
| Modify | `ThreatSheet.tsx` | “Add to combat” action with exact locator |
| Modify | focused Threat Sheet/combat tracker tests | user path/unavailable proof |
| Delete/Modify | legacy artifact/corpus combat-add route/service/types/tests when exact replacement has no consumer | demolition |

### Bounded discovery exception

```text
Directory: apps/live_control_server/services/, apps/live-control-ui/src/, current combat save/export modules
Maximum additional paths: 8
Allowed path kinds: exact combat route, save-slot serializer/version migrator, tracker row/drilldown component, legacy direct predecessor deletion, focused tests
Decision rule: include only to derive, insert, persist, reload, export, mutate, or drill down one exact-revision combatant
Required report: provide combat schema compatibility and predecessor consumer ledger
```

## §5 Explicitly out of scope

| Capability | Why excluded |
|---|---|
| full `/play` Surface migration | separate Campaign Supergraph/Surface capability |
| attack/effect/resource automation | not required for mutable roster operation |
| active combatant revision upgrade | prohibited; combat remains pinned |
| statblock/graph write | runtime cannot mutate authorities |
| image/token assignment workflow | `SBW17`; existing display may consume selected ref later |
| initiative rolling system redesign | only seed/default/explicit input |
| encounter builder/placement model | separate capability |
| corpus Markdown/artifact identity fallback | predecessor to remove |

## §6 Implementation contract

### `CombatantSeedV1`

```text
schema: dmb_combatant_seed_v1
provider: dungeonmind
statblock_id
revision_id
definition_digest
threat_id?
binding_id?
name
armor_class
max_hit_points
hit_point_formula?
initiative_modifier
speed_summary
challenge_rating?
human_adjudicated_element_keys[]
source_warnings[]
```

### Combat instance locator/snapshot

Add a versioned structure rather than more unrelated nullable fields:

```text
mechanics_ref:
  provider
  statblock_id
  revision_id
  definition_digest
  threat_id?
  binding_id?

mechanics_snapshot:
  schema: dmb_combatant_seed_v1
  name
  armor_class
  max_hit_points
  initiative_modifier
  speed_summary
  challenge_rating?
  human_adjudicated_element_keys[]
```

Runtime mutable fields remain separate:

```text
name override/display name
team/order/init
hp/max_hp/temp_hp
defeated
conditions/notes/tags
```

### Derivation decisions

- Use contract-typed fields only. Do not parse rendered Markdown or `rules_text` for AC/HP/speed/initiative.
- `initiative_modifier` derives from an explicit contract field when available; if the contract only exposes Dexterity and 5e ruleset semantics make derivation deterministic, document and test the exact rule. Stop if ruleset ambiguity exists.
- Human-adjudicated warnings are stored as bounded element keys/summary, not entire mechanics bodies.
- Snapshot is operational, not canonical. Full drilldown reads exact revision.
- Runtime name/HP/init overrides do not change the snapshot/digest; provenance records overrides.

```text
Input:
  exact StatblockRevisionResourceV1 + AddExactRevisionToCombatRequestV1

Output:
  deterministic CombatantSeedV1 and one or more persisted CombatantInstance records

Invariant:
  immutable locator/snapshot separated from runtime mutation

Failure behavior:
  exact revision missing/unavailable/digest mismatch before insertion -> block; no corpus fallback
  unsupported/ambiguous required minimum -> typed derivation error; no partial entity
  combat save write failure -> no partial visible state under existing atomic writer
  exact revision unavailable after reload -> row uses snapshot; drilldown unavailable
  malformed legacy save -> existing compatibility policy, never silently invent exact locator

Replay / idempotency:
  insertion is intentionally instance-creating; repeated user action creates new instances
  optional client operation ID may dedupe accidental network replay of one add request
  same count request response retry must not double-add if operation ID contract is used
  runtime mutations use existing entity identity/version semantics

Trust boundary:
  Verifies: exact revision/digest, typed minimum derivation, count/overrides, combat state schema
  Records without proving: encounter balance, appropriate team/initiative override
  Rejects: artifact path identity, latest revision, mechanics mutation from combat
```

### §6A State and fallback matrix

| Path | Loading | Success | Miss | Dependency unavailable | Integrity failure | Stale/new revision | Retry |
|---|---|---|---|---|---|---|---|
| Derive/add | exact read | seed + instances | 404 blocks | blocks before insertion | digest/minimum fail | exact requested remains | operation-ID replay safe if implemented |
| Combat reload | load save | snapshot row + locator | legacy row handled by explicit compatibility | Server unavailable still operational | malformed snapshot fails/diagnostic | new revision ignored | safe |
| Drilldown | exact read | full shared view | 404 unavailable detail | unavailable detail | digest mismatch detail blocked | no latest | retry |
| Runtime mutate | exact entity | hp/init/conditions update | entity 404 | N/A | mechanics fields immutable | revision unchanged | existing mutation replay |
| Export/save | serialize state | locator/snapshot retained | N/A | N/A | schema validation fails | unchanged | safe |

No fallback to corpus path, artifact ID, display name, candidate cache, or latest revision.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Persistence consequence |
|---|---|---|---|---|
| Mechanics | exact statblock/revision/digest | mismatch blocks | No | `mechanics_ref` |
| Combat instance | existing unique entity ID | repeated names allowed | No name lookup | mutable row identity |
| Add operation | optional exact client operation ID | changed payload conflict | No | network replay safety |
| Threat/binding | optional exact context IDs | mismatch does not replace mechanics locator; validate when supplied | No label lookup | provenance/drilldown context |
| Snapshot | bound to mechanics digest at insertion | mismatch integrity failure | No | offline operation |
| New revision | separate immutable ID | never rebind instance | No latest | existing row unchanged |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip | Duplicate/replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Add instances | combat encounter schema version with ref/snapshot | exact locator/snapshot + mutable values | operation-ID dedupe or documented route-level strategy | explicit migration/read policy for v1 legacy rows | remove entity through existing behavior if supported |
| Save/load slot | existing save slot with new fields | exact round-trip | safe repeat | schema version bump if required | restore prior save |
| Export | existing export representation | locator/snapshot retained | deterministic | old consumers policy explicit | N/A |
| Runtime mutate | existing atomic combat write | mechanics ref/snapshot unchanged | existing semantics | no mechanics migration | reverse via game action/manual edit |

### §6D Predecessor-to-consumer mapping

**Grounding source:** `StatblockRevisionResourceV1`, current `combatMinimums`, `CombatEntity`, legacy `addGeneratedStatblockToCombat`.

| Source | Seed/instance field | Rule | Proof |
|---|---|---|---|
| statblock/revision/digest | mechanics ref | exact copy | adapter test |
| name/AC/HP/formula/speed/CR | seed snapshot | typed direct mapping | simple fixture |
| initiative source | modifier | explicit deterministic rule | fixture/stop condition |
| human-adjudicated elements | keys/warnings | bounded | complex fixture |
| Threat/binding context | optional provenance/ref | exact IDs | route test |
| add request count/team/overrides | runtime instances | bounded, independent copies | integration test |
| legacy artifact/path/fingerprint | no normal-path mapping | delete/legacy compatibility only | demolition tests |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Deterministic typed seed | adapter | fixture tests | exact output |
| Missing/ambiguous minimum blocks | adapter | negative fixtures | no entity write |
| Add/replay count correct | route/combat service | operation retry tests | no accidental duplicates |
| Save/load/export retains ref/snapshot | combat store | round-trip tests | exact equality |
| Runtime mutations cannot alter mechanics | combat mutation service | patch/HP/condition tests | ref/snapshot unchanged |
| Offline row works; drilldown honest | UI/service | Server unavailable test | row usable, detail unavailable |
| New revision/binding upgrade does not rebind | integration | non-mutation fixture | old ID remains |
| Legacy path demolished/compatible | diff/tests | consumer ledger | normal artifact path gone |

Required commands:

```bash
uv run pytest tests/test_statblock_combat_adapter.py <focused combat state/save/load/export tests> -q
cd apps/live-control-ui && npm test -- --run <ThreatSheet/combat tracker tests> src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Add two instances from an exact Threat Sheet, mutate HP/conditions/initiative, save/reload/export, then stop DungeonMindServer and continue operating the rows while drilldown reports unavailable. Append/upgrade to a newer revision elsewhere and prove the combatants remain pinned.

## §8 Required handback

Include seed derivation matrix, combat schema compatibility/migration decision, base/head, paths, commands/results/provenance, live add/mutate/reload/offline evidence, demolition ledger, baseline failures/waivers, and confirmation that no Play rewrite/rules automation/revision upgrade/media ships.

## §9 Acceptance rubric

- [ ] Exact revision/digest is required before insertion.
- [ ] `CombatantSeedV1` is deterministic and typed.
- [ ] Locator/snapshot are separated from mutable combat state.
- [ ] Add/replay semantics prevent accidental duplicate network delivery.
- [ ] Save/load/export retain exact locator and snapshot.
- [ ] Runtime mutation cannot alter mechanics identity/digest.
- [ ] Offline row remains operational; drilldown fails honestly.
- [ ] Existing combatants never auto-upgrade.
- [ ] Artifact/corpus identity is not the normal path.

## §10 Reviewer protocol

Begin with persisted combat schema and mutation immutability. Audit initiative derivation, operation replay, offline behavior, legacy compatibility, and exact drilldown. Search for corpus/artifact reads, latest, writing mechanics fields from patch requests, and hidden Play redesign.

## §11 Re-review protocol

Rerun derivation fixtures, negative minimums, count/replay, all runtime mutations, save/load/export, unavailable drilldown, new-revision non-mutation, and legacy compatibility tests after every fix.

## Stop conditions

Stop if:

- initiative or another required seed field is ambiguous under the current contract/ruleset;
- combat persistence cannot add a versioned locator/snapshot without destructive migration;
- tracker logic assumes corpus Markdown is canonical;
- network replay cannot be made safe without a new general mutation-version contract;
- exact revision cannot be resolved server-side;
- a full Play rewrite is required;
- a path outside the bounded allowlist is required.

## Final dispatch check

- [ ] Re-anchor current combat schema/save/export paths.
- [ ] Resolve initiative derivation explicitly.
- [ ] Inventory legacy saves/consumers.
- [ ] Confirm no revision upgrade or Play rewrite ships.
