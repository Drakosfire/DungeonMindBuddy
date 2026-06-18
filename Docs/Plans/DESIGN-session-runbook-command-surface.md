# DESIGN — Session Runbook as Command Surface

**Status:** Draft design anchor  
**Created:** 2026-06-18  
**Project area:** DungeonBuddy / Command Board / Tiptap runbook  
**Primary premise:** The session runbook is the table-facing projection of prep, not the prep database itself.

---

## 0. North Star

The session runbook should read like a tight script and behave like a command surface.

It is not a dashboard of every prep object. It is the playable projection of prep: a calm, linear document that moves the GM from opening frame to scene beats, choices, consequences, likely combats, and fallback material. Every important noun and procedure in that document can be clicked, expanded, rolled, launched, cited, or edited without losing the thread.

The end-state product promise:

> Prep produces a beautiful editable session document. During play, every important noun and procedure is clickable. The GM never has to remember where the detail lives.

The runbook should feel like:

> A script with live hyperlinks, editable blocks, and GM tools hiding behind the nouns.

---

## 1. What We Have Proved Already

The current Tiptap and Markdown chain has crossed the line from exploration into product primitive.

Completed foundations:

- Semantic Markdown renderer and theme contract.
- Markdown embeds and modal previews in the Command Board.
- Semantic callout syntax for `READ-ALOUD`, `GM-NOTE`, `RULES`, and `WARNING`.
- Tiptap custom callout node rendering the same semantic class contract.
- Tiptap JSON → semantic Markdown export.
- Rich-text mark preservation in the exporter.
- Exporter safety hardening for labels, links, and block-start escaping.
- Browser-local Tiptap working-board state.
- Backend Markdown file write prepare/commit boundary.
- Manual dogfood of local edit → prepare → diff → commit → file on disk.

The critical architecture is now stable:

```txt
Tiptap JSON = local editable working-board state
Exported Markdown = derived artifact
Backend API = intentional file materialization boundary
Prep Markdown file = durable table-facing runbook artifact
Corpus/canon = separate authority boundary
Operational JSON = live combat/clocks/tools state
```

---

## 2. Product Distinction

The runbook body is not the database.

The runbook body owns:

- Session sequence.
- GM-facing framing.
- Read-aloud text.
- Scene beats.
- Choice/consequence prompts.
- Which references matter now.
- Which tools are contextually relevant.
- Which blocks are editable, locked, or committed.

The runbook body must not own:

- Canonical NPC truth.
- Full location truth.
- Full statblock truth.
- Roll table canonical storage.
- Combat HP/current state.
- Source document truth.
- Item ownership ledger.

Those live behind typed references and tools.

---

## 3. Runbook Default Experience

The default experience is linear and calm.

The GM scrolls through:

1. Opening frame.
2. Immediate table context.
3. Scene beats.
4. Player choices.
5. Consequences.
6. Likely combats.
7. Fallback material.
8. Emergency improvisation tools.

At any point, embedded chips let the GM drill sideways into detail without losing the main thread.

Example target shape:

```md
## Opening: North Reach Gate

> [!READ-ALOUD]
> The wall rises black against the storm...

> [!GM-NOTE]
> Lysandro should recognize Lysandra before the guard resolves entry.

If the players push toward the refugees, use [Gate Dilemma d12].

If combat starts, launch [North Gate Combat].

Active threats: [Sewer Meat Creature], [Aberrant Meatwing], [Corrupted Meat Golem].

Key people: [Lysandro Ironveil], [Brin Holloway], [Captain Lysandra Ironveil].

Location context: [North Reach Gate], [Mireward Wall].
```

But each bracket is a typed reference, not a plain link.

---

## 4. Core Layers

The runbook has four layers.

### 4.1 Runbook body

The readable session script: headings, scene beats, read-aloud, GM notes, choices, consequences, likely combats, fallback material.

### 4.2 Typed references

Inline chips pointing to NPCs, locations, statblocks, roll tables, items, citations, prior-session facts, and operational actions.

### 4.3 Context tools

Tools are available from the selected chip or selected block, but they should not visually compete with the prose.

Examples:

- Roll this table.
- Open statblock.
- Add to combat.
- Show source excerpt.
- Open corpus file.
- Edit block.
- Prepare write.
- Commit write.

