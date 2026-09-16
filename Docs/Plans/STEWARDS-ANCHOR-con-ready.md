# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY / DOGFOOD-CONTINUITY`  
**Updated:** 2026-09-16  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Re-anchor base:** `main@cf43ec97d6648667923c543e609dd4c27a6481fc` — parent of recap-provenance activation; pin the activation SHA after this transaction lands  
**Structural acceptance:** PASS — current-corpus 44-session governed-write continuity  
**Product readiness:** NOT READY — accepted World is structurally published but native scoped reads cannot admit ordinary recap-backed objects  
**Current forcing function:** make governed recap writes provenance-complete so a fresh published object survives native scoped projection and retrieval  
**Completed evaluation:** [`HANDOFF-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md) — MERGED #728  
**Durable gauntlet report:** [`../Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md`](../Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md)  
**Closed predecessor:** [`HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md) — STOP / dependency handback; Case B TRUE; no Buddy repair  
**Durable Case B report:** [`../Reports/REPORT-DOGFOOD-CONTINUITY-published-object-addressability-v1.md`](../Reports/REPORT-DOGFOOD-CONTINUITY-published-object-addressability-v1.md) — accepted evidence from `1a4588e7a853f811c15b213e4299866e3710281d`  
**Active implementation:** [`HANDOFF-DOGFOOD-CONTINUITY-recap-source-provenance-admission-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-recap-source-provenance-admission-v1.md) — ACTIVE; serial PR authorized  
**Readiness doctrine:** [`../Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md)  
**Benchmark authority:** [`../Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md`](../Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md)  
**Campaign graph architecture:** [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Steward process:** [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md)  
**Product roadmap:** [`../Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md)

> This is the current sequencing authority. Repository truth supersedes chat summaries, branch-only reports, and stale `CURRENT` prose elsewhere.

---

## 0. Pickup rule

Every fresh steward/worker begins with:

> **If the operator cannot dogfood the World through the normal product, it is not ready. Structural smoke does not override that.**

Read, in order:

1. `Docs/Design/ACCEPTANCE-dogfood-readiness.md`;
2. this anchor;
3. `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md`;
4. `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-published-object-addressability-v1.md`;
5. `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md` as the closed Case B predecessor;
6. `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-recap-source-provenance-admission-v1.md` for the **ACTIVE** implementation lane.

Do not reopen a Buddy addressability PR. Do not create a second provenance PR.

---

## 1. What is true

### 1.1 Structural current-corpus acceptance passed

Accepted structural witness:

```text
World:          dogfood-current-corpus-acceptance-v1
Database:       dmb_current_corpus_acceptance_v1
Terminal head:  rev:cce8d24621d65a018d3e2922552f56f2
Model calls:    44
Graph writes:   45
Structural STOP:null
```

This proves source → extraction → candidate integrity → Candidate Graph Admission → governed DungeonMind write → exact-head continuity processed the frozen 44-session corpus.

It does **not** prove source provenance completeness, product loadability, semantic usefulness, Agent usefulness, or model selection.

### 1.2 Accepted-World dogfood remains NOT READY

Canonical gauntlet run on `main` is `gauntlet-compliant-stop-v1`:

```text
dogfood_ready       = false
oracle answerable   = not started (STOP before Q01)
Agent suite         = STOPPED (not scored)
loadability         = product_unresolved
World head unchanged= true
```

A pre-fix `oracle answerable = 4 / 16` walk is retained only as superseded diagnostic evidence.

### 1.3 Addressability localized below Buddy

The published-object-addressability lane was required to classify the first owning boundary before editing Buddy reads. It is now closed. Its accepted report from `1a4588e7…`, now durable on `main`, establishes **Case B**:

```text
candidate/extract C2S22:       loc:mireward
published object:              node:location:mireward
existence subject:             node:location:mireward
published payload objects:     924
native scoped projection:      0 objects
Mireward native exact-object:  found=false / stored_provenance_invalid
Mireward source artifact row:  missing
World source_artifact rows:    1
payload evidence_refs:         399
scope_unknown exclusions:      918
in-scope provenance rejects:   6
Buddy read adapter mutation:   none
accepted World head mutation:  none
```

Boundary result:

```text
Case A — Buddy loses/remaps identity after native success
FALSE

Case B — published object exists but native DungeonMind cannot open it
TRUE → STOP

Case C — publication/admission identity split
NOT ESTABLISHED / not required to proceed
```

The durable Case B report records `effect.node_id_map` as absent from durable accepted-World stores; the C2S21 durable identity verdict agrees with `node:location:mireward`, while C2S22 `loc:mireward` has no sealed verdict. Do not turn that absence into a false Case C claim.

### 1.4 The likely next owning contract is systemic source provenance

The Case B counts make a one-object ID patch implausible: hundreds of payload objects/evidence refs coexist with effectively no usable source catalog for scoped native reads.

Existing repository architecture already defines the relevant source-authority law:

```text
_build_pair_to_dm = source revision identity derivation, not admission
publish_finalized_review = graph publication, not source insertion
confirmable governed writes require exact SourceArtifactV2 + SourceRevision
  prove/admit before confirmable prepare
confirm re-proves the sealed admitted pair
native projection fails closed on missing/mismatched provenance
```

The ACTIVE provenance slice applies that already-landed contract to governed recap candidate admission rather than inventing a new source store.

---

## 2. Current sequencing

### Step 1 — question gauntlet: COMPLETE

PR #728 merged as `982cfe04c6c976f9c9147ef48f3b7c29b4feec00`. Canonical verdict remains NOT READY. The Agent suite did not run because its readiness smoke failed.

### Step 2 — published-object addressability: CLOSED STOP / DEPENDENCY HANDBACK

Handoff:

`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md`

Durable accepted report:

```text
path:   Docs/Reports/REPORT-DOGFOOD-CONTINUITY-published-object-addressability-v1.md
from:   1a4588e7a853f811c15b213e4299866e3710281d
result: Case B TRUE → STOP
repair: no Buddy read-adapter change
lease:  released
```

Do not reopen a Buddy addressability implementation PR.

### Step 3 — recap source provenance admission: ACTIVE

Canonical implementation handoff:

`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-recap-source-provenance-admission-v1.md`

Activation gates 1–4 are satisfied. Topology is serial: exactly one implementation PR. Authorized branch `dogfood-continuity/recap-source-provenance-admission-v1`. Authorized title `DOGFOOD-CONTINUITY: make governed recap writes provenance-complete`.

Its single merge-ready invariant is:

> A governed recap candidate may become confirmable and publish only when every accepted assertion's exact source artifact/revision pair is admitted and snapshot-provable in DungeonMind, and its published evidence is compatible with that admitted source; the fresh published object must then survive native scoped projection and native retrieval at the same revision.

It must localize before editing:

```text
P1 source pair never admitted
P2 source pair admitted but evidence provenance incompatible
P3 both P1 + P2 are required by one provenance-complete invariant
P4 correct Buddy provenance still rejected by DungeonMind → STOP dependency handback
P5 only historical compatibility/backfill can repair old immutable World → STOP/split
```

Likely seams to prove, not assume:

```text
candidate_graph_admission confirmability
→ mounted WorldGraphSourceAdmissionAuthority
→ source pair snapshot proof
→ confirm-time re-proof
→ source-extraction EvidenceRef mapping
→ finalize/publish
→ native scoped projection/retrieval
```

### Step 4 — after provenance repair merge

The old accepted World is an immutable defect witness. The provenance PR must not rewrite it.

After merge + state sync + re-anchor, steward chooses exactly one separate acceptance action:

```text
A. replay durable frozen candidate/source artifacts into a pristine new World without model regeneration, if sufficient;
B. pristine current-corpus acceptance rerun through corrected production path;
C. separately designed historical provenance compatibility/backfill, only if preserving the exact old World is required.
```

Only after a normal product-loadable World exists should sequencing return to operator mounting → question gauntlet → graph/retrieval semantic failures → Agent usefulness.

---

## 3. PR topology and lane law

Current open implementation PRs observed at the provenance-design re-anchor: `none`.

Topology is serial:

```text
#728 gauntlet MERGED
  → published-object-addressability Case B STOP closed on main
  → recap-source-provenance-admission ACTIVE
  → exactly one provenance implementation PR
  → merge + state sync + re-anchor
  → exactly one separately designed acceptance/replay action
```

The ACTIVE provenance handoff leases the §5 paths. Do not open a second repair/successor PR from this sequence.

Do not open UI, Hermes, graph-coverage, Buddy addressability, accepted-world rebuild, or provenance-backfill work in parallel from this sequence.

---

## 4. Acceptance semantics to preserve

Use scoped labels:

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = PASS
GOVERNED RECAP SOURCE PROVENANCE = NOT ESTABLISHED for fresh writes
PRODUCT LOADABILITY = NOT_READY
OPERATOR DOGFOOD = NOT_READY
SEMANTIC COVERAGE = not started (STOP before Q01)
AGENT ANSWERABILITY = STOPPED (not scored)
SEMANTIC MODEL SELECTION = HOLD
```

A future provenance PR PASS may establish only:

```text
GOVERNED RECAP SOURCE PROVENANCE CONTRACT = PASS for fresh writes
```

It does not retroactively make the historical accepted World readable or ready.

---

## 5. Forbidden shortcuts

Do not:

- patch `loc:`/`node:` aliases in Buddy to hide a native provenance failure;
- mutate or republish an immutable accepted revision inside the provenance repair;
- insert source rows with direct SQL as the production mechanism;
- create a second source-artifact catalog;
- weaken DungeonMind provenance validation or add a generic “trust the artifact” waiver;
- globally relabel generic missing evidence as recap;
- rerun paid extraction merely to debug source persistence;
- tune Hermes before product loadability is restored;
- change benchmark gold/questions;
- treat raw payload presence or a PostgreSQL row as product dogfood;
- open a second repair/successor PR from the same lane.

---

## 6. Immediate finish line

The immediate finish line is not the old accepted World magically becoming healthy. It is a fresh governed recap write whose provenance contract is complete:

```text
verified recap bytes
→ exact source artifact + revision admitted in DungeonMind
→ confirmable candidate seals that admitted identity
→ confirm re-proves it
→ published evidence matches recap source provenance
→ native scoped projection admits the object
→ native search/object/neighborhood/evidence can open it
```

Then, and only then, run a separately authorized pristine acceptance/replay step to establish product loadability for campaign memory.
