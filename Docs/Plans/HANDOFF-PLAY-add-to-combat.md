---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: Playable Architecture Graduation / P4
  - Flow: PLAY
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
**Status:** DESIGNED — staged successor and directly dispatchable when the steward selects P4 and re-anchors the implementation branch. **No prerequisite exists merely because another handoff/document is absent from `main`, and P4 does not require P3A/P3B implementation merely to establish this exact Threat→Combat transition.**  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-add-to-combat.md`  
**Conversation/workstream:** `Playable Architecture Graduation / P4`  
**Flow / owner:** `PLAY`  
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

> **`Add to Combat` is an explicit, idempotent authority transition from one exact resolved Threat at one exact World Graph scope plus one exact immutable mechanics attachment `(statblock_id, revision_id, definition_digest)` into the existing `dmb_combat_encounter_state_v1` current Combat. The server independently revalidates the Run/campaign, exact Threat/scope, exact mechanics binding, immutable revision identity, and validation digest before creating entities. The client never submits a statblock body, never chooses first/latest/display-name mechanics, and never silently selects one of multiple exact bindings. Each created Combat entity retains immutable source Threat + statblock-revision references while Combat owns all mutable combat fields. A replay of the same request identity and same canonical intent creates nothing twice; the same request identity with different intent conflicts. All writers of the single current-Combat file serialize at the same Combat-owned mutation boundary so exact Add cannot lose concurrent HP/initiative/lifecycle changes. P4 does not create a second Combat store, does not add generic transaction/CAS infrastructure, does not implement missing P3B product behavior, and does not mutate World/Runbook/Run/mechanics authority.**

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
| Revalidate exact statblock revision triple | No; authority clause | Existing DungeonMindDnD/statblock contract | **Include / reuse** |
| Seed name/AC/HP from exact immutable revision | No; creation clause | Existing statblock definition | **Include** |
| Persist exact Threat + revision provenance on Combat entity | No; traceability clause | Combat schema extension | **Include** |
| Idempotent response-loss retry | No; mutation safety | Combat-owned request receipt | **Include** |
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
| Most dangerous ambiguity | Threat has multiple exact mechanics bindings and UI/server chooses array[0] or “primary.” **Forbidden.** Each exact available attachment is independently actionable. |
| Most dangerous mutation race | Add reads current Combat, HP/initiative/new/load mutates it, Add writes stale copy and loses the other change. All current-Combat writers must share one Combat mutation lock. |
| Most dangerous response-loss sequence | Server commits entities, response is lost, client retries and duplicates combatants. Request receipt makes exact replay a no-op. |
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
   - `apps/live_control_server/integrations/dungeonmind_statblocks/generated/models/statblock_revision_resource_v1.py`;
   - exact statblock fixture(s) under `tests/fixtures/statblocks/v1/`.
7. file mutation primitive:
   - `apps/live_control_server/services/registry_file_lock.py`.
8. PR #578 only as historical/dogfood interaction evidence; never import `ofConks*` or campaign-specific bridge data.

### Current design-anchor facts

At `53aaf9a566cfd40dd09f1a4c9723276cefa2a98a`:

```text
P3C exact mechanics read/render seam exists.
P3C Play composition wrapper exists but does not complete P3B.
Threat mechanics identity is statblock_id + revision_id + definition_digest.
Threat hydration is already server-owned and can return exact immutable revisions.
Existing Combat state is dmb_combat_encounter_state_v1 in current_combat.json.
CombatEntity already owns mutable hp/temp_hp/init/conditions/team/notes.
Existing Combat has a legacy generated-statblock Add path using artifact/corpus provenance.
Existing Combat save/load/new/unload lifecycle writes the same current-combat file.
registry_mutation_lock already exists as a repository file-mutation primitive.
```

P4 should replace none of those owners. It extends them narrowly.

### Authority matrix

| Fact/state | Owner before Add | Owner after Add |
|---|---|---|
| Threat identity | World Graph | World Graph; copied exact ref as immutable Combat provenance |
| World graph scope/revision used for admission | World Graph projection | immutable source ref on created Combat entity/receipt |
| Mechanics binding identity | World→DungeonMindDnD/statblock attachment | immutable exact ref on Combat entity/receipt |
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

  source: {
    run_id: UUID
    threat_node_id: string
    world_id: string
    campaign_id: string
    scope_mode: campaign | world
    graph_revision_id: string
  }

  mechanics: {
    statblock_id: string
    revision_id: string
    definition_digest: string
  }

  team: pc | ally | enemy | neutral
  count: 1..20
}
```

