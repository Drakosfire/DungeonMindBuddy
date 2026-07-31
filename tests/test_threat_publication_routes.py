"""SBW09a: durable Threat publication-operation route contract tests."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

import apps.live_control_server.routes.threat_publication as threat_publication_routes
import apps.live_control_server.services.threat_publication_operations as svc
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    PROVIDER_DUNGEONMIND,
    MechanicsLocatorV1,
)
from apps.live_control_server.main import create_app
from apps.live_control_server.models.statblock_mechanics_acceptance import AcceptedMechanicsRefV1
from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    RulesetRefV1,
)
from apps.live_control_server.services.threat_draft_store import (
    _draft_path,
    attach_accepted_mechanics_ref,
    create_threat_draft,
)

DEFAULT_DIGEST = "sha256:" + "a" * 64


class _FakeHead:
    def __init__(self, revision_id: str) -> None:
        self.head_revision_id = revision_id


def _mock_head(monkeypatch, revision_id: str) -> None:
    monkeypatch.setattr(
        svc.kernel, "open_world_graph_head", lambda root, world_id: _FakeHead(revision_id)
    )


def _make_mechanics_saved_draft(tmp_path: Path, monkeypatch, *, head: str = "rev:parent1"):
    draft = create_threat_draft(
        tmp_path,
        CreateThreatDraftRequest(
            world_id="world_1",
            campaign_id="campaign_1",
            name="Ironhide Brute",
            description="A brutal enforcer.",
            threat_kind="creature",
            generation_intent=GenerationIntentV1(
                ruleset=RulesetRefV1(system="dnd5e", edition="2024"), target_cr="3"
            ),
            graph_context_snapshot=GraphContextSnapshotV1(graph_revision_id="rev:aaa"),
            created_by="gm",
        ),
    )
    locator = MechanicsLocatorV1(
        provider=PROVIDER_DUNGEONMIND,
        statblock_id="sb_1",
        revision_id="rev_1",
        contract="dungeonmind.dungeonbuddy-statblocks",
        contract_version="1.0.0",
        definition_digest=DEFAULT_DIGEST,
    )
    ref = AcceptedMechanicsRefV1.from_locator(
        locator, accepted_from_draft_version=draft.version, accepted_at="2020-01-01T00:00:00Z"
    )
    draft = attach_accepted_mechanics_ref(
        tmp_path, draft_id=draft.draft_id, expected_version=draft.version, locator=ref
    )
    _mock_head(monkeypatch, head)
    return draft


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(threat_publication_routes, "repo_root", lambda: tmp_path)
    return TestClient(create_app())


def _begin_body(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "operation_id": str(uuid.uuid4()),
        "expected_draft_version": 2,
        "expected_parent_revision_id": "rev:parent1",
        "actor": "gm",
    }
    payload.update(overrides)
    return payload


def test_begin_route_returns_201_with_typed_envelope(tmp_path: Path, monkeypatch) -> None:
    draft = _make_mechanics_saved_draft(tmp_path, monkeypatch)
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations",
        json=_begin_body(expected_draft_version=draft.version),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["schema"] == "dmb_threat_publication_operation_response_v1"
    assert body["result_label"] == "publication_ready"
    assert body["draft_id"] == draft.draft_id
    assert body["operation"]["schema"] == "dmb_threat_publication_operation_v1"
    assert body["operation"]["state"] == "ready"
    assert body["operation"]["source_snapshot"]["schema"] == "dmb_threat_publication_source_v1"


def test_begin_route_exact_replay_returns_200(tmp_path: Path, monkeypatch) -> None:
    draft = _make_mechanics_saved_draft(tmp_path, monkeypatch)
    client = _client(tmp_path, monkeypatch)
    body = _begin_body(expected_draft_version=draft.version)

    first = client.post(f"/api/live/threat-drafts/{draft.draft_id}/publication-operations", json=body)
    assert first.status_code == 201

    replay = client.post(f"/api/live/threat-drafts/{draft.draft_id}/publication-operations", json=body)
    assert replay.status_code == 200
    assert replay.json()["operation"]["operation_id"] == first.json()["operation"]["operation_id"]


def test_begin_route_conflict_and_busy_return_409(tmp_path: Path, monkeypatch) -> None:
    draft = _make_mechanics_saved_draft(tmp_path, monkeypatch)
    client = _client(tmp_path, monkeypatch)
    op_id = str(uuid.uuid4())

    first = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations",
        json=_begin_body(operation_id=op_id, expected_draft_version=draft.version),
    )
    assert first.status_code == 201

    changed = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations",
        json=_begin_body(operation_id=op_id, expected_draft_version=draft.version, actor="other"),
    )
    assert changed.status_code == 409
    assert changed.json()["result_label"] == "publication_input_conflict"

    busy = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations",
        json=_begin_body(expected_draft_version=draft.version),
    )
    assert busy.status_code == 409
    assert busy.json()["result_label"] == "publication_busy"


def test_begin_route_parent_mismatch_returns_409(tmp_path: Path, monkeypatch) -> None:
    draft = _make_mechanics_saved_draft(tmp_path, monkeypatch, head="rev:actual")
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations",
        json=_begin_body(expected_draft_version=draft.version, expected_parent_revision_id="rev:wrong"),
    )
    assert response.status_code == 409
    assert response.json()["result_label"] == "publication_parent_mismatch"
    assert response.json()["operation"] is None


def test_begin_route_non_mechanics_saved_draft_returns_409(tmp_path: Path, monkeypatch) -> None:
    draft = create_threat_draft(
        tmp_path,
        CreateThreatDraftRequest(
            world_id="world_1",
            campaign_id="campaign_1",
            name="Ironhide Brute",
            description="A brutal enforcer.",
            threat_kind="creature",
            generation_intent=GenerationIntentV1(
                ruleset=RulesetRefV1(system="dnd5e", edition="2024"), target_cr="3"
            ),
            graph_context_snapshot=GraphContextSnapshotV1(graph_revision_id="rev:aaa"),
            created_by="gm",
        ),
    )
    _mock_head(monkeypatch, "rev:parent1")
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations",
        json=_begin_body(expected_draft_version=draft.version),
    )
    assert response.status_code == 409
    assert response.json()["result_label"] == "publication_source_mismatch"


def test_begin_route_rejects_extra_field_with_422(tmp_path: Path, monkeypatch) -> None:
    draft = _make_mechanics_saved_draft(tmp_path, monkeypatch)
    client = _client(tmp_path, monkeypatch)
    body = _begin_body(expected_draft_version=draft.version)
    body["unexpected"] = "nope"
    response = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations", json=body
    )
    assert response.status_code == 422


def test_begin_route_rejects_invalid_draft_id_with_422(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    response = client.post(
        "/api/live/threat-drafts/not-a-uuid/publication-operations",
        json=_begin_body(expected_draft_version=1),
    )
    assert response.status_code == 422


def test_read_route_returns_operation_and_404_when_missing(tmp_path: Path, monkeypatch) -> None:
    draft = _make_mechanics_saved_draft(tmp_path, monkeypatch)
    client = _client(tmp_path, monkeypatch)
    op_id = str(uuid.uuid4())
    client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations",
        json=_begin_body(operation_id=op_id, expected_draft_version=draft.version),
    )

    read = client.get(f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}")
    assert read.status_code == 200
    assert read.json()["operation"]["operation_id"] == op_id

    missing = client.get(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{uuid.uuid4()}"
    )
    assert missing.status_code == 404
    assert missing.json()["result_label"] == "publication_not_found"


def test_read_route_rejects_malformed_operation_id_with_422(tmp_path: Path, monkeypatch) -> None:
    draft = _make_mechanics_saved_draft(tmp_path, monkeypatch)
    client = _client(tmp_path, monkeypatch)
    response = client.get(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/../escape"
    )
    assert response.status_code in {404, 422}


def test_refresh_route_transitions_to_stale_on_parent_drift(tmp_path: Path, monkeypatch) -> None:
    draft = _make_mechanics_saved_draft(tmp_path, monkeypatch, head="rev:parent1")
    client = _client(tmp_path, monkeypatch)
    op_id = str(uuid.uuid4())
    client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations",
        json=_begin_body(operation_id=op_id, expected_draft_version=draft.version),
    )

    _mock_head(monkeypatch, "rev:parent2")
    refresh = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/refresh"
    )
    assert refresh.status_code == 200
    assert refresh.json()["result_label"] == "publication_stale"
    assert "graph_parent_changed" in refresh.json()["operation"]["stale_reasons"]


def test_cancel_route_is_terminal_and_idempotent(tmp_path: Path, monkeypatch) -> None:
    draft = _make_mechanics_saved_draft(tmp_path, monkeypatch)
    client = _client(tmp_path, monkeypatch)
    op_id = str(uuid.uuid4())
    client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations",
        json=_begin_body(operation_id=op_id, expected_draft_version=draft.version),
    )

    cancel_body = {"actor": "gm", "note": "done"}
    cancelled = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/cancel",
        json=cancel_body,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["result_label"] == "publication_cancelled"

    replay = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/cancel",
        json=cancel_body,
    )
    assert replay.status_code == 200
    assert replay.json()["result_label"] == "publication_cancelled"

    conflict = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/cancel",
        json={"actor": "someone-else"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["result_label"] == "publication_input_conflict"


def test_retry_route_supersedes_and_source_drift_conflicts(tmp_path: Path, monkeypatch) -> None:
    draft = _make_mechanics_saved_draft(tmp_path, monkeypatch, head="rev:parent1")
    client = _client(tmp_path, monkeypatch)
    old_id = str(uuid.uuid4())
    client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations",
        json=_begin_body(operation_id=old_id, expected_draft_version=draft.version),
    )
    _mock_head(monkeypatch, "rev:parent2")
    client.post(f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{old_id}/refresh")

    new_id = str(uuid.uuid4())
    retried = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{old_id}/retry",
        json={
            "new_operation_id": new_id,
            "expected_parent_revision_id": "rev:parent2",
            "actor": "gm",
        },
    )
    assert retried.status_code == 201
    assert retried.json()["result_label"] == "publication_ready"
    assert retried.json()["operation"]["operation_id"] == new_id
    assert retried.json()["operation"]["supersedes_operation_id"] == old_id

    old_read = client.get(f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{old_id}")
    assert old_read.json()["result_label"] == "publication_superseded"


def test_restart_reload_via_new_test_client_preserves_operation(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _make_mechanics_saved_draft(tmp_path, monkeypatch)
    monkeypatch.setattr(threat_publication_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    op_id = str(uuid.uuid4())
    begin = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations",
        json=_begin_body(operation_id=op_id, expected_draft_version=draft.version),
    )
    assert begin.status_code == 201

    restarted = TestClient(create_app())
    read = restarted.get(f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}")
    assert read.status_code == 200
    assert read.json()["operation"] == begin.json()["operation"]


def test_route_flow_leaves_threat_draft_bytes_unchanged(tmp_path: Path, monkeypatch) -> None:
    draft = _make_mechanics_saved_draft(tmp_path, monkeypatch, head="rev:parent1")
    draft_bytes_before = _draft_path(tmp_path, draft.draft_id).read_bytes()
    client = _client(tmp_path, monkeypatch)
    op_id = str(uuid.uuid4())

    client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations",
        json=_begin_body(operation_id=op_id, expected_draft_version=draft.version),
    )
    client.get(f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}")
    _mock_head(monkeypatch, "rev:parent2")
    client.post(f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/refresh")
    new_id = str(uuid.uuid4())
    client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/retry",
        json={
            "new_operation_id": new_id,
            "expected_parent_revision_id": "rev:parent2",
            "actor": "gm",
        },
    )
    client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{new_id}/cancel",
        json={"actor": "gm"},
    )

    assert _draft_path(tmp_path, draft.draft_id).read_bytes() == draft_bytes_before
