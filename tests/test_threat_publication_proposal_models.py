"""SBW09c1: Threat publication proposal model tests."""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from apps.live_control_server.models.threat_publication_proposal import (
    PrepareThreatPublicationProposalRequestV1,
    ThreatPublicationEffectSummaryV1,
    ThreatPublicationProposalLedgerV1,
    ThreatPublicationProposalResponseV1,
    ThreatPublicationProposalV1,
    canonical_string_list,
    prepare_request_digest,
    validate_proposal_id,
)


def _proposal(**overrides):
    base = {
        "proposal_id": str(uuid.uuid4()),
        "request_digest": "sha256:" + "a" * 64,
        "draft_id": str(uuid.uuid4()),
        "operation_id": str(uuid.uuid4()),
        "resolution_id": str(uuid.uuid4()),
        "source_digest": "sha256:" + "b" * 64,
        "resolution_request_digest": "sha256:" + "c" * 64,
        "candidate_set_digest": "sha256:" + "d" * 64,
        "expected_parent_revision_id": "rev:parent1",
        "decision": "create_new",
        "threat_node_id": "threat:authored:" + "e" * 32,
        "sealed_proposal_id": None,
        "sealed_proposal_digest": "sha256:" + "f" * 64,
        "sealed_proposal_version": 3,
        "sealed_proposal": {
            "schema": "dmb_extract_promote_proposal_v1",
            "proposal_id": None,
            "proposal_version": 3,
            "proposal_digest": "f" * 64,
            "prepared_by": "gm",
            "effect": {"world_id": "world_1", "parent_revision_id": "rev:parent1"},
        },
        "expected_contribution_id": "contribution:test",
        "accepted_assertion_ids": ["assertion:1"],
        "effect_summary": {
            "decision": "create_new",
            "threat_node_id": "threat:authored:" + "e" * 32,
            "external_resource_node_id": "external:dungeonmind:statblock:sb_1",
            "binding_edge_id": "edge:threat-statblock-binding:abc",
            "accepted_assertion_count": 1,
            "authored_field_assertion_count": 0,
        },
        "state": "active",
        "created_by": "gm",
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2020-01-01T00:00:00Z",
    }
    proposal_id = overrides.get("proposal_id", base["proposal_id"])
    base["sealed_proposal_id"] = proposal_id
    base["sealed_proposal"]["proposal_id"] = proposal_id
    base.update(overrides)
    return ThreatPublicationProposalV1.model_validate(base)


def test_validate_proposal_id_accepts_uuid_and_tpub() -> None:
    token = str(uuid.uuid4())
    assert validate_proposal_id(token) == token
    assert validate_proposal_id("tpub_alpha-1") == "tpub_alpha-1"


def test_validate_proposal_id_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="invalid proposal_id"):
        validate_proposal_id("../escape")


def test_prepare_request_digest_includes_route_identities() -> None:
    request = PrepareThreatPublicationProposalRequestV1.model_validate(
        {
            "proposal_id": str(uuid.uuid4()),
            "actor": "gm",
            "operator_note": "note",
            "supersedes_proposal_id": None,
        }
    )
    digest_a = prepare_request_digest(str(uuid.uuid4()), "op_1", "res_1", request)
    digest_b = prepare_request_digest(str(uuid.uuid4()), "op_1", "res_1", request)
    assert digest_a != digest_b


def test_canonical_string_list_dedupes_and_sorts() -> None:
    assert canonical_string_list([" brite ", "brute", "", "brute"]) == ["brite", "brute"]


def test_proposal_requires_sealed_id_equality() -> None:
    proposal_id = str(uuid.uuid4())
    mismatched = str(uuid.uuid4())
    payload = _proposal(proposal_id=proposal_id).model_dump(mode="json", by_alias=True)
    payload["sealed_proposal_id"] = mismatched
    with pytest.raises(ValidationError, match="sealed_proposal_id must equal proposal_id"):
        ThreatPublicationProposalV1.model_validate(payload)


def test_ledger_rejects_duplicate_proposal_ids() -> None:
    item = _proposal()
    with pytest.raises(ValidationError, match="duplicate proposal_id"):
        ThreatPublicationProposalLedgerV1.model_validate(
            {
                "draft_id": str(uuid.uuid4()),
                "operation_id": item.operation_id,
                "active_proposal_id": item.proposal_id,
                "proposals": [item.model_dump(mode="json", by_alias=True), item.model_dump(mode="json", by_alias=True)],
            }
        )


def test_ledger_rejects_two_active_proposals() -> None:
    first = _proposal()
    second = _proposal(operation_id=first.operation_id)
    with pytest.raises(ValidationError, match="more than one active"):
        ThreatPublicationProposalLedgerV1.model_validate(
            {
                "draft_id": str(uuid.uuid4()),
                "operation_id": first.operation_id,
                "active_proposal_id": first.proposal_id,
                "proposals": [
                    first.model_dump(mode="json", by_alias=True),
                    second.model_dump(mode="json", by_alias=True),
                ],
            }
        )


def test_effect_summary_requires_non_negative_counts() -> None:
    with pytest.raises(ValidationError):
        ThreatPublicationEffectSummaryV1.model_validate(
            {
                "decision": "connect_existing",
                "threat_node_id": "threat:1",
                "external_resource_node_id": "external:dungeonmind:statblock:sb_1",
                "binding_edge_id": "edge:1",
                "accepted_assertion_count": -1,
                "authored_field_assertion_count": 0,
            }
        )


def test_response_resolution_id_accepts_null() -> None:
    response = ThreatPublicationProposalResponseV1.model_validate(
        {
            "draft_id": str(uuid.uuid4()),
            "operation_id": str(uuid.uuid4()),
            "resolution_id": None,
            "result_label": "publication_proposal_not_found",
        }
    )
    assert response.resolution_id is None


def test_response_resolution_id_rejects_invalid_non_null() -> None:
    with pytest.raises(ValidationError, match="invalid resolution_id"):
        ThreatPublicationProposalResponseV1.model_validate(
            {
                "draft_id": str(uuid.uuid4()),
                "operation_id": str(uuid.uuid4()),
                "resolution_id": "../escape",
                "result_label": "publication_proposal_not_found",
            }
        )
