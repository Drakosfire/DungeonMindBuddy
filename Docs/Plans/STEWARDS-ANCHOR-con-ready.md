# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY / DOGFOOD-CONTINUITY`  
**Updated:** 2026-09-19  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Re-anchor input:** `main@026fd546cb564f3262dbbe6aaf94fc1cee6df84a` — V2-1 dispatch base; rebased onto `main@bdcabc513b7cb7f68aa5198c4932d92815fbf871` after #737  
**Current product frontier:** **Authoring v2 → derived gold → extraction ablation**  
**Active implementation PR:** **[#738](https://github.com/Drakosfire/DungeonMindBuddy/pull/738)** — `con-ready/v2-1-published-recap-local-proposal-v1`; serial CON-READY PR; review cycle 1 repairs awaiting re-review  
**Current sequencing authority:** [`PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`](PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md)  
**Completed V2-0 census:** [`../Reports/REPORT-CON-READY-authoring-v2-current-contract-census-v1.md`](../Reports/REPORT-CON-READY-authoring-v2-current-contract-census-v1.md)  
**ACTIVE V2-1 handoff:** [`HANDOFF-CON-READY-authoring-v2-published-recap-local-proposal-v1.md`](HANDOFF-CON-READY-authoring-v2-published-recap-local-proposal-v1.md)  
**Historical authoring ancestry:** [`ROADMAP-graph-object-authoring-surface.md`](ROADMAP-graph-object-authoring-surface.md) + [`../Design/DESIGN-graph-object-authoring-surface.md`](../Design/DESIGN-graph-object-authoring-surface.md)  
**Completed UI series authority:** [`HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md)  
**Readiness doctrine:** [`../Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md)

> Repository truth supersedes chat reconstruction. The current instruction is: **design the manual Authoring v2 loop before running the next extraction/model experiment.**

---

## 0. Pickup rule

Read, in order:

1. this anchor;
2. `Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`;
3. `Docs/Reports/REPORT-CON-READY-authoring-v2-current-contract-census-v1.md`;
4. `Docs/Plans/HANDOFF-CON-READY-authoring-v2-published-recap-local-proposal-v1.md`;
5. historical authoring ancestry only when needed to understand surviving implementation seams;
6. `Docs/Design/ARCHITECTURE-campaign-supergraph.md` when checking durable World authority.

The V2-1 handoff is **ACTIVE**. Its §4 paths are the current CON-READY implementation write lease. Implementation is [#738](https://github.com/Drakosfire/DungeonMindBuddy/pull/738) on `con-ready/v2-1-published-recap-local-proposal-v1` from dispatch base `026fd546cb564f3262dbbe6aaf94fc1cee6df84a`, rebased onto `main@bdcabc513b7cb7f68aa5198c4932d92815fbf871` after E5D #737 merged.

The next steward action is to re-review #738 after review-cycle-1 repairs (atomic recap/authoring scope + recap-contextualized manual/relationship proposals). Operator dogfood findings remain successor design evidence; the visible V2-1 authoring UI stays. V2-2 remains false.

---

## 1. What has been completed

### Campaign-memory substrate

```text
44-session structural current-corpus admission              PASS
candidate admission / governed write continuity             PASS
recap source provenance + source-read continuity            PASS
exact accepted-candidate replay                             PASS
published-memory ordinary browse                            PASS
browse/write authority separation                           PASS
```

### UI / inspection series

```text
#700 / UI-01   shared Peek                                  MERGED
#701 / UI-02   truthful Agent presence                      MERGED
#702 / UI-03   responsive secondary context                 MERGED
#704           recap World-reference glance                 MERGED
#733 / UI-04   campaign-information glance + Peek           MERGED
#735 / UI-05   floating independent world-object inspector  MERGED
#734           unauthorized close-chrome attempt            CLOSED UNMERGED
```

UI-05 accepted implementation head:

`f69163a2f4bca22d00c432c6c6419cd1b024d44d`

UI-05 merge:

`586a3dcb53b481ef2cf21890872a3f1e8465a925`

Formal review:

`APPROVE` — `5251493236`

The UI series has produced a coherent-enough campaign-memory inspection grammar:

```text
campaign/session
→ recap
→ pill
→ glance
→ floating Peek inspector
→ relationships / source
→ close
→ same recap context
```

Stage 4 / recap WOW remains formally human-gated after UI-05, but **another UI implementation slice is not preselected**.

---

## 2. Why the frontier moved to authoring

Once the inspection path became usable, the dominant failures became semantic rather than structural:

- wrong object kinds;
- missing pills/references;
- thin objects;
- isolated nodes / missing relationships;
- plausible extraction that is not the human-intended durable interpretation.

The project now needs a way for the GM to express what the graph **should** know.

That human judgment should become both:

1. better actual campaign memory; and
2. better evaluation authority.

Therefore the sequence is:

```text
real campaign source
→ human source-grounded authoring / correction
→ governed World commit
→ derived gold from human adjudication
→ extraction/model ablation
→ improve extraction
→ repeat
```

Primary principle:

```text
authored campaign truth is the product
gold/eval is derived evidence
```

---

## 3. Current Authoring v2 sequence

Authority:

`Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`

### V2-0 — COMPLETE / PASS

The current-contract census is recorded in:

`Docs/Reports/REPORT-CON-READY-authoring-v2-current-contract-census-v1.md`

It found the surviving governed World-write seam:

```text
POST /api/live/graph-authoring/prepare
→ POST /api/live/graph-authoring/commit
→ DungeonMind immutable World revision
```

It also proved that ordinary published-memory browse must remain non-write authority and that its current recap projection has no canonical evidence-span binding.

### V2-1 — ACTIVE

Authority:

`Docs/Plans/HANDOFF-CON-READY-authoring-v2-published-recap-local-proposal-v1.md`

```text
published Campaign + Focus-session recap
→ highlight source text OR start from existing pill
→ inspect exact source context
→ stage local object / link-existing / relationship proposal
→ review/remove staged proposal
→ continue reading
```

This slice is **local-only**. It must not call prepare/commit, quick-commit, merge materialization, or acquire `ExplicitAuthoringAuthority`.

Campaign/session switching must isolate staged proposals by scope and restore the correct scope's local drafts when revisited.

Negative/source-only, ambiguity, arbitrary claim editing, generalized correction schema, Agent assistance, and durable write remain later slices.

### V2-2 — NOT YET AUTHORIZED

```text
staged human proposal
→ prepare/diff
→ revision-bound confirm
→ governed World publication
→ new immutable World revision
→ ordinary recap/Peek reflects committed truth
```

No Buddy-only overlay as terminal World truth.

### V2-3 — NOT YET AUTHORIZED

Derive reproducible gold/eval from committed human adjudication:

- identity;
- classification;
- claims;
- relationships;
- grounding;
- negative/source-only judgments;
- ambiguity/human-review-required cases.

The GM must not re-enter the same judgment into fixture JSON.

### V2-4 — PARKED BEHIND GOLD

Run current extraction versus one bounded alternative—DeepSeek is a candidate, not preselected truth—against authored gold.

Evaluate more than graph density:

```text
node precision / recall
identity resolution
kind accuracy
claim coverage
edge precision / recall
predicate + direction
grounding correctness
unsupported assertion rate
source-only false positives
ambiguity handling
```

### V2-5 — PARKED BEHIND MANUAL LOOP

Agent-assisted `Assess World Graph`:

```text
highlight source
→ inspect existing World
→ Agent proposes smallest useful change
→ human edits/reviews
→ SAME governed commit path
```

The Agent gets no privileged write path.

---

## 4. What survives from the old authoring prototype

Keep as product/implementation evidence:

- Tiptap-backed source selection;
- manual object authoring;
- existing-object resolution;
- relationship staging;
- proposal/staging UX;
- prepare/review/confirm interaction;
- correction/merge lessons;
- event/audit concepts;
- source prose as the primary visual context.

Do **not** revive as current authority:

- Buddy-owned graph kernel/storage;
- file-backed authored overlay as terminal World truth;
- mutation of extracted run artifacts;
- gold fixture files as the primary write target;
- a second write protocol bypassing current governed DungeonMind publication.

Historical docs are ancestry. V2-0 decides what current contract replaces their old write assumptions.

---

## 5. Sequencing holds

Do **not** dispatch yet:

- DeepSeek extraction ablation;
- the fixed 16-question semantic gauntlet as automatic next work;
- predicate-family relationship rollup;
- 7A1 generic contextual Ask;
- Agent-authored graph changes;
- generalized graph editor;
- Play / Combat;
- another UI-polish series.

The semantic gauntlet remains useful later as an external regression set. It does not replace richer human-authored gold.

The post-UI-05 Stage 4 human witness may still be recorded independently. A serious UI regression may justify one bounded repair, but UI polish no longer owns the default sequence.

---

## 6. Current acceptance/status labels

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE             PASS
FRESH GOVERNED RECAP WRITE                       PASS
EXACT ACCEPTED-CANDIDATE REPLAY                  PASS
RECAP SOURCE-READ CONTINUITY                     PASS
PUBLISHED-MEMORY GRAPH REVIEW BROWSE AUTHORITY   PASS
GRAPH REVIEW BROWSE/WRITE AUTHORITY SEPARATION   PASS

UI-04 CAMPAIGN-INFORMATION GLANCE/PEEK           MERGED
UI-05 FLOATING WORLD-OBJECT PEEK                 PASS / MERGED

STAGE 4 / RECAP WOW                              HOLD — post-UI-05 human witness pending

AUTHORING V2                                     CURRENT IMPLEMENTATION FRONTIER
V2-0 CONTRACT CENSUS                             COMPLETE / PASS
V2-1 PUBLISHED-RECAP LOCAL PROPOSAL               ACTIVE — IMPLEMENTATION DISPATCHED
V2-2 GOVERNED WORLD COMMIT                       NOT AUTHORIZED
V2-3 DERIVED GOLD EXPORT                         NOT AUTHORIZED
V2-4 EXTRACTION/MODEL ABLATION                   PARKED BEHIND GOLD
V2-5 AGENT-ASSISTED ASSESSMENT                   PARKED BEHIND MANUAL LOOP

SEMANTIC COVERAGE                                NOT MEASURED
AGENT ANSWERABILITY                              NOT MEASURED
SEMANTIC MODEL SELECTION                         HOLD
```

---

## 7. Next steward transition

The design transition is complete:

```text
V2-0 current-contract census                    PASS
→ exact governed write boundary identified      PASS
→ bounded V2-1 handoff landed ACTIVE            PASS
→ one serial V2-1 implementation PR authorized  REVIEW CYCLE 1 — REPAIRS LANDED, AWAITING RE-REVIEW
```

Re-review #738 after the review-cycle-1 correctness repairs. Keep the visible authoring UI. Explore the HANDOFF operator dogfood findings during that review; do not fold Surface Context, Author Node, or merge into this PR. Do not dispatch V2-2, derived gold, extraction/model ablation, or Agent-assisted authoring until V2-1 merges and the workstream is re-anchored.
