---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / D.2C1 — DungeonMind reviewed first-world initialization authority
  - Flow: CUTOVER
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-reviewed-first-world-initialization.md
  - Implementation repository: Drakosfire/DungeonMind
  - Buddy predecessor: PR #640 / D.2B worldbuilding authority-port migration

  ## Outcome
  Add a DungeonMind-owned, zero-parent reviewed first-world initialization unit of
  work. Against a pristine world, one exact reviewed command must atomically
  persist the required source lineage, one reviewed GraphContributionV2, one
  internally materialized dm_union_graph_v6 initial revision whose parent is
  genuinely null, the new head, and a durable reviewed-initialization receipt.
  Exact retry/recovery returns that same receipt with zero second initialization.

  ## Non-goals
  - do not repurpose existing-world adoption
  - do not call ordinary existing-parent publication with a fake/EMPTY parent
  - do not accept caller-supplied graph payload bytes as first-world authority
  - do not change DungeonMind read behavior or Buddy product code in this PR
  - do not implement D.3 demolition

  ## Required proof
  - pristine PostgreSQL ∅ → D_0 with D_0.parent_revision_id is null
  - graph payload is materialized by DungeonMind from the reviewed contribution
  - source/revision/contribution/head/receipt commit atomically
  - exact retry and lost-response recovery return the same receipt/revision
  - same world + different initialization intent fails closed with zero mutation
  - exact receipt remains recoverable after a later legitimate child advances head
  - no existing_world_adoptions row is written
  - existing-world adoption and governed D_A → D_B publication regressions stay green
---

# HANDOFF — CUTOVER D.2C1: DungeonMind reviewed first-world initialization authority

**Created:** 2026-08-25  
**Status:** READY FOR IMPLEMENTATION  
**Workstream / flow:** `CUTOVER`  
**Direction:** DESIGN → CODE → REVIEW  
**Implementation repository:** `Drakosfire/DungeonMind`  
**Buddy design/re-anchor base:** `6ef7aefa741a82f512f5918b460cbee1a427cae4` — merge of Buddy PR #640  
**Buddy D.2B accepted head:** `caa9d84e4431db1b90ea58dab2e74d270fbcffee`  
**Buddy D.2B review cycles:** 3; Cycle 3 PASS-equivalent review `5020798053`  
**DungeonMind implementation base:** `c5d3688587b0f5d506e0f7d64f33eb0628bac896` — current `main`, merge of PR #45  
**Suggested DungeonMind branch:** `cutover/reviewed-first-world-initialization`  
**Suggested PR title:** `CUTOVER: add reviewed first-world initialization authority`  
**Predecessor:** Buddy D.2B / PR #640  
**Successor:** Buddy D.2C2 mounted first-world authority migration, then D.3 graph-engine deletion

> **Dispatch ruling:** D.2C decomposes into a provider prerequisite and a Buddy
> consumer migration. This PR is D.2C1: DungeonMind gains the missing semantic
> authority for creating a genuinely new reviewed world. D.2C2 then moves the
> mounted Buddy first-world prepare/confirm path onto that authority.
>
> Do not force first-world creation through the existing-parent publication API.
> There is no legitimate expected parent. Do not use `"EMPTY"`, a synthetic
> revision, or an overloaded existing-parent contract merely to reuse D.2A/D.2B.
>
> Do not repurpose `ExistingWorldAdoption`. That application service is durable
> migration provenance for an already-materialized world. A newly reviewed world
> must not be recorded forever as if it were imported historical state.

---

## 1. Mission and merge-ready invariant

Add one DungeonMind application capability for this state transition:

```text
pristine world
  no head
  no graph revisions
  no graph contributions
  no identity decisions
  no source history for W

+ one exact reviewed initialization command
  source lineage
  reviewed contribution
  semantic profile
  deterministic initialization identity

→ one atomic DungeonMind initialization

D_0.parent_revision_id == None
head == D_0
reviewed contribution durable
source lineage durable
reviewed-initialization receipt durable
```

The merge-ready invariant is:

> **DungeonMind can atomically initialize a pristine world from one exact reviewed
> contribution without caller-supplied graph bytes, without adoption semantics,
> and without a fabricated parent; exact replay/recovery returns the same durable
> initialization receipt and revision with zero second initialization.**

