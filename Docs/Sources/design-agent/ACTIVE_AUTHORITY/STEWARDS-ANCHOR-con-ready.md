# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY`  
**Created:** 2026-08-11  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Canonical product roadmap:** [`../Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md)  
**Historical starting point:** `main` after merged PR #560, merge commit `85a2bbf048d92afed1911031ca7b6a311115873c`

---

## 0. Why this document exists

This is the first document every design agent, implementation agent, reviewer, and re-anchor steward should read before doing work under CON-READY.

Its job is to keep the workstream aimed at a usable GM experience instead of drifting into demo completion, architecture completion, ontology expansion, or speculative framework work.

Chat history is not authority for a fresh agent. The checked-in roadmap and current repository state are.

A fresh CON-READY agent must:

1. read this anchor;
2. read the canonical CON-READY roadmap;
3. reconcile both against current `main`, active PRs, and relevant owning contracts;
4. identify which user story is currently false;
5. select the smallest independently useful slice that makes that story materially more true;
6. state what remains false afterward;
7. prove the GM-visible behavior, not merely the internal contract.

---

## 1. Mission

CON-READY exists to prove this product outcome:

> **A GM can bring playable material into a world, understand and navigate what was ingested, prepare the version they intend to run, and rely on DungeonBuddy during a live session for original source material, NPCs, locations, mechanics, shops/notes, Hermes retrieval, and combat preparation.**

The convention one-shot is the acceptance scenario, not the ontology.

The workstream should produce capabilities that remain useful when the source material is:

- authored by the GM;
- converted externally from PDF;
- purchased/downloaded material;
- a one-shot;
- a campaign chapter;
- supplemental worldbuilding material;
- material that belongs to an existing world;
- material that establishes a new world.

The upstream PDF extraction pipeline is not being wired into DungeonBuddy in this line. Markdown is the normalization boundary.

---

## 2. Governing product model

Keep these layers distinct:

```text
ORIGINAL SOURCE
rich Markdown brought into DungeonBuddy

        ↓ provenance / extraction

WORLD
reviewed durable semantic world knowledge

        ↓ GM preparation

PLAYABLE WORLD
what the GM intends to run

        ↓ actual play

PLAYED EXPERIENCE
what happened at the table / runtime state
```

### 2.1 Original Source

The source is not disposable extraction input.

It remains a first-class rich artifact that the GM can read and navigate. The source may preserve headings, tables, prose, links, images/assets, statblock text, and other details that should not be forced into graph ontology.

### 2.2 World

The World Graph is a semantic index and relational knowledge layer.

It may be intentionally lossy. It should capture enough durable identity and relationships to make the world findable and useful while retaining navigable provenance to richer source material.

### 2.3 Playable World

The Playable Layer contains durable GM decisions made for the version being prepared or run. It may include prep documents, new relationships, NPC interpretations, shop state, encounter composition, local overrides, and other deliberately kept ideas.

Playable decisions must not silently become graph canon.

### 2.4 Played Experience

Runtime state and outcomes remain separate from source truth and mechanics authority. Combat HP, initiative, conditions, defeat state, and other live mutation do not rewrite the World Graph or immutable mechanics.

---

## 3. Canonical success stories

The full acceptance text lives in [`../Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md). Use these IDs in every CON-READY handoff, review, and re-anchor.

| ID | User-visible success |
|---|---|
| `CR-U1` | Bring external Markdown into an existing or new world. |
| `CR-U2` | Read the imported source as a rich real document. |
| `CR-U3` | Get a useful semantic index of important people, threats, places, organizations, and relationships. |
| `CR-U4` | Recognize and cheaply correct meaningful extraction mistakes. |
| `CR-U5` | Follow a world object back to the relevant original source. |
| `CR-U6` | Hermes follows admitted provenance into source when graph detail is insufficient. |
| `CR-U7` | Hermes remains truthful about graph facts versus richer source detail. |
| `CR-U8` | Important NPCs are easy to find, open, understand, and query. |
| `CR-U9` | Important places and shops are easy to find and use, even when represented as documents. |
| `CR-U10` | Threats expose usable mechanics; external statblocks have a path toward exact accepted mechanics. |
| `CR-U11` | The GM can develop and persist the playable version without automatically rewriting graph canon. |
| `CR-U12` | Hermes can use deliberately saved playable material alongside world and source. |
| `CR-U13` | Expected combats can be prepared before the session. |
| `CR-U14` | Unexpected fights can be assembled quickly without JSON or memory reconstruction. |
| `CR-U15` | During play, DungeonBuddy is faster and safer than relying on memory/manual source search. |
| `CR-U16` | Hermes answers can navigate the GM to underlying NPC/location/threat/source/mechanics. |
| `CR-U17` | Reload/restart preserves the material and prep the GM depends on. |

