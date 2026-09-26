---
pr_body_template: |
  ## Handoff pointer
  - Repository: Drakosfire/DungeonMindBuddy
  - Direction: STEWARD → CODE → REVIEW
  - Thread: CON-READY PLAY
  - Slice: PLAY-1 — Buddy → WorldKeeper consumer proof
  - Handoff: Docs/Plans/HANDOFF-CON-READY-PLAY-worldkeeper-consumer-proof-v1.md
  - PLAY-0 design base: e696b20e5f5e34f0fb7cf2c8fb04dc48c1706ea4
  - WorldKeeper reviewed implementation pin: 49a8620f066ce7ef8972a699020c012f50af9158
  - WorldKeeper accepted merge: a0a70db275cf6c5f3876fe7b4d2a557de12388f5
  - DungeonMind runtime pin already in Buddy: 0f709d76fdc53bac9c9258d1751463ae2c76ca71
  - Buddy V3 profile prerequisite: PR #754 merge 7addcd05b20c894eb4d50b9d63e5ebdee4bc2cc7

  Prove the Buddy → WorldKeeper consumer boundary in-memory. Preserve exact
  GM-authored custom relationship predicates. Do not switch production routes
  or persistent World authority.
---

# HANDOFF — CON-READY PLAY-1: Buddy → WorldKeeper consumer proof

**Created:** 2026-09-25
**Status:** ACTIVE — PLAY-1 implementation authorized on the fresh-main-based branch
**Repository:** `Drakosfire/DungeonMindBuddy`
**Thread:** `CON-READY / PLAY`
**PR topology:** serial
**PLAY-0 accepted head:** `25197d1b9f2dbf96752e453c34456830d5a99d1a`  
**PLAY-0 final review:** `5324695932` — PASS / READY TO MERGE  
**PLAY-0 merge:** `6e92bec11df22b4b4243cb58c1bbcbe43b109ff6`
**Activation re-anchor / implementation base:** `main@f30b4c906bb179b25f00207c40cb38c0debdc264`
**Resolved path gate:** PR #767 merged at `f30b4c906bb179b25f00207c40cb38c0debdc264`; no open PR owns the PLAY-1 dependency or consumer paths at dispatch
**Activation placement:** User explicitly permits the handoff off `main`; this ACTIVE record and implementation are carried together in one fresh-main-based serial PR, without writing to `main`
**Suggested branch:** `codex/con-ready-play-1-worldkeeper-consumer-proof`
**Suggested PR title:** `CON-READY PLAY-1: prove Buddy WorldKeeper consumer mapping`
**WorldKeeper accepted head:** `49a8620f066ce7ef8972a699020c012f50af9158`
**WorldKeeper implementation dependency:** `49a8620f066ce7ef8972a699020c012f50af9158`
**WorldKeeper accepted merge evidence:** `a0a70db275cf6c5f3876fe7b4d2a557de12388f5`
**DungeonMind runtime head already pinned by Buddy:** `0f709d76fdc53bac9c9258d1751463ae2c76ca71`
**DungeonMind V3 authority finalization:** `54a419f99057d96e0c4e7620d8bd8ccc6816fb62`
**Buddy custom-profile prerequisite:** PR #754 merge `7addcd05b20c894eb4d50b9d63e5ebdee4bc2cc7`
**Buddy V3 profile descriptor SHA-256:** `d40a352d1c6cbd24df68be887be6dc65a470e4cea8fb64970ef9ad89b96a3339`
**V2-3:** NOT AUTHORIZED

## 0. Activation re-anchor

PLAY-0 is complete and accepted:

```text
PR #753
accepted head: 25197d1b9f2dbf96752e453c34456830d5a99d1a
final review: 5324695932 — PASS / READY TO MERGE
merge: 6e92bec11df22b4b4243cb58c1bbcbe43b109ff6
```

Fresh repository re-anchor after #767:

```text
DungeonMindBuddy main:
  f30b4c906bb179b25f00207c40cb38c0debdc264
```

