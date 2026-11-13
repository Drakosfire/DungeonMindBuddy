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

        from apps.live_control_server.services import build_pdf_capture_review

        async def review_capture(png, instruction):
            assert png == b"fixture PNG"
            assert instruction == "Extract only AC."
            return "Armor Class 16"

        monkeypatch.setattr(build_pdf_capture_review, "review_capture", review_capture)
        calls.clear()
        review_path = path + "/review"
        payload = {"region": locator, "instruction": "Extract only AC."}
        assert client.post(review_path, json=payload).status_code == 401
        assert client.post(review_path.replace("world-a", "world-b"), json=payload,
                           headers=auth).status_code == 404
        assert calls == []
        review = client.post(review_path, json=payload, headers=auth)
        assert review.status_code == 200, review.text
        assert review.json()["text"] == "Armor Class 16"
        assert all(review.json()["region"][key] == value for key, value in locator.items())
        assert calls == [(body, 1)]

        from generationengine.failures import FailureCode
        from generationengine.providers.errors import ProviderError

        async def failed_review(_png, _instruction):
            raise ProviderError.from_code(
                FailureCode.CONFIGURATION_UNAVAILABLE,
                "provider configuration unavailable",
            )

        monkeypatch.setattr(build_pdf_capture_review, "review_capture", failed_review)
        failed = client.post(review_path, json=payload, headers=auth)
        assert failed.status_code == 503
        assert failed.headers["content-type"].startswith("application/json")
        assert failed.json() == {
            "detail": "Buddy could not review this capture. Check provider configuration and retry."
        }

        import json
        from pathlib import Path

        from apps.live_control_server.services import statblock_definition_validation

        fixtures = Path(__file__).parent / "fixtures" / "statblocks" / "v1"
        definition = json.loads((fixtures / "candidate-response.json").read_text())["definition"]
        validated = []

        def validate_definition(*, definition):
            validated.append(definition)
            return statblock_definition_validation.ValidateDefinitionBuddyResponseV1(
                outcome="success", definition_digest="sha256:fixture",
            )

        monkeypatch.setattr(statblock_definition_validation, "validate_definition", validate_definition)
        validation_path = path + "/statblock:validate"
        crop = locator | {"right": 0.5}
        candidate = {"definition": definition, "regions": [locator, crop]}
        assert client.post(validation_path, json=candidate).status_code == 401
        assert client.post(validation_path, json=candidate | {"definition": {}}, headers=auth).status_code == 422
        assert client.post(validation_path, json=candidate | {"regions": []}, headers=auth).status_code == 422
        assert client.post(validation_path, json=candidate | {"regions": [locator, crop | {"page": 2}]},
                           headers=auth).status_code == 422
        assert client.post(validation_path.replace("world-a", "world-b"), json=candidate,
                           headers=auth).status_code == 404
        assert not validated
        result = client.post(validation_path, json=candidate, headers=auth)
        assert result.status_code == 200, result.text
        assert result.json()["validation"]["definition_digest"] == "sha256:fixture"
        assert result.json()["regions"] == [
            item | {"schema_version": "dm_native_pdf_region_v1"} for item in (locator, crop)
        ]
        assert len(validated) == 1

        from application_state import pdf_statblock_review

        stored = {}
        world_review_id = "00000000-0000-4000-8000-000000000002"

        def save_review(*, world_id, review_id, expected_revision, definition, regions):
            assert expected_revision == 0
            record = {"revision": 1, "definition": definition, "regions": regions}
            stored[world_id, str(review_id)] = record
            return record

        def read_review(*, world_id, review_id):
            return stored.get((world_id, str(review_id)))

        monkeypatch.setattr(pdf_statblock_review, "save_review", save_review)
        monkeypatch.setattr(pdf_statblock_review, "read_review", read_review)
        review_route = path + "/statblock-reviews/" + world_review_id
        draft = candidate | {"expected_revision": 0}
        assert client.put(review_route, json=draft).status_code == 401
        assert client.put(review_route, json=draft | {"regions": [locator | {"page": 2}]},
                          headers=auth).status_code == 422
        assert not stored
        saved = client.put(review_route, json=draft, headers=auth)
        assert saved.status_code == 200, saved.text
        assert client.get(review_route).status_code == 401
        assert client.get(review_route.replace("world-a", "world-b"), headers=auth).status_code == 404
        assert client.get(review_route, headers=auth).json() == saved.json()
        exact_validation = review_route + "/validate"
        validated.clear()
        assert client.post(exact_validation + "?expected_revision=1").status_code == 401
        assert client.post(exact_validation + "?expected_revision=2", headers=auth).status_code == 409
        assert not validated
        receipt = client.post(exact_validation + "?expected_revision=1", headers=auth)
        assert receipt.status_code == 200, receipt.text
        assert receipt.json()["revision"] == 1
        assert receipt.json()["regions"] == saved.json()["regions"]
        assert validated[0].model_dump(mode="json", by_alias=True) == saved.json()["definition"]
        records.clear()
        assert client.get(review_route, headers=auth).status_code == 404


def test_saved_pdf_review_creature_draft_replays_at_exact_revision(monkeypatch, tmp_path):
    from application_state import pdf_statblock_review
    from apps.live_control_server.routes import statblock_storage

    def authorize(request):
        if request.headers.get("authorization") != "Bearer fixture":
            raise HTTPException(status_code=401)

    monkeypatch.setattr(agent, "enforce_native_graph_gm", authorize)
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(statblock_storage, "statblock_data_root", lambda _: tmp_path)
    review = {"revision": 2, "regions": [], "definition": {
        "identity": {"name": "Fixture tree"},
        "ruleset": {"system": "dnd5e", "edition": "2024"},
        "movement": {"walk": 0}, "challenge": {"proficiency_bonus": 2},
    }}
    monkeypatch.setattr(pdf_statblock_review, "read_review",
                        lambda *, world_id, review_id: review if world_id == "world-a" else None)
    app = FastAPI()
    app.include_router(agent.router)
    route = ("/agent/worlds/world-a/build-pdf-sources/statblock-reviews/"
             "00000000-0000-4000-8000-000000000001/creature-draft")
    auth = {"Authorization": "Bearer fixture"}
    with TestClient(app) as client:
        assert client.post(route, params={"expected_revision": 2}).status_code == 401
        assert client.post(route, params={"expected_revision": 1}, headers=auth).status_code == 409
        assert client.post(route.replace("world-a", "world-b"), params={"expected_revision": 2},
                           headers=auth).status_code == 404
        created = client.post(route, params={"expected_revision": 2}, headers=auth)
        assert created.status_code == 200, created.text
        replay = client.post(route, params={"expected_revision": 2}, headers=auth)
        assert replay.status_code == 200 and replay.json() == created.json()
