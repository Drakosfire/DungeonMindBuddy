"""SBW09c1: Threat publication proposal route contract tests."""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import apps.live_control_server.routes.threat_publication_proposals as proposal_routes
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
from apps.live_control_server.models.threat_publication import BeginThreatPublicationOperationRequestV1
from apps.live_control_server.models.threat_publication_identity import MATCHING_PROFILE_V1
from apps.live_control_server.services.threat_draft_store import attach_accepted_mechanics_ref, create_threat_draft
from apps.live_control_server.services.threat_publication_operations import begin_publication_operation
from graph_memory.projection.world_projection import WorldGraphProjectionNodeView
from graph_memory.union_supergraph.load import DEFAULT_FIXTURE_PATH, load_union_supergraph_store
from graph_memory.world_supergraph import publish_world_graph_revision

DEFAULT_DIGEST = "sha256:" + "a" * 64


class _FakeHead:
    def __init__(self, revision_id: str) -> None:
        self.head_revision_id = revision_id


def _empty_parent_store():
    base = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    return base.model_copy(
        update={
            "nodes": {},
            "edges": {},
            "aliases": {},
            "adjacency": {},
            "evidence": {},
            "source_artifacts": {},
        }
    )


def _seed_graph_parent(tmp_path: Path) -> str:
    published = publish_world_graph_revision(
        tmp_path / "graph",
        "world_1",
        _empty_parent_store(),
        operation_ids=["op:proposal-api-test"],
    )
    return published.revision.revision_id


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
    parent = _seed_graph_parent(tmp_path)
    _mock_head(monkeypatch, parent)
    return draft, parent


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(proposal_routes, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(proposal_routes, "world_graph_root", lambda: tmp_path / "graph")
    return TestClient(create_app())


def _begin(tmp_path: Path, draft, parent: str) -> str:
    op_id = str(uuid.uuid4())
    outcome = begin_publication_operation(
        tmp_path,
        draft.draft_id,
        BeginThreatPublicationOperationRequestV1.model_validate(
            {
                "operation_id": op_id,
                "expected_draft_version": draft.version,
                "expected_parent_revision_id": parent,
                "actor": "gm",
            }
        ),
    )
    assert outcome.response.result_label == "publication_ready"
    return op_id


def _node(node_id: str, *, label: str, kind: str = "Threat") -> WorldGraphProjectionNodeView:
    return WorldGraphProjectionNodeView(
        node_id=node_id,
        label=label,
        kind=kind,
        role="antagonist",
        aliases=[],
        source_domains=["campaign"],
    )


def _create_new_resolution(tmp_path: Path, draft, op_id: str, parent: str) -> str:
    projection = identity_svc.build_projection_fixture(
        revision_id=parent, nodes=[_node("threat:visible", label="Visible")]
    )
    resolution_id = str(uuid.uuid4())
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepare = identity_svc.prepare_identity_candidates(
            tmp_path,
            draft.draft_id,
            op_id,
            identity_svc.PrepareThreatIdentityCandidatesRequestV1.model_validate(
                {"query_text": "Visible"}
            ),
        )
        cs = prepare.response.candidate_set
        assert cs is not None
        with patch.object(
            identity_svc,
            "_exact_revision_contains_node_id",
            side_effect=lambda _operation, node_id, *, world_root: False,
        ):
            decide = identity_svc.decide_identity_resolution(
                tmp_path,
                draft.draft_id,
                op_id,
                identity_svc.CreateThreatIdentityResolutionRequestV1.model_validate(
                    {
                        "resolution_id": resolution_id,
                        "matching_profile": MATCHING_PROFILE_V1,
                        "candidate_query": cs.candidate_query,
                        "candidate_set_digest": cs.candidate_set_digest,
                        "decision": "create_new",
                        "rejected_candidate_node_ids": [
                            c.node_id for c in cs.candidates if c.exact_name_collision
                        ],
                        "actor": "gm",
                        "reason": "new",
                    }
                ),
            )
    assert decide.response.result_label == "publication_identity_created_new"
    return resolution_id


def test_proposal_route_create_and_read_round_trip(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id = _begin(tmp_path, draft, parent)
    resolution_id = _create_new_resolution(tmp_path, draft, op_id, parent)
    proposal_id = str(uuid.uuid4())
    client = _client(tmp_path, monkeypatch)

    created = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/identity-resolutions/{resolution_id}/proposals",
        json={"proposal_id": proposal_id, "actor": "gm"},
    )
    assert created.status_code == 201
    assert created.json()["result_label"] == "publication_proposal_ready"

    read = client.get(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/proposals/{proposal_id}"
    )
    assert read.status_code == 200
    assert read.json()["proposal"]["proposal_id"] == proposal_id


def test_proposal_route_refuse_returns_conflict_without_storage(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id = _begin(tmp_path, draft, parent)
    projection = identity_svc.build_projection_fixture(
        revision_id=parent, nodes=[_node("threat:1", label="One")]
    )
    resolution_id = str(uuid.uuid4())
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepare = identity_svc.prepare_identity_candidates(
            tmp_path,
            draft.draft_id,
            op_id,
            identity_svc.PrepareThreatIdentityCandidatesRequestV1.model_validate({"query_text": "One"}),
        )
        cs = prepare.response.candidate_set
        assert cs is not None
        identity_svc.decide_identity_resolution(
            tmp_path,
            draft.draft_id,
            op_id,
            identity_svc.CreateThreatIdentityResolutionRequestV1.model_validate(
                {
                    "resolution_id": resolution_id,
                    "matching_profile": MATCHING_PROFILE_V1,
                    "candidate_query": cs.candidate_query,
                    "candidate_set_digest": cs.candidate_set_digest,
                    "decision": "refuse",
                    "rejected_candidate_node_ids": [],
                    "actor": "gm",
                    "reason": "no",
                }
            ),
        )

    client = _client(tmp_path, monkeypatch)
    response = client.post(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/identity-resolutions/{resolution_id}/proposals",
        json={"proposal_id": str(uuid.uuid4()), "actor": "gm"},
    )
    assert response.status_code == 409
    assert response.json()["result_label"] == "publication_proposal_identity_refused"


def test_proposal_route_not_found_is_404(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id = _begin(tmp_path, draft, parent)
    client = _client(tmp_path, monkeypatch)
    response = client.get(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{op_id}/proposals/{uuid.uuid4()}"
    )
    assert response.status_code == 404
    assert response.json()["result_label"] == "publication_proposal_not_found"
