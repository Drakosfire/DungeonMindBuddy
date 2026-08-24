---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / D.1 native governed write context
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-native-governed-write-context.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  Remove Buddy World Graph hydration/replay from the normal governed
  exact-run prepare → confirm workflow in `dungeonmind` authority mode.
  New review packages must seal public DungeonMind parent revision IDs,
  confirmation must reconstruct and validate against DungeonMind-native graph
  facts, and publication must produce a DungeonMind child without opening,
  rebuilding, or hydrating Buddy's World Graph.
---

# HANDOFF — CUTOVER D.1: native governed write context / hydration retirement

**Created:** 2026-08-24  
**Status:** READY TO IMPLEMENT  
**Workstream:** CUTOVER / World Graph runtime retirement  
**Direction:** DESIGN → CODE → REVIEW  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Buddy base / current `main`:** `65d13dcca8162b5eccd0c81dd4235dec93c8cd0c` (merge of Buddy PR #633)  
**#633 accepted head:** `ebb57adebe063b9c81fd4caa9a1274cfd6d6fb01`  
**DungeonMind pin:** `c5d3688587b0f5d506e0f7d64f33eb0628bac896` (DungeonMind PR #45 / R.3a)  
**Suggested implementation branch:** `cutover/native-governed-write-context`  
**Suggested PR title:** `CUTOVER: remove Buddy hydration from governed writes`  
**Predecessor:** Buddy PR #633 — unconditional native DungeonMind production reads / `DEMOLITION_READY`  
**Successor:** D.2 mounted legacy writer migration/retirement, then D.3 final Buddy graph-engine deletion

> **Dispatch ruling:** PR #633 finished the production-read cutover. The old
> Buddy graph runtime is no longer a valid read implementation in
> `dungeonmind` authority mode. A repository inventory after #633 shows that
> the normal governed write workflow still reconstructs DungeonMind into a
> Buddy `UnionSupergraphStore` during prepare/confirm. Therefore “demolish the
> Buddy graph runtime” must be decomposed. D.1 removes that write-side
> dependency first. It does **not** attempt to delete every historical/kernel
> consumer in one PR.

---

## 1. Mission

Make this statement mechanically true for the normal governed exact-run
review workflow:

> **When `DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind`, prepare and confirm
> use DungeonMind-native graph facts and public DungeonMind revision identity.
> They do not open, hydrate, replay, rebuild, or otherwise depend on Buddy's
> World Graph. Confirmation publishes a DungeonMind child directly.**

Today, after PR #633, reads are already clean:

```text
Buddy product read
        ↓
Buddy direct DTO adapter
        ↓
DungeonMind projection / retrieval
        ↓
DungeonMind PostgreSQL
```

But the normal governed write path still behaves approximately like this:

```text
prepare
  ↓
open Buddy World Graph head
  ↓
identity gate against UnionSupergraphStore
  ↓
seal Buddy/private parent revision

confirm in dungeonmind mode
  ↓
open DungeonMind authority
  ↓
hydrate exact DungeonMind parent into Buddy-shaped graph
  ↓
replay contributions / construct UnionSupergraphStore
  ↓
re-verify sealed package against hydrated Buddy revision
  ↓
translate to DungeonMind review
  ↓
publish DungeonMind child
```

After D.1:

```text
prepare in dungeonmind mode
  ↓
DungeonMind native mutation context @ exact current head
  ↓
identity gate / endpoint validation against that context
  ↓
seal public DungeonMind parent revision

confirm in dungeonmind mode
  ↓
DungeonMind native mutation context @ exact sealed parent
  ↓
verify source + sealed package
  ↓
reconstruct selected contribution without a filesystem graph
  ↓
DungeonMind review/finalize/publication
  ↓
exact DungeonMind child revision
```

The frozen Buddy graph may be physically absent for this workflow.

---

## 2. Why D.1 exists instead of one giant demolition PR

PR #633's implementation handback correctly declared `DEMOLITION_READY`, but
“demolition” is not one homogeneous dependency.

### 2.1 Product reads are already native

PR #633 removed `DUNGEONMIND_WORLD_GRAPH_DIRECT_READ`. In `dungeonmind`
authority mode, production projection, all five retrieval operations, and
Hermes latest-recap facts use DungeonMind directly. A DungeonMind failure fails
closed. Hydration is not a production-read fallback.

Do not reopen that work.

### 2.2 Normal governed writes still reconstruct Buddy graph state

Repository evidence on `main` `65d13dcc…`:

- `apps/live_control_server/services/extract_promote.py::prepare` calls
  `prepare_extract_promote(... world_root=world_graph_root())`.
- `src/graph_memory/extract_promote_ops.py::prepare_extract_promote` calls
  `gate_candidate_graph_against_head(...)`.
- `src/graph_memory/extract_identity_gate.py::gate_candidate_graph_against_head`
  calls `open_current_world_graph(root, world_id)` and resolves identity against
  a `UnionSupergraphStore`.
- DND-mode confirm calls
  `apps/live_control_server/integrations/dungeonmind_kernel/world_graph_authority.py::confirm_via_dungeonmind`.
- `confirm_via_dungeonmind` calls `_ensure_hydrated_revision(...)`, reconstructs
  the selected DungeonMind revision as a Buddy graph, verifies/rebuilds the
  contribution against the hydrated Buddy revision, and loads the hydrated
  store again for endpoint-kind checks.
- `hydrate_world_graph` imports and executes Buddy contribution replay,
  `rebuild_from_contributions`, `UnionSupergraphStore`, and Buddy revision
  publication/storage machinery.

That is current production write behavior, not archaeology.

### 2.3 Other graph-kernel consumers are not all the same problem

There are additional mounted or historical callers, including Threat
publication commit, first-world/worldbuilding flows, Graph Review legacy merge,
old correction/cutover tools, prewarm/recipes, scripts, and tests.

D.1 must inventory them, but must not silently widen into all of them.

The decomposition is:

```text
D.1  native governed write context
     normal exact-run prepare/confirm no longer needs Buddy graph hydration

D.2  mounted legacy writer migration / retirement
     migrate or explicitly retire every remaining current product writer

D.3  final graph-engine deletion
     no production imports; delete kernel/world_supergraph/union_supergraph;
     physical-absence proof
```

---

## 3. Governing invariants

### 3.1 DungeonMind owns graph truth and public revision identity

In `dungeonmind` mode:

- the current parent is a DungeonMind revision id;
- a newly sealed review package names that DungeonMind revision id directly;
- a committed child is a DungeonMind revision id;
- Buddy does not invent a private hydrated revision identity between them;
- exact retry and stale-parent decisions are made against DungeonMind durable
  publication/revision state.

A new D.1 package must never seal a private Buddy hydration revision.

### 3.2 Buddy owns product workflow; DungeonMind owns world knowledge

The boundary remains:

> **Buddy knows what the user is doing. DungeonMind knows what the world knows.**

Buddy still owns:

- exact-run selection;
- source-byte verification;
- review package shape;
- GM assertion selection;
- product-specific identity/review UX;
- operation/retry presentation;
- product receipt composition.

DungeonMind owns:

- current/historical graph revision truth;
- admitted object identity and kinds;
- governed source/provenance truth;
- contribution-review finalization;
- graph materialization;
- atomic head publication.

Do not move the agent harness, Plan/Play context, review UI state, or generic
product context into DungeonMind.

### 3.3 No compatibility hydration for new writes

Supporting current Buddy does not mean preserving old review packages forever.

For new D.1 prepares:

```text
parent_revision_id = exact public DungeonMind revision
```

A pre-D.1 uncommitted package that names a Buddy/private hydrated parent is not
reconstructed through hydration merely to preserve compatibility. It should
fail explicitly with re-prepare guidance.

Already-published durable DungeonMind operations are different: if the exact
operation already exists and proves publication, confirmation may return the
same durable child as an idempotent retry without reopening obsolete Buddy
state.

### 3.4 No hidden fallback

If DungeonMind cannot supply the exact graph state required for prepare or
confirm, fail closed.

Forbidden:

```text
DungeonMind unavailable
→ open frozen Buddy graph
→ continue anyway
```

Also forbidden:

```text
DungeonMind projection lacks needed fact
→ hydrate to recover it
```

If a current product requirement is genuinely missing from the DungeonMind
contract, STOP and dispatch the smallest DungeonMind prerequisite.

### 3.5 R.3 semantic contract remains frozen

This PR is write-context demolition, not a new graph interpretation.

Do not change:

- campaign/world scope semantics;
- GM/PLAYER semantics;
- evidence-chain admission;
- object/relationship identity semantics;
- exact pin behavior;
- search/retrieval behavior;
- source-anchor behavior;
- semantic-profile vocabulary;
- the ratified R.3 divergence ledger.

### 3.6 Source verification remains source verification

Source prose, exact source revision digest, span grounding, sealed review
material, and operator selection remain required.

Removing Buddy graph hydration must not weaken source/evidence checks.

---

## 4. Target internal contract: `WorldGraphMutationContext`

The old prepare/confirm code accepts a full `UnionSupergraphStore` because that
was once the only graph representation available. The current product logic
uses a much smaller subset of that graph.

Introduce the smallest storage-neutral internal view needed for governed
mutation decisions. Name may vary, but the contract should be explicit and
typed.

Provisional shape:

```text
WorldGraphMutationContext
  world_id
  revision_id
  head_revision_id
  objects
    object_id
    label
    kind
    aliases
    campaign_scope?      # only if current identity logic demonstrably needs it
```

The context is:

- Buddy-owned adaptation logic;
- derived from one exact DungeonMind revision;
- not an authority database;
- not an agent context;
- not a cache contract;
- not a new graph engine.

Do not copy the entire DungeonMind graph into a new Buddy domain model merely
under another name.

### 4.1 Minimum current consumers to support

The existing identity/proposal path currently uses the Buddy store for:

1. existing node identity/label/kind/aliases;
2. fixed-candidate scorer input;
3. `_infer_object_kind` for same-name PC/NPC/party/faction behavior;
4. `resolve_identity` candidate matching;
5. endpoint existence when reconstructing selected edge assertions;
6. endpoint kinds when translating accepted edges into DungeonMind-qualified
   predicates.

If implementation discovers another actual read of store state in the normal
prepare/confirm path, either include the minimal fact with an explicit reason
or STOP if it represents a materially different capability.

### 4.2 DungeonMind producer

In `dungeonmind` authority mode, build the mutation context from the existing
native DungeonMind read seam.

Default lens for identity should be whole-world GM identity visibility, because
the old durable world store was not campaign-copied identity authority:

```text
world_id         = requested world
scope_mode       = WORLD_CROSS_CAMPAIGN
campaign_id      = None
admissibility    = GM
revision_pin     = exact selected DungeonMind revision
query_text       = none
```

The implementation must verify this against current identity behavior rather
than silently narrowing to one campaign.

If the current DungeonMind projection cannot expose a required surviving
identity fact, STOP. Do not add a product-specific DungeonMind endpoint inside
this Buddy PR without a reviewed prerequisite.

### 4.3 File-mode producer

`buddy_files`, `quiesced`, and explicit fixture roots are not retired in D.1.
They may adapt a file-backed store into the same mutation-context interface.

That compatibility is scoped to those explicitly retained modes and tests. It
must not be reachable from `dungeonmind` production behavior.

---

## 5. Required refactors

### 5.1 Identity gate: remove `UnionSupergraphStore` as the semantic input

Refactor the current identity helpers so their logical dependency is the
mutation context, not storage.

At minimum:

- fixed-candidate scorer accepts a sequence/mapping of object identity facts;
- `_infer_object_kind` accepts object facts;
- identity resolution accepts the neutral object set;
- endpoint existence uses `existing_object_ids` plus nodes selected in the
  current batch;
- endpoint-kind qualification uses context object kinds plus newly selected
  node assertions.

Do not implement a second identity algorithm just for DungeonMind if the
existing one can be expressed over the neutral facts.

If the current `graph_memory.identity_resolution` functions are already pure
over simple dicts/object candidates, reuse those pure parts and move the store
adapter outward.

### 5.2 Package verification/reconstruction: split storage from semantics

`resolve_merged_contribution_from_package(...)` currently takes `root` and
ultimately loads a Buddy revision to prove endpoint availability.

Create a root-free/internal equivalent for DND mode, e.g.:

```text
verify_and_materialize_promote_package(
  review_package,
  confirming_principal,
  expected_parent_revision_id,
  assertion_ids,
  mutation_context,
  source_verification_context,
) -> verified + GraphContribution
```

Exact naming is not important. Dependency direction is.

The DND path must be able to:

- verify proposal digest / principal / exact parent;
- reconstruct selected slices;
- preserve assertion selection order/semantics;
- verify selected edge endpoints against the exact parent context;
- verify source bytes/digest;
- produce the same product contribution material expected by the current DND
  mapping layer;

without a filesystem graph root.

The retained file-mode wrapper may still obtain a mutation context from a
Buddy store.

### 5.3 New DungeonMind write module

Production DND write concerns should no longer live inside a module whose main
purpose is DND→Buddy hydration.

Preferred target:

```text
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
```

It may contain/refactor:

- DungeonMind repository/service construction;
- receipt/public parent binding only where still required;
- operation-id derivation;
- Buddy contribution → DungeonMind review candidate mapping;
- assertion verdict construction;
- identity dispositions;
- predicate/kind qualification;
- endpoint-kind admission;
- `finalize_contribution_review_v2` capability policy;
- publication;
- post-publication verification;
- typed Buddy-facing errors.

Hard dependency rule for the new production DND write module:

```text
NO graph_memory.kernel
NO graph_memory.world_supergraph
NO graph_memory.union_supergraph
```

Using Buddy proposal/contribution value models as a product contract is
acceptable in D.1. Owning a Buddy graph runtime is not.

### 5.4 Retire hydrated receipt decoration

Current confirm receipts may carry `projection_world_root` so Buddy receipt
code can reopen the hydrated graph and decorate affected assertion/object IDs.
That is a hydration-era escape hatch.

After D.1:

- derive affected IDs from sealed/reconstructed contribution material;
- use public DND parent/child revision IDs;
- do not return or consume a private graph-root override;
- do not hydrate just for receipt decoration.

---

## 6. DND-mode prepare behavior

For the normal exact-run prepare endpoint/workflow under `dungeonmind`:

1. resolve the exact ExtractionRun as today;
2. verify source URI/bytes/revision/span evidence as today;
3. resolve the current DungeonMind head;
4. build `WorldGraphMutationContext` from that exact head;
5. identity-gate candidate nodes against that context;
6. validate edge endpoint existence against that context + selected nodes;
7. seal the review package with the **public DungeonMind head revision id**;
8. return the normal product review package/summary.

Expected example on the current live world:

```text
parent_revision_id = rev:680c246047d67f9fe0293ee90526f670
```

Not:

```text
parent_revision_id = rev:<Buddy hydrated/private id>
```

The prepare request must succeed even when the configured old Buddy graph root
is missing, renamed, empty, or replaced by an explosion fixture.

---

## 7. DND-mode confirm behavior

For a new D.1 package:

### 7.1 Idempotent durable retry first

Derive the deterministic operation identity from the sealed package + selected
assertions + exact parent, as current DND publication logic does.

If DungeonMind already has a completed publication for that exact operation:

- validate the durable publication identity;
- return the same committed DungeonMind revision;
- do not rebuild/hydrate Buddy state;
- do not publish another child.

### 7.2 Exact parent verification

If no completed publication exists:

- package parent must be a public DungeonMind revision;
- resolve that exact revision;
- require current head to match the sealed parent for a new publication;
- if head advanced, fail stale-parent with re-prepare/review guidance;
- never translate the parent through a private Buddy hydration id.

### 7.3 Native context at sealed parent

Build the mutation context at the exact sealed parent, not “whatever head is
now convenient.”

This ensures:

```text
reviewed world == confirmed world
```

### 7.4 Reconstruct product contribution without graph storage

Using the sealed package, source verification, selected assertion IDs, and
native mutation context:

- verify the sealed proposal;
- reconstruct contribution slices;
- enforce endpoint existence;
- preserve accepted/rejected assertion partition;
- preserve current identity outcomes;
- derive endpoint kinds from context + selected node assertions.

### 7.5 Publish through DungeonMind

Reuse the current governed publication seam:

```text
Buddy reviewed contribution
→ DungeonMind v2 review candidate + verdicts
→ finalize contribution review v2
→ publish finalized review
→ immutable DungeonMind child
```

No local Buddy graph publication occurs.

### 7.6 Verify the child natively

Post-publication verification must use DungeonMind repository/read state:

- exact child exists;
- parent is the sealed parent;
- operation/publication record matches;
- current head is the child when publication won CAS;
- expected accepted objects/relationships are visible under the appropriate
  native DND read lens where the product contract requires them.

Do not verify success by rebuilding Buddy contribution history.

---

## 8. Legacy sealed package policy

D.1 is not a permanent migration layer for pre-D.1 in-flight review packages.

Classify package parent identity explicitly.

### 8.1 Public DungeonMind parent

Supported. Continue normally.

### 8.2 Known old Buddy A revision

Do **not** silently bridge it for a newly attempted D.1 publication. The package
was reviewed against the old model and must be re-prepared under current DND
truth.

Return an explicit stale/legacy-package error with re-prepare guidance.

### 8.3 Private hydrated Buddy revision

Unsupported. It is not public authority identity. Fail closed and require
re-prepare.

### 8.4 Existing durable DungeonMind operation

If the operation was already published before D.1 and DungeonMind durable state
can prove the exact result, idempotent recovery may return it. Recovery authority
is the durable DungeonMind publication, not the old package's ability to reopen
a Buddy graph.

---

## 9. Hydration retirement authorized in D.1

Once the normal DND prepare/confirm path no longer depends on hydration, delete
hydration machinery that has no named remaining current consumer.

Candidate deletions include:

- `HydrationHandle`;
- `HYDRATION_TRANSLATION_VERSION` / hydration metadata schema/file handling;
- DND→Buddy reverse contribution/identity translation used only by hydration;
- `hydrate_world_graph`;
- `_ensure_hydrated_revision`;
- `ensure_hydrated_authority`;
- `AuthorityReadRoute`;
- `route_read_request`;
- `route_service_read`;
- hydration cache root registration/config when no named current consumer
  remains;
- `projection_world_root` confirm-receipt decoration;
- replay-order reconstruction used only to build hydrated caches;
- tests whose sole purpose is validating the deleted hydration implementation.

Do not keep hydration because the R.3 differential harness historically used
it. Historical comparison evidence does not justify a production runtime.
Adapt a retained test to an explicit fixture/file oracle or retire it when its
supported-contract value is exhausted.

### 9.1 Important limitation

Do not delete a helper merely because it lives in
`integrations/dungeonmind_kernel/world_graph_authority.py`.

That module currently mixes:

- hydration/read compatibility;
- publication mapping;
- DungeonMind capability policy;
- semantic qualification;
- authority errors;
- historical adoption helpers.

Move/retain the smallest pieces with named current consumers. Delete the
hydration architecture, not necessarily the filename in one mechanical sweep.

---

## 10. Mandatory production-consumer inventory

Before editing, produce a bounded inventory and include the final table in the
handoff implementation record.

Required columns:

```text
path / callable
mounted product route or caller?
current dungeonmind behavior
Buddy graph-runtime dependency
D.1 disposition
successor owner if retained
```

At minimum classify:

1. exact-run / Graph Review prepare;
2. exact-run / Graph Review confirm;
3. Threat publication identity candidate preparation;
4. Threat publication commit;
5. worldbuilding prepare;
6. worldbuilding confirm;
7. first-world bootstrap/confirm;
8. `graph_review_contribution_merge`;
9. `world_graph_prewarm`;
10. projection recipes;
11. old Eldyrwild correction/cutover services;
12. scripts/evals/audits;
13. tests/fixtures.

Do not write “remaining writers use the kernel” without naming the actual
mounted route/caller.

### 10.1 Known dispatch-time classification

Already observed before D.1 implementation:

- Threat publication identity uses `project_world_graph`, so its graph read is
  already native under DND mode.
- Threat publication commit is mounted through API/UI and still imports Buddy
  kernel/contribution/UnionSupergraph machinery. That is likely D.2 work.
- Exact-run normal confirm is definitely D.1 because it calls
  `confirm_via_dungeonmind` and hydrates.

Treat these as starting evidence, not a substitute for the implementation
inventory.

---

## 11. Required implementation sequence

### Step 0 — re-anchor and inventory

Confirm:

```text
main = 65d13dcca8162b5eccd0c81dd4235dec93c8cd0c
#633 merged
DUNGEONMIND_WORLD_GRAPH_DIRECT_READ absent from runtime control
DungeonMind pin = c5d36885…
```

Then produce the §10 consumer inventory.

If current `main` moved, rebase/merge deliberately and update exact ancestry in
the handback.

### Step 1 — introduce neutral mutation context

Add the smallest typed context plus:

- DND-native producer;
- retained file-store producer for explicit legacy/test modes.

Tests first should prove DND context construction works with the frozen Buddy
world root unavailable.

### Step 2 — refactor identity gate and endpoint checks

Remove the logical dependency on `UnionSupergraphStore` from the pure identity
and contribution-reconstruction path.

Keep file-mode adapters as outer compatibility seams only where needed.

### Step 3 — make DND prepare native

Route `dungeonmind` prepare through the DND mutation context.

Seal public DND parent identity.

Explode any Buddy graph open/load call in the DND prepare tests.

### Step 4 — split native DND write integration from hydration module

Create/refactor the production write module under
`integrations/dungeonmind/`.

Move only still-current write concerns.

### Step 5 — make DND confirm native

Implement §7, including durable retry, exact parent, context-at-parent,
root-free reconstruction, publication, and native post-publish verification.

### Step 6 — delete now-unreachable hydration

Delete only after static/runtime inventory proves the normal DND read/write
paths no longer use it.

### Step 7 — rerun product contract and restart/absence proofs

Prove a newly published fixture child remains readable through the ordinary
native product path after restart, with the Buddy graph root absent.

### Step 8 — atomic state-authority sync

Update current CUTOVER state in the implementation PR; see §15.

---

## 12. Acceptance tests

### 12.1 DND prepare without Buddy graph

Required proof:

```text
authority = dungeonmind
old Buddy world graph root = absent / explosion stub
valid exact-run candidate + live/fixture DND parent
→ prepare succeeds
→ parent_revision_id == exact public DND parent
```

Tests must explode if DND prepare invokes:

- `open_current_world_graph`;
- `load_world_graph_revision`;
- `UnionSupergraphStore` construction;
- `ensure_hydrated_authority`;
- `hydrate_world_graph`;
- contribution replay/rebuild.

### 12.2 Identity behavior

At minimum prove:

- known existing object resolves to the current DND object id;
- create-new candidate retains the intended current identity outcome;
- same-name PC/NPC/party/faction inference behavior remains intentional;
- ambiguous/non-mutating identity outcome still fails/stays unresolved exactly
  as current product contract requires;
- fixed-candidate scorer remains diagnostic only.

Do not compare obsolete Buddy graph rows if DND semantics intentionally differ.

### 12.3 Endpoint existence

Prove:

- selected edge → existing DND node passes;
- selected edge → node introduced in same selected batch passes;
- selected edge → absent endpoint fails closed;
- endpoint validation uses the exact sealed parent context.

### 12.4 DND confirm without hydration

In an isolated test database/world:

```text
D_parent
→ prepare package sealing D_parent
→ confirm selected assertions
→ D_child
```

Assert:

- D_child parent == D_parent;
- exactly one child publication;
- no Buddy graph files created;
- no hydration cache created;
- no Buddy graph open/rebuild calls;
- response parent/child identities are public DND IDs.

### 12.5 Exact retry

Repeat the same logical confirmation.

Expected:

```text
same durable operation
same D_child
zero additional child revisions
no hydration
```

### 12.6 Stale parent

Prepare on `D_parent`, advance head independently to `D_other`, then confirm.

Expected:

- explicit stale-parent outcome;
- no new child from the stale package;
- no hydration/replay attempt;
- re-prepare guidance.

### 12.7 Legacy package

A package carrying a private/legacy Buddy parent must not trigger compatibility
hydration.

Expected: typed refusal / re-prepare requirement.

### 12.8 Authority unavailable

Missing/invalid DSN or unavailable DungeonMind:

- prepare fails closed;
- confirm fails closed;
- zero reads from frozen Buddy graph;
- zero local publication.

### 12.9 Source/evidence regression

Preserve existing checks for:

- exact source digest;
- source URI admission;
- source revision identity;
- span/evidence grounding;
- assertion selection;
- explicit empty-selection refusal;
- sealed proposal digest/principal.

### 12.10 Restart + physical-absence proof

Publish one test child through the D.1 path, stop/recreate the Buddy service
context, leave the old Buddy graph root absent, then prove through the ordinary
native production read seam:

- exact child is readable;
- head is the child;
- exact parent remains pinnable;
- affected object/relationship is retrievable where admitted.

This is the first meaningful demolition proof.

### 12.11 File-mode regression

Where `buddy_files`, `quiesced`, or explicit fixture-root modes are intentionally
retained in D.1, run their owning tests. Their existence must not create a DND
fallback.

### 12.12 Static dependency proof

The new production DND prepare/confirm modules must have zero imports of:

```text
graph_memory.kernel
graph_memory.world_supergraph
graph_memory.union_supergraph
```

Also run a call-site search proving DND production prepare/confirm cannot reach
hydration/rebuild through an indirect helper.

---

## 13. Live witness policy

No new live Eldyrwild graph mutation is required to merge D.1.

Allowed without a new operator decision:

- read-only construction of a mutation context at live `D_B`;
- read-only prepare characterization if it does not publish and if normal source
  material is available;
- isolated PostgreSQL/in-memory fixture publication;
- exact restart/absence proof against the isolated fixture.

If implementation wants to publish a new live Eldyrwild child merely as a D.1
witness, STOP and request explicit operator authorization.

The previous live `D_A → D_B` mutation already proves the DungeonMind writer
boundary can own a child. D.1 must prove Buddy no longer needs hydration to use
that boundary.

---

## 14. Performance / caching

This is not a new optimization lane.

Record representative prepare and confirm durations after the refactor so a
material regression is visible, but do not introduce:

- Redis;
- a distributed cache;
- a global mutable graph singleton;
- a second materialized graph;
- speculative search indexes;
- long-lived product-specific DungeonMind mirrors.

R.3a already made the native graph view fast enough for production. Prefer one
coherent exact-revision context per operation.

---

## 15. Atomic state-authority updates required in the implementation PR

The implementation PR must update the current mutable CUTOVER authority set.

### 15.1 `HANDOFF-CUTOVER-native-read-switch.md`

Mark #633 landed and record:

```text
accepted head ebb57ade…
merge       65d13dcc…
Cycle 2 approval 5011598382
DEMOLITION_READY
```

### 15.2 PR tracker + ACTIVE_AUTHORITY mirror

Change:

```text
native-read switch → DONE
```

Replace one broad demolition row with explicit sequencing:

```text
D.1 native governed write context / hydration retirement → DOING/DONE
D.2 mounted legacy writer migration/retirement           → READY after D.1
D.3 final Buddy graph-engine deletion                    → BLOCKED on D.2
```

The exact statuses at merge should reflect reality.

### 15.3 Roadmap + ACTIVE_AUTHORITY mirror

Record #633 merge/current main and the same D.1/D.2/D.3 decomposition.

Do not leave “native-read switch in review.”

### 15.4 `STEWARDS-ANCHOR-cutover.md`

Update current repository truth:

- current main includes #633 merge;
- native DND reads are unconditionally production;
- remaining CUTOVER debt is write-side/runtime demolition;
- D.1 specifically removes normal governed-write hydration.

### 15.5 This handoff

Add implementation record:

- exact base/head;
- files changed;
- consumer inventory;
- old-vs-new write diagram;
- tests and exact counts;
- DND dependency scan;
- isolated publication witness;
- restart/physical-absence witness;
- deleted hydration surface;
- retained D.2 consumers;
- final disposition.

Keep canonical/mirror files byte-identical.

---

## 16. Explicitly out of scope

Do **not** use D.1 to:

- migrate Threat publication commit merely because it imports the kernel;
- redesign Threat publication identity UX;
- rewrite worldbuilding/first-world persistence broadly;
- delete every historical correction/cutover service;
- delete all of `src/graph_memory`;
- retire `buddy_files` / `quiesced` globally;
- change DungeonMind graph semantics;
- change R.3 read semantics;
- add a product-specific DungeonMind identity API unless a STOP condition
  proves the current API insufficient;
- create a generalized “context platform” in DungeonMind;
- move Buddy agent/harness state into DungeonMind;
- change Play Surface or APP-STATE architecture;
- perform another live Eldyrwild mutation without explicit approval;
- preserve obsolete private revision identities just because old packages used
  them.

---

## 17. Stop conditions

STOP and hand back the exact missing boundary if any of these are true.

### 17.1 Missing DungeonMind fact

The accepted native DungeonMind projection cannot supply a graph fact that the
normal current identity/endpoint workflow genuinely requires.

Report:

```text
missing fact
current named consumer
why it is a surviving product requirement
why existing DND projection/retrieval cannot express it
smallest proposed DND prerequisite
```

Do not hydrate as a workaround.

### 17.2 Buddy-only identity semantics are actually product requirements

If identity resolution depends on Buddy-only state not represented in DND,
distinguish:

- obsolete implementation residue → retire;
- surviving current product requirement → bounded design decision / DND
  prerequisite.

Do not silently clone Buddy's old graph semantics.

### 17.3 Current DungeonMind review cannot express the package

If the v2 review/finalize/materialize contract cannot represent an assertion
that the current normal product can validly publish, STOP with the exact
assertion shape and ownership boundary.

Do not change DungeonMind public contracts opportunistically inside this PR.

### 17.4 Scope expands into another mounted writer

If refactoring a shared helper proves Threat publication or another mounted
writer must change atomically to keep the normal exact-run path correct, stop
and explain why the slice cannot remain bounded. Do not silently absorb a
second product workflow.

### 17.5 Physical-absence proof fails

If DND prepare/confirm still requires the frozen Buddy graph after the intended
refactor, D.1 is not done. Identify the exact dependency rather than marking it
cleanup debt.

---

## 18. Required handback

Return:

1. implementation branch and exact base/head SHAs;
2. changed-file list;
3. complete §10 consumer inventory;
4. exact `WorldGraphMutationContext` contract and why each field exists;
5. DND-mode prepare flow before/after;
6. DND-mode confirm flow before/after;
7. legacy-package disposition and test;
8. hydration/replay functions/files deleted;
9. any runtime helpers retained, with named current consumer;
10. static DND production dependency scan;
11. owning test commands and exact passed/skipped/failed counts;
12. isolated DND parent→child publication witness;
13. exact retry witness;
14. stale-parent witness;
15. source/evidence regression proof;
16. restart + old-Buddy-graph-absent proof;
17. representative prepare/confirm latency;
18. atomic roadmap/tracker/anchor sync proof and mirror byte identity;
19. workspace/branch status;
20. disposition:

```text
D1_DONE
```

or

```text
D1_BLOCKED
<exact stop condition>
```

---

## 19. Acceptance statement

D.1 is mergeable only when this statement is true:

> **In `dungeonmind` authority mode, the normal exact-run prepare → confirm
> workflow reads graph facts from DungeonMind, seals public DungeonMind parent
> revision IDs, and publishes DungeonMind child revisions without hydrating,
> replaying, rebuilding, or opening Buddy's World Graph. The old Buddy graph
> may be physically absent for this workflow.**

This is narrower than final CUTOVER completion, deliberately.

D.1 does not claim that no Buddy graph-engine code remains. It removes the
last known old-runtime dependency from the normal governed write path and
turns the remaining demolition into an explicit mounted-consumer retirement
problem.

---

## 20. Successor contract

After D.1, dispatch **D.2 — mounted legacy writer migration/retirement** from
the completed consumer inventory.

Expected candidates include, subject to the inventory:

- Threat publication commit — definitely mounted API/UI and still kernel-heavy;
- worldbuilding confirm if still mounted/current;
- first-world flow if still a supported current capability;
- Graph Review legacy merge if a mounted caller remains;
- any other product writer proven reachable.

D.2 should migrate or explicitly retire those product capabilities. It should
not preserve an obsolete writer merely because tests still instantiate it.

Then D.3 performs the final structural deletion:

```text
zero production imports:
  graph_memory.kernel
  graph_memory.world_supergraph
  graph_memory.union_supergraph

zero production UnionSupergraphStore construction
zero product contribution replay/rebuild
zero Buddy graph authority fallback
old graph physically absent
Buddy boots / reads / governed writes through DungeonMind
```

At D.3 completion, the architectural statement becomes literal:

> **DungeonBuddy does not contain a production World Graph runtime. It is a
> product that consumes DungeonMind.**
