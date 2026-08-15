---
document_id: dmb-report-pr578-play-dogfood-mining
title: PR #578 Play Dogfood Mining Report
document_class: evidence_report
status: evidence_non_authoritative
created_at: "2026-08-15"
source_pr: 578
source_pr_head: 88e4d65e7ed69afe262008749194e2b948ce4c43
source_pr_title: "PLAY: Of Conks Hempholm table-ready dogfood"
---

# PR #578 Play Dogfood Mining Report

## 0. Purpose

This report records the product and architecture lessons worth retaining from PR #578 without treating the dogfood implementation as merge-ready architecture.

PR #578 explicitly exists as a **mining / review** branch. Its purpose is to collect a table-ready Of Conks / Hempholm dogfood pile, prove useful interactions, and let stewardship extract focused successors rather than merge the branch as one undifferentiated change.

This report is evidence. It is **not** architecture, roadmap, or implementation-sequence authority.

Canonical decisions derived from this evidence belong in:

- `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
- `Docs/Design/DESIGN-play-surface-projection.md`
- `Docs/Design/DESIGN-playable-authoring-and-adoption.md`
- `Docs/Roadmaps/ROADMAP-con-ready.md`

## 1. Source set and pin

Primary evidence:

- PR #578 — `PLAY: Of Conks Hempholm table-ready dogfood`
- Head: `88e4d65e7ed69afe262008749194e2b948ce4c43`
- 156 changed files at the mined head
- Of Conks / Hempholm is proof material, not a product ontology.

High-value implementation seams inspected:

- `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`
- `apps/live-control-ui/src/playSurface/playPanels.ts`
- `apps/live-control-ui/src/playSurface/beats/BeatsPanel.tsx`
- `apps/live-control-ui/src/playSurface/beats/ofConksHempholmBeats.ts`
- `apps/live-control-ui/src/graphReference/PlayObjectSheetProjection.tsx`
- `apps/live-control-ui/src/graphReference/ofConksPlayObjectBridge.ts`
- `apps/live-control-ui/src/graphReference/PlayMapOverlaySection.tsx`
- `apps/live-control-ui/src/graphReference/ofConksMapOverlays.ts`
- `apps/live-control-ui/src/graphReference/ofConksNodeMedia.ts`
- `apps/live-control-ui/src/statblocks/projection/ThreatSheetProjection.tsx`
- `apps/live-control-ui/src/statblocks/projection/ofConksThreatPlayBridge.ts`
- `apps/live_control_server/services/play_run_state.py`
- `apps/live_control_server/services/canvas_block_proposal.py`
- `apps/live-control-ui/src/planSurface/canvasBlockProposal.ts`
- `evals/hermes_small_slice/gold/of_conks_grotesque_tree_v1.json`

## 2. Mining rule

Use this rule for every PR #578 feature:

> **Preserve the interaction that worked. Remove the adventure-specific mechanism that made it work.**

A hardcoded bridge is positive evidence when it proves a GM workflow. It is not, by itself, evidence that the bridge should become a generic registry or ontology.

## 3. Keeper findings

### 3.1 Play is a real surface

PR #578 proves that Play benefits from a dedicated table contract rather than behaving like Plan with fewer controls.

The useful interaction is:

```text
PLAN
develop and arrange what I intend to run

        ↓ deliberate handoff

PLAY
show me what I need right now at the table
```

The useful Play capability family is:

```text
Play
├── Run / Beats
├── Combat
├── Roll
├── Items
├── Mechanics / Statblocks
└── Object sheets / projections
```

The current prep-HTML host is migration glue, not a permanent substrate.

### 3.2 Play Object Sheets are a strong projection primitive

The strongest object interaction in #578 is a **table-first projection** of a world object.

For an NPC, the dogfood sheet prioritizes:

- At the table
- Attitude
- Offers / hooks
- Rules now
- Connected now
- Source / provenance
- relevant Play actions

Locations and items use different labels while preserving the same principle: table-useful information leads; graph/evidence internals move to Advanced.

The permanent lesson is not `PlayObjectBody`. The lesson is:

```text
WORLD + SOURCE + PLAYABLE + MECHANICS
                ↓
        PLAY OBJECT SHEET
```

### 3.3 Scene → Beat is useful Playable structure

The Hempholm scene deck proved that a runbook benefits from explicit session-shaped organization:

```text
Runbook
  Scene
    Beat
