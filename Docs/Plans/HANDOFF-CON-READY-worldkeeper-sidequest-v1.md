# HANDOFF — CON-READY: World Keeper side quest / DungeonBuddy authoring pause

**Created:** 2026-09-22  
**Status:** ACTIVE PAUSE / CROSS-REPOSITORY DESIGN HANDOFF  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Current design PR:** #745 — `CON-READY: re-anchor source-to-World authoring`  
**Pre-sidequest reviewed head:** `b7e71379399905b7853d3ee67459511b2669b003`  
**World Keeper repository:** sibling project to be bootstrapped separately  
**Buddy implementation authorization:** **NONE**  
**V2-3:** **NOT AUTHORIZED**

## 1. Why DungeonBuddy is pausing here

The authoring work reached an important boundary.

V2-2 / PR #742 proved that DungeonBuddy can publish a source-grounded human
authoring proposal into one immutable DungeonMind World revision. The C1/S1
dogfood then proved that the write is real while also exposing that the
authoring product is not yet one coherent loop:

```text
read source
→ author
→ publish
→ exact changed World
→ inspect
→ extend
→ continue
```

PR #745 re-anchored the interaction model around that loop instead of the
current Author Node wizard rail.

During review of #745, a deeper ownership issue became clear: DungeonBuddy
still owns too much semantic write machinery. It currently knows how to
coordinate source admission, classify write expressibility, translate product
proposals into DungeonMind contribution semantics, resolve transaction-local
references to durable identities, bind exact parent state, and coordinate
governed publication/recovery.

Those mechanisms were necessary during the DungeonMind cutover. They are not
all permanent DungeonBuddy product responsibilities.

We are therefore taking a deliberate side quest before adding more authoring
behavior to Buddy.

The side quest is **World Keeper**.

## 2. Target three-project boundary

```text
DungeonBuddy
  product interaction
  campaign/source selection
  local authoring UX
  user / agent intent
  presentation of prepared changes and durable results

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
  graph objects and relationships
  source/evidence provenance records
  identity ledger
  projection/retrieval semantics
  governed publication
  persistence
```

Short form:

> **Buddy interacts. World Keeper interprets and coordinates. DungeonMind
> remembers and governs durable World truth.**

World Keeper is intended to turn source-grounded application intent into a
validated, reviewable World change, commit the confirmed interpretation through
DungeonMind, and expose the resulting World knowledge back to clients.

## 3. What remains DungeonBuddy's responsibility

DungeonBuddy continues to own:

- the campaign-facing UI and interaction grammar;
- source selection and recap/session context;
- text highlighting and source-occurrence interaction;
- local/reversible draft editing and working UX;
- explicit human actions such as Create object, Link occurrence, Add
  relationship, and later Correct identity;
- presenting duplicate/ambiguity guidance without silently deciding identity;
- presenting a prepared World change for review;
- collecting explicit confirmation;
- inspecting and using the returned durable result in Plan, Play, Build,
  Graph Review, and Agent surfaces;
- product-specific error/loading/offline UX.

The source-to-World interaction design remains valuable Buddy product
authority.

## 4. What DungeonBuddy should stop growing

Do not add new permanent Buddy ownership for:

- DungeonMind contribution construction;
- DungeonMind assertion/evidence representation;
- source-admission choreography as a product concern;
- semantic write expressibility classification;
- transaction-local → durable identity compilation;
- identity-ledger interpretation;
- exact-parent publication planning internals;
- publication/recovery machinery that exists only to coordinate DungeonMind;
- DungeonMind-specific read integration duplicated across product surfaces.

Current Buddy implementations of those responsibilities are **migration
evidence and temporary seams**, not automatically the long-term architecture.

## 5. What World Keeper is expected to own

World Keeper's emerging responsibility is:

```text
application intent
+ source grounding
+ exact governed World state
→ exact prepared interpretation
→ explicit confirmation binding
→ governed publication/recovery
→ durable result identity + read-back
```

Expected conceptual operations include:

- Create object;
- Reference existing object;
- Link a source occurrence to durable World identity;
- Create relationship;
- later: change/correct assertion;
- later: explicit identity reconciliation.

Not all operations are v0 requirements.

The important ownership boundary is that clients express **intent**, not
DungeonMind storage/write records.

## 6. Safety properties that must survive extraction

World Keeper is not an excuse to weaken any accepted correctness property.

Preserve:

- exact immutable source identity;
- exact World parent/revision binding;
- explicit prepare → confirm boundary;
- no reinterpretation between prepare and confirm;
- stale-parent failure closed;
- idempotent publication/recovery;
- atomic publication of one coherent child;
- transaction-local references resolved before durable publication;
- no partial object-then-edge repair sequence;
- durable identity distinct from source occurrence;
- duplicate guidance distinct from identity authority;
- exact child read-back;
- publication success remains success even if later refresh fails;
- no privileged Agent write route.

## 7. Transaction-local findings preserved from #745 review

The parked transaction-semantics work exposed two important invariants that
belong in the World Keeper design.

### Prepare-time prospective identity

The accepted current Buddy implementation already behaves conceptually as:

```text
transaction-local object
→ deterministic prospective durable object identity during prepare translation
→ dependent relationship resolves to that prospective identity
→ exact object + relationship contribution is sealed
→ confirm reconstructs/proves the same contribution
→ DungeonMind atomically publishes it
```

Do not redesign this into:

```text
publish object
→ receive durable ID
→ rewrite/publish relationship
```

