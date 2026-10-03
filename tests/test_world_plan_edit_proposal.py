"""World-only Plan edits are inert proposals bound to the exact saved Plan."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from threading import Event
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.live_control_server.models.plan_document_edit_proposal import (
    WorldPlanDocumentEditProposalRequest,
)
from apps.live_control_server.routes import live, workspace_documents
from apps.live_control_server.services import plan_document_edit_proposal as service
from apps.live_control_server.services.workspace_document_registry import (
    WorldOwnedCommittedRevisionV2,
)
from apps.live_control_server.services.world_container_registry import create_world_container
from application_state.plan_action_dialogue.service import PlanActionDialogueService


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _request(**overrides) -> WorldPlanDocumentEditProposalRequest:
    data = {
        "idempotency_key": str(uuid4()),
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
    def __init__(self, replacement_markdown: str = "The shutters rattle in the wind.") -> None:
        self.requests: list = []
        self.replacement_markdown = replacement_markdown

    async def generate_structured(self, request):
        self.requests.append(request)
        return SimpleNamespace(
            parsed={
                "replacement_markdown": self.replacement_markdown,
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


class _FakeActionStore:
    def __init__(self) -> None:
        self.reservations = []
        self.finished = []
        self.action_id = None
        self.existing = None

    def get_by_key(self, _key):
        return self.existing

    def reserve(self, request):
        self.reservations.append(request)
        self.action_id = uuid4()
        return SimpleNamespace(
            action_id=self.action_id, dispatch_token=uuid4(), fence=1, status="pending"
        ), True

    def finish(self, **kwargs):
        self.finished.append(kwargs)
        return SimpleNamespace(status=kwargs["status"])


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
    snapshot = WorldOwnedCommittedRevisionV2(
        world_id=document_world_id,
        document_id="plan-1",
        kind=kind,
        status=status,
        object_revision=revision,
        work_revision_id=str(UUID("00000000-0000-4000-8000-000000000001")),
        revision_n=3,
        markdown=saved_markdown,
        content_sha256=_sha(saved_markdown),
        title="Plan",
    )
    monkeypatch.setattr(service, "get_world_container", lambda *_: world)
    monkeypatch.setattr(service, "get_committed_playable_revision", lambda *_args, **_kwargs: snapshot)
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
            action_store=_FakeActionStore(),
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
    action_store = _FakeActionStore()
    result = service.propose_world_plan_document_edit(
        root=tmp_path,
        request=_request(),
        generation_client=fake,
        model="test-model",
        action_store=action_store,
    )

    assert result.schema_version == "dmb_world_plan_document_edit_proposal_v1"
    assert result.action_id == action_store.action_id
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
    assert fake.requests[0].deadline_ms == 60_000
    assert action_store.reservations[0].basis.object_revision == 2
    assert action_store.reservations[0].basis.revision_n == 3
    assert action_store.reservations[0].draft_matches_basis is False
    assert action_store.finished[0]["status"] == "completed"
    context = json.loads(fake.requests[0].user_prompt)
    assert context["current_plan_markdown"] == "# Current local draft\n"
    assert "SAVED SERVER PROSE" not in fake.requests[0].user_prompt


def test_same_key_retry_reconciles_original_basis_after_plan_advances(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _authority(monkeypatch)
    request = _request()
    action_store = _FakeActionStore()
    basis = service._validate_world_authority(tmp_path, request)
    action_store.existing = SimpleNamespace(
        status="pending",
        basis=basis,
        request_fingerprint=service._action_fingerprint(request, basis),
    )
    monkeypatch.setattr(
        service,
        "get_committed_playable_revision",
        lambda *_args, **_kwargs: pytest.fail("idempotency hit must not rebind to current Plan basis"),
    )
    fake = _FakeGenerationClient()
    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=request,
            generation_client=fake,
            model="test-model",
            action_store=action_store,
        )
    assert caught.value.code == "action_pending"
    assert fake.requests == []


def test_completed_action_can_deliver_late_only_for_its_original_basis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    application_state_dsn: str,
) -> None:
    from threading import Event

    from application_state.plan_action_dialogue.types import PlanActionBasis

    original_snapshot = _authority(monkeypatch)
    request = _request()
    original_basis = PlanActionBasis(
        world_id="world-1",
        document_id="plan-1",
        object_revision=original_snapshot.object_revision,
        work_revision_id=UUID(original_snapshot.work_revision_id),
        revision_n=original_snapshot.revision_n,
        content_sha256=original_snapshot.content_sha256,
    )
    completed = Event()
    release_response = Event()

    class _HoldCompletedResponse(PlanActionDialogueService):
        def finish(self, **kwargs):
            result = super().finish(**kwargs)
            if kwargs["status"] == "completed":
                completed.set()
                if not release_response.wait(timeout=5):
                    raise TimeoutError("test did not release completed proposal response")
            return result

    store = _HoldCompletedResponse()
    fake = _FakeGenerationClient("LATE-REPLACEMENT-SENTINEL")
    executor = ThreadPoolExecutor(max_workers=1)
    future = None
    try:
        future = executor.submit(
            service.propose_world_plan_document_edit,
            root=tmp_path,
            request=request,
            generation_client=fake,
            model="test-model",
            action_store=store,
        )
        assert completed.wait(timeout=5)
        recorded = store.get_by_key(request.idempotency_key)
        assert recorded is not None
        assert recorded.status == "completed"
        assert recorded.basis == original_basis
        assert recorded.lease_expires_at is None

        _authority(monkeypatch, revision=3, saved_markdown="A newer committed Plan.")
        current_projection = service.get_world_plan_action_projection(
            root=tmp_path,
            world_id="world-1",
            document_id="plan-1",
            action_store=store,
        )
        assert current_projection.basis.object_revision == 3
        assert current_projection.actions == []

        release_response.set()
        response = future.result(timeout=5)
        assert response.action_id == recorded.action_id
        assert response.idempotency_key == request.idempotency_key
        assert response.base_revision == original_basis.object_revision
        assert response.base_content_sha256 == original_basis.content_sha256
        assert response.replacement_markdown == "LATE-REPLACEMENT-SENTINEL"
        assert len(fake.requests) == 1
    finally:
        release_response.set()
        if future is not None:
            future.result(timeout=5)
        executor.shutdown(wait=True, cancel_futures=True)


def test_persistence_uncertainty_never_returns_uncommitted_proposal_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    application_state_dsn: str,
) -> None:
    _authority(monkeypatch)

    class _CommitThenLoseReceipt(PlanActionDialogueService):
        def finish(self, **kwargs):
            result = super().finish(**kwargs)
            if kwargs["status"] == "completed":
                raise OSError("test simulates a lost persistence acknowledgement")
            return result

    store = _CommitThenLoseReceipt()
    fake = _FakeGenerationClient("UNRETURNED-REPLACEMENT-SENTINEL")
    request = _request()
    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=request,
            generation_client=fake,
            model="test-model",
            action_store=store,
        )
    assert caught.value.code == "action_persistence_uncertain"
    assert caught.value.status_code == 503
    assert len(fake.requests) == 1

    recorded = store.get_by_key(request.idempotency_key)
    assert recorded is not None
    assert recorded.status == "completed"
    assert recorded.assistant_summary == "Add a tense beat"
    assert recorded.assistant_summary != "UNRETURNED-REPLACEMENT-SENTINEL"
    assert store.completed_context(recorded.basis)[0].assistant_summary == "Add a tense beat"
    retry_fake = _FakeGenerationClient()
    with pytest.raises(service.PlanDocumentEditProposalError) as retry:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=request,
            generation_client=retry_fake,
            model="test-model",
            action_store=store,
        )
    assert retry.value.code == "action_already_completed"
    assert retry_fake.requests == []


def test_world_replacement_prompt_allows_only_echoing_existing_protected_tokens(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    marker = "<!-- dmb-playable-element:v2 kind=scene id=scene:town-breathes -->"
    link = "[Lysandra Ironveil](dmb-node:node:captain-lysandra-ironveil)"
    section = f"{marker}\n### Mireward After the Attack\n\n{link} is present.\n"
    _authority(monkeypatch)
    fake = _FakeGenerationClient(section)
    action_store = _FakeActionStore()
    result = service.propose_world_plan_document_edit(
        root=tmp_path,
        request=_request(draft_markdown=section, draft_sha256=_sha(section), selected_text=section),
        generation_client=fake,
        model="test-model",
        action_store=action_store,
    )

    assert result.replacement_markdown == section.strip()
    prompt = fake.requests[0].system_prompt
    assert "For this World replace-selection request only" in prompt
    assert "exact original spelling" in prompt
    assert "Never invent, change, remove, reorder, duplicate" in prompt
    assert "graph identities or graph truth" in prompt
    context = json.loads(fake.requests[0].user_prompt)
    assert context["selected_text"] == section
    assert context["current_plan_markdown"] == section


def test_world_caret_prompt_keeps_the_restricted_shared_grammar(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _authority(monkeypatch)
    fake = _FakeGenerationClient()
    service.propose_world_plan_document_edit(
        root=tmp_path,
        request=_request(target_kind="insert_at_caret", selected_text=""),
        generation_client=fake,
        model="test-model",
        action_store=_FakeActionStore(),
    )

    assert fake.requests[0].system_prompt == service._SYSTEM_PROMPT
    normalized_prompt = " ".join(fake.requests[0].system_prompt.split())
    assert "Do not produce HTML, graph node IDs, file paths, or unknown component markers." in normalized_prompt


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
        "idempotency_key": str(uuid4()),
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
    assert response.json()["idempotency_key"] == request["idempotency_key"]
    assert "session" not in response.json()
    assert len(fake.requests) == 1
    assert "Explicit unsaved editor draft" in fake.requests[0].user_prompt
    assert "Saved server-only prose" not in fake.requests[0].user_prompt

    retry = client.post("/api/live/world-plan-edit/propose", json=request)
    assert retry.status_code == 409
    assert "replacement_markdown" not in retry.json()
    assert len(fake.requests) == 1
    conflicting_retry = client.post(
        "/api/live/world-plan-edit/propose",
        json={**request, "instruction": "Use the same key for different intent."},
    )
    assert conflicting_retry.status_code == 409
    assert conflicting_retry.json()["detail"]["code"] == "action_idempotency_conflict"
    assert len(fake.requests) == 1
    actions = client.get(
        "/api/live/world-plan-edit/actions",
        params={"world_id": world.world_id, "document_id": document_id},
    )
    assert actions.status_code == 200
    assert actions.json()["actions"][0]["status"] == "completed"
    assert actions.json()["actions"][0]["assistant_summary"] == response.json()["summary"]
    assert "draft_sha256" not in json.dumps(actions.json())
    assert "replacement_markdown" not in json.dumps(actions.json())

    rejected = client.post("/api/live/world-plan-edit/propose", json={**request, "session": 1})
    assert rejected.status_code == 422
    assert len(fake.requests) == 1
    saved_after = client.get(f"/api/live/workspace-documents/{document_id}/snapshot").json()
    assert saved_after["loaded_revision"] == saved_before["loaded_revision"]
    assert saved_after["content_sha256"] == saved_before["content_sha256"]
    assert saved_after["markdown"] == committed_markdown


def test_late_provider_result_loses_expired_action_fence_without_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    world = create_world_container(tmp_path, name="Late Plan action world")
    client = _client(monkeypatch, tmp_path)
    created = client.post(
        "/api/live/workspace-documents/world-plans",
        json={
            "schema_version": "dmb_workspace_document_create_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "title": "Late Plan",
        },
    )
    assert created.status_code == 200
    document_id = created.json()["document_id"]
    committed_markdown = "# The saved Plan\n"
    prepared = client.post(
        "/api/live/tiptap/markdown-write/prepare",
        json={
            "schema_version": "dmb_tiptap_markdown_write_prepare_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "document_id": document_id,
            "markdown": committed_markdown,
            "expected_revision": created.json()["revision"],
        },
    )
    assert prepared.status_code == 200
    prepared_body = prepared.json()
    committed = client.post(
        "/api/live/tiptap/markdown-write/commit",
        json={
            "schema_version": "dmb_tiptap_markdown_write_commit_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "document_id": document_id,
            "markdown": committed_markdown,
            "expected_revision": prepared_body["registry_revision"],
            "writer_confirm_token": prepared_body["writer_confirm_token"],
        },
    )
    assert committed.status_code == 200
    saved = client.get(f"/api/live/workspace-documents/{document_id}/snapshot").json()

    entered = Event()
    release = Event()

    class _BlockingGenerationClient:
        def __init__(self) -> None:
            self.calls = 0
            self.reservation_seen = False

        async def generate_structured(self, generation_request):
            self.calls += 1
            with psycopg.connect(application_state_dsn) as conn:
                row = conn.execute(
                    "SELECT status, dispatch_token, lease_expires_at FROM plan_action.action WHERE idempotency_key = %s",
                    (request["idempotency_key"],),
                ).fetchone()
            self.reservation_seen = bool(row and row[0] == "pending" and row[1] and row[2])
            entered.set()
            if not release.wait(timeout=8):
                raise TimeoutError("test did not release blocked generation")
            return SimpleNamespace(
                parsed={
                    "replacement_markdown": "STALE-REPLACEMENT-SENTINEL",
                    "summary": "STALE-SUMMARY-SENTINEL",
                    "assumptions": [],
                    "cannot_complete_reason": None,
                },
                observation=SimpleNamespace(
                    response_model="observed-test-model",
                    resolved_model="test-model",
                    latency_ms=1,
                    input_tokens=1,
                    output_tokens=1,
                ),
            )

    fake = _BlockingGenerationClient()
    monkeypatch.setattr(service, "_resolve_model", lambda: "test-model")
    monkeypatch.setattr(service.GenerationClient, "from_env", lambda: fake)
    draft = "# Mounted Plan draft\n"
    request = {
        "idempotency_key": str(uuid4()),
        "document_id": document_id,
        "world_id": world.world_id,
        "base_revision": saved["loaded_revision"],
        "base_content_sha256": saved["content_sha256"],
        "draft_markdown": draft,
        "draft_sha256": _sha(draft),
        "target_kind": "insert_at_caret",
        "selected_text": "",
        "instruction": "Add a distant bell.",
        "conversation_history": [],
    }

    executor = ThreadPoolExecutor(max_workers=1)
    future = None
    try:
        future = executor.submit(client.post, "/api/live/world-plan-edit/propose", json=request)
        assert entered.wait(timeout=5)
        assert fake.calls == 1
        assert fake.reservation_seen

        duplicate = client.post("/api/live/world-plan-edit/propose", json=request)
        assert duplicate.status_code == 409
        assert fake.calls == 1

        with psycopg.connect(application_state_dsn) as conn:
            conn.execute(
                "UPDATE plan_action.action SET lease_expires_at = clock_timestamp() - interval '1 second' WHERE idempotency_key = %s",
                (request["idempotency_key"],),
            )
        status_page = client.get(
            "/api/live/world-plan-edit/actions",
            params={"world_id": world.world_id, "document_id": document_id},
        )
        assert status_page.status_code == 200
        action = status_page.json()["actions"][0]
        assert action["status"] == "indeterminate"
        assert action["assistant_summary"] is None
        retry = client.post("/api/live/world-plan-edit/propose", json=request)
        assert retry.status_code == 409
        assert fake.calls == 1

        release.set()
        original = future.result(timeout=8)
        assert original.status_code == 409
        original_text = original.text
        assert "STALE-REPLACEMENT-SENTINEL" not in original_text
        assert "STALE-SUMMARY-SENTINEL" not in original_text
        assert "replacement_markdown" not in original_text
        final_page = client.get(
            "/api/live/world-plan-edit/actions",
            params={"world_id": world.world_id, "document_id": document_id},
        )
        assert final_page.json()["actions"][0]["status"] == "indeterminate"
        assert "STALE-SUMMARY-SENTINEL" not in json.dumps(final_page.json())
        with psycopg.connect(application_state_dsn) as conn:
            status, summary, fence = conn.execute(
                "SELECT status, assistant_summary, fence FROM plan_action.action WHERE idempotency_key = %s",
                (request["idempotency_key"],),
            ).fetchone()
        assert status == "indeterminate"
        assert summary is None
        assert fence == 2
        assert fake.calls == 1
    finally:
        release.set()
        if future is not None:
            future.result(timeout=8)
        executor.shutdown(wait=True, cancel_futures=True)