### 4.4 Save/canon state

Save and authority boundaries are visible when editing or committing.

A block may be:

- Editable scratch.
- Saved runbook draft.
- Locked for live play.
- Committed to a safe prep target.
- Read-only canon/reference.
- Operational state, stored outside prose.

---

## 5. Typed Reference Model

The runbook should represent important nouns and procedures as typed chips.

Initial types:

```txt
npc
location
statblock
roll-table
item
citation
action
prior-fact
combat
```

Markdown-compatible fallback syntax:

```md
[Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil)
[North Reach Gate](#dmb-ref:location:north-reach-gate)
[Sewer Meat Creature](#dmb-ref:statblock:sewer-meat-creature)
[Gate Dilemma d12](#dmb-ref:roll-table:gate-dilemma-d12)
[Session 22 ending](#dmb-ref:citation:c2s22-ending)
[North Gate Combat](#dmb-action:combat:north-gate-combat)
```

This syntax keeps the file readable as Markdown while giving the renderer and Tiptap editor a stable enhancement contract.

Renderer-enhanced output should eventually look like:

```html
<button
  class="md-ref-chip md-ref-chip-npc"
  data-md-ref-type="npc"
  data-md-ref-id="lysandro-ironveil"
>
  Lysandro Ironveil
</button>
```

The chip is the doorway. The detail lives behind the doorway.

---

## 6. Chip Interaction Ladder

Each chip should have a compact, predictable interaction model.

### NPC chip

- Click: compact NPC card.
- Secondary action: full modal.
- Deep action: open corpus/source file.

### Location chip

- Click: location blurb, map note, immediate table facts.
- Secondary action: full modal.
- Deep action: open location file.

### Statblock chip

- Click: compact stat card.
- Secondary actions: full statblock, copy HP defaults, add to combat.

### Roll table chip

- Click: inline roll UI.
- Secondary actions: edit table, roll, copy result, prepare/commit if edited.

### Citation chip

- Click: source excerpt.
- Secondary actions: open full source, show provenance chain.

### Item chip

- Click: mechanics/lore/ownership card.
- Secondary actions: assign, inspect, open source.

### Action/combat chip

- Click: prepare/launch operational flow.
- Secondary actions: open combat tracker, add default entities, inspect encounter setup.

---

## 7. Visual Language

The runbook itself stays mostly prose and structured beats. Richness lives in chips and popups.

Color should carry type, not noise.

Suggested color semantics:

```txt
NPCs              warm/person color
Locations         cool/place color
Statblocks        danger/threat color
Roll tables       utility/procedure color
Items             treasure/object color
Citations         muted/source color
Live actions      strong/action color
Canon/save state  badge treatment, not chip color
```

The color should tell the GM what kind of thing the chip is before they read it.

---

## 8. Command Surface, Not Dashboard

The Command Board should avoid becoming a grid of competing panels.

Instead:

```txt
inline chip -> compact popover -> context drawer -> full modal
```

A right rail can exist, but it should be calm until something is selected.

No selection:

- Session status.
- Save boundary.
- Maybe clocks.

NPC selected:

- NPC card.
- Relationships.
- Source/corpus links.

Statblock selected:

- Quick statblock.
- Add-to-combat action.

Roll table selected:

- Roll UI.
- Edit/commit affordances.

Block selected:

- Edit, lock, prepare, commit controls.

This preserves the central thread of the runbook.

---

## 9. Locking and Save Model

Do not treat the runbook as one giant editable blob.

Each block should eventually know its state.

Candidate block save states:

```txt
editable_scratch
saved_runbook_draft
locked_for_live
committed_prep
read_only_reference
operational
```

Definitions:

### editable_scratch

Local-only and safe to mutate.

### saved_runbook_draft

Persisted as a browser-local or prep-draft working document, but not committed to a durable file.

### locked_for_live

Intended for table use. Edits require explicit unlock.

### committed_prep

Written to a safe prep Markdown file through backend prepare/commit.

### read_only_reference

Loaded from corpus/canon/source. Not directly editable in this runbook.

### operational

Live mutable state like HP, clocks, turn order, active combat, and temporary play state. Stored outside prose.

This model lets the UI say:

```txt
This paragraph is yours to edit.
This read-aloud block is locked for live play.
This NPC chip points to canon.
This roll table has unsaved edits.
This combat link launches operational state, not prose.
```

---

## 10. Data Model Direction

A future runbook document can be represented conceptually as:

```ts
type RunbookDocument = {
  schema_version: "dmb_runbook_document_v1";
  document_id: string;
  title: string;
  campaign_id: string;
  session: number;
  status: "scratch" | "draft" | "locked_for_live" | "committed";
  blocks: RunbookBlock[];
};

type RunbookBlock = {
  block_id: string;
  type:
    | "heading"
    | "scene-beat"
    | "read-aloud"
    | "gm-note"
    | "choice"
    | "consequence"
    | "combat-setup"
    | "fallback"
    | "reference-list";
  save_state:
    | "editable_scratch"
    | "saved_runbook_draft"
    | "locked_for_live"
    | "committed_prep"
    | "read_only_reference";
  content: unknown; // Tiptap JSON block content
  refs: RunbookReference[];
};

type RunbookReference = {
  ref_type:
    | "npc"
    | "location"
    | "statblock"
    | "roll_table"
    | "item"
    | "citation"
    | "combat"
    | "action"
    | "prior_fact";
  ref_id: string;
  label: string;
  href: string;
};
```

Do not build this full model in one PR. Use it as a target shape.

---

## 11. Tiptap Schema Direction

Current custom node:

- `callout`, with `kind` values for `read-aloud`, `gm-note`, `rules`, and `warning`.

Likely next nodes:

Block nodes:

```txt
sceneBeat
choiceBlock
consequenceBlock
combatSetupBlock
fallbackBlock
```

Inline atom nodes:

```txt
npcRef
locationRef
statblockRef
rollTableRef
itemRef
citationRef
combatLaunchRef
priorFactRef
```

The immediate next step should be inline reference chips, not a full runbook block system.

---

## 12. Roadmap: Proposed PR Sequence

This roadmap intentionally moves from small contracts to product workflow.

---

### PR 1 — Typed Markdown Reference Chips

**Branch:** `feat/runbook-reference-chips`  
**Title:** `feat(command-board): add typed runbook reference chips`

#### Goal

Add a Markdown-compatible typed reference syntax and render it as colored chips in the existing Markdown renderer.

#### Scope

- Add chip detection for Markdown links whose href begins with:
  - `#dmb-ref:`
  - `#dmb-action:`
- Render recognized links as typed chips.
- Add CSS classes by type.
- Add fixture coverage.
- Dogfood with one small runbook-style Markdown sample.

#### Supported initial examples

```md
[Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil)
[North Reach Gate](#dmb-ref:location:north-reach-gate)
[Sewer Meat Creature](#dmb-ref:statblock:sewer-meat-creature)
[Gate Dilemma d12](#dmb-ref:roll-table:gate-dilemma-d12)
[Session 22 ending](#dmb-ref:citation:c2s22-ending)
[North Gate Combat](#dmb-action:combat:north-gate-combat)
```

#### Acceptance Criteria

- Plain Markdown remains readable.
- Recognized links render with `md-ref-chip` classes.
- Ref type and id are available as data attributes.
- Unknown/invalid typed refs fall back safely to normal links or inert visible text.
- No resolver/popover required yet.

#### Out of Scope

- Corpus lookups.
- Popovers.
- Tiptap chip editing.
- Roll UI.
- Combat launch.

---

### PR 2 — Tiptap Inline Reference Chip Node Spike

**Branch:** `spike/tiptap-inline-reference-chips`  
**Title:** `spike(command-board): prototype Tiptap inline reference chips`

#### Goal

Teach Tiptap to represent the same typed references as inline atom nodes and export them to the Markdown fallback syntax from PR 1.

#### Scope

- Add one inline atom node: `runbookRef`.
- Attributes:
  - `refType`
  - `refId`
  - `label`
  - `href`
- Render as a chip inside Tiptap.
- Export to Markdown link syntax.
- Add toolbar/dev controls to insert sample refs.
- Add serializer tests.

#### Acceptance Criteria

- Tiptap chip renders inline with prose.
- Exported Markdown matches PR 1 syntax.
- Existing callouts still export correctly.
- Local state still persists.
- Prepare/commit still works with chip Markdown.

#### Out of Scope

