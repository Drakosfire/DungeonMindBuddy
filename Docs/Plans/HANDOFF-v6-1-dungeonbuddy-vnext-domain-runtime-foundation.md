---
pr_body_template: |
  ## Handoff pointer
  - Repository: Drakosfire/DungeonMindBuddy
  - Direction: DESIGN → CODE → REVIEW
  - Roadmap slice: V6.1 — DungeonBuddy vNext domain runtime foundation
  - Handoff: Docs/Plans/HANDOFF-v6-1-dungeonbuddy-vnext-domain-runtime-foundation.md
  - Buddy base: 3f1aa1baf9a72c16adf747ad5bf81e9e8b249a6a
  - DungeonMind runtime: 6edb9e40d1dc930f537c66deb1afbd1b99002844
  - Buddy DomainContract: dungeonbuddy.world revision 2

  Turn the accepted Buddy vNext domain mapping into an executable runtime seam:
  exact request mapping, pinned domain/profile construction, Buddy-owned admission
  policy, and KnowledgeReadContext assembly. Leave production World Graph routes,
  live authority, migration, and cutover unchanged.
---

# HANDOFF — V6.1 DungeonBuddy vNext domain runtime foundation

**Created:** 2026-09-24  
**Status:** ACTIVE — ready for implementation  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Roadmap:** V6 — DungeonBuddy domain implementation  
**Slice:** V6.1 — executable domain runtime foundation  
**Buddy base:** `3f1aa1baf9a72c16adf747ad5bf81e9e8b249a6a`  
**DungeonMind runtime:** `6edb9e40d1dc930f537c66deb1afbd1b99002844` — merged PR #75  
**V6.0.1 predecessor:** PR #747 — merged `99b8d431d6558f4d6028c736d41ebaa97af84ca5`  
**Corrected DomainContract:** `dungeonbuddy.world` revision `2`  
**DomainContract digest:** `d12f3a517a37d29a2ba52455d9ae1691bc5e4ff3fd6853b701a9e28e46ec65cd`  
**SemanticProfile:** `dungeonbuddy.dnd5e` revision `1`  
**SemanticProfile digest:** `51ea47ff45bc86ea158939c34a5769e7ee56de3911278d473570e3795edb7e14`  
**Runtime witness:** `tests/fixtures/vnext/dungeonbuddy_domain_runtime_preservation_v2.json`  
**Suggested branch:** `vnext/v6-1-domain-runtime-foundation`  
**Suggested PR title:** `VNEXT: implement DungeonBuddy domain runtime foundation`  
**Successor:** V6.2 — vNext read adaptation + World-object DTO preservation

## 1. Mission

Answer one question:

> Can DungeonMindBuddy execute its accepted World/TTRPG domain semantics through the generic DungeonMind vNext read runtime without switching production authority or reintroducing Buddy semantics into Kernel code?

This PR creates the reusable Buddy-owned seam that V6.2 will consume.

A PASS means this chain is real:

```text
Buddy semantic input
→ exact generic ProjectionRequest
→ exact Buddy DomainContract + SemanticProfile
→ Buddy DomainAdmissionPolicy
→ DungeonMind KnowledgeReadContext
→ generic Kernel admission
```

Disposition:

```text
V6_1_DUNGEONBUDDY_DOMAIN_RUNTIME_ACCEPTED
```

## 2. Re-anchor

Before coding, verify:

```text
DungeonMindBuddy main:
  3f1aa1baf9a72c16adf747ad5bf81e9e8b249a6a

DungeonMind dependency:
  6edb9e40d1dc930f537c66deb1afbd1b99002844

DomainContract revision 2 digest:
  d12f3a517a37d29a2ba52455d9ae1691bc5e4ff3fd6853b701a9e28e46ec65cd

SemanticProfile revision 1 digest:
  51ea47ff45bc86ea158939c34a5769e7ee56de3911278d473570e3795edb7e14

V6.0.1 disposition:
  V6_0_1_DUNGEONBUDDY_EVIDENCE_METADATA_CONTRACT_CORRECTED
```

If any identity changed materially, rebrief rather than following latest silently.

The dependency repin and evidence-metadata correction are already complete. Do not redo them.

## 3. Historical bookkeeping

Buddy still has one stale V0.2 acceptance field:

```text
Docs/Contracts/vnext/dmb_v0_2_contract_acceptance_v1.json
reviewed_implementation_head_sha = null
```

The accepted substantive V0.2 head is:

```text
2a17226b6b0b25a1084f404b6aca8bde442e4713
```

It is permitted to seal this field and its existing test in the first V6.1 commit. Do not alter the historical revision-1 descriptor digest, fixture digest, provider provenance, or V0 aggregate.

This bookkeeping is not the V6.1 capability.

## 4. Settled semantics — do not redesign

### Identity

```text
Buddy world_id → DungeonMind space_id
```

Validate nonblank, preserve exact bytes. No trim/case-fold/remint.

### Scope

Only authority scope axis:

```text
dungeonbuddy.scope:campaign
```

Campaign request:

```text
include_unscoped = true
binding campaign = exact campaign_id
```

World request:

```text
include_unscoped = true
wildcard campaign axis
```

### Focus

Session is not authority scope.

For session focus:

```text
FocusRef(dungeonbuddy.focus:campaign, exact campaign_id)   # when supplied
FocusRef(dungeonbuddy.focus:session, exact session_id)
```

Focus must not alter generic admission.

### Effective visibility

```text
player → [dungeonbuddy.visibility:player]

gm → [
  dungeonbuddy.visibility:gm,
  dungeonbuddy.visibility:player
]
```

Buddy owns product authorization. Kernel sees labels only.

### Standing

Default request standing:

```text
player → established
gm     → established + provisional
```

Player may not request provisional/retracted through this mapping.

### Domain identity

Runtime must use:

```text
DomainContract:
  dungeonbuddy.world / revision 2

SemanticProfile:
  dungeonbuddy.dnd5e / revision 1

Policy:
  dungeonbuddy.admission:world_v1
```

V6.0.1 settled evidence/source metadata ownership. Do not reopen it.

## 5. Important policy ruling

Current preserved Buddy authority semantics are already expressed by generic Kernel gates:

```text
standing
scope
domain declarations
visibility
semantic profile
evidence/source validity
```

Therefore V6.1's Buddy admission policy should be intentionally non-widening and currently non-filtering after those gates.

Implement conceptually:

```python
class DungeonBuddyWorldAdmissionPolicy:
    policy_id = "dungeonbuddy.admission:world_v1"

    def narrow(...):
        return True
```

This is not a placeholder hack. It is the explicit statement that **current Buddy admission has no additional domain-only exclusion beyond the accepted generic representation**.

Future domain-specific narrowing requires an explicit accepted change. The policy can never recover a candidate the Kernel rejected.

## 6. Runtime module

Prefer a new isolated package:

```text
src/graph_memory/vnext/
  __init__.py
  domain_runtime.py
```

Exact names may vary if current package conventions make a nearby location clearly better.

The module should provide equivalents of:

```text
DungeonBuddyVNextProjectionInput
build_dungeonbuddy_projection_request(...)
dungeonbuddy_world_domain_contract()
dungeonbuddy_dnd5e_semantic_profile()
DungeonBuddyWorldAdmissionPolicy
build_dungeonbuddy_read_context(...)
```

### Projection input

Use a typed/frozen input shape representing only the accepted mapping:

```text
world_id
scope_mode: campaign | world
role: gm | player
campaign_id: optional/required by mode
session_id: optional
standing_selector: optional explicit override
revision_id: optional exact revision pin
```

Do not use arbitrary dictionaries as the long-term public runtime seam merely because V0.2 used a test helper.

### Projection request mapper

Its output must be a real DungeonMind `ProjectionRequest`.

Behavior must match the accepted V0.2 mapping exactly:

- exact lowercase `gm` / `player` only;
- campaign mode requires nonblank campaign ID;
- world mode uses campaign wildcard;
- IDs are validated but not normalized;
- session focus remains focus;
- standing defaults above;
- invalid combinations fail closed.

If an explicit `revision_id` is supplied, preserve it exactly.

### Descriptor constructors

Runtime code must not depend on reading `Docs/**` files.

Construct the descriptors as Buddy-owned runtime models/constants and pin them by tests against the canonical checked-in JSON descriptors:

```text
Docs/Contracts/vnext/dungeonbuddy_world_domain_contract_v2.json
Docs/Contracts/vnext/dungeonbuddy_dnd5e_semantic_profile_v2.json
```

Canonical runtime descriptor digests must equal the checked-in digests.

### Context factory

Provide a small factory conceptually:

```text
build_dungeonbuddy_read_context(
  parsed_revision,
  projection_input,
  source_reader,
) -> KnowledgeReadContext
```

It must:

1. build the exact generic request;
2. instantiate/pin DomainContract revision 2;
3. instantiate/pin SemanticProfile revision 1;
4. use `DungeonBuddyWorldAdmissionPolicy`;
5. delegate authority enforcement to DungeonMind `KnowledgeReadContext`.

Do not wrap or reproduce Kernel admission rules.

## 7. Preservation proof

Use the already-accepted runtime witness:

```text
tests/fixtures/vnext/dungeonbuddy_domain_runtime_preservation_v2.json
```

Do not create a third semantic fixture unless implementation evidence requires a new semantic case.

### Request mapping proof

For every existing `request_context_cases` record:

```text
Buddy input
→ production V6.1 request mapper
→ exact expected ProjectionRequest
```

Structural equality is required.

Retain negative proofs for:

- unknown scope;
- missing campaign ID in campaign mode;
- unknown role;
- padded/case-shifted roles;
- blank world/campaign/session IDs;
- player request for non-established standing.

### Runtime admission proof

Build a real `ParsedKnowledgeRevision`, `InMemoryKnowledgeSourceReader`, and V6.1 `KnowledgeReadContext` from the v2 fixture.

Prove at minimum:

**campaign + GM**
- world-global established assertion admitted;
- campaign player-visible established assertions admitted;
- campaign GM-only provisional plan admitted;
- retracted assertion excluded by standing.

