"""SBW09b: Threat publication identity-resolution route contract tests."""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import apps.live_control_server.routes.threat_publication_identity as identity_routes
import apps.live_control_server.services.threat_publication_identity as identity_svc
import apps.live_control_server.services.threat_publication_operations as pub_svc
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
from apps.live_control_server.models.threat_publication_identity import MATCHING_PROFILE_V1
from apps.live_control_server.services.threat_draft_store import (
    _draft_path,
    attach_accepted_mechanics_ref,
    create_threat_draft,
)
from apps.live_control_server.models.threat_publication import BeginThreatPublicationOperationRequestV1
from apps.live_control_server.services.threat_publication_operations import begin_publication_operation
from graph_memory.projection.world_projection import WorldGraphProjectionNodeView

DEFAULT_DIGEST = "sha256:" + "a" * 64
PARENT = "rev:parent1"


class _FakeHead:
    def __init__(self, revision_id: str) -> None:
        self.head_revision_id = revision_id


def _mock_head(monkeypatch, revision_id: str) -> None:
    monkeypatch.setattr(
        pub_svc.kernel, "open_world_graph_head", lambda root, world_id: _FakeHead(revision_id)
    )


def _mechanics_saved_draft(tmp_path: Path, monkeypatch):
    draft = create_threat_draft(
        tmp_path,
        CreateThreatDraftRequest(
            world_id="world_1",
            campaign_id="campaign_1",
            name="Unique Threat",
            description="desc",
            threat_kind="creature",
            generation_intent=GenerationIntentV1(
                ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
                target_cr="3",
            ),
            graph_context_snapshot=GraphContextSnapshotV1(graph_revision_id="rev:aaa"),
            created_by="gm",
        ),
    )
    ref = AcceptedMechanicsRefV1.from_locator(
        MechanicsLocatorV1(
            provider=PROVIDER_DUNGEONMIND,
            statblock_id="sb_1",
            revision_id="rev_1",
            contract="dungeonmind.dungeonbuddy-statblocks",
            contract_version="1.0.0",
            definition_digest=DEFAULT_DIGEST,
        ),
        accepted_from_draft_version=draft.version,
        accepted_at="2020-01-01T00:00:00Z",
    )
    draft = attach_accepted_mechanics_ref(
        tmp_path, draft_id=draft.draft_id, expected_version=draft.version, locator=ref
    )
    _mock_head(monkeypatch, PARENT)
    return draft


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(identity_routes, "repo_root", lambda: tmp_path)
    return TestClient(create_app())


def _begin(tmp_path: Path, draft) -> str:
    op_id = str(uuid.uuid4())
    outcome = begin_publication_operation(
        tmp_path,
        draft.draft_id,
        BeginThreatPublicationOperationRequestV1.model_validate(
            {
                "operation_id": op_id,
                "expected_draft_version": draft.version,
                "expected_parent_revision_id": PARENT,
                "actor": "gm",
            }
        ),
    )
    assert outcome.response.result_label == "publication_ready"
    return op_id


def _projection(*nodes: WorldGraphProjectionNodeView):
    return identity_svc.build_projection_fixture(revision_id=PARENT, nodes=list(nodes))


def _node(node_id: str, *, label: str, kind: str = "Threat") -> WorldGraphProjectionNodeView:
    return WorldGraphProjectionNodeView(
        node_id=node_id,
        label=label,
        kind=kind,
        role="antagonist",
        aliases=[],
        source_domains=["campaign"],
    )


