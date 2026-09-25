"""V6.1 executable proof for the Buddy-owned vNext domain runtime seam."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dungeonmind.application.vnext import (
    InMemoryKnowledgeSourceReader,
    build_parsed_knowledge_revision,
)
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.contracts.vnext import (
    Assertion,
    DomainContractRef,
    Entity,
    EvidenceRefV3,
    IdentityAlias,
    KnowledgeRevision,
    ProjectionRequest,
    SourceArtifactV3,
    SourceRevisionV2,
)
from dungeonmind.domain.canonical import canonical_sha256
from graph_memory.vnext import (
    DUNGEONBUDDY_DOMAIN_DIGEST,
    DUNGEONBUDDY_POLICY_ID,
    DUNGEONBUDDY_PROFILE_DIGEST,
    DungeonBuddyVNextProjectionInput,
    build_dungeonbuddy_projection_request,
    build_dungeonbuddy_read_context,
    dungeonbuddy_dnd5e_custom_predicate_profile,
    dungeonbuddy_dnd5e_semantic_profile,
    dungeonbuddy_world_domain_contract,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    ROOT / "tests/fixtures/vnext/dungeonbuddy_domain_runtime_preservation_v2.json"
)
DOMAIN_PATH = ROOT / "Docs/Contracts/vnext/dungeonbuddy_world_domain_contract_v2.json"
PROFILE_PATH = ROOT / "Docs/Contracts/vnext/dungeonbuddy_dnd5e_semantic_profile_v2.json"
CUSTOM_PROFILE_PATH = ROOT / "Docs/Contracts/vnext/dungeonbuddy_dnd5e_semantic_profile_v3.json"


@pytest.fixture(scope="module")
def preservation() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _input(data: dict) -> DungeonBuddyVNextProjectionInput:
    return DungeonBuddyVNextProjectionInput(**data)


def test_runtime_descriptors_match_checked_in_canonical_identity() -> None:
    runtime_domain = dungeonbuddy_world_domain_contract()
    runtime_profile = dungeonbuddy_dnd5e_semantic_profile()
    checked_domain = json.loads(DOMAIN_PATH.read_text(encoding="utf-8"))
    checked_profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

    assert runtime_domain.model_dump(mode="json") == checked_domain
    assert runtime_profile.model_dump(mode="json") == checked_profile
    assert canonical_sha256(runtime_domain.model_dump(mode="json")) == (
        DUNGEONBUDDY_DOMAIN_DIGEST
    )
    assert canonical_sha256(runtime_profile.model_dump(mode="json")) == (
        DUNGEONBUDDY_PROFILE_DIGEST
    )
    assert runtime_domain.domain_revision == "2"
    assert runtime_domain.admission_policy_id == DUNGEONBUDDY_POLICY_ID


def test_custom_profile_is_a_distinct_immutable_opt_in_revision() -> None:
    profile = dungeonbuddy_dnd5e_custom_predicate_profile()
    checked = json.loads(CUSTOM_PROFILE_PATH.read_text(encoding="utf-8"))
    assert profile.model_dump(mode="json") == checked
    assert profile.profile_revision == "2"
    assert profile.schema_version == "dm_semantic_profile_v3"
    assert profile.open_predicate_namespaces[0].namespace == "dungeonbuddy.custom"
    assert profile.open_predicate_namespaces[0].allowed_value_kinds == ["entity_ref"]
    assert dungeonbuddy_dnd5e_semantic_profile().profile_revision == "1"


def test_custom_predicate_read_admission_uses_exact_pinned_v3_profile(preservation: dict) -> None:
    new_preservation = copy.deepcopy(preservation)
    profile = dungeonbuddy_dnd5e_custom_predicate_profile()
    new_preservation["semantic_profile_ref"]["profile_revision"] = profile.profile_revision
    new_preservation["semantic_profile_ref"]["descriptor_sha256"] = canonical_sha256(
        profile.model_dump(mode="json")
    )
    relationship = next(
        item for item in new_preservation["assertions"] if item["predicate"] == "dnd5e:located_in"
    )
    for assertion_id, predicate, value in (
        ("as:custom-works-at", "dungeonbuddy.custom:works_at", relationship["value"]),
        ("as:unscoped-works-at", "dungeonbuddy:works_at", relationship["value"]),
        ("as:wrong-kind", "dungeonbuddy.custom:has_motto", {"kind": "literal", "value": "A"}),
    ):
        item = copy.deepcopy(relationship)
        item.update(assertion_id=assertion_id, predicate=predicate, value=value)
        new_preservation["assertions"].append(item)

    context, result = _admission(
        new_preservation,
        DungeonBuddyVNextProjectionInput(world_id="eldyrwild", scope_mode="world", role="gm"),
    )
    admitted = set(result.admitted_assertion_ids)
    assert context.semantic_profile.schema_version == "dm_semantic_profile_v3"
    assert "as:custom-works-at" in admitted
    assert "as:unscoped-works-at" not in admitted
    assert "as:wrong-kind" not in admitted


def test_mapper_preserves_all_accepted_request_cases(preservation: dict) -> None:
    for case in preservation["request_context_cases"]:
        request = build_dungeonbuddy_projection_request(_input(case["buddy_input"]))
        assert request == ProjectionRequest.model_validate(case["projection_request"])


@pytest.mark.parametrize(
    "projection_input",
    [
        DungeonBuddyVNextProjectionInput(world_id="", scope_mode="world", role="gm"),
        DungeonBuddyVNextProjectionInput(
            world_id="world", scope_mode="campaign", role="gm"
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world", scope_mode="unknown", role="gm"  # type: ignore[arg-type]
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world", scope_mode="world", role="GM"  # type: ignore[arg-type]
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world", scope_mode="world", role=" player "  # type: ignore[arg-type]
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world", scope_mode="world", role="gm", campaign_id="campaign", session_id=""
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world",
            scope_mode="campaign",
            role="gm",
            campaign_id=" ",
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world", scope_mode="world", role="gm", revision_id=" "
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world",
            scope_mode="world",
            role="player",
            standing_selector=("provisional",),
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world",
            scope_mode="world",
            role="player",
            standing_selector=("retracted",),
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world",
            scope_mode="world",
            role="gm",
            standing_selector=("retracted",),
        ),
    ],
)
def test_mapper_rejects_invalid_or_unauthorized_inputs(
    projection_input: DungeonBuddyVNextProjectionInput,
) -> None:
    with pytest.raises(ValueError):
        build_dungeonbuddy_projection_request(projection_input)


def test_mapper_preserves_exact_identifier_bytes_and_revision() -> None:
    request = build_dungeonbuddy_projection_request(
        DungeonBuddyVNextProjectionInput(
            world_id=" World Exact ",
            scope_mode="campaign",
            role="gm",
            campaign_id=" Campaign Exact ",
            session_id=" Session Exact ",
            revision_id=" Revision Exact ",
            standing_selector=("established",),
        )
    )
    assert request.space_id == " World Exact "
    assert request.revision_id == " Revision Exact "
    assert request.scope_selector.bindings[0].value == " Campaign Exact "
    assert request.focus[0].id == " Campaign Exact "
    assert request.focus[1].id == " Session Exact "
    assert request.standing_selector == ["established"]


def _runtime_witness(preservation: dict):
    assertions = copy.deepcopy(preservation["assertions"])
    other_campaign = copy.deepcopy(assertions[2])
    other_campaign["assertion_id"] = "as:brennan-name-other-campaign"
    other_campaign["metadata"]["scope"][0]["value"] = "campaign-other"
    assertions.append(other_campaign)

    revision = KnowledgeRevision(
        space_id=preservation["space_id"],
        revision_id="rev:v6-1-witness",
        created_at=datetime(2026, 9, 24, tzinfo=UTC),
        operation_ids=["op:v6-1-witness"],
        graph_schema="dungeonbuddy.test:v6_1",
        graph_payload_sha256="1" * 64,
        domain_contract_ref=DomainContractRef.model_validate(
            preservation["domain_contract_ref"]
        ),
        semantic_profile_ref=SemanticProfileRef.model_validate(
            preservation["semantic_profile_ref"]
        ),
    )
    parsed = build_parsed_knowledge_revision(
        revision,
        entities=[Entity.model_validate(item) for item in preservation["entities"]],
        assertions=[Assertion.model_validate(item) for item in assertions],
        aliases=[
            IdentityAlias.model_validate(item) for item in preservation["aliases"]
        ],
        evidence=[
            EvidenceRefV3.model_validate(item) for item in preservation["evidence"]
        ],
    )
    reader = InMemoryKnowledgeSourceReader(
        artifacts={
            item["source_artifact_id"]: SourceArtifactV3.model_validate(item)
            for item in preservation["sources"]
        },
        revisions={
            item["source_revision_id"]: SourceRevisionV2.model_validate(item)
            for item in preservation["source_revisions"]
        },
    )
    return parsed, reader


def _admission(preservation: dict, projection_input: DungeonBuddyVNextProjectionInput):
    parsed, reader = _runtime_witness(preservation)
    context = build_dungeonbuddy_read_context(
        parsed_revision=parsed,
        projection_input=projection_input,
        source_reader=reader,
    )
    result = context.admit_candidates(tuple(parsed.assertions_by_id))
    return context, result


def test_campaign_gm_admission_preserves_expected_semantics(preservation: dict) -> None:
    context, result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            campaign_id="campaign-longmont",
            role="gm",
        ),
    )
    assert set(result.admitted_assertion_ids) == {
        "as:mireward-classification",
        "as:brennan-classification",
        "as:brennan-name",
        "as:brennan-secret-plan",
        "as:brennan-located-in-mireward",
    }
    assert "as:brennan-retracted-rumor" not in result.admitted_assertion_ids
    assert "as:brennan-name-other-campaign" not in result.admitted_assertion_ids
    assert result.work.policy_evaluations == len(result.admitted_assertion_ids)
    assert context.domain_policy.policy_id == context.domain_contract.admission_policy_id


def test_campaign_player_cannot_recover_generic_rejections(preservation: dict) -> None:
    _context, result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            campaign_id="campaign-longmont",
            role="player",
        ),
    )
    admitted = set(result.admitted_assertion_ids)
    assert "as:mireward-classification" in admitted
    assert "as:brennan-classification" in admitted
    assert "as:brennan-name" in admitted
    assert "as:brennan-secret-plan" not in admitted
    assert "as:brennan-retracted-rumor" not in admitted
    assert "as:brennan-name-other-campaign" not in admitted
    assert result.work.policy_evaluations == len(admitted)


def test_world_gm_wildcard_admits_campaign_scoped_assertions(preservation: dict) -> None:
    _context, result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild", scope_mode="world", role="gm"
        ),
    )
    assert "as:brennan-name" in result.admitted_assertion_ids
    assert "as:brennan-name-other-campaign" in result.admitted_assertion_ids


def test_session_focus_is_preserved_without_changing_admission(preservation: dict) -> None:
    base, base_result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            campaign_id="campaign-longmont",
            role="gm",
        ),
    )
    focused, focused_result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            campaign_id="campaign-longmont",
            session_id="session-28",
            role="gm",
        ),
    )
    assert focused_result.admitted_assertion_ids == base_result.admitted_assertion_ids
    assert [(item.kind, item.id) for item in focused.request.focus] == [
        ("dungeonbuddy.focus:campaign", "campaign-longmont"),
        ("dungeonbuddy.focus:session", "session-28"),
    ]
    assert base.request.focus == []


def test_missing_source_is_rejected_before_buddy_policy(preservation: dict) -> None:
    parsed, _reader = _runtime_witness(preservation)
    context = build_dungeonbuddy_read_context(
        parsed_revision=parsed,
        projection_input=DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            campaign_id="campaign-longmont",
            role="gm",
        ),
        source_reader=InMemoryKnowledgeSourceReader(),
    )
    result = context.admit_candidates(["as:brennan-name"])
    assert result.admitted_assertion_ids == ()
    assert result.excluded[0].reason == "source_missing"
    assert result.work.policy_evaluations == 0


def test_corrected_evidence_and_source_metadata_pass_unchanged(preservation: dict) -> None:
    assert preservation["evidence"][0]["domain_metadata"][0] == {
        "schema": "dungeonbuddy.domain_metadata:world_context_v1",
        "payload": {"context_type": "arrival_scene"},
    }
    assert preservation["sources"][0]["domain_metadata"][0]["schema"] == (
        "dungeonbuddy.source:context_v1"
    )
    _context, result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            campaign_id="campaign-longmont",
            role="gm",
        ),
    )
    assert "as:brennan-name" in result.admitted_assertion_ids


def test_context_request_is_a_real_projection_request(preservation: dict) -> None:
    context, _result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild", scope_mode="world", role="gm"
        ),
    )
    assert isinstance(context.request, ProjectionRequest)
