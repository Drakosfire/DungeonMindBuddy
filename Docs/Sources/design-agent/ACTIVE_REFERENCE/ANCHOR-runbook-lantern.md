---
document_id: dmb-anchor-runbook-lantern
title: Runbook Lantern
document_class: design_anchor
status: active
version: 2.0
created_at: "2026-06-18"
updated_at: "2026-08-15"
architecture_authority: "ARCHITECTURE-playable-material-and-runtime.md"
play_design: "DESIGN-play-surface-projection.md"
authoring_design: "DESIGN-playable-authoring-and-adoption.md"
workstream_anchor: "../Plans/STEWARDS-ANCHOR-con-ready.md"
roadmap: "../Roadmaps/ROADMAP-con-ready.md"
---

# ANCHOR — Runbook Lantern

## One-line anchor

> **The Runbook Lantern is the GM-facing light cast from World, Source, Mechanics, and deliberate Playable Material: it illuminates what matters for the current table moment without pretending to be the whole world, the source, mechanics authority, or live runtime state.**

Use the phrase:

```text
Runbook Lantern
```

when Play/runbook work starts drifting into a dashboard, database, duplicate mechanics store, hidden canon writer, or adventure-specific architecture.

## 1. Current authority

This anchor is a mnemonic, not sequencing authority.

Read in this order for current design:

1. `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
2. `Docs/Roadmaps/ROADMAP-con-ready.md`
3. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
4. `Docs/Design/DESIGN-play-surface-projection.md`
5. `Docs/Design/DESIGN-playable-authoring-and-adoption.md`
6. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`

Historical runbook direction documents remain evidence and may not override these authorities.

## 2. The lantern model

```text
ORIGINAL SOURCE
rich material and provenance

WORLD
durable semantic knowledge

MECHANICS
exact accepted rules/statblocks

PLAYABLE MATERIAL
the GM's deliberately prepared version
Runbook → Scene → Beat
object-attached prep
choices and consequences

        ↓ projected through Play

RUNBOOK LANTERN
the current table-facing light

        ↓ table interaction

PLAYED / RUNTIME STATE
current Scene/Beat, resolved Beats, selected choices,
notes, combat/runtime state
```

## 3. What belongs in the light

Ask:

> **Does this help the GM run the next few minutes without losing the thread?**

Good candidates:

- current Scene and Beat;
- At the Table;
- Read Aloud;
- GM Note;
- Rules Now;
- Warnings;
- Consequences;
- relevant-now NPC/location/item/threat references;
- map/media when useful;
- contextual Play actions such as Roll, Read Source, Ask Hermes, Add to Combat.

## 4. What does not belong to the lantern as authority

If it answers:

- **What is durably true in the world?** → World authority.
- **What exactly did the original material say?** → Source authority.
- **What are the exact creature mechanics?** → Mechanics authority.
- **What did the GM deliberately prepare for this run?** → Playable Material.
- **What is happening right now / already happened?** → Runtime authority.
- **Where do shared bars/projection hosts live?** → Surface Interaction Layer.

Play may project any of these. Projection does not transfer ownership.

## 5. Beat rule

The Beat is the smallest normal focused Runbook unit.

Useful semantics:

```text
At the table
Read aloud
GM note
Rules now
Warnings
Consequences
Open now
Tools
```

`treasure` is not a root Beat concept.

A treasure/reward is a **consequence** of search, success, choice, or another table condition.

Likewise, "If they wait/succeed/fail" are useful presentation labels over consequence triggers.

## 6. Separation rule

Keep this distinction intact:

```text
PLAYABLE MATERIAL
what the GM intends to run

≠

RUNTIME STATE
what has been selected/resolved/noted/changed during the run
```

Runtime points at stable Scene/Beat/Choice identities. It does not rewrite the Runbook.

## 7. Reference rule

References are handles into authority, not copies of truth.

A Beat or Object Sheet should point to:

- World object;
- Source;
- exact Mechanics;
- another Playable element;
- Play capability/tool.

Opening a reference should preserve the current table moment.

Opening is not mutation.

## 8. Agent rule

Hermes may help author the lantern, but:

```text
ground
→ propose
→ preview
→ GM approve
→ Canvas dirty
→ normal Save
```

No hidden Playable write. No hidden graph write.

## 9. Dogfood rule

A convention one-shot, Mireward, Of Conks, or any other real table is **proof material**.

Never promote a campaign-specific bridge, enum, node dictionary, or page layout into architecture merely because it made one dogfood run work.

Preserve the interaction. Replace the special-case mechanism.

## 10. Compact handoff paragraph

> **Runbook Lantern:** DungeonBuddy keeps Original Source, World, exact Mechanics, Playable Material, and Played/Runtime State distinct. Play is the table-facing projection over those authorities. A Runbook is durable Playable Material organized as stable Scenes and Beats. Beats lead with At the Table and may contain Read Aloud, GM Notes, Rules Now, Warnings, Consequences, references, and contexual tools. Rewards/treasure are consequences, not a separate Beat authority. Play Object Sheets are projections, not new object ontology. Runtime state records current/resolved/selected/noted state against stable playable IDs and never rewrites the Runbook. Hermes proposes playable changes; the GM approves; ordinary Save persists.
