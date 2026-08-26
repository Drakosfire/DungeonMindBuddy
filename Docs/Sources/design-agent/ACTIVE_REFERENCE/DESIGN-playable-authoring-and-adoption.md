---
document_id: dmb-design-playable-authoring-and-adoption
title: Playable Authoring and Adoption
document_class: product_design
status: active
version: 1.2
created_at: "2026-08-15"
updated_at: "2026-08-26"
workstream: PLAY-SURFACE
architecture_authority: "ARCHITECTURE-playable-material-and-runtime.md"
companion_designs:
  play_projection: "DESIGN-play-surface-projection.md"
  current_moment_cockpit: "DESIGN-play-current-moment-cockpit.md"
evidence:
  - "PR #578 — Canvas block proposal / Of Conks runbook dogfood"
  - "C2S27 native Play dogfood — Plan→Playable fidelity and unexpected-play evidence"
  - "PR #628 — BF1 Beat-first v2 grammar and manifest foundation"
  - "APP-STATE AS1–AS5 — durable WorkObject/WorkRevision + Play Runtime foundation"
supersedes_direction_from:
  - "DESIGN-runbook-roadmap-and-session-ingestion.md"
---

# Playable Authoring and Adoption

## 0. Purpose

This document defines how material becomes part of the **Playable Layer** without silently becoming World Graph canon.

It covers:

- GM-authored preparation;
- source/world material adopted into prep;
- Runbook / Beat / Scene / Decision composition;
- object-attached playable interpretation;
- Agent/Hermes proposals;
- explicit operator approval;
- revision safety;
- reopening and continuing preparation.

It does not define graph writes or source ingestion.

---

## 1. Product promise

> **The GM can develop the version they intend to run, keep the useful decisions, reopen them later, and let Agent/Hermes use them—without requiring those decisions to become canonical World Graph truth.**

The Runbook is a durable, versioned linear authoring object. Play later consumes that exact committed material into a table projection; the GM is not required to navigate the linear document structure during play.

---

## 2. Sources of Playable Material

### 2.1 Direct GM authoring

Examples:

- create a Beat;
- create a Scene;
- add a Decision with Options;
- add Read Aloud / GM Note / Rules Now / Warning;
- add a consequence;
- prepare optional/branch material;
- reference an NPC, location, Threat, statblock, table, map, source, or tool.

Authority: the Playable WorkRevision.

### 2.2 Adopt from Original Source

Examples:

- adopt read-aloud into the Runbook;
- preserve a module rule in Rules Now;
- attach a source-backed hook to an NPC;
- reference a source location without copying all prose.

Retain useful provenance when possible. Source remains source authority.

### 2.3 Adopt from World

Examples:

- insert a typed Hesta reference;
- include an existing location or Threat in a Beat/Scene;
- attach known relationships as context.

The World object remains World authority. Playable owns only why/how it matters for this run.

### 2.4 Adopt exact Mechanics

Playable prep may reference exact accepted mechanics such as a `StatblockRevision`.

Do not copy mechanics into a mutable Runbook schema merely for convenience.

### 2.5 Adopt Runtime outcomes later

After play, the GM may deliberately keep a runtime outcome as next-session prep, recap material, or a candidate World fact.

That is an explicit adoption/promotion action, never automatic Runtime→Playable→World mutation.

---

## 3. Authoring work object and revision truth

The first-class authoring target is an admitted durable Playable WorkObject.

The authoring surface knows:

- exact WorkObject/document ID;
- exact committed WorkRevision / revision number / digest;
- scope;
- editability;
- stable semantic element IDs where targeted mutations depend on them.

APP-STATE now provides immutable historical WorkRevisions. An existing Run may remain bound to revision N after N+1 is committed; Plan editing a newer revision does not make the old Run unreadable or silently retarget it.

The user should never supply filesystem paths as write authority.

### 3.1 Plan authors the exact Playable material — no lossy export

C2S27 falsified derivative export. The contract remains:

> **Plan authors and adopts the exact Playable work object itself. Playable Material is not produced by exporting a lossy derivative from a separate Plan document.**

Consequences:

- Plan edits the admitted Playable WorkObject through normal Canvas/document authority and ordinary Save/commit.
- If a separate free-form Plan document exists, adopting its material into the Playable WorkObject is explicit and reviewable.
- What the GM prepares is what Play later reads from the committed WorkRevision.
- There is no parallel “export to Runbook” transform that can drop semantic blocks, styling, references, or IDs.

