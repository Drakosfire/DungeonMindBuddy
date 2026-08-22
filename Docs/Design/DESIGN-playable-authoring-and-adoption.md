---
document_id: dmb-design-playable-authoring-and-adoption
title: Playable Authoring and Adoption
document_class: product_design
status: active
version: 1.1
created_at: "2026-08-15"
updated_at: "2026-08-21"
workstream: PLAY-SURFACE
architecture_authority: "ARCHITECTURE-playable-material-and-runtime.md"
companion_designs:
  play_projection: "DESIGN-play-surface-projection.md"
  current_moment_cockpit: "DESIGN-play-current-moment-cockpit.md"
evidence:
  - "PR #578 — Canvas block proposal / Of Conks runbook dogfood"
  - "C2 Session 27 native Play dogfood — BLOCKED / PLAY NOT READY (Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md)"
supersedes_direction_from:
  - "DESIGN-runbook-roadmap-and-session-ingestion.md"
---

# Playable Authoring and Adoption

## 0. Purpose

This document defines how material becomes part of the **Playable Layer** without silently becoming World Graph canon.

It covers:

- GM-authored preparation;
- source/world material adopted into prep;
- Runbook/Scene/Beat construction;
- object-attached playable interpretation;
- Hermes proposals;
- explicit operator approval;
- revision safety;
- reopening and continuing preparation.

It does not define graph writes or source ingestion.

## 1. Product promise

> **The GM can develop the version they intend to run, keep the useful decisions, reopen them later, and let Hermes use them—without requiring those decisions to become canonical World Graph truth.**

This is the concrete authoring contract behind CON-READY CR-U11 and CR-U12.

## 2. Sources of Playable Material

Playable Material can originate from several places.

### 2.1 Direct GM authoring

Examples:

- write a Scene;
- add a Beat;
- add a GM Note;
- decide an NPC's current attitude;
- change a shop for this run;
- prepare an encounter;
- add a consequence;
- create an optional branch.

Authority: the Playable revision itself.

### 2.2 Adopt from Original Source

Examples:

- copy/adopt read-aloud into the Runbook;
- preserve a module rule in Rules Now;
- attach a source-backed hook to an NPC;
- reference a source location without copying all prose.

The adopted block should retain useful provenance when possible.

The source remains source authority.

### 2.3 Adopt from World

Examples:

- insert a typed Hesta reference;
- attach the known relationship to the current Scene;
- include an existing location or threat in a Beat.

The World object remains World authority.

The Runbook owns only why/how it matters for this run.

### 2.4 Adopt exact Mechanics

Playable prep may reference exact mechanics such as an accepted `StatblockRevision`.

It should not copy mechanics into a new mutable Playable schema merely for convenience.

### 2.5 Adopt Runtime outcomes later

After play, the GM may deliberately keep a runtime outcome as next-session prep.

This is a new adoption action, not automatic promotion.

## 3. Authoring work object

The first-class authoring target is an admitted, durable Playable work object.

A workspace document / Markdown Canvas remains a valid normal implementation.

The authoring surface must know:

- exact document/work-object ID;
- current revision/digest;
- scope;
- whether the object is editable;
- semantic element IDs when targeted mutations depend on them.

The user should not supply filesystem paths as write authority.

### 3.1 Plan authors the exact Playable material — no lossy export

C2S27 falsified the derivative-export path: Plan ideas did not enter Play with sufficient semantic fidelity, and the Plan export dropped playable blocks and styling — authored work was lost.

The authoring contract is therefore:

> **Plan authors and adopts the exact Playable work object itself. Playable Material is not produced by exporting a lossy derivative from a separate Plan document.**

Consequences:

- The Plan surface edits the admitted Playable work object through the normal Canvas/document authority and ordinary Save; there is no parallel "export to Runbook" transformation that can drop blocks, styling, or semantics.
- If a separate free-form Plan document exists, adopting its material into the Playable work object is an explicit, reviewable adoption — not a batch export.
- What the GM sees while preparing in Plan is what Play will project at the table, up to projection (projection never rewrites the material).

