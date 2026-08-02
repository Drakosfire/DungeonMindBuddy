"""SBW09c2b: Threat publication commit route contract tests."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from graph_memory.kernel.contribution_models import ContributionMergeResult

import apps.live_control_server.routes.threat_publication_commits as commit_routes
import apps.live_control_server.services.threat_publication_commits as commit_svc
import apps.live_control_server.services.threat_publication_proposals as proposal_svc
from apps.live_control_server.main import create_app
from apps.live_control_server.models.threat_publication_commit import ConfirmThreatPublicationRequestV1
from tests.test_threat_publication_proposals import (
    _begin_operation,
    _create_new_resolution,
    _mechanics_saved_draft,
    _prepare_request,
)


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(commit_routes, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(commit_routes, "world_graph_root", lambda: tmp_path / "graph")
    return TestClient(create_app())


def _prepare_proposal(tmp_path: Path, draft, op_id: str, resolution_id: str, proposal_id: str):
    outcome = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(proposal_id),
        world_root=tmp_path / "graph",
    )
    assert outcome.response.result_label == "publication_proposal_ready"
    assert outcome.response.proposal is not None
    return outcome.response.proposal


def _merge_success(proposal):
    return ContributionMergeResult(
        world_id="world_1",
        parent_revision_id=proposal.expected_parent_revision_id,
        revision_id="rev:api-committed",
        contribution_ids=[proposal.expected_contribution_id],
        accepted_assertion_ids=list(proposal.accepted_assertion_ids),
        published=True,
    )


def _pipeline(tmp_path: Path, monkeypatch):
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    proposal_id = str(uuid.uuid4())
    proposal = _prepare_proposal(tmp_path, draft, op_id, resolution_id, proposal_id)
    return draft, op_id, proposal_id, proposal


def test_commit_route_confirm_created_returns_201(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, proposal_id, proposal = _pipeline(tmp_path, monkeypatch)
    client = _client(tmp_path, monkeypatch)
    commit_id = str(uuid.uuid4())

    def _confirm(root, d, o, p, body, **kw):
        return commit_svc.confirm_threat_publication(
            root,
            d,
            o,
            p,
            body,
            world_root=tmp_path / "graph",
            merge_fn=lambda *_a, **_k: _merge_success(proposal),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    monkeypatch.setattr(commit_routes, "confirm_threat_publication", _confirm)
    response = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/proposals/{proposal_id}/commits",
        json={
            "commit_id": commit_id,
            "sealed_proposal_digest": proposal.sealed_proposal_digest,
            "expected_parent_revision_id": proposal.expected_parent_revision_id,
            "actor": "gm",
        },
    )

    assert response.status_code == 201
    assert response.json()["result_label"] in {
        "publication_commit_verified",
        "publication_commit_committed_unverified",
    }


def test_commit_route_busy_returns_409(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, proposal_id, proposal = _pipeline(tmp_path, monkeypatch)
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(
        commit_routes,
        "confirm_threat_publication",
        lambda *_a, **_k: commit_svc.CommitOutcome(
            commit_svc._response(
                draft.draft_id,
                op_id,
                proposal_id,
                str(uuid.uuid4()),
                "publication_commit_busy",
                message="operation already claimed",
            )
        ),
    )

    response = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/proposals/{proposal_id}/commits",
        json=ConfirmThreatPublicationRequestV1.model_validate(
            {
                "commit_id": str(uuid.uuid4()),
                "sealed_proposal_digest": proposal.sealed_proposal_digest,
                "expected_parent_revision_id": proposal.expected_parent_revision_id,
                "actor": "gm",
            }
        ).model_dump(mode="json", by_alias=True),
    )
    assert response.status_code == 409
    assert response.json()["result_label"] == "publication_commit_busy"


def test_commit_route_recovery_pending_returns_503(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, proposal_id, proposal = _pipeline(tmp_path, monkeypatch)
    client = _client(tmp_path, monkeypatch)
    commit_id = str(uuid.uuid4())
    monkeypatch.setattr(
        commit_routes,
        "confirm_threat_publication",
        lambda *_a, **_k: commit_svc.CommitOutcome(
            commit_svc._response(
                draft.draft_id,
                op_id,
                proposal_id,
                commit_id,
                "publication_commit_recovery_pending",
                retry_allowed=True,
            )
        ),
    )

    response = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/proposals/{proposal_id}/commits",
        json={
            "commit_id": commit_id,
            "sealed_proposal_digest": proposal.sealed_proposal_digest,
            "expected_parent_revision_id": proposal.expected_parent_revision_id,
            "actor": "gm",
        },
    )
    assert response.status_code == 503
    assert response.json()["result_label"] == "publication_commit_recovery_pending"


def test_commit_route_get_not_found_is_404_no_artifact(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    client = _client(tmp_path, monkeypatch)

    response = client.get(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/commits/{uuid.uuid4()}"
    )

    assert response.status_code == 404
    assert response.json()["result_label"] == "publication_commit_not_found"
    assert not (tmp_path / "out" / "threat_publication_commits" / draft.draft_id / op_id).exists()
