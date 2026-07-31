from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apps.live_control_server.config as live_config
from apps.live_control_server.main import create_app
from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    RulesetRefV1,
)
from apps.live_control_server.services.threat_draft_store import (
    create_threat_draft,
    get_threat_draft,
)
from tests.test_threat_statblock_publication_service import (
    WORLD_ID,
    _initialize_world,
    _mark_mechanics_saved,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = REPO_ROOT / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"


@pytest.fixture
def publication_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    world_root = tmp_path / "world"
    repo.mkdir()
    world_root.mkdir()
    head = _initialize_world(world_root)

    draft = create_threat_draft(
        repo,
        CreateThreatDraftRequest(
            world_id=WORLD_ID,
            campaign_id="longmont-c2",
            name="Route Threat",
            description="Route test threat.",
            threat_kind="creature",
            generation_intent=GenerationIntentV1(
                ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
            ),
            graph_context_snapshot=GraphContextSnapshotV1(graph_revision_id=head),
            created_by="gm",
        ),
    )
    _mark_mechanics_saved(repo, draft)
    saved = get_threat_draft(repo, draft.draft_id)

    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(world_root))
    monkeypatch.setattr(live_config, "repo_root", lambda: repo)
    monkeypatch.setattr(live_config, "world_graph_root", lambda: world_root)
    import apps.live_control_server.routes.threat_statblock_publication as pub_routes

    monkeypatch.setattr(pub_routes, "repo_root", lambda: repo)
    monkeypatch.setattr(pub_routes, "world_graph_root", lambda: world_root)
    client = TestClient(create_app())
    return client, repo, world_root, saved, head


def _begin_body(saved, *, operation_id: str, parent_revision_id: str) -> dict:
    return {
        "schema": "dmb_begin_threat_statblock_publication_request_v1",
        "operation_id": operation_id,
        "expected_draft_version": saved.version,
        "expected_parent_revision_id": parent_revision_id,
    }


def test_begin_get_reconcile_cancel_routes(publication_client) -> None:
    client, _repo, _world, saved, head = publication_client
    op_id = str(uuid.uuid4())
    begin = client.post(
        f"/api/live/threat-drafts/{saved.draft_id}/publication-operations",
        json=_begin_body(saved, operation_id=op_id, parent_revision_id=head),
    )
    assert begin.status_code == 200, begin.text
    body = begin.json()
    assert body["schema"] == "dmb_threat_statblock_publication_operation_response_v1"
    assert body["result_label"] == "publication_claimed"
    assert body["operation"]["authority_state"] == "awaiting_identity_resolution"

    loaded = client.get(
        f"/api/live/threat-drafts/{saved.draft_id}/publication-operations/{op_id}"
    )
    assert loaded.status_code == 200
    assert loaded.json()["operation"]["operation_id"] == op_id

    reconcile = client.post(
        f"/api/live/threat-drafts/{saved.draft_id}/publication-operations/{op_id}:reconcile",
        json={"expected_operation_version": body["operation"]["operation_version"]},
    )
    assert reconcile.status_code == 200
    assert reconcile.json()["result_label"] == "publication_resumed"

    cancel = client.post(
        f"/api/live/threat-drafts/{saved.draft_id}/publication-operations/{op_id}:cancel",
        json={"expected_operation_version": body["operation"]["operation_version"]},
    )
    assert cancel.status_code == 200
    assert cancel.json()["result_label"] == "publication_cancelled"


def test_routes_reject_query_parameters(publication_client) -> None:
    client, _repo, _world, saved, head = publication_client
    op_id = str(uuid.uuid4())
    response = client.post(
        f"/api/live/threat-drafts/{saved.draft_id}/publication-operations?debug=1",
        json=_begin_body(saved, operation_id=op_id, parent_revision_id=head),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_routes_reject_extra_fields(publication_client) -> None:
    client, _repo, _world, saved, head = publication_client
    op_id = str(uuid.uuid4())
    payload = _begin_body(saved, operation_id=op_id, parent_revision_id=head)
    payload["world_id"] = WORLD_ID
    response = client.post(
        f"/api/live/threat-drafts/{saved.draft_id}/publication-operations",
        json=payload,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_error_envelope_shape(publication_client) -> None:
    client, _repo, _world, saved, head = publication_client
    response = client.post(
        f"/api/live/threat-drafts/{saved.draft_id}/publication-operations",
        json=_begin_body(saved, operation_id=str(uuid.uuid4()), parent_revision_id="rev:missing"),
    )
    assert response.status_code == 409
    body = response.json()
    assert body["schema"] == "dmb_threat_statblock_publication_error_v1"
    assert body["code"] == "stale_parent_revision"
    assert body["status_code"] == 409
    assert body["diagnostics"]


def test_invalid_draft_id_path_returns_422(publication_client) -> None:
    client, _repo, _world, _saved, _head = publication_client
    response = client.get(
        f"/api/live/threat-drafts/not-a-uuid/publication-operations/{uuid.uuid4()}"
    )
    assert response.status_code == 422
    body = response.json()
    assert body["schema"] == "dmb_threat_statblock_publication_error_v1"
    assert body["code"] == "invalid_request"


def test_invalid_operation_id_path_returns_422(publication_client) -> None:
    client, _repo, _world, saved, _head = publication_client
    response = client.get(
        f"/api/live/threat-drafts/{saved.draft_id}/publication-operations/not-valid"
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_missing_operation_returns_404(publication_client) -> None:
    client, _repo, _world, saved, _head = publication_client
    response = client.get(
        f"/api/live/threat-drafts/{saved.draft_id}/publication-operations/{uuid.uuid4()}"
    )
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "operation_not_found"
    assert body["status_code"] == 404


def test_reconcile_version_mismatch_returns_typed_409(publication_client) -> None:
    client, _repo, _world, saved, head = publication_client
    op_id = str(uuid.uuid4())
    begin = client.post(
        f"/api/live/threat-drafts/{saved.draft_id}/publication-operations",
        json=_begin_body(saved, operation_id=op_id, parent_revision_id=head),
    )
    assert begin.status_code == 200
    response = client.post(
        f"/api/live/threat-drafts/{saved.draft_id}/publication-operations/{op_id}:reconcile",
        json={"expected_operation_version": 999},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "operation_version_mismatch"