The reviewed PLAY-1 semantic lease remains valid. The prior path collision is
resolved:

```text
merged PR #767 — VNEXT: adapt complete entity reads to World-object DTO
formerly owned:
  pyproject.toml

PLAY-1 requires:
  pyproject.toml
  uv.lock
  apps/live_control_server/integrations/worldkeeper/**
  tests/test_con_ready_play_worldkeeper_consumer.py
  bounded CON-READY authority/report paths
```

PLAY-1 starts from the #767 merge on `main`, not from its PR branch. The
dependency and consumer paths are free in the open-PR inventory at dispatch.

Open settlement PR #766 does not overlap the PLAY-1 implementation/dependency
lease identified above. If its merge changes current authority documents before
PLAY-1 activation, re-read them but do not broaden PLAY-1 automatically.

Activation checks completed after #767 resolved:

1. fetch current `main`;
2. verify no open PR owns `pyproject.toml`, `uv.lock`, or
   `apps/live_control_server/integrations/worldkeeper/**`;
3. verify Buddy still pins DungeonMind runtime
   `0f709d76fdc53bac9c9258d1751463ae2c76ca71` or classify any accepted successor;
4. verify WorldKeeper dependency target remains reviewed head
   `49a8620f066ce7ef8972a699020c012f50af9158`;
5. verify Buddy custom profile revision 2 digest remains
   `d40a352d1c6cbd24df68be887be6dc65a470e4cea8fb64970ef9ad89b96a3339`;
6. update only re-anchor/activation metadata if semantics are unchanged;
7. record `Status: ACTIVE` in this fresh-main-based implementation PR under the
   user's explicit exception to main-first placement;
8. open only the serial PLAY-1 implementation PR; do not merge it here.

A later `main` advance is not itself a blocker when these contracts and leases
remain unchanged. Material contract drift requires rebrief.


## 1. Mission

Answer one question:

> Can DungeonBuddy express a real GM-authored object + relationship transaction
> through the accepted WorldKeeper boundary without knowing DungeonMind write
> mechanics, including a relationship predicate the Kernel has never enumerated
> before?

PLAY-1 is a consumer proof only.

Required chain:

```text
Buddy staged proposals
→ Buddy-owned mapper
→ WorldChangeIntent
→ injected WorldChangeService
→ DungeonMindWorldKeeperRuntime
→ PreparedWorldChange
→ explicit test confirmation
→ VerifiedCommittedChange
```

No production route, browser, persistent World, or live campaign authority is
changed.

Final disposition:

```text
CON_READY_PLAY_1_WORLDKEEPER_CONSUMER_PROOF_ACCEPTED
```

Only Steward review may record it.

## 2. Why this is the next slice

The prerequisites are now real:

```text
DungeonMind V5.4 prospective publication          ACCEPTED
DungeonMind semantic-profile V3                  ACCEPTED
WorldKeeper WK-5 consumer service                ACCEPTED
WorldKeeper V3 profile preservation              ACCEPTED / #8
Buddy vNext domain runtime                       ACCEPTED / #749
Buddy opt-in custom predicate profile V3         ACCEPTED / #754
Buddy source-to-World ownership reconciliation   MERGED / #745
```

The unresolved product/runtime question is now the consumer boundary itself.

Do not repair the old Buddy prospective-ID/compiler path as the destination.

Do not jump ahead to persistent dogfood or browser wiring before this mapping is
proved independently.

## 3. Ownership under test

### DungeonBuddy owns

- product proposal DTOs;
- reversible staging;
- explicit create-new / exact-existing-object choices;
- GM-authored relationship term selection;
- product-local validation of its proposal/reference shape;
- mapping product intent into generic WorldKeeper contracts.

### WorldKeeper owns

- generic `WorldChangeIntent`;
- semantic preparation;
- same-transaction `ResultOf(client_op_id)`;
- immutable `PreparedWorldChange`;
- confirmation coordination;
- verified durable-result reshaping.

