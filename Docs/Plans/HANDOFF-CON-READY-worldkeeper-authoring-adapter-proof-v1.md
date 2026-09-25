---
pr_body_template: |
  ## Handoff pointer
  - Repository: Drakosfire/DungeonMindBuddy
  - Direction: STEWARD → CODE
  - Slice: CON-READY — WorldKeeper authoring adapter proof
  - Handoff: Docs/Plans/HANDOFF-CON-READY-worldkeeper-authoring-adapter-proof-v1.md
  - Design base: 08e4c39967e63bc3b60791748129ca3eaa42f161
  - WorldKeeper WK-5 merge: 8a5efb96b69dc9ca136288ecc80f67c1ed027bd1
  - DungeonMind runtime: 6edb9e40d1dc930f537c66deb1afbd1b99002844
  - V6.1 merge: 7a63c8b39937776ddede24d3d76001ef59fd37c4

  This PR proves the Buddy → WorldKeeper application-intent seam for the
  supported authoring subset. It does not switch production publication.
---

# HANDOFF — CON-READY WorldKeeper authoring adapter proof

**Status:** BLOCKED — custom-predicate authority prerequisite; no adapter implementation yet
**Repository:** `Drakosfire/DungeonMindBuddy`
**Workstream:** `CON-READY / source-to-World authoring`
**Design base:** `08e4c39967e63bc3b60791748129ca3eaa42f161`
**Dispatch main:** `24ceed5d1661f7069faf3833ace641b71ea82d94`
**Suggested implementation branch:** `con-ready/worldkeeper-authoring-adapter-proof-v1`
**Suggested implementation PR title:** `CON-READY: prove WorldKeeper authoring adapter`
**WorldKeeper WK-5 accepted head:** `c1aeb157e14f2c07036e6346e93b2e47a228f387`
**WorldKeeper WK-5 merge:** `8a5efb96b69dc9ca136288ecc80f67c1ed027bd1`
**DungeonMind runtime:** `6edb9e40d1dc930f537c66deb1afbd1b99002844`
**V6.1 accepted head:** `9e2abbae42acc847b214460644caef2448637495`
**V6.1 merge:** `7a63c8b39937776ddede24d3d76001ef59fd37c4`
**PR topology:** implementation stacked on design PR #752 by user direction

## 1. Mission

Prove one narrow claim:

> DungeonBuddy can translate the supported published-recap authoring transaction
> into the generic `WorldChangeService` contract without owning DungeonMind
> publication semantics and without switching the current production authoring
> path yet.

This is a migration proof/foundation, not a production switch.

A PASS means this chain is real in focused tests:

```text
Buddy staged product proposals
→ Buddy-owned application-intent mapper
→ WorldChangeIntent
→ WorldChangeService
→ PreparedWorldChange
→ explicit commit
→ VerifiedCommittedChange
```

The canonical witness is the transaction-local case that motivated the
WorldKeeper extraction:

```text
Create local:brewery
existing Pippa → works_at → local:brewery

→ one WorldChangeIntent
→ relationship target = result_of(local:brewery)
→ one atomic DungeonMind child
→ the relationship uses the exact durable entity allocated for the brewery
```

Final disposition:

```text
CON_READY_WORLDKEEPER_AUTHORING_ADAPTER_PROOF_ACCEPTED
```

## 2. Activation gates

Do not dispatch implementation until all gates are satisfied.

### Gate A — WorldKeeper consumer boundary — SATISFIED

```text
WorldKeeper PR #7 / WK-5
accepted head:
  c1aeb157e14f2c07036e6346e93b2e47a228f387

merge:
  8a5efb96b69dc9ca136288ecc80f67c1ed027bd1

disposition:
  WK_5_CONSUMER_COMPOSITION_ACCEPTED
```

WorldKeeper now exposes:

```text
WorldChangeService
  prepare_change(intent)
  commit_prepared_change(prepared, confirmed_by)

DungeonMindWorldKeeperRuntime
```

### Gate B — Buddy source-to-World re-anchor — SATISFIED

Buddy PR #745 must be merged or superseded by equivalent checked-in authority.

The required authority claims are:

```text
Buddy owns product interaction + application intent.
WorldKeeper owns semantic transaction interpretation/coordination.
DungeonMind owns durable truth.
The old Buddy transaction-semantics handoff is migration evidence only.
A fresh Buddy handoff is required for implementation.
```

