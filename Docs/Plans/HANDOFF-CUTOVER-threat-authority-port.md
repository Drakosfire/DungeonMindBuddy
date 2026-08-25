---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / D.2A Threat authority-port migration
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-threat-authority-port.md
  - Implementation repository: Drakosfire/DungeonMindBuddy
  - Predecessor: Buddy PR #634 / D.1 native governed writes

  Move the mounted Threat publication lifecycle off Buddy's World Graph runtime
  and behind one storage-neutral World Graph authority port. In dungeonmind
  authority mode, Threat operation head reads, create-new occupancy checks,
  proposal exact-parent preflight, publication, recovery, and verification must
  use DungeonMind-native authority without opening, mutating, replaying,
  rebuilding, or projecting through the Buddy graph kernel.

  The new port is intentionally middleware-ready: product services consume
  domain values and receipts, while the current production adapter owns
  DungeonMind/PostgreSQL details. DungeonBuddy-owned publication operation,
  identity, proposal, and commit state remains a separate persistence concern
  and is not migrated to PostgreSQL in this slice. The parallel APP-STATE lane
  owns that future Buddy persistence architecture and must not be absorbed here.
---

# HANDOFF — CUTOVER D.2A: Threat publication behind a World Graph authority port

**Created:** 2026-08-24  
**Status:** IMPLEMENTING — D.2A Threat authority-port migration; do not mark D.2A `DONE` until the implementation PR merges  
**Workstream:** CUTOVER / D.2 mounted legacy writer migration  
**Direction:** DESIGN → CODE → REVIEW  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Design authority base:** `31f2885cc18f96b98a1028304ae98914d1139fa3` (merge of Buddy PR #634)  
**Design PR base:** `5e596e1e90c156573da602f1f9591ee4828c3aee` (includes APP-STATE AS0 handoff)  
**#634 accepted head:** `aa4980a8cfd1dfedbb8b05d683f01cf27cfd0c3b`  
**#634 accepting review:** GitHub COMMENT `5013231548` (`Review Cycle 3 — APPROVED`)  
**DungeonMind pin:** `c5d3688587b0f5d506e0f7d64f33eb0628bac896`  
**Parallel architecture authority:** `Docs/Plans/HANDOFF-APP-STATE-application-state-architecture.md` (AS0; Buddy application-state persistence lane)  
**Suggested implementation branch:** `cutover/threat-authority-port`  
**Suggested PR title:** `CUTOVER: move Threat publication behind DungeonMind authority port`  
**Predecessor:** Buddy PR #634 — D.1 native governed write context / hydration retirement  
**Successors:** D.2B worldbuilding writer migration; D.2C first-world/bootstrap migration; D.3 final Buddy graph-engine deletion

> **Dispatch ruling:** D.1 proved that a mounted Buddy workflow can seal a
> public DungeonMind parent, publish a DungeonMind child, recover durably, and
> remain correct without hydrating Buddy's graph. D.2 must now remove the
> remaining mounted product writers from the Buddy graph runtime. Threat
> publication is the first bounded successor because its lifecycle is already
> explicit and well tested, but its operation, occupancy, proposal, commit,
> recovery, and verification seams still reach `graph_memory.kernel` and the
> filesystem World Graph. This slice migrates that complete authority boundary.
>
> It also establishes the application-facing seam that a future governed
> persistence middleware may wrap or implement. It does **not** design or build
> that broader middleware, and it does **not** move DungeonBuddy-owned state to
> PostgreSQL. The parallel APP-STATE AS0 authority independently assigns Buddy
> application state to Buddy-owned persistence and preserves DungeonMind as
> sole World Graph authority; D.2A composes with that boundary rather than
> competing with it.

---

## 1. Mission

Make this statement mechanically true:

> **When `DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind`, the complete mounted
> Threat publication lifecycle consumes World Graph authority only through a
> storage-neutral application port backed by DungeonMind. No mounted Threat
> operation opens, mutates, loads, rebuilds, replays, or verifies against
> Buddy's filesystem World Graph.**

The lifecycle in scope is broader than the final merge call:

```text
SBW09a publication operation
  current-head admission / refresh

SBW09b identity
  exact-parent projection
  create-new global node-id occupancy

SBW09c1 proposal
  exact-parent object/resource/binding preflight
  sealed contribution construction

SBW09c2b commit
  durable intent
  publication
  uncertain-outcome recovery
  exact-child verification
```

The identity candidate projection itself already routes through the current
production projection service and therefore reaches DungeonMind natively in
`dungeonmind` mode. Do not replace a working native projection merely to make
all reads look identical. The remaining direct Buddy graph dependencies around
that projection are in scope.

---

## 2. Why this slice establishes an authority port

D.1's native writer is intentionally concrete. It opens the pinned DungeonMind
PostgreSQL repository bundle inside the integration module and performs the
exact-run publication protocol there. That was the correct way to prove the
cutover invariant first.

Repeating the same repository orchestration directly inside Threat,
worldbuilding, first-world, Agent Surface, Play Surface, and future product
work would create a new form of coupling:

```text
product service
  → DungeonMind repository bundle
  → repository-specific records
  → PostgreSQL topology
```

Instead D.2A introduces one explicit application boundary:

```text
Threat product lifecycle
        ↓
WorldGraphAuthority port
        ↓
DungeonMindWorldGraphAuthorityAdapter
        ↓
DungeonMind application/repository contracts
        ↓
PostgreSQL
```

The port is not a new graph authority. It is a capability boundary around the
existing DungeonMind authority.

The implementation must preserve this ownership rule:

> **Buddy knows what the user is doing. DungeonMind knows what the world
> knows. PostgreSQL is durable infrastructure, not a reason to collapse those
> ownership domains.**

---

## 3. Relationship to the planned DungeonBuddy persistence middleware

A broader middleware may later govern DungeonBuddy's own PostgreSQL state.
This handoff deliberately prepares for that work without attempting it.

### 3.1 Two ownership domains remain separate

Future shape:

```text
                         shared DB/runtime infrastructure
                         /                         \
                        /                           \
        DungeonBuddy-owned state              World Graph authority
                 ↓                                      ↓
       DungeonBuddyStateStore                    WorldGraphAuthority
                 ↓                                      ↓
             PostgreSQL                              DungeonMind
                                                        ↓
                                                    PostgreSQL
```

They may eventually share connection infrastructure, tracing, health checks,
retry utilities, or deployment configuration. They do not share domain
semantics.

### 3.2 Buddy-owned Threat state stays Buddy-owned

The following remain DungeonBuddy product state in D.2A:

- publication operation ledgers;
- identity-resolution ledgers;
- proposal ledgers;
- commit/receipt ledgers;
- lifecycle locks;
- Threat draft state;
- accepted-mechanics state.

Their current filesystem stores may remain in this PR. Do not migrate them to
PostgreSQL merely because a future middleware is planned.

### 3.3 No cross-authority transaction

Do **not** create one database transaction spanning Buddy state and DungeonMind
World Graph publication.

Preserve the existing recovery-oriented shape:

```text
1. persist Buddy-owned publication intent
2. call World Graph authority with a stable idempotency key
3. receive or recover one durable authority publication
4. persist the Buddy-owned receipt / verification state
```

If step 4 fails after step 2 committed, the next attempt recovers from
DungeonMind authority before any second publication attempt. This is an
architectural invariant, not a temporary filesystem workaround.

### 3.4 Parallel APP-STATE lane is authoritative for Buddy persistence

The design PR base contains `HANDOFF-APP-STATE-application-state-architecture.md` (AS0).
That lane explicitly owns the future Buddy application-state substrate,
repository/transaction boundary, schema migration/deployment rules, and
application-state cutover/demolition rules. It also explicitly preserves
DungeonMind as World Graph authority and states that APP-STATE must not absorb
CUTOVER D.2/D.3 implementation.

Therefore:

- D.2A must not invent a competing `DungeonBuddyStateStore` architecture;
- D.2A must not depend on AS0/AS1 landing before the Threat authority cutover;
- APP-STATE must not become the implementation of World Graph publication;
- if both lanes later share low-level PostgreSQL runtime/configuration, that
  shared infrastructure is below two separate domain boundaries;
- edits to root DB config, dependency pins, server bootstrap, Docker/dev
  lifecycle, or central persistence authority docs are collision hotspots and
  must be serialized with the APP-STATE lane rather than casually co-edited.

The useful integration seam produced here is the **World Graph authority port**.
The useful seam produced by APP-STATE will be **Buddy application-state
persistence**. Keeping those names and responsibilities distinct is part of the
design.

---

## 4. Current mounted dependencies to remove

Repository inventory at design base `31f2885c…`:

### 4.1 SBW09a — publication operation

`apps/live_control_server/services/threat_publication_operations.py`

- imports `graph_memory.kernel`;
- `_read_graph_head(...)` calls `kernel.open_world_graph_head(...)` against
  `world_graph_root()`;
- begin/refresh therefore still uses Buddy's filesystem head as publication
  authority even though product reads have already cut over.

Required D.2A behavior: current-head admission/refresh reads the public
DungeonMind head through the authority port.

### 4.2 SBW09b — identity

`apps/live_control_server/services/threat_publication_identity.py`

- exact-parent candidate projection already goes through
  `services.world_graph_projection.project_world_graph`, which is native in
  DungeonMind authority mode;
- `_exact_revision_contains_node_id(...)` still calls
  `kernel.load_world_graph_revision_with_integrity(...)` against
  `world_graph_root()` for global create-new occupancy;
- the module still directly imports kernel and union-supergraph binding types.

Required D.2A behavior: retain the native candidate projection; move global
exact-revision occupancy to the authority port. Pure binding/model namespace
debt may remain only if it performs no graph-runtime work and is explicitly
owned by D.3.

### 4.3 SBW09c1 — proposal

`apps/live_control_server/services/threat_publication_proposals.py`

- `_load_exact_parent_store(...)` loads the Buddy revision store;
- exact-parent Threat/resource/binding compatibility preflight reads
  `UnionSupergraphNode` / `UnionSupergraphEdge` state;
- assertion construction calls Kernel builders;
- expected-contribution reconstruction still accepts a filesystem graph root.

Required D.2A behavior: exact-parent preflight consumes storage-neutral facts
from the authority port. Contribution/proposal construction may continue to use
Buddy-owned value contracts, but it must not require a graph store or filesystem
root in the DungeonMind path.

### 4.4 SBW09c2b — commit/recovery/verification

`apps/live_control_server/services/threat_publication_commits.py`

Current behavior still depends on Buddy graph APIs for:

- contribution source digest helpers;
- `merge_contribution_to_revision`;
- immutable operation/revision lookup;
- exact revision integrity load;
- replay-manifest/support verification;
- `rebuild_from_contributions` equivalence audit;
- revision-pinned Kernel projection;
- post-commit node/edge/binding verification.

Required D.2A behavior: publication and recovery use DungeonMind durable
publication state; verification uses DungeonMind-native publication and exact
child facts. Do not reconstruct a Buddy graph to preserve a historical audit
implementation.

---

## 5. The port contract

Create a Buddy-owned, storage-neutral application port. Preferred placement is
an application-facing package such as:

```text
apps/live_control_server/ports/world_graph_authority.py
```

The exact path may follow repository convention, but the port itself must **not**
live inside `integrations/dungeonmind`; otherwise callers will depend on the
adapter namespace instead of the capability.

A Python `Protocol` or equivalently narrow interface is appropriate.

The minimum capabilities required by this slice are conceptually:

```text
WorldGraphAuthority
  current_head(world_id)
  read_revision(world_id, revision_id)
  publish(request)
  recover(world_id, authority_operation_id)
```

Do not treat these names as mandatory spelling. The semantic contract is
mandatory.

### 5.1 `current_head`

Returns public authority head identity for one world.

Product callers receive domain values such as `world_id` / `revision_id`; they
do not receive a repository, connection, DSN, SQL row, or DungeonMind
infrastructure object.

### 5.2 `read_revision`

Returns an immutable, storage-neutral revision view sufficient for Threat
preflight and verification.

The view should expose only facts product logic actually consumes, for example:

```text
revision identity
objects by object id
  label / kind / role / aliases
  campaign scope / summary / source domains when supported
  external-resource payload when present
relationships by relationship id
  subject / target / predicate / direction
  source domains when supported
  Threat statblock binding payload when present
```

Do not return DungeonMind ORM/repository records or a raw PostgreSQL row map.
Do not recreate a `UnionSupergraphStore` under a new name.

If a field required by the current Threat preflight cannot be represented by
DungeonMind's supported contract, stop and identify the semantic gap. Do not
hydrate Buddy state to fill it.

### 5.3 `publish`

Publishes one exact governed contribution/effect against one exact expected
public parent and returns a durable authority receipt.

The request must carry, directly or transitively:

- world id;
- expected parent revision id;
- stable authority operation/idempotency id;
- the exact reviewed contribution/effect;
- the actor/principal required by the DungeonMind review contract;
- any sealed identity semantics required to make confirm deterministic.

The receipt must expose the durable facts needed by the product lifecycle,
including at least:

- world id;
- authority operation id;
- parent revision id;
- child/published revision id;
- reviewed contribution identity and/or immutable digest binding;
- accepted assertion identities or another exact durable equivalent.

Use DungeonMind's governed review/finalization/publication boundary. Do not
write DungeonMind tables directly from product code.

### 5.4 `recover`

Recovers terminal publication state by the exact authority operation/idempotency
id without re-running product reconstruction.

Threat's historical Kernel lookup was plural because immutable filesystem
revision manifests had to be searched. Do not simulate that implementation if
DungeonMind guarantees one finalized publication per operation id. Preserve the
observable safety algebra instead:

```text
none found                 → no terminal authority publication proven
exact terminal publication → recover that exact receipt
contradictory/ambiguous     → integrity failure; never choose one arbitrarily
```

---

## 6. Stable idempotency before mutation

Before calling `publish`, the product commit record must already contain a
stable authority operation/idempotency identity derived from sealed pre-write
authority.

It must:

- be deterministic for the claimed proposal/commit;
- remain identical across network/process/receipt-write retries;
- be persisted before the authority call;
- not depend on the resulting child revision;
- not be repinned when the graph head advances.

Reusing an existing sealed identity such as the expected contribution identity
is acceptable if the DungeonMind contract can bind it without ambiguity.
Introducing a separate deterministic `authority_operation_id` is also
acceptable. Whichever representation is chosen becomes part of the durable
commit/recovery contract and requires tests.

Do not use a random value minted after the mutation begins.

---

## 7. DungeonMind production adapter

Implement a production adapter such as:

```text
DungeonMindWorldGraphAuthorityAdapter
```

under `apps/live_control_server/integrations/dungeonmind/`.

It owns:

- authority database URL resolution;
- construction of the pinned DungeonMind repository/application services;
- mapping between Buddy product contribution/effect values and DungeonMind
  governed review/publication contracts;
- current-head and exact-revision reads;
- durable publication recovery;
- infrastructure exceptions → stable authority-port failures.

Product services must not import:

- `PostgresDatabase`;
- `PostgresRepositoryBundle`;
- DungeonMind repository implementations;
- a database URL in order to perform their domain logic.

Those details remain below the port.

### 7.1 Reuse D.1 implementation knowledge without coupling to Graph Review

`apps/live_control_server/integrations/dungeonmind/world_graph_writes.py`
already proves several hard behaviors:

- public parent validation;
- mutation-context adaptation;
- identity-ledger sealing;
- v2 candidate/review construction;
- finalized-review publication;
- durable publication recovery;
- post-publish child/head verification.

Prefer extracting or reusing genuinely product-neutral DungeonMind adapter
primitives from that implementation rather than independently inventing a
second publication protocol.

However:

- do not make Threat call the extract-promote-specific confirm endpoint merely
  to reuse code;
- do not change D.1's public behavior as incidental cleanup;
- if a shared helper cannot be extracted without materially changing the
  already-accepted Graph Review path, keep the D.1 path stable and document the
  exact consolidation debt for D.2B/D.3.

---

## 8. Threat product semantics that remain above the port

The authority port must not absorb product behavior merely because it touches
graph facts.

Threat services continue to own:

- publication operation lifecycle and source snapshot;
- identity candidate presentation and GM identity decision;
- create-new vs connect-existing product choice;
- statblock binding intent;
- proposal supersession rules;
- accepted assertion/effect construction;
- commit claim and retry presentation;
- user-facing result labels;
- committed / committed-unverified / verified product state;
- product-specific verification of the expected Threat/resource/binding effect.

The adapter owns durable graph authority mechanics, not Threat UX/business
workflow.

---

## 9. Native exact-parent preflight

The current preflight semantics must survive the storage migration.

At the exact sealed parent:

### create-new

Prove:

- the derived Threat object id is globally unoccupied;
- any pre-existing external-resource object with the deterministic id is
  semantically compatible;
- any pre-existing deterministic binding relationship is compatible;
- no conflicting `uses_statblock` relationship occupies the same semantic
  binding surface.

### connect-existing

Prove:

- the selected target exists at the sealed parent;
- it is a Threat under supported DungeonMind/Buddy wire semantics;
- its identity fields still match the snapshotted candidate to the extent those
  fields are part of the supported authority contract;
- external resource and binding compatibility checks above still hold.

The preflight must use the exact public parent, not current head after the fact.
The actual publish still performs expected-parent enforcement; preflight is not
a substitute for CAS.

---

## 10. Publication and recovery semantics

Preserve the existing at-most-once product guarantee while changing the
underlying authority proof.

### 10.1 Before mutation

- active proposal is exact and still claimable;
- predecessor operation and identity authority are still admissible under the
  existing Threat lifecycle rules;
- expected parent is exact;
- commit intent + authority idempotency identity are durable in Buddy state.

### 10.2 First authority call

Call the port once.

If it returns a committed receipt, persist the Buddy receipt and advance to
native verification.

### 10.3 Uncertain response

If the authority call throws or its response cannot prove whether publication
committed:

- do not immediately publish again;
- call `recover` with the durable authority operation id;
- one recovered terminal publication becomes the committed receipt;
- contradictory authority state is integrity failure;
- absence may permit only the existing bounded recovery policy, after all
  predecessor/head conditions required by that policy are revalidated.

### 10.4 Known committed publication

Once DungeonMind proves a terminal publication, no product-state write failure,
identity supersession, verification failure, or process restart may make the
operation publishable again.

This remains the central SBW09c2b invariant.

---

## 11. Replace Buddy-specific verification with native authority proofs

Do not port historical implementation checks mechanically.

The old verifier proves truth by loading the Buddy child store, inspecting its
replay manifest/support maps, rebuilding all contributions, and running the
Buddy Kernel projection. Those checks are valuable historical evidence but are
not the authoritative implementation after cutover.

For a DungeonMind child, verification should compose native durable proofs:

1. recovered/fresh publication receipt binds the exact authority operation,
   parent, child, reviewed contribution, and immutable contribution hash;
2. the reviewed contribution/effect corresponds to the sealed Threat proposal
   and exact accepted assertion identities;
3. an exact read of the published child shows the expected materialized
   Threat/resource/binding facts;
4. child parent identity equals the sealed expected parent;
5. mechanics payload remains outside World Graph authored facts except for the
   existing external-resource/binding contract;
6. create-new or connect-existing product constraints hold on the resulting
   child.

Do not require Buddy replay-manifest equivalence or construct a Buddy graph only
for verification.

If native authority is temporarily unavailable after a known commit, preserve
`committed_unverified` honesty and zero additional publication attempts.

---

## 12. Failure contract

The port should expose a small stable failure taxonomy. Exact class names are
implementation-owned; required distinctions are:

```text
authority unavailable
exact revision unavailable / unknown
integrity / contradictory authority state
stale expected parent
inexpressible/unsupported semantic mapping
publication failed before terminal proof
```

Threat services map those failures into existing product result labels where
semantically equivalent.

Do not leak raw psycopg, SQLAlchemy, repository, JSON-decoding, or DungeonMind
infrastructure exceptions through routes.

No failure may silently fall back to Buddy's World Graph.

---

## 13. Middleware-readiness requirements

This PR is considered middleware-ready only if all of these are true:

1. Mounted Threat services depend on the port, not DungeonMind repositories or
   PostgreSQL APIs.
2. Port inputs/outputs are storage-neutral domain values.
3. Database URL / repository construction exists only in the adapter/factory.
4. Product-state stores remain separately owned and can later be replaced
   without changing the World Graph port.
5. No API exposes a raw transaction/connection to callers.
6. Publication idempotency is explicit and durable.
7. Recovery can occur after loss of a product receipt without a second graph
   publication.
8. A future middleware can wrap or implement the same port without changing
   Threat service call sites.
9. The port does not import or depend on APP-STATE domain repositories; any
   future shared PostgreSQL runtime remains below both boundaries.

A generic `db.insert/update/query` wrapper does **not** satisfy this design.

---

## 14. Scope

### In scope

- introduce the storage-neutral World Graph authority port;
- add the DungeonMind production adapter/factory;
- move SBW09a current-head reads behind the port;
- move SBW09b global exact-parent create-new occupancy behind the port;
- move SBW09c1 exact-parent Threat/resource/binding preflight behind the port;
- remove filesystem graph-root requirements from DND proposal reconstruction;
- publish Threat contributions/effects through DungeonMind governed authority;
- recover uncertain/terminal Threat publication from DungeonMind durable state;
- replace Buddy child/rebuild/projection verification with native authority
  receipt + child-fact verification;
- preserve existing Threat routes/models/result semantics unless a change is
  strictly required by native authority;
- add unit/integration/static tests proving no mounted DND Threat path reaches
  the Buddy graph runtime;
- update CUTOVER tracker/roadmap + ACTIVE_AUTHORITY mirrors atomically in the
  implementation PR.

### Explicitly out of scope

- building the future DungeonBuddy persistence middleware;
- implementing APP-STATE AS0/AS1 contracts;
- moving Threat operation/identity/proposal/commit ledgers to PostgreSQL;
- moving ThreatDraft or accepted-mechanics state;
- one transaction spanning Buddy product state and DungeonMind;
- rewriting Threat publication UX;
- changing identity candidate policy;
- generic authored-object publication;
- migrating worldbuilding writes;
- migrating first-world/bootstrap writes;
- Agent Surface or Play Surface work;
- final deletion of all `graph_memory.kernel`, `world_supergraph`, or
  `union_supergraph` packages;
- live Eldyrwild mutation as part of implementation acceptance.

---

## 15. Retained paths and named deletion owners

| Path / concern | D.2A disposition | Remaining owner |
|---|---|---|
| D.1 exact-run Graph Review native writer | retain behavior; shared adapter internals may be extracted | D.2B/D.3 consolidation if still needed |
| Threat filesystem product ledgers | retain as Buddy-owned state | APP-STATE/future Buddy persistence migration |
| Threat native identity candidate projection | retain | normal product path |
| pure Threat/statblock binding contracts under `union_supergraph` namespace | may remain if runtime-free and relocation would widen slice | D.3 namespace demolition |
| file-mode/test-only graph adapters | may remain only when unmounted and named | D.3 |
| worldbuilding kernel writer | untouched | D.2B |
| first-world/bootstrap kernel writer | untouched | D.2C |
| historical correction/eval/scripts | untouched | D.3 or historical archive |
| hydration fail-closed stubs | untouched | D.3 |

If repository inventory proves another **mounted Threat publication** path still
opens or mutates Buddy's graph, it belongs in D.2A even if not named above.
If the discovered caller is a different product workflow, stop and assign it to
the appropriate successor instead of silently widening this PR.

---

## 16. Required tests

Exact filenames may follow current test ownership, but the PR must prove these
behaviors.

### 16.1 Port unit contract

With a fake authority implementation:

- Threat services receive only port domain values;
- current-head refresh maps exact head and typed failures correctly;
- exact revision preflight handles absent/present/conflicting objects and
  relationships;
- no raw repository/DB object is required by service tests.

### 16.2 Operation/head migration

- begin seals the DungeonMind public current head;
- refresh marks stale when DungeonMind head advances;
- Buddy filesystem head may be missing and cannot affect the result;
- authority unavailable fails closed.

### 16.3 Identity occupancy

Adversarial witness:

- a derived create-new id exists in the exact DungeonMind revision but is not
  visible in the campaign projection;
- candidate projection alone would not reveal it;
- port exact-revision occupancy refuses create-new correctly;
- no Buddy revision load is invoked.

### 16.4 Proposal preflight

Cover both create-new and connect-existing:

- compatible resource/binding reuse;
- conflicting resource;
- conflicting binding;
- missing connect-existing target;
- wrong target kind;
- changed snapshotted target identity;
- exact expected-parent semantics.

### 16.5 Native parent → child publication

Against an isolated PostgreSQL authority fixture:

```text
D_A = current DungeonMind head
prepare Threat proposal @ D_A
confirm
D_B = published DungeonMind child
D_B.parent == D_A
```

Assert the expected Threat/resource/binding effect and durable publication
receipt.

### 16.6 Exact retry

Repeat the identical confirm after the first successful publication:

- result is terminal/already committed under existing product semantics;
- same child `D_B`;
- same durable authority operation identity;
- zero second publication/finalization;
- product receipt facts remain exact.

### 16.7 Lost receipt / uncertain outcome

Inject failure after DungeonMind publication but before Buddy receipt save.
On the next call:

- durable Buddy intent is present;
- authority recovery finds the exact publication;
- no second publication occurs;
- product state advances to committed/verification state from recovered facts.

### 16.8 Stale parent

Advance DungeonMind head after prepare but before first publication:

- expected-parent publication fails closed;
- no hidden repin;
- no Buddy fallback;
- product state truthfully reports the existing stale/not-ready semantics.

### 16.9 Native verification

Prove verification succeeds from DungeonMind publication + exact child facts
with all of the following exploded if called:

- `open_world_graph_head`;
- `load_world_graph_revision_with_integrity`;
- `merge_contribution_to_revision`;
- `find_world_graph_revisions_by_operation_id`;
- `rebuild_from_contributions`;
- Buddy Kernel `project_world_graph`;
- hydration/replay helpers retired by D.1.

### 16.10 Physical-absence witness for mounted Threat lifecycle

Run the complete mounted Threat backend lifecycle with the Buddy World Graph
root absent/unusable.

At minimum:

```text
begin operation
prepare identity candidates
resolve identity
prepare proposal
confirm publication
read/retry terminal commit
```

The DungeonMind-backed path must succeed without constructing a Buddy graph.

### 16.11 Static dependency witness

For mounted Threat service modules, prove no direct runtime imports of:

```text
graph_memory.kernel
graph_memory.world_supergraph
```

Any retained `graph_memory.union_supergraph.*` import must be individually
classified as a pure value/contract import with no graph store construction and
assigned to D.3 relocation/deletion. Prefer removing it now if bounded.

---

## 17. Acceptance proof

D.2A is merge-ready only when the implementation PR records:

1. exact immutable implementation base descended from this design;
2. changed-file inventory;
3. port + adapter contract summary;
4. mounted Threat consumer inventory before/after;
5. unit test commands and counts;
6. isolated PostgreSQL integration test commands and counts;
7. parent→child publication witness;
8. exact retry witness;
9. uncertain-outcome/lost-receipt recovery witness;
10. stale-parent witness;
11. Buddy graph physical-absence witness;
12. static dependency scan result;
13. `ruff`/type/test status required by repository policy;
14. atomic tracker/roadmap + ACTIVE_AUTHORITY mirror update;
15. explicit APP-STATE collision check for shared config/dependency/bootstrap
    paths, with no unauthorized cross-lane edits.

No live Eldyrwild publication is required. Synthetic/isolated authority data is
preferred for this migration proof.

---

## 18. Stop conditions

Stop rather than guessing if any of these occur.

### 18.1 DungeonMind cannot express a required Threat fact

If exact DungeonMind revision/publication contracts cannot represent a fact
needed for create-new/connect-existing safety or materialization verification,
identify the exact semantic gap. Do not reconstruct Buddy state as a
compatibility answer.

The correct successor may be a bounded DungeonMind contract PR.

### 18.2 Port starts becoming a generic database abstraction

If implementation begins exposing SQL, generic CRUD, connections, repository
bundles, or arbitrary transactions to product code, stop. That is not the
World Graph authority port in this handoff.

### 18.3 Buddy persistence middleware becomes required

If migrating the Threat graph authority unexpectedly requires moving Buddy
operation/proposal/commit state to PostgreSQL, stop and explain the coupling.
The two persistence domains are intentionally separate. APP-STATE is the owner
of that architecture, not CUTOVER.

### 18.4 Cross-domain atomic transaction appears necessary

Do not solve an uncertain publication by wrapping Buddy + DungeonMind state in
one transaction. Preserve durable intent + idempotent authority recovery. If a
new failure mode makes that insufficient, document it explicitly for review.

### 18.5 D.1 must materially change

If extracting a shared DungeonMind publication primitive would alter D.1's
accepted exact-run semantics, keep D.1 stable. Do not destabilize #634 for
abstraction purity.

### 18.6 Another product workflow enters the diff

Worldbuilding and first-world are named successors. Shared helper edits are
allowed only when necessary for Threat correctness and covered by owning tests.
Do not silently migrate a second product writer.

### 18.7 APP-STATE implementation collides on shared infrastructure

If APP-STATE AS1 or another active state-migration slice owns a shared root
configuration/dependency/bootstrap path required by D.2A, do not merge parallel
incompatible edits. Re-anchor and serialize the shared infrastructure change,
while preserving the distinct WorldGraphAuthority and Buddy-state boundaries.

---

## 19. Exit state and successors

After D.2A, repository truth should be:

```text
Mounted graph readers
  → DungeonMind native

Exact-run Graph Review governed writes
  → DungeonMind native (D.1)

Threat publication lifecycle
  → WorldGraphAuthority port
      → DungeonMind production adapter

DungeonBuddy Threat workflow state
  → still Buddy-owned stores
     (APP-STATE/future persistence migration may replace storage later)

Remaining mounted Buddy graph writers
  → worldbuilding
  → first-world/bootstrap
```

Then dispatch:

```text
D.2B  worldbuilding writer behind the proven authority boundary
D.2C  first-world/bootstrap through the appropriate DungeonMind initialization authority
D.3   delete the obsolete Buddy graph engine, compatibility namespaces, and historical runtime stubs
```

Before reusing the D.2A port in D.2B, treat Threat as evidence rather than
proof of a universal abstraction. Extend the port only for capabilities
worldbuilding genuinely requires. Do not predict the full future middleware
API from one client.

APP-STATE may proceed independently as long as its implementation does not
claim World Graph authority and shared infrastructure edits are serialized.

---

## 20. Implementation-agent first pass

Before editing code:

1. read `AGENTS.md` and the repository PR/review-cycle process;
2. read `HANDOFF-APP-STATE-application-state-architecture.md` only for the
   parallel ownership/collision boundary; do not implement its AS0/AS1 scope;
3. rebase from the exact immutable `main` that contains this handoff;
4. inventory every mounted Threat route/service and every direct/transitive
   graph-runtime call reachable in `dungeonmind` mode;
5. inspect D.1 `world_graph_writes.py` and pinned DungeonMind publication
   contracts for reusable native primitives;
6. write the port contract and fake tests before changing Threat behavior;
7. migrate SBW09a → SBW09b occupancy → SBW09c1 → SBW09c2b in dependency order;
8. preserve product-state persistence and lifecycle semantics;
9. run the physical-absence and isolated PostgreSQL witnesses;
10. re-check APP-STATE for active shared-path leases before touching root DB
    config, dependency pins, server bootstrap, or Docker/dev lifecycle;
11. update tracker/roadmap/mirrors atomically with final implementation state;
12. hand back exact SHAs, commands, counts, remaining dependencies, and any
    D.3 pure-contract namespace debt.

The implementation PR should not claim the future middleware exists. Its claim
is narrower and testable:

> **Threat publication no longer knows how World Graph persistence works; it
> knows only the World Graph authority capability it needs.**