This PR is independently useful even before Buddy is repinned: an in-process
DungeonMind caller can exercise the complete authority against PostgreSQL.

---

## 2. Why D.2C1 exists

Buddy's remaining mounted first-world path is still entirely legacy graph
runtime authority:

- `classify_world_graph_state(...)` inspects Buddy filesystem head/revision state;
- `materialize_first_world_plan(...)` constructs a Kernel empty technical baseline;
- `confirm_first_world(...)` calls `initialize_reviewed_world(...)` from
  `graph_memory.kernel.reviewed_world_initialization`;
- the legacy transaction stages an empty filesystem world, merges the reviewed
  contribution, verifies/rebuilds it, writes a reviewed initialization receipt,
  and atomically renames the staged world into place.

D.2B deliberately did not touch this path because existing-world publication
and first-world creation have different state machines.

DungeonMind already proves the **storage primitive** required here:

- `PostgresWorldGraphRepository` accepts a real `PublishRevisionCommand` whose
  `parent_revision_id=None` and `expected_parent_revision_id=None` when the
  current head is genuinely absent;
- `PostgresExistingWorldAdoptionRepository.adopt(...)` proves the database can
  atomically lock a pristine world, persist source/history records, publish a
  parent-null graph revision, advance head, write a terminal receipt, and replay
  exactly.

But DungeonMind does **not** currently expose the correct semantic application
boundary. Its public zero-head UoW is `ExistingWorldAdoption`, which consumes an
already-materialized graph payload and records migration/adoption provenance.
That is the wrong authority for new first-world authoring.

D.2C1 fills exactly that gap.

---

## 3. Locked design decisions

### 3.1 One real first authoritative revision, not a persisted empty-baseline revision

The DungeonMind-native first world is one revision:

```text
D_0.parent_revision_id = None
D_0 = materialize(reviewed contribution over an empty v6 value baseline)
```

The old Buddy `baseline_revision_id → initial_head_revision_id` topology is a
Kernel implementation detail, not a domain invariant worth reproducing in the
new authority. D.2C2 will version/adapt the Buddy product receipt if necessary;
D.2C1 must not create a meaningless durable empty revision solely to preserve an
obsolete internal shape.

An **in-memory empty v6 value** used as materialization input is legitimate. A
persisted or governance-visible fake parent is not.

### 3.2 DungeonMind materializes the graph; the caller does not supply it

The reviewed initialization command carries reviewed facts and source authority,
not a `graph_payload` field.

DungeonMind constructs a strict empty `UnionGraphV6Payload` using:

```text
world_id
semantic_profile
relationship_endpoint_aspect_schema = dm_relationship_endpoint_aspect_v1
objects = []
relationships = []
evidence_refs = []
```

and applies the reviewed contribution under first-world rules. The resulting
payload is parsed/revalidated through the pinned v6 reader before publication.

This is the central distinction from `ExistingWorldAdoption`: adoption accepts
sealed already-materialized world bytes; reviewed initialization authors the
first World Graph from reviewed facts.

### 3.3 No identity matching in a pristine world

First-world initialization has no existing graph identity to bind against.
Accepted object facts must create new identities. The command fails closed if
its reviewed contribution attempts existing-object/merge semantics.

At minimum reject:

- non-empty `identity_decision_ids`;
- corrections targeting prior contributions;
- accepted identity outcomes that mean `confirm_existing` / `resolved_existing`;
- accepted edges whose endpoints are not created by the same reviewed initial
  contribution;
- any mechanics/statblock binding already excluded by the v6 World Graph seam.

Rejected assertions remain durable review history but do not materialize.

### 3.4 Preserve source/evidence closure atomically

A first authoritative graph whose evidence cannot resolve through DungeonMind's
source authority is not complete.

The command therefore carries the exact `SourceArtifactV2` / `SourceRevisionV2`
records required by the reviewed contribution and accepted evidence. Validate:

- every source record belongs to the command world where the contract requires
  world binding;
- source revision → artifact ownership closes exactly;
- contribution/assertion/evidence source identities resolve inside the command;
- duplicate durable ids with contradictory payloads fail closed;
- no source record is silently looked up from unrelated current world state to
  repair an incomplete command.

