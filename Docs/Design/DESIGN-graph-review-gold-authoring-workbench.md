# Design — Graph Review + Gold Authoring Workbench

**Status:** Accepted design direction  
**Date:** 2026-07-02  
**Workstream:** Graph Memory / Graph Review / Gold Authoring  
**Supersedes:** `Docs/Plans/HANDOFF-prime-design-graph-exploring-tool-consolidation.md`  
**Companion roadmap:** `Docs/Plans/ROADMAP-graph-review-gold-authoring-workbench.md`

## 1. Product thesis

Graph review should feel like reading a living campaign chronicle, not operating a graph QA dashboard.

The durable workbench is a shared prose-with-pills projection surface with two modes:

1. **Review mode** compares two graph readings of a recap as side-by-side projected prose.
2. **Author mode** turns one projection lane into a gold-labeling surface where the GM selects text, declares nodes, draws edges, links to existing campaign objects, and accepts or rejects LLM-assisted proposals.

The source text remains primary. Graph nodes and edges are useful only insofar as they reveal usable campaign meaning: threats, encounters, statblocks, NPCs, locations, quests, factions, objects, relationships, consequences, and prep affordances.

The central UX promise:

```text
The GM touches prose, and the campaign graph reveals what can be used at the table.
```

## 2. Why this design exists

The first Graph Review Workbench successfully consolidated several existing review tools into a lane-based diagnostic surface, but dogfood showed that it failed the human-review goal. It still centered metadata panels, scorecards, tables, object IDs, and evidence lists. The user did not need more metadata first. The user needed to see the recap prose itself, with graph projections rendered directly over it.

The corrected target is not “merge viewers.” The corrected target is:

```text
Render graph interpretation as projected reading behavior over source prose,
then make that same projection substrate writable for human gold authoring.
```

This moves the tool from a diagnostic dashboard toward a magical campaign workbench: the recap is the surface; the graph is revealed through it; the GM can correct and author truth directly inside it.

## 3. Core principles

### 3.1 Source prose is the surface

Review and authoring both start from rendered recap markdown. Metadata tables are secondary drill-ins. The right rail is collapsed by default.

### 3.2 Game utility before graph metadata

A node hover must answer useful GM questions before it answers extraction-debug questions.

Bad default:

```text
threat/combat encounter · extracted from this paragraph · 3 connected edges
```

Better default:

```text
Tripod Null-Calf
Siege scout and gate-pressure monster.
Appears in: Mireward Gate Battle
Connected to: North Gate, Mireward defenders, Shepherd corruption
Available game surfaces: Statblock, Encounter notes, Related threats
```

Evidence, comparator scores, source-span IDs, extraction pass names, and raw object details are available only after explicit drill-in.

### 3.3 Relationships are game links

Edges should render as readable relationships and useful campaign affordances, not as triples first.

Examples:

```text
Tripod Null-Calf threatens North Gate
Captain Lysandra Ironveil defends Mireward Gate
Under-Hymn Brood undermines palisade supports
```

Clicking a relationship highlights endpoint spans in the prose and opens a relationship card. Evidence and score are nested under an explicit Evidence / Debug affordance.

### 3.4 Authoring is naming, linking, and judging

Gold authoring is a human data-labeling tool over prose:

- select text → declare node;
- click two nodes/spans → draw edge;
- link a span/node to an existing corpus or graph object;
- ask the LLM to propose local or whole-document additions;
- accept, reject, or edit proposals;
- save through a safe two-phase write path.

The LLM never writes directly into the projection. It proposes into a staging tray. Only accepted or edited-then-accepted items become part of the authored graph.

### 3.5 One substrate, two modes

Review and authoring share the same rendering substrate, lane model, node/edge presentation components, and projection payload family. Author mode is not a separate editor that merely resembles review mode.

### 3.6 Delight needs explicit state

The UX can be magical only if the state is legible. The user must always know:

- which lane is gold, live, seeded draft, or blank authoring draft;
- which lane is editable;
- what is staged versus accepted;
- how many unsaved changes exist;
- whether they are selecting text, drawing an edge, reviewing proposals, or inspecting relationships.

## 4. Primary modes

## 4.1 Review mode

Review mode places two graph sources in a two-lane prose projection.

Lane sources may include:

- gold fixture projection;
- live graph-ingest run projection;
- live baseline run;
- live vocabulary-assisted run;
- manual/reference variant reshaped into the projection contract when feasible;
- future authored gold draft.

The lane comparison is visual first:

- matched pills cross-highlight between lanes;
- gold-only or live-only objects are visible inline;
- relationships can highlight endpoints in prose;
- metrics are a thin summary strip, not the primary content;
- evidence and scoring are drill-in details.

Review mode answers:

```text
What did each graph source believe while reading this recap,
and how do those beliefs differ in the prose itself?
```

## 4.2 Author mode

Author mode makes one gold-shaped lane writable.

Entry options:

1. **Start blank:** render processed recap markdown with zero authored graph objects.
2. **Start from run:** seed the authoring draft from a live run or existing gold fixture, then let the human correct it.

Authoring primitives:

1. **Span → node:** select text, choose node type, label it, and create an evidence-backed node.
2. **Node/span → edge:** click node A, click node B or fresh span, pick or type a predicate, and confirm the relationship.
3. **Link to existing:** connect an authored node or selected span to an existing corpus/graph object, such as an NPC hub, location, statblock, encounter, thread, or global node.
4. **LLM per-seed expand:** ask the model to propose nearby nodes, edges, attributes, and existing links from one declared seed.
5. **LLM whole-document reflow:** ask the model to propose a fuller graph using accepted human labels as anchors and constraints.
6. **Staging tray decisions:** accept, reject, or edit proposals before they enter the document.
7. **Safe save:** batch changes and write through a prepare → diff → confirm → commit cycle.

Author mode answers:

```text
How can the GM turn this prose into curated, reusable gold truth
without hand-writing candidate_graph_gold.json?
```

## 5. Layout and interaction model

## 5.1 Default layout

- Main surface: two-lane projected markdown reader.
- Right rail: collapsed by default.
- Lane header: always visible and explicit.
- Staging tray: visible only in author mode when proposals or unsaved changes exist.
- Metrics/debug: collapsed or thin-strip by default.

Example lane headers:

```text
Left: Gold Draft · editable · 9 unsaved changes
Right: Live Run · read-only · vocabulary run
```

## 5.2 Node hover card

A node hover card should show game-useful details first.

Preferred sections:

1. **Identity:** name, game-facing type, short description.
2. **Use at table:** statblock, encounter note, location dossier, NPC dossier, item card, quest thread, or generation affordance.
3. **Connected objects:** readable connected relationships, hoverable/clickable.
4. **Authoring actions:** edit label/type, link existing object, draw edge, ask for proposals.
5. **Evidence / Debug:** explicit drill-in only.

If a useful surface exists, such as a statblock for Tripod Null-Calf, the hover card should offer it directly. If one does not exist but the node type implies one, the card may offer a draft-generation affordance.

## 5.3 Relationship card

Clicking a relationship opens a game-facing relationship card.

Example:

```text
Tripod Null-Calf threatens North Gate
This relationship makes the Null-Calf part of the north-gate pressure sequence.
Use it to pin barricades, mark gate supports, or interrupt cure/support lines.

Actions: Highlight endpoints · Open North Gate · Open encounter · Evidence / Debug
```

Evidence, source anchors, comparator score, extractor pass, and raw object IDs are intentionally behind Evidence / Debug.

## 5.4 Existing-object linking

Author mode must distinguish three node states:

1. **Authored local node:** created from selected text in this gold fixture.
2. **Linked existing node:** connected to an existing corpus/graph object.
3. **Proposed unresolved node:** suggested by the LLM but not accepted.

