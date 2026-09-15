---
pr_body_template: |
  ## Handoff pointer
  - Workstream: KERNEL / vNext V0.2 — DungeonBuddy contract pin + domain preservation proof
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-v0-2-dungeonmind-vnext-contract-pin-domain-proof.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  Pin DungeonBuddy to the exact frozen DungeonMind vNext V0.1 contract identity,
  prove the Buddy World/TTRPG domain can express its current authority semantics
  through the generic contract without inventing Kernel fields, and leave the
  production World Graph read/write path unchanged.
---

# HANDOFF — V0.2: pin DungeonMind vNext and prove DungeonBuddy domain preservation

**Created:** 2026-09-15  
**Status:** ACTIVE — ready for implementation dispatch  
**Workstream:** KERNEL / DungeonMind vNext roadmap  
**Roadmap phase:** V0 — Contract freeze  
**Slice:** V0.2 — DungeonMindBuddy consumer/domain proof  
**Direction:** DESIGN → CODE → REVIEW  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Design-time Buddy main:** `a9d1155c3713128a900c5f85357fe7803df0b9a9`  
**Current production DungeonMind pin:** `d8f7a9f0d6b256f5cf4588987520bf286f1eade3` — DungeonMind PR #52 merge  
**Required DungeonMind vNext pin:** `63ec810a02f18c4e25af228f6fdb19d99d12579e` — DungeonMind PR #56 merge  
**Accepted V0.1 implementation head:** `ba2ec6dc16137b57aab4ca7544f00eb4a5802a15`  
**Canonical DungeonMind V0.1 aggregate:** `fd04a9047b8ed79aaa5e710b2247ce1b2654c0e44e05d24fafb2adecb9e7b7ea`  
**Suggested implementation branch:** `contracts/v0-2-dungeonbuddy-domain-proof`  
**Suggested PR title:** `CONTRACTS: pin DungeonMind vNext and prove DungeonBuddy domain mapping`  
**Predecessor:** DungeonMind PR #56 — `CONTRACTS: V0.1 generic vNext schema surface`  
**Successor on success:** Steward marks `VNEXT_CONTRACT_FROZEN`; DungeonMind V1 may begin and DungeonBuddy V6 may proceed in parallel when separately dispatched.

---

## §1 Mission

Answer one question:

> **Can DungeonMindBuddy consume the exact frozen DungeonMind vNext contract and express the current World/TTRPG authority semantics it depends on without adding Buddy-only fields to the generic Kernel contract or changing production behavior?**

The intended proof chain is:

```text
DungeonMind PR #56 exact contract identity
        ↓
Buddy exact package + artifact pin
        ↓
Buddy-owned DomainContract fixture
        ↓
Buddy-owned SemanticProfile v2 fixture
        ↓
current Buddy semantic mapping fixture
        ↓
strict validation through the frozen DungeonMind models
        ↓
no local Kernel schema invention
```

This is the consumer half of V0.

Successful disposition:

```text
V0_2_DUNGEONBUDDY_DOMAIN_PROOF_ACCEPTED
```

Only after this proof is accepted may the Steward mark:

```text
VNEXT_CONTRACT_FROZEN
```

This PR does **not** implement the vNext runtime domain policy, migrate live authority, switch production reads, or cut Buddy over to vNext storage.

---

## §2 Re-anchor before coding

The design-time Buddy anchor is:

```text
a9d1155c3713128a900c5f85357fe7803df0b9a9
```

Do not preserve that SHA merely because it appears in this handoff.

Before implementation:

1. fetch current `DungeonMindBuddy/main`;
2. rebase/create the implementation branch from current main;
3. record the exact Buddy base SHA in the PR;
4. confirm DungeonMind `main` still contains PR #56 merge:

   ```text
   63ec810a02f18c4e25af228f6fdb19d99d12579e
   ```

