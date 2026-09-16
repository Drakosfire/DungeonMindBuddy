# HANDOFF — DOGFOOD-CONTINUITY: published-object addressability v1

**Created:** 2026-09-15  
**Activated:** 2026-09-16  
**Status:** ACTIVE — published-object addressability; #728 merged; serial implementation PR authorized  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Flow / owner:** `DOGFOOD-CONTINUITY / product loadability`  
**Direction:** DESIGN → CODE → REVIEW → TARGETED DOGFOOD  
**Design authority base:** `main@832b6347a08fab7355cae5b97890c0543eaa6d55`  
**Activation gate:** satisfied — #728 MERGED; `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md` is durable on `main`  
**Dispatch base:** `main@8b1e7ca37053a84095e3f94aa8c6b70db426fd0a` — activation commit; create the implementation branch from current `origin/main` at or after this SHA  
**Implementation branch after activation:** `dogfood-continuity/published-object-addressability-v1`, created from that exact `main`  
**PR topology:** `serial`  
**PR authorization:** open/update exactly one implementation PR for this addressability capability; no UI/Hermes/coverage successor PRs from the same worker  
**PR title:** `DOGFOOD-CONTINUITY: make published World objects round-trip through product reads`

**Activation facts:**

```text
predecessor #728 merge SHA:
982cfe04c6c976f9c9147ef48f3b7c29b4feec00
activation commit:
8b1e7ca37053a84095e3f94aa8c6b70db426fd0a
reviewed eval head:
ac18bfc59f9f2cfaf152116006a7923ff74353d9
formal review cycles on #728:
5 (Cycle 5 APPROVE 5227405549)
canonical report:
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md
canonical run:
gauntlet-compliant-stop-v1
dogfood_ready:
false
oracle:
not started (STOP before Q01)
Agent suite:
STOPPED (not scored)
C1S10 BENCHMARK_REVISION:
rev:6d15a3f9f7d2208d444df1097db0166a
terminal head:
rev:cce8d24621d65a018d3e2922552f56f2
Mireward loadability pin:
rev:24268294e868b30034e247aa9e23087b
Mireward candidate:
loc:mireward
Mireward published:
node:location:mireward
Mireward product:
product_unresolved
open implementation PRs at activation:
none
§4 collision:
none — KERNEL v0-2 lists world_graph_reads.py as not-expected; no open PRs
```

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Readiness doctrine: [`../Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md). Evaluation authority: [`../Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md`](../Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md).

> Activation does not change the mission, invariant, write lease, or Case A/B/C stop conditions. Exact IDs below replace the pre-merge operator summary. Create the implementation branch only from `main@8b1e7ca3…` or later `origin/main` containing this ACTIVE handoff. Do not open a second PR.

---

## §1 Mission and merge-ready invariant

**Mission:** make a governed, admitted DungeonMind World object that is exposed by publication/projection under durable identity X reliably openable as the same object through DungeonBuddy's normal product graph read contracts at the same World/campaign/revision.

**Merge-ready invariant:**

> For every representative admitted object exercised by this slice, any durable object ID exposed by the product projection/search boundary must round-trip without caller-side ID invention through exact-object, complete-object, neighborhood, and evidence reads in the same World/campaign/revision context. If an identity redirect/remap exists, it must be explicit, deterministic, durable, and consistently reflected by every read surface. A raw publication payload, admission package, or database record is not sufficient when normal product reads cannot resolve the object.

The first required real witness is the accepted-world Mireward failure from the question gauntlet:

```text
extract/admission identity observed: loc:mireward
published/remapped identity observed: node:location:mireward
ordinary product search/object/complete-object/evidence: unresolved/empty
```

Durable report IDs are recorded in Activation facts. If accepted-database inspection differs, repository/runtime evidence wins; record the exact observed identities before changing code.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | Yes. This slice is only durable published-object identity → normal product read round-trip. |
| Most likely false fix | Add a Buddy/UI alias that makes Mireward appear to open while raw DungeonMind publication/retrieval still disagrees about the durable identity. |
| Will §7 detect that? | Yes. Evidence begins below Buddy at the native DungeonMind read service, then walks the same object through projection/search/object/complete-object/neighborhood/evidence. |
| Easiest boundary to under-test | Search can return an object/label while exact object lookup still requires a different ID. The test must round-trip the ID returned by search/projection. |
| Authorized topology | Serial. The current eval report lands first; this is one product-loadability repair. UI mounting and Hermes remain blocked successors. |
| Fact that forces stop/split | Native DungeonMind cannot round-trip the published object at the exact revision, or fixing the issue requires changing publication/write semantics rather than Buddy's read adaptation. |

---

## §2 Accepted evidence and current truth

The predecessor structural acceptance remains true:

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = PASS
accepted World = dogfood-current-corpus-acceptance-v1
accepted database = dmb_current_corpus_acceptance_v1
accepted terminal head = rev:cce8d24621d65a018d3e2922552f56f2
44 model calls / 45 graph writes / no structural STOP
```

That result does not imply dogfood readiness.

The accepted follow-on gauntlet is durable on `main` as `gauntlet-compliant-stop-v1`:

```text
dogfood_ready = false
loadability = product_unresolved
oracle answerable = not started (STOP before Q01)
Agent suite = STOPPED (not scored)
World head unchanged = true
```

A pre-fix walk that scored `oracle answerable = 4 / 16` exists only as superseded historical diagnostic evidence in that report. It is not the canonical score.

Relevant handback for this slice, with exact report identities:

```text
ingested_object_unreadable
  candidate = loc:mireward
  published = node:location:mireward
  loadability pin = rev:24268294e868b30034e247aa9e23087b
  search/object/complete-object/evidence = empty / found: false
  seed_status = product_unresolved
```

Other accepted handbacks remain **out of scope** here:

```text
hermes_cannot_answer
UI defaults to world eldyrwild
C1+C2 union/campaign mismatch
12 graph-coverage failures at C1S10
```

Do not bundle them into this PR.

---

## §3 Root-boundary localization is part of the implementation contract

Do not choose a fix before proving which authority boundary is broken.

Use the exact accepted database and exact revision(s) named by the merged gauntlet report. At minimum inspect the gauntlet's C1S10 benchmark revision; also check the accepted terminal head if useful to prove the defect is not historical-pin-specific.

For the representative object, capture the following ledger before editing code:

```text
candidate/extract id
sealed admission node_id_map entry, if present
accepted assertion subject id
published DungeonMind object id in exact revision payload
native DungeonMind projection object id
native DungeonMind search matched object id
native DungeonMind exact-object lookup result for that id
Buddy projection object id
Buddy search matched node id
Buddy exact-object lookup result
Buddy complete-object result
Buddy neighborhood result
Buddy evidence result
```

### Boundary decision

#### Case A — DungeonMind native reads round-trip; Buddy loses/remaps identity incorrectly

This is the intended Buddy-owned repair path.

Fix the smallest Buddy direct-read adaptation seam so the ID returned by projection/search is accepted by exact-object/complete-object/neighborhood/evidence without caller-side rewriting.

Proceed with this PR.

#### Case B — the exact published DungeonMind object appears in payload/projection but DungeonMind's own retrieval cannot open it by the published ID

STOP.

Produce a compact dependency handback with exact World/revision/object IDs and native DungeonMind request/results. Do **not** hide the dependency defect behind a Buddy alias table, prefix heuristic, duplicated object, or evaluator translation.

The steward must then design/route a DungeonMind-owned repair.

#### Case C — publication/admission itself wrote inconsistent identities

Examples:

```text
node_id_map says X
accepted existence assertion is written against Y
relationships/evidence are attached to Z
```

STOP.

This is a write/publication contract defect, not a read-adapter repair. Return the exact mismatch to the steward for a separate write-side handoff. Do not broaden this lease into extraction/admission/publication code.

---

## §4 Context and ownership

### Product read authority

DungeonBuddy's mounted World Graph read path is:

```text
/api/live/world-graph/**
  → apps/live_control_server/services/world_graph_retrieval.py
  → apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
  → DungeonMind VersionedUnionGraphSnapshotReader / WorldGraphRetrievalService
```

The direct-read adapter's standing invariant already says product reads consume one exact DungeonMind published revision and do not reconstruct/fallback to Buddy graph files.

That invariant remains unchanged.

### Identity authority

Do not invent a new display-ID vocabulary in this slice.

The durable identity must come from the accepted publication/identity authority. Buddy may adapt wire naming only when that adaptation is deterministic and round-trippable.

Existing examples in the repository use multiple historical/extractor-facing forms (`loc:…`, `location:…`, `node:…`). This slice is specifically intended to eliminate any path where one form is emitted as durable product identity while another undocumented form is required to read it.

### Runtime/state ownership

Use the already-created acceptance database read-only.

```text
World:     dogfood-current-corpus-acceptance-v1
Database:  dmb_current_corpus_acceptance_v1
Host:      loopback:54329
```

Capture head before and after targeted dogfood. It must remain unchanged.

No new 44-session extraction run is required for this slice.

---

## §5 Files in scope — prospective write lease

This table becomes an exclusive lease only when the steward changes `BLOCKED → ACTIVE`.

| Action | Path | Purpose |
|---|---|---|
| MODIFY if Case A | `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py` | repair the direct read identity round-trip at the Buddy adaptation boundary |
| CREATE | `tests/test_published_object_addressability.py` | focused cross-operation regression proving one emitted durable ID can be reused across product reads |
| CREATE | `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-published-object-addressability-v1.md` | boundary localization, exact accepted-world witness, evidence, and dogfood verdict |

### Bounded discovery exception

One additional **Buddy read-side** production path may be added only if the defect is proven Case A and the direct adapter delegates the relevant identity adaptation to that exact file.

Allowed roots:

```text
apps/live_control_server/services/
apps/live_control_server/models/
```

Maximum additional production paths: `1`.

Before editing it, record in the PR/report why `world_graph_reads.py` alone cannot own the fix.

### Explicitly out of scope

```text
src/graph_memory/extraction/**
src/graph_memory/extract_identity_gate.py
src/graph_memory/candidate_graph_to_contribution.py
apps/live_control_server/services/candidate_graph_admission.py
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
DungeonMind dependency pin/version
apps/live-control-ui/**
Hermes / Agent runtime or prompts
MODEL_POLICY.json / model selection
benchmark gold
corpus source files
accepted database mutation
```

If one of these must change, STOP and hand back.

---

## §6 Implementation contract

```text
Input:
  one exact World/campaign/revision context
  one durable product-visible object identity X

Output:
  the same X is a valid handle across the normal product read family,
  or the response explicitly resolves X through one durable redirect to Y
  and all read operations report/consume Y consistently

Invariant:
  product-visible published identity is round-trippable

Failure behavior:
  true object miss → truthful empty/missing result
  stale/unknown revision → existing fail-closed error
  wrong campaign/admissibility → existing fail-closed scope behavior
  identity ambiguity/collision → no heuristic guessing
  dependency cannot resolve its own published id → STOP Case B

Replay/idempotency:
  repeated reads against same immutable revision → same resolved identity/result
  no read mutates World or identity ledger
```

### Round-trip matrix

| Operation | Input identity | Required result |
|---|---|---|
| projection | exact context | exposes canonical/readable durable ID `X` |
| search | query or seed | matched ID is `X` (or same explicit canonical redirect target) |
| object | `X` | `outcome != empty`, `resolved_node_id == X` or explicit canonical target |
| complete-object | `X` | `found=true`, same resolved identity |
| neighborhood | seed `X` | X is not reported missing; related data remains same revision |
| evidence(node) | target `X` | node is not treated as nonexistent; admitted anchors/evidence returned when present |

A caller must not need to know that `loc:mireward` should secretly become `node:location:mireward`, `location:mireward`, or vice versa. If such a redirect is authoritative, the product contract must own it explicitly.

---

## §7 Evidence required to merge

### 7.1 Zero-mutation accepted-world witness

Before code change:

```text
record accepted terminal head
record C1S10 benchmark revision
record exact Mireward identity ledger across publication/native reads/Buddy reads
classify Case A/B/C
```

After code change (Case A only):

```text
same database
same immutable benchmark revision
same immutable terminal head
same published object
normal product reads now round-trip
head before == head after
```

### 7.2 Focused deterministic regression

The regression must prove behavior, not just the literal string `Mireward`.

At minimum:

1. construct/fixture a published object with the same identity shape/remap class as the real witness;
2. obtain its ID from projection or search;
3. pass that exact returned ID unchanged into object lookup;
4. pass it unchanged into complete-object;
5. seed neighborhood with it;
6. target node evidence with it;
7. assert every response binds the same revision and resolved identity;
8. assert an actually unknown ID remains a truthful miss rather than being prefix-guessed.

### 7.3 Real targeted operator dogfood

Using the normal product API/surface against the accepted World:

```text
find/open Mireward
inspect complete object detail
follow at least one relationship if present
inspect evidence/source navigation if present
return/reopen the object using the ID emitted by the product
```

If the current UI cannot select the accepted World because of the separate default/mounting handback, direct normal product HTTP calls may serve as the targeted witness for this PR, but the report must keep `OPERATOR DOGFOOD = NOT_READY` and explicitly name the UI blocker. Do not relabel this slice as full dogfood readiness.

### 7.4 No full semantic/Agent gauntlet as an implementation debugging loop

Do not spend 16 Agent calls while this PR is still trying to make one object readable.

After merge and state sync, the steward decides whether to:

```text
repair operator World/campaign mounting next
or
rerun the full gauntlet if normal operator mounting is already sufficient
```

Hermes tuning remains blocked until product loadability and the relevant operator path are green.

---

## §8 Review questions

Formal review must answer:

1. Is the repair at the earliest proven failing boundary?
2. Does projection/search emit an ID that exact-object can consume unchanged?
3. Does complete-object agree with exact-object?
4. Do neighborhood/evidence use the same identity rather than a second translation?
5. Is any identity redirect durable/authoritative rather than a Buddy heuristic?
6. Does an unknown ID still fail honestly?
7. Did the change leave the accepted World and revision head untouched?
8. Did the PR avoid UI/Hermes/coverage fixes?
9. If native DungeonMind was the failing boundary, did the worker STOP instead of masking it?

A passing unit suite without the real accepted-world witness is insufficient.

---

## §9 Stop conditions

STOP immediately if:

- the merged gauntlet report is not on `main` at activation time;
- the exact accepted-world Mireward failure cannot be reproduced and the report does not explain why;
- raw DungeonMind retrieval cannot open its own published object identity (Case B);
- accepted publication/admission identity is internally inconsistent (Case C);
- the fix needs write/admission/extraction code;
- the fix needs a new cross-layer alias registry or ontology decision;
- the accepted World would need mutation/republication to make the test pass;
- the worker needs to change UI/Hermes/model policy/corpus;
- a second implementation PR appears necessary.

Return evidence to the steward instead of widening the branch.

---

## §10 Explicit successors — sequencing only, not authorized lanes

This handoff does **not** authorize these PRs. It records why they remain later:

### Successor candidate: operator World/campaign mounting

Current handback:

```text
UI default World = eldwyrwild/eldyrwild path rather than accepted dogfood World
C1+C2 union campaign selection/lens mismatch
```

Goal: a human can select/mount the accepted World and intended campaign lens through normal product affordances.

### Successor candidate: rerun accepted-world question gauntlet

After loadability + mounting are sufficient, rerun the same fixed Q01–Q16 benchmark rather than changing the questions.

Use the new result to choose between:

```text
remaining A/B/C/E → graph construction/retrieval/authority work
oracle-answerable D/F → Agent orchestration/synthesis work
```

### Successor candidate: Hermes oracle-gap repair

The first run showed four oracle-answerable questions with zero Hermes tool calls. That is valuable evidence, but do not tune Hermes until the graph path it is expected to use is product-loadable and operator-dogfoodable.

---

## §11 Completion rubric

This handoff is merge-ready only if, after activation:

- [x] merged gauntlet report is durable on `main`;
- [ ] exact accepted World/revision/head are re-anchored;
- [ ] pre-change Mireward identity/read ledger is captured;
- [ ] defect is classified Case A, B, or C;
- [ ] only Case A proceeds to Buddy code change;
- [ ] product-visible durable ID round-trips across projection/search/object/complete-object/neighborhood/evidence;
- [ ] unknown IDs still miss honestly;
- [ ] accepted World head is unchanged;
- [ ] focused deterministic regression passes;
- [ ] real accepted-world targeted dogfood passes for object opening/inspection;
- [ ] report states the remaining operator/UI and semantic/Agent gates truthfully;
- [ ] no second PR or successor lane is opened.

A successful merge establishes:

```text
PRODUCT OBJECT ADDRESSABILITY = PASS for the repaired contract/witness
```

It does **not** by itself establish:

```text
OPERATOR DOGFOOD = PASS
SEMANTIC COVERAGE = acceptable
AGENT ANSWERABILITY = acceptable
DOGFOOD_READY = true
SEMANTIC MODEL SELECTION = PASS
```

Those claims remain gated by `Docs/Design/ACCEPTANCE-dogfood-readiness.md`.