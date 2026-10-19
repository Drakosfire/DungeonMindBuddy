"""Owning HTTP/provider/storage and exact-scene boundaries for reviewed Play edits."""
import asyncio
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException

from application_state.play.edition_service import read_content
from application_state.play_scene_edit import PlaySceneEditProposalService
from apps.live_control_server.routes import play_runs as routes
from apps.live_control_server.services import play_scene_edit_proposal as service
from apps.live_control_server.services import agent_graph_auth
from tests.test_agent_play_surface_context import _create_real_world_play_context


def http(app, method, path, body=None):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path, json=body)
    return asyncio.run(run())


def app_for(monkeypatch, root):
    monkeypatch.setattr(agent_graph_auth, "enforce_native_graph_gm", lambda request: SimpleNamespace(subject="test-gm"))
    from apps.live_control_server import config
    monkeypatch.setattr(config, "managed_world_data_root", lambda: root)
    app = FastAPI()
    app.include_router(routes.router)
    return app


@pytest.mark.parametrize("method,suffix", [("GET", ""), ("GET", "/"+str(uuid4())), ("POST", "/"+str(uuid4()))])
def test_unauthorized_routes_reject_before_state_or_provider(monkeypatch, method, suffix):
    def deny(request):
        raise HTTPException(status_code=401, detail="GM required")
    monkeypatch.setattr(agent_graph_auth, "enforce_native_graph_gm", deny)
    monkeypatch.setattr(service, "propose_scene_edit", lambda **kw: pytest.fail("provider/state reached"))
    monkeypatch.setattr(PlaySceneEditProposalService, "get", lambda *a, **kw: pytest.fail("store reached"))
    monkeypatch.setattr(PlaySceneEditProposalService, "list_records", lambda *a, **kw: pytest.fail("store reached"))
    app = FastAPI()
    app.include_router(routes.router)
    response = http(app, method, "/api/live/world-play-runs/v2/"+str(uuid4())+"/content/proposals"+suffix+"?world_id=world", {})
    assert response.status_code == 401


class Generator:
    def __init__(self, replacement):
        self.replacement = replacement
        self.calls = []
    async def generate_structured(self, request):
        self.calls.append(request)
        return SimpleNamespace(parsed={"replacement_markdown": self.replacement, "summary": "Clarify the gate scene.",
            "assumptions": ["A proposed preparation detail."], "cannot_complete_reason": None},
            observation=SimpleNamespace(response_model="test-model", resolved_model="test-model", latency_ms=12))