The PostgreSQL UoW writes these records in the same transaction as contribution,
revision/head, and receipt.

### 3.5 Durable first-world provenance is its own contract family

Do not insert a row into `existing_world_adoptions` and do not use adoption
schema names.

Add a reviewed-initialization contract family with explicit semantic names,
preferred shape:

```text
dm_reviewed_world_initialization_command_v1
dm_reviewed_world_initialization_receipt_v1
```

The receipt is durable historical proof of the exact genesis operation. It must
remain retrievable after later legitimate child revisions advance the current
head.

### 3.6 Exact replay is receipt-first, not inferred from head

The operation has one deterministic caller-supplied initialization identity,
for example `initialization_id` / `operation_id`.

Replay algebra:

```text
same world + same initialization id + exact same bound command
  → same receipt
  → same D_0
  → zero new rows

same world + different initialization intent
  → conflict / already initialized
  → zero mutation

same initialization id reused for another world
  → idempotency conflict
  → zero mutation
```

A current head existing is not by itself proof of replay. The receipt is.

### 3.7 Uncertain outcomes recover from durable authority

If the transaction may have committed but the caller does not receive the
response, a retry probes the reviewed-initialization receipt first. An exact
stored receipt returns success. Contradictory durable state fails integrity.

Do not issue a blind second initialization after an uncertain result.

---

## 4. Proposed public contracts

Names may vary slightly if current DungeonMind naming conventions demand it,
but the semantics may not drift.

### `ReviewedWorldInitializationCommandV1`

Required conceptual fields:

```text
schema_version
initialization_id
world_id
campaign_id | null
source_plan_schema
source_plan_id
source_plan_sha256
semantic_profile: SemanticProfileRef
source_artifacts: list[SourceArtifactV2]
source_revisions: list[SourceRevisionV2]
reviewed_contribution: GraphContributionV2
actor
requested_initialized_at
```

Rules:

- `initialization_id`, world, plan identity, and actor are nonblank and bounded;
- `source_plan_sha256` is content-bound provenance supplied by the caller;
- reviewed contribution world equals command world and is `active`;
- contribution has at least one accepted materializable assertion;
- first-world identity restrictions from §3.3 hold;
- source closure from §3.4 holds;
- semantic profile resolves through the normal DungeonMind registry;
- command does not contain `expected_parent_revision_id` and does not contain a
  graph payload.

The command fingerprint/digest must bind all semantic fields including source
records and the complete reviewed contribution.

### `ReviewedWorldInitializationReceiptV1`

Required conceptual fields:

```text
schema_version
initialization_id
world_id
campaign_id | null
source_plan_schema
source_plan_id
source_plan_sha256
command_sha256
reviewed_contribution_id
reviewed_contribution_sha256
published_revision_id
published_graph_schema = dm_union_graph_v6
published_graph_payload_sha256
accepted_assertion_ids
actor
initialized_at
```

The receipt is immutable. Readback must reconstruct and fingerprint-check it,
and must verify its published revision still exists and agrees with world,
schema, payload digest, and `parent_revision_id=None`.

Do **not** require `published_revision_id == current head` during receipt read;
later descendants are legitimate.

---

## 5. First-world v6 materialization

Create a dedicated pure first-world materializer rather than manufacturing a
normal existing-parent review state.

Preferred shape:

```python
materialize_reviewed_world_initialization_v6(
    command: ReviewedWorldInitializationCommandV1,
    *,
    graph_reader: GraphSnapshotReader,
) -> FirstWorldMaterialization
```

The materializer:

1. creates the empty `UnionGraphV6Payload` value from world + semantic profile;
2. validates the reviewed contribution and source/evidence closure;
3. applies accepted assertions in deterministic order;
4. emits the final graph payload plus exact accepted assertion ids;
5. reparses the final payload with the same pinned v6 reader;
6. never observes a repository, head, adoption receipt, or caller graph bytes.

For the current Buddy first-world producer, accepted `node` + `edge` assertions
are sufficient. Do not generalize first-world semantics merely because the v6
incremental materializer supports more kinds. A narrow v1 contract may admit:

```text
accepted: node, edge
rejected history: any currently valid contribution assertion kind
```

If implementation demonstrates that source/evidence closure requires a narrow
`evidence_ref` accepted form, add only that proven form and record it in tests.