Current merged authority:

```text
PR #745
CON-READY: re-anchor source-to-World authoring
MERGED
accepted head: 4ee829a7b2caa98d2a4c12774422efe989b054d7
merge: 24ceed5d1661f7069faf3833ace641b71ea82d94
```

The user authorized implementation after #745 merged, including execution
from the rebased design branch while PR #752 remains open. PR #752 stays
documentation-only; the implementation uses a separate stacked branch.

### Gate C — Buddy V6.1 domain runtime foundation — SATISFIED

```text
PR #749
accepted head:
  9e2abbae42acc847b214460644caef2448637495

merge:
  7a63c8b39937776ddede24d3d76001ef59fd37c4

disposition:
  V6_1_DUNGEONBUDDY_DOMAIN_RUNTIME_ACCEPTED
```

Accepted identities:

```text
DomainContract:
  dungeonbuddy.world / revision 2
  sha256 d12f3a517a37d29a2ba52455d9ae1691bc5e4ff3fd6853b701a9e28e46ec65cd

SemanticProfile:
  dungeonbuddy.dnd5e / revision 1
  sha256 51ea47ff45bc86ea158939c34a5769e7ee56de3911278d473570e3795edb7e14
```

These V6.1 identities remain historical runtime authority for the existing
read proof. They are not a complete manual-authoring vocabulary: only two
relationship predicates are declared, while the product supports preset and
GM-crafted relationship types. The adapter must use an accepted successor
profile that preserves V6.1 semantics and explicitly admits a scoped custom
relationship namespace; it must not mutate revision 1 or its digest.

### Gate C2 — authored-predicate authority — BLOCKING

Before adapter implementation resumes, accept and pin:

1. DungeonMind's versioned, type-constrained open-predicate-namespace contract
   in both governed materialization and reads;
2. WorldKeeper compatibility with that descriptor and its DungeonMind pin;
3. Buddy's successor semantic profile, with `dungeonbuddy.custom` admitted
   for `entity_ref` predicates and fixed V6.1 terms retained.

The canonical `works_at` witness must use the exact qualified predicate
`dungeonbuddy.custom:works_at`. Adding that single term to a closed list is
not sufficient: a second previously unknown GM-authored predicate must also
pass. Existing Worlds pinned to an older profile require separate explicit
profile-transition authority; this adapter may not change their profile.

Proposed prerequisite PRs (not acceptance evidence while open):

```text
DungeonMind #77  V3 open predicate namespace, exact head 0f709d76fdc53bac9c9258d1751463ae2c76ca71
WorldKeeper #8   sealed V3 prepare/compile/commit compatibility, exact head 46d2557fdefd26defd26fa3d64358723152fc3e4
Buddy #754       opt-in Buddy V3 profile revision 2, exact head acf2e5cb286cf7c5040e9c6a51f4ba2978ec0731
```

Do not treat these proposed heads as merged authority. Re-anchor all three
before activating this handoff; an existing V2-pinned World remains unable to
publish authored predicates until a separately reviewed profile transition
exists.

### Gate D — dispatch from rebased design authority

At implementation dispatch, the user directed an isolated implementation
branch from the design PR rebased onto fresh Buddy `main`. The main snapshot is
`24ceed5d1661f7069faf3833ace641b71ea82d94`; the implementation PR is
stacked on PR #752 until the design PR merges. Complete these checks:

1. fetch current Buddy `main`;
2. verify #745 or successor authority is merged;
3. confirm no active CON-READY implementation PR owns the same paths;
4. record exact implementation base SHA;
5. re-read `pyproject.toml` and `uv.lock`;
6. re-read current Graph Authoring product DTOs and current V6.1 exports;
7. update only dispatch metadata if no semantic claim changed.

If any contract changed materially, return to Steward.

## 3. Why this is not a production switch

WorldKeeper v0 can express:

```text
CreateObject
UseExisting
CreateRelationship
CreateFact
DurableObjectRef
ResultOf
prepare
commit
durable entity/assertion result mappings
exact-child verification
```

Current Buddy authoring additionally contains:

```text
link_existing
merge_objects
```

`link_existing` is source-occurrence / alias / mention binding. WorldKeeper
v0 explicitly does not yet own occurrence/mention binding.

`merge_objects` is identity reconciliation and is also outside current
WorldKeeper authority.

