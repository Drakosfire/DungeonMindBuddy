"""Executable proof for the V6.0.1 evidence metadata ownership correction."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

from dungeonmind.application.vnext import (
    AlwaysAdmitPolicy,
    InMemoryKnowledgeSourceReader,
    KnowledgeReadContext,
    build_parsed_knowledge_revision,
)
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.contracts.vnext import (
    Assertion,
    DomainContractDescriptor,
    DomainContractRef,
    Entity,
    EvidenceRefV3,
    IdentityAlias,
    KnowledgeRevision,
    ProjectionRequest,
    SemanticProfileDescriptorV2,
    SourceArtifactV3,
    SourceRevisionV2,
)
from dungeonmind.domain.canonical import canonical_sha256

ROOT = Path(__file__).resolve().parents[1]
DOMAIN_V1_PATH = ROOT / "Docs/Contracts/vnext/dungeonbuddy_world_domain_contract_v1.json"
DOMAIN_V2_PATH = ROOT / "Docs/Contracts/vnext/dungeonbuddy_world_domain_contract_v2.json"
PROFILE_PATH = ROOT / "Docs/Contracts/vnext/dungeonbuddy_dnd5e_semantic_profile_v2.json"
FIXTURE_V1_PATH = ROOT / "tests/fixtures/vnext/dungeonbuddy_domain_preservation_v1.json"
FIXTURE_V2_PATH = ROOT / "tests/fixtures/vnext/dungeonbuddy_domain_runtime_preservation_v2.json"
CORRECTION_ARTIFACT_PATH = (
    ROOT / "Docs/Contracts/vnext/dmb_v6_0_1_domain_contract_correction_v1.json"
)
HANDOFF_PATH = (
    ROOT
    / "Docs/Plans/HANDOFF-v6-0-1-dungeonbuddy-evidence-metadata-contract-correction.md"
)
EXPECTED_DOMAIN_V1_DIGEST = (
    "9c1d3eb3e01ffebde959625a54831f1e5c25aad8a5c422ffaaedd09d8d929a8e"
)
EXPECTED_DOMAIN_V2_DIGEST = (
    "d12f3a517a37d29a2ba52455d9ae1691bc5e4ff3fd6853b701a9e28e46ec65cd"
)
EXPECTED_RUNTIME_SHA = "6edb9e40d1dc930f537c66deb1afbd1b99002844"
EXPECTED_FIXTURE_V2_DIGEST = (
    "4fdc327cdf6887dc4ae154e44da9904974c82e40d310a807f590ce2db6d21121"
)
EXPECTED_DISPOSITION = "V6_0_1_DUNGEONBUDDY_EVIDENCE_METADATA_CONTRACT_CORRECTED"
REVIEWED_HEAD = "1f5c47ab20605b4e07b2afe8db65f9d7152388e0"
SUBSTANTIVE_PASS_REVIEW = "5299327752"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_revision_2_is_additive_and_revision_1_is_byte_preserved() -> None:
    domain_v1_data = _json(DOMAIN_V1_PATH)
    domain_v2_data = _json(DOMAIN_V2_PATH)
    domain_v1 = DomainContractDescriptor.model_validate(domain_v1_data)
    domain_v2 = DomainContractDescriptor.model_validate(domain_v2_data)

    assert DOMAIN_V1_PATH.read_bytes() == (
        ROOT / "Docs/Contracts/vnext/dungeonbuddy_world_domain_contract_v1.json"
    ).read_bytes()
    assert canonical_sha256(domain_v1.model_dump(mode="json")) == EXPECTED_DOMAIN_V1_DIGEST
    assert canonical_sha256(domain_v2.model_dump(mode="json")) == EXPECTED_DOMAIN_V2_DIGEST
    assert domain_v1.domain_revision == "1"
    assert domain_v2.domain_revision == "2"
    assert domain_v1.domain_metadata_schemas == domain_v2.domain_metadata_schemas
    assert domain_v2.source_annotation_schemas == [
        "dungeonbuddy.source:context_v1",
        "dungeonbuddy.domain_metadata:world_context_v1",
    ]
    comparable_v1 = domain_v1_data | {"domain_revision": "2"}
    comparable_v1["source_annotation_schemas"] = domain_v2_data[
        "source_annotation_schemas"
    ]
    assert comparable_v1 == domain_v2_data


def test_runtime_fixture_v2_changes_only_contract_identity() -> None:
    historical = _json(FIXTURE_V1_PATH)
    runtime = _json(FIXTURE_V2_PATH)
    assert runtime["schema"] == "dmb_dungeonbuddy_domain_runtime_preservation_v2"
    assert runtime["domain_contract_ref"] == {
        "schema_version": "dm_domain_contract_ref_v1",
        "domain_id": "dungeonbuddy.world",
        "domain_revision": "2",
        "descriptor_sha256": EXPECTED_DOMAIN_V2_DIGEST,
    }
    historical["schema"] = runtime["schema"]
    historical["domain_contract_ref"] = runtime["domain_contract_ref"]
    assert historical == runtime
    evidence_entry = runtime["evidence"][0]["domain_metadata"][0]
    assert evidence_entry == {
        "schema": "dungeonbuddy.domain_metadata:world_context_v1",
        "payload": {"context_type": "arrival_scene"},
    }
    source_entry = runtime["sources"][0]["domain_metadata"][0]
    assert source_entry["schema"] == "dungeonbuddy.source:context_v1"


def test_correction_artifact_and_runtime_pin_are_sealed() -> None:
    artifact = _json(CORRECTION_ARTIFACT_PATH)
    assert artifact["buddy_base_sha"] == "99ec0d56911b62ad9b9d63db1c8f9406ca4f319d"
    assert artifact["dungeonmind_runtime_sha"] == EXPECTED_RUNTIME_SHA
    assert artifact["v0_2_domain_digest"] == EXPECTED_DOMAIN_V1_DIGEST
    assert artifact["corrected_domain_digest"] == EXPECTED_DOMAIN_V2_DIGEST
    assert artifact["preservation_fixture_v2_digest"] == EXPECTED_FIXTURE_V2_DIGEST
    assert artifact["verification_disposition"] == EXPECTED_DISPOSITION
    assert canonical_sha256(_json(FIXTURE_V2_PATH)) == EXPECTED_FIXTURE_V2_DIGEST
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")
    assert f"**Status:** COMPLETE — `{EXPECTED_DISPOSITION}`" in handoff
    assert f"**Accepted implementation head:** `{REVIEWED_HEAD}`" in handoff
    assert f"**Substantive PASS review:** `{SUBSTANTIVE_PASS_REVIEW}`" in handoff
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f"DungeonMind.git@{EXPECTED_RUNTIME_SHA}" in pyproject


def _context(
    fixture: dict,
    domain: DomainContractDescriptor,
    *,
    evidence_mutation: dict | None = None,
    assertion_mutation: dict | None = None,
) -> tuple[KnowledgeReadContext, tuple[str, ...]]:
    evidence_data = copy.deepcopy(fixture["evidence"])
    assertion_data = copy.deepcopy(fixture["assertions"])
    if evidence_mutation is not None:
        evidence_data[0]["domain_metadata"][0].update(evidence_mutation)
    if assertion_mutation is not None:
        assertion_data[2]["metadata"].setdefault("domain_metadata", []).append(
            assertion_mutation
        )

    profile_data = _json(PROFILE_PATH)
    profile = SemanticProfileDescriptorV2.model_validate(profile_data)
    domain_ref = DomainContractRef(
        domain_id=domain.domain_id,
        domain_revision=domain.domain_revision,
        descriptor_sha256=canonical_sha256(domain.model_dump(mode="json")),
    )
    profile_ref = SemanticProfileRef(
        profile_id=profile.profile_id,
        profile_revision=profile.profile_revision,
        descriptor_sha256=canonical_sha256(profile.model_dump(mode="json")),
    )
    revision = KnowledgeRevision(
        space_id=fixture["space_id"],
        revision_id=f"rev:v6-0-1:{domain.domain_revision}",
        created_at=datetime(2026, 9, 23, tzinfo=UTC),
        operation_ids=["op:v6-0-1-proof"],
        graph_schema="dungeonbuddy.test:v6_0_1",
        graph_payload_sha256="1" * 64,
        domain_contract_ref=domain_ref,
        semantic_profile_ref=profile_ref,
    )
    parsed = build_parsed_knowledge_revision(
        revision,
        entities=[Entity.model_validate(item) for item in fixture["entities"]],
        assertions=[Assertion.model_validate(item) for item in assertion_data],
        aliases=[IdentityAlias.model_validate(item) for item in fixture["aliases"]],
        evidence=[EvidenceRefV3.model_validate(item) for item in evidence_data],
    )
    artifacts = {
        item["source_artifact_id"]: SourceArtifactV3.model_validate(item)
        for item in fixture["sources"]
    }
    revisions = {
        item["source_revision_id"]: SourceRevisionV2.model_validate(item)
        for item in fixture["source_revisions"]
    }
    request_data = fixture["request_context_cases"][0]["projection_request"]
    request = ProjectionRequest.model_validate(request_data)
    context = KnowledgeReadContext(
        parsed=parsed,
        request=request,
        domain_contract=domain,
        semantic_profile=profile,
        domain_policy=AlwaysAdmitPolicy(policy_id=domain.admission_policy_id),
        source_reader=InMemoryKnowledgeSourceReader(
            artifacts=artifacts, revisions=revisions
        ),
    )
    candidate_ids = tuple(item["assertion_id"] for item in assertion_data)
    return context, candidate_ids


def test_revision_1_reproduces_failure_and_revision_2_admits_same_evidence() -> None:
    fixture_v1 = _json(FIXTURE_V1_PATH)
    fixture_v2 = _json(FIXTURE_V2_PATH)
    domain_v1 = DomainContractDescriptor.model_validate(_json(DOMAIN_V1_PATH))
    domain_v2 = DomainContractDescriptor.model_validate(_json(DOMAIN_V2_PATH))

    context_v1, ids_v1 = _context(fixture_v1, domain_v1)
    result_v1 = context_v1.admit_candidates(ids_v1)
    evidence_backed_v1 = {
        item.assertion_id: item.reason for item in result_v1.excluded
    }
    assert evidence_backed_v1["as:brennan-name"] == "domain_declaration"
    assert result_v1.work.policy_evaluations == 0

    context_v2, ids_v2 = _context(fixture_v2, domain_v2)
    result_v2 = context_v2.admit_candidates(ids_v2)
    assert "as:brennan-name" in result_v2.admitted_assertion_ids
    assert "as:brennan-classification" in result_v2.admitted_assertion_ids
    assert "as:brennan-secret-plan" in result_v2.admitted_assertion_ids
    assert all(item.reason != "domain_declaration" for item in result_v2.excluded)
    assert result_v2.work.policy_evaluations == 5


def test_revision_2_still_rejects_undeclared_evidence_metadata() -> None:
    fixture = _json(FIXTURE_V2_PATH)
    domain = DomainContractDescriptor.model_validate(_json(DOMAIN_V2_PATH))
    context, _ids = _context(
        fixture,
        domain,
        evidence_mutation={"schema": "unknown:schema"},
    )
    result = context.admit_candidates(["as:brennan-name"])
    assert result.excluded[0].reason == "domain_declaration"
    assert result.work.policy_evaluations == 0


def test_revision_2_still_rejects_undeclared_assertion_metadata() -> None:
    fixture = _json(FIXTURE_V2_PATH)
    domain = DomainContractDescriptor.model_validate(_json(DOMAIN_V2_PATH))
    context, _ids = _context(
        fixture,
        domain,
        assertion_mutation={"schema": "unknown:schema", "payload": {"x": 1}},
    )
    result = context.admit_candidates(["as:brennan-name"])
    assert result.excluded[0].reason == "domain_declaration"
    assert result.work.policy_evaluations == 0
