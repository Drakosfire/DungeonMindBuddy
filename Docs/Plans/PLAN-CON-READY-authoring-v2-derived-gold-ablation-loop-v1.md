# PLAN — CON-READY: Authoring v2 → derived gold → extraction ablation loop

**Created:** 2026-09-18  
**Status:** ACTIVE SEQUENCING AUTHORITY — V2-0 complete; V2-1 merged; V2-1A merged; V2-2 ACTIVE  
**Canonical path:** `Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`  
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY / campaign memory authoring`  
**Re-anchor input:** `main@28754d1fdda15be97475f35e08127833b088a256` — V2-1A / PR #741 merged  
**Predecessor UI series:** UI-01 through UI-05 merged; Stage 4 WOW remains human-gated  
**Historical authoring ancestry:** `ROADMAP-graph-object-authoring-surface.md`, `DESIGN-graph-object-authoring-surface.md`, July authored-memory checkpoint  
**Current World authority:** DungeonMind-owned immutable World revisions / governed World publication  
**V2-0 census:** `Docs/Reports/REPORT-CON-READY-authoring-v2-current-contract-census-v1.md` — COMPLETE / PASS  
**Active implementation handoff:** `Docs/Plans/HANDOFF-CON-READY-authoring-v2-governed-world-commit-v1.md`

> The next useful loop is not “improve extraction, then hope the benchmark represents what we want.”  
> It is **human authoring → durable campaign truth → derived gold → extraction ablation → better extraction**.

---

## 1. Product decision

Authoring comes before the next extraction/model ablation.

The product should let the GM correct and enrich campaign memory while reviewing the actual source material. Those deliberate adjudications then become the strongest available evaluation signal for extraction.

The causal loop is:

```text
real recap / campaign source
→ human notices what the graph should have understood
→ author or correct that meaning explicitly
→ preserve exact evidence and authority
→ commit through governed World publication
→ derive evaluation gold from the authored judgment
→ run extraction/model ablations against that gold
→ inspect failure categories
→ improve extraction
→ repeat
```

### Primary principle

```text
authored campaign truth is the product
gold/eval is derived evidence
```

Do not rebuild a gold-first authoring workbench.

---

## 2. Why this is the current frontier

The campaign-memory substrate is now materially real:

```text
structural current-corpus admission                PASS
governed candidate admission/write                 PASS
recap source provenance/read continuity            PASS
published-memory ordinary browse                   PASS
browse/write authority separation                  PASS
UI-04 campaign-information glance + Peek           MERGED
UI-05 floating world-object Peek                   MERGED
```

The product can now expose semantic failures clearly enough for a GM to judge them:

- wrong object kinds such as creature/threat material appearing as `ITEM`;
- important mentions with no pill/reference;
- thin objects with insufficient claims;
- isolated nodes / missing relationships;
- plausible graph content that is simply the wrong durable interpretation.

That is exactly the point where manual adjudication becomes more valuable than another blind extraction experiment.

---

## 3. What survives from the old authoring work

The July Graph Object Authoring work is **prototype/implementation ancestry**, not current write authority.

Useful surviving product evidence includes:

- Tiptap-backed source selection;
- manual object authoring;
- existing-object resolution;
- relationship staging;
- local proposal/staging UX;
- prepare/confirm interaction shape;
- authored-memory event/audit concepts;
- correction / merge workflow lessons;
- the principle that source prose remains primary.

Current source still retains `GraphReviewAuthorDraftWorkspace` and related authoring UX. CUTOVER explicitly preserved the authoring workspace while retiring Buddy-owned graph storage.

### What is superseded

Do not revive as authority:

- file-backed authored graph overlays as durable World truth;
- Buddy-owned graph kernel/storage;
- gold fixture files as the primary write destination;
- direct mutation of extracted run artifacts;
- a second manual-write protocol that bypasses current DungeonMind World publication.

The v2 design must consume current governed authority rather than route around it.

---

## 4. Current authority model

```text
DungeonBuddy
  owns source-selection UX
  owns authoring interaction / local staging
  owns proposal/review presentation
  owns product-side exact source/work context

