from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.live_control_server.models.statblock_candidate_workflow import (
    GenerateThreatDraftCandidateRequestV1,
)
from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    RulesetRefV1,
)
from apps.live_control_server.services.statblock_candidate_generation import (
    generate_candidate_from_draft,
    map_draft_to_generate_request,
    read_candidate,
)
from apps.live_control_server.services.threat_draft_store import (
    ThreatDraftStoreError,
    create_threat_draft,
    get_threat_draft,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    downstream_timeout,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "statblocks" / "v1" / "candidate-response.json").read_text(
        encoding="utf-8"
    )
)


def _create_draft(tmp_path: Path):
    return create_threat_draft(
        tmp_path,
        CreateThreatDraftRequest(
            world_id="world_1",
            campaign_id="campaign_1",
            name="Ironhide Brute",
            description="A brutal enforcer.",
            threat_kind="creature",
            intended_roles=["brute"],
            generation_intent=GenerationIntentV1(
                ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
                target_cr="3",
                must_include=["reach"],
            ),
            graph_context_snapshot=GraphContextSnapshotV1(
                graph_revision_id="rev_graph_1",
                selected_node_ids=["node_a"],
                admitted_source_anchor_ids=["anchor_1"],
            ),
            created_by="gm",
        ),
    )


class FakeClient:
    def __init__(self, *, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls: list[dict] = []

    def generate_candidate(self, body: dict):
        self.calls.append(body)
        if self.error is not None:
            raise self.error
        return self.payload

    def get_candidate(self, candidate_id: str):
        if self.error is not None:
            raise self.error
        assert self.payload is not None
        return self.payload


def test_request_mapping_disables_images(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    body = map_draft_to_generate_request(draft, request_id="req-1")
    assert body["asset_options"]["generate_images"] is False
    assert body["source"]["description"] == "A brutal enforcer."
    assert body["intent"]["target_cr"] == "3"
    assert body["intent"]["roles"] == ["brute"]


def test_stale_version_blocks_downstream(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(payload=FIXTURE)
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        generate_candidate_from_draft(
            tmp_path,
            draft_id=draft.draft_id,
            request=GenerateThreatDraftCandidateRequestV1(expected_draft_version=99),
            client=client,  # type: ignore[arg-type]
        )
    assert exc_info.value.status_code == 409
    assert client.calls == []


def test_success_stores_ref_and_cache(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    payload = dict(FIXTURE)
    payload["expires_at"] = "2099-01-01T00:00:00Z"
    client = FakeClient(payload=payload)
    result = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-fixed",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert result.outcome == "success"
    assert result.candidate_ref is not None
    assert result.candidate_ref.candidate_id == "cand_fixture1"
    assert result.candidate_ref.generated_from_draft_version == 1
    assert result.request_id == "req-fixed"
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert reloaded.version == 1
    assert reloaded.description == draft.description
    assert len(reloaded.candidate_refs) == 1
    read = read_candidate(tmp_path, candidate_id="cand_fixture1")
    assert read.status == "active"
    assert read.candidate is not None
    assert read.candidate["candidate_id"] == "cand_fixture1"


def test_failure_preserves_draft(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(error=downstream_timeout())
    result = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(expected_draft_version=1),
        client=client,  # type: ignore[arg-type]
    )
    assert result.outcome == "failure"
    assert result.failure_category == "downstream_timeout"
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert reloaded.version == 1
    assert reloaded.candidate_refs == []