---

## 4. Runbook authoring model

The durable hierarchy remains Beat-first:

```text
Runbook
  → ordered Beats
      → ordered Scenes
      → ordered Decisions
          → ordered Options
```

The BF1 v2 grammar is active implementation truth:

```text
beat     → H2
scene    → H3 inside Beat
choice   → H3 inside Beat (optional same-Beat scene association)
option   → marked list item inside choice
```

`choice` is the wire kind; Decision is the product word.

The Runbook is a **linear, readable authoring source**. Its order matters for prep, initial Beat seeding, and explicit order-based navigation. Play is free to project the same truth as a Scene-centered cockpit rather than a document tree.

### 4.1 Create / organize Beats

The GM can:

- create/reorder a Beat;
- choose `spine`, `optional`, or `interrupt`;
- set objective / pressure / phase / summary;
- author At the Table, Read Aloud, GM Note, Rules Now, Warning;
- add Beat-level consequences;
- add Scenes;
- add Decisions;
- add typed references/actions;
- delete/replace Beat with explicit impact when durable Runtime references would be affected.

Stable ID survives ordinary title/prose edits.

### 4.2 Create / organize Scenes inside a Beat

The GM can:

- create/reorder Scene within its Beat;
- set table situation/intent;
- add semantic blocks;
- add prepared pressure/clock definitions;
- add typed references;
- associate Beat-owned Decisions with this Scene;
- delete/replace Scene with explicit impact when Runtime references would be affected.

Scene is the normal table workspace in Play, but remains durably owned by its Beat.

### 4.3 Consequence authoring

Consequences remain authored outcome framing, not a rules engine.

Examples:

```text
If they wait
→ advance Tree Growth.

If they succeed
→ Nar helps freely.

If they search
→ recover precious metal leaves worth 100 gp.

If they choose Fire
→ Firefighting aftermath becomes emphasized.
```

Reward is a useful presentation hint, not a separate treasure subsystem.

### 4.4 Choice / Decision authoring

A Decision has stable identity and ordered stable Options.

An Option may carry:

- authored consequence text;
- `activates` references to later Beat/Scene IDs;
- `suppresses` references to later Beat/Scene IDs.

This is enough to express useful authored branching such as:

```text
A → emphasize B
A → de-emphasize C
```

The authoring UI should describe these as branch/relevance effects, not permissions. A suppressed Scene remains valid Playable material and remains inspectable/navigable at the table.

The first implementation does not add boolean expressions (`A && B && !C`), arbitrary conditions, a workflow graph editor, or automatic consequence execution.

If players later choose something outside all authored Options, Runtime need not fabricate a selection. A later deliberate authoring/Agent proposal may add a new Option through the normal WorkRevision path.

---

## 5. References and unexpected-play preparation

Authoring should prefer typed references over duplication.

References may target:

- World object;
- Source artifact / source anchor;
- Threat / exact mechanics;
- another Playable Beat/Scene;
- roll table;
- map/asset;
- Play capability/tool.

References authored into the current Beat/Scene seed Play's contextual `At a Glance` projection.

But authors are not expected to predict everything the players will do. The Play surface must also provide global/on-demand retrieval for known campaign material that was never referenced by the current Beat/Scene. This requirement does **not** justify polluting the Runbook with exhaustive references merely to make objects discoverable at runtime.

---

## 6. Object-attached Playable authoring

The GM may add run-specific interpretation to a durable World object without promoting it into World truth.

Useful semantic roles may include:

- At the table;
- Attitude;
- Offer / hook;
- Rules now;
- Warning;
- consequence / pressure;
- relevant-now references.

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

These roles do not become universal World fields.

---

## 7. Notes versus authored GM Notes

Do not conflate:

- **GM Note semantic block** — authored Playable Material committed in a WorkRevision;
- **table note** — Runtime observation created while playing.

Table notes may be projected as pinned context objects associated with Run/Beat/Scene/originating Play element. This authoring design does not prescribe a new note persistence schema; deliberate post-session adoption may turn a Runtime note into new Playable material through the normal proposal/adoption + Save path.

---

## 8. Agent/Hermes proposal model

Agent/Hermes is a collaborator, not an implicit writer.

### 8.1 Allowed proposal posture

It may propose:

