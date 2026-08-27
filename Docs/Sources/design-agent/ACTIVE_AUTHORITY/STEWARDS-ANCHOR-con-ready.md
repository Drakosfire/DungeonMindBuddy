# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY`  
**Updated:** 2026-08-26  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Re-anchor base:** `main` `39ef105d3996ef0062dd45a089fecada14915436` (PLAY-SURFACE BF2 / PR #652 merged)
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

PLAY PRODUCT
BF2 / PR #652    DONE — v2 READY, deterministic Beat seed, exact WorkRevision admission
                 accepted head 9dffcab96ad3f527efedc3981aea805a63deb4df
                 merge 39ef105d3996ef0062dd45a089fecada14915436
                 review cycles: 5
BF3A             CURRENT — Scene-centered Current Moment cockpit (Scenes first)
```

Current Play runtime/product state:

- Beat-first v2 material can be authored/serialized/sealed.
- BF2 admits v2 native READY with durable `currentBeatId` and optional `currentSceneId`.
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
BF2 / PR #652
DONE — v2 READY Runtime + current-position/relevance
        ↓
BF3A
CURRENT — Scene-centered Current Moment cockpit (Scenes)
        ↓
BF3B
Decision interaction and visible relevance
        ↓
BF3C / BF3.x / P3 family
additional At-a-Glance categories; fast cross-Beat inspect + retrieval
        ↓
P4 / Combat lane
Threat→Combat + expandable Combat workspace + durable Combat proof
        ↓
real-session dogfood
```

BF4 Plan Beat-first authoring composition may proceed in parallel after BF1 on a disjoint lease and should not block the next cockpit dogfood.

Agent Surface may proceed in parallel on disjoint leases. It is not a prerequisite for fast object/statblock retrieval.

---

## 4. BF3A dispatch boundary

BF2 / PR #652 is merged. Do not reopen v2 admission, seed, or relevance in this slice.

BF3A owns only:

- Scene-centered current-moment presentation of admitted v2 READY;
- Beat-only central workspace when `currentSceneId` is null;
- collapsible Beat Context and At a Glance (presentation-only);
- Scenes as the first At-a-Glance category;
- inspect versus explicit Make Current for current-Beat Scenes;
- v2 Runtime overlay after progress CAS.

BF3A does **not** own:

- Decision selection UI;
- NPC/Location/Threat/Notes At-a-Glance categories;
- cross-Beat inspection or global finder;
- Combat workspace;
- Agent Interaction;
- new backend/API/schema;
- AppChrome / Surface Interaction ownership.

BF3B owns Decision interaction. Later slices own additional categories and retrieval.

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

- BF2 / PR #652 is DONE (merge `39ef105d3996ef0062dd45a089fecada14915436`, 5 review cycles).
- BF3A Current Moment cockpit is in flight and is **not** DONE.
- BF3B Decision interaction remains false.
- BF3.x / P3 retrieval remains false.
- P4 / Combat remains false.
- global/on-demand retrieval is not proven.
- native unexpected Threat→Combat end-to-end is not proven.
- Combat durability is not assumed.
- CR-U17 is not complete overall.
- no new Note schema is authorized.
- no Choice condition/workflow DSL is authorized.
- no Agent dependency is authorized for basic Play retrieval.