### DungeonMind owns

- durable entity/assertion allocation;
- semantic-profile admission;
- provenance/evidence authority;
- immutable child publication;
- CAS;
- idempotent replay/recovery.

PLAY-1 must make these ownership lines visible in code.

## 4. Accepted profile for PLAY-1

Use Buddy's accepted opt-in semantic profile:

```text
profile_id       dungeonbuddy.dnd5e
profile_revision 2
schema_version   dm_semantic_profile_v3
descriptor_sha256 d40a352d1c6cbd24df68be887be6dc65a470e4cea8fb64970ef9ad89b96a3339
```

Runtime constructor:

```python
dungeonbuddy_dnd5e_custom_predicate_profile()
```

It preserves the fixed Buddy/D&D profile and additionally opens exactly:

```text
namespace: dungeonbuddy.custom
allowed value kind: entity_ref
```

No V2→V3 migration is implied.

The isolated PLAY-1 parent revision is created pinned to profile revision 2 from
the beginning.

Do not use `dungeonbuddy_dnd5e_semantic_profile()` revision 1 for the canonical
custom-predicate witness.

## 5. WorldKeeper dependency

Add an exact WorldKeeper dependency at the reviewed #8 implementation head:

```text
worldkeeper @ git+https://github.com/Drakosfire/WorldKeeper.git@49a8620f066ce7ef8972a699020c012f50af9158
```

Update `uv.lock`.

Do not repin Buddy's DungeonMind dependency in PLAY-1. Current Buddy already
pins the substantively reviewed runtime required by WorldKeeper #8:

```text
0f709d76fdc53bac9c9258d1751463ae2c76ca71
```

The DungeonMind #78 merge finalized authority only; it did not change the
runtime code consumed here.

## 6. Buddy consumer package

Create:

```text
apps/live_control_server/integrations/worldkeeper/__init__.py
apps/live_control_server/integrations/worldkeeper/graph_authoring_consumer.py
```

The consumer must depend on the generic service boundary:

```python
WorldChangeService
```

not on DungeonMind publication APIs.

Preferred shape, exact names may vary:

```python
@dataclass(frozen=True, slots=True)
class PlayAuthoringContext:
    space_id: str
    campaign_id: str
    evidence_ref_ids: tuple[str, ...]
    producer: str = "dungeonbuddy:con-ready-play"

class WorldKeeperGraphAuthoringConsumer:
    def __init__(self, service: WorldChangeService) -> None: ...

    def build_intent(
        self,
        *,
        context: PlayAuthoringContext,
        proposals: Sequence[GraphObjectAuthoringProposalPayload],
    ) -> WorldChangeIntent: ...

    def prepare(
        self,
        *,
        context: PlayAuthoringContext,
        proposals: Sequence[GraphObjectAuthoringProposalPayload],
    ) -> PreparedWorldChange: ...

    def commit(
        self,
        prepared: PreparedWorldChange,
        *,
        confirmed_by: str,
    ) -> VerifiedCommittedChange: ...
```

Implementation may expose fewer methods if tests can still inspect the exact
mapped `WorldChangeIntent`.

The constructor must accept an injected `WorldChangeService`. This is the
Buddy seam.

## 7. Supported Buddy proposal subset

PLAY-1 supports only:

```text
object        operation=None | "create" → create
relationship operation=None | "create" → create
```

The current Buddy DTO normally leaves `operation=None` for these staged
creates. Preserve that existing meaning. Any other operation value, including
a blank string, fails closed; do not reinterpret update, alias, or
`link_existing` as create.

For the bounded relationship proof, `direction=None | "directed"` means
directed. Reject `undirected`. `relationshipLabel` and relationship `summary`
must be absent or blank; reject nonblank values rather than discarding them.

For **both object and relationship proposals**, only this GM-private proposal
metadata shape is supported:

```text
visibility.visibility = gm_private
visibility.revealState = unrevealed
visibility.visibilityNote = absent or blank
graphScopes = exactly recap_graph + campaign_memory_graph, once each
```