Exact wire nesting/naming may follow repository style, but these semantics may not be weakened.

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
5. load current Combat;
6. missing current Combat → `404`, no write;
7. require request `encounter_id` to equal current Combat `encounter_id` → otherwise `409`, no write;
8. require Combat campaign, request campaign, and Run campaign to agree → otherwise `409`, no write;
9. construct the existing exact Threat hydration request from request world/campaign/scope/revision + exact Threat node ID with mechanics included;
10. call existing server `query_threats_with_hydration(...)` / current equivalent;
11. require response world/campaign/scope/revision to equal the requested exact tuple;
12. require exactly one exact returned Threat node ID match;
13. find the **exact requested mechanics triple** among available hydrated bindings;
14. zero exact matching available binding → `409`, no write;
15. multiple exact matches for the same requested identity → integrity failure `500`, no write;
16. require returned revision identity to equal the requested binding triple;
17. require revision validation receipt/digest coherence using current statblock contract;
18. incoherent server/hydration payload → `500`, no write;
19. hydration dependency unavailable → `503`, no write;
20. derive name/AC/max HP/current HP seed only from that exact immutable revision;
21. enter the Combat mutation lock;
22. re-read current Combat and re-check encounter/campaign + request receipt under the lock;
23. exact replay → return prior entity IDs/current Combat with `replayed=true`, no append;
24. request-ID intent conflict → `409`, no write;
25. append `count` Combat entities + durable receipt in one atomic current-Combat write;
26. return `replayed=false`.

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

ExactStatblockRevisionRef {
  statblock_id
  revision_id
  definition_digest
}
```

Each newly created exact-Threat entity carries both.

Existing legacy Combat entities without these refs remain readable/mutable.

Do not migrate or rewrite old entities merely because the model gains optional fields.

`CombatSource` may gain a new explicit value such as:

```text
exact_threat
```

Use the smallest vocabulary change consistent with existing model style.

### G. Seed values vs mutable Combat values

Creation seeds:

```text
name    ← exact revision definition.name
ac      ← exact revision definition.armor_class
max_hp  ← exact revision definition.hit_points.average
hp      ← same max_hp seed
team    ← explicit operator input
init    ← existing unset/default Combat behavior
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

Add a Combat-owned receipt representation, conceptually:

```text
CombatAddReceipt {
  request_id: UUID
  encounter_id: string
  source_threat_ref: CombatThreatSourceRef
  statblock_revision_ref: ExactStatblockRevisionRef
  team: CombatTeam
  count: int
  entity_ids: string[]
}
```

Stored on `CombatEncounterState` as an optional/default-empty collection or equivalent current-encounter structure.

Canonical replay semantics:

```text
same request_id
+ same encounter_id
+ same exact source ref
+ same exact mechanics ref
+ same team
+ same count
  → replay success
  → no new entities
  → same original entity_ids

same request_id
+ any material intent difference
  → 409
  → no write
```

Receipts are encounter-local. Do not invent a cross-encounter global receipt ledger in P4.

If implementation proves current encounter lifecycle can recycle the same encounter identity in a way that makes safe replay impossible, **stop/rebrief** rather than hiding the problem with a generic transaction system.

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
| Current Combat missing | 404 / no write |
| Encounter mismatch | 409 / no write |
| Run/request/Combat campaign mismatch | 409 / no write |
| Exact Threat absent | 409 / no write |
| Requested mechanics triple absent/not available | 409 / no write |
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
| Modify | `apps/live_control_server/services/combat_state.py` | exact source/revision refs, receipt, exact Add mutation, Combat-local serialization |
| Modify if needed | `apps/live_control_server/services/combat_saves.py` | make lifecycle writers share the same current-Combat lock |
| Modify | `apps/live_control_server/routes/live.py` | exact Add route/request/response transport under existing Combat API owner |