def test_http_propose_review_apply_and_replay_leave_plan_notes_and_other_scenes_intact(tmp_path, application_state_dsn, monkeypatch):
    world, obj, pin, run = _create_real_world_play_context(tmp_path)
    content = read_content(world_id=world.world_id, run_id=run.run_id)
    start, end = service.scene_body_range(content.markdown, "scene:gate-line")
    replacement = content.markdown[start:end].replace("Guards waver", "Guards brace") + "\n| Name | State |\n| --- | --- |\n| Lantern | Lit |\n\n> [!READ-ALOUD]\n> The gate is waiting.\n"
    generator = Generator(replacement)
    monkeypatch.setattr(service.GenerationClient, "from_env", lambda: generator)
    monkeypatch.setattr(service, "load_dungeonmindbuddy_dotenv", lambda: None)
    monkeypatch.setattr(service, "load_buddy_model_policy", lambda **kw: {"actions": {"structured_generation": "writer"}, "models": {"writer": "test-model"}})
    app = app_for(monkeypatch, tmp_path)
    proposal_id = str(uuid4())
    command = str(uuid4())
    path = f"/api/live/world-play-runs/v2/{run.run_id}/content/proposals/{proposal_id}?world_id={world.world_id}"
    request = {"schema_version": "dmb_play_scene_edit_request_v1", "run_revision": run.run_revision,
        "content_basis": {"edition_revision": 0, "edition_revision_id": None, "content_sha256": content.content_sha256},
        "scene_id": "scene:gate-line", "instruction": "Clarify this scene, preserving choices, and add the table/read aloud."}
    response = http(app, "POST", path, request)
    assert response.status_code == 200, response.text
    record = response.json()
    assert record["status"] == "ready", record
    assert "context_receipt" not in record and "request" not in record
    assert "scene_note" not in record["basis"]
    assert len(generator.calls) == 1
    result = record["result"]
    assert result["candidate_markdown"].startswith(content.markdown[:start])
    assert result["candidate_markdown"].endswith(content.markdown[end:])
    assert read_content(world_id=world.world_id, run_id=run.run_id) == content  # proposal is inert
    commit = {"schema_version": "dmb_world_play_run_content_commit_v1", "expected_origin": content.origin.model_dump(mode="json"),
        "expected_edition_revision": 0, "expected_content_sha256": content.content_sha256,
        "expected_run_revision": run.run_revision, "markdown": result["candidate_markdown"]}
    saved = http(app, "PUT", f"/api/live/world-play-runs/v2/{run.run_id}/content/commands/{command}?world_id={world.world_id}", commit)
    assert saved.status_code == 200, saved.text
    assert saved.json()["observed_run_revision"] == run.run_revision
    effective = read_content(world_id=world.world_id, run_id=run.run_id)
    assert effective.markdown == result["candidate_markdown"] and effective.edition_revision == 1
    from apps.live_control_server.services.workspace_document_registry import get_committed_playable_revision
    assert get_committed_playable_revision(str(obj.work_object_id), revision_n=pin.revision_n, expected_sha256=pin.content_sha256, kind=None, expected_world_id=world.world_id).markdown == content.markdown
    from apps.live_control_server.services.play_run_registry import get_world_play_run
    retained = get_world_play_run(tmp_path, world_id=world.world_id, run_id=run.run_id)
    assert retained.progress == run.progress and retained.run_revision == run.run_revision
    replay = http(app, "POST", path, request)
    assert replay.json() == record and len(generator.calls) == 1
    conflict = http(app, "POST", path, {**request, "instruction": "Different instruction"})
    assert conflict.status_code == 409 and len(generator.calls) == 1
    listed = http(app, "GET", f"/api/live/world-play-runs/v2/{run.run_id}/content/proposals?world_id={world.world_id}")
    assert listed.json()["proposals"] == [record]


def test_stale_scene_rejected_before_generation(tmp_path, application_state_dsn, monkeypatch):
    world, _, pin, run = _create_real_world_play_context(tmp_path)
    app = app_for(monkeypatch, tmp_path)
    monkeypatch.setattr(service.GenerationClient, "from_env", lambda: pytest.fail("stale request dispatched"))
    path = f"/api/live/world-play-runs/v2/{run.run_id}/content/proposals/{uuid4()}?world_id={world.world_id}"
    request = {"run_revision": run.run_revision, "content_basis": {"edition_revision": 0, "edition_revision_id": None, "content_sha256": pin.content_sha256}, "scene_id": "scene:the-crush", "instruction": "Edit it"}
    assert http(app, "POST", path, request).status_code == 409
    request["scene_id"] = "scene:gate-line"
    request["content_basis"]["content_sha256"] = "0"*64
    assert http(app, "POST", path, request).status_code == 409


def test_exact_unicode_crlf_range_and_structural_or_media_escape_rejected():
    original = "\ufeff---\r\nname: Test\r\n---\r\n<!-- dmb-playable-element:v2 kind=beat id=beat:road -->\r\n## Road\r\n\r\n<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->\r\n### Gate\r\n\r\n🧙 waits.\r\n\r\n<!-- dmb-playable-element:v2 kind=scene id=scene:lake -->\r\n### Lake\r\n\r\nUnchanged.\r\n"
    start, end = service.scene_body_range(original, "scene:gate")
    result = service.build_candidate(original, "scene:gate", "🧙 listens.")
    assert result["candidate_markdown"] == original[:start]+result["replacement_markdown"]+original[end:]
    assert result["body_start_utf8"] == len(original[:start].encode())
    for fragment in ["<!-- dmb-playable-element:v2 kind=scene id=scene:new -->\n### New", "<script>alert(1)</script>", "![New](dmb-media:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa)", "![Outside](https://example.com/map.png)"]:
        with pytest.raises(ValueError):
            service.build_candidate(original, "scene:gate", fragment)