- Full resolver.
- Markdown import.
- Editing chip attrs through polished UI.
- Document manager.

---

### PR 3 — Runbook Reference Chip Popover Shell

**Branch:** `feat/runbook-reference-popover-shell`  
**Title:** `feat(command-board): add runbook reference chip popover shell`

#### Goal

Make typed chips interactive without building full data resolution yet.

#### Scope

- Add click/focus handling for `md-ref-chip` elements.
- Open a compact popover or side context card.
- Show:
  - label
  - type
  - ref id
  - href
  - placeholder actions appropriate to type
- Add keyboard and escape handling.
- Add tests for chip click behavior.

#### Acceptance Criteria

- Clicking a chip does not navigate away.
- Popover/context card opens.
- Popover is type-aware.
- Prose layout remains calm.
- No giant dashboard panel appears by default.

#### Out of Scope

- API-backed lookup.
- Real statblock rendering.
- Real combat launch.
- Real roll UI.

---

### PR 4 — API-Backed Reference Resolver v1

**Branch:** `feat/runbook-reference-resolver-v1`  
**Title:** `feat(command-board): resolve runbook reference chips from live indexes`

#### Goal

Resolve chips into compact cards using existing live indexes and known corpus metadata.

#### Scope

Use existing or adjacent endpoints where available:

- NPC index.
- Location index.
- Statblock index.
- Roll table index.

Resolve chip types:

- `npc` → compact NPC card.
- `location` → location blurb/card.
- `statblock` → quick statblock card.
- `roll-table` → table metadata and placeholder roll action.
- `citation` → inert source/provenance placeholder if full citation resolver does not exist yet.
- `action` → typed action placeholder.

#### Acceptance Criteria

- Chip cards show real data where resolver can find it.
- Missing refs show a clear unresolved state.
- No canon data is edited through the chip.
- Errors do not break the runbook.

#### Out of Scope

- Mutating corpus.
- Full modal editor.
- Roll table editing.
- Combat tracker mutation.

---

### PR 5 — Tiptap-Authored Command Board Runbook Dogfood

**Branch:** `feat/tiptap-authored-command-board-runbook`  
**Title:** `feat(command-board): dogfood a Tiptap-authored session runbook`

#### Goal

Create one table-facing runbook authored through Tiptap, written through backend prepare/commit, and rendered by the static Command Board with typed chips.

#### Target File

```txt
evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-session-runbook.md
```

#### Static Embed Target

Add or update a Command Board page section:

```html
<section class="prep-panel runbook-panel">
  <div class="panel-heading">
    <h2>Session Runbook</h2>
    <a href="/tiptap-callout-spike?doc=north-gate-session-runbook">Edit in Tiptap</a>
  </div>

  <div
    class="md-embed"
    data-md-src="content/tiptap/north-gate-session-runbook.md"
    data-md-theme="command"
  ></div>
</section>
```

#### Acceptance Criteria

- Runbook file is authored/committed through Tiptap flow.
- Static Command Board renders it as a Markdown embed.
- Typed chips render visibly.
- At least one chip of each major type appears.
- The runbook reads as a linear session script.

#### Out of Scope

- Replacing Live Play wholesale.
- Full query-param document manager.
- Markdown import.
- Corpus writes.

---

### PR 6 — Document Descriptor and Route Parameter Support

**Branch:** `feat/tiptap-runbook-document-descriptors`  
**Title:** `feat(command-board): add Tiptap runbook document descriptors`

#### Goal

Replace hardcoded Tiptap document/target path values with a small descriptor registry.

#### Descriptor Shape

```ts
type TiptapRunbookDescriptor = {
  documentId: string;
  title: string;
  campaignId: string;
  session: number;
  targetRelpath: string;
  themeId: "command" | "plain" | "statblock";
  description?: string;
};
```

#### Scope

- Add a small local descriptor registry.
- Support route query like:

```txt
/tiptap-callout-spike?doc=north-gate-session-runbook
```

- Initialize localStorage key per descriptor.
- Set default write target from descriptor.

#### Acceptance Criteria

- Existing spike document still works.
- North Gate runbook opens by descriptor.
- Local state does not collide between documents.
- Prepare/commit targets the descriptor file.

#### Out of Scope

- Backend document registry.
- Multi-document dashboard.
- Markdown import.

