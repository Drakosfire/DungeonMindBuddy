# PR Tracker — Play + World-Object Combat Projection

**Status:** PRE-DISPATCH / KERNEL-CUTOVER GATED  
**Date:** 2026-08-07  
**Repository:** `Drakosfire/DungeonMindBuddy` for coordination; implementation ownership may move per slice after the DungeonMind kernel cutover  
**Roadmap authority:** [`../Roadmaps/ROADMAP-play-world-object-combat-projection.md`](../Roadmaps/ROADMAP-play-world-object-combat-projection.md) — landed on `main` at `e0dc0a098d1306694e0cfbaccf80ef97879ca884`  
**Parent decisions:**
- [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md)
- [`../Design/ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md)
- [`../Design/DESIGN-authored-threat-statblock-domain-contract.md`](../Design/DESIGN-authored-threat-statblock-domain-contract.md)
- [`PR-TRACKER-threat-statblock-authoring-projection.md`](PR-TRACKER-threat-statblock-authoring-projection.md)

This tracker sequences the smallest useful PRs needed to make Play a first-class surface, make Combat Tracker its first workspace, add first-class NPC and Player Character world objects, and prove exact world-object → mechanics → runtime projection during live play.

The sequence is intentionally **not** a full Play rewrite. Threat is the first runtime proof because its exact StatblockRevision projection path is already the strongest implemented domain. NPC and Player Character then prove that the same substrate supports different world-object semantics and different mechanics authorities.

---

## 1. Dispatch rules

1. One implementation PR proves one independently useful capability and one authority invariant.
2. Re-anchor every code slice after the DungeonMind graph-kernel cutover; do not dispatch against assumed old paths.
3. Threat, NPC, and Player Character remain distinct concrete world-object kinds.
4. Shared code may own projection envelopes, capability routing, common cards, and runtime adapter protocols; domain fields remain in domain adapters/contracts.
5. Do not create a universal `Character` schema to make Combat convenient.
6. Do not invent a `CharacterRevision` contract before auditing the actual PC generator/character-sheet authority.
7. Combat normal-path ingress may not use corpus Markdown, artifact path, filename, display name, or implicit latest revision.
8. Exact consumers retain exact immutable source identity through save/reload.
9. Runtime HP/init/conditions/notes never mutate graph truth or accepted mechanics.
10. Play publishes into the existing Surface Interaction Layer; it does not own duplicate Nav/Tool/Edit/Agent/Projection hosts.
11. The app-scoped World Graph lens/projection provider remains the shared read path. Equivalent Play requests should reuse admitted resident projection state.
12. Legacy combat saves receive explicit compatibility behavior; never fabricate exact source identity that historical data did not record.
13. Every slice that replaces a legacy path includes a demolition ledger.
14. Every user-facing gate ends with a real dogfood scenario, not only unit tests.
15. Cross-repo slices must state which repository owns the contract and which repository owns the consumer adapter.

Required demolition declaration in implementation PR bodies:

```text
Replaced path:
Deleted in this PR: yes | no
If no, retained reason:
Named remaining consumer:
Required deletion owner:
```

Required authority declaration:

```text
Reads authority from:
Writes authority to:
Explicitly cannot mutate:
Exact identities persisted:
Fallbacks prohibited:
```

---

## 2. Program gates

| Gate | Status | Meaning |
|---|---|---|
| `KERNEL-0` | BLOCKING | DungeonMind becomes the re-anchored World Graph kernel and exposes stable exact object/projection contracts to DungeonBuddy. |
| `WORLDOBJ-1` | BLOCKED ON `KERNEL-0` | Threat/NPC/PlayerCharacter can be returned as distinct exact world-object projections. |
| `PLAY-1` | BLOCKED ON `KERNEL-0` | `/play` is a first-class Surface Interaction consumer with Combat workspace mounted. |
| `COMBAT-1` | BLOCKED ON `KERNEL-0` | Combat persistence can retain exact object/resource source locators separately from mutable state. |
| `MAGIC-P1` | BLOCKED | Exact Threat → Play → CombatantInstance → exact Threat/statblock reopen. |
| `MAGIC-P2` | BLOCKED | Exact NPC → Play → optional mechanics → CombatantInstance → NPC reopen. |
| `MAGIC-P3` | BLOCKED | Exact PlayerCharacter → Play → audited mechanics/state adapter → combat → PC reopen. |
| `DOGFOOD-PLAY` | BLOCKED | Mixed PC/NPC/Threat live combat with warm graph projection reuse and measured interaction latency. |

`MAGIC-P1` is the earliest useful live proof and should not wait for complete NPC/PC mechanics integration.

---

## 3. PR series overview

| ID | Status | Primary repo after re-anchor | Mission | Depends on |
|---|---|---|---|---|
| `PWO00` | DONE — DOCS ON MAIN | DungeonMindBuddy | Freeze roadmap + PR sequence. | — |
| `PWO01` | NEXT AFTER CUTOVER | DungeonMind + DungeonMindBuddy | Re-anchor graph object/projection/resource-binding contracts and PC mechanics inventory. | `KERNEL-0` |
| `PWO02` | BLOCKED | DungeonMind | First-class NPC world-object contract + projection. | `PWO01` |
| `PWO03` | BLOCKED | DungeonMind | First-class Player Character world-object contract + migration/link from party anchors. | `PWO01` |
| `PWO04` | BLOCKED | DungeonMindBuddy | Shared world-object projection envelope/capability adapter characterized across Threat/NPC/PC. | `PWO02`, `PWO03` |
| `PLAY01` | BLOCKED | DungeonMindBuddy | `/play` route + Play Surface Interaction publication + Combat workspace host. | `PWO01` |
| `COMBAT01` | BLOCKED | DungeonMindBuddy | Exact source locator + bounded snapshot persistence; legacy identity compatibility. | `PWO01` |
| `PLAY02` | BLOCKED | DungeonMindBuddy | Compact Play Combat Tracker UX over existing server-backed mutations. | `PLAY01`, `COMBAT01` |
| `COMBAT02` | RE-ANCHOR | DungeonMindBuddy | Exact Threat/StatblockRevision → deterministic CombatantSeed adapter. | Threat exact projection + `COMBAT01` |
| `PLAY03` | BLOCKED | DungeonMindBuddy | Play Find/open/add/reopen Threat proof using shared projection infrastructure. | `PLAY02`, `COMBAT02` |
| `NPC01` | BLOCKED | DungeonMind + DungeonMindBuddy | Freeze optional NPC mechanics-binding representation; NPC CombatantSeed adapter. | `PWO02`, `COMBAT01` |
| `PLAY04` | BLOCKED | DungeonMindBuddy | NPC projection + truthful Add-to-combat capability. | `PLAY03`, `NPC01`, `PWO04` |
| `PC01` | BLOCKED | DungeonMind + owning PC system | Audit/freeze exact PC mechanics and persistent-state authority. | `PWO03` |
| `PC02` | BLOCKED | DungeonMindBuddy | PC CombatantSeed + persistent-state/encounter-overlay adapter. | `PC01`, `COMBAT01` |
| `PLAY05` | BLOCKED | DungeonMindBuddy | Player Character projection + combat activation/reopen. | `PLAY04`, `PC02`, `PWO04` |
| `PLAY06` | BLOCKED | DungeonMindBuddy | Warm projection/performance telemetry + mixed live dogfood hardening. | `PLAY05` |

Some contract PRs may move fully into `DungeonMind` after cutover. This tracker remains the product sequencing authority unless superseded by a deliberately linked cross-repo tracker.

---

## 4. `PWO01` — Kernel cutover re-anchor and contract inventory

**Mission:** after DungeonMind becomes the graph kernel, produce one exact inventory of the contracts DungeonBuddy will consume before any new object type is implemented.

**This is primarily a contract/audit PR.** It should be small enough that downstream PRs can cite exact names, schemas, paths, and base SHAs instead of carrying assumptions from DungeonMindBuddy's predecessor graph.

### Required inventory

```text
World object identity
  world_id
  object/node id
  concrete kind
  campaign/world tenancy
  immutable graph revision identity

Projection request/response
  exact world/campaign/scope/focus/revision behavior
  relationship payload
  object-specific payload seam
  cache/request identity

External generated-resource binding
  resource kind
  resource id
  revision id
  digest
  binding role

DungeonBuddy adapter boundary
  exact consumer types
  error states
  stale/revision behavior
```

### PC audit required in this slice

Find the actual current authority for:

```text
PC stable identity
character-sheet/build persistence
revision/version identity if any
current HP/resources persistence
ruleset/version declaration
combat minimum derivation
save/reload semantics
```

The handback must explicitly answer:

> Can the existing PC system provide an exact mechanics reference suitable for a pinned Play/Combat consumer? If yes, name it. If no, identify the smallest missing contract without inventing its implementation in this PR.

### Explicit non-goals

- no NPC implementation;
- no PlayerCharacter implementation;
- no Play route;
- no combat migration;
- no universal object framework.

### Exit proof

A downstream coding agent can write exact tests against the new kernel contracts without looking at predecessor union-store types or guessing PC authority.

---

## 5. `PWO02` — First-class NPC world object

**Mission:** the kernel can represent and project one persistent fictional NPC as a concrete world-object kind distinct from Threat and Player Character.

### Minimum contract

Required world-facing fields should remain bounded:

```text
exact object identity
kind = npc
name
aliases[]
summary / description
world/campaign scope
relationships
provenance / evidence pointers under kernel policy
image refs when the general object contract supports them
```

Do not force occupation, motivations, personality, secrets, statblock, or other optional content into universal required kernel fields unless existing graph architecture already models them as assertions/relationships.

### Identity rule

Hostility or combat participation does not change object kind.

```text
Lysandra as ally → NPC
Lysandra temporarily hostile → same NPC
Lysandra in combat → same NPC + runtime instance
```

### Extraction/authoring compatibility

The slice must identify how existing generic actor/NPC extraction maps into `npc` without converting existing Threat objects or PC party anchors.

### Exit proof

Exact projection of one known NPC returns `kind=npc`, stable identity, useful summary, and graph relationships through the kernel's normal projection path.

---

## 6. `PWO03` — First-class Player Character world object

**Mission:** a Player Character becomes a first-class world object rather than only a deterministic party anchor or generic character label.

### Minimum world-facing contract

```text
exact object identity
kind = player_character
name
aliases[]
summary / description where available
world/campaign scope
party membership relationships
other graph relationships
provenance / import authority
image refs when supported
```

### Migration / linking requirement

Current deterministic party-anchor identity is valuable and must not be casually duplicated.

The PR must define one of:

1. promote/link the existing stable party anchor to the new PlayerCharacter object identity; or
2. perform an explicit identity migration with deterministic mapping and diagnostics.

Prohibited outcome:

```text
Baergrom (party anchor)
Baergrom (new PlayerCharacter)
```

as two silently independent durable graph identities.

### Rich PC detail

This slice creates the object contract and identity path. It does not need to solve all PC-action extraction. It must, however, leave a clear graph seam for richer PC assertions/relationships rather than treating party membership as the complete PC model.

### Mechanics rule

Do not copy a character sheet or invent a mechanics schema in the graph node. The exact PC mechanics reference remains owned by `PC01` after the audit from `PWO01`.

### Exit proof

One party member resolves through the normal graph projection as `player_character` with stable identity and party relationships, with no duplicate anchor identity.

---

## 7. `PWO04` — Shared world-object projection and capability adapter

**Mission:** characterize the smallest shared DungeonBuddy UI contract that can project Threat, NPC, and Player Character without erasing their domain differences.

This PR should extract shared infrastructure only after all three concrete kernel projections are inspectable.

### Candidate shared envelope

Conceptual only until re-anchor confirms exact names:

```text
WorldObjectProjection
  objectRef
  kind
  label
  summary
  scope
  images
  relationships
  provenanceSummary
  capabilities
  domainPayload
```

### Required proof

The same shared card/projection host can:

- render common identity/scope/relationships;
- dispatch Threat body to Threat projection;
- dispatch NPC body to NPC projection;
- dispatch PC body to PC projection;
- expose contextual capability descriptors without making a generic object own domain writes.

### `combat_projectable`

Characterize a contextual capability result such as:

```text
enabled
  action target / adapter key

disabled
  truthful domain reason
```

Examples:

```text
Threat with exact accepted binding → enabled
NPC with exact combat mechanics → enabled
NPC with no mechanics → disabled: No combat mechanics attached
PC before mechanics/state adapter lands → disabled: Player Character combat adapter unavailable
```

### Non-goals

- no broad capability registry redesign unless current Surface Interaction contract cannot express the requirement;
- no graph writes;
- no combat mutation.

---

## 8. `PLAY01` — First-class Play surface shell

**Mission:** make `/play` a real Surface Interaction consumer and mount Combat Tracker as its first workspace.

### Required behavior

- add Play route/key/nav entry through AppChrome;
- publish Play surface identity, campaign/session ambient context, and lease-scoped interaction contribution;
- retain the existing app-scoped World Graph lens and projection providers;
- render a Play-owned workspace region containing Combat Tracker;
- remove Combat Tracker from being conceptually a fourth top-level authority surface;
- keep older `/surface` compatibility only if a named consumer still requires it.

### Projection reuse proof

With an unchanged exact World Graph request:

```text
Plan → Build → Play
```

must not cause Play to create its own equivalent graph store/provider.

### Exit proof

`/play` loads under shared AppChrome, publishes a Play lease, and can open a shared graph-object projection without any combat feature changes yet.

---

## 9. `COMBAT01` — Combat source identity + persistence re-anchor

**Mission:** evolve persisted combat identity so runtime state can be derived from exact world/mechanics sources without making those sources mutable.

### Required new structure

Exact schema names may differ after re-anchor, but the persistence boundary must separate:

```text
source locator
  world object ref + kind
  binding/resource revision refs when present
  exact mechanics digest when applicable
  placement ref when present

bounded operational snapshot
  minimum values required to keep combat usable

runtime mutable state
  HP/init/temp HP/conditions/notes/team/defeated/etc.
```

### Legacy compatibility

Inventory existing fields including:

```text
statblock_path
statblock_artifact_id
statblock_title
corpus_fingerprint
source enum legacy values
```

Choose explicit behavior per old save version:

```text
load as legacy-unbound row
migrate only when exact identity is provable
reject malformed data with diagnostics
```

Never infer exact statblock/world-object identity from title/path/name merely to make migration appear complete.

### Immutability tests

Every current mutation route must prove source locator and snapshot identity remain unchanged under:

- HP set/delta;
- initiative change;
- team change;
- conditions;
- notes;
- defeated toggle;
- turn advancement;
- save/load/export.

### Exit proof

A synthetic exact-source combatant survives save/reload while mutable combat operations cannot alter its immutable locator.

---

## 10. `PLAY02` — Compact Combat Tracker workspace

**Mission:** make the existing server-backed combat functionality usable as the primary Play workspace before adding new object types.

### Preserve from existing runtime

- current encounter load/new/unload/save behavior where still authoritative;
- turn advancement;
- initiative mutation/sorting;
- HP/temp HP mutation;
- team, condition, note, defeated state;
- fail-soft behavior for non-critical dependencies.

### UX changes required

- initiative bands: `21+`, `16–20`, `11–15`, `6–10`, `1–5`;
- strong band separators and local/sticky column context;
- compact read mode instead of a table full of always-visible form controls;
- HP popover with `-12`, `+7`, direct set;
- Enter commit-and-blur; Escape cancel-and-blur;
- persistent/current turn controls appropriate for long roster scrolling;
- row click/name target reserved for exact world-object projection when bound.

### Exit proof

A real encounter can be run through the Play workspace with the existing mutation set at lower cognitive cost than the current React roster.

---

## 11. `COMBAT02` — Exact Threat revision to CombatantSeed

**Mission:** re-anchor and implement the already-designed exact StatblockRevision combat adapter against current post-cutover contracts.

This is the successor to the pre-designed `HANDOFF-sbw15-exact-revision-combat-adapter.md`, not a revival of its stale path assumptions.

### Input

```text
exact Threat world-object ref when available
exact Threat binding ref
exact statblock_id
exact revision_id
exact definition_digest
verified accepted StatblockRevision
bounded insertion options
```

### Output

Deterministic `CombatantSeed` containing:

```text
immutable source locator
bounded operational snapshot
suggested/default team/name/init inputs
warnings/adjudication markers required for honest operation
```

### Hard rules

- structured accepted revision only;
- no Markdown parsing;
- no old generated-artifact view;
- no latest revision;
- no copied full mechanics body;
- derivation failure creates no partial combatant.

### Exit proof

Create two independent combatant instances from one exact accepted Threat revision, mutate them independently, save/reload, and prove both retain the same exact immutable mechanics identity.

---

## 12. `PLAY03` — Threat cross-surface projection/runtime Magic Moment

**Mission:** prove the architecture end to end with the already-mature Threat domain.

### User path

```text
Plan or Build
→ inspect Tripod Null-Calf Threat
→ switch to Play
→ Find existing
→ same exact Threat object opens
→ Add to combat
→ combat row appears
→ mutate HP/init/status
→ click row name
→ reopen same Threat + exact StatblockRevision projection
```

### Required checks

- Play uses shared app-level graph lens/projection request identity;
- Threat Sheet is the same domain projection, not a Play fork;
- Add-to-combat is Play policy over shared exact object identity;
- exact revision/digest pinned at insertion;
- a newer accepted revision does not change active combatant;
- mechanics unavailable after insertion leaves bounded row operation functional and drilldown honestly unavailable;
- no second equivalent graph load introduced by Play.

### Gate

Passing this slice opens `MAGIC-P1` and allows immediate live dogfood even while NPC/PC integration continues.

---

## 13. `NPC01` — NPC exact mechanics attachment and CombatantSeed

**Mission:** allow an NPC to remain an NPC while optionally acquiring exact combat mechanics.

### Contract decision first

Using the `PWO01` kernel inventory, choose one exact representation:

```text
generic WorldObjectResourceBinding(resource_kind=statblock)
```

or

```text
typed NPCStatblockBinding built on the same exact external resource locator
```

Do not reuse `ThreatStatblockBinding` as the NPC domain model.

### Behavior

- NPC with no mechanics: valid projection, `combat_projectable` disabled truthfully;
- NPC with exact accepted statblock mechanics: enabled;
- seed retains NPC world-object identity plus exact mechanics identity;
- combat mutation never writes back into NPC graph truth;
- changing/rebinding the NPC later does not silently repin an active combatant.

### Exit proof

One Lysandra-like NPC with attached mechanics creates a runtime ally and reopens the same NPC projection after save/reload.

---

## 14. `PLAY04` — NPC projection + live combat activation

**Mission:** complete the user-facing NPC path through shared projection infrastructure.

### NPC sheet priority

Useful play information first:

```text
identity / portrait
role and concise description
current relevant relationships / affiliations
combat mechanics summary when attached
connected world objects
advanced provenance/evidence behind disclosure
```

Do not make the sheet a Threat Sheet with labels changed.

### Gate

Passes `MAGIC-P2` when an NPC can be found, inspected, added, run, reloaded, and reopened without object-kind or mechanics-authority confusion.

---

## 15. `PC01` — Exact Player Character mechanics + persistent-state contract

**Mission:** freeze the authority boundary intentionally deferred by this docs series.

This may be one design/contract PR plus a separate implementation PR if the current PC system lacks an exact revision identity.

### Required classification

For each combat-relevant PC field, record its owner:

| Field | Mechanics revision | Persistent character state | Encounter overlay | Derived |
|---|---:|---:|---:|---:|
| max HP | decide from actual system | | | |
| current HP | | expected | maybe overlay policy | |
| AC | decide | | | maybe |
| initiative modifier | decide | | | maybe |
| spell slots/resources | | expected | maybe transaction/overlay | |
| conditions | | maybe | maybe | |
| equipment-dependent values | decide | maybe | | maybe |

Do not fill this table by analogy to monsters. Ground it in the actual PC implementation and game-state persistence model.

### Required output

- exact stable PC mechanics locator;
- exact version/revision behavior or explicit versioned snapshot contract;
- persistent mutable character-state identity;
- conflict/update semantics between character state and encounter overlay;
- offline/reload behavior;
- upgrade/level-up behavior while an encounter is active.

### Stop condition

If the existing PC system cannot support exact pinned mechanics without a substantial redesign, stop and create a dedicated PC mechanics roadmap rather than hiding the work inside Combat.

---

## 16. `PC02` — Player Character CombatantSeed/state adapter

**Mission:** adapt the exact PC mechanics/state authority into the same bounded Combat runtime protocol without pretending it is a StatblockRevision.

### Required behavior

- exact `player_character` world-object identity retained;
- exact PC mechanics locator retained;
- persistent state read/write follows `PC01` authority;
- encounter-local fields stay in Combat;
- seed derives bounded tracker values;
- no copied full character sheet in graph or combat persistence;
- save/reload cannot fork persistent PC state silently.

### Exit proof

One PC can enter combat, mutate both encounter-local and intentionally persistent fields, reload, and prove every field returned to the correct owner.

---

## 17. `PLAY05` — Player Character projection + combat activation

**Mission:** complete the mixed-world-object combat experience.

### PC sheet priority

The first Play projection should emphasize what the GM needs during play without trying to reproduce every player-facing sheet feature:

```text
identity / portrait
class/level or equivalent mechanics summary from exact authority
AC / HP / movement and key play stats
party/world relationships
backstory/goals hooks when relevant
open exact/full PC mechanics view
```

### Gate

Passes `MAGIC-P3` when a PC can be found through the World Graph, inspected, activated in combat through its PC adapter, run/reloaded, and reopened as the same Player Character identity.

---

## 18. `PLAY06` — Warm projection + live dogfood hardening

**Mission:** prove the product feels fast enough to use during a real session, not merely that all identities are correct.

### Required mixed dogfood

Run at least one encounter containing:

```text
multiple Player Characters
one or more NPC allies
multiple Threat instances
```

### Instrument / record

```text
surface switch: Plan → Build → Play
World Graph projection reuse/coalescing
Find existing latency
object-open latency
exact mechanics hydration latency
Add-to-combat latency
HP mutation latency
turn-advance latency
save/reload latency
duplicate graph/mechanics requests
failure behavior when mechanics dependency is unavailable
```

### Performance success direction

No hard SLO is frozen by this tracker yet. The dogfood report must identify where delays are perceptible in live play and whether app-scoped graph state remains warm across surfaces.

If Play performs a duplicate equivalent World Graph load because of route-local ownership, treat that as an architectural regression, not a polish issue.

### Exit proof

The GM can switch surfaces, inspect exact objects, construct/modify combat, and continue turn operations without abandoning DungeonBuddy for manual notes because the graph/mechanics path is too slow or brittle.

---

## 19. Post-proof successor queue

These are real dogfood needs but intentionally remain successors to the projection/runtime spine.

| ID | Status | Mission |
|---|---|---|
| `PLAY-RULES` | LATER | Rules-term hover/focus projections from ingested rules authority. |
| `PLAY-SPAWN` | LATER | Structured summon/minion spawn templates from abilities/resources. |
| `PLAY-STATUS` | LATER | Status duration/tick semantics, beginning with end-of-turn expiry. |
| `PLAY-ENCOUNTER` | LATER | Rapid encounter construction/reconfiguration and exact placements. |
| `PLAY-PCSTATE` | LATER IF NEEDED | Broader persistent PC resource/state workflows beyond combat minimums. |
| `PLAY-PERF` | CONTINUOUS | Cache residency, prefetch/coalescing, unload/reload, observability. |

Do not pull these forward merely because the old combat tracker or live dogfood notes mention them. Pull them forward only when they are required to make the current projection/runtime proof usable.

---

## 20. Test and evidence expectations

Every implementation slice should include the smallest relevant combination of:

```text
kernel contract tests
exact identity/revision tests
projection tests
Surface Interaction lease/stale async tests
runtime immutability tests
save/load/export tests
legacy compatibility tests
unavailable dependency tests
cross-surface request reuse tests
user-path component tests
manual live dogfood evidence
```

High-value adversarial cases across the series:

- same display name, different object IDs;
- NPC and Threat with similar labels do not merge by UI convenience;
- party anchor and PlayerCharacter do not duplicate identity;
- NPC with no mechanics cannot be added but remains fully inspectable;
- exact mechanics revision missing before insertion blocks atomically;
- mechanics unavailable after insertion leaves bounded runtime operational;
- newer mechanics revision exists but active combatant remains pinned;
- stale retained Add-to-combat callback cannot act on a new surface/request lease;
- switching campaign/world invalidates inappropriate projection capability;
- legacy combat save cannot invent exact source identity;
- PC persistent state and encounter overlay do not fork silently.

---

## 21. Immediate dispatch logic

```text
DungeonMind kernel cutover
→ PWO01 re-anchor + PC authority audit

PWO01
├→ PWO02 NPC world object
├→ PWO03 PlayerCharacter world object
├→ PLAY01 Play shell
└→ COMBAT01 combat source/persistence re-anchor

PLAY01 + COMBAT01
→ PLAY02 compact combat workspace

Threat exact projection + COMBAT01
→ COMBAT02 exact Threat seed
→ PLAY03 Threat Magic Moment
→ begin live dogfood immediately

PWO02 + COMBAT01
→ NPC01 mechanics adapter
→ PWO04 shared object projection/capability characterization
→ PLAY04 NPC Magic Moment

PWO03 + PWO01 PC audit
→ PC01 mechanics/state contract
→ PC02 PC runtime adapter
→ PLAY05 PC Magic Moment

PLAY05
→ PLAY06 mixed dogfood + performance hardening
```

`PWO02`, `PWO03`, `PLAY01`, and `COMBAT01` may proceed in parallel after `PWO01` when repository ownership and exact kernel contracts are stable.

`PLAY03` should not wait for `PLAY04`/`PLAY05`: the Threat path is the fastest way to prove the cross-surface architecture and begin collecting live-play signal.

---

## 22. PR body requirements

Every PR in this series states:

1. slice ID and gate;
2. immutable base SHA and owning repository;
3. exact input and output contracts;
4. authority read/write boundary;
5. identity and revision rules;
6. success, miss, unavailable, integrity-failure, stale, retry, and reload behavior as applicable;
7. migration/demolition declaration;
8. tests run and evidence provenance;
9. live dogfood still required;
10. named successor capabilities that remain false.

No PR may claim “Play supports world objects” if only Threat works, “NPC supports combat” if mechanics are still title/path-derived, or “PC supports combat” if persistent character state ownership is still ambiguous.
