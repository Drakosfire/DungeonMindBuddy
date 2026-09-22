# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY / DOGFOOD-CONTINUITY`  
**Updated:** 2026-09-22  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Current design PR:** #745 — `CON-READY: re-anchor source-to-World authoring`  
**PR #745 pre-sidequest reviewed head:** `b7e71379399905b7853d3ee67459511b2669b003`  
**Current product frontier:** **Authoring v2 PAUSED — World Keeper side quest**  
**Active DungeonBuddy implementation PR:** **NONE**  
**V2-3 derived gold:** **NOT AUTHORIZED**  
**Current pause authority:** [`HANDOFF-CON-READY-worldkeeper-sidequest-v1.md`](HANDOFF-CON-READY-worldkeeper-sidequest-v1.md)  
**Current interaction design:** [`../Design/DESIGN-source-to-world-authoring-interaction-contract.md`](../Design/DESIGN-source-to-world-authoring-interaction-contract.md)  
**Current sequencing authority:** [`PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`](PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md)  
**Parked migration evidence:** [`HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md`](HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md)  
**Durable World architecture:** [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)

> Repository truth supersedes chat reconstruction. The current instruction is:
> **do not grow DungeonBuddy's semantic write machinery. Bootstrap and review
> World Keeper, then return here for a fresh migration re-anchor.**

---

## 0. Mandatory pickup order

Read, in order:

1. this anchor;
2. `Docs/Plans/HANDOFF-CON-READY-worldkeeper-sidequest-v1.md`;
3. `Docs/Design/DESIGN-source-to-world-authoring-interaction-contract.md`;
4. `Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`;
5. the C1/S1 governed-authoring dogfood report;
6. `Docs/Plans/HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md`
   only as parked implementation/migration evidence;
7. `Docs/Design/ARCHITECTURE-campaign-supergraph.md` when checking durable
   World authority;
8. World Keeper's own steward/architecture docs once its sibling repository is
   initialized.

Do not dispatch from historical authoring handoffs.

No current Buddy implementation lease is open for this lane.

---

## 1. Where DungeonBuddy left off

The important completed sequence is:

```text
UI-01 shared Peek                              MERGED
UI-02 truthful Agent presence                  MERGED
UI-03 responsive secondary context             MERGED
UI-04 campaign-information glance + Peek       MERGED
UI-05 floating world-object Peek               MERGED — #735

V2-0 current authoring contract census         COMPLETE / PASS
V2-1 published-recap local proposal            MERGED — #738
V2-1A working projection / UI dogfood          MERGED — #741
V2-2 governed World commit                     MERGED — #742
DungeonMind party-registry provenance repair   MERGED — DungeonMind #73
C1/S1 governed authoring dogfood               COMPLETED
source-to-World interaction re-anchor          OPEN — #745
```

V2-2 proved a real durable write path:

```text
published campaign source
→ staged human proposal
→ prepare against exact governed World parent
→ explicit confirmation
→ one immutable DungeonMind child revision
→ durable created object identity
```

The C1/S1 dogfood then proved that this is not theoretical: a new authored
object was durably published to the Eldyrwild World.

The dogfood also showed that a successful write alone is not the product
"wow" moment.

---

## 2. What the dogfood exposed

The important product findings were:

1. **Publication does not naturally become inspection.** A published durable
   reference can still route back into Author Node resolution instead of opening
   exact World truth.
2. **Relationship authoring owns stale state incorrectly.** Opening the
   relationship flow can inherit the previously selected object.
3. **Working/post-publish presentation overclaims continuity.** A green receipt
   does not guarantee that the recap visibly reflects the new committed object.
4. **Same-batch object + relationship is falsely rejected.** Buddy's prepare
   classifier requires already-durable endpoint IDs even though the existing
   contribution translator already understands transaction-local object
   references.
5. **Duplicate guidance is useful but must not become identity authority.**
   "Similar object exists" must leave room for use-existing, create-distinct, or
   explicit identity reconciliation.

These are preserved requirements.

They are no longer automatic authorization to implement more semantic write
logic inside DungeonBuddy.

---

## 3. Why the project is taking the World Keeper side quest

The #745 design audit showed that the authoring architecture is healthier than
the authoring product. Its review then exposed another boundary problem:

DungeonBuddy still owns semantic responsibilities that exist mainly because it
was the migration host while DungeonMind became the durable authority.

Examples include:

- source-admission choreography;
- Graph Review write expressibility classification;
- transaction-local reference → prospective durable identity translation;
- DungeonMind contribution construction;
- exact-parent publication binding;
- governed publication/recovery orchestration;
- DungeonMind-specific read adapters spread through the product boundary.

If we continue building those responsibilities in Buddy, the product becomes
more tightly coupled to the knowledge kernel precisely when the architecture is
telling us to separate them.

World Keeper is the deliberate extraction boundary.

---

## 4. Target responsibility split

```text
DungeonBuddy
  product interaction
  campaign/source selection
  local/reversible authoring UX
  user / agent intent
  prepared-change presentation
  durable-result presentation

        ↓ application intent / queries

World Keeper
  semantic interpretation
  source/evidence interpretation
  transaction-local reference semantics
  governed transaction planning
  prepare/review/commit contract
  publication/recovery orchestration
  application-facing World read/query boundary

        ↓ governed durable semantics

DungeonMind
  durable World knowledge
  immutable revisions
  objects / relationships
  source/evidence provenance records
  identity ledger
  projection/retrieval
  governed publication
  persistence
```

Short form:

> **Buddy interacts. World Keeper interprets and coordinates. DungeonMind
> remembers and governs durable truth.**

A separate repository does not automatically require a network microservice.
The World Keeper bootstrap should first establish ownership and transport-neutral
contracts.

---

## 5. Safety guarantees that survive the move

Do not trade correctness for extraction cleanliness.

Preserve:

- immutable source identity and provenance;
- exact World revision/parent binding;
- prepare → explicit confirm;
- exact prepared interpretation cannot silently change before confirm;
- stale parent fails closed;
- idempotent recovery;
- one coherent atomic child;
- transaction-local references resolved as part of that coherent prepared
  change;
- no object-first / relationship-later repair publication;
- durable object identity distinct from source occurrence;
- duplicate advice distinct from identity authority;
- exact child read-back;
- refresh failure distinct from publication failure;
- no privileged Agent write path.

---

## 6. #745 review findings that must not be lost

Formal review `5279631534` held the first #745 head for four precision issues.

The current branch must preserve these corrections:

### A. Steward authority must tell one story

This anchor and its design-agent mirror are the mandatory pickup truth.

The old V2-2-active language is retired.

### B. Prepare-time exact interpretation is the safety model

Do not describe the system as:

```text
publish object
→ receive ID
→ rewrite relationship
```

The accepted current seam instead establishes prospective durable object
identity while translating the prepared transaction, resolves dependent
relationships into the same exact contribution, seals that interpretation, and
publishes it atomically.

World Keeper should preserve the semantic guarantee without exposing the
current Buddy/DungeonMind internal representation.

### C. Local proposal/reference IDs must be unique

Within one proposed transaction, local reference identity must be non-empty and
unique. A local endpoint must resolve to exactly one object operation.

Duplicate-key collapse is a correctness bug, not a UI inconvenience.

### D. Relationship result handle is not yet frozen

The exact durable relationship must be provable in the published child.

Whether a committed-change receipt returns a direct local-operation →
relationship-ID mapping is a World Keeper design question, not something to
invent inside Buddy during the pause.

---

## 7. Status of the transaction-semantics handoff

`HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md` is now:

```text
PARKED MIGRATION EVIDENCE
```

It still accurately identifies a current implementation mismatch:

`classify_graph_review_expressibility()` rejects transaction-local endpoints
that the downstream contribution translator already knows how to resolve.

Do not implement that handoff from this anchor.

After World Keeper design is accepted, a fresh Buddy re-anchor must choose:

- minimal temporary Buddy bridge;
- direct implementation/migration behind World Keeper;
- new design if the service boundary changes the underlying semantics.

---

## 8. Explicit holds

Do not dispatch while the World Keeper side quest is active:

- source-to-World transaction semantics as a Buddy implementation;
- inspection/publish-continuity implementation;
- broad Author Node/relationship IA rewrite;
- V2-3 derived gold;
- V2-4 extraction/model ablation;
- V2-5 Agent-assisted authoring;
- identity merge/reconciliation;
- generalized graph editor;
- another Buddy graph/knowledge authority.

A severe unrelated regression may still be repaired as a bounded defect. It
does not reopen this authoring lane.

---

## 9. What World Keeper must establish before return

At minimum:

- a README stating the project role;
- its own mandatory steward anchor;
- architecture authority;
- DungeonBuddy / World Keeper / DungeonMind responsibility boundary;
- governed World-change lifecycle;
- conceptual WorldChangeIntent contract;
- conceptual PreparedWorldChange contract;
- source/ancestry index;
- coarse implementation roadmap;
- an explicit decision on library/application-contract first versus immediate
  network-service deployment.

World Keeper must not recreate DungeonMind storage, revision, provenance, or
identity-ledger ownership.

---

## 10. DungeonBuddy resume gate

No CON-READY authoring implementation resumes until all are true:

1. World Keeper bootstrap/design is reviewed and accepted;
2. the three-project responsibility boundary is explicit;
3. the intent/prepared-change seam is coherent enough to identify the migration
   boundary;
4. current Buddy semantic-compiler responsibilities are classified as move,
   temporary bridge, or delete;
5. current DungeonBuddy `main` and open PRs are re-read;
6. #745/current interaction authority is reconciled with the accepted World
   Keeper design;
7. a **new** fresh-main DungeonBuddy handoff explicitly authorizes one bounded
   next implementation.

The old transaction handoff does not auto-reactivate.

---

## 11. Product goal on return

The side quest does not change the desired user experience.

We still want:

```text
read source
→ inspect governed World truth
→ author intended change
→ see reversible working interpretation
→ Publish…
→ review one exact governed change
→ Confirm
→ inspect exact durable result
→ query/use it from another surface
→ continue
```

The desired architectural change is:

> DungeonBuddy should no longer have to know how to compile that intent into
> DungeonMind's governed write machinery.

That responsibility belongs in World Keeper.

---

## 12. Current terminal state

```text
AUTHORING V2                         PAUSED
BUDDY AUTHORING IMPLEMENTATION       NONE AUTHORIZED
PR #745                              OPEN DESIGN RE-ANCHOR
WORLD KEEPER SIDE QUEST              ACTIVE
TRANSACTION-SEMANTICS HANDOFF        PARKED MIGRATION EVIDENCE
V2-3 DERIVED GOLD                    NOT AUTHORIZED
V2-4 MODEL ABLATION                  PARKED
V2-5 AGENT AUTHORING                 PARKED
```

The next substantive move in this lane is outside DungeonBuddy: establish
World Keeper's design authority, then return here deliberately.