```

Useful Beat semantics observed in dogfood:

- title / summary
- kind: spine / optional / interrupt
- At the table
- Read aloud
- GM note
- Rules now
- warnings
- what happens if the table waits, succeeds, fails, or chooses something
- object/reference chips
- contextual tool actions

This structure is warranted by dogfood, but it belongs to **Playable Material**, not the World Graph.

### 3.4 Consequences are the durable outcome concept

PR #578 used several parallel fields such as `treasure`, `ifTheyWait`, `ifTheySucceed`, and `ifTheyFail`.

The permanent model should consolidate outcomes under **consequences**.

A consequence may represent:

- a reward or treasure;
- a cost or injury;
- a clock/state change;
- a relationship change;
- access gained or lost;
- information revealed;
- a location/world reaction;
- a branch transition;
- another table-visible result.

`reward` may be a consequence flavor or presentation hint. `treasure` is not a top-level Beat primitive.

### 3.5 Authored Playable Material and runtime state must remain separate

PR #578 usefully separates its hardcoded authored spine from persisted `PlayRunStateDocument`.

That separation is worth retaining:

```text
PLAYABLE MATERIAL
what could/should be run

        ↓ table interaction

PLAYED / RUNTIME STATE
what is selected, resolved, noted, or currently happening
```

The current runtime schema leaks adventure-specific enums (`hill`, `alchemist`, `guild`, `celebration`, `fire`). The permanent runtime contract must instead record opaque choice/option IDs defined by the authored playable material.

### 3.6 Threat → mechanics → Add to Combat is the right table handoff

The useful interaction is:

```text
Threat
  ↓ exact mechanics
Threat sheet
  ↓
Add to combat
  ↓
Combat
```

The Of Conks `threat node → workbench draft` dictionary is dogfood-only.

The permanent authority remains:

```text
Threat
  ↓ uses_statblock / exact accepted binding
immutable accepted StatblockRevision
  ↓
