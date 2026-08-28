# CON-READY — Product Roadmap and Acceptance Stories

**Status:** ACTIVE PRODUCT ROADMAP  
**Line of work:** `CON-READY`  
**Re-anchored:** 2026-08-26 from `main` `4d82f12ad9c6d679b5dbce83db527eb7dbd27957` (PLAY-SURFACE BF3A / PR #655 merged)
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Historical starting anchor:** `85a2bbf048d92afed1911031ca7b6a311115873c`  
**Stewardship anchor:** [`../Plans/STEWARDS-ANCHOR-con-ready.md`](../Plans/STEWARDS-ANCHOR-con-ready.md)

---

## 0. Purpose

CON-READY is a product-readiness workstream.

It is not an architecture-completion program. Architecture, schemas, migrations, and contracts matter only when they enable or protect concrete GM-visible capability.

CON-READY succeeds when:

> **A GM can bring playable material into a world, prepare the version they intend to run, and rely on DungeonBuddy during a live session for current Scene context, authored branching, source/world/object detail, exact mechanics, unexpected-play retrieval, notes, Agent/Hermes assistance, and Combat—without rebuilding context after reload.**

The convention one-shot remains the forcing-function acceptance scenario, but the capabilities must remain useful for ordinary campaign play.

---

## 1. Product model

```text
ORIGINAL SOURCE
rich prose, tables, images, maps, statblocks

        ↓ extraction / provenance

WORLD
durable semantic representation
identity, relationships, accepted assertions, mechanics bindings

        ↓ GM preparation / deliberate adoption

PLAYABLE MATERIAL
the version the GM intends to run
Runbooks, Beats, Scenes, Decisions, consequences,
object-attached prep, encounter composition, local interpretations

        ↓ actual table interaction

PLAYED / RUNTIME STATE
current Beat/Scene, selected Choices, resolved Beats, notes,
linked Combat/runtime state and other run-local outcomes
```

These layers must not collapse merely because they refer to the same fictional world.

### 1.1 Source remains first-class

World is intentionally lossy. The GM and Agent should be able to follow admitted provenance back to readable rich source when compact World representation is insufficient.

### 1.2 Playable material is durable without becoming canon

GM prep is durable intent, not automatic World truth.

APP-STATE now provides stable WorkObject identity, immutable historical WorkRevisions, and PostgreSQL Play Runtime/continuity. Filesystem path/worktree location is no longer Play identity or authority.

### 1.3 Play design authority

Current Play authorities:

- [`../Design/ARCHITECTURE-playable-material-and-runtime.md`](../Design/ARCHITECTURE-playable-material-and-runtime.md)
- [`../Design/DESIGN-play-current-moment-cockpit.md`](../Design/DESIGN-play-current-moment-cockpit.md)
- [`../Design/DESIGN-play-surface-projection.md`](../Design/DESIGN-play-surface-projection.md)
- [`../Design/DESIGN-playable-authoring-and-adoption.md`](../Design/DESIGN-playable-authoring-and-adoption.md)
- [`../Design/DESIGN-play-surface-gm-cockpit-target.md`](../Design/DESIGN-play-surface-gm-cockpit-target.md)

The durable model is Beat-first; the default runtime projection is Scene-centered when a Scene is current.

Choices/Decisions retain authored Options, consequences, and `activates`/`suppresses` branch relevance. Those edges influence emphasis; they do not gate access/navigation.

---

## 2. Governing principles

1. **User stories are the gates.** A slice is complete when a GM-visible story works end-to-end with real material.
2. **Source stays readable.** Ingestion must not replace useful source with stripped semantic output.
3. **World placement and writes are explicit.** Playable/Runtime work does not silently publish canon.
4. **Graph provenance is useful navigation.** Evidence should lead back to the useful source.
5. **Agent/Hermes remains governed.** Context follow-through is admitted and bounded; proposals require approval.
6. **Mechanics deserve exact structure where it pays off.** Threat/statblock mechanics should become reusable exact resources.
7. **Documents are valid product objects.** Useful material need not gain bespoke ontology first.
8. **Unexpected play is a required acceptance case.** Prepared paths alone are insufficient.
9. **Playable structure is not World ontology.** Beat/Scene/Decision is a Playable domain model.
10. **Runtime points at Playable; it does not rewrite it.** Historical WorkRevision pinning is real.
11. **Stable identity beats display text.** Durable references use stable IDs.
12. **Authored branching is real but non-gating.** `activates`/`suppresses` alter relevance, not navigation permission.
13. **Scene is the normal table workspace; Beat supplies context.** This is projection hierarchy, not a change to durable containment.
14. **Inspect is not Make Current.** Looking at another Scene/object never silently mutates Runtime position.
15. **Useful campaign material must be reachable faster than finding where it was authored.** Contextual and global/on-demand retrieval are complementary.
16. **Combat remains Combat-owned.** Play may link/project it, not absorb combat state.
17. **Durability claims are scoped.** The Play path is now durable; CR-U17 remains false overall until every relied-upon capability—especially Combat—survives restart/worktree/browser loss.

---

# 3. Acceptance user stories

## CR-U1 — Bring external material into DungeonBuddy

> **As a GM, I can bring external Markdown into the world I am working on without preparing it specifically for DungeonBuddy.**

Success includes normal paste/file ingress, explicit world placement, durable source identity, useful title, reopen/edit, and one normalization boundary for future upstream extraction.

Not success: undocumented manual file copying, bespoke CLI-only workflows, or requiring graph IDs/internal storage vocabulary from the GM.

## CR-U2 — Read the original source as a real document

> **As a GM, I can read imported material comfortably inside DungeonBuddy.**

Headings, paragraphs, emphasis, lists, tables, links, spacing/typography, and available images/assets should remain useful.

## CR-U3 — DungeonBuddy gives me a useful semantic index

> **As a GM, I can quickly find important people, threats, places, organizations, and relationships without rereading everything.**

The World representation may remain intentionally lossy and point back to source.

## CR-U4 — I can inspect and correct what DungeonBuddy understood

> **As a GM, I can repair important extraction/identity/relationship mistakes without thinking in graph-database terms.**

Human-facing correction language and duplicate prevention matter more than exposing graph machinery.

## CR-U5 — I can follow a world object back to its source

> **As a GM, compact object detail can take me back to the exact rich source that established it.**

Provenance is normal navigation, not only audit metadata.

## CR-U6 — Agent/Hermes can follow provenance when graph detail is insufficient

> **As a GM, Agent/Hermes can use admitted source follow-through for a known object without gaining arbitrary filesystem authority.**

## CR-U7 — Agent/Hermes remains truthful about standing

> **Useful source detail may appear in an answer without pretending source prose and accepted World assertion are identical authority.**

## CR-U8 — Important NPCs are ready to use

> **As a GM, I can find/open an important NPC quickly, understand who they are, follow useful relationships/source, and ask Agent/Hermes about them.**

A universal NPC ORM is not required.

## CR-U9 — Important places and shops are ready to use

> **As a GM, I can quickly open an important place/shop and get what I need to run it.**

A rich document is an acceptable answer when it solves the task.

## CR-U10 — Threats have usable mechanics

> **As a GM, I can reach the actual accepted statblock for a creature/threat quickly.**

Preferred authority:

```text
Threat
→ exact accepted StatblockRevision
```

Exact mechanics should not require regeneration when already known.

## CR-U11 — I can develop the version I intend to run

> **As a GM, during prep I can organize, develop, save, reopen, and revise the Playable version without automatically rewriting World.**

Current durable structure:

```text
Runbook
  Beat (context / objective / pressure / phase)
    Scene (concrete playable situation)
    Decision → Options → consequences → activates/suppresses
```

APP-STATE historical WorkRevisions mean revision N remains a real durable version after N+1 exists.

The Runbook is the exact linear authored source. Play projects it into a Scene-centered cockpit rather than requiring document-tree navigation at the table.

## CR-U12 — Agent/Hermes can reason over and help author the playable version

> **As a GM, deliberately saved Playable Material can join governed World/Source/Mechanics context, and Agent/Hermes suggestions remain proposals until I approve and Save them.**

## CR-U13 — Prepared combats are ready before the session

> **As a GM, expected encounters can be prepared with exact identities/mechanics and handed to Combat before play.**

Combat may advance in parallel but remains Combat-owned.

## CR-U14 — An unexpected fight does not break the workflow

> **As a GM, when players start a fight I did not prepare, I can find known NPCs/threats, see exact mechanics, add them to Combat, and begin running without JSON or memory reconstruction.**

This is mandatory dogfood.

## CR-U15 — I can use DungeonBuddy instead of my memory

> **As a GM running the session, DungeonBuddy is faster and safer than remembering where information was.**

Representative live actions/questions now explicitly include:

- resume the exact last current Scene;
- inspect Beat context;
- see which Scenes/locations/NPCs/threats/tables/notes are around this moment;
- inspect a Scene under another Beat without moving the current moment;
- explicitly Make that Scene Current if the table actually moves there;
- “Show me the Tunnel Crawler statblock.”
- find an unplanned known NPC/Threat not referenced by the current Scene;
- select an authored Decision Option and see what became emphasized/de-emphasized;
- keep a table note pinned to the context where it originated;
- expand Combat and collapse back to the same Scene.

The GM should not need to know which internal authority supplied the answer.

## CR-U16 — Navigation is part of the answer

> **As a GM, useful answers/objects open the underlying NPC, location, threat, source, mechanics, or Playable material without making me reconstruct table context.**

Opening is inspect/read by default. Runtime position changes only through explicit actions.

## CR-U17 — Reload does not destroy preparation

> **As a GM, restart/reload preserves every piece of material and runtime state I depend on.**

Play-specific durability is now substantially true:

- Plan/Runbook WorkObjects and historical WorkRevisions → PostgreSQL;
- Play Run + manifest + progress/rebase → PostgreSQL;
- active Run selection/resume → PostgreSQL;
- legacy Play filesystem persistence → demolished.

CR-U17 remains **false overall** until Combat and any other relied-upon non-Play state meet the same standard.

---

# 4. Delivery roadmap

## 4.0 Current delivery state — 2026-08-26

Repository truth at this re-anchor:

```text
PLAY STRUCTURE
BF1 / PR #628    DONE — Beat-first v2 grammar, index, manifest foundation

APP-STATE
AS1              DONE — Plan WorkObjects / immutable WorkRevisions
AS2              DONE — Runbook / historical Playable WorkRevisions
AS3              DONE — Play Run + manifest + Runtime CAS/rebase on PostgreSQL
AS4              DONE — active Run / resume continuity on PostgreSQL
AS5 / PR #650    DONE — legacy Play filesystem persistence demolished

PLAY PRODUCT
BF2 / PR #652    DONE — v2 READY/current-position/relevance
                 accepted head 9dffcab96ad3f527efedc3981aea805a63deb4df
                 merge 39ef105d3996ef0062dd45a089fecada14915436
                 review cycles: 5
BF3A / PR #655   DONE — Current Moment
                 accepted head 3d5925c8ad1bdbe934020e1c4cd7f2f3fafbbec7
                 merge 4d82f12ad9c6d679b5dbce83db527eb7dbd27957
                 review cycles: 2
DF0 / PR #657    DONE — local Play dogfood gateway
                 accepted head dc20fe8e63eec691265e75eb73c69f441ffd779d
                 merge 87a769d05605ff021d28f0b69c5d7ab0b8205440
                 review cycles: 3
PLAN-BLANK-SHELL CURRENT — zero-material Plan authoring + local→durable promotion
BF4A             BLOCKED ON PLAN-BLANK-SHELL — native Runbook reopen/save
BF3B             BLOCKED ON BF4A — Decision interaction and visible relevance
BF3C / BF3.x     later — additional At-a-Glance categories / retrieval
BF4              authoring composition; may run in parallel on disjoint lease

CUTOVER
separate active lane; do not make remaining CUTOVER work a reason to pause disjoint Play Surface work
```

### Current story truth

| Story | State now | Why |
|---|---|---|
| CR-U11 | **Partially true, foundation strong** | durable WorkObject/WorkRevision + BF1 structure exist; Plan currently lacks a valid local blank authoring state — PLAN-BLANK-SHELL owns that seam; BF4A then owns native Runbook reopen/save |
| CR-U13 | **Partial / Combat-owned** | exact mechanics/projection seams exist, but durable integrated Combat acceptance is separate |
| CR-U14 | **False as native end-to-end story** | C2S27 proved fast unplanned combat in the legacy tracker; native global Threat→exact mechanics→Combat flow still needs proof |
| CR-U15 | **PARTIAL** | BF3A Current Moment is implemented and merged; DF0 merged local Play dogfood gateway. Decision interaction and later cockpit capabilities remain false. |
| CR-U16 | **Partial** | projection seams exist; cross-Beat inspect/global on-demand retrieval remains a prioritized gap |
| CR-U17 | **Play portion true; overall false** | Play durability is PostgreSQL-backed; Combat/other relied-upon state must still prove continuity |

### Immediate delivery sequence

```text
1. BF2 — DONE (PR #652, merge 39ef105d3996ef0062dd45a089fecada14915436, 5 review cycles)
   - seed new v2 currentBeatId
   - restore exact historical pinned WorkRevision
   - explicit Beat/Scene current-position mutations
   - activates/suppresses emphasis

2. BF3A — DONE (PR #655, merge 4d82f12ad9c6d679b5dbce83db527eb7dbd27957, 2 review cycles)
   - active Scene is the default central workspace
   - Beat-only state when no Scene is current
   - collapsible Beat Context / At a Glance
   - Scenes inspect versus explicit Make Current

3. DF0 — DONE (PR #657, merge 87a769d05605ff021d28f0b69c5d7ab0b8205440, 3 review cycles)
   - explicit check/apply for Buddy application state
   - ordinary uvicorn + Vite then reaches /play
   - empty Play creates a blank committed Runbook explicitly; bootstrap does not seed

4. PLAN-BLANK-SHELL — CURRENT — zero-material Plan authoring + local→durable promotion
   - bare /plan opens editable local draft with Edit/Tools chrome
   - first Save promotes through existing Plan create contract
   - PLAN-BLANK-SHELL is in flight and is not DONE

5. BF4A — BLOCKED ON PLAN-BLANK-SHELL — native Runbook reopen/save

6. BF3B — BLOCKED ON BF4A — Decision interaction and visible relevance
   - current-context Decisions / Options
   - select / change / clear selection
   - authored consequence and emphasized / de-emphasized presentation
   - no auto-navigation

5. FAST RETRIEVAL / OBJECT PROJECTIONS — BF3.x / P3 family
   - inspect material from other Beats without changing current moment
   - global/on-demand known object finder
   - fast NPC/location/Threat/table opening
   - exact statblock hot path

6. THREAT → COMBAT + COMBAT WORKSPACE — P4 / Combat lane
   - Add to Combat from prepared or unexpected Threat
   - Combat is one At-a-Glance entry with compact status, not a floating side rail
   - opening Combat uses the same central workspace; Combat remains Combat-owned
   - collapse/close returns to the exact current Scene
   - durable Combat authority required for CR-U17 overall
   - this Combat workspace is not implemented until P4

7. BF4 — Plan Beat-first authoring composition
   - may proceed in parallel after BF1 on disjoint leases
   - must not block getting DF0/BF3B back to a real table

8. REAL SESSION DOGFOOD
   - deliberately include an off-script scene change
   - unplanned NPC/Threat
   - exact mechanics lookup
   - unexpected Add to Combat
   - authored Decision branch
   - reload/resume
```

Agent Surface and kernel hoist work may proceed in parallel where leases/authority boundaries are clean, but neither is a prerequisite for fast native object/statblock retrieval.

---

## CR01 — Source Ingress & Reading

**Primary stories:** CR-U1, CR-U2.  
**Outcome:** external Markdown → chosen world → durable source → rich reopen/read/edit.

## CR02 — Source-Backed World Ingestion

**Primary stories:** CR-U3, CR-U4, CR-U5.  
**Outcome:** bounded extraction/review/publication on real material with object→source navigation.

## CR03 — Agent/Hermes Source Follow-Through

**Primary stories:** CR-U6, CR-U7.  
**Outcome:** graph discovery may follow admitted provenance into the exact source artifact without arbitrary filesystem authority.

## CR04 — Game-Facing Objects & Mechanics

**Primary stories:** CR-U8, CR-U9, CR-U10.  
**Outcome:** useful NPC/location/threat/document projections; exact mechanics where valuable; no unnecessary universal ontology.

## CR05 — Playable Preparation

**Primary stories:** CR-U11, CR-U12.  
**Outcome:** exact versioned Playable WorkObjects with stable Beat/Scene/Decision/Option identity, explicit authoring/adoption, and governed Agent proposals.

The datastore decision is already made for the current foundation: Buddy PostgreSQL application state owns durable WorkObjects/WorkRevisions. Do not reopen file authority.

## CR06 — Combat Readiness Integration

**Primary stories:** CR-U13, CR-U14.  
**Outcome:** prepared **and unexpected** known Threat/NPC encounters can reach Combat from Play without campaign bridges, JSON reconstruction, or authoring-location hunts.

Preferred path:

```text
current context OR global finder
→ Threat
→ exact accepted StatblockRevision
→ Add to Combat
→ Combat-owned runtime
```

## CR07 — Real One-Shot / Campaign Run

**Primary stories:** CR-U15, CR-U16, CR-U17 plus cumulative verification.  
**Outcome:** run a real session through the target Play cockpit.

Required live proof includes:

- exact resume to last current Beat/Scene;
- Beat context + Scene-centered board;
- authored Decision selection and visible branch relevance;
- inspect another Beat/Scene without moving current position;
- explicit Make Current;
- presence-first `At a Glance`;
- unplanned global object/Threat retrieval;
- exact statblock with no noticeable table-breaking delay;
- prepared and unexpected Add to Combat;
- Combat expand/collapse with exact Scene return;
- note capture;
- restart/reload without reconstruction.

Anything that forces the GM to abandon DungeonBuddy for manual source search, memory reconstruction, or combat rebuilding is concrete CON-READY debt.

---

# 5. Explicitly deferred / not required for CON-READY

Not required before CON-READY succeeds:

- direct PDF pipeline wiring;
- arbitrary Agent filesystem search;
- multimodal interpretation of every imported image;
- perfect automatic extraction of Scenes/Beats/branches;
- universal Adventure ORM;
- full universal NPC/Shop ontology;
- automatic World writes from brainstorming;
- automatic Playable→World or Runtime→Playable promotion;
- a universal asset-management platform;
- boolean Choice condition DSL / workflow engine;
- a new Note table without dogfood evidence;
- completion of every kernel/hoist possibility.

Deferring automatic Scene/Beat extraction does not defer GM-authored Playable structure.

---

# 6. Final acceptance journey

CON-READY is successful when this works with real material:

```text
I bring source material into DungeonBuddy and can read it.

DungeonBuddy gives me enough World/index structure to find important people,
places, organizations, threats, and their source.

I prepare the exact version I intend to run as a durable Runbook.

I start/resume a Run.

Within seconds I see the Scene I left off on, inside accessible Beat context.

The players make an authored Decision; I record the Option and the cockpit
shows the consequence and changed relevance without trapping navigation.

The players immediately do something I did not expect.

I inspect a Scene under another Beat without losing my current moment.
I find an NPC/Threat that was not referenced by the current Scene.
I open the exact statblock quickly.
I add it to Combat.
Combat expands as the working instrument.
I collapse it and I am back in the exact Scene.

If the table actually moved to that other Scene, I explicitly Make Current.

I record notes without rewriting the Runbook or World.

I reload/restart and the state I depended on is still there.
```

---

# 7. Stewardship rule

Every implementation/review under CON-READY must re-anchor against current repository truth and the user stories above.

Do not silently redefine CON-READY as architecture completion. Do not dispatch BF3B until DF0 proves the merged Current Moment is reachable through the supported local operator path. Do not bundle Decisions, finder, Combat, or Runbook reference into DF0.