The public World Keeper contract need not expose Buddy's current ID algorithm or
DungeonMind contribution schema. It must preserve the stronger semantic
guarantee: the prepared change already has an exact coherent interpretation.

### Local-reference uniqueness

Within one proposed transaction:

```text
every transaction-local operation/reference ID is non-empty and unique

a local object reference resolves to exactly one object operation
in that exact proposed transaction
```

Missing, duplicate, wrong-kind, or out-of-transaction references fail closed.

## 8. Relationship result handle remains open

DungeonMind has durable relationship identity, but the current Buddy Graph
Authoring receipt returns created object IDs rather than a frozen
local-relationship → durable-relationship mapping.

Do not invent that contract in Buddy while this side quest is active.

World Keeper design must decide whether exact relationship navigation is
returned directly in its committed-change receipt or derived through exact
child-revision read-back.

The current correctness requirement is only:

> the exact durable relationship exists in the published child and can be
> proven/read back.

## 9. Exact DungeonBuddy pause point

The relevant history is:

```text
V2-0 contract census                         COMPLETE / PASS
V2-1 published-recap local proposal          MERGED — PR #738
V2-1A working-projection dogfood             MERGED — PR #741
V2-2 governed World commit                   MERGED — PR #742
DungeonMind provenance repair                MERGED — DungeonMind #73
C1/S1 governed authoring dogfood             COMPLETED
source-to-World interaction re-anchor        OPEN — Buddy #745
transaction-semantics Buddy implementation   PARKED / DO NOT DISPATCH
V2-3 derived gold                            NOT AUTHORIZED
V2-4 extraction/model ablation               PARKED
V2-5 Agent-assisted authoring                PARKED
```

The C1/S1 dogfood proved a real durable publication and exposed the key product
gaps:

- publication result does not naturally transition into exact durable
  inspection;
- relationship authoring can inherit stale object state;
- working/post-publish recap presentation overclaims what changed;
- same-batch new-object + relationship intent is incorrectly rejected by the
  current Buddy classifier even though the contribution translator already
  understands transaction-local object references;
- duplicate detection is useful guidance but must not become automatic identity
  authority.

These findings are **preserved requirements**, not immediate authorization to
repair them inside Buddy.

## 10. Status of the old transaction-semantics handoff

`HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md` is now
**PARKED MIGRATION EVIDENCE**.

It identifies a real current Buddy defect and useful tests.

It does **not** authorize a Buddy implementation PR while the World Keeper
boundary is being established.

After World Keeper design is accepted, a fresh DungeonBuddy re-anchor must
decide whether:

1. the defect is fixed as a minimal temporary Buddy bridge before migration;
2. the capability moves directly into World Keeper and Buddy becomes its
   client; or
3. the migration sequence requires another bounded design.

No old handoff activates automatically.

## 11. V2-3 and later work remain held

Do not use this pause to jump around the authoring boundary.

Still unauthorized:

- V2-3 derived-gold export;
- extraction/model ablation;
- Agent-assisted graph authoring;
- identity merge/reconciliation UX;
- generalized graph editor work;
- broad authoring UI redesign;
- another graph authority inside Buddy.

The goal is to resume the same product mission with a cleaner ownership model,
not abandon the product loop.

## 12. World Keeper bootstrap expectations

The sibling World Keeper repository should first establish:

- README;
- mandatory steward anchor;
- architecture authority;
- DungeonBuddy / World Keeper / DungeonMind responsibility boundary;
- governed World-change lifecycle;
- conceptual WorldChangeIntent contract;
- conceptual PreparedWorldChange contract;
- source/ancestry index;
- coarse roadmap.

Implementation is not implied by repository creation.

The World Keeper design should remain transport-neutral initially. A separate
repository does not require an immediate network microservice. An in-process
reference implementation may be the safest first implementation.

## 13. DungeonBuddy resume gate

Do not resume CON-READY authoring implementation until all are true:

1. World Keeper bootstrap/design has been reviewed and accepted;
2. the Buddy/Keeper/Mind responsibility boundary is explicit;
3. the WorldChangeIntent and prepared-change concepts are coherent enough to
   identify the application/service seam;
4. the migration design identifies which current Buddy mechanisms move,
   which remain temporary, and which disappear;
5. current DungeonBuddy `main` and open PRs are re-read;
6. #745/current interaction authority is reconciled with the accepted World
   Keeper boundary;
7. one fresh Buddy handoff explicitly authorizes the next bounded implementation
   slice.

Resume does **not** mean automatically dispatching the parked transaction
handoff.

## 14. Pickup rule while the side quest is active

A fresh DungeonBuddy agent working in this area should read:

1. `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`;
2. this handoff;
3. `Docs/Design/DESIGN-source-to-world-authoring-interaction-contract.md`;
4. `Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`;
5. the C1/S1 governed-authoring dogfood report;
6. `HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md` only as
   parked implementation evidence;
7. `Docs/Design/ARCHITECTURE-campaign-supergraph.md` for durable World
   architecture;
8. World Keeper's own steward/architecture docs once that repository exists.

Repository truth supersedes chat reconstruction.

## 15. Desired return state

When the side quest returns to DungeonBuddy, the product goal is unchanged:

```text
read source
→ inspect governed World truth
→ author intended change
→ see reversible working interpretation
→ Publish…
→ review one exact governed change
→ Confirm
→ inspect exact durable result
→ query/use it elsewhere
→ continue
```

The architectural improvement is that DungeonBuddy should no longer have to
know how to compile that intent into DungeonMind's governed write machinery.

That work belongs in World Keeper.