- insert/edit Read Aloud;
- insert/edit GM Note;
- insert/edit Rules Now;
- insert/edit Warning;
- add/edit consequence;
- add typed reference;
- create/rearrange Beat/Scene/Decision when the mutation contract safely preserves stable identity;
- add an Option / branch effect when the GM explicitly chooses to update prep after unexpected play.

### 8.2 Grounding

Before proposing source/world-derived material, use governed context and carry provenance when appropriate.

### 8.3 Exact targeting

A proposal targets:

- exact Playable WorkObject;
- exact base WorkRevision/digest;
- stable semantic element/position where applicable.

Heading text/fuzzy text is not permanent authority.

### 8.4 Preview and approval

```text
Agent returns proposal
→ UI renders proposed change
→ GM approves or rejects
→ apply to admitted WorkObject
→ Canvas becomes dirty
→ ordinary Save commits next WorkRevision
```

No proposal is applied or made durable automatically.

### 8.5 Concurrency safety

Apply fails safely when:

- base revision changed;
- current Canvas has conflicting unsaved edits;
- target element disappeared;
- proposal scope no longer matches the active WorkObject.

Correct response is re-ground/re-ask, not fuzzy silent retargeting.

---

## 9. Review/adoption language

Prefer operator-intent language:

- Add to prep;
- Keep this;
- Approve into Runbook;
- Replace this GM Note;
- Add consequence;
- Add Option;
- Save.

Avoid filesystem paths, hashes as primary UI, graph mutation vocabulary for Playable-only edits, or “publish canon” unless actually entering World promotion.

---

## 10. Source / World / Mechanics staleness

Playable Material may outlive the source/world/mechanics revision from which it was prepared.

Later changes do not silently rewrite prep.

When useful, surface staleness signals such as:

- source changed since adoption;
- referenced World object changed;
- mechanics binding moved to a newer accepted revision.

The GM decides whether to update the Playable version.

---

## 11. Promotion and post-session adoption

### Playable → World

A GM may deliberately promote a run-local fact through the existing World/graph review authority. The Playable WorkRevision remains provenance/evidence; it does not magically become a graph row.

### Runtime → Playable

Post-session, the GM may inspect:

- resolved Beats;
- selected Choices;
- notes;
- Combat outcomes;
- improvised facts.

Possible deliberate actions:

- keep as next prep;
- add to recap;
- promote to World;
- discard as transient.

No automatic promotion.

---

## 12. Revision and Run compatibility

A Run binds one exact committed Playable WorkRevision.

- Newer WorkRevisions do not invalidate the historical revision already pinned by a Run.
- Ordinary authoring produces new immutable revisions; it does not rewrite the Run's bytes.
- Explicit same-grammar rebase may move a Run to a newer revision only when Runtime references remain preserve-only admissible.
- v1→v2 is a structural grammar boundary and is not silently mapped; existing v1 Runs remain bound to their exact v1 revisions, while a new v2 Run is the normal path for Beat-first structure.

---

## 13. Authoring acceptance stories

A conforming implementation should prove:

1. GM creates/reopens a durable Playable Runbook WorkObject.
2. GM authors Beat→Scene/Decision→Option v2 structure with stable IDs.
3. Renaming prose/title does not change semantic identity.
4. GM authors an Option with consequence + activates/suppresses effects.
5. Those effects survive Save/reload and remain visible during authoring.
6. GM inserts exact Threat/mechanics references rather than copying statblock truth.
7. Runbook remains a readable linear document even though Play later projects it Scene-first visually.
8. A newer WorkRevision does not make a Run pinned to an older revision unreadable.
9. Agent/Hermes proposes a targeted Playable change grounded in admitted context.
10. UI previews and requires explicit approval.
11. stale/dirty state prevents unsafe apply.
12. approved proposal becomes durable only through ordinary Save/WorkRevision commit.
13. unexpected-play discoverability does not require authors to exhaustively reference every possible campaign object in every Beat/Scene.

---

## 14. Non-goals

- No automatic World Graph publication.
- No universal Adventure ORM.
- No requirement that source ingestion automatically extract Scenes/Beats.
- No separate agent-only writer.
- No fuzzy text locator as permanent semantic identity.
- No copy of exact statblock mechanics into Runbook storage.
- No forced typed schema for every creative note.
- No automatic source/world/mechanics reconciliation.
- No automatic Runtime→Playable or Playable→World promotion.
- No workflow/condition DSL beyond the existing small Choice transition vocabulary.
- No requirement that runtime Play navigate the Runbook as a document tree.