Combat participant
```

The product lesson is that **Add to combat belongs on the table-facing threat projection**.

### 3.7 Hermes proposal → GM approval → ordinary save is a strong authoring seam

PR #578's Canvas proposal flow demonstrates the desired agentic write boundary:

```text
ground
→ propose typed change
→ preview
→ GM approves
→ mutate open playable work object
→ ordinary Save
```

Important retained safety properties:

- Hermes proposes rather than silently writes;
- proposal targets an explicit work object;
- proposal can carry provenance refs;
- expected content digest / revision protects against stale admission;
- dirty local state blocks unsafe application;
- durable save remains the normal document authority.

Text-heading locators are prototype mechanics and should not become permanent identity.

### 3.8 Maps and media are useful, but not Play-owned truth

The map prototype proves a small reusable interaction:

```text
source/media asset
+ normalized annotation coordinates
+ graph/playable reference target
→ clickable map projection
```

Media association and pin coordinates should become durable data with source/asset authority. They should not remain `ofConks*` TypeScript dictionaries or become a special Play-only map system.

### 3.9 Small real-world Hermes evals are valuable

The Grotesque Tree eval demonstrates a useful evaluation pattern:

- a real object and source;
- question families;
- expected information buckets;
- forbidden behaviors;
- whether source opening is required;
- whether an authoring proposal is expected;
- repeated trials.

This methodology should be reused for Hermes graph/source/playable-context work.

## 4. Field classification

### 4.1 `PlayObjectBody`

| Dogfood field | Permanent class | Decision |
|---|---|---|
| `kind` | WORLD / PROJECTION | Object kind comes from durable identity; presentation adapts to it. |
| `atTable` | PLAYABLE | GM-adopted table interpretation. |
| `attitude` | PLAYABLE | Object-attached playable interpretation; not universal NPC canon. |
| `offersHooks` | PLAYABLE | GM-facing prep blocks. |
| `rulesNow` | PLAYABLE / MECHANICS reference | Playable framing may point to mechanics; must not duplicate mechanics authority when exact mechanics exist. |
| `connectedNow` | PROJECTION / PLAYABLE curation | Curated "relevant now" set, not full graph adjacency. |
| `toolLinks` | PROJECTION | Surface capability links. |
| `sourceBlocks` | SOURCE | Source prose remains source authority. |
| `provenance` | SOURCE | Source locator / provenance. |
| node media | SOURCE / ASSET | Asset association outside Play authority. |
| map pins | ASSET ANNOTATION / PROJECTION | Durable annotation data projected in Play. |

### 4.2 `AdventureScene`

| Dogfood field | Permanent class | Decision |
|---|---|---|
| `id` | PLAYABLE | Stable identity required across saves/revisions. |
| `title` | PLAYABLE | Editable display content. |
| `order` | PLAYABLE | Session-shaped organization. |
| `intent` | PLAYABLE | GM-facing scene framing. |
| `clocks` | PLAYABLE | Prepared pressure/clock definitions; live clock values are runtime. |
| `readAloud` | PLAYABLE | Semantic content block. |
| `gmNote` | PLAYABLE | Semantic content block. |
| `chips` | PLAYABLE references | Durable handles, not copied object truth. |
| `beats` | PLAYABLE | Scene composition. |
| `branchKind` | PLAYABLE structure | Generalize to authored choices/transitions; do not hardcode known branch families. |
| `requiresAftermath` | DOGFOOD-SPECIFIC | Replace with generic authored choice/condition references. |

### 4.3 `AdventureBeat`

| Dogfood field | Permanent class | Decision |
|---|---|---|
| `id` | PLAYABLE | Stable identity. |
| `title` | PLAYABLE | Display content. |
| `kind` | PLAYABLE | Useful small vocabulary: spine / optional / interrupt. |
| `summary` | PLAYABLE | Compact table orientation. |
| `atTable` | PLAYABLE | Primary table-facing framing. |
| `readAlouds` | PLAYABLE | Semantic blocks. |
| `gmNote` | PLAYABLE | Semantic block. |
| `rulesNow` | PLAYABLE + mechanics refs | Table framing, not mechanics authority. |
| `warnings` | PLAYABLE | Semantic blocks. |
| `ifTheyWait` | PLAYABLE CONSEQUENCE | Consequence trigger = wait. |
| `ifTheySucceed` | PLAYABLE CONSEQUENCE | Consequence trigger = success. |
| `ifTheyFail` | PLAYABLE CONSEQUENCE | Consequence trigger = failure. |
| `treasure` | PLAYABLE CONSEQUENCE | Consequence kind/presentation = reward. No root `treasure` field. |
| `chips` | PLAYABLE references | Typed handles. |
| `toolLinks` | PROJECTION | Surface actions/capabilities. |

### 4.4 `PlayRunStateDocument`

| Dogfood field | Permanent class | Decision |
|---|---|---|
| `run_id` | RUNTIME | Stable run identity. |
| campaign/adventure IDs | RUNTIME scope | Reference durable scope; do not make runtime the scope authority. |
| `current_scene_id` | RUNTIME | Reference stable playable Scene identity. |
| branch enums | DOGFOOD-SPECIFIC | Replace with generic `choiceId → optionId` selections. |
| `resolved_beat_ids` | RUNTIME | Retain. |
| `scene_notes` | RUNTIME | Generalize to notes keyed by stable playable element ID. |
| `updated_at` | RUNTIME | Retain. |

### 4.5 Canvas block proposals

| Dogfood concern | Permanent class | Decision |
|---|---|---|
| proposal kind | AUTHORING | Typed playable mutation proposal. |
| target document | AUTHORING authority | Must target explicit admitted work object. |
| expected SHA | AUTHORING concurrency | Retain CAS/revision protection. |
| provenance refs | AUTHORING provenance | Retain when grounded in source/world. |
| preview | PROJECTION | User-facing preview, not authority. |
| approve | OPERATOR decision | Required before applying proposal. |
| normal Save | DOCUMENT authority | Remains durable persistence boundary. |

## 5. Mechanisms to discard rather than generalize

The following are useful prototype evidence but poor permanent authority:

- `ofConksPlayObjectBridge.ts`
- `ofConksHempholmBeats.ts`
- `ofConksThreatPlayBridge.ts`
- `buildPlayLocalGraphReferenceResolution()` and other fabricated local graph resolution
- `ofConksNodeMedia.ts`
- `ofConksMapOverlays.ts`
- `playPrepHost.ts` / `MirewardPrep` global-script embedding
- adventure-specific branch enums in `PlayRunStateDocument`
- text-heading / fuzzy-text mutation locators as durable identity

## 6. Locked design consequences

The following decisions are promoted into the canonical design documents:

1. **Play is its own surface contract.**
2. **Runbook → Scene → Beat is warranted Playable structure.**
3. **Beat outcomes are `consequences`; reward/treasure is a consequence flavor, not a root field.**
4. **Playable Material and Runtime State are different authorities.**
5. **Playable structure needs stable identity independent of editable display text.**
6. **Play Object Sheets are projections, not a new object ontology.**
7. **Object-attached playable interpretation is valid without automatic World Graph promotion.**
8. **Threat mechanics retain exact accepted mechanics authority; Play only projects/action-enables it.**
9. **Hermes proposes playable changes; the GM approves; ordinary Save persists.**
10. **Maps/media annotations are reusable asset data, not Play-specific hardcoding.**
11. **Documents remain valid Playable Material; no universal Adventure ORM is required.**
12. **The Of Conks implementation remains mining evidence and should not be merged wholesale.**

## 7. Intentionally unresolved

These questions belong to focused implementation design/handoffs after the canonical design pack is accepted:

- exact serialized representation of stable Scene/Beat/block IDs in Markdown/Tiptap;
- whether first implementation stores semantic structure inline, as a sidecar, or through existing workspace metadata;
- exact Play panel migration order from legacy prep HTML to native capabilities;
- exact external statblock admission mechanism;
- how much run-state recovery/version migration is required when playable material is edited after a run begins;
- exact asset registry/annotation storage contract;
- CR03B same-artifact retrieval architecture if expanded provenance remains insufficient.

Those are implementation decisions, not reasons to delay the product model.
