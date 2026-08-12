# CON-READY — Product Roadmap and Acceptance Stories

**Status:** ACTIVE PRODUCT ROADMAP  
**Line of work:** `CON-READY`  
**Re-anchored:** 2026-08-11  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Historical starting anchor:** `main` after merged PR #560, merge commit `85a2bbf048d92afed1911031ca7b6a311115873c`  
**Stewardship anchor:** [`../Plans/STEWARDS-ANCHOR-con-ready.md`](../Plans/STEWARDS-ANCHOR-con-ready.md)

---

## 0. Purpose

CON-READY is a product-readiness workstream.

It is not a demo program, a PDF-ingestion program, or an architecture-completion program. Architecture and contracts matter only when they enable or protect a concrete GM-visible capability.

The convention one-shot is the forcing-function acceptance scenario because it is bounded, time-sensitive, and unforgiving. The resulting capabilities should remain useful for ordinary campaign material.

CON-READY succeeds when:

> **A GM can bring playable material into a world, understand and navigate what was ingested, prepare the version they intend to run, and rely on DungeonBuddy during a live session for original source material, NPCs, locations, mechanics, shops/notes, Hermes retrieval, and combat preparation.**

Success is defined by the user stories in this document. Internal contracts, schemas, migrations, projections, and architecture are implementation means rather than independent definitions of success.

---

## 1. Product model

CON-READY distinguishes four useful layers of state.

```text
ORIGINAL SOURCE
The Markdown brought into DungeonBuddy.
Rich prose, tables, images, statblocks, adventure text.

        ↓ extraction / provenance

WORLD
Durable semantic representation.
NPCs, threats, locations, relationships, mechanics bindings.
Lossy on purpose; points back to source.

        ↓ GM preparation

PLAYABLE WORLD
The version the GM intends to run.
Prep, NPC development, invented relationships, shop state,
encounter composition, local changes, GM notes.

        ↓ actual play

PLAYED EXPERIENCE
What happened at the table.
Combat/runtime state, decisions, consequences, session notes.
```

These layers must not be collapsed merely because they refer to the same fictional world.

### 1.1 Original Source remains first-class

The World Graph is a semantic and relational knowledge layer, not a replacement for the source prose.

A graph object should retain navigable provenance into the rich source that established it. When the compact graph representation is insufficient, both the GM and Hermes should be able to follow that provenance through governed source access.

### 1.2 The World Graph may be intentionally lossy

CON-READY does not require every useful sentence, scene, clue, item, table, shop, or adventure beat to become graph ontology.

The graph should capture enough durable identity and relationships to make the world navigable and queryable, while source documents preserve richer detail.

### 1.3 Playable material is durable without automatically becoming canon

GM preparation, brainstorming decisions, local relationships, encounter compositions, shop changes, and other choices made for a particular run must be preservable without silently publishing them into durable World Graph truth.

The exact storage contract for this `Playable Layer` is not frozen by this roadmap. The product behavior is.

---

## 2. Governing principles

1. **User stories are the gates.** A slice is complete when a GM-visible story works end-to-end with real material.
2. **Markdown is the ingress boundary.** PDF extraction is upstream and out of scope; `.md` upload and paste should converge on one normalization path.
3. **World placement is explicit.** Imported material belongs to an existing world or establishes a new world container. Do not require an orphan-source architecture for CON-READY.
4. **Source stays readable.** Ingestion must not turn the original material into stripped debug text.
5. **Graph provenance is useful navigation.** Evidence/provenance should let the GM and Hermes reach the original source, not exist only for audits.
6. **Hermes remains governed.** Source follow-through must extend admitted provenance, not grant arbitrary filesystem or corpus browsing.
7. **Mechanics deserve structure where it pays off.** Threat/statblock mechanics should preferentially become exact typed resources because Hermes and Combat can reuse them.
8. **Documents are valid product objects.** A shop, prep sheet, NPC notes, or other useful material need not gain bespoke ontology before it can be useful.
9. **Preparation is not automatic canon.** Creative collaboration may persist in the Playable Layer without rewriting the World Graph.
10. **Combat may advance in parallel.** CON-READY defines what the GM must be able to hand to Combat; it does not require the full future Play roadmap to land first.
11. **Unexpected play is an acceptance case.** Prepared paths alone are insufficient.
12. **No hidden Eldyrwild assumption.** A new one-shot world must work without special-case knowledge of the existing campaign.

---

# 3. Acceptance user stories

## CR-U1 — Bring external material into DungeonBuddy