**campaign + player**
- world-global established assertion admitted;
- campaign player-visible established assertions admitted;
- GM-only assertion excluded by visibility;
- provisional/retracted material not admitted.

**world + GM**
- campaign-scoped assertions are admitted through wildcard scope.

**session-focused request**
- admission set is identical to the equivalent non-focused request;
- focus is preserved on the request/context.

Also prove:

```text
policy.policy_id == DomainContract.admission_policy_id
```

and that candidates rejected by generic scope/visibility/standing/evidence rules never become admitted through the Buddy policy.

## 8. Runtime identity proof

Tests must pin:

```text
runtime DomainContract digest
  == d12f3a517a37d29a2ba52455d9ae1691bc5e4ff3fd6853b701a9e28e46ec65cd

runtime SemanticProfile digest
  == 51ea47ff45bc86ea158939c34a5769e7ee56de3911278d473570e3795edb7e14
```

Also prove the corrected evidence-backed witness passes without modifying:

```text
EvidenceRefV3.domain_metadata:
  dungeonbuddy.domain_metadata:world_context_v1

SourceArtifactV3.domain_metadata:
  dungeonbuddy.source:context_v1
```

## 9. Scope

Expected changed paths:

```text
Docs/Plans/HANDOFF-v6-1-dungeonbuddy-vnext-domain-runtime-foundation.md

src/graph_memory/vnext/__init__.py
src/graph_memory/vnext/domain_runtime.py

tests/test_v6_1_dungeonbuddy_vnext_domain_runtime.py
```

Permitted bookkeeping:

```text
Docs/Contracts/vnext/dmb_v0_2_contract_acceptance_v1.json
tests/test_v0_2_dungeonmind_vnext_contract_acceptance.py
```

Focused fixture/descriptor assertions may be added to the V6.1 test.

No `pyproject.toml` / `uv.lock` change is expected: PR #747 already landed the DungeonMind runtime pin.

## 10. Explicitly out of scope

Do not modify:

```text
apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
production World Graph service/route wiring
frontend/API DTO contracts
live authority data
DungeonMind repository
WorldKeeper runtime/integration
bridge-genesis migration
legacy → vNext translation
production read switching
production write switching
prospective publication adapters
World-object DTO projection
search/retrieval route behavior
```

Those belong to V6.2+, V7, or later cutover work.

V6.1 is a library/runtime foundation only.

## 11. Acceptance matrix

A PASS requires:

1. DomainContract revision 2 runtime constructor matches canonical digest.
2. SemanticProfile runtime constructor matches canonical digest.
3. policy identity matches the descriptor.
4. policy cannot widen generic admission.
5. all positive request fixture cases map exactly.
6. malformed/unknown Buddy request inputs fail closed.
7. campaign GM admission matches expected preserved semantics.
8. campaign player admission matches expected preserved semantics.
9. world GM wildcard scope works.
10. session focus does not change admission.
11. corrected evidence/source metadata passes real Kernel admission.
12. historical V0.2 and V6.0.1 tests remain green.
13. no production route/read/write path changed.

## 12. Verification

Run:

```text
uv sync --locked

uv run pytest -q \
  tests/test_v0_2_dungeonmind_vnext_contract_acceptance.py \
  tests/test_v6_0_1_dungeonbuddy_evidence_metadata_contract.py \
  tests/test_v6_1_dungeonbuddy_vnext_domain_runtime.py

uv run pytest -q tests/test_world_graph_object_projection.py

uv run ruff check \
  src/graph_memory/vnext \
  tests/test_v6_1_dungeonbuddy_vnext_domain_runtime.py

git diff --check
```

Also run the current default/non-live suite. If inherited collection failures remain, compare exact base/head and classify rather than repairing unrelated debt.

## 13. Stop conditions

Stop and rebrief if:

- current Buddy semantics require session to become authority scope;
- GM/player product roles must enter Kernel runtime;
- the policy must widen/recover a generic Kernel rejection;
- runtime descriptors cannot reproduce the accepted v2/profile digests;
- valid v2 evidence still fails generic admission;
- implementing this seam requires production World Graph routing changes;
- a new Kernel contract or runtime capability is required;
- migration/live authority is needed to prove V6.1.

## 14. Handback

Return:

```text
base SHA
exact head SHA
branch / PR
commit list
changed paths

runtime DomainContract digest
runtime SemanticProfile digest

request mapping proof results
admission preservation proof results
negative/fail-closed proof results

focused tests
World Graph regression
default-suite classification
Ruff
diff check

what remains false
```

## 15. Acceptance token

Only Steward review may record:

```text
V6_1_DUNGEONBUDDY_DOMAIN_RUNTIME_ACCEPTED
```

A PASS means Buddy has one executable, pinned vNext domain runtime seam.

It does **not** mean production reads use it.

## 16. Successor

After V6.1 acceptance, dispatch V6.2:

```text
V6.2 — vNext read adaptation + World-object DTO preservation
```

V6.2 may adapt the current Buddy read intents onto the V6.1 context/read services and prove resulting generic vNext reads can reconstruct the product-facing World-object semantics.

Production switching remains later.