---

### PR 7 — Minimal Markdown to Tiptap Import for Supported Runbook Syntax

**Branch:** `feat/tiptap-runbook-markdown-import-v1`  
**Title:** `feat(command-board): import supported runbook Markdown into Tiptap`

#### Goal

Load a committed runbook Markdown file back into Tiptap for supported syntax.

#### Supported Import

- Headings.
- Paragraphs.
- Lists if cheap.
- Semantic callouts.
- Typed reference links.
- Basic marks if already reliable.

#### Acceptance Criteria

- A committed Tiptap-authored runbook can be reopened and edited without losing major structure.
- Unsupported Markdown degrades visibly and safely.
- Import does not execute HTML.
- Import does not mutate files.

#### Out of Scope

- Full CommonMark import.
- Arbitrary HTML.
- Corpus import.

---

### PR 8 — Block Save-State Badges

**Branch:** `feat/runbook-block-save-state-badges`  
**Title:** `feat(command-board): show runbook block save-state badges`

#### Goal

Make edit/canon/live boundaries visible at block level.

#### Scope

- Add save-state badge rendering for selected/hovered blocks.
- States:
  - local scratch
  - saved draft
  - locked for live
  - committed prep
  - read-only reference
- Add lock/unlock affordance for live play blocks.

#### Acceptance Criteria

- The user can tell whether a block is local, committed, locked, or read-only.
- Commit controls are not ambiguous.
- Read-only/canon blocks are not directly editable.

#### Out of Scope

- Full block database.
- Collaborative editing.
- Fine-grained permissions.

---

### PR 9 — First Real Replacement of a Markdown Surface

**Branch:** `feat/replace-north-gate-runbook-markdown-surface`  
**Title:** `feat(command-board): replace North Gate runbook surface with Tiptap-backed authoring`

#### Goal

Replace one existing Markdown-only prep surface with a Tiptap-authored runbook workflow.

#### Scope

- Pick one real North Gate / Live Play runbook surface.
- Keep static rendering as the play-facing default.
- Add edit link to Tiptap document editor.
- Use descriptor route.
- Support import or explicit seeded source depending on prior PR state.
- Commit back to safe prep file.

#### Acceptance Criteria

- GM can run from the static rendered runbook.
- GM can edit through Tiptap.
- GM can prepare/commit updates.
- Static runbook updates after reload.
- Chips are interactive.
- Canon boundaries remain visible.

#### Out of Scope

- Replacing every Markdown surface.
- General CMS.
- Player-facing publishing.

---

### PR 10 — Reusable Runbook Editor Component

**Branch:** `refactor/tiptap-runbook-editor-component`  
**Title:** `refactor(command-board): extract reusable Tiptap runbook editor`

#### Goal

Move from spike route/component to reusable product component.

#### Scope

- Extract `TiptapRunbookEditor`.
- Extract document descriptor handling.
- Extract file write panel.
- Extract local state hook.
- Keep callout and reference chip extensions modular.

#### Acceptance Criteria

- Spike route can use reusable editor.
- North Gate runbook can use reusable editor.
- Tests move with extracted hooks/components.
- Behavior remains unchanged.

#### Out of Scope

- New product features.
- Broad redesign.

---

## 13. Recommended Immediate Next PR

Start with PR 1:

```txt
feat(command-board): add typed runbook reference chips
```

Why this first:

- It is the smallest step from Markdown renderer to command surface.
- It makes the runbook concept visible immediately.
- It does not require a resolver, popover, document manager, or Markdown import.
- It creates the stable syntax that Tiptap can export to.

Primary success metric:

```txt
A Markdown runbook can contain typed references that still read naturally as prose, but render as recognizable, type-colored chips in Command Board.
```

---

## 14. Design Guardrails

Do not let the runbook become a dashboard.

Do not let Tiptap become canon by accident.

Do not hide write boundaries.

Do not require the GM to know file paths during play.

Do not make every surface editable by default.

Do not put combat HP or live clocks in prose.

Do not build a generic CMS before proving one playable runbook loop.

---

## 15. End-State Summary

A session runbook is a linear playable document with typed, tool-aware references.

It reads like a script.

It behaves like a command surface.

It writes safely.

It never confuses local draft, prep file, canon reference, or live operational state.