### Node

- subject id required and unique;
- create-new semantics only;
- require a valid profile-qualified `dm_kind` / equivalent normalized v2 field;
- materialize object existence + aliases/evidence using the established v6
  metadata conventions;
- duplicate object ids fail closed.

### Edge

- both endpoints must already be created in the same initial materialization;
- relationship id and profile-qualified predicate follow the existing v6
  governed publication conventions;
- relationship id collision fails closed unless exact replay is already handled
  above the pure materializer.

### Evidence

Reuse the established v6 evidence lifting/fallback rules where they are truly
identical. Extract a bounded pure helper from `review_materialization_v6.py` if
that reduces duplicate logic **without changing D_A→D_B behavior**. Existing
review-publication tests must prove semantic parity after any helper extraction.

Do not refactor the whole v6 materializer for abstraction purity.

---

## 6. PostgreSQL atomic unit of work

Add a dedicated repository/application UoW, preferred shape:

```text
application/reviewed_world_initialization.py
infrastructure/postgres/reviewed_world_initialization.py
```

The PostgreSQL boundary must perform one transaction:

```text
lock world
→ receipt-first replay probe
→ assert pristine target
→ validate/materialize exact command
→ insert source artifacts/revisions
→ append reviewed contribution
→ publish D_0 with parent=None / expected_parent=None
→ insert reviewed initialization receipt
→ commit
```

Pristine means, for this world, no pre-existing:

- World Graph head;
- graph revision;
- graph contribution;
- identity decision;
- source artifact owned by the world;
- reviewed-world-initialization receipt;
- existing-world-adoption receipt.

If another writer wins the world lock first, the loser rechecks durable receipt
identity and either returns exact replay or fails closed. It must not overwrite
or adopt the winner's world.

The normal `PostgresWorldGraphRepository` parent-null CAS primitive may be reused
inside this transaction. Do not expose its private in-transaction method to Buddy
or make Buddy coordinate multiple repositories.

### Migration

Current DungeonMind migration head at design time is `0006_existing_world_adoptions.py`.
Add the next Alembic migration for a dedicated reviewed-world-initialization
receipt table (expected `0007_*` unless repository truth changes before dispatch).

Recommended durable columns mirror existing receipt patterns:

```text
world_id                unique / primary ownership key
initialization_id       unique
source_plan_id
source_plan_sha256
command_sha256
reviewed_contribution_id
reviewed_contribution_sha256
published_revision_id
published_graph_schema
published_graph_payload_sha256
initialized_at
schema_version
record_fingerprint
payload jsonb
```

Exact schema is implementation-owned; the invariants above are not optional.

---

## 7. Error semantics

Use typed DungeonMind errors; do not leak psycopg exceptions as product-facing
behavior.

Required classes/reasons can map into existing error families where appropriate:

```text
initialization target not pristine
initialization idempotency conflict
reviewed initialization command invalid/inexpressible
source/evidence closure failure
materialization failure
persistence integrity failure
persistence unavailable
initialization outcome unknown
```

Outcome-unknown is only for a state where durable commit cannot be proved or
ruled out. Exact receipt recovery converts uncertainty to success.

---

## 8. Write lease — DungeonMind implementation PR

The implementation PR owns only the provider capability.

Expected paths:

| Action | Path | Purpose |
|---|---|---|
| Create | `src/dungeonmind/contracts/reviewed_world_initialization.py` | command/receipt contracts |
| Create | `src/dungeonmind/application/reviewed_world_initialization.py` | pure validation/materialization + application UoW |
| Modify | `src/dungeonmind/application/repositories.py` | narrow repository protocol/types |
| Modify | `src/dungeonmind/application/__init__.py` | public export if repository convention requires |
| Create | `src/dungeonmind/infrastructure/postgres/reviewed_world_initialization.py` | atomic PostgreSQL implementation |
| Modify | `src/dungeonmind/infrastructure/postgres/__init__.py` | adapter export/wiring |
| Create | `migrations/versions/<next>_reviewed_world_initializations.py` | durable receipt table |
| Create/Modify | `tests/**reviewed_world_initialization**` | pure/in-memory/Postgres owning-boundary proof |
| Modify if bounded | `src/dungeonmind/application/review_materialization_v6.py` | extract only a proven pure v6 helper shared by first-world materialization |
| Modify if bounded | existing v6 publication tests | prove helper extraction is behavior-preserving |