5. confirm the checked-in provider aggregate is still exactly:

   ```text
   fd04a9047b8ed79aaa5e710b2247ce1b2654c0e44e05d24fafb2adecb9e7b7ea
   ```

If DungeonMind contract identity has moved, STOP and rebrief rather than silently following latest.

### Steward bookkeeping prerequisite

DungeonMind PR #56 has merged. The living DungeonMind Steward handoff therefore must be updated to record:

- PR #56 merge `63ec810a...`;
- accepted implementation head `ba2ec6dc...`;
- four formal review cycles;
- canonical V0.1 aggregate `fd04a904...`;
- V0.1 disposition `V0_1_DUNGEONMIND_CONTRACT_FROZEN`;
- V0.2 as the active remaining V0 proof.

That bookkeeping may land as a tiny docs-only DungeonMind sync. It is a **pre-merge gate for V0.2**, not a reason to delay implementation work.

---

## §3 Binding authority

Read these before writing code.

### DungeonMind

1. `Docs/Architecture/AUTHORITY.md`
2. `Docs/Architecture/ARCHITECTURE-domain-agnostic-governed-memory-vnext.md`
3. `Docs/Architecture/ARCHITECTURE-vnext-read-path-and-performance.md`
4. `Docs/Roadmaps/ROADMAP.md`
5. `Docs/Handoffs/HANDOFF-STEWARDSHIP-vnext-roadmap.md`
6. merged V0.1 artifact:

   ```text
   Docs/Contracts/vnext/dm_vnext_contract_v1.json
   ```

7. vNext public contracts under:

   ```text
   src/dungeonmind/contracts/vnext/
   ```

The exact provider contract identity is the checked-in bundle aggregate plus its semantic-invariant manifest. Buddy does not get to define an equivalent local interpretation.

### DungeonMindBuddy

Read the current versions of:

```text
pyproject.toml
uv.lock
src/graph_memory/projection/world_projection.py
src/graph_memory/evidence/source_domain.py
apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
```

Also use current tests around direct DungeonMind reads, authority, object projection, retrieval, and contribution mapping as regression evidence.

Historical whole-world adoption/conformance reports may explain why the generic vNext contract exists, but they do not outrank current code or the frozen V0.1 contract.

---

## §4 Current consumer truth that V0.2 must preserve

V0.2 is a contract proof against the semantics Buddy already exposes. It is not permission to redesign those semantics.

### 4.1 World identity

Current Buddy uses `world_id` as the authority namespace.

vNext mapping:

```text
Buddy world_id
→ DungeonMind space_id
```

The value is preserved exactly.

Example:

```text
eldyrwild → eldyrwild
```

Do not mint a new space ID because the transport name changed.

### 4.2 Campaign scope

Current production mapping is:

```text
Buddy scope_mode = campaign
  → one campaign + world-owned/unscoped knowledge

Buddy scope_mode = world
  → all campaign scopes in the same world + world-owned/unscoped knowledge
```

vNext representation:

```text
campaign-specific assertion
  scope = [
    { axis = dungeonbuddy.scope:campaign, value = <campaign_id> }
  ]

world-global assertion
  scope = []
```

Campaign request:

```text
ScopeSelector(
  include_unscoped = true,
  bindings = [
    { axis = dungeonbuddy.scope:campaign, value = <campaign_id> }
  ],
  wildcard_axes = []
)
```

World / cross-campaign request:

```text
ScopeSelector(
  include_unscoped = true,
  bindings = [],
  wildcard_axes = [dungeonbuddy.scope:campaign]
)
```

There is no generic Kernel `campaign_id` field and no replacement `ScopeModeV3` enum.

### 4.3 Session focus is not authority scope

Current direct-read behavior explicitly treats session focus as presentation/ranking metadata, not admission.

Therefore V0.2 must **not** add `dungeonbuddy.scope:session` merely because sessions exist.

Represent focused session context through `FocusRef`.

For a campaign-qualified focus, use separate non-authoritative focus refs, for example:

```text
FocusRef(kind = dungeonbuddy.focus:campaign, id = C2)
FocusRef(kind = dungeonbuddy.focus:session,  id = session-28)
```

This lets a world/cross-campaign request remain cross-campaign while still carrying the current focus campaign + session for domain ranking/presentation later.

If implementation evidence shows session currently changes authority admission, STOP. Do not smuggle that behavior into focus or scope.

### 4.4 GM / PLAYER visibility

Product authorization remains outside DungeonMind.

Buddy maps an already-authorized role to effective Kernel audience labels.

Required mapping:

```text
PLAYER
→ [dungeonbuddy.visibility:player]

GM
→ [
     dungeonbuddy.visibility:player,
     dungeonbuddy.visibility:gm
   ]
```

Assertion visibility mapping:

```text
current visibility = player
→ LabelsAny([dungeonbuddy.visibility:player])

current visibility = gm
→ LabelsAny([dungeonbuddy.visibility:gm])
```

This preserves the useful property that GM sees player-visible material while PLAYER cannot satisfy a GM-only requirement.

Do not move product authentication/authorization logic into DungeonMind.

### 4.5 Standing / canon state

Required conceptual mapping:

```text
canonical   → established
provisional → provisional
retracted   → retracted
```

V0.2 proves the representation only. Historical migration details belong to V7.

### 4.6 Epistemic meaning and claim mode

The generic Kernel vocabulary is intentionally split:

```text
epistemic_basis
  asserted | inferred | speculative

claim_mode
  Buddy-owned qualified term
```

At minimum the Buddy domain fixture should declare representative claim modes:

```text
dungeonbuddy.claim:fact
dungeonbuddy.claim:belief
dungeonbuddy.claim:rumor
dungeonbuddy.claim:plan
dungeonbuddy.claim:observed_event
```

A normal asserted fact can therefore be represented as:

```text
epistemic_basis = asserted
claim_mode = dungeonbuddy.claim:fact
```

`source_derived_candidate` is **not** to be recreated as a new Kernel epistemic enum. The vNext architecture intentionally moves candidate/proposal state into governed contribution/disposition state. V0.2 may demonstrate that concept with a proposed assertion + unresolved/provisional disposition, but it must not freeze a full historical migration algorithm. V7 owns exact legacy translation.

### 4.7 Fictional time

Fictional time remains Buddy-owned domain data.

The preservation fixture must exercise a `DomainTemporalScope`, for example:

```text
kind = domain_ref
schema = dungeonbuddy.time:fictional_anchor_v1
payload = canonical JSON owned by Buddy
```

The exact fixture payload must be sufficient to distinguish campaign-qualified fictional/session chronology without requiring a Kernel `session_id` or fictional-time enum.

Do not implement temporal inference in V0.2.

### 4.8 Source classifications and source context

Current Buddy source domains are:

```text
recap
statblock
worldbuilding
npc_note
location_note
faction_note
item_note
session_memory
manual_seed
future_artifact
party_registry
```

Every current source-domain value must be representable as domain-qualified source classification, preferred mapping:

```text
recap          → dungeonbuddy.source:recap
statblock      → dungeonbuddy.source:statblock
worldbuilding  → dungeonbuddy.source:worldbuilding
...
```

The fixture must account for the full current `KNOWN_SOURCE_DOMAINS` set so a later new domain cannot silently disappear from the proof.

Current source campaign/session association is domain meaning, not a generic `SourceArtifact` field.

Preferred representation:

```text
DomainMetadataEntry(
  schema = dungeonbuddy.source:context_v1,
  payload = {
    campaign_id: ...,
    session_id: ...
  }
)
```

This metadata lives on the Buddy-owned source fixture while the frozen `SourceArtifactV3` remains generic.

### 4.9 World-object shape

The generic Kernel Entity is intentionally only identity.

Buddy World-object semantics must be expressible through assertions/profile terms:

```text
entity identity          → Entity
kind/classification      → TermRef assertion
label/summary/attribute  → Literal assertion
relationship             → EntityRef assertion
aliases                  → IdentityAlias
support/provenance       → EvidenceRef + SourceArtifact/SourceRevision
```

The V0.2 fixture must include at least:

- one person/NPC-like entity;
- one location-like entity;
- one classification term;
- one literal label or summary;
- one entity-ref relationship;
- one alias;
- campaign scope;
- player-visible and GM-only knowledge;
- evidence + source identity;
- fictional-time domain metadata/scope.

The exact ontology terms are Buddy/profile-owned. Prefer an already accepted `dnd5e:` term where current semantics truly match; otherwise use an explicit Buddy-qualified term and document the decision. Do not coerce unlike concepts solely to reuse a namespace.

---

## §5 Required Buddy-owned domain fixture

Add one data-only `DomainContractDescriptor` fixture for the preservation proof.

Minimum semantic contents:

```text
domain_id = dungeonbuddy.world

scope_axes = [
  dungeonbuddy.scope:campaign
]

visibility_labels = [
  dungeonbuddy.visibility:player,
  dungeonbuddy.visibility:gm
]

claim_modes includes at least:
  dungeonbuddy.claim:fact
  dungeonbuddy.claim:belief
  dungeonbuddy.claim:rumor
  dungeonbuddy.claim:plan
  dungeonbuddy.claim:observed_event

temporal_extension_schemas includes:
  dungeonbuddy.time:fictional_anchor_v1

source_annotation_schemas includes:
  dungeonbuddy.source:context_v1

admission_policy_id = opaque Buddy-owned policy identity
```

Binding ruling:

> **Do not declare session as a scope axis in this V0 proof.**

This descriptor is data-only. It does not register or execute a runtime policy.

---

## §6 Required semantic-profile fixture

Add one `SemanticProfileDescriptorV2` fixture proving that World-object meaning can live outside Kernel structure.

It should contain enough vocabulary to validate the §4.9 witness, including:

```text
term namespaces owned by Buddy / D&D
classification term(s)
literal predicate(s)
entity-ref predicate(s)
```

Recommended shape:

```text
profile_id = dungeonbuddy.dnd5e
profile_revision = explicit immutable fixture revision
term_namespaces = [dungeonbuddy, dnd5e]
```

Do not copy the current namespaces-only `dm_semantic_profile_v1` descriptor and call it v2 without adding the validation-relevant predicate/classification data required by the frozen V0.1 contract.

Create exact `DomainContractRef` and `SemanticProfileRef` values from canonical descriptor digests and prove they match the fixture bytes/objects deterministically.

---

## §7 Exact provider pin strategy

V0.2 must pin **the artifact**, not merely a commit that happens to contain it.

### 7.1 Dependency pin

Update Buddy from:

```text
dungeonmind[postgres] @ git+https://github.com/Drakosfire/DungeonMind.git@d8f7a9f0d6b256f5cf4588987520bf286f1eade3
```

to:

```text
dungeonmind[postgres] @ git+https://github.com/Drakosfire/DungeonMind.git@63ec810a02f18c4e25af228f6fdb19d99d12579e
```

Update `uv.lock` accordingly.

The provider diff from the current Buddy pin through PR #56 adds vNext docs/contracts/tests/scripts; it does not modify the existing DungeonMind application/infrastructure runtime paths. That is why this repin belongs in V0.2 rather than a separate runtime-upgrade PR.

Still run the current direct-read/write regression cohort. Unexpected behavior drift is a STOP condition.

### 7.2 Exact bundle copy

Vendor the exact provider artifact byte-for-byte into Buddy under an obvious path, preferred:

```text
Docs/Contracts/dungeonmind/dm_vnext_contract_v1.json
```

Source:

```text
Drakosfire/DungeonMind
commit: 63ec810a02f18c4e25af228f6fdb19d99d12579e
path: Docs/Contracts/vnext/dm_vnext_contract_v1.json
aggregate: fd04a9047b8ed79aaa5e710b2247ce1b2654c0e44e05d24fafb2adecb9e7b7ea
```

Do not regenerate an independently equivalent bundle from Buddy code.

### 7.3 Buddy pin manifest

Add a small Buddy-owned pin manifest, preferred:

```text
Docs/Contracts/dungeonmind/dm_vnext_contract_pin_v1.json
```

It should record at least:

```text
schema = dmb_dungeonmind_vnext_contract_pin_v1
provider_repository
provider_commit
provider_bundle_path
provider_contract_family
provider_contract_revision
provider_aggregate_sha256
vendored_bundle_sha256
```

The pin manifest is Buddy's declaration of exactly what it consumed.

Tests should verify the vendored provider bundle's own aggregate according to the provider algorithm, but must not reconstruct a substitute schema family locally.

---

## §8 Preservation fixture

Add one canonical Buddy preservation fixture, preferred:

```text
tests/fixtures/vnext/dungeonbuddy_domain_preservation_v1.json
```

It should contain explicit paired examples rather than prose-only claims.

At minimum include:

### Request/context cases

```text
campaign + GM
campaign + PLAYER
world/cross-campaign + GM
session-focused campaign request
session-focused world/cross-campaign request
```

For every case record:

```text
current Buddy meaning/input
expected generic ProjectionRequest
why the mapping preserves admission/focus semantics
```

### Knowledge cases

```text
world-global assertion
campaign-specific assertion
player-visible assertion
gm-only assertion
established/provisional/retracted standing examples
fictional-time domain_ref
World-object classification/literal/relationship
IdentityAlias
evidence/source support
```

### Source cases

The fixture or an adjacent mapping ledger must cover exactly the current Buddy `KNOWN_SOURCE_DOMAINS` set.

### Governance candidate case

Demonstrate that proposal/candidate state can be carried through `KnowledgeContribution` / `ContributionDisposition` without inventing a Kernel `source_derived_candidate` epistemic enum.

This is a representation proof, not a historical migration algorithm.

---

## §9 Machine-readable acceptance artifact

Add a small V0.2 result artifact after the proof is known, preferred:

```text
Docs/Contracts/vnext/dmb_v0_2_contract_acceptance_v1.json
```

Do **not** use the future V8 name `dm_vnext_contract_acceptance_v1`.

Record at minimum:

```text
schema
Buddy base/head SHA
DungeonMind provider merge SHA
DungeonMind accepted V0.1 implementation head
DungeonMind contract aggregate
vendored provider bundle SHA-256
Buddy DomainContract descriptor path + canonical SHA-256
Buddy SemanticProfile descriptor path + canonical SHA-256
preservation fixture path + canonical SHA-256
source-domain mapping coverage digest or exact set
verification disposition
```

The artifact should become the durable cross-repository V0 witness the Steward can cite when declaring `VNEXT_CONTRACT_FROZEN`.

---

## §10 In scope

1. Repin the installed DungeonMind dependency to merged PR #56.
2. Update `uv.lock`.
3. Vendor the exact frozen DungeonMind contract bundle.
4. Add Buddy's exact provider pin manifest.
5. Add a data-only Buddy `DomainContractDescriptor` fixture.
6. Add a data-only Buddy `SemanticProfileDescriptorV2` fixture.
7. Add one canonical DungeonBuddy preservation fixture.
8. Add focused tests validating all fixtures through the frozen provider models.
9. Prove the current Buddy request/context meanings map onto the frozen generic projection contract.
10. Prove all current Buddy source-domain values are representable through qualified source classification.
11. Prove a representative World object needs no new generic Kernel field.
12. Add the V0.2 machine-readable acceptance artifact.
13. Run regression gates proving the provider repin did not alter current production behavior.

---

