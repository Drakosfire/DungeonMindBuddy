# HANDOFF — V6.0.1 DungeonBuddy evidence-metadata contract correction

**Created:** 2026-09-23  
**Status:** COMPLETE — `V6_0_1_DUNGEONBUDDY_EVIDENCE_METADATA_CONTRACT_CORRECTED`
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**DungeonMindBuddy base:** `99ec0d56911b62ad9b9d63db1c8f9406ca4f319d`  
**DungeonMind runtime target:** `6edb9e40d1dc930f537c66deb1afbd1b99002844` — merged PR #75  
**Frozen DungeonMind V0 aggregate:** `fd04a9047b8ed79aaa5e710b2247ce1b2654c0e44e05d24fafb2adecb9e7b7ea`  
**Predecessor Buddy proof:** PR #719 — V0.2 domain preservation proof  
**Blocked successor:** V6.1 — DungeonBuddy vNext domain runtime foundation  
**Suggested branch:** `contracts/v6-0-1-evidence-metadata-ownership-correction`  
**Suggested PR title:** `CONTRACTS: correct DungeonBuddy vNext evidence metadata ownership`
**Accepted implementation head:** `1f5c47ab20605b4e07b2afe8db65f9d7152388e0`
**Substantive PASS review:** `5299327752`

## 1. Mission

Repair one accepted Buddy domain-contract mismatch discovered when V6.1 first exercised the frozen vNext contract through DungeonMind V5 runtime admission.

The question is:

> Can DungeonBuddy preserve the accepted V0.2 evidence meaning while declaring that meaning in the exact DomainContract bucket DungeonMind uses for `EvidenceRefV3` / `SourceArtifactV3` metadata, without changing the frozen DungeonMind contract or rewriting the historical V0.2 proof?

A PASS should make V6.1 executable again without changing generic Kernel semantics.

## 2. Observed stop condition

The accepted V0.2 preservation fixture contains:

```text
EvidenceRefV3
  evidence_ref_id = ev:session-28-mireward-arrival
  domain_metadata:
    schema = dungeonbuddy.domain_metadata:world_context_v1
    payload:
      context_type = arrival_scene
```

The accepted Buddy DomainContract revision 1 declares:

```text
domain_metadata_schemas:
  dungeonbuddy.domain_metadata:world_context_v1

source_annotation_schemas:
  dungeonbuddy.source:context_v1
```

DungeonMind runtime admission is explicit:

```text
Assertion.metadata.domain_metadata
  -> DomainContract.domain_metadata_schemas

EvidenceRefV3.domain_metadata
SourceArtifactV3.domain_metadata
  -> DomainContract.source_annotation_schemas
```

Therefore the accepted evidence object is structurally valid but not admissible under its pinned DomainContract.

Every evidence-backed assertion using that evidence is rejected with:

```text
domain_declaration
```

before DungeonBuddy's domain policy executes.

## 3. Steward ruling

This is a **DungeonBuddy DomainContract mapping defect**, not a DungeonMind runtime defect.

Do not change DungeonMind `evidence_chain_passes()` to accept `domain_metadata_schemas` for evidence/source metadata.

Rationale:

1. DungeonMind already applies a coherent ownership split.
2. `source_annotation_schemas` is the only declaration surface governing metadata attached to `EvidenceRefV3` and `SourceArtifactV3`.
3. Broadening the Kernel gate to a union of domain/source schema lists would weaken declaration precision for every domain.
4. The frozen V0 contract does not need a structural change.
5. The V0.2 proof failed to exercise runtime admission; this is exactly the kind of semantic mismatch V6 exists to expose.

## 4. Preserve historical V0.2 truth

Do **not** mutate the historical accepted descriptor in place.

Keep:

```text
Docs/Contracts/vnext/dungeonbuddy_world_domain_contract_v1.json
domain_revision = 1
```

byte-for-byte unchanged.

Keep the frozen provider bundle and aggregate unchanged.

Do not rewrite the historical V0.2 preservation fixture merely to make the old proof appear as though it exercised V5 runtime admission.

Instead, add a corrected immutable Buddy domain revision.

## 5. Corrected DomainContract revision

Create:

```text
Docs/Contracts/vnext/dungeonbuddy_world_domain_contract_v2.json
```

with:

```text
schema_version = dm_domain_contract_v1
domain_id = dungeonbuddy.world
domain_revision = 2
admission_policy_id = dungeonbuddy.admission:world_v1

scope_axes:
  dungeonbuddy.scope:campaign

visibility_labels:
  dungeonbuddy.visibility:gm
  dungeonbuddy.visibility:player

claim_modes:
  dungeonbuddy.claim:belief
  dungeonbuddy.claim:fact
  dungeonbuddy.claim:observed_event
  dungeonbuddy.claim:plan
  dungeonbuddy.claim:rumor

temporal_extension_schemas:
  dungeonbuddy.time:fictional_anchor_v1

domain_metadata_schemas:
  dungeonbuddy.domain_metadata:world_context_v1

source_annotation_schemas:
  dungeonbuddy.source:context_v1
  dungeonbuddy.domain_metadata:world_context_v1
```

The important correction is additive:

```text
dungeonbuddy.domain_metadata:world_context_v1
```

remains valid assertion/domain metadata **and** is explicitly declared as a source/evidence annotation schema.

Do not rename the schema solely to satisfy the Kernel gate. The evidence-local meaning `context_type = arrival_scene` is already Buddy-owned semantic content; this correction declares where that existing schema may legally appear.

## 6. Why overlap is intentional

DungeonMind V0 exposes two declaration lists but does not require them to be disjoint.

For Buddy:

```text
dungeonbuddy.domain_metadata:world_context_v1
```

is domain context that may appear on graph assertion metadata and evidence-local annotations.

```text
dungeonbuddy.source:context_v1
```

remains source-artifact tenancy/context metadata such as:

```text
campaign_id
session_id
```

The two schemas remain semantically distinct even though both are legal source/evidence annotations under revision 2.

Do not collapse them into one generic metadata bag.

## 7. Runtime preservation witness v2

Add a successor runtime fixture rather than rewriting the historical V0.2 fixture:

```text
tests/fixtures/vnext/dungeonbuddy_domain_runtime_preservation_v2.json
```

It may reuse the exact V0.2 entities/assertions/evidence/source records, but must pin:

```text
DomainContractRef
  domain_id = dungeonbuddy.world
  domain_revision = 2
  descriptor_sha256 = canonical digest of dungeonbuddy_world_domain_contract_v2.json
```

The semantic content of the witness must remain unchanged, including:

```text
EvidenceRefV3.domain_metadata:
  schema = dungeonbuddy.domain_metadata:world_context_v1
  payload.context_type = arrival_scene

SourceArtifactV3.domain_metadata:
  schema = dungeonbuddy.source:context_v1
  payload.campaign_id = campaign-longmont
  payload.session_id = session-28
```

This proves the correction is declaration ownership, not semantic rewriting.

## 8. Required executable proof

Use DungeonMind runtime pinned at:

```text
6edb9e40d1dc930f537c66deb1afbd1b99002844
```

Build the v2 witness into a real `ParsedKnowledgeRevision` and real `KnowledgeReadContext`.

Use an `AlwaysAdmitPolicy` or the smallest policy necessary so the test isolates generic declaration/admission behavior.

Prove:

1. the exact evidence-backed representative assertions no longer fail `domain_declaration`;
2. `EvidenceRefV3` with `dungeonbuddy.domain_metadata:world_context_v1` is accepted because revision 2 declares it in `source_annotation_schemas`;
3. `SourceArtifactV3` with `dungeonbuddy.source:context_v1` remains accepted;
4. an undeclared evidence metadata schema still fails closed as `domain_declaration`;
5. an undeclared assertion metadata schema still fails closed independently;
6. DomainContract revision 1 still reproduces the discovered failure, proving the correction is real and versioned rather than hidden by test setup.

## 9. Exact contract identity

Add a canonical digest assertion for revision 2.

Record the v2 DomainContractRef in the runtime fixture.

Do not alter:

```text
DungeonMind provider aggregate
fd04a9047b8ed79aaa5e710b2247ce1b2654c0e44e05d24fafb2adecb9e7b7ea
```

Do not alter the vendored V0 provider bundle.

This PR changes only Buddy-owned domain interpretation.

## 10. V0.2 acceptance artifact

The historical V0.2 acceptance artifact may be updated only for bookkeeping that was already pending, such as sealing its reviewed implementation head if required.

