# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY / DOGFOOD-CONTINUITY`  
**Updated:** 2026-09-16  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Re-anchor base:** `main@982cfe04c6c976f9c9147ef48f3b7c29b4feec00` — #728 gauntlet report merged; published-object addressability ACTIVE  
**Structural acceptance:** PASS — current-corpus 44-session governed-write continuity  
**Product readiness:** NOT READY — accepted-World dogfood failed loadability/operator/Agent gates  
**Current forcing function:** repair published-object addressability so admitted World objects round-trip through ordinary product reads  
**Completed evaluation:** [`HANDOFF-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md) — MERGED #728  
**Durable report:** [`../Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md`](../Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md)  
**Active implementation:** [`HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md)  
**Readiness doctrine:** [`../Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md)  
**Benchmark authority:** [`../Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md`](../Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md)  
**Campaign graph architecture:** [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Steward process:** [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md)  
**Product roadmap:** [`../Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md)

> This is the current sequencing authority. Repository truth supersedes old chat summaries and stale `CURRENT` prose elsewhere.

---

## 0. Pickup rule

Every fresh steward/worker must begin with this distinction:

> **If the operator cannot dogfood the World through the normal product, it is not ready. Structural smoke does not override that.**

Read, in order:

1. `Docs/Design/ACCEPTANCE-dogfood-readiness.md`;
2. this anchor;
3. `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md` for the durable NOT READY verdict;
4. `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md` for the active implementation lane.

Do not infer readiness from the structural acceptance report alone.

---

## 1. What is true

### 1.1 Structural current-corpus acceptance passed

The recovery/drain completed #722–#726 and one pristine full acceptance run on real integrated `main`.

Accepted structural witness:

```text
World:          dogfood-current-corpus-acceptance-v1
Database:       dmb_current_corpus_acceptance_v1
Terminal head:  rev:cce8d24621d65a018d3e2922552f56f2
Model calls:    44
Graph writes:   45
Structural STOP:null
```

This proves the production source → extraction → candidate integrity → Candidate Graph Admission → governed DungeonMind write → exact-head continuity chain can process the frozen current corpus.

It does **not** prove product loadability, semantic usefulness, Agent usefulness, or model selection.

### 1.2 The first accepted-World dogfood says NOT READY

Durable gauntlet authority is `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md` on `main@982cfe04…`, run `gauntlet-compliant-stop-v1`:

```text
dogfood_ready       = false
oracle answerable   = not started (STOP before Q01)
Agent suite         = STOPPED (not scored)
loadability         = product_unresolved
World head unchanged= true
```

A pre-fix `oracle answerable = 4 / 16` walk is retained in that report only as superseded historical diagnostic evidence. It is not the canonical score.

Accepted handbacks:

```text
ingested_object_unreadable
  candidate = loc:mireward
  published = node:location:mireward
  loadability pin = rev:24268294e868b30034e247aa9e23087b
  normal product search/object/complete-object/evidence cannot open it

hermes_cannot_answer
  Agent runtime unavailable: openai-api / gpt-5.6-luna / chat_completions 400
  suite STOPPED before Q01; not scored as D

operator mounting/context
  default UI World is not the accepted dogfood World
  C1+C2 union/campaign lens is not an ordinary clean operator path

graph coverage
  Q01–Q16 not started on the compliant run
```

Do not flatten these into one score. They belong to different ownership boundaries.

### 1.3 The readiness law is now durable

`Docs/Design/ACCEPTANCE-dogfood-readiness.md` defines the cumulative gate order:

```text
structural acceptance
→ product loadability/addressability
→ operator dogfoodability
→ semantic usefulness / oracle answerability
→ Agent usefulness
```

A lower-layer PASS cannot override a higher-layer failure.

---

## 2. Current sequencing

### Step 1 — evaluation lane: COMPLETE

PR #728 merged as `982cfe04c6c976f9c9147ef48f3b7c29b4feec00`. The durable report is on `main`. Verdict remains NOT READY. The eval PR did not patch production.

### Step 2 — published-object addressability: CURRENT / ACTIVE

`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md` is ACTIVE.

Dispatch base: `main@982cfe04c6c976f9c9147ef48f3b7c29b4feec00`.
Authorized branch: `dogfood-continuity/published-object-addressability-v1`.
Authorized PR title: `DOGFOOD-CONTINUITY: make published World objects round-trip through product reads`.

That slice owns only this invariant:

> A durable object identity exposed by accepted publication/projection/search must round-trip through ordinary product object/complete-object/neighborhood/evidence reads at the same World/campaign/revision.

The first real witness is Mireward (`loc:mireward` → `node:location:mireward`, product_unresolved).

### Step 3 — classify the owning boundary before fixing

The addressability handoff requires a three-way decision:

```text
A. DungeonMind native reads round-trip, Buddy adapter does not
   → Buddy read-side repair proceeds

B. DungeonMind native retrieval cannot open its own published ID
   → STOP; dependency handback; no Buddy alias shim

C. publication/admission itself wrote inconsistent IDs
   → STOP; write-side successor design; do not widen read repair
```

### Step 4 — only after addressability

Do not pre-dispatch these. They remain sequencing candidates:

```text
operator World/campaign mounting
→ rerun the same fixed question gauntlet
→ use remaining A/B/C/E failures for graph/retrieval work
→ use oracle-answerable D/F failures for Agent work
```

Hermes tuning is not the next action while the product cannot reliably open what publication says exists.

---

## 3. PR topology and lane law

Current open implementation PRs observed at this re-anchor: `none`.

Topology remains serial:

```text
question-gauntlet eval PR #728 MERGED
  → published-object-addressability PR (authorized, not yet opened)
  → merge + targeted dogfood + sync + re-anchor
  → choose exactly one next slice from observed evidence
```

Do not open UI/Hermes/coverage PRs from an addressability finding.

A new defect is evidence for the steward, not permission for worker fan-out.

---

## 4. Acceptance semantics to preserve

Use scoped labels:

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = PASS
PRODUCT LOADABILITY = NOT_READY
OPERATOR DOGFOOD = NOT_READY
SEMANTIC COVERAGE = not started (STOP before Q01); historical 4/16 is not canonical
AGENT ANSWERABILITY = STOPPED (not scored)
SEMANTIC MODEL SELECTION = HOLD
```

The accepted World is real and structurally coherent enough to have a revision lineage. It is not yet a World the product can honestly call ready.

Presence in any of these is insufficient by itself:

```text
candidate graph
admission package
published payload
PostgreSQL row
raw DungeonMind projection dump
Graph Review evidence list
```

For readiness, the ordinary product must be able to open and use the resulting object.

---

## 5. Forbidden shortcuts

Do not:

- rerun the 44-session paid extraction merely to repair a read identity issue;
- query PostgreSQL directly and call that dogfood;
- add evaluator-only or UI-only ID translations to hide a publication/read mismatch;
- use repository Markdown fallback to rescue graph coverage;
- tune Hermes before the graph path it must use is loadable;
- change benchmark questions/gold to fit current output;
- treat HTTP 200 + abstention + zero tools as successful Agent dogfood;
- call the World ready because structural acceptance passed;
- open a second repair/successor PR from the same lane.

---

## 6. Current finish line

The immediate finish line is **not** semantic model selection and not an Agent score.

It is:

```text
accepted publication says object X exists
→ normal product can find X
→ open X
→ inspect complete X
→ traverse X
→ inspect X evidence/source
→ same exact revision/authority throughout
```

Until that is true for the real accepted-world witness, CON-READY remains `NOT READY` at the World-memory dogfood boundary.