## §11 Out of scope — falsification

Any of the following means the PR has crossed its lease:

- changing production World Graph read routing;
- changing `world_graph_reads.py` request mapping to vNext;
- replacing current `WorldGraphProjectionRequestV2` in production;
- changing write/publication behavior;
- creating a vNext KnowledgeSpace/repository;
- migrating Eldyrwild or any live authority;
- bridge-genesis execution;
- dual write;
- runtime DomainAdmissionPolicy implementation/registration;
- application-layer vNext `KnowledgeReadContext`;
- parsed revision/index work;
- deleting current World contracts;
- changing product API/DTO/UI schemas;
- moving product authentication into DungeonMind;
- implementing fictional-time inference;
- solving every D&D ontology term;
- performance claims;
- starting V1/V2/V6 runtime work inside this PR.

This PR proves the language is sufficient. It does not start speaking that language in production.

---

## §12 Preferred write lease

Expected files:

```text
pyproject.toml
uv.lock

Docs/Contracts/dungeonmind/dm_vnext_contract_v1.json
Docs/Contracts/dungeonmind/dm_vnext_contract_pin_v1.json
Docs/Contracts/vnext/dungeonbuddy_world_domain_contract_v1.json
Docs/Contracts/vnext/dungeonbuddy_dnd5e_semantic_profile_v2.json
Docs/Contracts/vnext/dmb_v0_2_contract_acceptance_v1.json

tests/fixtures/vnext/dungeonbuddy_domain_preservation_v1.json
tests/test_v0_2_dungeonmind_vnext_contract_acceptance.py
```

One small test/helper module is allowed if it makes canonical digest verification or fixture loading clearer.

Production files under these families are **not** expected:

```text
apps/live_control_server/services/
apps/live_control_server/routes/
apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
src/graph_memory/kernel*
apps/live-control-ui/
application_state/
```

Touching them is a STOP/rebrief unless the only change is an unavoidable import/test fixture correction caused by the additive pin and the Steward explicitly approves it.

---

## §13 Acceptance matrix

Focused tests must prove at least the following.

### Exact provider identity

1. `pyproject.toml` pins DungeonMind exactly to `63ec810a...`.
2. lockfile resolves that exact commit.
3. vendored bundle is the provider artifact, not a Buddy-generated equivalent.
4. bundle `aggregate_sha256` is exactly `fd04a904...`.
5. recomputing the provider aggregate from the vendored artifact according to its documented algorithm matches the embedded value.
6. Buddy pin manifest names the exact provider repository/commit/path/aggregate.
7. installed `dungeonmind.contracts.vnext` imports successfully from the repinned dependency.

### Domain contract

8. Buddy DomainContract validates through frozen `DomainContractDescriptor`.
9. only `dungeonbuddy.scope:campaign` is declared as authority scope in the V0.2 descriptor.
10. GM/player labels are Buddy-qualified terms, not Kernel enums.
11. claim modes are Buddy-qualified terms.
12. fictional time is declared as a domain temporal schema.
13. source campaign/session context is declared as a Buddy source annotation schema.
14. descriptor canonical digest matches its `DomainContractRef`.

### Semantic profile

15. v2 profile validates through frozen `SemanticProfileDescriptorV2`.
16. representative classification, literal, and entity-ref predicates are declared.
17. canonical profile digest matches its `SemanticProfileRef`.
18. no DungeonMind generic contract needs an NPC/location/faction enum to validate the World-object fixture.

### Current Buddy request semantics

19. exact `world_id` value becomes exact `space_id` value.
20. campaign request uses `include_unscoped=true` + exact campaign binding.
21. world/cross-campaign request uses `include_unscoped=true` + campaign wildcard.
22. PLAYER maps to player label only.
23. GM maps to player + GM labels.
24. session focus is represented by FocusRefs and does not alter scope selection.
25. campaign-qualified session focus can be represented without a generic `session_id` field.
26. unknown Buddy scope/admissibility fixture values fail the local proof instead of passing through.