### Server — read/reuse, not redesign

```text
apps/live_control_server/services/play_run_registry.py
apps/live_control_server/services/threat_query_hydration.py
apps/live_control_server/services/registry_file_lock.py
apps/live_control_server/integrations/dungeonmind_statblocks/generated/**
```

`registry_file_lock.py` is read-only unless current implementation cannot reuse it without a tiny bug fix; if a generic primitive change becomes necessary, stop/rebrief before editing.

### Frontend — expected production lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/playSurface/reference/PlayThreatMechanicsSection.tsx` | render Play-owned Add affordance next to exact binding(s), keep neutral panel read-only |
| Create | `apps/live-control-ui/src/playSurface/reference/PlayAddToCombatControl.tsx` | explicit team/count + request identity + local mutation status |
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
+ encounter_id
+ exact Threat source tuple
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

### C. Exact mechanics tuple

```text
statblock_id
revision_id
definition_digest
```

Every field participates in canonical replay intent.

### D. No body trust

The route must be safe if a malicious/stale client changes any presentation value it saw earlier.

Therefore presentation values are not accepted as authoritative request fields.

The server independently obtains the exact immutable revision through the existing governed hydration path and derives Combat seeds from it.

### E. Multi-binding command semantics

For Threat bindings A and B:

```text
Add A
  → request exact triple A

Add B
  → request exact triple B
```

The server does not know or infer which one is “active.” It proves only that the requested exact triple is an available accepted attachment for the exact Threat at the exact requested graph revision.

### F. Entity creation

For count N, create N distinct Combat entity IDs in deterministic current repository style.

All N entities receive the same immutable source/mechanics refs and explicit team, but remain separate mutable Combat entities.

Do not persist the entire statblock revision definition inside each entity unless the existing Combat schema already requires a bounded creation snapshot. Exact refs are the provenance contract.

### G. Legacy compatibility

Existing Combat JSON may lack:

```text
source_threat_ref
statblock_revision_ref
add_receipts
```

It must continue to deserialize and support existing HP/initiative/turn/lifecycle operations.

P4 must not force a migration rewrite merely on read.

Legacy generated-statblock Add remains functional unless the slice explicitly proves it should be retired; retiring it is not required for P4.

### H. Combat lifecycle and receipt scope

A receipt belongs to the loaded current encounter.

The UI owns a fresh `request_id` per explicit Add intent and may reuse it only to retry that same unresolved command.

When the selected encounter/action context changes, discard the old retry identity and require a fresh operator action.

Do not automatically retry an old request across a new/load/unload Combat lifecycle transition.

### I. UI local state

`PlayAddToCombatControl` should own only transient form/request state:

```text
team
count
request_id for current unresolved intent
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

1. **Happy path:** exact Threat + exact available revision adds one Combat entity.
2. **Count:** count > 1 creates exactly N distinct entities.
3. **Seed authority:** name/AC/max HP/current HP come from the independently hydrated exact immutable revision, not caller fields.
4. **Exact source refs:** created entities retain exact Run/Threat/world/campaign/scope/graph-revision provenance.
5. **Exact mechanics refs:** entities retain exact statblock/revision/digest provenance.
6. **Multi-binding:** requesting B adds B even if A appears first; no array-order/primary fallback.
7. **Missing exact mechanics triple:** 409 and byte-for-byte current Combat unchanged.
8. **Run campaign mismatch:** 409/no write.
9. **Encounter mismatch:** 409/no write.
10. **Missing Run:** 404/no write.
11. **Missing current Combat:** 404/no write.
12. **Hydration dependency unavailable:** 503/no write.
13. **Hydration response scope mismatch:** fail closed/no write.
14. **Duplicate exact Threat hit/internal response ambiguity:** 500/no write.
15. **Binding/revision identity or digest incoherence:** 500/no write.
16. **Exact replay:** same request ID + same canonical intent returns original entity IDs with no duplicate.
17. **Intent conflict:** same request ID + changed team/count/source/mechanics → 409/no write.
18. **Concurrent distinct exact Adds:** both commits survive.
19. **Add vs HP mutation:** both commits survive; HP change is not lost.
20. **Add vs initiative/entity mutation:** both commits survive.
21. **Add vs new/load/unload lifecycle:** serialized deterministic valid result; no torn/malformed current Combat.
22. **Legacy state:** pre-P4 Combat JSON without new refs/receipts loads and existing mutation routes remain valid.
23. **Post-add mutability:** HP/temp HP/init/conditions/team changes preserve immutable source/mechanics refs and never call World/Run/statblock write paths.

Use an exact revision fixture or governed mocked hydration response. Do not fake the core admission by directly injecting a caller-provided statblock body into the Add service.

### Frontend proof

Required component/API tests:

1. one exact available binding → one Add affordance tied to its exact triple;
2. multiple available bindings → one explicit affordance per exact binding; no hidden winner;
3. unavailable/partial/integrity-failed binding → not actionable;
4. team/count are visible and submitted exactly;
5. request contains exact Run/Threat/world/campaign/scope/revision + mechanics triple;
6. request contains **no statblock definition/body/name/HP**;
7. no action context → P3C mechanics remains read-only;
8. double click/in-flight interaction produces one request;
9. retry after uncertain transport failure reuses request ID + canonical intent;
10. new deliberate Add after success receives a new request ID;
11. 409/503 is local and leaves mechanics/object sheet rendered;
12. changing encounter/source/binding context clears stale retry identity;
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
- Server independently revalidated exact Threat + exact mechanics? yes/no
- Combat entity retains exact immutable Threat/mechanics provenance? yes/no
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
runtime. Exact source/mechanics identity is retained as provenance while all mutable
combat state remains Combat-owned. No second Combat store, generic runtime/transaction,
or DungeonMind kernel contract was justified. P5 remains independent.
```

---

## §8 Required review handback

Record:

1. Review Cycle N + exact PR/head SHA;
2. exact implementation base SHA;
3. P3C source contract consumed, including exact reviewed/merge anchors if still relevant;
4. actual route path and request/response schema names;
5. exact Combat schema additions;
6. exact request receipt/replay semantics;
7. exact Combat lock owner and every current writer brought under it;
8. happy-path exact Threat + mechanics tuple used in proof;
9. multi-binding proof and selected exact attachment;
10. all failure-code/no-write proofs;
11. concurrency/lifecycle evidence;
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
- [ ] Server independently validates Run/campaign/current encounter.
- [ ] Server independently hydrates exact Threat at exact graph scope.
- [ ] Server selects only the exact requested statblock/revision/digest attachment.
- [ ] Server verifies immutable revision + validation digest coherence.
- [ ] Seed name/AC/HP come from exact immutable revision.
- [ ] Combat entities retain immutable exact Threat + mechanics provenance.
- [ ] HP/temp HP/init/conditions/team/notes remain Combat-only mutable fields.
- [ ] No World/Run/Runbook/statblock writeback occurs.
- [ ] Same request ID + same intent is idempotent.
- [ ] Same request ID + different intent conflicts without write.
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
- exact statblock binding cannot be identified by `(statblock_id, revision_id, definition_digest)`;
- server must trust a caller-supplied statblock body to perform Add;
- exact Add requires a new DungeonMind/DungeonMindDnD contract;
- safe response-loss replay cannot be represented encounter-locally without a new cross-encounter identity model;
- current Combat lifecycle recycles encounter identity in a way that makes request replay unsafe and cannot be fixed locally;
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

Likewise, P4 does not imply P3A/P3B are complete. Those remain independently dispatchable Play capabilities whose future host/integration work can consume this exact Add contract without changing Combat authority.