The UI does not perform identity merge. It asks a backend resolver for candidates and lets the human choose.

Required interaction:

```text
Selected span: Tripod Null-Calf
Declared type: combat_encounter / threat
Resolver suggestions:
  - Link to existing statblock: Tripod Null-Calf
  - Link to existing threat family: Shepherd corruption siege horrors
  - Create new local node
  - Search manually
```

This fills the architectural gap between gold authoring and the existing campaign/corpus graph. Gold authoring cannot become a session-local island.

## 6. Data model expectations

## 6.1 Projection payload

Both review and authoring should use an edit-friendly projection payload family shaped around:

- markdown;
- source anchors/spans;
- node views keyed by stable IDs;
- mentions / pill placements anchored into markdown;
- relationship views;
- evidence badges;
- linked existing-object refs;
- lane source metadata;
- authoring state when applicable.

Gold projection must render the gold fixture’s own recap copy, not a live run’s recap copy. Anchoring should prefer text-snippet matching within each lane’s own document rather than assuming shared line numbers across gold and live copies.

## 6.2 Gold fixture output

Author mode writes candidate-graph-gold-shaped data. It must not invent a parallel gold format.

The authored fixture should support:

- nodes;
- edges;
- evidence refs;
- semantic state;
- linked existing-object refs where applicable;
- stable IDs for authored objects;
- provenance sufficient for later comparison.

## 6.3 Authoring event log

Keep an append-only event log now, but do not build analysis UI in the first slice.

The low-lift requirement is to preserve human-vs-LLM decisions while they are available:

```json
{
  "schema": "dmb_graph_gold_authoring_event_v1",
  "event_id": "...",
  "campaign_id": "...",
  "session_id": "...",
  "timestamp": "...",
  "trigger": "manual | per_seed_expand | whole_doc_reflow",
  "seed": { "node_id": "...", "node_type": "...", "label": "...", "span_text": "..." },
  "llm_proposal": {},
  "human_decision": "accept | reject | edit",
  "final_value": {}
}
```

Later analysis can mine this data for prompt, taxonomy, and extraction-policy improvements. That analysis surface is out of scope for v1.

## 7. Backend contracts needed

## 7.1 Gold projection endpoint

Return a projection payload shaped like the live union-supergraph projection, but sourced from a gold fixture.

Required behavior:

- use the gold fixture’s own normalized recap copy;
- bulk-resolve gold evidence refs;
- construct node views and relationship views;
- produce mentions by snippet/text matching inside the gold recap;
- avoid line-number assumptions across lanes.

## 7.2 Game object enrichment adapter

The projection UI needs game-facing affordances, not only graph metadata.

Given a node or linked object, the backend should provide available surfaces such as:

- statblock;
- encounter note;
- NPC dossier;
- location dossier;
- item card;
- faction brief;
- quest/thread surface;
- related threats;
- generation affordance when expected material is missing.

This adapter may be thin at first and can return empty affordances honestly. The UI should degrade cleanly.

## 7.3 Existing-object resolver

Given selected text, declared type, label, source context, campaign/session, and current draft graph, return candidate existing objects and create-new options.

The resolver owns candidate identity suggestions. The UI owns human choice.

## 7.4 Gold authoring write endpoints

Mirror the Party Registry two-phase write pattern:

1. `prepare_graph_gold_authoring_write(...)` returns a diff and confirm token derived from target path, new content, and current file-state token.
2. `commit_graph_gold_authoring_write(...)` requires the confirm token and rejects stale-file conflicts.

Edits accumulate client-side or in a draft session; save writes a batch, not one request per node or edge.

## 7.5 LLM-assist actions

Two structured-extraction actions:

1. `graph_gold_authoring_seed_expand`
2. `graph_gold_authoring_document_reflow`

Rules:

- use strict JSON-schema structured output;
- use centralized model policy action IDs;
- use the existing environment/client bootstrap path;
- surface refusal/incomplete/errors to the staging tray;
- never write proposals directly into the document.