> **As a GM, I can take Markdown from outside DungeonBuddy and bring it into the world I am working on without preparing it specifically for DungeonBuddy.**

Success means:

- paste Markdown is supported;
- `.md` file loading may follow but must use the same normalization boundary;
- the GM can choose an existing world or establish a new world;
- the source is persisted inside that world's existing local filesystem hierarchy;
- the source gets a useful title and can be reopened and edited through Build;
- future Markdown emitted by the external PDF pipeline can enter through the same boundary.

Not success:

- manually copying a file into an undocumented path;
- running a bespoke CLI to make the source visible;
- requiring graph IDs, ExtractionRun vocabulary, or internal document kinds from the GM.

---

## CR-U2 — Read the original source as a real document

> **As a GM, I can open the material I imported and read it comfortably inside DungeonBuddy.**

Minimum useful rendering includes:

- headings;
- paragraphs;
- emphasis;
- lists;
- tables;
- links;
- useful spacing and typography.

The source representation must remain extensible to images/assets. If a local Markdown image reference is available, the GM-facing reading experience should render it. Multimodal interpretation of those images by Hermes is not a CON-READY blocker.

The normal presentation is the named source document, not hashes, artifact IDs, or evidence spans.

---

## CR-U3 — DungeonBuddy gives me a useful semantic index

> **As a GM, after ingesting the material I can quickly find the important people, threats, places, organizations, and relationships without rereading the entire source.**

The first useful extraction target is bounded:

- named NPCs / actors;
- creatures / threats;
- locations;
- factions / organizations / groups;
- useful source-backed relationships;
- provenance back into the source.

CON-READY does not initially require perfect extraction of beats, clues, events, items, objectives, branches, or full adventure structure.

Additional extraction structure should enter the roadmap only when real one-shot dogfood demonstrates that its absence materially harms preparation or live play.

---

## CR-U4 — I can inspect and correct what DungeonBuddy understood

> **As a GM, I can recognize important extraction mistakes and repair them without thinking in graph-database terms.**

Common corrections should be cheap:

- wrong name → rename;
- source mention matches an existing object → connect/use existing;
- accidental duplicate → merge/connect appropriately;
- wrong or irrelevant object → remove/ignore;
- missing important object → add;
- wrong relationship → change/remove.

When importing into an established world, the normal experience should help prevent duplicate durable identities.

The product language should be human-facing: for example, “This looks like the existing Hesta. Use her?” rather than exposing graph-collision vocabulary.

---

## CR-U5 — I can follow a world object back to its source

> **As a GM, when the compact NPC/location/threat view is not enough, I can open its original source and land near the passage that established it.**

Example:

```text
Hesta
Halfling apothecary

Owns → Hesta's Apothecary

SOURCE
Hesta's Apothecary
[Read source]
```

`Read source` should open the rich Markdown document, ideally at or near the relevant passage. Exact source anchors and hashes remain integrity mechanisms underneath the user-facing interaction.

Provenance is therefore a normal navigation feature, not only an evidence/debug panel.

---

## CR-U6 — Hermes can follow provenance when the graph is insufficient

> **As a GM, I can ask Hermes about a known object, and if the graph does not contain enough detail, Hermes can consult the original source material that object came from.**

Target behavior:

```text
GM asks about Hesta
→ Hermes finds Hesta in the World Graph
→ graph facts are insufficient
→ Hermes follows admitted source provenance
→ Hermes reads more of the exact source artifact
→ Hermes answers from graph + source as appropriate
```

The governing boundary is:

> **Graph admission grants bounded access to the exact source artifact behind the admitted provenance.**

It does not grant arbitrary Markdown, corpus, or filesystem browsing.

The likely capability is source-artifact follow-through from an admitted anchor, with bounded reading around that anchor and potentially bounded search within that exact admitted artifact.

---

## CR-U7 — Hermes remains truthful about graph facts and source detail

> **As a GM, Hermes can use useful detail from the original source even when that detail has not been independently promoted as a graph assertion, without pretending those states are identical.**

The distinction should normally remain unobtrusive. Hermes should lead with useful game information rather than provenance reports, while preserving the authority distinction underneath.

---

## CR-U8 — Important NPCs are ready to use

> **As a GM, I can find an important NPC quickly, open them, understand who they are, and ask Hermes about them.**

A formal universal NPC sheet is not required for CON-READY.

A useful experience may combine:

- name and concise source-backed summary;
- important relationships;
- links to relevant place/threat/source material;
- `Ask Hermes`;
- `Read source`.