def test_identity_routes_preserve_exact_restart_reload(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id = _begin(tmp_path, draft)
    projection = _projection(_node("threat:1", label="One"))
    resolution_id = str(uuid.uuid4())

    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        client = _client(tmp_path, monkeypatch)
        prepare = client.post(
            f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/identity-candidates/prepare",
            json={"query_text": "One"},
        )
        assert prepare.status_code == 200
        cs = prepare.json()["candidate_set"]
        decide = client.post(
            f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/identity-resolutions",
            json={
                "resolution_id": resolution_id,
                "matching_profile": MATCHING_PROFILE_V1,
                "candidate_query": cs["candidate_query"],
                "candidate_set_digest": cs["candidate_set_digest"],
                "decision": "refuse",
                "rejected_candidate_node_ids": [],
                "actor": "gm",
                "reason": "no",
            },
        )
        assert decide.status_code == 201

    reloaded = TestClient(create_app())
    monkeypatch.setattr(identity_routes, "repo_root", lambda: tmp_path)
    read = reloaded.get(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/identity-resolutions/{resolution_id}"
    )
    assert read.status_code == 200
    body = read.json()
    assert body["result_label"] == "publication_identity_refused"
    assert body["resolution"]["resolution_id"] == resolution_id
    assert body["resolution"]["request_digest"] == decide.json()["resolution"]["request_digest"]


def test_identity_flow_leaves_graph_draft_mechanics_and_dms_unchanged(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    draft_before = _draft_path(tmp_path, draft.draft_id).read_bytes()
    op_id = _begin(tmp_path, draft)
    pub_before = pub_svc._ledger_path(tmp_path, draft.draft_id).read_bytes()
    projection = _projection(_node("threat:1", label="One"))

    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        client = _client(tmp_path, monkeypatch)
        prepare = client.post(
            f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/identity-candidates/prepare",
            json={"query_text": "One"},
        )
        cs = prepare.json()["candidate_set"]
        client.post(
            f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/identity-resolutions",
            json={
                "resolution_id": str(uuid.uuid4()),
                "matching_profile": MATCHING_PROFILE_V1,
                "candidate_query": cs["candidate_query"],
                "candidate_set_digest": cs["candidate_set_digest"],
                "decision": "refuse",
                "rejected_candidate_node_ids": [],
                "actor": "gm",
                "reason": "no",
            },
        )

    assert _draft_path(tmp_path, draft.draft_id).read_bytes() == draft_before
    assert pub_svc._ledger_path(tmp_path, draft.draft_id).read_bytes() == pub_before


def test_read_route_returns_not_found_when_predecessor_missing(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id = _begin(tmp_path, draft)
    projection = _projection(_node("threat:1", label="One"))
    resolution_id = str(uuid.uuid4())

    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        client = _client(tmp_path, monkeypatch)
        prepare = client.post(
            f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/identity-candidates/prepare",
            json={"query_text": "One"},
        )
        cs = prepare.json()["candidate_set"]
        decide = client.post(
            f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/identity-resolutions",
            json={
                "resolution_id": resolution_id,
                "matching_profile": MATCHING_PROFILE_V1,
                "candidate_query": cs["candidate_query"],
                "candidate_set_digest": cs["candidate_set_digest"],
                "decision": "refuse",
                "rejected_candidate_node_ids": [],
                "actor": "gm",
                "reason": "no",
            },
        )
        assert decide.status_code == 201

    pub_svc._ledger_path(tmp_path, draft.draft_id).unlink()
    read = client.get(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/identity-resolutions/{resolution_id}"
    )
    assert read.status_code == 404
    assert read.json()["result_label"] == "publication_identity_not_found"


def test_routes_pass_repo_and_world_roots_independently(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    world = tmp_path / "world"
    repo.mkdir()
    world.mkdir()
    monkeypatch.setattr(identity_routes, "repo_root", lambda: repo)
    monkeypatch.setattr(identity_routes, "world_graph_root", lambda: world)

    captured: dict[str, object] = {}

    def capture_prepare(root, draft_id, operation_id, body, *, world_root=None):
        captured["repo_root"] = root
        captured["world_root"] = world_root
        return identity_svc.IdentityResolutionOutcome(
            identity_svc._response(
                draft_id,
                operation_id,
                "publication_identity_candidates_ready",
            )
        )

    draft_id = str(uuid.uuid4())
    operation_id = str(uuid.uuid4())
    with patch.object(
        identity_routes, "prepare_identity_candidates", side_effect=capture_prepare
    ):
        client = TestClient(create_app())
        response = client.post(
            f"/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-candidates/prepare",
            json={},
        )

    assert response.status_code == 200
    assert captured["repo_root"] == repo
    assert captured["world_root"] == world