Reject any other visibility, reveal state, nonblank visibility note, or graph
scope shape for **either** proposal kind. Map the supported GM-private shape
to every generated fact and relationship assertion's metadata in §11; do not
silently convert a player-visible or hidden-until-revealed object or
relationship proposal into GM-only durable assertions. This bounded proof
does not establish a general visibility conversion.

It must fail closed for:

```text
link_existing
merge_objects
object update/alias/link_existing operations
relationship update/link_existing operations
manual_ref endpoint
unresolved authored_node endpoint
occurrence/mention binding
identity reconciliation
```

Do not call the historical production writer as fallback.

## 8. Object mapping

For one Buddy object proposal:

```text
proposal.localProposalId
→ CreateObject.client_op_id
```

Map the bounded durable meaning already accepted by Buddy profile authority.

Required object facts when present:

```text
label
  → dnd5e:name
  → literal

kind
  → dnd5e:classification
  → term_ref

summary
  → dnd5e:summary
  → literal
```

Accepted kind mapping:

```text
npc           → dnd5e:npc
location      → dnd5e:location
faction       → dungeonbuddy:faction
organization  → dungeonbuddy:organization
```

Unknown kinds fail closed.

Non-empty aliases or role semantics that are not representable by this accepted
subset fail closed. Do not silently discard them.

Each fact gets a deterministic **transaction-local** client operation ID derived
from the proposal ID and fact role, e.g.:

```text
npc-gate-runner.fact.name
npc-gate-runner.fact.classification
npc-gate-runner.fact.summary
```

These are transaction-local IDs only.

Buddy must never derive an `ent:*` or `asrt:*` ID.

## 9. Relationship endpoint mapping

Map endpoints exactly:

```text
existing_graph_node(nodeId=N)
→ DurableObjectRef(durable_object_id=N)

local_proposal(localProposalId=X)
→ ResultOf(client_op_id=X)
```

A local endpoint must name exactly one object-create proposal in the same
submitted batch.

Operation order must not matter.

Fail closed on:

- blank durable ID;
- missing local proposal;
- duplicate local proposal ID;
- local reference to relationship/non-object proposal;
- local reference outside the submitted batch;
- `manual_ref`;
- unresolved non-durable authored-node identity.

## 10. Relationship predicate mapping — critical PLAY-1 rule

Buddy owns lexical/product mapping. WorldKeeper does not invent vocabulary.

### Fixed qualified predicates

If the product proposal already supplies one accepted fixed qualified predicate
from the profile, preserve it exactly.

Examples currently accepted:

```text
dnd5e:located_in
dungeonbuddy:allied_with
```

Do not introduce aliases for fixed predicates in this PR.

### GM-authored custom predicates

A GM-authored local relationship term such as:

```text
works_at
mentors
trained_by
```

maps only by exact namespace qualification:

```text
works_at   → dungeonbuddy.custom:works_at
mentors    → dungeonbuddy.custom:mentors
trained_by → dungeonbuddy.custom:trained_by
```

The local term must already satisfy the local portion of DungeonMind's qualified
term grammar:

```text
^[a-z0-9]+(?:[._-][a-z0-9]+)*$
```

Do not slugify, lowercase, synonym-map, fuzzy-match, or otherwise reinterpret an
invalid term.

Invalid local term fails closed.

Do not map `works_at` to `dnd5e:located_in`.
Do not map unknown terms to `dungeonbuddy:allied_with`.

The exact selected meaning is the contract.

## 11. Assertion metadata

Use accepted Buddy vNext constants from:

```text
src/graph_memory/vnext/domain_runtime.py
```

Canonical GM witness metadata:

```text
scope
  dungeonbuddy.scope:campaign = <campaign_id>

visibility
  labels_any(dungeonbuddy.visibility:gm)

epistemic_basis
  asserted

claim_mode
  dungeonbuddy.claim:fact

standing
  established

temporal_scope
  timeless

evidence_ref_ids
  exact already-admitted IDs supplied to the consumer
```