Success is access and usability, not maximum typed-field coverage.

---

## CR-U9 — Important places and shops are ready to use

> **As a GM, I can quickly open an important place or shop and get the information needed to run it.**

A shop may remain a rich source/playable document rather than a first-class graph ontology if it can be:

- found quickly;
- rendered well;
- reached from relevant NPC/location context;
- queried through the governed agent/source path;
- preserved with its useful inventory, prices, descriptions, and notes.

Documents are an acceptable product answer when they solve the GM's task.

---

## CR-U10 — Threats have usable mechanics

> **As a GM, when the source contains a creature I expect to use, I can reach its actual statblock easily from the creature/threat.**

The preferred target is:

```text
Threat
  ↓ exact mechanics binding
accepted immutable StatblockRevision
```

rather than repeatedly extracting combat numbers from prose.

CON-READY must determine the smallest useful path for externally supplied statblocks to enter the accepted mechanics system. External mechanics should not need to be regenerated merely because DungeonBuddy did not author them originally.

If typed import proves substantially larger than expected, a rich rendered/queryable source statblock may serve as an intermediate state, but typed exact mechanics remains the target because it unlocks reuse by Hermes and Combat.

---

## CR-U11 — I can develop the version of the world I intend to run

> **As a GM, during prep I can brainstorm with Hermes, make decisions, and preserve those decisions without automatically rewriting the World Graph.**

Examples include:

- newly invented NPC relationships;
- motivations and secrets adopted for this run;
- encounter composition;
- shop changes;
- scene alterations;
- local notes and overrides.

A decision such as “Hesta secretly treated the mayor's daughter during quarantine” should be durable when the GM deliberately keeps it, but should not automatically create a canonical graph assertion.

This is the `Playable Layer` product requirement.

---

## CR-U12 — Hermes can reason over the playable version

> **As a GM, once I deliberately save something as part of my prep, Hermes can use it alongside the durable world and original source.**

Target model:

```text
WORLD GRAPH
source-backed durable world knowledge

ORIGINAL SOURCE
rich admitted prose behind that knowledge

PLAYABLE LAYER
GM-authored decisions for the current run
```

This follows source follow-through in priority. Perfect Playable-Layer retrieval is not required before the first useful source-backed convention milestone if it would endanger the bounded one-shot path.

---

## CR-U13 — Prepared combats are ready before the session

> **As a GM, I can identify the combats I expect to run and have their combatants/mechanics prepared before sitting down at the table.**

CON-READY defines the expected handoff:

```text
prepared encounter
  ├── exact creature/threat identity
  ├── quantity
  ├── exact mechanics where available
  └── encounter notes
        ↓
Combat
```

Combat implementation may proceed as a parallel workstream. CON-READY must not require the entire future Play/world-object program before a useful convention combat workflow exists.

---

## CR-U14 — An unexpected fight does not break the workflow

> **As a GM, when the players start a fight I did not prepare, I can assemble it from known NPCs/threats and begin running it without editing JSON or reconstructing everything from memory.**

This is a required dogfood scenario. Prepared combat alone is not sufficient.

---

## CR-U15 — I can use DungeonBuddy instead of my memory

> **As a GM running the session, DungeonBuddy is faster and safer than trying to remember where the information was.**

Representative live questions include:

- “Who runs the apothecary?”
- “What exactly does Hesta sell?”
- “Open Hesta's shop.”
- “What does the source say about the eastern door?”
- “Show me the Tunnel Crawler statblock.”
- “Who in town knows about the mine?”
- “What did I decide about Hesta and the mayor during prep?”

The answer may come from the World Graph, source follow-through, Playable Layer, or exact mechanics. The GM should not need to know which internal subsystem supplied it.

---

## CR-U16 — Navigation is part of the answer

> **As a GM, when Hermes tells me about something, I can easily open the underlying NPC, location, threat, source document, or mechanics instead of receiving only prose.**

Hermes is a route into the useful parts of DungeonBuddy, not a detached chatbot next to them.

---

## CR-U17 — Reload does not destroy preparation

> **As a GM, I can restart/reload DungeonBuddy and still have the imported material, extracted world, source navigation, prep documents, mechanics, and prepared combat state I was relying on.**

No success claim may depend on transient developer state or manual reconstruction after restart.

---

# 4. Delivery roadmap

The roadmap is sequenced by user-visible capability rather than architecture layer.

## CR01 — Source Ingress & Reading

