# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY`  
**Updated:** 2026-08-26  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Re-anchor base:** `main` `cc016661f80416e0816f56349217cf33c53a195f` (APP-STATE AS5 / PR #650 merged)  
**Product roadmap:** [`../Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md)  
**Primary Play architecture:** [`../Design/ARCHITECTURE-playable-material-and-runtime.md`](../Design/ARCHITECTURE-playable-material-and-runtime.md)  
**Primary cockpit contract:** [`../Design/DESIGN-play-current-moment-cockpit.md`](../Design/DESIGN-play-current-moment-cockpit.md)  
**Approved target:** [`../Design/DESIGN-play-surface-gm-cockpit-target.md`](../Design/DESIGN-play-surface-gm-cockpit-target.md)

---

## 0. Pickup rule

Repository truth supersedes older chat, handoffs, and pre-APP-STATE design assumptions.

Before dispatching a CON-READY / PLAY-SURFACE implementation:

1. fetch current `main`;
2. inspect open PRs/worktrees for lease collision;
3. read the current roadmap + Play authorities above;
4. record the exact implementation base;
5. keep one independently useful capability per PR;
6. require exact-head evidence and review-cycle counting;
7. do not merge unless explicitly instructed.

---

## 1. Current product truth

The Play persistence foundation is no longer the blocker.

```text
BF1 / PR #628    DONE — Beat-first v2 grammar/index/manifest

APP-STATE
AS1              DONE — Plan WorkObjects / immutable WorkRevisions
AS2              DONE — Runbook + historical Playable WorkRevisions
AS3              DONE — Run/manifest + progress CAS/rebase PostgreSQL
AS4              DONE — active Run / resume PostgreSQL
AS5 / PR #650    DONE — legacy Play filesystem persistence demolished
```

Current Play runtime/product state:

- Beat-first v2 material can be authored/serialized/sealed.
- BF1 intentionally still blocks v2 READY admission until BF2 seeds lawful current position.
- historical pinned Playable revisions are real and remain readable after newer revisions exist.
- bare `/play` active selection and Play Runtime are PostgreSQL-backed.
- `out/runtime/play` is not current product authority.
- CR-U17 remains false **overall** because Combat and any other relied-upon non-Play state still need equivalent durability proof.

CUTOVER remains a separate active lane. Disjoint Play Surface work may proceed in parallel.

---

## 2. Current Play design truth

The approved cockpit image remains the target.

Durable hierarchy:

```text
Runbook
  → Beat
      → Scene / Decision
```

Runtime projection hierarchy:

```text
Beat context wrapper
Active Scene central workspace (when present)
Decisions / notes / relevant objects around it
```

Do not confuse Scene-centered projection with the rejected Scene-first grammar.

### Choice / Decision law

Keep the Choice system:

```text
Decision
→ Options
→ authored consequence
→ activates / suppresses later Beat/Scene relevance
```

Runtime persists `choiceId → optionId` only.

`activates` / `suppresses` influence emphasis. They are not navigation permission. De-emphasized material remains inspectable and may explicitly be made current.

No general condition/workflow DSL without new dogfood evidence.

### Unexpected-play law

C2S27 showed that players immediately depart from authored expectations.

Play must support:

```text
CONTEXTUAL
current Beat/Scene references

GLOBAL / ON-DEMAND
known campaign material needed unexpectedly
```

And must distinguish:

```text
OPEN / INSPECT
preserve current Runtime position

MAKE CURRENT
explicit Beat+Scene Runtime mutation
```

Useful material must be reachable faster than finding where it was authored.

### Statblock / Combat hot path

High-priority interaction:

```text
context or finder
→ Threat
→ exact StatblockRevision
→ Add to Combat
```

Combat may expand into the central working area, but remains Combat-owned. Collapse returns to the exact originating Scene.

### Runbook posture

Runbook is the exact linear durable authored source/instructions. It is available as reference but is not the primary runtime navigator.

### Notes posture

Table notes are simple Runtime records projected as pinned context. Do not invent a new note table until BF3/dogfood proves independent note identity/lifecycle is needed.

---

## 3. Current delivery sequence

```text
BF2
v2 READY Runtime + current-position/relevance
        ↓
BF3
Scene-centered current-moment cockpit
        ↓
BF3.x / P3 family
fast cross-Beat inspect + global/on-demand object/statblock retrieval
        ↓
P4 / Combat lane
Threat→Combat + expandable Combat workspace + durable Combat proof
        ↓
real-session dogfood
```

BF4 Plan Beat-first authoring composition may proceed in parallel after BF1 on a disjoint lease and should not block the next cockpit dogfood.

Agent Surface may proceed in parallel on disjoint leases. It is not a prerequisite for fast object/statblock retrieval.

---

## 4. BF2 dispatch boundary

Do not dispatch BF2 from the historical BF1 handoff unchanged.

A fresh BF2 handoff must use the updated authorities and current `main`.

BF2 owns only:

- v2 READY admission;
- deterministic new-Run `currentBeatId` seed;
- explicit Beat/Scene current-position validation/mutation;
- exact historical pinned WorkRevision admission;
- derived `activates`/`suppresses` relevance.

BF2 does **not** own:

- full cockpit presentation;
- global finder UI;
- new note schema;
- Combat persistence;
- Agent Surface;
- Plan authoring composition;
- a condition/workflow DSL.

BF3 owns the Scene-centered cockpit realization.

---

## 5. Acceptance pressure to retain

The next live dogfood must intentionally include:

- resume to exact last Scene;
- Beat context visible/accessibly expandable;
- authored Decision branch and visible relevance change;
- inspect a Scene under another Beat without moving current position;
- explicit Make Current;
- unplanned known NPC/Threat retrieval;
- exact statblock opening with no table-breaking delay;
- unexpected Add to Combat;
- Combat expand/collapse with exact Scene return;
- notes;
- reload/resume.

A path that forces manual source search, memory reconstruction, JSON surgery, Plan/Build navigation for known mechanics, or loss of current context is product debt even if the underlying architecture is technically correct.

---

## 6. What remains deliberately false

- BF2 is not implemented merely because BF1/APP-STATE are complete.
- Scene-centered BF3 cockpit is not implemented.
- global/on-demand retrieval is not proven.
- native unexpected Threat→Combat end-to-end is not proven.
- Combat durability is not assumed.
- CR-U17 is not complete overall.
- no new Note schema is authorized.
- no Choice condition/workflow DSL is authorized.
- no Agent dependency is authorized for basic Play retrieval.