Therefore this PR proves only the exact supported semantic subset.

Do not encode `link_existing` as `UseExisting`.

`UseExisting` means:

> this application transaction intentionally refers to this existing durable
> entity.

It does not mean:

> this source occurrence should now be durably linked to that entity.

Those are different semantics.

## 4. Ownership for this slice

### DungeonBuddy owns

- product proposal DTOs;
- campaign/session/source interaction context;
- local/reversible proposal IDs;
- explicit create-new and existing-object choices;
- product vocabulary → generic WorldKeeper intent mapping;
- product-specific mapping errors;
- deciding which proposal batches are eligible;
- eventual route/UX switching.

### WorldKeeper owns

- generic intent validation;
- same-transaction `result_of(...)` semantics;
- exact prepared meaning;
- stable prepared/publication identity;
- commit coordination;
- durable result mapping;
- exact child verification.

### DungeonMind owns

- durable entity/assertion IDs;
- source/provenance authority;
- semantic admission;
- immutable revisions;
- expected-parent/CAS;
- atomic publication;
- durable replay/recovery.

The new Buddy product mapper must not import DungeonMind publication or
materialization application modules.

## 5. Dependency pin

At implementation dispatch, add WorldKeeper as an exact dependency:

```text
worldkeeper @
git+https://github.com/Drakosfire/WorldKeeper.git@
8a5efb96b69dc9ca136288ecc80f67c1ed027bd1
```

Update `uv.lock` normally.

Do not repin DungeonMind unless another already-accepted Buddy prerequisite has
changed it before dispatch.

## 6. Buddy application-intent mapper

Preferred package:

```text
apps/live_control_server/integrations/worldkeeper/
  __init__.py
  graph_authoring.py
```

This module is Buddy-owned because it translates product intent into a generic
application contract.

It should depend on:

```text
worldkeeper.WorldChangeService
worldkeeper.WorldChangeIntent
worldkeeper.CreateObject
worldkeeper.CreateFact
worldkeeper.CreateRelationship
worldkeeper.UseExisting
worldkeeper.DurableObjectRef
worldkeeper.ResultOf
worldkeeper.AssertionMetadata
...
```

It must not depend on:

```text
DungeonMindWorldKeeperRuntime
DungeonMind publication functions
Buddy world_graph_writes publication helpers
```

Preferred shape; exact names may vary:

```python
class WorldKeeperAuthoringAdapter:
    def __init__(self, service: WorldChangeService) -> None: ...

    def prepare_supported_batch(
        self,
        *,
        context: PublishedRecapAuthoringContext,
        proposals: Sequence[GraphObjectAuthoringProposalPayload],
    ) -> PreparedWorldChange: ...

    def commit_prepared(
        self,
        prepared: PreparedWorldChange,
        *,
        confirmed_by: str,
    ) -> VerifiedCommittedChange: ...
```

Do not create another confirmation-token protocol here.

The purpose of this adapter is product mapping, not semantic transaction
orchestration.

## 7. Supported proposal subset

### 7.1 Object create

Support current create semantics only.

Conceptually:

```text
Buddy object proposal
  localProposalId = X
  operation = create

→

CreateObject(
  client_op_id = X,
  facts = <accepted Buddy object meaning>
)
```

Any label, kind, role, summary, scope, visibility, standing, claim mode, or
domain metadata emitted as durable knowledge must use the accepted Buddy
DomainContract and its accepted successor SemanticProfile semantics.

Do not invent fixed domain vocabulary in this PR. A GM-crafted relationship
term is permitted only under the accepted `dungeonbuddy.custom` namespace
rule, with `entity_ref` value semantics; the adapter must preserve its local
term exactly and reject invalid lexical forms instead of silently normalizing
or substituting another predicate.

If a current product field cannot be represented by accepted domain authority,
fail closed with a mapping error.

### 7.2 Relationship create

Support create semantics.

Endpoint mapping:

```text
existing_graph_node(nodeId=N)
→ DurableObjectRef(N)

local_proposal(localProposalId=X)
→ ResultOf(X)
```

Conceptually:

```text
Buddy relationship proposal
  localProposalId = R
  source = ...
  relationshipType = ...
  target = ...

→

CreateRelationship(
  client_op_id = R,
  source = <mapped endpoint>,
  predicate = <accepted fixed term or exact dungeonbuddy.custom:local term>,
  target = <mapped endpoint>,
  metadata = <accepted metadata>,
)
```