A PR may advance several stories when they share one coherent invariant, but the PR must name the primary story or stories it makes observably more true.

---

## 4. Current repository anchor at workstream creation

At creation of CON-READY, PR #560 has merged.

The workstream therefore begins from a Build surface that already has:

- intentional durable Build source-document selection/creation;
- exact durable `documentId` work-object identity;
- Markdown Canvas as authoring/CAS authority;
- revision-safe Build source rename;
- graph-reference insertion in Build;
- shared Surface Context scaffolding;
- app-level Hermes/AgentInteraction continuity scaffolding from earlier work.

Do not rebuild these capabilities.

The old DOGFOOD-POLISH backlog is historical input, not CON-READY authority. Reuse completed infrastructure where it helps the user stories; do not continue old sequencing merely because it exists.

### 4.1 Current Hermes boundary

At this anchor, Hermes has model-visible campaign tools for:

- bounded graph retrieval/expansion;
- reading source anchors admitted into the active graph retrieval session;
- exact Threat mechanics hydration through `uses_statblock` bindings;
- declaring conversation-only context where appropriate.

Hermes is intentionally forbidden from arbitrary Markdown, corpus, filesystem, web, or ambient-memory factual discovery inside the graph-agent path.

CON-READY should preserve that trust boundary.

The desired source extension is:

> **A graph-admitted source anchor may authorize bounded follow-through into the exact SourceArtifact behind that provenance.**

It is not:

> “Hermes may search every Markdown file on disk.”

### 4.2 Current extraction boundary

The existing bounded worldbuilding extraction profile already covers named actors/creatures, locations, organizations/groups/factions, source-backed relationships, and evidence refs.

It deliberately excludes many adventure-like categories such as items, clues, beats, events, and encounter jobs.

Do not assume CON-READY needs a broad `adventure_module_v0` before real dogfood proves that omission is blocking the GM workflow.

### 4.3 Current source/provenance boundary

Existing source artifacts and anchors already retain exact provenance/integrity information, including artifact identity, source URI, content digest, world/campaign scope where applicable, workspace document identity/revision, and bounded line/span evidence.

CON-READY should make that infrastructure useful in ordinary navigation and Hermes source follow-through rather than replacing it with a parallel source system.

### 4.4 Current mechanics boundary

Threat + Statblock is the most mature structured mechanics path.

The preferred normal form is:

```text
Threat
  ↓ uses_statblock / exact binding
immutable accepted StatblockRevision
```

Do not replace this with a combat-specific duplicate creature model.

External statblocks still need the smallest practical import/admission path; determining and implementing that path belongs to CON-READY when advancing `CR-U10`.

### 4.5 Current Combat boundary

Combat may proceed in parallel.

The existing Combat Roster is useful and server-backed, but the full Play/world-object combat roadmap is substantially larger than the convention requirement.

CON-READY must define and dogfood the smallest truthful handoff from prepared/known threats and mechanics into whatever Combat surface exists at convention time.

Do not block CON-READY on completion of the entire Play roadmap.

### 4.6 Current-state re-anchor — 2026-08-20 (post-C2S27)

Recorded by the PLAY-SURFACE handoff
`Docs/Plans/HANDOFF-PLAY-SURFACE-c2s27-reanchor-and-workspace-cleanup.md`
under the operator-authorized documentation-only exception. Final dogfood
truth: `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`.

```text
main: 62f7f9e856327247b8677b4c951801e4c58a826c (merge of PR #622, D2 exact Runbook view)

merged and proven:
  P1/P2/P3A/D1/D2 — durable Runbook identity, exact Run binding + sealed manifest,
  native /play admission, Start Run, exact Runbook view, Runtime CAS progress

C2 Session 27 real-table dogfood (D3):
  verdict BLOCKED / PLAY NOT READY
  exact Run admission worked; the native Table was rejected as the table instrument;
  the HTML Combat Tracker carried the session

PR #623 (D4 current-Beat table stage):
  closed unmerged — evidence/mining only; Table implementation, hidden Scenes prose
  parsing, Combat localStorage changes, and bundled multi-capability code not merged
```

Currently false or fragile user stories (the highest-value falsehoods):

- **CR-U11** — Plan ideas did not enter Play with sufficient semantic fidelity; the Plan export dropped playable blocks and styling; prep does not survive worktree switches.
- **CR-U13 / CR-U14** — the Combat Tracker interaction proved out, but its state is browser-`localStorage`/export only; not durable.
- **CR-U15** — native Play was abandoned at the table; the Combat Tracker was materially more useful.
- **CR-U16** — statblock/roll-table opening remains a first-class, currently clunky-to-absent table need.
- **CR-U17** — reload/restart does not preserve the material and prep the GM depends on across browser/worktree boundaries.