The exact Plan↔Playable composition is frozen by the reviewed current-moment
cockpit contract (`DESIGN-play-current-moment-cockpit.md` §8): Plan edits the same
admitted Playable work object directly; free-form planning documents adopt
material through the explicit, reviewable adoption seam; Beat/Scene/Decision
authoring uses structure-aware controls over the same document rather than a
graph editor; and the Plan preview and Play projection read the same committed
revision. The no-lossy-derivative rule is settled here and there.

## 4. Runbook authoring

After C2S27, the Beat is the session-scale organization unit; Scenes are
concrete situations inside a Beat. See
`ARCHITECTURE-playable-material-and-runtime.md` §5.

The Beat-first authoring model is now frozen by the reviewed current-moment
cockpit contract (`DESIGN-play-current-moment-cockpit.md` §1–§2, §8): Beats are
authored as v2 H2 elements, Scenes as v2 H3 elements inside exactly one Beat,
Decisions as v2 H3 `choice` elements — Beat-owned siblings of Scenes,
distinguished by directive kind rather than heading level — with an
optional Scene projection association, and Options as marked list items carrying authored
consequences and `activates`/`suppresses` edges. The shipped P1/P2 grammar
remains Scene-first and cannot serialize this; the authoring controls below
are implemented through the reviewed slice sequence, not by patching v1.

### 4.1 Create/organize Beats

The GM can:

- create Beat;
- choose `spine`, `optional`, or `interrupt`;
- set the table objective / pressure / phase;
- write At the Table;
- add Read Aloud;
- add GM Note;
- add Rules Now;
- add Warning;
- add Consequences;
- add Decisions with Options and authored transitions;
- add references/actions;
- title/reorder Beats within the Runbook;
- delete/replace Beat with explicit impact on referenced runtime state.

Stable identity is preserved through title/prose edits.

### 4.2 Create/organize Scenes inside a Beat

The GM can:

- create Scene inside a Beat;
- title/reorder Scene within its Beat;
- set table intent;
- add pressure/clock definitions;
- add typed references;
- add authored choices/transitions;
- delete/replace Scene with explicit impact on referenced runtime state.

### 4.3 Consequence authoring

The authoring UI should help express:

```text
trigger / condition
→ outcome
```

without forcing a large rules engine.

Examples:

```text
If they wait
→ advance Tree Growth.

If they succeed
→ Nar helps freely.

If they search
→ recover precious metal leaves worth 100 gp.

If they choose Fire
→ open Firefighting aftermath.
```

"Reward" is a useful presentation/category hint. It does not require `treasure` as a separate Beat field.

### 4.4 Choice / Decision authoring

A Choice/Decision has stable identity and stable options.

The GM may connect an option to:

- a next Scene or Beat;
- one or more consequences;
- an authored transition that changes which later Scenes/Beats remain possible or relevant;
- another Playable reference.

The first implementation need not become a general workflow graph.

## 5. Object-attached playable authoring

The GM can add run-specific material to a World object.

Useful semantic roles include:

- At the table;
- Attitude;
- Offer / hook;
- Rules now;
- Warning;
- consequence / pressure;
- relevant-now references.

These roles are intentionally flexible.

Example:

```text
World NPC: Morwin Blackwell

Playable attachment:
At the table:
  sleepy shopkeep, keeps mistaking the party for old customers

Attitude:
  furious at Saladin

Offer:
  gem-cutting job
```

This does not require adding `attitude` or `offers` as universal World Graph fields.

## 6. Typed references

Authoring should prefer references over duplication.

References may target:

- World object;
- Source/document/evidence;
- Threat / exact mechanics;
- another Playable Scene/Beat/object;
- Play capability/tool;
- later, reusable asset annotation.

The Canvas/editor is responsible for preserving durable reference identity through Save/reload.

## 7. Hermes proposal model

Hermes is a collaborator, not an implicit writer.

### 7.1 Allowed proposal posture

Hermes may propose changes such as:

- insert Read Aloud;
- insert GM Note;
- insert Rules Now;
- insert Warning;
- add/edit Consequence;
- add a typed reference;
- later, create/rearrange Scene/Beat when the mutation contract supports stable identity safely.

### 7.2 Grounding

Before proposing source/world-derived material, Hermes must use the governed context available to it.

A proposal may carry provenance references.

The proposal itself is not truth merely because Hermes generated it.

### 7.3 Targeting

A proposal targets:

- exact Playable work object;
- exact base revision/digest;
- stable semantic element/position when applicable.

Heading text and fuzzy old text may remain temporary compatibility locators but are not the permanent identity contract.

### 7.4 Preview and approval

Required flow:

```text
Hermes returns proposal
→ UI renders proposed block/change
→ GM approves or rejects
→ apply to current admitted work object
```

No proposal is applied automatically.

### 7.5 Concurrency safety

Application fails safely when:

- target document changed since admission;
- current local Canvas contains conflicting unsaved edits;
- stable target element no longer exists;
- proposal scope no longer matches the active work object.

The correct user action is re-ground/re-ask, not silent fuzzy retargeting.

### 7.6 Persistence

Approved proposal application creates ordinary local document dirtiness.

Durability remains:

```text
apply proposal
→ Canvas dirty
→ normal Save / revision write
```

Agent mutation does not gain a private persistence path.

## 8. Review/adoption language

The product language should describe operator intent, not storage mechanics.

Prefer:

- Add to prep
- Keep this
- Approve into Runbook
- Replace this GM Note
- Add consequence
- Save

Avoid exposing:

- graph mutation language for Playable-only edits;
- filesystem paths;
- artifact hashes as primary UI;
- "publish canon" unless the operator is actually entering a separate World promotion flow.

## 9. Source/world staleness

Playable Material may outlive the source/world revision from which it was prepared.

That is acceptable.

A later source/world change should not silently rewrite prep.

Instead, when useful, DungeonBuddy may surface:

- source changed since this block was adopted;
- referenced World object changed;
- mechanics binding moved to a newer accepted revision.

The GM decides whether to update the playable version.

Staleness is a review signal, not automatic mutation.

## 10. Promotion to World

The Playable Layer is not a dead end.

A GM may deliberately promote an adopted run-local fact into durable World knowledge.

That must route through the existing World/graph review authority.

Example:

```text
Playable:
Hesta secretly treated the mayor's daughter.

GM action:
Make this part of the world.

→ graph authoring/review
→ accepted World assertion if approved
```

The Playable authoring surface may initiate this workflow later, but it cannot bypass it.

## 11. Runtime adoption after play

Post-session, the GM may inspect:

- resolved Beats;
- selected choices;
- scene notes;
- combat outcomes;
- improvised NPC/location facts.

The system may propose:

- keep as next prep;
- add to recap;
- promote to World;
- discard as transient.

Those are separate deliberate actions.

No automatic "runtime becomes canon" path is allowed.

## 12. Revision and run compatibility

When a Run already exists against Playable revision R:

- ordinary prose edits that preserve referenced element IDs can create R+1 safely;
- removal/replacement of referenced Scene/Beat/Choice IDs requires explicit compatibility handling;
- current Run remains bound to its recorded revision until migrated or intentionally continued on a new revision.

The first implementation may choose a conservative rule such as "finish current Run on its pinned revision."

It must not silently reinterpret runtime references.

## 13. Authoring acceptance stories

A conforming first implementation should prove:

1. GM creates a Playable Runbook as a durable workspace object.
2. GM creates at least two Scenes and several stable Beats.
3. GM renames a Beat; its stable identity remains unchanged.
4. GM adds a consequence representing a reward; no treasure-specific storage is required.
5. GM attaches a run-local Attitude/Offer to a World NPC without changing graph canon.
6. GM inserts an existing Threat reference rather than copying statblock data.
7. Hermes proposes a GM Note grounded in admitted context.
8. UI previews it and requires explicit approval.
9. A stale digest or dirty Canvas prevents unsafe apply.
10. After approval, the document is dirty but not durable until ordinary Save.
11. Save/reload preserves the playable material and stable IDs.
12. Hermes can later use the deliberately saved Playable Material alongside governed World/Source context.

## 14. Non-goals

- No automatic World Graph publication.
- No universal Adventure ORM.
- No requirement that source ingestion automatically extract Scenes/Beats.
- No separate agent-only document writer.
- No fuzzy text locator as permanent semantic identity.
- No copy of exact statblock mechanics into Runbook storage.
- No forced typed schema for every creative GM note.
- No automatic staleness reconciliation.
- No automatic Runtime → Playable or Playable → World promotion.