This is the canonical same-batch proof.

### 7.3 Existing durable identity

Existing graph-node references are explicit product identity choices.

Use the exact durable ID.

Do not derive identity from labels, source text, local proposal hashes, or old
Buddy prospective-ID algorithms.

`UseExisting` may be emitted only when it truthfully represents an identity
choice. It is not required merely because a relationship endpoint already has a
durable ID.

## 8. Explicitly unsupported in this PR

Reject before calling `WorldChangeService.prepare_change`:

```text
proposal_kind = link_existing
proposal_kind = merge_objects

object operation != create
relationship operation != create

manual_ref endpoint
authored_node endpoint without one exact current durable entity ID
```

Use one narrow Buddy-owned typed mapper error, for example:

```text
WorldKeeperAuthoringMappingError

codes:
  unsupported_operation
  duplicate_local_proposal_id
  missing_local_reference
  wrong_kind_local_reference
  invalid_durable_reference
  unsupported_domain_mapping
  missing_evidence_binding
```

Do not invoke the legacy write path from inside this adapter when mapping fails.

This PR does not switch production traffic, so unsupported mapping is evidence
about migration coverage, not a product regression.

## 9. Transaction-local referential integrity

Before delegating, Buddy must validate its own DTO referential shape.

Within one submitted proposal batch:

```text
every localProposalId is nonblank
every localProposalId is unique

every local relationship endpoint names either:
  one exact durable entity
  OR
  one exact object-create proposal in the same batch

a local endpoint referencing a relationship proposal fails
a missing local endpoint fails
an out-of-batch local endpoint fails
```

Then WorldKeeper independently validates the resulting generic intent.

This is not duplicate semantic authority:

- Buddy validates product DTO integrity.
- WorldKeeper validates generic World-change semantics.

Buddy must not calculate prospective durable IDs.

## 10. Evidence and source grounding

This proof uses existing durable evidence identity only.

For any emitted fact/relationship that requires support:

```text
published-recap product context
→ exact existing governed evidence_ref_id
→ WorldKeeper AssertionMetadata.evidence_ref_ids
```

Do not treat any of these as a durable evidence ID:

```text
recapArtifactId
source path
selected prose
browser digest
Tiptap offsets
local source-selection ID
```

Those may remain Buddy context or diagnostics.

If the exact durable evidence ref cannot be resolved through current accepted
authority, fail with:

```text
missing_evidence_binding
```

Do not call source-admission choreography from this adapter.

If ordinary supported authoring cannot obtain an existing exact evidence ref,
stop. That is concrete evidence for a new WorldKeeper/DungeonMind prerequisite.

## 11. Scope, visibility, standing, and metadata

Reuse V6.1 domain/runtime authority and its accepted custom-predicate profile
successor.

The adapter must not create a second independent vocabulary map for:

```text
campaign scope
visibility
standing
claim mode
domain metadata
predicate qualification
```

Prefer accepted Buddy domain/profile helpers and constructors.

If the accepted runtime does not expose enough mapping to construct valid WorldKeeper
`AssertionMetadata`, stop and rebrief rather than copying old
`contribution_mapping.py` or `assertion_qualification.py` internals into the
new package.

## 12. Concrete WorldKeeper runtime composition

Preferred path:

```text
apps/live_control_server/integrations/worldkeeper/runtime.py
```

This module may import:

```text
worldkeeper.integrations.dungeonmind.DungeonMindWorldKeeperRuntime
```

and accepted Buddy descriptor constructors.

Preferred shape:

```python
def build_worldkeeper_change_service(...) -> WorldChangeService:
    return DungeonMindWorldKeeperRuntime(
        repository=<existing DungeonMind vNext repository>,
        domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
        clock=...,
    )
```

Use the same existing production DungeonMind repository authority/factory that
the server already composes.

The selected World must already pin that V3 profile. Do not use this runtime
composition as an implicit profile migration for an existing V2-pinned World.

This module is the only new Buddy layer allowed to know the concrete
DungeonMind-backed WorldKeeper runtime.

Do not add HTTP between Buddy and WorldKeeper.

## 13. No production route switch

Do not switch:

```text
POST /api/live/graph-authoring/prepare
POST /api/live/graph-authoring/commit
```

Do not modify the current route/service write path merely to make this proof
convenient.

