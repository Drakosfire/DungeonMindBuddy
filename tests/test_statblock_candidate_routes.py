from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    GeneratedStatblockCandidateV1,
)
from apps.live_control_server.main import create_app
import apps.live_control_server.routes.statblock_candidates as candidate_routes
import apps.live_control_server.routes.threat_drafts as threat_drafts_routes
from apps.live_control_server.services import statblock_candidate_generation as generation

FIXTURE_RAW = json.loads(
    (Path(__file__).parent / "fixtures" / "statblocks" / "v1" / "candidate-response.json").read_text(
        encoding="utf-8"
    )
)


def _draft_payload() -> dict:
    return {
        "world_id": "world_1",
        "campaign_id": "campaign_1",
        "name": "Ironhide Brute",
        "description": "A brutal enforcer.",
        "threat_kind": "creature",
        "generation_intent": {
            "ruleset": {"system": "dnd5e", "edition": "2024"},
            "must_include": [],
            "must_avoid": [],
        },
        "encounter_context": {"terrain_notes": []},
        "graph_context_snapshot": {
            "graph_revision_id": "rev_graph_1",
            "selected_node_ids": [],
            "admitted_source_anchor_ids": [],
        },
        "created_by": "gm",
    }


def test_generate_and_read_candidate_routes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(candidate_routes, "repo_root", lambda: tmp_path)

    class FakeClient:
        def generate_candidate(self, body: dict):
            assert body["asset_options"]["generate_images"] is False
            payload = dict(FIXTURE_RAW)
            payload["candidate_id"] = "cand_route1"
            payload["expires_at"] = "2099-01-01T00:00:00Z"
            receipt = dict(payload["generation_receipt"])
            receipt["request_id"] = body["request_id"]
            payload["generation_receipt"] = receipt
            return GeneratedStatblockCandidateV1.model_validate(payload)

        def get_candidate(self, candidate_id: str):
            payload = dict(FIXTURE_RAW)
            payload["candidate_id"] = candidate_id
            payload["expires_at"] = "2099-01-01T00:00:00Z"
            return GeneratedStatblockCandidateV1.model_validate(payload)

    original = generation.generate_candidate_from_draft

    def _wrapped(root, **kwargs):
        kwargs["client"] = FakeClient()
        return original(root, **kwargs)

    monkeypatch.setattr(generation, "generate_candidate_from_draft", _wrapped)
    monkeypatch.setattr(candidate_routes, "generate_candidate_from_draft", _wrapped)

    client = TestClient(create_app())
    created = client.post("/api/live/threat-drafts", json=_draft_payload()).json()
    draft_id = created["draft_id"]

    generated = client.post(
        f"/api/live/threat-drafts/{draft_id}/candidates:generate",
        json={"expected_draft_version": 1, "client_request_id": "req-route-1"},
    )
    assert generated.status_code == 200
    body = generated.json()
    assert body["outcome"] == "success"
    assert body["candidate_ref"]["candidate_id"] == "cand_route1"

    read = client.get("/api/live/statblock-candidates/cand_route1")
    assert read.status_code == 200
    assert read.json()["status"] == "active"
    assert read.json()["candidate"]["candidate_id"] == "cand_route1"

    stale = client.post(
        f"/api/live/threat-drafts/{draft_id}/candidates:generate",
        json={"expected_draft_version": 99},
    )
    assert stale.status_code == 409


def test_accept_mechanics_route_contract(monkeypatch, tmp_path: Path) -> None:
    import json
    from pathlib import Path as P

    from apps.live_control_server.services import statblock_mechanics_acceptance as acc

    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(candidate_routes, "repo_root", lambda: tmp_path)

    fixtures = P(__file__).parent / "fixtures" / "statblocks" / "v1"
    validate = json.loads((fixtures / "validate-response.json").read_text(encoding="utf-8"))
    definition = json.loads((fixtures / "candidate-response.json").read_text(encoding="utf-8"))[
        "definition"
    ]

    def _fake_accept(root, *, draft_id, request):
        from apps.live_control_server.models.statblock_mechanics_acceptance import (
            AcceptThreatDraftMechanicsResponseV1,
        )

        return AcceptThreatDraftMechanicsResponseV1(
            draft_id=draft_id,
            operation_id=request.operation_id,
            result_label="mechanics_saved",
            authority_state="reconciled",
            draft_ref="attached",
            workflow_state="mechanics_saved",
        )

    monkeypatch.setattr(candidate_routes, "begin_or_resume_acceptance", _fake_accept)

    client = TestClient(create_app())
    created = client.post("/api/live/threat-drafts", json=_draft_payload()).json()
    draft_id = created["draft_id"]
    op_id = "accop_route_test"
    accepted = client.post(
        f"/api/live/threat-drafts/{draft_id}/mechanics:accept",
        json={
            "operation_id": op_id,
            "expected_draft_version": 1,
            "definition": definition,
            "validation_receipt": validate["validation_receipt"],
            "validation_definition_digest": validate["definition_digest"],
            "change_summary": "save",
        },
    )
    assert accepted.status_code == 200
    body = accepted.json()
    assert body["schema"] == "dmb_accept_threat_draft_mechanics_response_v1"
    assert body["result_label"] == "mechanics_saved"
    assert body["operation_id"] == op_id