Do not change its recorded revision-1 DomainContract digest to revision 2. V0.2 is historical evidence for the contract-shape proof it actually performed.

If useful, add a new correction artifact:

```text
Docs/Contracts/vnext/dmb_v6_0_1_domain_contract_correction_v1.json
```

recording:

```text
schema
buddy_base_sha
dungeonmind_runtime_sha
v0_2_domain_revision = 1
v0_2_domain_digest
corrected_domain_revision = 2
corrected_domain_digest
preservation_fixture_v2_digest
reason = evidence_metadata_schema_ownership_mismatch
verification_disposition
```

Do not rewrite historical acceptance identity.

## 11. Files in scope

Expected:

```text
Docs/Contracts/vnext/dungeonbuddy_world_domain_contract_v2.json
Docs/Contracts/vnext/dmb_v6_0_1_domain_contract_correction_v1.json
Docs/Plans/HANDOFF-v6-0-1-dungeonbuddy-evidence-metadata-contract-correction.md
tests/fixtures/vnext/dungeonbuddy_domain_runtime_preservation_v2.json
tests/test_v6_0_1_dungeonbuddy_evidence_metadata_contract.py
```

If dependency repin was already intentionally part of the blocked V6.1 local work, it may remain deferred to V6.1. This corrective PR does not require changing production Buddy runtime code.

Do not modify DungeonMind.

Do not modify production World Graph services/routes/UI.

## 12. Required negative proof

At minimum:

```text
rev1 descriptor + accepted V0.2 evidence
  -> domain_declaration exclusion

rev2 descriptor + same evidence
  -> passes generic declaration/evidence gate

rev2 descriptor + evidence metadata unknown:schema
  -> domain_declaration exclusion

rev2 descriptor + assertion metadata unknown:schema
  -> domain_declaration exclusion
```

The correction must not make arbitrary metadata admissible.

## 13. Verification

Run at minimum:

```text
uv sync --locked

uv run pytest -q   tests/test_v0_2_dungeonmind_vnext_contract_acceptance.py   tests/test_v6_0_1_dungeonbuddy_evidence_metadata_contract.py

uv run ruff check <changed Python files>

git diff --check
```

Also run the current Buddy default/non-live suite or classify inherited baseline failures exactly using current `main` as the comparison base.

No live authority migration is required.

## 14. Stop conditions

Stop and rebrief if:

- DungeonMind V5 cannot admit the same semantic witness even after the schema is correctly declared in `source_annotation_schemas`;
- fixing the witness requires changing a frozen DungeonMind contract field;
- the same qualified schema cannot legally appear in both Buddy declaration lists;
- the runtime requires stripping evidence metadata;
- source/evidence admission requires product-role logic inside DungeonMind;
- a broader source/evidence contract redesign becomes necessary.

## 15. Acceptance

Only Steward review may record:

```text
V6_0_1_DUNGEONBUDDY_EVIDENCE_METADATA_CONTRACT_CORRECTED
```

A PASS means:

- historical V0.2 revision 1 remains preserved;
- Buddy has a corrected immutable DomainContract revision 2;
- the representative evidence-backed vNext witness passes generic DungeonMind runtime admission;
- undeclared metadata still fails closed;
- DungeonMind V0/V5 contracts remain unchanged.

## 16. Successor

After acceptance, resume the existing V6.1 handoff against:

```text
DungeonMind runtime:
  6edb9e40d1dc930f537c66deb1afbd1b99002844

Buddy DomainContract:
  dungeonbuddy.world revision 2
```

V6.1 should then implement the Buddy-owned runtime policy/request/context foundation using the corrected descriptor and v2 runtime preservation fixture.

V6.2 and V7 remain blocked only until V6.1 completes, not on any new Kernel capability.

## 17. Completion record

Steward review `5299327752` gave a substantive PASS to implementation head:

```text
1f5c47ab20605b4e07b2afe8db65f9d7152388e0
```

The accepted disposition is:

```text
V6_0_1_DUNGEONBUDDY_EVIDENCE_METADATA_CONTRACT_CORRECTED
```

The post-review finalization is limited to this completion record, the correction
artifact disposition, and their sealing assertions. No runtime, fixture,
descriptor, or dependency state changed during finalization.
