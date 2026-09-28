from pathlib import Path

import pytest

from apps.live_control_server.models.threat_draft import CreateWorldThreatDraftRequest
from apps.live_control_server.models.threat_publication import BeginThreatPublicationOperationRequestV1
from apps.live_control_server.services import threat_publication_operations as operations
from apps.live_control_server.services.threat_draft_store import create_threat_draft


@pytest.mark.parametrize("expected_version", [1, 999])
def test_world_draft_publication_rejects_before_operation_or_graph_effects(
    tmp_path: Path, monkeypatch, expected_version: int,
) -> None:
    draft = create_threat_draft(tmp_path, CreateWorldThreatDraftRequest(
        scope_mode="world", world_id="world_a", campaign_id=None,
        name="World creature", description="An authored creature.",
        threat_kind="creature", created_by="gm",
        generation_intent={"ruleset": {"system": "dnd5e", "edition": "2024"}},
        graph_context_snapshot={"graph_revision_id": None},
    ))

    def forbidden(*args, **kwargs):
        pytest.fail("World-only eligibility rejection must precede graph/operation effects")

    for name in ("_read_graph_head", "build_source_snapshot", "_save_ledger_unlocked"):
        monkeypatch.setattr(operations, name, forbidden)
    request = BeginThreatPublicationOperationRequestV1(
        operation_id="pubop_world_guard", expected_draft_version=expected_version,
        expected_parent_revision_id="rev:parent", actor="gm",
    )
    result = operations.begin_publication_operation(tmp_path, draft.draft_id, request)
    assert not result.created
    assert result.response.result_label == "publication_source_mismatch"
    assert result.response.operation is None
    assert "World-only" in result.response.message
    assert not operations._ledger_path(tmp_path, draft.draft_id).exists()