DungeonMind / governed World boundary
  owns World identity
  owns immutable World revisions + head
  owns admissibility / evidence rules
  owns durable World publication

GraphContribution / governed write path
  is current architectural ancestry for durable contributions
  must be censused before v2 implementation freezes exact port names

Agent
  is NOT the first author
  becomes an assistant after the manual loop is proven
```

### First design question

Before an implementation handoff lands, answer:

> **What exact current governed contract receives a human-authored node / claim / edge / correction proposal and turns it into a new World revision with source/evidence identity preserved?**

Do not assume the historical authored-overlay path is still valid.

Do not invent a new write seam if the current D.2C4/manual-authoring or GraphContribution authority already expresses the operation.

---

# 5. Target authoring interaction

The eventual manual interaction should begin from campaign material, not from an empty graph form.

```text
read recap / source
→ highlight text OR start from an existing graph pill
→ Author memory
→ inspect exact selected source context
→ choose intended meaning
→ stage proposal
→ inspect proposed graph effect + evidence
→ explicitly prepare / confirm
→ committed World revision
→ ordinary browse immediately reflects the result
```

The human must be able to express at least:

```text
LINK TO EXISTING OBJECT
CREATE OBJECT
ADD CLAIM / FACT
ADD RELATIONSHIP
CORRECT EXISTING INTERPRETATION
KEEP SOURCE-ONLY / NOT GRAPH-WORTHY
AMBIGUOUS / NEEDS REVIEW
```

That final pair matters. Good extraction gold includes deliberate negatives and ambiguity, not just “more graph.”

### Example

If extraction presents “hybrid monsters” as an item, the GM can adjudicate:

```text
selected evidence:
  exact recap span

human judgment:
  not an item
  creature/threat concept
  existing identity? <chosen / none>
  claims: <supported facts>
  relationships: <supported source/predicate/target>
```

The proposal is source-grounded human judgment. It is not a prompt to silently regenerate the whole recap.

---

# 6. Planned sequence

Each row is a separate steward slice unless implementation evidence proves two adjacent rows share one safe authority boundary.

## V2-0 — Current manual-authoring contract census — COMPLETE

**Type:** DESIGN / RECONNAISSANCE — COMPLETE  
**Implementation:** none

Census result:

```text
existing governed write seam:
  POST /api/live/graph-authoring/prepare
  → POST /api/live/graph-authoring/commit
  → DungeonMind immutable World revision

ordinary published browse:
  may stage source-contextualized local proposals
  may not acquire write authority in V2-1