Do not create an independent vocabulary table if existing exported constants or
constructors suffice.

A tiny pure helper may be added under the new consumer package if required for
mapping WorldKeeper's metadata model.

## 12. Evidence rule

PLAY-1 uses already-admitted evidence only.

The consumer input receives exact durable evidence IDs.

Do not synthesize evidence identity from:

```text
recapArtifactId
source path
selected prose
Tiptap offsets
hashes
browser-local selection IDs
```

The isolated parent revision must already contain the exact `EvidenceRefV3`
record in its native graph payload. WorldKeeper's write runtime obtains its
evidence witness from that exact parent graph; it does not consume a
`KnowledgeSourceReader` in PLAY-1. Do not add a source reader fixture or source
admission path to this proof.

If an evidence ID is missing, WorldKeeper prepare must fail closed.

PLAY-1 does not admit sources.

Evidence support still does not imply occurrence/mention binding.

## 13. In-memory composition

Canonical proof composition:

```text
Buddy WorldKeeperGraphAuthoringConsumer
        ↓ injected protocol
WorldChangeService
        ↓ concrete test composition
DungeonMindWorldKeeperRuntime
        ↓
InMemoryKnowledgeRevisionRepository
```

Use:

```python
dungeonbuddy_world_domain_contract()
dungeonbuddy_dnd5e_custom_predicate_profile()
```

Seed one native vNext parent whose exact refs/digests match those descriptors.

No production vNext repository factory is required or authorized.

Do not add one in PLAY-1.

## 14. Canonical witness A — works_at

Seed isolated authority:

```text
space:
  space:play-witness

campaign:
  campaign:play-witness

existing durable entity:
  ent:pippa

existing admitted evidence:
  ev:play-session-note
```

Buddy proposals:

```text
object:
  localProposalId = brewery
  label = The Wizard's Tower Brewing Co
  kind = location

relationship:
  localProposalId = rel-pippa-brewery
  source = existing_graph_node(ent:pippa)
  relationshipType = works_at
  target = local_proposal(brewery)
```

Expected intent:

```text
CreateObject(
  client_op_id=brewery,
  ...
)

CreateRelationship(
  client_op_id=rel-pippa-brewery,
  source=DurableObjectRef(ent:pippa),
  predicate=dungeonbuddy.custom:works_at,
  target=ResultOf(brewery),
  ...
)
```

Required prepare proof:

```text
no durable mutation
prepared profile = exact Buddy V3 profile revision 2
prospective handle brewery exists
custom predicate remains dungeonbuddy.custom:works_at
no predicted durable entity/assertion ID exists in Buddy output
```

Required commit proof:

```text
exactly one child
brewery → ent:<DungeonMind allocated>
rel-pippa-brewery → asrt:<DungeonMind allocated>

exact child assertion:
  predicate = dungeonbuddy.custom:works_at
  subject = ent:pippa
  target = exact allocated brewery entity

exact_child_read_back = true
```

Retry the same prepared value:

```text
same VerifiedCommittedChange
same child
same mappings
no second head event
```

## 15. Canonical witness B — previously unknown predicate

A second independent witness must use a valid term not enumerated in any fixed
predicate table or special-case branch.

Recommended:

```text
dungeonbuddy.custom:mentors
```

Use exact durable or same-transaction entity endpoints as convenient.

Prove:

```text
consumer maps bare "mentors" only by namespace qualification
prepare preserves exact predicate
commit admits exact predicate under V3 open namespace
exact child contains exact predicate
no code path special-cases "mentors"
```

The test must be written so replacing `mentors` with another valid local term
would exercise the same mapping branch.

## 16. V2-pinned negative witness

Seed another isolated parent using Buddy profile revision 1.

Attempt the same custom predicate.

Required result:

```text
publication/prepare fails closed under pinned V2 semantics
no child
no silent profile transition
no automatic repin to V3
```