Explicitly out of scope:

- any `Drakosfire/DungeonMindBuddy` production code;
- Buddy `WorldGraphAuthority` / adapters;
- Buddy `pyproject.toml` or `uv.lock` pin;
- existing-world adoption contract/receipt semantics except regression tests;
- changes to normal existing-parent governed publication semantics;
- read/projection/retrieval behavior;
- APP-STATE;
- D.3 deletion.

If implementation needs a new generic transaction coordinator, graph CRUD API,
or rewrites existing-world adoption to share a broad framework, stop and re-brief.

---

## 9. Required evidence

Evidence must exercise the application/repository owning boundary.

### 9.1 Pure command/materializer

Prove:

- deterministic command digest/fingerprint;
- empty/zero-accepted contribution refused;
- world/source/contribution mismatch refused;
- unresolved source-revision ownership refused;
- accepted existing-identity semantics refused;
- correction/prior-history dependency refused;
- accepted edge with missing initial endpoint refused;
- valid node+edge contribution materializes strict `dm_union_graph_v6`;
- output reparses under pinned semantic profile;
- output graph is derived internally, not accepted from command bytes.

### 9.2 Real PostgreSQL pristine `∅ → D_0`

Against a disposable test database:

```text
no W rows
initialize exact command C
receipt R
D_0 = R.published_revision_id
```

Assert:

- `D_0.parent_revision_id is None`;
- head is exactly `D_0`;
- one reviewed-initialization receipt;
- one durable reviewed contribution with exact digest;
- required source artifact/revision records exist and fingerprint-check;
- accepted assertion ids in receipt equal the durable/materialized accepted set;
- D_0 graph payload contains exactly the expected initial objects/relationships;
- D_0 reparses with the v6 reader;
- zero `existing_world_adoptions` rows for W.

### 9.3 Exact retry

Call initialize again with exact C:

- same receipt;
- same D_0;
- zero new graph revisions;
- zero new contributions/source rows/receipts.

### 9.4 Conflicting initialization

After C succeeds, attempt C2 for same W with different plan/contribution/digest:

- typed conflict/already-initialized failure;
- head remains D_0;
- receipt remains C's receipt;
- zero partial C2 rows.

Also test same initialization id reused for another world fails idempotency.

### 9.5 Lost response / recovery

Inject failure after transaction commit but before caller receives a usable
result. Retry exact C:

- same receipt / D_0;
- no second initialization;
- no outcome-unknown once durable receipt is readable.

Inject failure before commit and prove no partial source/contribution/head/receipt
rows survive.

### 9.6 Receipt survives descendants

After successful initialization, publish one legitimate governed child
`D_0 → D_1` using the existing normal review-publication seam. Then replay/read
initialization C/R:

- initialization receipt remains valid and returns D_0;
- current head may be D_1;
- no attempt to reset head to D_0;
- historical genesis remains distinguishable from current authority state.

### 9.7 Regression proof

Run focused existing suites for:

- existing-world adoption exact replay/conflict/recovery;
- finalized v2/v6 review publication and stale-parent CAS;
- graph repository parent-null + normal parented publication;
- source/contribution persistence integrity;
- migration upgrade from current head.

No existing adoption receipt/schema changes are acceptable merely to make this
new path easier.

---

## 10. Stop / split conditions

Stop and re-brief if any of these becomes necessary:

### 10.1 Caller-supplied graph payload is required

That would collapse reviewed authoring back into adoption semantics. Stop.

### 10.2 A fake persisted baseline/parent is required

A value-level empty materialization input is fine. A governance-visible
`EMPTY`, synthetic parent id, or persisted no-op revision invented only for API
compatibility is not.

### 10.3 Existing-world adoption provenance would be reused

Do not store reviewed first-world initialization as an adoption. Add the narrow
new receipt contract instead.

### 10.4 Existing-parent publication semantics must change materially

Keep D.1/D.2A/D.2B stable. A small pure helper extraction is allowed only with
semantic parity proof.

### 10.5 Identity resolution against pre-existing graph facts becomes necessary

