"""Private blob reads and authenticated, owner-resolved Action prompt routes."""
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from application_state.plan_action_dialogue.types import ActionPromptReferenceV1
from apps.live_control_server.routes import live
from apps.live_control_server.services import plan_action_prompt_evidence as evidence
from apps.live_control_server.services.agent_prompt_evidence import PromptEvidenceError


def ref(payload='{"input":"private <script>"}'):
    return ActionPromptReferenceV1(world_id="world-a", action_id=uuid4(), dispatch_fence=1,
        authorization_event_id=uuid4(), provider_attempt_id=uuid4(), evidence_id=uuid4(),
        provider="synthetic", model="synthetic", api_mode="responses", serializer_version="openai-sdk-json-v1",
        payload_sha256=sha256(payload.encode()).hexdigest(), payload_utf8_bytes=len(payload.encode()))


def test_actual_private_blob_roundtrip_and_corruption(monkeypatch, tmp_path):
    from apps.live_control_server.services import agent_prompt_evidence as blobs
    monkeypatch.setattr(blobs, "artifact_data_root", lambda: tmp_path)
    payload = '{"input":"private <script>"}'
    reference = ref(payload)
    identity = blobs.store_prompt(payload, digest=reference.payload_sha256, size=reference.payload_utf8_bytes)
    reference = reference.model_copy(update={"evidence_id": identity})
    monkeypatch.setattr(evidence, "_references", lambda world, action: [reference] if world == reference.world_id and action == reference.action_id else [])
    assert evidence.prompt_body(reference.world_id, reference.action_id, reference.provider_attempt_id)["payload_json"] == payload
    index = evidence.prompt_index(reference.world_id, reference.action_id)
    assert "evidence_id" not in index["references"][0] and "dispatch_fence" not in index["references"][0]
    with pytest.raises(PromptEvidenceError):
        evidence.prompt_body(reference.world_id, uuid4(), reference.provider_attempt_id)
    with pytest.raises(PromptEvidenceError):
        evidence.prompt_body(reference.world_id, reference.action_id, uuid4())
    path = tmp_path / "out" / "agent_request_evidence" / (str(identity) + ".json")
    path.write_bytes(b"x" * reference.payload_utf8_bytes)
    with pytest.raises(PromptEvidenceError):
        evidence.prompt_body(reference.world_id, reference.action_id, reference.provider_attempt_id)


def test_mounted_prompt_reads_require_authentication_and_exact_world_selector(monkeypatch):
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", "x" * 40)
    monkeypatch.setattr(live, "get_world_container", lambda root, world: SimpleNamespace(world_id=world))
    monkeypatch.setattr(live, "managed_world_data_root", lambda root: root)
    reference = ref()
    called = []
    def read_action(self, *, world_id, action_id):
        called.append((world_id, action_id))
        if world_id != reference.world_id or action_id != reference.action_id:
            from application_state.errors import ApplicationStateValidationError
            raise ApplicationStateValidationError("unavailable")
        return SimpleNamespace(consultation=SimpleNamespace(prompt_references=[reference]))
    monkeypatch.setattr(evidence.PlanActionDialogueService, "read_prompt_action", read_action)
    monkeypatch.setattr(evidence, "read_prompt", lambda ref: '{"input":"private"}')
    app = FastAPI(); app.include_router(live.router)
    client = TestClient(app, client=("127.0.0.1", 12345))
    path = f"/api/live/world-plan-edit/actions/{reference.action_id}/prompts"
    assert client.get(path, params={"world_id": reference.world_id}).status_code == 401
    assert not called
    headers = {"Authorization": "Bearer " + "x" * 40}
    for suffix in ("", f"/{reference.provider_attempt_id}"):
        response = client.get(path + suffix, params={"world_id": reference.world_id}, headers=headers)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store" and response.headers["pragma"] == "no-cache"
        assert "evidence_id" not in response.text and "dispatch_fence" not in response.text
    assert client.get(path, params={"world_id": "other-world"}, headers=headers).status_code == 404
    assert client.get(path + f"/{uuid4()}", params={"world_id": reference.world_id}, headers=headers).status_code == 404
    assert client.get(path + '?world_id=world-a&world_id=world-a', headers=headers).status_code == 422
    assert client.get(path, params={"world_id": reference.world_id, "evidence_id": str(reference.evidence_id)}, headers=headers).status_code == 422