**Primary stories:** CR-U1, CR-U2.  
**Outcome:** paste Markdown → choose/create world → durable source → reopen → rich reading/editing.

Design ingress so `.md` files and future RulesIngestion-produced Markdown can use the same boundary. Preserve an extensible asset/image model even if paste-only is the first UI.

## CR02 — Source-Backed World Ingestion

**Primary stories:** CR-U3, CR-U4, CR-U5.  
**Outcome:** run bounded extraction on real one-shot material, review/correct meaningful mistakes, publish into the chosen world, and navigate object → relevant source.

This slice or its immediate predecessors must cover generic first-world initialization when the chosen destination has no graph yet.

## CR03 — Hermes Source Follow-Through

**Primary stories:** CR-U6, CR-U7.  
**Outcome:** graph retrieval remains the discovery path; when an admitted source artifact is needed, Hermes can read farther into that exact artifact without arbitrary filesystem authority.

This is a high-priority CON-READY capability.

## CR04 — Game-Facing Objects & Mechanics

**Primary stories:** CR-U8, CR-U9, CR-U10.  
**Outcome:** NPC/location/threat navigation leads with useful game content; external statblocks have the best practical path toward exact accepted mechanics; shops/documents remain usable without unnecessary ontology.

## CR05 — Playable Preparation

**Primary stories:** CR-U11 and the first useful part of CR-U12.  
**Outcome:** durable non-graph preparation can be authored, reopened, and deliberately used by the GM. Start with existing document/reference capabilities before inventing a new datastore.

## CR06 — Combat Readiness Integration

**Primary stories:** CR-U13, CR-U14.  
**Outcome:** prepared encounters can reach Combat and unexpected combats can be assembled quickly. Coordinate with the parallel Combat track rather than replacing it.

## CR07 — Real One-Shot Run

**Primary stories:** CR-U15, CR-U16, CR-U17 plus cumulative verification of all prior stories.  
**Outcome:** use an actual selected convention adventure without implementation-tailored fixtures, manual JSON surgery, or hidden Eldyrwild assumptions.

Anything that forces the GM to abandon DungeonBuddy for manual source search, memory reconstruction, or combat rebuilding becomes concrete CON-READY debt.

---

# 5. Explicitly deferred / not required for CON-READY

The following are not required before CON-READY can succeed:

- wiring the PDF extraction pipeline directly into DungeonBuddy;
- Hermes arbitrary filesystem or Markdown search;
- Hermes multimodal interpretation of imported images;
- perfect extraction of scenes, clues, beats, events, items, or branches;
- a universal Adventure schema;
- full NPC or Shop ontology;
- automatic graph writes from Hermes brainstorming;
- automatic promotion of Playable Layer decisions into canon;
- continuous Hermes conversation identity across every surface;
- completion of the entire formal Play/world-object roadmap;
- a universal asset-management platform;
- broad latency/performance work not demonstrated as a blocker by real dogfood.

These may become successors when actual use proves their value.

---

# 6. Final acceptance journey

CON-READY is complete only when this experience works with real one-shot material:

```text
I have external Markdown for an adventure.

I bring it into DungeonBuddy.

I choose an existing world or create a new one.

I can read the original material comfortably, including its useful structure
and available assets.

DungeonBuddy extracts enough of the world that I can find the important NPCs,
locations, organizations, and threats.

I open an NPC.

I can jump directly to where that NPC came from in the source.

I ask Hermes something the graph summary does not contain.

Hermes follows the NPC's admitted provenance, consults the source, and gives me
a useful answer without pretending arbitrary files are authoritative.

I can open important shops and other playable material as readable documents.

I can open the monsters and their mechanics.

During prep, I develop NPC relationships and other ideas and keep them as part
of the world I intend to run without silently rewriting graph canon.

My expected combats are prepared.

The players do something unexpected and I can adapt the combat without JSON or
memory reconstruction.

During play I use Hermes and navigation to recover information faster than I
could by manually searching the source.

I restart DungeonBuddy and the material and preparation I depended on are still
there.
```

If this journey works, CON-READY is successful.

---

# 7. Stewardship rule

Every agent designing, implementing, reviewing, or re-anchoring work under CON-READY must begin with [`../Plans/STEWARDS-ANCHOR-con-ready.md`](../Plans/STEWARDS-ANCHOR-con-ready.md), reconcile it against current repository state, and judge proposed work against the user stories above.

No successor roadmap or implementation handoff may silently redefine CON-READY as an architecture-completion program.