PLAY-1 does not implement a V2→V3 transition.

## 17. Required negative coverage

At minimum:

1. duplicate `localProposalId`;
2. missing local endpoint;
3. local endpoint naming a relationship proposal;
4. out-of-batch local endpoint;
5. `manual_ref`;
6. exact existing endpoint without durable ID;
7. unsupported `link_existing` proposal;
8. unsupported `merge_objects`;
9. unsupported update operation;
10. unknown object kind;
11. invalid authored predicate local term;
12. unsupported custom predicate value kind if mapper can express the case;
13. missing adapter evidence ID;
14. evidence ID absent from parent;
15. unsupported alias/role semantics;
16. stale prepared change after another commit;
17. repeated commit of same prepared value remains idempotent;
18. custom predicate against V2-pinned parent fails closed.
19. object proposal with player-visible visibility, non-default reveal state,
    nonblank visibility note, or non-default/duplicate `graphScopes` fails
    before prepare; no GM-private facts are emitted from it;
20. relationship proposal with the same unsupported metadata shapes fails
    before prepare; no GM-private relationship assertion is emitted from it.

Do not add broad fallback logic to turn negative cases green.

## 18. Boundary fitness

Add source-level guards proving the new consumer module does not import/call:

```text
dungeonmind.application
dungeonmind.infrastructure
world_graph_writes
contribution_mapping
assertion_qualification
publish_prospective_contribution
publish_prospective_publication
allocate_prospective_result_id
```

The consumer may import:

- Buddy proposal models;
- Buddy vNext domain constants/helpers;
- generic WorldKeeper application contracts.

The focused test may import:

```text
DungeonMindWorldKeeperRuntime
InMemoryKnowledgeRevisionRepository
```

for composition.

Production application modules must not import the new PLAY-1 consumer in this
PR.

## 19. Files in scope

Dependency:

```text
pyproject.toml
uv.lock
```

Implementation:

```text
apps/live_control_server/integrations/worldkeeper/__init__.py
apps/live_control_server/integrations/worldkeeper/graph_authoring_consumer.py
```

Focused proof:

```text
tests/test_con_ready_play_worldkeeper_consumer.py
```

Bookkeeping/report:

```text
Docs/Plans/HANDOFF-CON-READY-PLAY-worldkeeper-consumer-proof-v1.md
Docs/Reports/REPORT-CON-READY-PLAY-worldkeeper-consumer-proof-v1.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md
Docs/Plans/PLAN-CON-READY-PLAY-dogfood-thread-v1.md
Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md
```

One narrowly extracted pure helper may be added only if required for readability.
Record any scope expansion in the handoff before review.

## 20. Explicitly out of scope

Do not modify:

```text
apps/live_control_server/routes/graph_authoring.py
apps/live_control_server/services/graph_object_authoring_prepare.py
apps/live_control_server/services/graph_object_authoring_commit.py
apps/live-control-ui/**
production World Graph routing
live Eldyrwild data
```

Do not implement:

- persistent PLAY authority;
- PostgreSQL PLAY repository composition;
- source admission;
- occurrence/mention binding;
- `link_existing`;
- merge/reconciliation;
- dual write;
- bridge-genesis migration;
- legacy→vNext translation;
- production read switching;
- production write switching;
- Agent authoring;
- V2-3 derived gold;
- a WorldKeeper network service;
- changes to WorldKeeper or DungeonMind repositories.

If the proof requires any of these, STOP.

## 21. Why production Graph Authoring remains untouched

The current Graph Authoring route still targets historical/current production
World authority.

WorldKeeper's accepted consumer path targets vNext
`KnowledgeRevisionRepository`.

Switching that route now would require migration/cutover authority not owned by
PLAY-1.

PLAY-1 therefore proves the application boundary against isolated vNext
authority only.

PLAY-2 will separately ask whether the same path survives persistent isolated
PostgreSQL authority.

## 22. Verification