def test_failed_and_pending_proposals_never_redispatch(tmp_path, application_state_dsn, monkeypatch):
    from apps.live_control_server.models.play_scene_edit_proposal import PlaySceneEditProposalRequest
    from apps.live_control_server.services.agent_play_surface_context import resolve_world_play_session_turn_snapshot
    world, _, pin, run = _create_real_world_play_context(tmp_path)
    app = app_for(monkeypatch, tmp_path)
    generator = Generator("![New image](https://example.com/unknown.png)")
    monkeypatch.setattr(service.GenerationClient, "from_env", lambda: generator)
    monkeypatch.setattr(service, "load_dungeonmindbuddy_dotenv", lambda: None)
    monkeypatch.setattr(service, "load_buddy_model_policy", lambda **kw: {"actions": {"structured_generation": "writer"}, "models": {"writer": "test-model"}})
    request = PlaySceneEditProposalRequest(run_revision=run.run_revision, scene_id="scene:gate-line", instruction="Edit the scene",
        content_basis={"edition_revision": 0, "edition_revision_id": None, "content_sha256": pin.content_sha256})
    proposal_id = uuid4()
    path = f"/api/live/world-play-runs/v2/{run.run_id}/content/proposals/{proposal_id}?world_id={world.world_id}"
    failed = http(app, "POST", path, request.model_dump(mode="json"))
    assert failed.status_code == 200 and failed.json()["status"] == "failed"
    assert http(app, "POST", path, request.model_dump(mode="json")).json() == failed.json()
    assert len(generator.calls) == 1
    _, receipt = resolve_world_play_session_turn_snapshot(root=tmp_path, world_id=world.world_id, run_id=run.run_id,
        run_revision=run.run_revision, content_basis=request.content_basis)
    pending_id = uuid4()
    PlaySceneEditProposalService().reserve(world_id=world.world_id, run_id=run.run_id, proposal_id=pending_id,
        request=request.model_dump(mode="json"), context_receipt=receipt)
    pending = http(app, "POST", path.replace(str(proposal_id), str(pending_id)), request.model_dump(mode="json"))
    assert pending.json()["status"] == "pending" and len(generator.calls) == 1
    assert read_content(world_id=world.world_id, run_id=run.run_id).edition_revision == 0


def test_existing_media_presentation_can_change_without_new_media_identity():
    original = '<!-- dmb-playable-element:v2 kind=beat id=beat:road -->\n## Road\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->\n### Gate\n\n![Map](dmb-media:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa "dmb-image:v1 width=30 collapsed=false")\n'
    result = service.build_candidate(original, "scene:gate", '![Map detail](dmb-media:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa "dmb-image:v1 width=70 collapsed=true")')
    assert "width=70 collapsed=true" in result["candidate_markdown"]


def test_scene_can_reuse_a_saved_media_reference_in_its_admitted_beat_context():
    media = "dmb-media:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    original = f'<!-- dmb-playable-element:v2 kind=beat id=beat:road -->\n## Road\n\n![Area map]({media})\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->\n### Gate\n\nThe gate waits.\n'
    candidate = service.build_candidate(original, "scene:gate", f'![Scene map]({media})', admitted_media={media})
    assert candidate["candidate_markdown"].count(media) == 2
    with pytest.raises(ValueError, match="outside the admitted"):
        service.build_candidate(original, "scene:gate", "![Invented](dmb-media:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb)", admitted_media={media})
