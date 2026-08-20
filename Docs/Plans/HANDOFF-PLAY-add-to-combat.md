---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: PLAY-SURFACE / Playable Architecture Graduation / P4
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-add-to-combat.md
  - Suggested branch / PR: agent/play-add-to-combat / `PLAY: add exact Threat to Combat`

  ## Verification pointer
  - Design anchor: current main `53aaf9a566cfd40dd09f1a4c9723276cefa2a98a` (merge of PR #608)
  - P3C final reviewed head: `6b0b177f08a09c2b1f8c8ff9a1eb71b450b57087`
  - P3C formal review cycles: 2
  - Implementation base/head: <PIN_AT_DISPATCH> / <implementation head>
  - Changed paths: must remain inside HANDOFF §4
  - Verification: HANDOFF §7 + roadmap review disposition

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and roadmap review disposition are the review contract.
  This body is transport metadata.
---

# HANDOFF — add exact Threat mechanics to the existing Combat runtime

**Created:** 2026-08-16  
**Status:** DESIGNED — **DEFERRED, not current dispatch authority.** Cycle 4 repair of generation-local Add receipts on save/load. Generation bootstrap, exact-revision model path, binding identity, and predecessor seed mapping remain as Cycles 2–3. The C2 Session 27 dogfood showed Combat state must first become durable and browser/worktree-independent (`Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`); the current sequence is Lane B (durable Combat state / database-backed tracker authority) before this exact Threat→Combat mutation is re-pinned. This handoff is preserved design evidence and is **not** "directly dispatchable when selected" until a durable Combat re-anchor names P4 next. **No prerequisite exists merely because another handoff/document is absent from `main`, and P4 does not require P3A/P3B implementation merely to establish this exact Threat→Combat transition.**
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-add-to-combat.md`  
**Conversation/workstream:** `PLAY-SURFACE / Playable Architecture Graduation / P4`
**Flow / owner:** `PLAY-SURFACE`
**Direction:** DESIGN → CODE → REVIEW  
**Design anchor:** current `main` `53aaf9a566cfd40dd09f1a4c9723276cefa2a98a` — merge of PR #608  
**P3C final reviewed head:** `6b0b177f08a09c2b1f8c8ff9a1eb71b450b57087`  
**P3C review cycles:** `2`  
**Implementation base:** `PIN_AT_DISPATCH`  
**Suggested branch:** `agent/play-add-to-combat`  
**PR title:** `PLAY: add exact Threat to Combat`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

---

## Dispatch posture — code authority, not document placement

This handoff is intentionally usable as a staged design artifact.

At implementation dispatch:

1. re-read current `main` and pin that exact SHA as the implementation base;
2. re-read the current P3C mechanics seam and existing Combat service/routes named below;
3. inspect active PR/write leases for collisions on Combat, `routes/live.py`, Play reference components, and API client files;
4. run steward preflight against this handoff;
5. update path names in the implementation handback if current owners moved;
6. stop/re-brief only for a **material product/authority change**, not because another design handoff is on a branch or has not been merged.

P3A/P3B remain separate capabilities. P4 must not silently implement their missing native `/play` host, graph-reference click/open, occurrence derivation, or Projection-host lease. Conversely, their absence does not prevent P4 from establishing and proving the exact server mutation plus its Play-facing action component against the current P3C seam.

If current `main` has gained a real native Play host by dispatch, wire the action through that existing host and add the corresponding live proof. If it has not, component + API + server owning-boundary evidence is sufficient for this slice; do not invent a route merely to satisfy ceremony.

---

## §1 Mission and merge-ready invariant

**Mission:** From an authored Threat's exact P3C mechanics attachment, an explicit GM action adds one or more entities to the **existing** Combat runtime using the exact Threat identity and immutable statblock revision as provenance. After creation, Combat alone owns mutable HP, temporary HP, initiative, conditions, team, and encounter-local notes. No Combat mutation writes back to World, Playable, Run progress, or the immutable mechanics revision.

**Merge-ready invariant:**

> **`Add to Combat` is an explicit, idempotent authority transition from one exact resolved Threat at one exact World Graph scope plus one exact mechanics attachment identified by `binding_id` together with its coherent immutable revision triple `(statblock_id, revision_id, definition_digest)` into the existing `dmb_combat_encounter_state_v1` current Combat. The server independently revalidates the Run/campaign, exact Threat/scope, exact `binding_id`, immutable revision identity, and validation digest before creating entities. The client never submits a statblock body, never chooses first/latest/display-name mechanics, and never silently selects one of multiple exact bindings — including two bindings that share one revision triple. Each created Combat entity retains immutable source Threat + `binding_id` + statblock-revision references while Combat owns all mutable combat fields. Replay identity is bound to a non-recyclable Combat-owned `combat_generation_id` that Combat persist-establishes under the current-Combat lock **before** Add is actionable; Add never mints that id, including never for absent or legacy current files. A replay of the same request identity and same canonical intent against that same persisted generation creates nothing twice; the same request identity with different intent conflicts. All writers of the single current-Combat file serialize at the same Combat-owned mutation boundary so exact Add cannot lose concurrent HP/initiative/lifecycle changes. P4 does not create a second Combat store, does not add generic transaction/CAS infrastructure, does not implement missing P3B product behavior, and does not mutate World/Runbook/Run/mechanics authority.**

### Architecture boundary

The architecture already defines the transition:

```text
World Threat
  → accepted exact mechanics binding
  → immutable StatblockRevision
  → Play Threat mechanics projection
  → explicit Add to Combat
  → existing Combat runtime
  → Combat owns mutable HP / temp HP / initiative / conditions / team
```

P4 is the first mutation after the read-only P3C mechanics projection.

It is **not** a new Combat system. Current main already owns Combat in:

```text
apps/live_control_server/services/combat_state.py
  → out/runtime/.../combat/current_combat.json
  → dmb_combat_encounter_state_v1
  → mutable CombatEntity state

apps/live_control_server/services/combat_saves.py
  → new/load/unload/save current Combat lifecycle

apps/live_control_server/routes/live.py
  → /api/live/combat/current
  → existing HP / initiative / turn / lifecycle routes
  → existing legacy generated-statblock Add path
```

The dogfood/legacy path proved the table behavior. P4 graduates the **identity and mutation boundary**, not the old artifact/corpus representation.

### One independently useful capability

P4 includes:

```text
exact Threat + exact immutable mechanics attachment
  → explicit operator choice
  → exact server revalidation
  → idempotent append to existing Combat
  → Combat-owned mutable state
```

Necessary serialization hardening of the same `current_combat.json` owner is part of this capability because an Add operation is not correct if it can erase a concurrent HP/initiative/lifecycle write.

P4 does **not** include a generic transaction framework or a Combat UI overhaul.

### Capability decomposition

| Candidate outcome | Independently useful? | Durable/public contract? | Decision |
|---|---:|---:|---|
| Explicit Add action for one exact P3C binding | Yes | New Play→Combat command | **Include** |
| Select quantity/team explicitly | No; command inputs | Existing Combat semantics | **Include** |
| Revalidate exact Threat + graph scope server-side | No; authority clause | Existing Threat hydration contract | **Include / reuse** |
| Revalidate exact `binding_id` plus coherent revision triple | No; authority clause | Existing World→statblock binding + DungeonMindDnD/statblock contract | **Include / reuse** |
| Seed name/AC/HP from exact immutable revision | No; creation clause | Existing statblock definition | **Include** |
| Persist exact Threat + revision provenance on Combat entity | No; traceability clause | Combat schema extension | **Include** |
| Idempotent response-loss retry | No; mutation safety | Combat-owned request receipt bound to non-recyclable `combat_generation_id` | **Include** |
| Persist Combat-owned generation on current-Combat bootstrap | No; replay-authority bootstrap | Explicit contract change from unpersisted `GET /combat/current` `_initial_state` | **Include** |
| Serialize all current-Combat writers | No; same persistence safety boundary | Existing file mutation ownership | **Include if current code still lacks shared serialization** |
| Choose first/highest/primary mechanics automatically | No | Unsafe hidden policy | **Prohibit** |
| Name/HP/initiative override during Add | Yes | Additional creation workflow | **Exclude** |
| Roll initiative automatically | Yes | Combat workflow | **Exclude** |
| Start/advance Combat automatically | Yes | Combat workflow | **Exclude** |
| Delete/remove combatants | Yes | Separate Combat mutation | **Exclude** |
| Combat tracker redesign | Yes | Separate surface capability | **Exclude** |
| P3B native click/open/occurrence derivation | Yes | Separate Play capability | **Exclude** |
| Persist active mechanics choice in Run | Yes | New Runtime semantic | **Exclude** |
| Generic Combat CAS token | Yes | New shared mutation contract | **Exclude unless evidence forces stop/rebrief** |
| Generic transaction framework | Yes | Buddy-shared primitive | **Exclude** |
| World/mechanics binding adoption/edit | Yes | Different authority mutation | **Exclude** |
| DungeonMind kernel change | Yes | Cross-system governance | **Prohibit** |

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Most dangerous shortcut | Client sends the already-rendered statblock body and server trusts it. **Forbidden.** Client sends exact refs only; server re-hydrates/revalidates. |
| Most dangerous ambiguity | Threat has multiple exact mechanics bindings, including two that share one revision triple, and UI/server chooses array[0], “primary,” or the triple alone. **Forbidden.** Each available `binding_id` is independently actionable. |
| Most dangerous mutation race | Add reads current Combat, HP/initiative/new/load mutates it, Add writes stale copy and loses the other change. All current-Combat writers must share one Combat mutation lock. |
| Most dangerous response-loss sequence | Server commits entities, response is lost, then `new_combat_encounter`/`load_combat_save` recycles `encounter_id` without the later receipt. Receipts bound only to `encounter_id` would append again. Bind receipts to non-recyclable `combat_generation_id`. |
| Most dangerous generation bootstrap hole | `GET /api/live/combat/current` currently returns synthetic unpersisted `_initial_state`. If the client copies an ephemeral UUID, later reads/Add admission can see a different generation; if Add mints for absent/legacy state, Add becomes the bootstrap mutation. Persist generation under the Combat lock on the current-Combat bootstrap read **before** Add is actionable. Add never mints. |
| Most dangerous save/load receipt import | `save_current_as` snapshots G1 receipts; `load_combat_save` mints G2. Retaining those receipts makes G2 carry G1 replay guards. Rebinding them to G2 claims those requests committed in G2. Clear `add_receipts` in the same atomic current-Combat write that mints G2. The save file and entity provenance stay untouched. |
| Most likely scope creep | Rebuilding Combat tracker, encounter authoring, P3B host, generic CAS, or Run-linked Combat architecture. Stop/split instead. |

---

## §2 Current owners and authority inputs

### Parent authority — read at dispatch

1. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
   - projection architecture;
   - Threat→exact mechanics→Combat transition;
   - Combat mutable-state ownership;
   - no World writeback.
2. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - P3/P4 boundary;
   - promotion test;
   - current roadmap observations at dispatch.
3. `Docs/Plans/HANDOFF-PLAY-native-threat-mechanics.md`
   - exact mechanics identity;
   - multi-binding behavior;
   - surface-neutral mechanics panel boundary.
4. current P3C implementation:
   - `apps/live-control-ui/src/playSurface/reference/PlayThreatMechanicsSection.tsx`;
   - `apps/live-control-ui/src/playSurface/reference/PlayGraphObjectSheet.tsx`;
   - `apps/live-control-ui/src/statblocks/projection/useExactThreatMechanics.ts`;
   - `apps/live-control-ui/src/statblocks/projection/ThreatMechanicsPanel.tsx`;
   - `apps/live-control-ui/src/statblocks/projection/threatSheetViewModel.ts`.
5. existing Combat owner:
   - `apps/live_control_server/services/combat_state.py`;
   - `apps/live_control_server/services/combat_saves.py`;
   - Combat routes in `apps/live_control_server/routes/live.py`.
6. existing server authority resolution:
   - `apps/live_control_server/services/play_run_registry.py`;
   - `apps/live_control_server/services/threat_query_hydration.py`;
   - `apps/live_control_server/integrations/dungeonmind_statblocks/models.py` (`ExactRevisionResourceV1` Buddy envelope);
   - `apps/live_control_server/integrations/dungeonmind_statblocks/generated/models.py` (generated `StatblockRevisionResourceV1`);
   - exact statblock fixture(s) under `tests/fixtures/statblocks/v1/`.
7. file mutation primitive:
   - `apps/live_control_server/services/registry_file_lock.py`.
8. PR #578 only as historical/dogfood interaction evidence; never import `ofConks*` or campaign-specific bridge data.

### Current design-anchor facts

At `53aaf9a566cfd40dd09f1a4c9723276cefa2a98a`:

```text
P3C exact mechanics read/render seam exists.
P3C Play composition wrapper exists but does not complete P3B.
Threat mechanics *revision* identity is statblock_id + revision_id + definition_digest.
Threat *attachment* identity is binding_id, which additionally incorporates role, phase_key, and variant_label (`compute_binding_id` / `compute_world_object_statblock_binding_id`). Two available bindings may share one revision triple.
Threat hydration is already server-owned and can return exact immutable revisions plus locator `bindingId`.
Existing Combat state is dmb_combat_encounter_state_v1 in current_combat.json.
CombatEntity already owns mutable hp/temp_hp/init/conditions/team/notes.
Existing Combat has a legacy generated-statblock Add path using artifact/corpus provenance.
Existing Combat save/load/new/unload lifecycle writes the same current-combat file.
`new_combat_encounter` currently accepts an arbitrary existing `encounter_id`; `load_combat_save` restores a saved encounter wholesale. `encounter_id` is therefore recyclable and is not by itself a safe replay authority.
`GET /api/live/combat/current` calls `load_or_initialize_current_combat()`. When `current_combat.json` is absent, that service returns synthetic `_initial_state` **without persisting** (`tests/test_statblock_add_to_combat.py::test_current_combat_read_initializes_empty_without_writing`). An ephemeral in-memory generation cannot be copied into Add.
Exact revision seed fields live on Buddy `ExactRevisionResourceV1` in `integrations/dungeonmind_statblocks/models.py`, which extends generated `StatblockRevisionResourceV1` in `generated/models.py`. Paths are `definition.identity.name`, `definition.defenses.armor_classes[]` with unique `default`, and `definition.vitality.hit_points` (`method`, `displayed_average`, `fixed_value`, formula). There is no `generated/models/statblock_revision_resource_v1.py`, `definition.name`, `definition.armor_class`, or `definition.hit_points.average`.
registry_mutation_lock already exists as a repository file-mutation primitive.
```

P4 should replace none of those owners. It extends them narrowly.

### Authority matrix

| Fact/state | Owner before Add | Owner after Add |
|---|---|---|
| Threat identity | World Graph | World Graph; copied exact ref as immutable Combat provenance |
| World graph scope/revision used for admission | World Graph projection | immutable source ref on created Combat entity/receipt |
| Mechanics attachment identity (`binding_id`) | World→DungeonMindDnD/statblock attachment | immutable exact ref on Combat entity/receipt |
| Immutable revision triple | StatblockRevision | copied onto Combat entity/receipt; must cohere with `binding_id` |
| Statblock definition | immutable StatblockRevision | immutable revision remains source; Combat seeds creation values only |
| Name/AC/max HP seed | exact immutable revision | Combat entity snapshot at creation |
| Current HP/temp HP | n/a | Combat only |
| Initiative | n/a | Combat only |
| Conditions | n/a | Combat only |
| Team | explicit Add input, then Combat | Combat only |
| Encounter notes | n/a | Combat only |
| Run progress | Run Runtime | unchanged |
| Runbook | Playable | unchanged |

---

## §3 Observable contract

### A. Explicit Play action

The action belongs in Play composition, not in the neutral mechanics renderer.

`ThreatMechanicsPanel` must remain surface-neutral and read-only.

Preferred composition:

```text
PlayThreatMechanicsSection
  → useExactThreatMechanics
  → ThreatMechanicsPanel          # read only
  → for each exact actionable binding:
       PlayAddToCombatControl     # Play-owned mutation affordance
```

If one exact available binding exists, show one explicit Add control for that binding.

If multiple exact bindings exist, **each available binding has its own explicit Add control**, labeled with enough role/phase/variant/revision context to make the choice visible.

Never:

```text
bindings[0]
latest revision
highest revision
first role == primary
match by display name
```

as an implicit active mechanics choice.

Unavailable, partial, missing, or integrity-failed bindings are not actionable.

### B. Operator inputs

P4 supports only:

```text
team: pc | ally | enemy | neutral
count: 1..20
```

Visible defaults may be:

```text
team = enemy
count = 1
```

Defaults must remain visible/editable before submission.

P4 does not accept:

```text
name override
HP override
max HP override
initiative override
group/placement override
condition seed
quantity inferred from prose
```

Those are separate Combat workflows.

### C. Client command — refs only

Conceptual request:

```text
AddExactThreatCombatRequest {
  request_id: UUID
  encounter_id: string
  combat_generation_id: UUID

  source: {
    run_id: UUID
    threat_node_id: string
    world_id: string
    campaign_id: string
    scope_mode: campaign | world
    graph_revision_id: string
  }

  mechanics: {
    binding_id: string
    statblock_id: string
    revision_id: string
    definition_digest: string
  }

  team: pc | ally | enemy | neutral
  count: 1..20
}
```

Exact wire nesting/naming may follow repository style, but these semantics may not be weakened.

`binding_id` is required and non-empty. It is the mechanics *attachment* identity from the current hydration locator (`ThreatBindingHydrationV1.bindingId`) / typed binding (`ThreatStatblockBindingV1.bindingId`). Predecessor computation already includes role, phase_key, and variant_label (`src/graph_memory/union_supergraph/statblock_binding.py`). The revision triple remains required and must cohere with that binding; it is not a substitute for `binding_id`.

`combat_generation_id` is required. The client copies it from **persisted** current Combat after the Combat-owned bootstrap read in §3H. It is never invented by the client and never minted by Add. Recyclable `encounter_id` remains a consistency check, not replay authority. The Add control is not actionable until that bootstrap returned a persisted generation.

The client MUST NOT send:

```text
statblock definition JSON
name
AC
HP
source prose
World summary
binding body
```

The server derives creation values from the exact admitted immutable revision.

### D. Route

Preferred route under the existing `/api/live` Combat owner:

```text
POST /api/live/combat/current/add-threat
```

Do not create a second Play-owned Combat API namespace merely because the action originates in Play.

Conceptual response:

```text
AddExactThreatCombatResponse {
  schema_version: dmb_add_exact_threat_to_combat_v1
  request_id: UUID
  replayed: bool
  entity_ids: string[]
  combat: CombatEncounterState
}
```

### E. Server admission order

Before writing Combat:

1. normalize/validate request identity fields;
2. load `run_id` through existing Play Run registry;
3. missing Run → `404`, no write;
4. require request campaign to equal Run campaign → otherwise `409`, no write;
5. load current Combat from disk (do not synthesize `_initial_state`, do not mint a generation);
6. absent `current_combat.json` or missing/blank `combat_generation_id` → `409`, no write, no mint;
7. require request `encounter_id` to equal current Combat `encounter_id` → otherwise `409`, no write;
8. require request `combat_generation_id` to equal the **persisted** current Combat `combat_generation_id` → otherwise `409`, no write;
9. require Combat campaign, request campaign, and Run campaign to agree → otherwise `409`, no write;
10. construct the existing exact Threat hydration request from request world/campaign/scope/revision + exact Threat node ID with mechanics included;
11. call existing server `query_threats_with_hydration(...)` / current equivalent;
12. require response world/campaign/scope/revision to equal the requested exact tuple;
13. require exactly one exact returned Threat node ID match;
14. find the **exact requested `binding_id`** among available hydrated bindings (`hydrationStatus == available` and non-empty locator `bindingId`);
15. zero exact matching available `binding_id` → `409`, no write;
16. multiple hydrated rows with the same requested `binding_id` → integrity failure `500`, no write;
17. require that binding's locator triple `(statblockId, revisionId, definitionDigest)` equals the requested triple;
18. when the typed binding object is present, require `binding.bindingId` equals the requested `binding_id` and its revision triple equals the requested triple;
19. require returned revision identity to equal the requested triple;
20. require revision validation receipt/digest coherence using current statblock contract;
21. incoherent server/hydration payload → `500`, no write;
22. hydration dependency unavailable → `503`, no write;
23. derive name/AC/max HP/current HP seed only from that exact immutable revision using §3G predecessor mapping; mapping failure → `500`, no write;
24. enter the Combat mutation lock;
25. re-read current Combat and re-check encounter_id + combat_generation_id + campaign + request receipt under the lock;
26. exact replay against the same `combat_generation_id` → return prior entity IDs/current Combat with `replayed=true`, no append;
27. request-ID intent conflict → `409`, no write;
28. append `count` Combat entities + durable receipt in one atomic current-Combat write;
29. return `replayed=false`.

The authority verification may perform network/read work before the Combat lock. The lock protects the read-modify-write and replay decision. Revalidate the current encounter under the lock before committing.

### F. Immutable source references on Combat entities

Extend the existing Combat schema without breaking legacy records.

Conceptual refs:

```text
CombatThreatSourceRef {
  run_id
  threat_node_id
  world_id
  campaign_id
  scope_mode
  graph_revision_id
}

ExactMechanicsAttachmentRef {
  binding_id
  statblock_id
  revision_id
  definition_digest
}
```

Each newly created exact-Threat entity carries both. `binding_id` is required provenance; the revision triple is required and must cohere with it. Role/phase/variant remain diagnostic labels on the hydration binding, not a second identity.

Existing legacy Combat entities without these refs remain readable/mutable.

Do not migrate or rewrite old entities merely because the model gains optional fields.

`CombatSource` may gain a new explicit value such as:

```text
exact_threat
```

Use the smallest vocabulary change consistent with existing model style.

### G. Seed values vs mutable Combat values

Creation seeds come from the current exact Buddy revision envelope `ExactRevisionResourceV1` (`apps/live_control_server/integrations/dungeonmind_statblocks/models.py`), which extends generated `StatblockRevisionResourceV1` in `generated/models.py`. Field paths are on `.definition`. There is no `generated/models/statblock_revision_resource_v1.py`, `definition.name`, `definition.armor_class`, or `definition.hit_points.average`.

```text
name    ← definition.identity.name
ac      ← unique default armor-class profile value
max_hp  ← method-specific HP seed below
hp      ← same max_hp seed
team    ← explicit operator input
init    ← existing unset/default Combat behavior
```

**Name.** `definition.identity.name` must be a non-empty string. Missing/blank → `500`, no write.

**Armor class.** Use `definition.defenses.armor_classes`.

```text
require a non-empty array
require exactly one profile with default == true
seed ac from that profile's integer `value`
```

Fail closed (`500`, no write) if:

```text
armor_classes is missing/empty/not an array
zero default profiles
two or more default profiles
the unique default profile has a non-integer or missing value
```

Do **not** fall back to `armor_classes[0]`. `combatMinimums()` in `apps/live-control-ui/src/contracts/dungeonbuddy-statblocks-v1/combatMinimums.ts` is a presentation helper and its `[0]` fallback is forbidden for Combat seed admission. The generated contract already requires exactly one default profile; a hydrated revision that violates that is an integrity failure.

**Hit points.** Use `definition.vitality.hit_points`. P4 does not roll dice.

```text
method == "fixed"
  → seed max_hp/hp from integer `fixed_value`
  → `fixed_value` missing/null/non-integer → 500, no write
  → do not use displayed_average as the Combat seed

method == "formula"
  → seed max_hp/hp from integer `displayed_average`
  → `displayed_average` missing/null/non-integer → 500, no write
  → do not evaluate `formula` at Add time
  → do not use `fixed_value` (predecessor leaves it null for formula)

any other method
  → 500, no write
```

Do **not** use `displayed_average ?? fixed_value` as a silent fallback.

Concrete predecessor fixture `tests/fixtures/statblocks/v1/exact-revision-response.json` must seed:

```text
name   = "Ironhide Brute"
ac     = 15          # unique default natural_armor
max_hp = 68          # method=formula displayed_average
hp     = 68
```

After creation:

```text
hp / temp_hp / init / conditions / team / notes
  → Combat-owned mutable state
```

Those mutations never alter:

```text
World Threat
World→mechanics binding
StatblockRevision
Run
Runbook
```

A later new statblock revision does not auto-refresh an existing combatant. The stored exact revision reference is the pin for how that combatant entered Combat.

### H. Idempotency receipt

Response loss must not duplicate combatants.

Current main already recycles `encounter_id`:

```text
new_combat_encounter accepts an arbitrary existing encounter_id
load_combat_save restores a saved encounter record wholesale
```

An older save can therefore restore the same `encounter_id` without a receipt written later. Binding receipts only to `encounter_id` would make response-loss replay append again. That is the handoff's own stop condition; P4 must not pretend the current label is safe.

**Required Combat-local replay authority:** add `combat_generation_id` (UUID) on `CombatEncounterState`.

**One Combat-owned bootstrap rule.** A `combat_generation_id` exists only after Combat persists it under `combat_mutation_lock`. Never return a generation from a Combat read unless that id is already on disk in `current_combat.json`. The client never invents one. **Add never mints one**, including never for absent current files and never for legacy current files.

The existing current-Combat read is the bootstrap writer:

```text
GET /api/live/combat/current
```

Under the same Combat lock used by Add/HP/lifecycle:

```text
absent current_combat.json
  → persist _initial_state with a minted combat_generation_id
  → return that persisted state

existing current file missing/blank combat_generation_id
AND add_receipts empty/absent (legacy live current)
  → persist the same Combat plus a minted combat_generation_id
  → no other semantic change except the new field and updated_at
  → return that persisted state

existing current file missing/blank combat_generation_id
AND add_receipts non-empty
  → 500 fail-closed
  → no persist, no mint
  → do not drop receipts to make bootstrap succeed
  → do not mint a generation that would own another generation's replay guards

existing current file already has combat_generation_id
  → return it unchanged
  → do not mint
  → do not rewrite
```

This is an explicit contract change from predecessor `test_current_combat_read_initializes_empty_without_writing`. Replace that test with persist-on-bootstrap proofs. Do not keep an unpersisted synthetic GET that also returns a generation.

Play copies `combat_generation_id` from that persisted GET. The Add control stays disabled until the GET response includes a persisted generation. A later Add against an absent file or a current file still lacking generation is `409` / no write / no mint — Add is not a bootstrap fallback.

Mint a fresh `combat_generation_id` only when current Combat is created or replaced as a distinct live instance, in the same persist that writes that instance:

```text
GET /api/live/combat/current bootstrap   # absent or legacy-missing-generation only
new_combat_encounter                    # always, even if the caller reuses encounter_id
load_combat_save                        # always a new live generation; do not reuse the save's generation as current
unload_current_combat                   # fresh empty current Combat
```

Do **not** mint on Add, HP/temp HP, initiative, turn, or `save_current_as`. A save snapshots whatever generation was current, including that generation's `add_receipts`. Loading that save into current still mints a new generation so restored content is a new live instance.

**Receipts are generation-local replay guards, not snapshot history.** `load_combat_save` must, in the same atomic current-Combat write:

```text
mint a fresh combat_generation_id   # G2; do not reuse the save's G1
clear loaded add_receipts           # empty collection on current Combat
restore entities and other Combat fields from the save
leave combat/saves/<id>.json untouched
```

Do **not** retain G1 receipts on G2 current Combat. Do **not** rewrite those receipts' `combat_generation_id` to G2. Either would give G2 replay or conflict authority for requests that never committed in G2. Entity `source_threat_ref` / `mechanics_attachment_ref` provenance remains intact.

`new_combat_encounter` and `unload_current_combat` persist a fresh generation with empty `add_receipts`.

Do **not** rewrite `combat/saves/*.json` on disk merely to add `combat_generation_id` or to strip receipts. Legacy save slots remain readable; generation is established on the live current file by bootstrap or by new/load/unload persist.

HP/initiative/turn remain valid on a legacy current file that still lacks generation. Those routes are not Add and are not required to mint. Visiting GET is what makes Add actionable.

`encounter_id` remains a recyclable human/lifecycle label and a consistency check. It is not replay authority.

Add a Combat-owned receipt representation, conceptually:

```text
CombatAddReceipt {
  request_id: UUID
  encounter_id: string
  combat_generation_id: UUID
  source_threat_ref: CombatThreatSourceRef
  mechanics_attachment_ref: ExactMechanicsAttachmentRef
  team: CombatTeam
  count: int
  entity_ids: string[]
}
```

Stored on `CombatEncounterState` as an optional/default-empty collection or equivalent current-encounter structure.

Canonical replay semantics:

```text
same request_id
+ same combat_generation_id
+ same encounter_id
+ same exact source ref
+ same exact binding_id
+ same exact revision triple
+ same team
+ same count
  → replay success
  → no new entities
  → same original entity_ids

same request_id
+ any material intent difference, including a different binding_id
  → 409
  → no write

request combat_generation_id != current combat_generation_id
  → 409
  → no write
  → even if encounter_id matches
```

Receipts live on the current Combat generation as replay guards for that generation only. After `load_combat_save` they are empty on current Combat even if the save file still contains G1 receipts. Do not invent a cross-encounter global receipt ledger or a generic transaction/CAS primitive.

This remains Combat-local: `combat_saves.py` / `combat_state.py` mint and compare the generation id. It does not hoist a Buddy-shared mutation token.

### I. Current-Combat serialization

P4 must not introduce a new store or generic transaction framework.

Use the existing repository file-lock primitive through a Combat-local seam, for example:

```text
combat_mutation_lock(base)
  → registry_mutation_lock(combat_state_path(base))
```

Exact helper name may vary.

Every top-level mutation of `current_combat.json` must participate in the same lock if current code does not already guarantee that:

```text
GET /api/live/combat/current bootstrap persist
exact Threat Add
legacy generated-statblock Add
entity patch
HP delta
initiative update
active-turn/advance-turn
new Combat
load Combat save
unload current Combat
```

`save current as` may read a coherent snapshot under the same boundary if needed; do not hold the lock across unrelated slow I/O unless correctness requires it.

Avoid nested acquisition. Prefer:

```text
public top-level mutator acquires lock
  → read
  → mutate
  → atomic write helper
```

with the lower-level write helper remaining non-locking.

### J. Failure matrix

| Condition | Result |
|---|---|
| Run missing | 404 / no write |
| Current Combat missing or unbootstrapped generation | 409 / no write / no mint |
| Legacy bootstrap: non-empty `add_receipts` and missing generation | 500 / no persist / no mint |
| Encounter mismatch | 409 / no write |
| Combat generation mismatch | 409 / no write |
| Run/request/Combat campaign mismatch | 409 / no write |
| Exact Threat absent | 409 / no write |
| Requested `binding_id` absent/not available | 409 / no write |
| Requested `binding_id` present but revision triple does not cohere | 500 / no write |
| Hydration scope mismatch / duplicate exact Threat / internally incoherent revision | 500 / no write |
| Threat/mechanics hydration dependency unavailable | 503 / no write |
| Same request ID + same intent | 200 success / replayed true / no duplicate |
| Same request ID + different intent | 409 / no write |
| Concurrent distinct valid Adds | both preserved |
| Add concurrent with HP/initiative mutation | both preserved |
| Add concurrent with new/load/unload | serialized; deterministic final valid state; never torn/lost write |
| UI 409/503 | local action error; mechanics/object sheet remains usable |

---

## §4 Files in scope — write lease

Pin the exact implementation base at dispatch. These are current expected owners; if a path moved, substitute only its direct owner and record that in the handback.

### Design / evidence

| Action | Path | Purpose |
|---|---|---|
| Create / Modify | `Docs/Plans/HANDOFF-PLAY-add-to-combat.md` | implementation pin + evidence handback |

**Do not modify the living roadmap merely to stage this design.** A later implementation/state-authority sync may record P4 evidence when that is the actual workstream transition.

### Server — expected production lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live_control_server/services/combat_state.py` | exact source/`binding_id`/revision refs, `combat_generation_id`, Combat-owned GET bootstrap persist, receipt, exact Add mutation, Combat-local serialization, predecessor seed mapping from `ExactRevisionResourceV1` |
| Modify | `apps/live_control_server/services/combat_saves.py` | mint non-recyclable `combat_generation_id` on new/load/unload; on load, clear loaded `add_receipts` in the same atomic current write; share the same current-Combat lock; do not rewrite save files |
| Modify | `apps/live_control_server/routes/live.py` | exact Add route/request/response transport under existing Combat API owner |

### Server — read/reuse, not redesign

```text
apps/live_control_server/services/play_run_registry.py
apps/live_control_server/services/threat_query_hydration.py
apps/live_control_server/services/registry_file_lock.py
apps/live_control_server/integrations/dungeonmind_statblocks/models.py
apps/live_control_server/integrations/dungeonmind_statblocks/generated/models.py
apps/live_control_server/integrations/dungeonmind_statblocks/generated/**
```

Consume `ExactRevisionResourceV1` from `models.py`. Do not invent `generated/models/statblock_revision_resource_v1.py`.

`registry_file_lock.py` is read-only unless current implementation cannot reuse it without a tiny bug fix; if a generic primitive change becomes necessary, stop/rebrief before editing.

### Frontend — expected production lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/playSurface/reference/PlayThreatMechanicsSection.tsx` | render Play-owned Add affordance next to exact binding(s), keep neutral panel read-only |
| Create | `apps/live-control-ui/src/playSurface/reference/PlayAddToCombatControl.tsx` | explicit team/count + request identity + local mutation status; disabled until persisted `combat_generation_id` |
| Modify if context plumbing is required | `apps/live-control-ui/src/playSurface/reference/PlayGraphObjectSheet.tsx` | pass existing Run/encounter action context only; no P3B implementation |
| Modify | `apps/live-control-ui/src/api/types.ts` | exact Add request/response client types |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | exact Add command transport |

### Tests — bounded discovery

Implementation agent may add/modify the direct owning tests for the files above plus up to **six** additional existing test-only paths under:

```text
tests/**
apps/live-control-ui/src/**/*.test.ts
apps/live-control-ui/src/**/*.test.tsx
```

for:

```text
Combat route/service/lifecycle concurrency
GET current Combat generation bootstrap
P3C Play mechanics composition
API transport
legacy Combat compatibility
```

If production code requires more than the named paths above plus **two** direct owner replacements due to repo movement, update/rebrief the write lease before proceeding.

### Deliberate non-lease / read only

```text
Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md
Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md
Docs/Design/**
apps/live_control_server/services/play_run_registry.py       # consume only
apps/live_control_server/services/threat_query_hydration.py # consume only
apps/live-control-ui/src/statblocks/projection/ThreatMechanicsPanel.tsx
apps/live-control-ui/src/tiptap/**
apps/live-control-ui/src/graphReference/**
DungeonMind / DungeonMindDnD generated contracts
```

A required change to the exact Threat/statblock wire contract, generated DungeonMindDnD models, World Graph semantics, Run schema, or neutral mechanics panel is a stop/rebrief unless it is a trivial compatibility repair independently justified by current code.

---

## §5 Explicitly out of scope

P4 must not claim or implement:

- P3A native Runbook route/deck;
- P3B graph-reference click/open normalization;
- P3B Runbook occurrence derivation;
- P3B Projection-host publication/lease;
- generic Play Object Sheet completion;
- a second Combat runtime or second `current_combat` store;
- Combat tracker redesign;
- encounter authoring UI;
- delete/remove combatant;
- automatic Combat start;
- initiative rolling;
- automatic quantity from authored prose;
- name/HP/initiative override during Add;
- persistent active/default mechanics selection in Run;
- statblock body copying into Play/Run/Combat provenance;
- campaign-specific `ofConks*`/Threat bridge maps;
- World Graph writes;
- mechanics binding adoption/editing;
- statblock authoring;
- Run progress mutation;
- generic `WorkObject*` refs;
- generic Runtime state;
- generic transaction framework;
- generic Combat CAS token without a demonstrated need;
- DungeonMind kernel change;
- P5 proposal/adoption workflow.

---

## §6 Implementation contract

### A. Exact command identity

The durable mutation identity is:

```text
request_id
+ combat_generation_id
+ encounter_id
+ exact Threat source tuple
+ exact binding_id
+ exact mechanics revision tuple
+ explicit team
+ explicit count
```

Labels/titles are never identity.

### B. Exact Threat source tuple

```text
run_id
threat_node_id
world_id
campaign_id
scope_mode
graph_revision_id
```

Every field participates in canonical replay intent.

### C. Exact mechanics attachment

```text
binding_id
statblock_id
revision_id
definition_digest
```

Every field participates in canonical replay intent.

`binding_id` is the attachment identity. The revision triple is the immutable mechanics revision and must cohere with that attachment. Two available bindings that share one revision triple remain two commands.

A missing/blank `binding_id` is not a legal request. An available hydration row with a null/blank locator `bindingId` is not actionable.

### D. No body trust

The route must be safe if a malicious/stale client changes any presentation value it saw earlier.

Therefore presentation values are not accepted as authoritative request fields.

The server independently obtains the exact immutable revision through the existing governed hydration path and derives Combat seeds from it.

### E. Multi-binding command semantics

For Threat bindings A and B, including the case where A and B share one revision triple:

```text
Add A
  → request binding_id A + A's coherent revision triple

Add B
  → request binding_id B + B's coherent revision triple
```

The server does not know or infer which one is “active.” It proves only that the requested `binding_id` is an available accepted attachment for the exact Threat at the exact requested graph revision and that the requested revision triple coheres with that binding.

Selecting by revision triple alone is forbidden: it would make A and B indistinguishable, then classify two legitimate triple matches as an integrity failure.

### F. Entity creation

For count N, create N distinct Combat entity IDs in deterministic current repository style.

All N entities receive the same immutable source/`binding_id`/revision refs and explicit team, but remain separate mutable Combat entities.

Do not persist the entire statblock revision definition inside each entity unless the existing Combat schema already requires a bounded creation snapshot. Exact refs are the provenance contract.

### G. Legacy compatibility

Existing Combat JSON may lack:

```text
source_threat_ref
mechanics_attachment_ref
combat_generation_id
add_receipts
```

It must continue to deserialize and support existing HP/initiative/turn/lifecycle operations.

P4 must not force a migration rewrite of `combat/saves/*.json` merely on read.

GET `/api/live/combat/current` **does** persist-establish `combat_generation_id` on the live current file when that file is absent or legacy-missing-generation **and** `add_receipts` is empty/absent. Non-empty receipts with a missing generation is incoherent: GET fail-closes (`500`), no persist, no mint.

Legacy generated-statblock Add remains functional unless the slice explicitly proves it should be retired; retiring it is not required for P4.

### H. Combat lifecycle and receipt scope

A receipt belongs to the loaded current Combat *generation* as a replay guard for that generation only. It is not imported snapshot history.

`encounter_id` may recycle. `combat_generation_id` must not.

`save_current_as` snapshots the current generation, including `add_receipts`. `load_combat_save` mints a new generation and **clears** loaded `add_receipts` in that same current-Combat write. The save file is not rewritten. Entity provenance is not stripped.

The UI reads `combat_generation_id` from **persisted** current Combat after GET bootstrap, owns a fresh `request_id` per explicit Add intent, and may reuse that `request_id` only to retry that same unresolved command against the same generation.

The Add control is not actionable until that GET returned a persisted `combat_generation_id`. Do not invent a client-side UUID. Do not send Add against missing/blank generation.

When the selected encounter/generation/action context changes, discard the old retry identity and require a fresh operator action.

Do not automatically retry an old request across a new/load/unload Combat lifecycle transition. Those transitions mint a new `combat_generation_id` and, on load, drop imported receipts; a stale G1 retry must 409 rather than append or conflict against G1 receipts in G2.

### I. UI local state

`PlayAddToCombatControl` should own only transient form/request state:

```text
team
count
request_id for current unresolved intent
combat_generation_id copied from persisted current Combat after GET bootstrap
submitting
local error/success acknowledgement
```

It does not own Combat state or mechanics identity.

Disable duplicate submission while one request is in flight.

If transport failure leaves commit state uncertain, a retry button/action reuses the exact same `request_id` and canonical intent.

If server returns success, generate a new request ID only for a new deliberate Add action.

### J. Neutral mechanics seam remains neutral

Static invariant:

```text
apps/live-control-ui/src/statblocks/projection/ThreatMechanicsPanel.tsx
```

must not import:

```text
Combat API
Play Run context
PlayAddToCombatControl
team/count controls
```

P4 action composition stays above it in Play.

---

## §7 Evidence required to merge

Evidence must prove the mutation at the owner, not merely helpers.

### Server authority / mutation proof

Required tests:

1. **Happy path:** exact Threat + exact available `binding_id` adds one Combat entity.
2. **Count:** count > 1 creates exactly N distinct entities.
3. **Seed authority against the predecessor fixture:** using `tests/fixtures/statblocks/v1/exact-revision-response.json` (or an equivalent governed hydration of that revision), created entity `name == "Ironhide Brute"`, `ac == 15`, `max_hp == 68`, `hp == 68`. Caller-supplied name/AC/HP are ignored/rejected.
4. **AC unique-default rule:** zero default profiles or two default profiles → `500` / no write; do not seed from `armor_classes[0]`.
5. **HP method rule:** `method=formula` with null `displayed_average` → `500` / no write; `method=fixed` with null `fixed_value` → `500` / no write; formula method must not evaluate dice and must not fall back to `fixed_value`.
6. **Exact source refs:** created entities retain exact Run/Threat/world/campaign/scope/graph-revision provenance.
7. **Exact mechanics refs:** entities retain exact `binding_id` plus coherent statblock/revision/digest provenance.
8. **Shared-triple multi-binding:** two available bindings A and B share one revision triple and differ by `binding_id` (role/phase/variant). Add A creates entities whose provenance `binding_id` is A; Add B independently creates entities whose provenance `binding_id` is B. Neither request is an integrity failure merely because the triples match.
9. **Array-order:** requesting B adds B even if A appears first; no primary/first fallback.
10. **Missing `binding_id` / unavailable binding:** 409 and byte-for-byte current Combat unchanged.
11. **`binding_id` vs triple mismatch:** requested `binding_id` exists but the requested triple does not cohere → `500` / no write.
12. **Run campaign mismatch:** 409/no write.
13. **Encounter mismatch:** 409/no write.
14. **Combat generation mismatch:** same `encounter_id`, different `combat_generation_id` → 409/no write.
15. **Missing Run:** 404/no write.
16. **Unbootstrapped current Combat:** Add against absent `current_combat.json` or a current file missing `combat_generation_id` → 409 / no write / **no mint**. Add is not a bootstrap fallback.
17. **Absent-state bootstrap:** `GET /api/live/combat/current` with no current file persists `_initial_state` plus a `combat_generation_id`; the file exists afterward; the response generation equals the on-disk generation. This replaces `test_current_combat_read_initializes_empty_without_writing`.
18. **Legacy-state bootstrap:** GET a pre-P4 current file that lacks `combat_generation_id` **and** has empty/absent `add_receipts` persists exactly one generation onto that same live current file; other Combat fields besides `updated_at` remain; save slots are not rewritten.
18b. **Incoherent receipts without generation:** GET a current file that lacks `combat_generation_id` but has non-empty `add_receipts` → `500` fail-closed; no persist; no mint; receipts are not dropped to make bootstrap succeed.
19. **Stable repeated reads:** two sequential GETs after bootstrap return the same `combat_generation_id`; the second GET does not mint or rewrite.
20. **First-Add retry safety:** GET bootstrap → successful Add → lost response → GET again still same generation → exact old-token retry replays and does not append. Bootstrap between Add and retry must not mint a new generation.
21. **Concurrent bootstrap:** two overlapping GETs against absent current serialize on the Combat lock and persist exactly one generation; both responses carry that same id.
22. **new/load/unload rotation:** each of `new_combat_encounter`, `load_combat_save`, and `unload_current_combat` persists a new `combat_generation_id` distinct from the prior live generation, even when `encounter_id` is reused; an old-token Add then 409s. new/unload persist empty `add_receipts`.
23. **Hydration dependency unavailable:** 503/no write.
24. **Hydration response scope mismatch:** fail closed/no write.
25. **Duplicate exact Threat hit/internal response ambiguity:** 500/no write.
26. **Binding/revision identity or digest incoherence:** 500/no write.
27. **Exact replay:** same request ID + same canonical intent including `binding_id` and `combat_generation_id` returns original entity IDs with no duplicate.
28. **Intent conflict:** same request ID + changed team/count/source/`binding_id`/triple → 409/no write.
29. **Recycled encounter_id after new:** complete Add, `new_combat_encounter` with the same `encounter_id`, exact old-token retry → 409; no duplicate entities.
30. **Post-P4 save/load receipt isolation:**
    ```text
    G1 Add
      → save G1 with that receipt
      → load save as G2
      → current Combat has G2, empty add_receipts, restored entities
      → combat/saves/<id>.json still has G1 + G1 receipts
      → old G1 token 409s
      → G1 receipt cannot replay or intent-conflict in G2
      → new G2 Add succeeds normally
    ```
    Do not rebind G1 receipts onto G2.
31. **Older save restore without that receipt:** complete Add, `load_combat_save` of a prior snapshot of the same `encounter_id` that lacks that receipt, exact old-token retry → 409; no duplicate entities.
32. **Concurrent distinct exact Adds:** both commits survive.
33. **Add vs HP mutation:** both commits survive; HP change is not lost.
34. **Add vs initiative/entity mutation:** both commits survive.
35. **Add vs new/load/unload lifecycle:** serialized deterministic valid result; no torn/malformed current Combat; lifecycle mints a new `combat_generation_id`; load clears imported `add_receipts`.
36. **Legacy HP without generation:** pre-P4 current Combat JSON without new refs/receipts/generation id still supports existing HP/initiative/turn routes without requiring Add. GET of that same file is the bootstrap that persist-establishes generation before Add is actionable. Save slots are not rewritten merely by that GET.
37. **Post-add mutability:** HP/temp HP/init/conditions/team changes preserve immutable source/`binding_id`/revision refs and never call World/Run/statblock write paths.

Use an exact revision fixture or governed mocked hydration response. Do not fake the core admission by directly injecting a caller-provided statblock body into the Add service.

### Frontend proof

Required component/API tests:

1. one exact available binding → one Add affordance tied to its `binding_id`;
2. multiple available bindings, including two that share a revision triple → one explicit affordance per `binding_id`; no hidden winner;
3. unavailable/partial/integrity-failed/missing-`bindingId` binding → not actionable;
4. team/count are visible and submitted exactly;
5. request contains exact Run/Threat/world/campaign/scope/revision + `combat_generation_id` copied from persisted current Combat + `binding_id` + revision triple;
6. request contains **no statblock definition/body/name/HP**;
7. no action context → P3C mechanics remains read-only;
7b. no persisted `combat_generation_id` yet → Add control is not actionable; client does not invent a UUID;
8. double click/in-flight interaction produces one request;
9. retry after uncertain transport failure reuses request ID + canonical intent;
10. new deliberate Add after success receives a new request ID;
11. 409/503 is local and leaves mechanics/object sheet rendered;
12. changing encounter/generation/source/`binding_id` context clears stale retry identity;
13. `ThreatMechanicsPanel` has no Combat action/import regression;
14. P3C existing mechanics tests remain green.

### Existing Combat regressions

Run the owning existing tests for:

```text
GET/POST current Combat
HP delta + temp HP
initiative updates
active turn / advance turn
legacy generated-statblock Add
save/load/unload/new Combat
```

If a current owner has no tests, add the narrow missing regression required to prove P4 did not break it rather than claiming untested compatibility.

### Type/build/lint

Run the repository's current exact equivalents, including at minimum where applicable:

```bash
cd apps/live-control-ui
pnpm run typecheck
pnpm run build

# server focused tests
uv run pytest <exact focused combat/threat/play route tests>

# repository lint/static checks used by the lane
uv run ruff check <changed Python paths>
```

Record exact commands and exact results. Do not state they passed unless run at the implementation/evidence head.

### Steward / diff proof

```bash
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-add-to-combat.md \
  --pr <N>

git diff --check
git diff --name-only <PIN_AT_DISPATCH>...HEAD
```

### Static boundary audit

At minimum:

```bash
rg -n "ofConks|Add to Combat|add.*combat|Combat" \
  apps/live-control-ui/src/playSurface \
  apps/live-control-ui/src/statblocks/projection
```

Verify:

```text
no ofConks/campaign bridge enters product path
ThreatMechanicsPanel stays Combat-free
Add control is Play-owned
no statblock body is sent by client
no World/Run/Runbook mutation is introduced
```

### Live/dogfood proof

If a native `/play` product host exists at implementation time, do one minimal live proof:

```text
open an authored Threat
choose one exact mechanics attachment
set count/team
Add to Combat
confirm exact entities appear in current Combat
mutate HP/initiative
confirm source/mechanics refs remain pinned
```

If native `/play` still does not exist, **do not block P4 merely for that missing host**. Prove the actual available owning boundaries instead:

```text
Play action component
→ real API contract
→ server exact authority admission
→ persisted current Combat
→ existing Combat mutation behavior
```

Record that native host dogfood is unavailable rather than pretending it ran.

### Roadmap review

At implementation completion answer:

```text
P4_HOIST_OBSERVATION
- Reused existing current Combat store/runtime? yes/no
- Server independently revalidated exact Threat + exact `binding_id` + coherent revision triple? yes/no
- Combat entity retains exact immutable Threat/`binding_id`/revision provenance? yes/no
- Two bindings sharing one revision triple remained independently actionable? yes/no
- Replay bound to Combat-local `combat_generation_id` rather than recyclable `encounter_id`? yes/no
- Combat persist-established that generation on GET bootstrap before Add, and Add never minted it? yes/no
- Load of a post-P4 save minted G2 and cleared imported `add_receipts` without rewriting the save or stripping entity provenance? yes/no
- Seed name/AC/HP used predecessor identity/defenses/vitality fields with fail-closed AC/HP rules? yes/no
- Mutable HP/init/conditions/team remain Combat-only? yes/no
- Any World/Run/Runbook/statblock writeback? yes/no
- Any generic transaction/CAS primitive required? yes/no
- Any second non-Combat consumer of this exact mutation contract? yes/no
- Any DungeonMind/DungeonMindDnD contract change required? yes/no
- Does P5 proposal/adoption remain independently useful? yes/no
```

Expected if this design holds:

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
P4 graduated the explicit exact Threat→Combat transition onto the existing Combat
runtime. Attachment identity is `binding_id` with a coherent revision triple; replay
is bound to Combat-local `combat_generation_id` persist-established on the current-Combat
bootstrap read before Add. Load mints a new generation and clears imported Add receipts.
Mutable combat state remains Combat-owned. No second Combat store, generic
runtime/transaction, or DungeonMind kernel contract was justified. P5 remains independent.
```

---

## §8 Required review handback

Record:

1. Review Cycle N + exact PR/head SHA;
2. exact implementation base SHA;
3. P3C source contract consumed, including exact reviewed/merge anchors if still relevant;
4. actual route path and request/response schema names;
5. exact Combat schema additions;
6. exact request receipt/replay semantics, including the single Combat-owned generation bootstrap rule, proof that Add never mints, and proof that load mints G2 and clears imported `add_receipts`;
7. exact Combat lock owner and every current writer brought under it;
8. happy-path exact Threat + `binding_id` + revision tuple used in proof;
9. shared-triple multi-binding proof: two `binding_id`s with one revision triple remain independently actionable;
9b. predecessor seed proof: Ironhide Brute name/AC/HP plus AC/HP fail-closed cases;
10. all failure-code/no-write proofs;
11. concurrency/lifecycle evidence, including absent/legacy/stable/first-Add-retry/concurrent bootstrap, new/load/unload rotation, post-P4 save/load receipt isolation, and receipts-without-generation fail-closed;
12. legacy Combat compatibility evidence;
13. frontend exact-action evidence;
14. confirmation client sends no statblock body;
15. confirmation neutral mechanics panel remains Combat-free;
16. confirmation no P3B completion is claimed;
17. confirmation no World/Runbook/Run/mechanics mutation occurs;
18. changed paths vs §4/bounded discovery;
19. exact test/typecheck/build/lint/preflight results with provenance;
20. nano-commit/fix story;
21. roadmap disposition;
22. successor boundary: P5 remains false/unimplemented.

One formal reviewer judgment against one distinct head SHA counts as one review cycle.

---

## §9 Acceptance rubric

PASS only if all are true:

- [ ] One independently useful capability: explicit exact Threat→existing Combat transition.
- [ ] Existing `dmb_combat_encounter_state_v1` / current-Combat store remains the Combat owner; no second store.
- [ ] Action is explicit and Play-owned; neutral mechanics panel remains read-only.
- [ ] Zero/non-available bindings are not actionable.
- [ ] Multiple exact bindings never collapse to a hidden winner.
- [ ] Team/count are explicit visible inputs.
- [ ] Client sends exact refs only, not statblock body/name/HP.
- [ ] Server independently validates Run/campaign/current encounter and `combat_generation_id`.
- [ ] `combat_generation_id` is persist-established by Combat-owned GET bootstrap before Add is actionable; Add never mints, including never for absent or legacy current files.
- [ ] Absent-state bootstrap, legacy-state bootstrap, stable repeated GETs, first-Add retry, concurrent bootstrap, and new/load/unload rotation are proven.
- [ ] Server independently hydrates exact Threat at exact graph scope.
- [ ] Server selects only the exact requested `binding_id` and requires its revision triple to cohere.
- [ ] Two bindings sharing one revision triple remain independently actionable.
- [ ] Server verifies immutable revision + validation digest coherence.
- [ ] Seed name/AC/HP come from predecessor fields `identity.name`, unique default `armor_classes[].value`, and method-specific `vitality.hit_points` (`displayed_average` for formula, `fixed_value` for fixed), with the Ironhide Brute fixture proving `name="Ironhide Brute"`, `ac=15`, `hp=68`.
- [ ] Combat entities retain immutable exact Threat + `binding_id` + revision provenance.
- [ ] HP/temp HP/init/conditions/team/notes remain Combat-only mutable fields.
- [ ] No World/Run/Runbook/statblock writeback occurs.
- [ ] Same request ID + same intent against the same `combat_generation_id` is idempotent.
- [ ] Same request ID + different intent, including a different `binding_id`, conflicts without write.
- [ ] Recycled `encounter_id` via new/load cannot satisfy an older request receipt.
- [ ] `load_combat_save` of a post-P4 save mints G2 and clears loaded `add_receipts` in the same current-Combat write; the save file and entity provenance remain intact; old G1 tokens 409 and cannot replay or conflict in G2.
- [ ] GET bootstrap of non-empty `add_receipts` with missing generation fail-closes (`500`) without minting or dropping receipts.
- [ ] Current Combat mutation/lifecycle writers serialize so no concurrent lost updates occur.
- [ ] Legacy current Combat remains readable/mutable.
- [ ] Existing legacy generated Add remains valid unless separately rebriefed.
- [ ] No generic transaction/CAS framework is introduced.
- [ ] No P3A/P3B capability is silently implemented or claimed.
- [ ] No `ofConks*` bridge enters product code.
- [ ] No DungeonMind/DungeonMindDnD contract change is required.
- [ ] Actual changed paths remain within §4/bounded discovery.
- [ ] Focused server/frontend/concurrency/regression evidence is exact and independently rerunnable.
- [ ] Roadmap review preserves the P4/P5 boundary unless evidence explicitly changes architecture.

REQUEST CHANGES for repairable implementation/evidence gaps.

STOP/rebrief for authority/scope mismatch.

---

## Stop conditions

Stop and report rather than expanding if any of these becomes true:

- current Combat has been replaced by a materially different owner and this design would create a second store;
- exact Threat hydration can no longer prove exact world/campaign/scope/revision identity;
- exact mechanics attachment cannot be identified by `binding_id` on the current hydration contract;
- `binding_id` cannot be carried without a new DungeonMind/DungeonMindDnD contract;
- server must trust a caller-supplied statblock body to perform Add;
- exact Add requires a new DungeonMind/DungeonMindDnD contract;
- Combat-local `combat_generation_id` cannot be persist-established on GET bootstrap / new / load / unload without introducing a generic transaction/CAS framework;
- GET `/api/live/combat/current` cannot persist generation under the Combat lock, or Add would have to mint for absent/legacy current files;
- `load_combat_save` cannot mint a new generation and clear imported `add_receipts` in the same current-Combat write without introducing a generic transaction/CAS framework or rewriting save files;
- unique-default AC or method-specific HP seed cannot be derived from the current exact-revision contract without inventing fields;
- safe concurrent mutation requires a generic transaction/CAS framework rather than a Combat-local file lock;
- action requires persistent active mechanics selection in Run;
- action requires World or mechanics binding mutation;
- implementation needs P3B graph-reference/occurrence/host work to make the server transition correct;
- implementation begins a Combat tracker redesign or new encounter authoring workflow;
- another active lane owns `combat_state.py`, `combat_saves.py`, `routes/live.py`, or the P3C Play action paths and cannot be serialized cleanly.

Report:

```text
Stop condition:
Invariant clause affected:
Why current P4 mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed split/rebrief:
State-authority update needed:
```

---

## §10 Successor boundary

If P4 lands without contradictory evidence, the next roadmap capability remains:

```text
P5 — shared proposal/adoption seam in Buddy
```

P5 is distinct because P4 is an explicit operator-command mutation into an existing runtime, while P5 concerns proposal/adoption workflows and governed mutation seams across surfaces.

P4 must not pre-build P5.

Likewise, P4 does not imply P3A/P3B are complete. Those remain independently useful Play capabilities whose future host/integration work can consume this exact Add contract without changing Combat authority; P3B is currently NON-DISPATCHABLE behind the post-C2S27 sequence.