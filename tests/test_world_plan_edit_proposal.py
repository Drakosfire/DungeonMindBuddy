"""World-only Plan edits are inert proposals bound to the exact saved Plan."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.live_control_server.models.plan_document_edit_proposal import (
    WorldPlanDocumentEditProposalRequest,
)
from apps.live_control_server.routes import live, workspace_documents
from apps.live_control_server.services import plan_document_edit_proposal as service
from apps.live_control_server.services.workspace_document_registry import (
    WorldOwnedPlanRecordV2,
    WorldOwnedPlanSnapshotV2,
    WorldOwnedRunbookRecordV2,
    WorldOwnedRunbookSnapshotV2,
)
from apps.live_control_server.services.world_container_registry import create_world_container


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _request(**overrides) -> WorldPlanDocumentEditProposalRequest:
    data = {
        "document_id": "plan-1",
        "world_id": "world-1",
        "base_revision": 2,
        "base_content_sha256": _sha("SAVED SERVER PROSE"),
        "draft_markdown": "# Current local draft\n",
        "draft_sha256": _sha("# Current local draft\n"),
        "target_kind": "replace_selection",
        "selected_text": "local draft",
        "instruction": "Make this more suspenseful.",
        "conversation_history": [{"role": "user", "content": "Start the scene."}],
    }
    data.update(overrides)
    return WorldPlanDocumentEditProposalRequest.model_validate(data)


class _FakeGenerationClient:
    def __init__(self) -> None:
        self.requests: list = []

    async def generate_structured(self, request):
        self.requests.append(request)
        return SimpleNamespace(
            parsed={
                "replacement_markdown": "The shutters rattle in the wind.",
                "summary": "Add a tense beat",
                "assumptions": ["The sound is proposed atmosphere."],
                "cannot_complete_reason": None,
            },
            observation=SimpleNamespace(
                response_model="observed-test-model",
                resolved_model="test-model",
                latency_ms=314,
                input_tokens=80,
                output_tokens=30,
                cost_usd=0.002,
            ),
        )


def _authority(
    monkeypatch: pytest.MonkeyPatch,
    *,
    world_id: str = "world-1",
    document_world_id: str = "world-1",
    kind: str = "plan",
    status: str = "active",
    revision: int = 2,
    saved_markdown: str = "SAVED SERVER PROSE",
):
    world = SimpleNamespace(world_id=world_id)
    if kind == "plan":
        record = WorldOwnedPlanRecordV2(
            document_id="plan-1",
            title="Plan",
            world_id=document_world_id,
            status=status,
            created_at="2026-10-01T00:00:00Z",
            updated_at="2026-10-01T00:00:00Z",
        )
        snapshot = WorldOwnedPlanSnapshotV2(
            record=record,
            markdown=saved_markdown,
            content_sha256=_sha(saved_markdown),
            file_fingerprint="postgres",
            file_exists=False,
            loaded_revision=revision,
        )
    else:
        record = WorldOwnedRunbookRecordV2(
            document_id="plan-1",
            title="Runbook",
            world_id=document_world_id,
            created_at="2026-10-01T00:00:00Z",
            updated_at="2026-10-01T00:00:00Z",
        )
        snapshot = WorldOwnedRunbookSnapshotV2(
            record=record,
            markdown=saved_markdown,
            content_sha256=_sha(saved_markdown),
            file_fingerprint="postgres",
            file_exists=False,
            loaded_revision=revision,
        )
    monkeypatch.setattr(service, "get_world_container", lambda *_: world)
    monkeypatch.setattr(service, "get_workspace_document_snapshot", lambda *_: snapshot)
    return snapshot


@pytest.mark.parametrize(
    ("authority", "overrides", "expected_code"),
    [
        ({"world_id": "another-world"}, {}, "plan_target_mismatch"),
        ({"document_world_id": "another-world"}, {}, "plan_target_mismatch"),
        ({"kind": "runbook"}, {}, "plan_target_mismatch"),
        ({"status": "discarded"}, {}, "plan_target_mismatch"),
        ({}, {"base_revision": 1}, "plan_base_stale"),
        ({}, {"base_content_sha256": "a" * 64}, "plan_base_stale"),
        ({}, {"draft_sha256": "a" * 64}, "draft_digest_mismatch"),
        ({}, {"selected_text": "   "}, "plan_target_missing"),
        ({}, {"target_kind": "insert_at_caret", "selected_text": "selected"}, "plan_target_invalid"),
    ],
)
def test_invalid_world_plan_binding_fails_before_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    authority: dict,
    overrides: dict,
    expected_code: str,
) -> None:
    _authority(monkeypatch, **authority)
    fake = _FakeGenerationClient()

    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=_request(**overrides),
            generation_client=fake,
            model="test-model",
        )

    assert caught.value.code == expected_code
    assert fake.requests == []


def test_world_request_forbids_session_and_campaign_authority_fields() -> None:
    with pytest.raises(ValueError):
        _request(session=1)
    with pytest.raises(ValueError):
        _request(campaign_id="world-1")


def test_world_proposal_uses_only_explicit_draft_context_and_returns_exact_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    snapshot = _authority(monkeypatch)
    fake = _FakeGenerationClient()
    result = service.propose_world_plan_document_edit(
        root=tmp_path,
        request=_request(),
        generation_client=fake,
        model="test-model",
    )

    assert result.schema_version == "dmb_world_plan_document_edit_proposal_v1"
    assert result.document_id == "plan-1"
    assert result.world_id == "world-1"
    assert not hasattr(result, "session")
    assert result.base_revision == 2
    assert result.base_content_sha256 == snapshot.content_sha256
    assert result.draft_sha256 == _sha("# Current local draft\n")
    assert result.selected_text_sha256 == _sha("local draft")
    assert result.model == "observed-test-model"
    assert result.replacement_markdown == "The shutters rattle in the wind."
    assert len(fake.requests) == 1
    context = json.loads(fake.requests[0].user_prompt)
    assert context["current_plan_markdown"] == "# Current local draft\n"
    assert "SAVED SERVER PROSE" not in fake.requests[0].user_prompt


def _client(monkeypatch: pytest.MonkeyPatch, root: Path) -> TestClient:
    monkeypatch.setattr(workspace_documents, "repo_root", lambda: root)
    monkeypatch.setattr(live, "repo_root", lambda: root)
    app = FastAPI()
    app.include_router(workspace_documents.router)
    app.include_router(live.router)
    return TestClient(app)


def test_world_plan_route_uses_real_saved_world_plan_and_never_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    world = create_world_container(tmp_path, name="Reviewed Apply route world")
    client = _client(monkeypatch, tmp_path)
    created = client.post(
        "/api/live/workspace-documents/world-plans",
        json={
            "schema_version": "dmb_workspace_document_create_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "title": "Reviewed Plan",
        },
    )
    assert created.status_code == 200
    record = created.json()
    document_id = record["document_id"]
    committed_markdown = "# Saved server-only prose\n"
    prepared = client.post(
        "/api/live/tiptap/markdown-write/prepare",
        json={
            "schema_version": "dmb_tiptap_markdown_write_prepare_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "document_id": document_id,
            "markdown": committed_markdown,
            "expected_revision": record["revision"],
        },
    )
    assert prepared.status_code == 200
    commit_fields = prepared.json()
    committed = client.post(
        "/api/live/tiptap/markdown-write/commit",
        json={
            "schema_version": "dmb_tiptap_markdown_write_commit_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "document_id": document_id,
            "markdown": committed_markdown,
            "expected_revision": commit_fields["registry_revision"],
            "writer_confirm_token": commit_fields["writer_confirm_token"],
        },
    )
    assert committed.status_code == 200
    saved_before = client.get(f"/api/live/workspace-documents/{document_id}/snapshot").json()
    draft = "# Explicit unsaved editor draft\n"

    fake = _FakeGenerationClient()
    monkeypatch.setattr(service, "_resolve_model", lambda: "test-model")
    monkeypatch.setattr(service.GenerationClient, "from_env", lambda: fake)
    request = {
        "document_id": document_id,
        "world_id": world.world_id,
        "base_revision": saved_before["loaded_revision"],
        "base_content_sha256": saved_before["content_sha256"],
        "draft_markdown": draft,
        "draft_sha256": _sha(draft),
        "target_kind": "insert_at_caret",
        "selected_text": "",
        "instruction": "Add a tense opening.",
        "conversation_history": [],
    }
    response = client.post("/api/live/world-plan-edit/propose", json=request)
    assert response.status_code == 200, response.text
    assert response.json()["schema_version"] == "dmb_world_plan_document_edit_proposal_v1"
    assert response.json()["world_id"] == world.world_id
    assert response.json()["document_id"] == document_id
    assert "session" not in response.json()
    assert len(fake.requests) == 1
    assert "Explicit unsaved editor draft" in fake.requests[0].user_prompt
    assert "Saved server-only prose" not in fake.requests[0].user_prompt

    rejected = client.post("/api/live/world-plan-edit/propose", json={**request, "session": 1})
    assert rejected.status_code == 422
    assert len(fake.requests) == 1
    saved_after = client.get(f"/api/live/workspace-documents/{document_id}/snapshot").json()
    assert saved_after["loaded_revision"] == saved_before["loaded_revision"]
    assert saved_after["content_sha256"] == saved_before["content_sha256"]
    assert saved_after["markdown"] == committed_markdown