### Knowledge preservation

27. unscoped/world-global assertion validates.
28. campaign-scoped assertion validates.
29. player-visible assertion validates.
30. GM-only assertion validates.
31. canonical/provisional/retracted meanings are representable through `KnowledgeStanding`.
32. fictional-time domain_ref validates with canonical JSON.
33. representative World object validates as Entity + assertions + alias.
34. relationship is represented as an EntityRef assertion.
35. literal attribute is represented as a Literal assertion.
36. evidence/source identity validates without World/campaign/session fields in generic source contracts.
37. proposal/candidate state is representable through contribution/disposition rather than a new Kernel epistemic enum.

### Source-domain coverage

38. the fixture mapping keys equal current `KNOWN_SOURCE_DOMAINS` exactly.
39. every current source domain maps to a syntactically valid qualified `source_classification`.
40. source campaign/session association is Buddy domain metadata, not a generic source field.

### No runtime cutover

41. current production World read adapter files are unchanged.
42. current product API/DTO/UI schemas are unchanged.
43. no migration or authority-state mutation is introduced.
44. existing direct-read/write owning tests remain green after the dependency repin.

---

## §14 Regression gates

At minimum run:

```bash
uv sync --locked

uv run pytest -q \
  tests/test_v0_2_dungeonmind_vnext_contract_acceptance.py \
  tests/test_cutover_direct_dungeonmind_world_graph_reads.py \
  tests/test_cutover_dungeonmind_world_graph_authority.py \
  tests/test_world_graph_object_projection.py \
  tests/test_world_graph_projection_routes.py \
  tests/test_world_graph_retrieval_routes.py

uv run ruff check .
```

Also run the repository's current required non-live/default suite and any dependency/import gate required by current CI.

If live PostgreSQL tests are environment-gated, report exact skips honestly; do not call them passing when they did not execute.

Run:

```bash
git diff --check
```

and an explicit forbidden-path diff guard showing no production routing/UI/migration change.

### Dependency repin regression rule

If current production behavior changes after the `d8f7a9f... → 63ec810...` repin:

```text
same failure on exact old Buddy base / old pin → inherited baseline
new only on V0.2 head               → blocker
cannot establish                    → blocker
```

Do not repair unrelated runtime behavior inside the V0.2 contract proof.

---

## §15 Stop / rebrief conditions

STOP instead of improvising if any of these occur:

1. A required Buddy semantic cannot be represented without adding a new field to the frozen DungeonMind generic contract.
2. Session must become an authority scope to match current behavior.
3. PLAYER fail-closed behavior requires Kernel knowledge of the product role rather than effective labels.
4. Buddy must add a `world_id`, `campaign_id`, `GM`, `PLAYER`, `NPC`, or fictional-time field to a generic vNext provider model.
5. The provider bundle cannot be pinned exactly without Buddy regenerating its own supposedly equivalent contract.
6. `SemanticProfileRef` / `DomainContractRef` cannot pin the Buddy descriptors without weakening existing identity rules.
7. A DomainContract fixture requires executable module paths, callbacks, URLs, or arbitrary hooks.
8. The DungeonMind repin changes existing production behavior unexpectedly.
9. Exact current source-domain semantics require a new Kernel `SourceDomain` enum.
10. Candidate/proposal state can only be preserved by recreating `source_derived_candidate` as Kernel epistemic vocabulary.
11. The proof requires live authority migration or publication.
12. A product/API/UI change becomes necessary to make the fixture pass.
13. V0.2 starts implementing the V6 runtime domain policy instead of proving the frozen contract shape.

Required stop report:

```text
Stop condition:
Current Buddy semantic affected:
Frozen DungeonMind contract shape:
Why the semantic cannot be represented:
Why a local workaround would create drift:
Options considered:
Recommended architecture/roadmap change:
V0.2 disposition:
V1/V6 impact:
```

