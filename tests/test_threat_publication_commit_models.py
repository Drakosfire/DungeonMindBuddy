"""SBW09c2b: Threat publication commit model tests."""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from apps.live_control_server.models.threat_publication_commit import (
    ConfirmThreatPublicationRequestV1,
    ThreatPublicationCommitLedgerV1,
    ThreatPublicationCommitResponseV1,
    ThreatPublicationCommitV1,
    confirm_request_digest,
    validate_commit_id,
)
from apps.live_control_server.models.threat_publication_identity import (
    ThreatIdentityCandidateV1,
)


def _commit(**overrides):
    proposal_id = overrides.get("proposal_id", str(uuid.uuid4()))
    commit_id = overrides.get("commit_id", str(uuid.uuid4()))
    base = {
        "commit_id": commit_id,
        "request_digest": "sha256:" + "a" * 64,
        "draft_id": str(uuid.uuid4()),
        "operation_id": str(uuid.uuid4()),
        "proposal_id": proposal_id,
        "proposal_request_digest": "sha256:" + "b" * 64,
        "sealed_proposal_digest": "sha256:" + "c" * 64,
        "sealed_proposal_version": 3,
        "resolution_id": str(uuid.uuid4()),
        "source_digest": "sha256:" + "d" * 64,
        "resolution_request_digest": "sha256:" + "e" * 64,
        "candidate_set_digest": "sha256:" + "f" * 64,
        "world_id": "world_1",
        "campaign_id": "campaign_1",
        "expected_parent_revision_id": "rev:parent1",
        "expected_contribution_id": "contribution:test",
        "expected_contribution_source_payload_sha256": "a" * 64,
        "accepted_assertion_ids": ["assertion:1"],
        "decision": "create_new",
        "threat_node_id": "threat:authored:" + "0" * 32,
        "selected_target": None,
        "external_resource_node_id": "external:dungeonmind:statblock:sb_1",
        "binding_id": "threat-statblock-binding:abc",
        "binding_edge_id": "edge:threat-statblock-binding:abc",
        "state": "committing",
        "merge_attempt_count": 1,
        "committed_revision_id": None,
        "recovered_via_operation_lookup": False,
        "verification_status": "not_started",
        "verification_codes": [],
        "warnings": [],
        "created_by": "gm",
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2020-01-01T00:00:00Z",
    }
    base.update(overrides)
    return ThreatPublicationCommitV1.model_validate(base)


def test_validate_commit_id_accepts_uuid_and_tcommit() -> None:
    token = str(uuid.uuid4())
    assert validate_commit_id(token) == token
    assert validate_commit_id("tcommit_alpha-1") == "tcommit_alpha-1"


def test_validate_commit_id_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="invalid commit_id"):
        validate_commit_id("../escape")


def test_confirm_request_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ConfirmThreatPublicationRequestV1.model_validate(
            {
                "commit_id": str(uuid.uuid4()),
                "sealed_proposal_digest": "sha256:" + "a" * 64,
                "expected_parent_revision_id": "rev:parent1",
                "actor": "gm",
                "unexpected": True,
            }
        )


def test_create_new_requires_selected_target_null() -> None:
    target = ThreatIdentityCandidateV1.model_validate(
        {
            "node_id": "threat:1",
            "label": "Existing",
            "kind": "Threat",
            "role": "antagonist",
            "aliases": [],
            "source_domains": ["worldbuilding"],
            "binding_ids": [],
            "has_exact_accepted_binding": False,
            "match_score": 0,
            "match_reasons": [],
            "exact_name_collision": False,
        }
    )
    with pytest.raises(ValidationError, match="create_new requires selected_target=null"):
        _commit(selected_target=target.model_dump(mode="json", by_alias=True))


def test_committed_verified_requires_verification_passed() -> None:
    with pytest.raises(ValidationError, match="committed_verified requires verification_status=passed"):
        _commit(
            state="committed_verified",
            committed_revision_id="rev:committed1",
            verification_status="failed",
        )


def test_raw_sha256_field_rejects_prefixed_digest() -> None:
    with pytest.raises(ValidationError, match="raw lowercase 64-hex"):
        _commit(expected_contribution_source_payload_sha256="sha256:" + "a" * 64)


def test_confirm_request_digest_includes_route_identities() -> None:
    request = ConfirmThreatPublicationRequestV1.model_validate(
        {
            "commit_id": str(uuid.uuid4()),
            "sealed_proposal_digest": "sha256:" + "a" * 64,
            "expected_parent_revision_id": "rev:parent1",
            "actor": "gm",
            "operator_note": "note",
        }
    )
    digest_a = confirm_request_digest(str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()), request)
    digest_b = confirm_request_digest(str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()), request)
    assert digest_a != digest_b


def test_ledger_rejects_commit_identity_mismatch() -> None:
    item = _commit()
    with pytest.raises(ValidationError, match="commit draft_id must match ledger draft_id"):
        ThreatPublicationCommitLedgerV1.model_validate(
            {
                "draft_id": str(uuid.uuid4()),
                "operation_id": item.operation_id,
                "commit": item.model_dump(mode="json", by_alias=True),
            }
        )


def test_response_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ThreatPublicationCommitResponseV1.model_validate(
            {
                "draft_id": str(uuid.uuid4()),
                "operation_id": str(uuid.uuid4()),
                "proposal_id": str(uuid.uuid4()),
                "commit_id": str(uuid.uuid4()),
                "result_label": "publication_commit_not_found",
                "retry_allowed": False,
                "extra": True,
            }
        )
