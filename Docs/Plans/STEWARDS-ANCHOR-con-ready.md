# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY`  
**Updated:** 2026-09-04  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Re-anchor base:** `main` `3b84015cc90dd6c60e8d8dca6d9e2e7516779afa` (DOGFOOD-CONTINUITY handoff; after PR #682 SI-6 ACCEPT)  
**Product roadmap:** [`../Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md)  
**Current forcing function:** DOGFOOD-CONTINUITY DFC-1 — [`HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md`](HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md)  
**Of Conks report:** [`../Reports/REPORT-of-conks-end-to-end-dogfood.md`](../Reports/REPORT-of-conks-end-to-end-dogfood.md)  
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

SURFACE-INTEGRATION is **CLOSED** (SI-6 ACCEPTED, PR #682). The temporary feature freeze is lifted. The active CON-READY forcing function is **DOGFOOD-CONTINUITY DFC-1** — historical material inventory and Of Conks and Cons continuity — not automatic resume of the old BF3B branch.

The Play persistence foundation is no longer the blocker.

```text
SURFACE-INTEGRATION
SI-6 / PR #682    DONE / ACCEPTED — merge 86296a4021816862b1ee82cbf7478b2882493963
SI-7              DONE — re-sequenced to DOGFOOD-CONTINUITY DFC-1

DOGFOOD-CONTINUITY
DFC-1             CURRENT — historical material inventory / Of Conks and Cons continuity

PLAY STRUCTURE
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
BF3A / PR #655   DONE — Scene-centered Current Moment cockpit (Scenes first)
                 accepted head 3d5925c8ad1bdbe934020e1c4cd7f2f3fafbbec7
                 merge 4d82f12ad9c6d679b5dbce83db527eb7dbd27957
                 review cycles: 2
DF0 / PR #657    DONE — local Play dogfood gateway
PLAN-BLANK-SHELL / PR #661 DONE — blank Plan is a real authoring surface state
                 accepted head ffa0b18d6212a6780d6be90f91a25626bf15b464
                 merge 770f79cca4aa3c12aa8a35db2db77ce376f2ff9e
                 review cycles: 4
BF4A / PR #660   DONE — native Runbook reopen/save
                 accepted head d9b34ca87166572af8b482523862722fdd928fbe
                 merge a3fd6219062d1cd978c394d07e2f80aaa6d203eb
                 review cycles: 2
BF3B             LATER — Scene-owned Decision interaction (parked; stale "CURRENT" sequencing retired)
PR #670          CLOSED UNMERGED — exploratory cockpit prototype; 0 review cycles
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
BF3A / PR #655
DONE — Scene-centered Current Moment cockpit (Scenes)
        ↓
DF0
DONE — local Play dogfood bootstrap/readiness
        ↓
PLAN-BLANK-SHELL / PR #661
DONE — blank Plan is a real authoring surface state
        accepted head ffa0b18d6212a6780d6be90f91a25626bf15b464
        merge 770f79cca4aa3c12aa8a35db2db77ce376f2ff9e
        review cycles: 4
        ↓
BF4A
DONE — native Runbook reopen/save
        accepted head d9b34ca87166572af8b482523862722fdd928fbe
        merge a3fd6219062d1cd978c394d07e2f80aaa6d203eb
        review cycles: 2
        ↓
DFC-1
CURRENT — DOGFOOD-CONTINUITY historical material inventory / Of Conks and Cons continuity
        handoff: HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md
        ↓
BF3B
LATER — Scene-owned Decision interaction (parked until after DFC-1)
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

## 4. DF0 completion and BF4A dispatch boundary

BF3A / PR #655 is merged. Do not reopen Current Moment presentation in this slice.

DF0 owns only:

- explicit local `check` / `apply` composition for Buddy application state;
- provisioning the standard local Buddy logical database when missing;
- explicit Alembic upgrade and leftover Runbook adoption;
- domain-neutral APP-STATE unavailable copy;
- documented ordinary uvicorn + Vite Play startup;
- a development-only Play setup hint.

DF0 does **not** own:

- migrate-on-boot or import-on-boot;
- World Graph / file-authority fallback;
- seeding a fake Runbook;
- starting or selecting a Play Run;
- Decision selection UI;
- Combat, Agent Interaction, or CUTOVER.

DF0 is complete at PR #657. PLAN-BLANK-SHELL is complete at PR #661. BF4A is
DONE at PR #660. **DFC-1** is the current CON-READY forcing function. BF3B
(Scene-owned Decision interaction) remains a later product capability — the old
"CURRENT / IN FLIGHT" sequencing on `agent/play-surface-decision-cockpit-recut`
is retired as stale.

Create blank Runbook, chooser copy, and paste/replace remain predecessor or
separate product work. They are not BF3B. Closed unmerged PR #670 is exploratory
evidence only and is not a review cycle.

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
- BF3A / PR #655 is DONE (merge `4d82f12ad9c6d679b5dbce83db527eb7dbd27957`, 2 review cycles).
- DF0 local Play dogfood bootstrap is DONE (PR #657, merge `87a769d05605ff021d28f0b69c5d7ab0b8205440`).
- PLAN-BLANK-SHELL / PR #661 is DONE (merge `770f79cca4aa3c12aa8a35db2db77ce376f2ff9e`, 4 review cycles).
- BF4A native Runbook authoring is DONE (PR #660, accepted head `d9b34ca87166572af8b482523862722fdd928fbe`, merge `a3fd6219062d1cd978c394d07e2f80aaa6d203eb`, 2 review cycles).
- SURFACE-INTEGRATION is CLOSED (SI-6 ACCEPTED, PR #682 merge `86296a4021816862b1ee82cbf7478b2882493963`, 2 review cycles).
- DFC-1 historical material inventory is **CURRENT** (not done).
- BF3B Decision interaction is **not current** — parked until after DFC-1. Closed unmerged PR #670 is exploratory evidence only (0 review cycles).
- BF3.x / P3 retrieval remains false.
- P4 / Combat remains false.
- global/on-demand retrieval is not proven.
- native unexpected Threat→Combat end-to-end is not proven.
- Combat durability is not assumed.
- CR-U17 is not complete overall.
- no new Note schema is authorized.
- no Choice condition/workflow DSL is authorized.
- no Agent dependency is authorized for basic Play retrieval.
