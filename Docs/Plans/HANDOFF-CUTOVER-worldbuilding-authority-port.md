---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / D.2B — worldbuilding authority-port migration
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-worldbuilding-authority-port.md
  - Implementation repository: Drakosfire/DungeonMindBuddy
  - Predecessor: Buddy PR #637 / D.2A Threat authority port

  ## Outcome
  Move the mounted existing-world worldbuilding prepare → confirm workflow off
  Buddy's World Graph runtime and onto the storage-neutral WorldGraphAuthority
  boundary proven by D.2A. In dungeonmind authority mode, prepare must read one
  exact public parent plus the identity snapshot used for create-new/bind-existing
  semantics through the authority port; confirm must rebuild from that sealed
  parent/identity authority, publish or recover exactly one DungeonMind child,
  and verify the resulting worldbuilding facts without opening, loading, merging,
  replaying, or rebuilding Buddy's filesystem graph.

  ## Parallel-lane contract
  APP-STATE may proceed in parallel. D.2B must not edit pyproject.toml, uv.lock,
  src/application_state/**, workspace-document persistence, or the APP-STATE
  authority docs. D.2C first-world/bootstrap remains a separate successor and
  its implementation lease does not open in this PR.

  ## Required proof
  - exact DungeonMind parent + identity-snapshot prepare with Buddy graph absent
  - create-new / bind-existing identity semantics preserved
  - identity-ledger drift without graph-head advance does not change sealed confirm
  - native D_A → D_B publication and exact retry/recovery with zero second publish
  - stale distinct operation fails closed
  - accepted worldbuilding facts verified on the exact DungeonMind child
  - complete mounted worldbuilding lifecycle succeeds with Buddy graph runtime exploded
  - D.1 Graph Review and D.2A Threat authority-port regressions remain green
---

# HANDOFF — CUTOVER D.2B: Worldbuilding publication behind World Graph authority

**Created:** 2026-08-24  
**Status:** DESIGNED — dispatch after this design is accepted and re-anchored  
**Workstream / flow:** `CUTOVER`  
**Direction:** DESIGN → CODE → REVIEW  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Design base:** `28daea7e90b396c1b9e9b5fcc12a0b9427674d8c` — merge of Buddy PR #637 / D.2A  
**D.2A accepted head:** `3c74dc40dbcaf46b316e379e5a703e66570d2dea`  
**D.2A review cycles:** 3; Cycle 3 PASS-equivalent  
**DungeonMind pin at design:** `c5d3688587b0f5d506e0f7d64f33eb0628bac896`  
**Parallel authority:** `Docs/Design/ARCHITECTURE-application-state-layer.md` / APP-STATE AS0, merged in Buddy PR #636  
**Suggested implementation branch:** `cutover/worldbuilding-authority-port`  
**Suggested PR title:** `CUTOVER: move worldbuilding publication behind DungeonMind authority`  
**Predecessor:** D.2A Threat authority port / Buddy PR #637  
**Successors:** D.2C first-world/bootstrap authority migration; D.3 final Buddy graph-engine deletion

> **Dispatch ruling:** D.2A proved that a mounted product workflow can consume a
> storage-neutral `WorldGraphAuthority`, publish/recover through DungeonMind, and
> remain correct with Buddy's World Graph physically absent. D.2B is the second
> client and therefore the first real generalization test of that seam.
>
> This slice is not “replace one Kernel merge.” Existing-world worldbuilding
> prepare still loads a Buddy revision store to decide create-new occupancy,
> bind-existing target validity, redirects, canon/memory state, and alias
> ownership. Confirm still imports the Kernel and merges into Buddy storage.
> D.2B migrates the complete mounted prepare → confirm authority boundary.
>
> First-world/bootstrap is deliberately excluded. Existing-world publication has
> a real expected parent; first-world initialization does not. D.2C must use the
> appropriate initialization authority rather than inventing a fake empty parent
> to fit this slice.

---

## 1. Mission and merge-ready invariant

Make this statement mechanically true:

> **When `DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind`, the mounted existing-world
> worldbuilding prepare → confirm workflow obtains graph and identity authority
> only through `WorldGraphAuthority`, seals the exact parent + identity snapshot
> used for its dispositions, and publishes or recovers one exact DungeonMind
> child without opening, loading, mutating, replaying, rebuilding, or verifying
> against Buddy's filesystem World Graph.**

One invariant governs every path in this slice:

```text
one exact existing-world authority snapshot
  = immutable graph parent
  + identity semantics captured for that prepare

prepare
  → deterministic reviewed worldbuilding plan

confirm
  → rebuild against that same sealed authority snapshot
  → exact idempotent governed publication or recovery
  → exact DungeonMind child verification
```

If implementation requires a second independently useful capability — first-world
initialization, Buddy application-state migration, Graph Review redesign, or a
new generic persistence substrate — stop and split.

---

## 2. Re-anchored repository state

At design base `28daea7e…`:

- D.1 / #634 is merged: exact-run Graph Review governed writes publish DungeonMind
  children without Buddy hydration.
- D.2A / #637 is merged: Threat head reads, occupancy, preflight,
  publish/recover/verify use `WorldGraphAuthority` in DungeonMind mode.
- `WorldGraphAuthority` currently exposes `current_head`, `read_revision`,
  `publish`, `recover`, and Threat-oriented `verify_child`.
- D.2A's production adapter already owns DungeonMind/PostgreSQL construction and
  maps product values to governed review publication.
- APP-STATE AS0 / #636 is merged. AS1 is allowed to proceed independently and
  owns Buddy Plan persistence, `src/application_state/**`, `pyproject.toml`,
  `uv.lock`, workspace-document persistence, and its own application-state DB.
- There are no open Buddy PRs at this design re-anchor.

The Campaign Supergraph tracker/roadmap still describe D.2A as `DOING`. That is
now stale. Per `AGENTS.md`, the D.2B implementation PR owns the backward-looking
atomic predecessor sync: D.2A becomes `DONE`, #637 merge/head/review truth is
recorded, and D.2B becomes the active CUTOVER slice. This design PR does not
perform routine state-sync bookkeeping.

---

## 3. Current mounted worldbuilding authority dependencies

### 3.1 Prepare still opens Buddy graph state

`apps/live_control_server/services/extract_promote.py::prepare_worldbuilding`
currently calls `build_worldbuilding_write_plan(...)` with:

```text
world_root=world_graph_root()
expected_parent_revision_id=request.expected_parent_revision_id
```

`src/graph_memory/worldbuilding_write_plan.py` then uses Buddy graph runtime to:

- open the current World Graph and compare the expected parent to head;
- load the exact `UnionSupergraphStore` revision;
- reject create-new when a node id or active redirect already occupies the id;
- resolve bind-existing against exact-parent nodes;
- reject merged-away, redirected, rejected, provisional, or wrong-kind targets;
- consult alias ownership while constructing bind-existing support assertions.

Those are real authority semantics. They cannot be replaced by a naive node-id
lookup without weakening the product contract.

### 3.2 Identity authority is no longer automatically revision-bound

The Buddy store historically co-located graph revision facts and identity
redirect/canon state. DungeonMind does not: the identity decision ledger is
append-only authority separate from the immutable graph revision, and the
current repository has no historical “identity ledger as-of graph revision”
read.

D.1 already encountered this exact problem. The accepted repair sealed the
identity snapshot used at prepare so later identity changes without graph-head
advance cannot change confirm semantics.

D.2B must not repeat the pre-D.1 Cycle-2 bug.

### 3.3 Confirm still mutates Buddy graph directly

`apps/live_control_server/services/extract_promote.py::confirm_worldbuilding`
currently imports `graph_memory.kernel` inside the mounted service and calls:

```text
kernel.merge_contribution_to_revision(...)
```

against `world_graph_root()` after rebuild-verifying the response-carried plan.
That is the remaining existing-world worldbuilding writer D.2B retires.

### 3.4 Worldbuilding and first-world share an orchestration file

`extract_promote.py` also owns first-world preparation/confirmation. Parallel
D.2B/D.2C implementation would therefore collide on a central file even before
port evolution is considered.

D.2B may extract only the existing-world worldbuilding orchestration into a
narrow service module and leave thin compatibility delegation in
`extract_promote.py`. It must not refactor first-world behavior while doing so.
This is a seam extraction to reduce ownership collision, not a general service
rewrite.

---

## 4. Target architecture

After D.2B:

```text
POST /api/live/extract-promote/worldbuilding/prepare
POST /api/live/extract-promote/worldbuilding/confirm
                  ↓
worldbuilding_graph_publication service
                  ↓
WorldGraphAuthority
   ├─ current_head
   ├─ exact mutation-context read
   ├─ exact revision read
   ├─ publish
   └─ recover
                  ↓
DungeonMindWorldGraphAuthorityAdapter
                  ↓
DungeonMind governed review / publication
                  ↓
PostgreSQL
```

Product code owns:

- exact ExtractionRun/source resolution;
- worldbuilding dispositions;
- candidate semantics;
- deterministic plan/effect construction;
- plan verification/rebuild rules;
- user/API receipt semantics;
- product-specific verification that the accepted worldbuilding effect is
  represented on the published child.

The authority adapter owns:

- DungeonMind/PostgreSQL construction;
- exact graph/head reads;
- exact identity-ledger adaptation needed by mutation context;
- stable mapping of product operation identity to DungeonMind review-operation
  identity;
- governed publication and durable recovery;
- raw infrastructure failure translation.

Neither side becomes a generic database abstraction.

---

## 5. Port evolution: only capabilities the second client proves it needs

D.2B may extend `WorldGraphAuthority`, but the extension must be justified by
worldbuilding's existing semantics rather than predicted future clients.

### 5.1 Add an exact mutation-context capability

Worldbuilding requires more than D.2A's `WorldGraphRevisionView`: create-new and
bind-existing depend on canon/memory state, redirects, alias ownership, and the
identity decisions that produce those facts.

Add one storage-neutral capability conceptually equivalent to:

```text
mutation_context(
  world_id,
  revision_id,
  sealed_identity_decisions? = None,
) -> WorldGraphMutationContext
```

Exact spelling is implementation-owned. Required semantics:

**Prepare mode — no sealed decisions supplied**

- read the requested immutable graph revision;
- read the current DungeonMind identity ledger for that world;
- adapt both into the existing storage-neutral `WorldGraphMutationContext`;
- include the serializable identity-ledger records used to create the context;
- include the current public head id so stale-parent prepare can fail closed.

**Confirm mode — sealed decisions supplied**

- read the same immutable graph revision;
- reconstruct identity redirects/canon/alias semantics from the sealed decision
  snapshot carried by the plan;
- do **not** substitute today's live identity ledger;
- return a context semantically equivalent to the prepare context even if later
  identity decisions were appended without graph-head advancement.

The existing D.1 DungeonMind mutation-context producer should be reused or
factored through product-neutral adapter helpers where bounded. Do not implement
an independent second identity adaptation algorithm.

The current `WorldGraphMutationContext` still imports some Buddy identity value
contracts under `graph_memory.kernel`. That is pure-value namespace debt, not a
reason to retain graph runtime. D.3 owns final relocation/deletion unless a
small neutral extraction is necessary to make this method import-safe.

### 5.2 Generalize the adapter's review-operation mapping without breaking Threat

D.2A's DungeonMind adapter currently maps every authority operation through a
Threat-named/hash-scoped review-operation derivation. A second client must not
pretend its publications are Threat operations.

Introduce a storage-neutral product operation namespace/family at the port
boundary, for example:

```text
operation_namespace = "threat" | "worldbuilding"
```

or an equivalent closed value.

Required compatibility rule:

> **Threat publication must continue to derive exactly the same DungeonMind
> review-operation ids as D.2A so previously published Threat operations remain
> recoverable.**

The implementation may keep `derive_threat_review_operation_id(...)` as the
historical compatibility branch and add a worldbuilding mapping. Do not silently
change Threat's hash schema while “generalizing” the function.

Worldbuilding's authority operation identity must be deterministic from sealed
pre-write authority, such as:

```text
world_id + plan_id + plan_digest
```

It must be stable across response loss, process restart, and exact retry, and
must not depend on the published child revision.

### 5.3 Do not force generic child verification in this slice

`WorldGraphExpectedChildFacts` / `verify_child` is currently Threat-shaped.
D.2B does not need to rewrite the entire D.2A verification contract merely for
symmetry.

Worldbuilding may verify its child by composing:

- the exact `WorldGraphPublicationReceipt`;
- `read_revision(world_id, published_revision_id)`;
- a pure worldbuilding assertion→expected-fact verifier.

If a genuinely small generic publication-verification primitive emerges, it may
be added. Rewriting Threat verification for aesthetic purity is out of scope.

---

## 6. Worldbuilding plan authority: introduce a native-safe v2

The current `dmb_worldbuilding_write_plan_v1` assumes the graph parent also pins
identity state. That is false under DungeonMind authority.

D.2B therefore introduces a versioned successor rather than silently changing
v1 semantics:

```text
dmb_worldbuilding_write_plan_v2
```

The exact model names may follow repository convention. Required difference:
plan authority includes the identity snapshot used at prepare.

Conceptually:

```text
plan.effect.identity_authority = {
  schema: "dmb_worldbuilding_identity_snapshot_v1",
  decisions: [ ... exact serializable decision records used at prepare ... ]
}
```

The snapshot is part of canonical effect/digest/plan identity. It is not
presentation metadata.

### 6.1 v1 disposition

In `dungeonmind` authority mode, a response-carried v1 plan has no sealed
identity authority and therefore cannot be safely reconstructed.

Required behavior:

```text
v1 confirm in dungeonmind mode
  → fail closed
  → named legacy/reprepare error
  → zero publication
  → never hydrate/reopen Buddy graph for compatibility
```

A freshly prepared plan emits v2. There is no durable plan registry requiring a
migration: callers re-prepare.

Explicit non-production `buddy_files` tests/tools may retain a bounded legacy
adapter only if existing repository policy requires it, but production
DungeonMind confirmation must never route v1 through Buddy graph state.

### 6.2 Preserve rebuild-as-verify

D.2B does not replace worldbuilding's existing trust boundary with “the browser
sent a digest.” Confirm still:

1. re-resolves the exact ExtractionRun/source facts server-side;
2. loads the immutable graph parent through authority;
3. reconstructs identity semantics from the plan's sealed identity snapshot;
4. rebuilds the expected write plan/effect from the original dispositions;
5. requires canonical equality of plan id/digest/decision digest/effect;
6. materializes the contribution from the rebuilt authority, never directly
   from unverified client assertion bodies.

The identity snapshot follows the accepted D.1 sealed-snapshot model. Malformed,
unsupported, invented, or non-reconstructable decision records fail closed.
If implementation discovers that preserving the existing worldbuilding
rebuild-as-verify adversarial guarantees requires a stronger durable/signed
prepare capability than D.1 provides, stop and re-brief rather than adding a
hidden plan registry.

---

## 7. Refactor the plan builder from stores to mutation context

`src/graph_memory/worldbuilding_write_plan.py` should no longer require a
`Path`/World Graph root or `UnionSupergraphStore` to implement existing-world
prepare semantics.

Replace store-shaped authority inputs with
`WorldGraphMutationContext` (or a narrowly derived pure value view).

Required semantic preservation:

### create-new

At the sealed parent/identity snapshot:

- candidate-derived object id must not exist in `context.objects`;
- candidate-derived object id must not be an active identity redirect source;
- conflict remains `new_node_id_conflict` / equivalent stable product error;
- no current-head or filesystem lookup occurs inside the pure builder.

### bind-existing

At the sealed parent/identity snapshot:

- target must exist;
- redirected/merged-away targets are refused with the existing canonical target
  diagnostic where available;
- rejected/retracted and noncanonical provisional identities remain invalid;
- target kind compatibility remains unchanged;
- alias ownership used by support assertion construction comes from the
  mutation context, including identity merge side effects;
- candidate semantic validation remains unchanged.

### parent/head admission

The pure builder should receive a context already containing:

```text
revision_id == expected parent
head_revision_id == head observed for prepare
```

and fail stale if the expected parent is not the observed current head. It must
not open storage itself to prove this.

### contribution value contracts

`GraphContribution`, `GraphContributionAssertion`, and mapping helpers may remain
Buddy-owned product value contracts in this slice even if they currently live
under `graph_memory.kernel.*`. Runtime graph opening/loading/merging is the
D.2B target. D.3 owns final pure-value namespace relocation unless bounded work
is required to keep imports runtime-free.

---

## 8. Extract existing-world worldbuilding orchestration from `extract_promote.py`

Create a narrow service, preferred shape:

```text
apps/live_control_server/services/worldbuilding_graph_publication.py
```

It owns existing-world:

- prepare;
- confirm;
- authority error → product error mapping;
- deterministic authority operation id;
- recover/publish sequencing;
- post-publish worldbuilding child verification.

`extract_promote.py` may retain thin delegates so route imports and unrelated
exact-run/first-world behavior do not churn.

Do not move:

- first-world admission/materialization;
- recap exact-run prepare/confirm;
- source URI policy unrelated to worldbuilding;
- general ExtractPromote error/model architecture.

The purpose is to give D.2B and D.2C separate implementation ownership, not to
create a new “publication framework.”

---

## 9. Prepare semantics

For one `WorldbuildingWritePlanPrepareRequest`:

1. resolve and validate the exact worldbuilding ExtractionRun exactly as today;
2. resolve candidate preview/source lineage exactly as today;
3. obtain the requested parent mutation context from `WorldGraphAuthority`;
4. prove requested parent is still the public head at prepare;
5. construct the v2 plan from the mutation context and explicit dispositions;
6. seal the identity snapshot from that exact context into canonical plan effect;
7. return the inert plan; no World Graph publication occurs.

Prepare must succeed with:

- Buddy World Graph root missing;
- Buddy Kernel open/load functions exploded;
- DungeonMind as the only production graph/identity authority.

Authority unavailable or parent unreadable fails closed with the existing
worldbuilding error family. No file fallback.

---

## 10. Confirm, publication, retry, and uncertain outcome

D.2B adopts D.2A's durable authority safety algebra rather than reproducing the
old filesystem-specific “retry becomes stale parent” implementation detail.

### 10.1 Rebuild before mutation

Confirm first rebuild-verifies the v2 plan against:

- server-resolved run/source authority;
- immutable graph parent from the port;
- the plan's sealed identity snapshot.

No mutation occurs before this succeeds.

### 10.2 Derive one stable authority operation id

Derive a deterministic worldbuilding operation id from the verified sealed plan.
Persisting a separate Buddy commit ledger is **not** required in this slice: the
response-carried plan already provides deterministic immutable operation input,
and DungeonMind provides durable terminal publication recovery.

Do not add a worldbuilding plan/commit filesystem registry merely to mimic
Threat's product-state lifecycle.

### 10.3 Recover before publishing

After rebuild verification:

```text
recover(world, namespace=worldbuilding, operation_id, expected_parent, contribution)
```

If one exact terminal publication exists and its expected parent + reviewed
contribution/review intent match, return the same published child as an
idempotent product result.

If recovered authority contradicts the current verified plan, fail integrity.
Never choose a publication by operation id alone.

### 10.4 No terminal publication exists

Only then prove current head still equals the sealed expected parent and call
`publish(...)` exactly once.

If head advanced first, return stale-parent without mutation. Do not repin.

### 10.5 Uncertain authority response

If `publish` throws after the commit point may have occurred:

- do not issue a blind second publish;
- call `recover` with the same namespace/id/expected parent/contribution;
- exact recovered terminal publication becomes success;
- contradictory publication is integrity failure;
- only proven absence permits the existing bounded retry behavior.

### 10.6 Exact retry becomes explicitly idempotent

The historical Kernel route reported a successful plan's second confirm as
`stale_parent_revision` because the head had advanced. That implementation
cannot distinguish ordinary retry from a lost first response.

Under durable DungeonMind recovery, the correct native contract is:

```text
same verified plan + same operation id + existing exact publication
  → already_applied
  → same child revision
  → zero second finalization/publication
```

This is an intentional D.2B contract amendment required for safe uncertain-outcome
recovery. Version the confirm response/model if necessary; do not silently
reinterpret the old enum.

A distinct plan prepared at an old parent remains stale and fails closed.

---

## 11. Native child verification

Worldbuilding confirmation must stop using Buddy replay/rebuild equivalence as
publication truth.

For a known DungeonMind publication, prove:

1. receipt world and expected parent equal the verified plan;
2. published child parent equals the sealed parent;
3. reviewed contribution identity/digest is bound to the exact materialized
   rebuilt contribution;
4. authority accepted assertion identities match the World-Graph-expressible
   accepted assertions expected from the plan;
5. an exact read of the child represents the accepted worldbuilding object and
   relationship facts required by the effect;
6. rejected assertions, deferred candidates, and unresolved mentions remain
   product/contribution metadata and are reported from the verified plan rather
   than invented as child graph facts.

Unlike D.2A Threat mechanics, D.2B has no pre-authorized “field-class D” carve-out
for ordinary worldbuilding assertions. If the DungeonMind materializer cannot
represent a worldbuilding fact required by the verified accepted effect, stop
with an exact semantic-gap report. Do not silently filter it and do not hydrate
Buddy state to fill it.

`published_audit_degraded` may remain only for a known committed publication
whose native verification cannot currently complete because authority is
unavailable. It must never make the operation publishable again.

---

## 12. API compatibility and versioning

Keep route ownership stable:

```text
POST /api/live/extract-promote/worldbuilding/prepare
POST /api/live/extract-promote/worldbuilding/confirm
```

Expected API changes are limited to the authority contract required by D.2B:

- v2 write plan carrying sealed identity authority;
- confirm request accepting the v2 plan;
- confirm receipt able to represent `already_applied` safely.

Do not redesign worldbuilding review UX, disposition names, candidate schema,
source profile, or route layout.

Existing exact-run `/confirm` must continue to reject worldbuilding plan schemas.
First-world schemas/routes remain unchanged.

---

## 13. APP-STATE parallel-lane contract

APP-STATE AS1 may run concurrently with D.2B.

D.2B's lease must remain disjoint from AS1's known ownership.

### D.2B must not edit

```text
pyproject.toml
uv.lock
src/application_state/**
apps/live_control_server/routes/workspace_documents.py
apps/live_control_server/services/tiptap_markdown_write.py
apps/live_control_server/services/workspace_document_registry.py
Docs/Design/ARCHITECTURE-application-state-layer.md
Docs/Roadmaps/ROADMAP-application-state.md
Docs/Plans/HANDOFF-APP-STATE-*.md
Docs/Plans/STEWARDS-ANCHOR-application-state.md
```

D.2B does not need new dependencies. DungeonMind/Postgres support already exists.

### Runtime/database isolation

D.2B PostgreSQL integration tests use only an isolated CUTOVER test database via
`DMB_CUTOVER_TEST_DATABASE_URL` or the existing equivalent.

They must never use:

```text
dungeonmind_cutover_live
DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL pointing at operator live state
DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL
DMB_APPLICATION_STATE_TEST_DATABASE_URL
```

APP-STATE and CUTOVER may share a physical Postgres server but not a logical
product database, transaction, migration tree, or test-state namespace.

If implementation unexpectedly needs `pyproject.toml`, `uv.lock`, central server
bootstrap, or another AS1-leased path, stop and serialize/transfer that path.
Do not edit first and rely on Git conflict resolution.

---

## 14. D.2C collision boundary

D.2C is a named successor, not a parallel implementation lane.

D.2B must not modify:

```text
apps/live_control_server/services/first_world_graph.py
first-world plan/materialization behavior
first-world route semantics
first-world API schemas except a mechanically unavoidable shared import with no behavior change
```

D.2B may leave `extract_promote.py` with a thin first-world path untouched.

After D.2B, D.2C re-anchors and decides the correct initialization capability.
The likely shape is an explicit initialization authority, not
`publish(expected_parent="EMPTY")`; this handoff does not pre-design it.

---

## 15. Implementation write lease

The implementation PR's HANDOFF §4 write lease is:

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/graph_memory/worldbuilding_write_plan.py` | replace Buddy store/root authority inputs with storage-neutral mutation context; v2 identity snapshot; preserve disposition/mapping semantics |
| Create | `apps/live_control_server/services/worldbuilding_graph_publication.py` | own existing-world worldbuilding prepare/confirm authority orchestration |
| Modify | `apps/live_control_server/services/extract_promote.py` | thin delegation only; remove mounted worldbuilding Kernel merge/root coupling; leave first-world/recap unchanged |
| Modify | `apps/live_control_server/models/extract_promote.py` | versioned worldbuilding plan/confirm models and `already_applied` receipt contract |
| Modify | `apps/live_control_server/ports/world_graph_authority.py` | exact mutation-context capability + operation namespace/family required by second client |
| Modify | `apps/live_control_server/integrations/dungeonmind/world_graph_authority_adapter.py` | native mutation context, worldbuilding operation mapping, publish/recover support |
| Modify | `apps/live_control_server/integrations/dungeonmind/world_graph_writes.py` | reuse/factor D.1 identity-context primitives and add worldbuilding-compatible review-operation mapping where necessary; D.1 behavior unchanged |
| Modify | `apps/live_control_server/integrations/buddy_files/world_graph_authority_adapter.py` | satisfy the extended port for explicit non-production file mode without expanding production fallback |
| Modify | `tests/test_worldbuilding_write_plan.py` | pure context-based plan semantics, v2 sealing, legacy refusal |
| Modify | `tests/test_live_extract_promote_api.py` | route contract and recap/first-world regressions |
| Create | `tests/test_cutover_worldbuilding_authority_port.py` | fake-port / physical-absence / identity-drift product tests |
| Create | `tests/test_cutover_worldbuilding_authority_port_integration.py` | isolated PostgreSQL parent→child/retry/recover/stale/native verification witness |
| Modify | `Docs/Plans/HANDOFF-CUTOVER-threat-authority-port.md` | backward-looking D.2A completion/archive truth only |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | D.2A DONE + D.2B active predecessor sync |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | same backward-looking CUTOVER state sync |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-cutover.md` | D.2A merge/review truth + D.2B dispatch anchor |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md` | byte-identical tracker mirror |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md` | byte-identical roadmap mirror |

### Bounded discovery exception

```text
Directory: tests/
Maximum additional paths: 4
Allowed: owning worldbuilding/CUTOVER regression modules needed to prove §18
Decision rule: only when the guarantee already exists in that test owner's domain

Directory: apps/live_control_server/
Maximum additional paths: 2
Allowed: __init__/export or narrow error-mapping helper required by the extracted service
Decision rule: compile/import necessity only; no new product surface
```

A required production path outside this lease is a stop report.

The following are **not** implicitly leased:

```text
apps/live_control_server/routes/extract_promote.py
pyproject.toml
uv.lock
src/application_state/**
apps/live_control_server/services/first_world_graph.py
apps/live-control-ui/**
Docker/compose files
DungeonMind repository source
```

If route code truly requires modification rather than continuing to call the
same service names/models, stop and request a bounded lease amendment before edit.

---

## 16. Explicitly out of scope

- APP-STATE AS1 or any Buddy application-state PostgreSQL migration;
- `worldbuilding_source` WorkObject migration (APP-STATE AS6+ candidate);
- first-world/bootstrap migration;
- Graph Review D.1 redesign;
- Threat D.2A semantic changes;
- generic publication framework or generic database middleware;
- worldbuilding UI/Graph Review UX redesign;
- extraction prompt/profile improvements;
- identity merge/split authoring UI;
- live Eldyrwild mutation;
- final `graph_memory.kernel` / `world_supergraph` / `union_supergraph` namespace deletion;
- new Postgres dependencies or migration trees.

---

## 17. Failure contract

Map authority failures into stable worldbuilding product failures.

Required distinctions:

```text
authority unavailable
world/head not initialized
exact revision unavailable
stale expected parent
legacy v1 plan / reprepare required
identity snapshot malformed or inexpressible
bind target missing / redirected / invalid
create-new occupancy conflict
plan rebuild verification failure
authority operation id conflict / contradictory recovery
DungeonMind semantic mapping inexpressible
known committed but verification degraded
```

No raw psycopg/repository/DungeonMind infrastructure exception reaches the HTTP
boundary.

No failure silently falls back to Buddy graph storage.

---

## 18. Evidence required to merge

Evidence must exercise the owning boundary, not only helpers.

### 18.1 Pure plan/context tests

Prove `build_worldbuilding_write_plan` and verifier behavior with a
`WorldGraphMutationContext`, no filesystem root:

- create-new free id;
- create-new object conflict;
- create-new active redirect-source conflict;
- bind-existing success;
- bind-existing missing target;
- redirected/merged-away target refusal;
- rejected/retracted target refusal;
- provisional target refusal;
- wrong kind refusal;
- alias ownership preserved for bind support;
- stale expected parent from context head mismatch;
- v2 identity snapshot included in canonical plan digest;
- v1 DungeonMind confirm requires reprepare.

### 18.2 Prepare physical-absence witness

With DungeonMind authority/fake port mounted:

- Buddy world root does not exist;
- `kernel.open_current_world_graph` / `load_world_graph_revision` explode if called;
- real `prepare_worldbuilding` succeeds from port mutation context;
- returned parent is exact;
- returned v2 plan contains the identity snapshot used for decisions.

### 18.3 Identity drift without graph-head advance

Adversarial sequence:

```text
D_A = public graph head
I_0 = identity ledger snapshot
prepare v2 plan at D_A + I_0
append identity decision I_1 without advancing graph head
live mutation context at D_A now resolves differently
confirm original plan
```

Required result:

- confirm rebuild uses sealed I_0 semantics;
- it does not substitute I_1;
- either the original plan publishes exactly as prepared or another independent
  invariant (for example stale graph parent) legitimately blocks it;
- no Buddy graph is opened.

Also test malformed/unsupported sealed identity records fail closed.

### 18.4 Isolated PostgreSQL D_A → D_B publication

Against disposable CUTOVER PostgreSQL:

```text
D_A = current DungeonMind head
prepare worldbuilding plan @ D_A
confirm
D_B = DungeonMind child
D_B.parent == D_A
```

Prove:

- one finalized publication;
- exact deterministic worldbuilding operation namespace/id;
- exact reviewed contribution binding;
- expected accepted worldbuilding assertion set;
- expected materialized objects/relationships on D_B;
- Buddy graph runtime/root unused.

### 18.5 Exact retry / durable recovery

Repeat the identical confirmed v2 plan:

- product result is `already_applied` (or exact versioned equivalent);
- same D_B;
- same authority operation id;
- no second DungeonMind revision;
- no second finalized publication;
- receipt assertion ids/plan identity remain exact.

Adversarial conflicts:

- same authority operation id + changed expected parent → integrity failure;
- same authority operation id + changed rebuilt contribution/digest → integrity failure.

### 18.6 Uncertain publish response

Inject a failure after DungeonMind commits D_B but before the service receives a
usable publication response.

The worldbuilding service must:

- recover the exact terminal publication using the same operation id;
- return/derive the same D_B;
- create no second revision/finalization;
- remain independent of Buddy graph storage.

This may be same-call recovery or a replayed HTTP call; the proof must exercise
`confirm_worldbuilding`, not merely direct adapter `publish/recover` calls.

### 18.7 Stale distinct plan

Prepare plan P at D_A. Advance head by an unrelated publication D_X without
creating P's operation id. Confirm P:

- stale-parent refusal;
- zero P publication;
- no hidden repin;
- no Buddy fallback.

### 18.8 Native child verification

For committed D_B, explode if called:

```text
kernel.open_current_world_graph
kernel.load_world_graph_revision
kernel.merge_contribution_to_revision
rebuild_from_contributions
Buddy Kernel projection/hydration helpers
```

Verification still proves the expected accepted worldbuilding facts from the
DungeonMind receipt + exact child revision.

### 18.9 Complete mounted lifecycle physical absence

Drive the actual server/service path:

```text
resolve run
prepare worldbuilding v2
confirm
read exact receipt
exact retry
```

with Buddy graph storage physically absent and runtime graph APIs exploded.

### 18.10 Regression proof

Run and record focused regressions for:

- D.1 native governed Graph Review write path;
- D.2A Threat authority port, including lost-receipt recovery;
- existing first-world tests unchanged;
- recap extract-promote prepare/confirm unchanged;
- explicit `buddy_files` tests that remain supported until D.3.

### 18.11 Static dependency proof

The mounted DungeonMind worldbuilding service path must have no runtime imports
of:

```text
graph_memory.kernel as kernel
graph_memory.world_supergraph
UnionSupergraphStore
world_graph_root used as production authority
```

Pure contribution/value-model imports under historical namespaces must be
listed explicitly as D.3 relocation debt.

### 18.12 Parallel lease proof

At handback:

```text
git diff --name-only <D2B_BASE>...HEAD
```

must stay inside §15/bounded discovery.

Specifically assert no changes to:

```text
pyproject.toml
uv.lock
src/application_state/**
workspace-document persistence
first_world_graph.py
```

unless an operator-authorized lease amendment was recorded before the edit.

---

## 19. Stop conditions

Stop and re-brief rather than guessing when any of these occur.

### 19.1 DungeonMind cannot express an accepted worldbuilding fact

Name the exact assertion/property/relationship semantic gap. Do not silently
filter it, coerce it, or hydrate Buddy state.

### 19.2 Identity snapshot cannot preserve rebuild authority safely

If the accepted D.1 sealed-snapshot pattern is insufficient for worldbuilding's
rebuild-as-verify trust boundary, stop. Do not create an undocumented filesystem
plan registry, hidden signing key, or APP-STATE dependency inside D.2B.

### 19.3 Port starts becoming generic CRUD/database middleware

Connections, SQL, arbitrary transactions, repository bundles, and generic
insert/update/query methods do not belong in `WorldGraphAuthority`.

### 19.4 Threat operation recovery would change

Any operation-id generalization that would make D.2A's already-published Threat
operations unrecoverable is a blocker. Preserve exact historical Threat mapping.

### 19.5 D.1 materially changes

If sharing mutation-context/publication helpers would alter D.1 accepted
semantics, keep D.1 stable and duplicate a bounded adapter primitive if needed.
Do not destabilize #634 for abstraction purity.

### 19.6 First-world enters the implementation diff

Stop and split. D.2C owns initialization.

### 19.7 APP-STATE write lease collision

Stop and report contested path, current owner, why D.2B needs it, and whether a
seam split can avoid it. Do not edit first.

### 19.8 A durable Buddy worldbuilding commit registry becomes required

That is a second persistence contract. Re-brief it separately; do not smuggle it
into this migration.

---

## 20. Backward-looking predecessor sync required in the implementation PR

Before claiming D.2B dispatch complete, the implementation PR must atomically
record already-true D.2A facts:

```text
Buddy PR #637 merged
merge: 28daea7e90b396c1b9e9b5fcc12a0b9427674d8c
accepted head: 3c74dc40dbcaf46b316e379e5a703e66570d2dea
review cycles: 3
D.2A: DONE
D.2B: active/in-flight (not DONE)
D.2C: READY/BLOCKED only according to then-current truth
D.3: remains blocked on D.2B + D.2C
```

Sync the tracker/roadmap mirrors byte-identically.

Do not invent D.2B's future merge SHA/review count or mark D.2C complete.

---

## 21. Merge-ready acceptance rubric

- [ ] One independently useful capability: existing-world worldbuilding authority migration.
- [ ] Prepare and confirm use `WorldGraphAuthority` in DungeonMind production mode.
- [ ] Worldbuilding plan v2 binds exact graph parent + identity snapshot.
- [ ] Confirm rebuilds from sealed identity semantics, not today's live ledger.
- [ ] No mounted worldbuilding path opens/loads/merges/rebuilds Buddy graph in DungeonMind mode.
- [ ] Deterministic worldbuilding operation namespace/id supports exact recovery.
- [ ] Threat operation-id mapping remains backward-compatible.
- [ ] Exact retry returns same child with zero second publication.
- [ ] Distinct stale plan fails closed without repin.
- [ ] Native child verification proves accepted worldbuilding facts.
- [ ] No silent DungeonMind semantic filtering of required worldbuilding assertions.
- [ ] D.1 Graph Review and D.2A Threat regressions remain green.
- [ ] First-world behavior is unchanged.
- [ ] APP-STATE write/runtime/database ownership is untouched.
- [ ] Changed paths stay inside §15 / authorized bounded discovery.
- [ ] D.2A predecessor state-sync lands atomically with implementation.

---

## 22. Exit state and next dispatch

After D.2B, repository truth should be:

```text
Production graph reads
  → DungeonMind native

Graph Review governed existing-world writes
  → DungeonMind native (D.1)

Threat publication
  → WorldGraphAuthority → DungeonMind (D.2A)

Existing-world worldbuilding prepare/confirm
  → WorldGraphAuthority → DungeonMind (D.2B)

Buddy application state
  → separate APP-STATE lane

Remaining mounted Buddy graph writer
  → first-world/bootstrap only
```

Then re-anchor and design/dispatch D.2C around the actual post-D.2B port.

D.2C's design question is intentionally left open:

> **What is the correct DungeonMind authority capability for creating the first
> published world revision when there is no legitimate expected parent?**

D.2B must not answer that by inventing an empty-parent sentinel.

After D.2C, D.3 can prove zero mounted Buddy graph-runtime consumers and delete
the obsolete graph engine/compatibility namespaces.

---

## 23. Implementation-agent first pass

Before editing:

1. read `AGENTS.md` and the external-agent PR/review loop;
2. re-anchor to the exact current `main` containing this accepted handoff;
3. inspect active PRs/worktrees and confirm §15 does not collide with APP-STATE;
4. inventory the actual mounted worldbuilding route → service → plan-builder →
   graph-runtime call graph;
5. read D.2A port/adapter and D.1 mutation-context/identity-sealing code;
6. write failing port/mutation-context tests before changing worldbuilding logic;
7. refactor worldbuilding plan construction to storage-neutral context;
8. extract the existing-world worldbuilding service seam without touching
   first-world behavior;
9. add v2 plan + operation namespace/recovery contract;
10. run fake-port physical-absence and isolated PostgreSQL witnesses;
11. rerun D.1 + D.2A regressions;
12. perform the backward-looking D.2A tracker/roadmap/steward sync atomically;
13. hand back exact base/head SHAs, changed paths, commands/counts, review-ready
    evidence, remaining D.3 pure-value namespace debt, and any stop-condition
    decisions.

The implementation PR's claim is deliberately narrow:

> **Existing-world worldbuilding no longer knows how World Graph persistence
> works. It knows only the exact graph + identity authority capability required
> to prepare, publish, recover, and verify one reviewed worldbuilding effect.**
