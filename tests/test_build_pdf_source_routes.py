from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from apps.live_control_server.integrations.dungeonmind import native_world_source_admission
from apps.live_control_server.routes import agent
from dungeonmind.application.vnext.native_source_admission import build_native_pdf_source_records


def test_pdf_upload_and_reopen_use_verified_world(monkeypatch):
    records = {}

    class Repository:
        def retain_native_pdf_source(self, command, body):
            artifact, revision = build_native_pdf_source_records(command, body)
            records[command.space_id, revision.source_revision_id] = (artifact, revision, 1, body)
            return revision

        def get_native_pdf_source(self, space, revision):
            return records.get((space, revision))

    def authorize(request):
        if request.headers.get("authorization") != "Bearer fixture":
            raise HTTPException(status_code=401)

    monkeypatch.setattr(agent, "enforce_native_graph_gm", authorize)
    monkeypatch.setattr(agent, "_verified_world_id", lambda world_id: world_id)
    monkeypatch.setattr(native_world_source_admission, "_repository", Repository)
    monkeypatch.setattr(
        native_world_source_admission, "_source_world_binding",
        lambda _root, world: SimpleNamespace(native_world_id=f"space:{world}"),
    )
    app = FastAPI()
    app.include_router(agent.router)
    path = "/agent/worlds/world-a/build-pdf-sources"
    upload = path + "?admission_id=00000000-0000-4000-8000-000000000001"
    body = b"%PDF-1.7\n"
    auth = {"Authorization": "Bearer fixture"}
    with TestClient(app) as client:
        assert client.post(upload, content=body).status_code == 401
        admitted = client.post(upload, content=body, headers={
            **auth, "Content-Type": "application/pdf", "X-Pdf-Created-At": "2026-11-11T00:00:00Z",
        })
        assert admitted.status_code == 200, admitted.text
        locator = admitted.json() | {"page": 1, "left": 0, "top": 0, "right": 1, "bottom": 1}
        assert client.post(path + "/open", json=locator).status_code == 401
        assert client.post(path.replace("world-a", "world-b") + "/open", json=locator,
                           headers=auth).status_code == 404
        opened = client.post(path + "/open", json=locator, headers=auth)
        assert opened.status_code == 200, opened.text
        assert opened.content == body
        assert opened.headers["cache-control"] == "no-store"

        from apps.live_control_server.services import build_pdf_region_render

        calls = []

        def render_region(pdf, region):
            calls.append((pdf, region.page))
            return b"fixture PNG"

        monkeypatch.setattr(build_pdf_region_render, "render_region", render_region)
        render_path = path + "/open?render=true"
        assert client.post(render_path, json=locator).status_code == 401
        assert client.post(render_path.replace("world-a", "world-b"), json=locator,
                           headers=auth).status_code == 404
        assert client.post(render_path, json=locator | {"page": 2},
                           headers=auth).status_code == 422
        assert calls == []
        rendered = client.post(render_path, json=locator, headers=auth)
        assert rendered.status_code == 200, rendered.text
        assert rendered.headers["content-type"] == "image/png"
        assert rendered.headers["cache-control"] == "no-store"
        assert rendered.content == b"fixture PNG"
        assert calls == [(body, 1)]

        from base64 import b64decode

        def read_crop(crop):
            assert b64decode(crop.png_base64) == b"fixture PNG"
            return {"text": "Armor Class 16"}

        monkeypatch.setattr(agent, "read_crop", read_crop)
        calls.clear()
        ocr_path = path + "/ocr"
        assert client.post(ocr_path, json=locator).status_code == 401
        assert client.post(ocr_path.replace("world-a", "world-b"), json=locator,
                           headers=auth).status_code == 404
        assert client.post(ocr_path, json=locator | {"page": 2},
                           headers=auth).status_code == 422
        assert calls == []
        transcription = client.post(ocr_path, json=locator, headers=auth)
        assert transcription.status_code == 200, transcription.text
        assert transcription.json() == {"text": "Armor Class 16"}
        assert calls == [(body, 1)]