Current delivery priority (details in `Docs/Roadmaps/ROADMAP-con-ready.md` §4.0):

```text
1. Lane A: active-Run continuity / Resume vs Start New
2. Lane B: durable Combat state / database-backed tracker authority
   (resolve the retained uncommitted Combat-save worktree first)
3. after both domain slices prove their own durability invariants, extract a
   bounded shared persistence primitive only if a common seam is evidenced
4. design task: Beat/Scene/Decision + Plan→Playable authoring model, including
   the P1/P2 structure, serialization, manifest, current-position, sealed-Run,
   and migration/rebase redesign
   (no native Play table implementation until that model is reviewed)
```

Lane A may re-anchor for dispatch. Lane B is blocked until the retained
`agent/play-command-board-disk-saves` worktree is mined/adopted/committed or
discarded because it contains uncommitted Combat durability work with no
remote backup. P3B (native graph-object sheets) and P4 (exact Threat→Combat)
remain designed but **deferred**; neither is current dispatch authority.

---

## 5. Roadmap slices

The canonical sequence is capability-oriented:

| Slice | Primary stories | Product outcome |
|---|---|---|
| `CR01` Source Ingress & Reading | U1–U2 | Paste/load Markdown into an existing/new world; reopen and read it richly. |
| `CR02` Source-Backed World Ingestion | U3–U5 | Extract enough durable world identity, review/correct it, and navigate object → source. |
| `CR03` Hermes Source Follow-Through | U6–U7 | Hermes can read farther into exact admitted source artifacts when graph detail is insufficient. |
| `CR04` Game-Facing Objects & Mechanics | U8–U10 | NPC/place/threat access is game-useful; statblocks have a practical exact-mechanics path. |
| `CR05` Playable Preparation | U11–U12 | GM prep decisions persist outside automatic graph canon and become usable context. |
| `CR06` Combat Readiness Integration | U13–U14 | Prepared and unexpected combat can reach the tracker quickly. |
| `CR07` Real One-Shot Run | U15–U17 + cumulative | Real convention material is prepared/run without manual repair paths. |

This order is not permission to chain-dispatch blindly. After every merge, re-evaluate current `main`, open PRs, user-story truth, and parallel work.

A later slice may begin early when it has no unsafe dependency and its parallel progress clearly reduces convention risk.

---

## 6. Dispatch rule: product story first

Every CON-READY implementation handoff must start with:

```text
Primary CON-READY user story/stories:
Current user-visible failure:
One independently useful outcome after this PR:
What remains false afterward:
Real one-shot dogfood proof:
```

Do not start with a schema or subsystem.

Bad mission:

> Add SourceArtifactSearchRequestV2 and projection adapter.

Good mission:

> When Hermes finds Hesta but the graph summary is insufficient, it can follow Hesta's admitted provenance and read more of that exact source document to answer the GM.

The implementation may require a SourceArtifact search/read contract, but that contract is not the product definition.

---

## 7. Architecture restraint rules

### 7.1 Do not widen ontology by default

Before adding a new graph node type or extraction category, ask:

> Can the GM already accomplish the task by navigating/querying the rich source document or Playable Layer?

If yes, ontology expansion is not automatically justified.

### 7.2 Do not invent a universal Adventure system

The one-shot acceptance scenario does not justify a universal adventure schema, scene engine, clue graph, or encounter ontology without concrete user-story evidence.

### 7.3 Do not make documents second-class

A rich Markdown document is a valid product representation for shops, prep, notes, handouts, and other material where special structure has not proved necessary.

### 7.4 Do not weaken Hermes source authority

Source follow-through must remain scoped to admitted artifacts/provenance. Never solve convenience by giving Hermes unrestricted local-file discovery.

### 7.5 Do not silently write creative prep into canon

Hermes may propose. The GM may keep a proposal in the Playable Layer. Promotion into durable world truth is a distinct governed action.

### 7.6 Do not duplicate mechanics authority

Combat, Plan, Build, and Hermes should consume the same exact accepted mechanics identity where available.

### 7.7 Do not require architecture completion for usability

If a bounded document- or adapter-based path makes the real GM story work truthfully, prefer it over waiting for a broader future framework.

---

## 8. Dogfood standard

Every substantial CON-READY slice ends with a real user-path dogfood scenario.

Use actual one-shot material whenever the capability is mature enough to do so.

Avoid fixtures specifically authored to make the implementation succeed.

The cumulative run should answer questions like:

- Can the GM import the material without repo surgery?
- Can the GM read it comfortably?
- Can the GM find Hesta?
- Can the GM open Hesta's source?
- Can Hermes answer a question requiring source detail beyond the node projection?
- Can the GM reach a statblock?
- Can a shop remain useful as a document?
- Can a new prep relationship persist without becoming automatic canon?
- Can an expected combat be prepared?
- Can an unexpected combat be assembled quickly?
- Can the app restart without losing the working state?