In particular, do not rewrite production behavior in:

```text
apps/live_control_server/services/graph_object_authoring_prepare.py
apps/live_control_server/services/graph_object_authoring_commit.py
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
```

unless a tiny test seam is strictly required and separately justified.

The new adapter/runtime is exercised directly by focused tests.

First prove the new ownership boundary. Production switching is a successor.

## 14. Migration responsibility ledger

Check in a small report or handoff section recording:

```text
Buddy responsibility                         disposition
---------------------------------------------------------------
product proposal DTOs                        KEEP
local staging / working projection           KEEP
review/publish UX                            KEEP
product → WorldChangeIntent mapping          KEEP IN BUDDY

current contribution_mapping.py              MIGRATION EVIDENCE
current assertion_qualification.py           MIGRATION EVIDENCE / SHRINK LATER
world_graph_writes.py publication logic      RETIRE AFTER SWITCH
Buddy publication recovery                   RETIRE AFTER SWITCH
Buddy prospective durable-ID logic           DELETE / DO NOT COPY

source occurrence link_existing              CONTRACT GAP
merge/reconciliation                         DEFERRED
```

This is required side-quest return evidence.

## 15. Canonical proof

Use disposable/in-memory DungeonMind vNext authority containing:

```text
existing durable entity:
  Pippa

existing durable evidence:
  one exact published-recap evidence ref
```

Create current Buddy product proposals equivalent to:

```text
object:
  localProposalId = local:brewery
  Create "The Wizard's Tower Brewing Co"

relationship:
  localProposalId = local:works-at
  source = existing Pippa
  predicate = works_at
  target = local:brewery
```

The emitted predicate is exactly `dungeonbuddy.custom:works_at`. Repeat the
publication/read-back proof with one other newly crafted term not enumerated
in the profile; a successful `works_at`-only exception is not acceptance.

Exercise only:

```text
Buddy WorldKeeperAuthoringAdapter
→ WorldChangeService
```

Prove:

```text
prepare performs no durable mutation

PreparedWorldChange contains:
  one CreateObject for local:brewery
  one CreateRelationship for local:works-at
  relationship target = ResultOf(local:brewery)

commit:
  publishes exactly one child
  local:brewery → ent:<DungeonMind allocated>
  local:works-at → asrt:<DungeonMind allocated>

exact child:
  relationship target == exact allocated brewery entity
  exact_child_read_back == true

retry:
  same child
  same durable mappings
  no second publication event
```

## 16. Required negative proofs

At minimum:

1. duplicate `localProposalId` fails before WorldKeeper prepare;
2. missing local endpoint fails;
3. local endpoint referencing relationship proposal fails;
4. out-of-batch local endpoint fails;
5. blank existing durable ID fails;
6. `manual_ref` fails;
7. `link_existing` fails as unsupported contract gap;
8. `merge_objects` fails as unsupported;
9. object/relationship update semantics fail as unsupported;
10. missing durable evidence mapping fails;
11. mapper never invents entity/assertion IDs;
12. mapper never imports DungeonMind publication/materialization code;
13. current production Graph Authoring routes remain on the pre-existing path.

## 17. Boundary fitness

### Product mapper

For:

```text
apps/live_control_server/integrations/worldkeeper/graph_authoring.py
```

forbid imports/references to:

```text
dungeonmind.application
dungeonmind.infrastructure
world_graph_writes
contribution_mapping
publish_prospective_contribution
publish_prospective_publication
allocate_prospective_result_id
```

### Runtime composition

For:

```text
apps/live_control_server/integrations/worldkeeper/runtime.py
```

allow the concrete WorldKeeper DungeonMind runtime and existing repository
composition seam.

Forbid direct calls to DungeonMind publication/allocation primitives.

### Production routes

No current production route/service module may import the new adapter in this
PR.

Add a focused source guard if practical.

## 18. Expected implementation paths

Preferred new paths:

```text
apps/live_control_server/integrations/worldkeeper/__init__.py
apps/live_control_server/integrations/worldkeeper/graph_authoring.py
apps/live_control_server/integrations/worldkeeper/runtime.py

tests/test_worldkeeper_graph_authoring_adapter.py

Docs/Reports/REPORT-CON-READY-worldkeeper-authoring-adapter-proof-v1.md
```

Expected dependency paths:

```text
pyproject.toml
uv.lock
```

Permitted state-sync paths after #745 merges:

```text
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md
Docs/Plans/HANDOFF-CON-READY-worldkeeper-authoring-adapter-proof-v1.md
```

Do not modify V6.1 implementation paths except for a tiny export clearly
implied by its accepted public API. If more is required, stop.

## 19. Explicit non-goals

Do not:

```text
switch production graph-authoring prepare/commit
delete world_graph_writes.py
rewrite Graph Authoring UI
change frontend DTOs

implement link_existing occurrence binding
implement merge/reconciliation
add automatic dedupe

change DungeonMind
change WorldKeeper
create/admit source or evidence records
change live World state

add HTTP between Buddy and WorldKeeper
implement V2-3 derived gold
start extraction/model ablation
add Agent write capability
```

## 20. Verification

After activation, run at minimum:

```bash
uv sync --locked

uv run ruff check \
  apps/live_control_server/integrations/worldkeeper \
  tests/test_worldkeeper_graph_authoring_adapter.py

uv run pytest -q \
  tests/test_worldkeeper_graph_authoring_adapter.py \
  tests/test_graph_object_authoring_prepare.py \
  tests/test_graph_object_authoring_published_recap_write.py

git diff --check
```

Also run:

- accepted V6.1 focused suite;
- current package/import boundary fitness;
- current default non-live suite, or classify inherited failures against exact
  base/head if baseline prevents a clean run.

Report exact installed SHAs for:

```text
WorldKeeper
DungeonMind
```

## 21. Acceptance rubric

- [ ] Gate B is merged/satisfied and exact authority SHA recorded.
- [ ] fresh-main implementation base recorded.
- [ ] exact WorldKeeper WK-5 pin added.
- [ ] mapper depends on `WorldChangeService`, not DungeonMind write APIs.
- [ ] concrete runtime composition isolated from product mapping.
- [ ] accepted Buddy DomainContract and custom-predicate profile reused.
- [ ] same-batch object + relationship maps through `ResultOf`.
- [ ] prepare mutates no durable state.
- [ ] commit produces one verified child and exact durable mappings.
- [ ] retry is idempotent.
- [ ] duplicate/missing/wrong-kind local refs fail closed.
- [ ] `link_existing` explicitly remains a contract gap.
- [ ] merge/update semantics are not smuggled in.
- [ ] evidence refs are durable authority IDs.
- [ ] Buddy generates no prospective durable IDs.
- [ ] production routes remain unchanged.
- [ ] current production authoring regressions remain green.
- [ ] migration responsibility ledger is checked in.
- [ ] exact-head verification passes.

Final disposition:

```text
CON_READY_WORLDKEEPER_AUTHORING_ADAPTER_PROOF_ACCEPTED
```

## 22. Successor decision

After acceptance, Steward chooses from evidence.

### If the supported mapping is sufficient

Design a production-switch PR:

```text
published-recap supported authoring batch
→ WorldChangeService
```

with explicit error/receipt DTO adaptation and retirement of corresponding
Buddy publication-driver code.

### If evidence binding blocks ordinary authoring

Return to WorldKeeper/DungeonMind design with the exact missing primitive.

Do not make Buddy source-admission choreography permanent merely to force the
migration.

### If `link_existing` is required for the first production switch

Design occurrence/mention semantics first.

Do not encode it as `UseExisting`.

## 23. Stop conditions

Stop and return to Steward if implementation requires:

- changing WorldKeeper contracts;
- changing DungeonMind contracts;
- accepting a custom term without the versioned predicate-namespace authority;
- silently changing an existing World's pinned semantic profile;
- copying current DungeonMind contribution-building code into the mapper;
- generating future durable IDs in Buddy;
- admitting new source/evidence state;
- switching production routes;
- implementing occurrence binding;
- implementing merge/reconciliation;
- modifying live World state to prove the adapter.

## 24. Handback

Return:

```text
activation-gate SHAs
implementation base SHA
branch / PR
exact head
commit list
changed paths

WorldKeeper pin
DungeonMind pin
V6.1 descriptor/profile identities

actual adapter public shape
actual runtime composition shape
supported proposal matrix
unsupported proposal matrix

canonical same-batch witness
negative reference-integrity proofs
evidence-binding proof
boundary/source-guard proofs

focused tests
regression tests
default-suite classification
Ruff
diff check

migration responsibility ledger
remaining contract gaps
final disposition
```
