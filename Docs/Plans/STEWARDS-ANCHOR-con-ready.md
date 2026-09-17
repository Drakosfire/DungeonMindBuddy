# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT
**Line of work:** `CON-READY / DOGFOOD-CONTINUITY`
**Updated:** 2026-09-17
**Repository:** `Drakosfire/DungeonMindBuddy`
**Re-anchor base:** `main@ec286369409bc7b0f86cc1d1c5ff9a31bdd8487d` — #730 merged; recap source-read continuity ACTIVE
**Structural current-corpus acceptance:** PASS
**Fresh governed recap source-provenance contract:** PASS — PR #729 merged `074d4f66f94d4b391a7aaf485b69030a20d576e4`
**Exact accepted-candidate replay:** PASS — PR #730 merged `ec286369409bc7b0f86cc1d1c5ff9a31bdd8487d`
**Product readiness:** NOT READY — ordinary recap source-read remains the Gate B STOP
**Active lane:** [`HANDOFF-DOGFOOD-CONTINUITY-recap-source-read-continuity-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-recap-source-read-continuity-v1.md) — ACTIVE; serial PR authorized
**Closed predecessor:** [`HANDOFF-DOGFOOD-CONTINUITY-current-corpus-candidate-replay-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-current-corpus-candidate-replay-v1.md) — MERGED #730; lease released
**Readiness doctrine:** [`../Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md)
**Benchmark authority:** [`../Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md`](../Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md)
**Campaign graph architecture:** [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
**Steward process:** [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md)

> This is the current sequencing authority. Repository truth supersedes chat summaries, branch-only reports, and stale current-state prose elsewhere.

---

## 0. Pickup rule

Every steward/worker begins with:

> **If the operator cannot dogfood the World through the normal product, it is not ready. Structural smoke does not override that.**

Read, in order:

1. `Docs/Design/ACCEPTANCE-dogfood-readiness.md`;
2. this anchor;
3. `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-recap-source-read-continuity-v1.md` for the ACTIVE lane;
4. `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-candidate-replay-v1.md` for the accepted #730 evaluation claim;
5. the accepted predecessor reports when historical evidence is needed.

Do not reopen #730. Do not open UI, Hermes, gauntlet, model-selection, backfill, or another graph-admission PR from this sequence.

---

## 1. Where we are in the journey

The CON-READY campaign-memory line has progressively removed upstream ambiguity.

### 1.1 Chronological graph writing works structurally

Historical current-corpus acceptance processed the frozen 44-session recap corpus in strict chronological order through source → extraction → Candidate Graph Admission → governed DungeonMind write with exact-head continuity.

Accepted witness:

```text
historical World:     dogfood-current-corpus-acceptance-v1
historical database:  dmb_current_corpus_acceptance_v1
manifest:             44 sessions
model calls:          44
graph writes:         45
terminal head:        rev:cce8d24621d65a018d3e2922552f56f2
STRUCTURAL ACCEPTANCE = PASS
```

That result never established product loadability or semantic quality.

### 1.2 Dogfood exposed a native provenance defect

The accepted-World question gauntlet stopped before Q01 because ordinary product use was not ready. Published-object addressability then localized the first graph-read failure below Buddy: objects existed in immutable revision payloads, but DungeonMind native scoped reads rejected recap-backed objects because their source artifacts/revisions were not durably admitted.

Canonical Case B conclusion:

```text
published object exists
native DungeonMind cannot open it
Buddy did not cause/remap the failure
Case B = TRUE → dependency handback
```

The historical World remains an immutable defect witness.

### 1.3 PR #729 repaired the fresh governed-write provenance contract

PR #729 merged as:

```text
merge: 074d4f66f94d4b391a7aaf485b69030a20d576e4
reviewed head: 5cc8a89ce67d2cc9abefe66c7f343f6dd3cb01c3
formal review: Cycle 4 APPROVE / 5230245572
```

It established for fresh recap writes:

```text
exact recap source pair prove/admit before confirmable prepare
confirm re-proves sealed source identity
recap provenance uses the shared session_recap contract
fresh published object survives native scoped projection/retrieval
```

Bounded claim:

```text
FRESH GOVERNED RECAP SOURCE PROVENANCE CONTRACT = PASS
```

It did not rewrite or repair the historical 44-session World.

### 1.4 PR #730 replayed the exact accepted candidates

PR #730 merged as:

```text
merge: ec286369409bc7b0f86cc1d1c5ff9a31bdd8487d
reviewed head: 634f8d4b0807058a8309d5b19978855b9c7d4cc5
formal review: Cycle 1 APPROVE (GitHub COMMENT fallback, self-review)
```

Accepted bounded evaluation claim:

```text
PRISTINE ACCEPTED-CANDIDATE REPLAY = PASS
model_calls = 0
genesis + 44 confirms = complete
terminal replay head = rev:aa435599cb957b666987503b7bef585c
C1 projection = 514 nodes
C2 projection = 527 nodes
GRAPH IDENTITY ROUND-TRIP = PASS on the replay witness
Mireward opens at new C2S22 revision
C1S10 replay pin exists and is an ancestor of terminal head
PRODUCT LOADABILITY = NOT_READY
OPERATOR DOGFOOD = NOT_MEASURED
```

The graph itself is no longer the active problem. The 1041/1041 emitted-ID sweep is accepted as diagnostic identity evidence from a pre-fail-closed smoke; the merge verdict rests on exact 44-candidate replay plus a truthful source-read STOP.

### 1.5 The remaining Gate B failure is source navigation

Ordinary recap source-read does not reopen the cited span.

Mireward witness:

```text
object: node:location:mireward
source domain: session_recap
source pair: admitted
can_open_source: true
ordinary source-read outcome: partial
diagnostic: unsupported_locator
verified digest: none
locator_identity: registered repo:// recap file URI
source_span_ref_id: empty
line span: represented only inside evidence_ref_id
```

The first owning boundary is the source locator/span contract used by ordinary Buddy source-read.

---

## 2. Current readiness labels

Accepted repository authority now supports:

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = PASS
FRESH GOVERNED RECAP SOURCE PROVENANCE CONTRACT = PASS
PRISTINE ACCEPTED-CANDIDATE REPLAY = PASS
GRAPH IDENTITY ROUND-TRIP = PASS on the replay witness
SOURCE NAVIGATION = NOT_READY
PRODUCT LOADABILITY = NOT_READY
OPERATOR DOGFOOD = NOT_MEASURED / NOT_READY for the workflow
SEMANTIC COVERAGE = NOT_MEASURED by the current formal gauntlet
AGENT ANSWERABILITY = NOT_MEASURED by the current formal gauntlet
SEMANTIC MODEL SELECTION = HOLD
```

Do not use the old pre-fix `4/16` oracle diagnostic as a current semantic score.

Product Gate B remains NOT_READY until ordinary source-read returns digest-verified source content for recap evidence.

---

## 3. Current sequencing

### Step 1 — question gauntlet

COMPLETE as an evaluation STOP. PR #728 merged. It established that dogfood readiness had to be repaired before semantic/Agent scoring.

### Step 2 — published-object addressability

CLOSED as Case B STOP / dependency handback. No Buddy alias or read-remap repair was authorized.

### Step 3 — recap source-provenance admission

COMPLETE. PR #729 merged. Fresh governed recap source provenance is accepted.

### Step 4 — exact current-corpus candidate replay

COMPLETE. PR #730 merged. Exact accepted-candidate replay is accepted. Product loadability remains NOT_READY at source-read.

### Step 5 — recap source-read continuity

ACTIVE:

`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-recap-source-read-continuity-v1.md`

Authorized implementation PR:

```text
DOGFOOD-CONTINUITY: make recap evidence source-readable
branch: dogfood-continuity/recap-source-read-continuity-v1
```

First worker action is localization across candidate → stored evidence → source-anchor → Buddy read. Do not parse `evidence_ref_id` as the production locator.

### Step 6 — after source-read continuity

Do not pre-decide the next repair. Re-run the bounded product-loadability witness first.

If graph reads + source-read are green, then test ordinary operator World/campaign mounting. Only after operator dogfoodability is sufficient should the 16-question C1S1–10 gauntlet run against the replay C1S10 historical revision pin.

Then repair failures at the earliest remaining boundary:

```text
A/B/C/E graph coverage / connectivity / retrieval / source authority
before
D/F Agent orchestration / synthesis
```

Hermes/model tuning remains downstream.

---

## 4. ACTIVE source-read invariant

The recap source-read continuity handoff owns one bounded invariant:

> **A provenance-valid recap evidence anchor emitted by normal graph retrieval must carry an explicit canonical locator/span identity sufficient for ordinary Buddy source-read to reopen and digest-verify the exact cited source bytes at the same World/campaign/revision, without reconstructing that span by parsing `evidence_ref_id`.**

The worker must localize where the canonical span identity disappears before editing:

```text
candidate/extraction evidence
→ governed recap evidence stamping
→ DungeonMind EvidenceRef / SourceAnchor metadata
→ Buddy source-anchor adaptation
→ source-read locator classification
→ digest-verified content read
```

Possible owning cases include:

```text
R1 write stamping drops source_span_ref_id / canonical locator
R2 DungeonMind publication or retrieval fails to preserve a supplied span
R3 Buddy anchor adaptation drops an otherwise preserved span
R4 source-read classifier fails to consume a valid preserved locator/span
R5 correct metadata still cannot be read without changing DungeonMind semantics → STOP dependency handback
```

The handoff explicitly forbids treating `evidence_ref_id` as a hidden second locator schema.

---

## 5. Forbidden shortcuts

Do not:

- parse line/span semantics out of `evidence_ref_id` as the production repair;
- special-case Mireward or one source-anchor id;
- weaken digest verification;
- treat `repo://` alone as enough to prove the cited span;
- fall back to arbitrary full-file content when the evidence claims a narrower span;
- rewrite the historical accepted World;
- regenerate candidates/models to fix source navigation;
- reopen graph identity/admission semantics unless localization proves the defect is there;
- modify UI/Hermes/Agent/benchmark gold in the source-read repair;
- open a second implementation PR while this serial lane is ACTIVE.

---

## 6. Immediate finish line

The next readiness milestone is not semantic QA yet. It is complete Gate B continuity:

```text
exact accepted candidate
→ provenance-correct governed publication
→ campaign projection
→ emitted durable id
→ exact-object / complete-object / neighborhood / evidence
→ source anchor
→ exact recap span read
→ digest verification against admitted source revision
```

When that chain works through the normal product path, proceed to operator mounting/dogfood. Semantic and Agent evaluation come after that.