If the answer requires “the developer knows where the JSON/file is,” the story is not complete.

---

## 9. Explicit non-goals unless re-promoted by dogfood

Do not pull these into a slice merely because they are adjacent:

- direct PDF pipeline integration;
- arbitrary Hermes filesystem search;
- multimodal Hermes interpretation of imported images;
- perfect clue/beat/event/item extraction;
- universal Adventure ontology;
- full NPC/Shop ontology;
- autonomous graph publication from Hermes;
- automatic promotion from Playable Layer to canon;
- cross-surface Hermes thread perfection;
- full future Play/world-object roadmap completion;
- general asset-management platform;
- broad performance work without a measured live-use blocker.

If a dogfood failure makes one of these necessary, update the roadmap deliberately and record why.

---

## 10. Re-anchor protocol after every merge

The steward owns continuity.

After each CON-READY merge:

1. record the merged PR and exact merge SHA;
2. refresh current `main` and relevant open PRs;
3. mark which CR user stories materially advanced;
4. record the actual delivered behavior, not only the PR description;
5. record new dogfood findings;
6. identify which story is now the highest-value falsehood;
7. check for collision with the parallel Combat or other workstreams;
8. update this anchor only when the workstream's operating truth changed;
9. update the roadmap when product scope, success criteria, or sequencing changed;
10. dispatch only after reconciling the next slice against current repository reality.

Do not use stale chat summaries as the next agent's authority.

---

## 11. Stop conditions for implementation agents

An implementation agent must stop and return a reconnaissance/finding report rather than silently expand scope when:

- the requested story requires a new authority model not resolved by current decisions;
- a second independently useful durable contract appears inside the slice;
- the implementation would require unrestricted Hermes filesystem access;
- existing source provenance cannot identify the needed SourceArtifact reliably;
- a new-world path would require special-casing Eldyrwild semantics;
- external statblock import cannot map truthfully into the accepted mechanics model without a new contract decision;
- the Playable Layer cannot be implemented through existing documents/references without choosing a new durable authority;
- the parallel Combat work has changed the integration boundary materially;
- real dogfood disproves the assumptions used to select the slice.

The correct response to a stop condition is a precise handback, not speculative framework construction.

---

## 12. Source-of-truth reading order for future agents

At pickup, read in this order:

1. **This document** — operating mission and stewardship constraints.
2. [`../Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md) — canonical success stories and roadmap.
3. Current `main`, active CON-READY PRs, and immediately relevant code/contracts.
4. Relevant existing architecture only for the selected story. Common sources include:
   - `Docs/Design/DECISION-grounded-authored-world-object-lifecycle.md`;
   - `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`;
   - Hermes graph interaction/runtime contracts;
   - graph SourceArtifact/source-anchor contracts;
   - workspace document/Markdown Canvas authority;
   - current Threat/statblock authority;
   - Combat roadmap/implementation when working on U13/U14.
5. Historical DOGFOOD-POLISH handoffs only when they explain already-delivered behavior or a known finding.

Repository reality beats stale planning prose.

---

## 13. Steward pickup prompt

Use this as the default prompt for a fresh CON-READY steward:

```text
You own the CON-READY workstream for this slice.

Read Docs/Plans/STEWARDS-ANCHOR-con-ready.md and
Docs/Roadmaps/ROADMAP-con-ready.md first. Reconcile them against current main,
open CON-READY/adjacent PRs, and the owning contracts for the user story under
consideration.

CON-READY is a usability program. Success is defined by the CR-U user stories,
not architecture completion. Identify the highest-value user-visible falsehood,
decompose the smallest independently useful slice that makes it materially more
true, state what remains false, and write/execute/review against a real GM path.

Preserve these boundaries unless current repository authority or new dogfood
requires an explicit re-anchor:
- Markdown is the ingress boundary; PDF wiring is out of scope.
- Original source remains a rich first-class artifact.
- The World Graph may be intentionally lossy and points back to source.
- Hermes may follow admitted provenance into exact source artifacts, but may not
  gain arbitrary filesystem/corpus discovery.
- Playable GM decisions may persist without automatically becoming graph canon.
- Threat mechanics should reuse exact accepted statblock authority.
- Combat can progress in parallel; do not wait for the full future Play roadmap.
- Unexpected live-play variation is an acceptance case.

Before dispatch, name the primary CR-U story/stories, the current user-visible
failure, the one independently useful outcome, the remaining falsehood, and the
real one-shot dogfood proof.
```

---

## 14. Steward's final question

Before approving any CON-READY work, ask:

> **If this architecture vanished from the PR description and I only watched the GM use the product, what new thing could they reliably do?**

If the answer is unclear, the slice is not yet anchored strongly enough to CON-READY.