```

The census found no missing backend World-write architecture blocking Authoring v2. It also confirmed that ordinary recap projection currently has no canonical evidence span binding, so V2-1 must preserve exact recap source identity without synthesizing `sourceSpanRefId`.

Inventory:

- surviving Graph Review authoring UX and tests;
- current explicit write authority gating;
- current DungeonMind `world_graph_writes` manual-authoring paths;
- GraphContribution source kinds / authored-by semantics;
- source admission requirements for a GM-authored correction;
- exact prepare/confirm/revision-drift behavior;
- how a human correction supersedes or corrects extracted assertions;
- how the committed revision becomes visible to ordinary published-memory browse.

**Exit:** one bounded implementation handoff for V2-1, with no legacy-overlay ambiguity.

---

## V2-1 — Source selection / pill → manual source-grounded proposal — COMPLETE / MERGED (PR #738)

**Goal:** acquire high-quality human judgment without writing yet.

**Active handoff:** `Docs/Plans/HANDOFF-CON-READY-authoring-v2-published-recap-local-proposal-v1.md`

The GM can:

- highlight source text or start from an existing graph reference;
- see exact selected text + surrounding/source identity;
- find/link an existing World object or propose a new one;
- stage currently expressible local object / link-existing / relationship intent;
- inspect the staged proposal;
- switch campaign/session without cross-scope proposal leakage.

Negative/source-only adjudication, ambiguity, arbitrary claim editing, and generalized correction schema remain later work. They are not to be encoded as fake object kinds or operator-note conventions in V2-1.

No model assistance required.

No durable World write required unless the current authority boundary naturally makes staging inseparable from prepare.

**Exit proof:** a real C1/C2 semantic defect can be represented accurately as a staged human proposal without editing fixture JSON or raw graph files.

---

## V2-1A — Working-projection UI dogfood — DONE / MERGED

**Goal:** make the published recap a continuous source-oriented authoring and inspection workspace.

**Result:** MERGED as PR #741 at `28754d1fdda15be97475f35e08127833b088a256`; accepted implementation head `9b5874e9b30663d4008427acebdff03d7c6531ae`; Review Cycle 3 PASS / MERGE-READY (`5262735475`).

**Completed handoff:** `Docs/Plans/HANDOFF-CON-READY-authoring-v2-working-projection-ui-dogfood-v1.md`

The GM can keep the recap visible while using Author Node, see local object/link adjudications immediately reflected as an uncommitted working projection, inspect truthful root prose, and expand one connected object without losing root context.

Canonical recap Markdown and durable World memory remain unchanged until an explicit governed publication step.

---

## V2-2 — Governed commit → immediately visible World memory — ACTIVE

**Goal:** the GM can teach the actual campaign memory from the published recap surface.

**Active handoff:** `Docs/Plans/HANDOFF-CON-READY-authoring-v2-governed-world-commit-v1.md`

Required:

```text
published recap
→ staged human proposal
→ explicit Review & publish
→ server-proven recap source identity
→ prepare/diff against current World parent
→ revision-bound confirm
→ governed DungeonMind World publication
→ new immutable World revision
→ durable created node ID(s)
→ same-scope recap refresh / exact read-back
```

Preserve:

- canonical recap bytes as read-only source;
- server-owned source authority rather than browser-supplied path/digest;
- explicit GM authorship / authority class;
- campaign/world/session scope;
- visibility;
- idempotency / stale-revision failure;
- auditability;
- current exact-run `sourceRunId` compatibility.

Published-recap authoring adds a mutually exclusive `recapArtifactId` source selector. The server resolves that selected recap record into the existing canonical recap SourceArtifact/source-admission path; it does not fabricate an extraction run.

A deliberate same-label **Create new** may publish a second distinct durable node. This slice does not add automatic merge, reconciliation, delete, or duplicate cleanup. Existing recap mention ambiguity must remain fail-safe rather than choosing an arbitrary identity.

Do not create a Buddy-only authored overlay as terminal truth.

**Exit proof:** publish one real new campaign object through the product, capture its immutable World revision and durable node ID, reload/read it through ordinary World-backed browse, and prove the disposable same-label duplicate/ambiguity case required for later ablation work.

---

## V2-3 — Derived gold from human-authored judgments

**Goal:** turn product corrections into evaluation authority without making evaluation the authoring destination.

A derived evaluation record should be able to express:

### Identity
- expected canonical object;
- new vs existing;
- aliases / identity equivalence.

### Classification
- kind / role / authority class.

### Claims
- facts expected on an object;
- temporal/epistemic scope when required.

### Relationships
- source;
- predicate;
- target;
- direction.

### Grounding
- exact supporting source/evidence span.

### Negative judgment
- source material that should **not** become durable graph memory;
- unsupported candidate that should be rejected.

### Ambiguity
- multiple defensible interpretations;
- intentionally unscored / human-review-required cases.

Gold export must be reproducible from committed human adjudications plus immutable source/World identities.

It must not require a second manual rewrite of the same judgment into fixture syntax.

**Exit proof:** export a small C1/C2 authored-gold cohort and independently trace every expected node/claim/edge/negative back to the exact human adjudication + source.

---

## V2-4 — Extraction / model ablation against authored gold

Only now promote the parked extraction experiment.

Compare current extraction and one bounded alternative (DeepSeek is a candidate, not preselected truth) against authored gold.

Useful dimensions include:

```text
node recall / precision
identity resolution
kind accuracy
claim coverage
edge recall / precision
predicate choice
direction
grounding correctness
unsupported assertion rate
source-only false-positive rate
ambiguity handling
```

Examples should include objects like Grobnok and isolated item/place/creature cases where current graph richness is visibly uneven.

Do not optimize for graph density.

Do not relax fail-closed evidence rules merely to improve recall.

---

## V2-5 — Agent-assisted assessment and proposal

Only after the manual proposal/review/write loop is trustworthy:

```text
highlight source
→ Assess World Graph
→ inspect existing matches
→ Agent proposes smallest useful node / claim / edge / correction
→ human edits/reviews
→ SAME governed proposal/commit path
```

The Agent gets no privileged write route.

This is where `DESIGN-magic-moment-contextual-source-to-world-graph.md` becomes an implementation target.

---

# 7. Relationship to the semantic gauntlet

The existing 16-question semantic gauntlet remains useful.

It is not the immediate product successor.

It can serve two later purposes:

1. a fixed regression set while authoring corrections accumulate;
2. an external check that improvements to extraction actually improve answerable campaign truth rather than merely matching authored fixtures.

Do not use the old gauntlet as a substitute for richer human-authored gold.

---

# 8. Relationship to Stage 4 / UI language

UI-01 through UI-05 have created a coherent-enough campaign-memory inspection grammar to support authoring work.

Stage 4 / recap WOW remains formally human-gated until the post-UI-05 operator witness is recorded.

That gate does **not** require another UI implementation slice before Authoring v2 design may proceed.

If post-UI-05 dogfood discovers a severe interaction regression, repair it as a bounded defect. Otherwise stop polishing the inspector and use it as the context surface for authoring.

---

# 9. Explicit non-goals

Do not dispatch from this plan:

- 7A1 generic contextual Ask;
- Agent-driven authoring before manual authoring is proven;
- DeepSeek ablation before derived gold exists;
- predicate-family relationship rollup merely to make thin edges look richer;
- a generalized graph editor;
- Buddy-owned World storage;
- file-backed authored overlay as terminal truth;
- gold-first manual fixture editing;
- automatic fuzzy identity merge;
- autonomous Agent commit;
- broad extraction prompt changes;
- Play/Combat work.

---

# 10. Current status / next steward action

```text
UI-01 shared Peek                              MERGED
UI-02 truthful Agent presence                  MERGED
UI-03 responsive secondary context             MERGED
UI-04 campaign-information glance + Peek       MERGED
UI-05 floating world-object Peek               MERGED (#735)

Stage 4 / recap WOW                            HOLD — post-UI-05 human witness pending

Authoring v2                                   CURRENT IMPLEMENTATION FRONTIER
V2-0 current manual-authoring contract census  COMPLETE / PASS
V2-1 published-recap local proposal             MERGED — PR #738
V2-1A working-projection UI dogfood             MERGED — PR #741
V2-2 governed World commit                      ACTIVE — current handoff
V2-3 derived gold export                        NOT YET AUTHORIZED
V2-4 extraction/model ablation                  PARKED BEHIND GOLD
V2-5 Agent-assisted assessment                  PARKED BEHIND MANUAL LOOP
```

Exactly one V2-2 implementation PR is authorized by the ACTIVE governed-World-commit handoff above. The plan does not authorize repair fan-out, V2-3 gold export, extraction/model ablation, Agent authoring, merge/reconciliation, or statblock successor PRs.

V2-1A / PR #741 predecessor state is synchronized here. V2-2 is the active frontier. After V2-2 merges and its exact live write/read-back witness is accepted, synchronize state authority again before authorizing V2-3.