## 8. User stories canonized

## 8.1 The page wakes up as campaign prep

As a GM, I open a recap projection and read it like normal prose. Important people, places, threats, quests, and encounters appear as subtle magical markings. The right rail is collapsed by default.

When I hover Tripod Null-Calf, I see what it is, what scene or encounter it belongs to, what known game artifacts exist for it, and what it connects to. If a statblock exists, I can open it. If an encounter note exists, I can open it. If related threats exist, I can inspect them.

## 8.2 Two enchanted readings of the same session

As a GM, I place gold on the left and a live run on the right. Both render as prose with pills. Hovering a gold pill highlights the matched live pill. Missing and extra graph beliefs are visible inline.

## 8.3 Relationships are game links

As a GM, I click a node and reveal relationship chips such as `threatens → North Gate` or `appears in → Mireward Gate Battle`. Hovering a relationship highlights both endpoint spans. Clicking it opens a game-facing relationship card. Evidence and score are drill-in details.

## 8.4 Name a thing into the graph

As a GM, I highlight a phrase, declare it as a node, choose a type and label, and the phrase becomes a committed pill.

## 8.5 Draw a relationship by touching story objects

As a GM, I click one node, then another node or fresh span, label the relationship, preview it as a sentence, and confirm it.

## 8.6 The assistant proposes, but connects to the existing world

As a GM, I ask for proposals from a seed. The staging tray includes both new objects and possible links to existing corpus/graph objects. I choose create-new, link-existing, reject, or edit.

## 8.7 Correct a live run into gold

As a GM, I start from a live run and edit it into a gold draft. The live run becomes clay, not canon.

## 8.8 Reflow from my anchors

As a GM, I label several important anchors and ask the model to propose a fuller graph around them without overwriting accepted human labels.

## 8.9 Seal the gold fixture safely

As a GM, I save a batch of edits. The UI shows a human-readable diff, then commits only after confirmation. Rejected proposals never enter the gold fixture.

## 8.10 Keep the event data, defer mining UI

As a maintainer, I want authoring decisions logged now so future analysis can discover where the model diverges from human judgment. The analysis UI is later.

## 8.11 Retire old surfaces when this is real

As the only user, I do not need backward-compatibility ceremony. Once the new workbench covers real review and authoring sessions, old table-first surfaces should be removed or hidden. Useful diagnostic pieces can move inside drill-in panels.

## 8.12 Never lose orientation

As a GM, I always know what each lane is, whether it is editable, what is staged, what is accepted, and what remains unsaved.

## 9. Non-goals

- Do not build a node-link diagram as the primary interaction.
- Do not make metrics or evidence the default user-facing surface.
- Do not make LLM proposals appear in the document before acceptance.
- Do not build event-log analytics in v1.
- Do not preserve old tool routes for compatibility once the new surface is proven.
- Do not let the UI invent identity merge semantics.
- Do not write directly to gold fixtures without two-phase confirmation.
- Do not use prompt-only JSON for LLM assist.

## 10. Acceptance tests

### Review-mode acceptance

Open a real session with gold in one lane and a live run in the other. Both lanes render as prose-with-pills. Hovering a matched node in either lane highlights its counterpart. Missing/extra nodes are visible inline. The user can inspect relationships and useful game surfaces without opening a metadata table.

### Author-mode acceptance

Open a blank projection for a real recap paragraph. Select a phrase and declare a node. Trigger per-seed LLM assist. Accept one proposal and reject one. Save through a two-phase write. The resulting gold fixture contains exactly accepted items, and the event log records both accepted and rejected proposal decisions.

### Existing-link acceptance

Select a span that corresponds to an existing object. The resolver returns candidate existing nodes or corpus refs. The user links the authored node to an existing object instead of creating an isolated duplicate.

## 11. Final design sentence

```text
Graph Review + Gold Authoring is a magical prose-first workbench where the GM reads, compares, names, links, and safely seals graph truth directly inside the campaign chronicle.
```