At exact implementation head run:

```bash
uv sync --locked

uv run pytest -q \
  tests/test_con_ready_play_worldkeeper_consumer.py

uv run pytest -q \
  tests/test_v6_1_dungeonbuddy_vnext_domain_runtime.py \
  tests/test_v6_0_1_dungeonbuddy_evidence_metadata_contract.py

uv run ruff check \
  apps/live_control_server/integrations/worldkeeper \
  tests/test_con_ready_play_worldkeeper_consumer.py

uv run python -c "import worldkeeper; from worldkeeper.integrations.dungeonmind import DungeonMindWorldKeeperRuntime"

git diff --check
```

Also run the current default non-live suite. If inherited collection failures
remain, compare exact base/head and classify them rather than repairing unrelated
debt.

Report exact installed revisions for:

```text
WorldKeeper
DungeonMind
```

## 23. Acceptance rubric

- [ ] handoff is ACTIVE on the fresh-main-based implementation branch under the explicit user exception to main-first placement;
- [ ] PR #767 collision was resolved and dependency paths were free at dispatch;
- [ ] WorldKeeper dependency pinned to reviewed #8 head `49a8620...`;
- [ ] existing DungeonMind runtime pin remains coherent;
- [ ] canonical parent uses exact Buddy custom profile V3 revision 2 and descriptor SHA-256 `d40a352d1c6cbd24df68be887be6dc65a470e4cea8fb64970ef9ad89b96a3339`;
- [ ] consumer depends on injected `WorldChangeService`;
- [ ] consumer emits generic WorldKeeper contracts only;
- [ ] object create mapping is exact;
- [ ] durable existing endpoint mapping is exact;
- [ ] local endpoint uses `ResultOf(client_op_id)`;
- [ ] GM custom predicate is preserved as `dungeonbuddy.custom:<exact-term>`;
- [ ] `works_at` witness passes;
- [ ] second previously unknown custom predicate witness passes;
- [ ] operation ordering does not change semantic intent;
- [ ] Buddy predicts no durable ID;
- [ ] prepare performs no durable mutation;
- [ ] one commit yields exact verified entity/assertion mappings;
- [ ] exact child contains exact custom predicate and endpoints;
- [ ] retry is idempotent;
- [ ] V2-pinned parent rejects custom predicate without transition;
- [ ] unsupported Buddy semantics fail closed;
- [ ] no route/UI/persistent/live-World change;
- [ ] exact-head verification is reported.

Final disposition:

```text
CON_READY_PLAY_1_WORLDKEEPER_CONSUMER_PROOF_ACCEPTED
```

## 24. Successor

After PLAY-1 acceptance, design PLAY-2 from the actual proof:

> Compose the accepted Buddy consumer and WorldKeeper runtime over an isolated,
> persistent vNext PostgreSQL authority; prove restart/reopen persistence and
> durable result recovery without touching current Eldyrwild or production
> routing.

PLAY-2 is not authorized by this handoff.

## 25. Stop conditions

Stop and return to Steward if implementation requires:

- changing WorldKeeper contracts;
- changing DungeonMind contracts;
- changing the accepted Buddy V3 profile;
- a V2→V3 migration;
- source/evidence admission;
- production route wiring;
- persistent authority;
- live World mutation;
- copying DungeonMind publication logic into Buddy;
- predicting durable IDs;
- special-casing individual custom predicates instead of namespace qualification.

## 26. Handback

Return only:

```text
implementation base SHA
branch / PR
exact head
commit list
changed paths

WorldKeeper installed SHA
DungeonMind installed SHA
Buddy DomainContract digest
Buddy custom SemanticProfile digest

actual consumer public shape
actual supported/unsupported mapping matrix

works_at canonical witness
second unknown-predicate witness
V2-pinned negative witness
reference-integrity negatives
evidence negative proof
boundary/source guards

focused tests
V6 regression tests
default-suite classification
Ruff
diff check

what remains false
final disposition
```