The target is no longer pristine first-world initialization. That is another
capability.

### 10.6 Buddy production code becomes necessary in this PR

Stop. D.2C2 owns the consumer migration after this provider merges.

---

## 11. Successor: Buddy D.2C2

After this DungeonMind PR merges:

1. re-anchor Buddy + DungeonMind;
2. repin Buddy to the exact DungeonMind merge if required;
3. extend the Buddy World Graph authority boundary with a **real initialization
   capability** — either `initialize_world(...)` on the existing authority port
   or a separate narrow `WorldGraphInitializer`, chosen from the concrete D.2C1
   API rather than predicted in advance;
4. extract mounted first-world orchestration from `extract_promote.py` into a
   dedicated service;
5. replace `classify_world_graph_state(world_root, ...)`, empty Kernel baseline,
   `initialize_reviewed_world(...)`, and reviewed-init filesystem receipts with
   DungeonMind authority calls;
6. preserve exact run/source/workspace-lineage rematerialization and first-world
   decision semantics;
7. version/adapt the Buddy confirm receipt honestly if the legacy
   `baseline_revision_id` no longer exists under the native one-revision genesis;
8. prove prepare→confirm→exact retry against isolated PostgreSQL with Buddy graph
   root physically absent and Kernel/world_supergraph entry points exploding;
9. carry the backward-looking CUTOVER state sync for Buddy #640 and this D.2C1
   merge;
10. only then mark D.2C complete and open D.3 demolition.

D.2C2 must not invent a synthetic baseline just to avoid product response
versioning.

---

## 12. Parallel-lane contract

Buddy APP-STATE PR #641 is active at this design re-anchor. Its write lease owns
Plan persistence, `src/application_state/**`, `pyproject.toml`, `uv.lock`, and
workspace-document persistence paths.

D.2C1 is in the separate DungeonMind repository and therefore has no source-path
collision with #641. It also has no shared runtime requirement with Buddy's
application-state database.

For D.2C2, continue treating `workspace_document_registry.py` as APP-STATE-owned
while #641 remains open. First-world may **read** the existing lineage service;
it must not modify that file without an explicit lease transfer/serialization
decision.

---

## 13. State-authority sync

Buddy PR #640 is now merged, but the current Campaign Supergraph tracker/roadmap
and CUTOVER steward anchor still say D.2B is `DOING` and still name the pre-#640
Buddy main.

Do not edit Buddy state authorities from this DungeonMind implementation PR.
The next Buddy implementation consumer, D.2C2, owns the backward-looking atomic
sync and must record:

```text
D.2B / Buddy #640 = DONE
merge = 6ef7aefa741a82f512f5918b460cbee1a427cae4
accepted head = caa9d84e4431db1b90ea58dab2e74d270fbcffee
review cycles = 3
Cycle 3 PASS-equivalent = 5020798053
D.2C decomposed into provider D.2C1 + Buddy consumer D.2C2
D.2C1 exact DungeonMind merge/review truth
D.2C2 = active
D.3 = still blocked on D.2C2
```

Do not mark D.2C done when only the DungeonMind provider exists.

---

## 14. Merge-ready acceptance rubric

- [ ] One capability: DungeonMind reviewed first-world initialization authority.
- [ ] Genuine parent-null initial revision; no fake/synthetic parent.
- [ ] No caller graph payload; DungeonMind materializes strict v6 from reviewed facts.
- [ ] Dedicated reviewed-init contract/receipt; no adoption provenance.
- [ ] Source + contribution + revision/head + receipt commit atomically.
- [ ] First-world identity semantics fail closed against existing/bind behavior.
- [ ] Exact retry returns same receipt/revision with zero second writes.
- [ ] Conflicting initialization fails with zero mutation.
- [ ] Lost-response recovery is receipt-first and exact.
- [ ] Receipt remains valid after head advances to a descendant.
- [ ] Zero existing-world-adoption row for reviewed initialization.
- [ ] Existing-world adoption regressions remain green.
- [ ] Existing-parent v6 governed publication regressions remain green.
- [ ] Migration upgrade proof passes from current migration head.
- [ ] No Buddy production code or APP-STATE scope enters this PR.

When these are true, D.2C1 is `DONE`; D.2C2 becomes the next CUTOVER implementation slice.