---

## §16 What remains false after V0.2

Even after a successful V0.2 merge:

- production Buddy still uses current World-shaped DungeonMind read/write contracts;
- no vNext KnowledgeSpace exists in durable storage;
- no live authority has been migrated;
- no vNext `ParsedKnowledgeRevision` exists;
- no revision-local vNext indexes exist;
- no `KnowledgeReadContext` exists;
- no generic/domain admission runtime exists;
- no V6 DungeonBuddy runtime DomainContract implementation is registered;
- no vNext projection/retrieval service is serving product traffic;
- no bridge-genesis migration exists;
- no dual write exists;
- no old World history is rewritten;
- no old public contract is removed;
- no product route/UI contract changes;
- no performance improvement is claimed;
- no V8 joint semantic/performance acceptance artifact exists;
- no V9 cutover has happened.

What becomes true is narrower and important:

> Both repositories agree on one exact vNext language, and Buddy has proved it can express its domain through that language without changing the Kernel contract.

---

## §17 Handback requirements

Return all of the following.

### Repository identity

```text
Buddy base SHA
Buddy head SHA
branch
PR number / URL / state
commit list
changed-path inventory
paths outside lease, if any
```

### Provider pin

```text
DungeonMind dependency SHA
provider bundle source path
provider aggregate
vendored bundle byte/canonical SHA-256
pin manifest path + digest
proof provider aggregate recomputes exactly
```

### Buddy domain identity

```text
DomainContract descriptor path
DomainContract canonical SHA-256
DomainContractRef
SemanticProfileDescriptorV2 path
SemanticProfile canonical SHA-256
SemanticProfileRef
preservation fixture path + canonical SHA-256
```

### Mapping proof

Return the exact mapping table used for:

```text
world_id → space_id
campaign scope
world/cross-campaign scope
GM/PLAYER → effective audience labels
assertion visibility
standing
session focus
fictional time
source domain classification
source campaign/session metadata
World-object classification/literal/relationship/alias
candidate/proposal governance state
```

Any intentional non-mapping must be called out explicitly with its owning future phase.

### Verification

Exact commands + results for:

```text
focused V0.2 tests
current DungeonMind direct-read/write regressions
ruff/type/import gates required by repo
full non-live/default suite
lockfile check
diff check
forbidden-path guard
```

### Disposition

Only one of:

```text
V0_2_DUNGEONBUDDY_DOMAIN_PROOF_ACCEPTED
V0_2_HOLD
V0_2_REBRIEF_REQUIRED
```

---

## §18 Steward review lens

The Steward review should ask:

1. **Did Buddy pin the exact provider artifact, or merely something equivalent-looking?**
2. **Can all required Buddy meanings be expressed without changing frozen Kernel structure?**
3. **Did campaign/world/GM/player/session semantics preserve their current authority boundaries?**
4. **Did session remain focus rather than silently becoming scope?**
5. **Did source classification/context remain Buddy-owned data?**
6. **Can a representative World object exist as generic Entity + assertions instead of Kernel ontology?**
7. **Did candidate/proposal state stay in governance rather than leak back into epistemic enums?**
8. **Did the dependency repin leave current production behavior untouched?**
9. **Did this PR avoid starting V6 runtime implementation early?**
10. **Is the machine-readable V0.2 acceptance artifact strong enough for a new Steward to declare V0 complete without chat history?**

Merge-worthy means:

> **DungeonMindBuddy has consumed the exact frozen DungeonMind V0.1 contract and demonstrated, with canonical fixtures and digests, that its World/TTRPG semantics fit that contract without local Kernel invention.**

On exact-head PASS, the Steward should record:

```text
V0_2_DUNGEONBUDDY_DOMAIN_PROOF_ACCEPTED
VNEXT_CONTRACT_FROZEN
```

Then update the living DungeonMind Steward handoff before another roadmap PR merges.
