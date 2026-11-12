import asyncio
import json
from pathlib import Path

import httpx
import pytest

from apps.live_control_server.services import build_pdf_statblock_extraction as extraction


def test_model_request_contains_transcriptions_and_guidance_only(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-key")
    monkeypatch.setattr(extraction, "_model", lambda: "gpt-6-luna")
    calls = []
    def handle(request):
        calls.append(json.loads(request.content))
        return httpx.Response(400, json={"error": {"message": "fixture stop"}})

    with pytest.raises(extraction.StatblockExtractionError):
        asyncio.run(extraction.extract_statblock(
            ["Armor Class 16 transcription", "actions transcription"],
            "Preserve the printed action names.",
            transport=httpx.MockTransport(handle),
        ))

    assert len(calls) == 1
    body = calls[0]
    assert body["model"] == "gpt-6-luna"
    assert body["input"] == json.dumps({
        "author_guidance": "Preserve the printed action names.",
        "ocr_transcriptions": ["Armor Class 16 transcription", "actions transcription"],
    }, ensure_ascii=False)
    assert body["instructions"] == extraction.INSTRUCTIONS
    assert not body.get("tools")
    prompt = body["input"]
    for forbidden in ("source_revision_id", "content_sha256", "page_number", "left", "receipt", "telemetry"):
        assert forbidden not in prompt
    assert body["text"]["format"]["name"] == extraction.SCHEMA_NAME
    assert body["text"]["format"]["strict"] is True


def test_valid_structured_response_becomes_a_complete_candidate(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-key")
    monkeypatch.setattr(extraction, "_model", lambda: "gpt-6-luna")
    from apps.live_control_server.integrations.dungeonmind_statblocks.generated import StatblockDefinitionV1Input

    fixture = Path(__file__).parent / "fixtures" / "statblocks" / "v1" / "candidate-response.json"
    definition = StatblockDefinitionV1Input.model_validate(
        json.loads(fixture.read_text())["definition"],
    ).model_dump(mode="json", by_alias=True)
    output = json.dumps({"status": "complete", "definition": definition, "missing_details": []})
    calls = []

    def handle(request):
        body = json.loads(request.content)
        calls.append(body)
        response = {
            "id": "resp_pdf_statblock_fixture",
            "object": "response",
            "created_at": 1,
            "status": "completed",
            "model": body["model"],
            "output": [{
                "type": "message", "id": "msg_pdf_statblock_fixture", "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": output, "annotations": []}],
            }],
        }
        return httpx.Response(200, request=request, json=response)

    result = asyncio.run(extraction.extract_statblock(
        ["Ironhide Brute. Armor Class 15."], "Preserve printed values.",
        transport=httpx.MockTransport(handle),
    ))

    assert result.status == "complete"
    assert result.definition.model_dump(mode="json", by_alias=True) == definition
    assert result.missing_details == []
    assert len(calls) == 1


def test_extraction_prompt_does_not_add_host_locators():
    prompt = extraction.extraction_prompt(["OCR text"], "author note")
    assert json.loads(prompt) == {
        "author_guidance": "author note",
        "ocr_transcriptions": ["OCR text"],
    }


def test_incomplete_output_requires_missing_details():
    with pytest.raises(ValueError):
        extraction.StatblockExtractionOutput.model_validate({
            "status": "incomplete", "definition": None, "missing_details": [],
        })


def test_pdf_regions_create_only_a_source_linked_review_draft(monkeypatch):
    from pathlib import Path
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from application_state import pdf_statblock_review
    from apps.live_control_server.integrations.dungeonmind_statblocks.generated import StatblockDefinitionV1Input
    from apps.live_control_server.routes import agent

    fixtures = Path(__file__).parent / "fixtures" / "statblocks" / "v1"
    definition = json.loads((fixtures / "candidate-response.json").read_text())["definition"]
    candidate = StatblockDefinitionV1Input.model_validate(definition)
    calls = []
    saved = {}

    def authorize(request):
        if request.headers.get("authorization") != "Bearer fixture":
            raise HTTPException(status_code=401)

    monkeypatch.setattr(agent, "enforce_native_graph_gm", authorize)
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)

    class Region:
        def __init__(self, values):
            self.values = values

        @property
        def page(self):
            return self.values["page"]

        def model_dump(self, *, mode):
            return {"schema_version": "dm_native_pdf_region_v1", **self.values}

    def open_region(world, locator, request):
        calls.append(("open", locator["page"]))
        return b"verified PDF", Region(locator)

    monkeypatch.setattr(agent, "_authorized_build_pdf_region", open_region)
    monkeypatch.setattr(agent, "_render_build_pdf_region", lambda pdf, region: b"verified crop")

    def read_crop(crop):
        calls.append(("ocr", crop.png_base64))
        return {"text": f"OCR for region {len(calls)}"}

    monkeypatch.setattr(agent, "read_crop", read_crop)

    async def extract(transcriptions, instruction):
        calls.append(("extract", transcriptions, instruction))
        return extraction.StatblockExtractionOutput(
            status="complete", definition=candidate, missing_details=[],
        )

    monkeypatch.setattr(extraction, "extract_statblock", extract)

    def save_review(*, world_id, review_id, expected_revision, definition, regions):
        assert expected_revision == 0
        result = {"revision": 1, "definition": definition, "regions": regions}
        saved[world_id, str(review_id)] = result
        return result

    monkeypatch.setattr(pdf_statblock_review, "save_review", save_review)
    monkeypatch.setattr(
        pdf_statblock_review, "read_review",
        lambda *, world_id, review_id: saved.get((world_id, str(review_id))),
    )

    app = FastAPI()
    app.include_router(agent.router)
    review_id = "00000000-0000-4000-8000-000000000088"
    path = f"/agent/worlds/world-a/build-pdf-sources/statblock-reviews/{review_id}/from-regions"
    regions = [
        {"source_revision_id": "srev:one", "content_sha256": "a" * 64,
         "page": 1, "left": 0.0, "top": 0.0, "right": 0.5, "bottom": 1.0},
        {"source_revision_id": "srev:one", "content_sha256": "a" * 64,
         "page": 2, "left": 0.1, "top": 0.0, "right": 0.9, "bottom": 1.0},
    ]
    payload = {"regions": regions, "instruction": "Keep the printed names."}
    with TestClient(app) as client:
        assert client.post(path, json=payload).status_code == 401
        assert calls == []
        response = client.post(path, json=payload, headers={"Authorization": "Bearer fixture"})
        assert response.status_code == 200, response.text
        assert response.json()["revision"] == 1
        assert response.json()["definition"] == candidate.model_dump(mode="json", by_alias=True)
        assert response.json()["regions"] == [
            {"schema_version": "dm_native_pdf_region_v1", **region} for region in regions
        ]
        assert calls[:4] == [("open", 1), ("ocr", "dmVyaWZpZWQgY3JvcA=="),
                             ("open", 2), ("ocr", "dmVyaWZpZWQgY3JvcA==")]
        assert calls[4] == ("extract", ["OCR for region 2", "OCR for region 4"],
                            "Keep the printed names.")
        assert len(saved) == 1
        assert client.post(path, json=payload, headers={"Authorization": "Bearer fixture"}).json() == response.json()
        assert len([call for call in calls if call[0] == "extract"]) == 1


def test_incomplete_pdf_statblock_extraction_does_not_save(monkeypatch):
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from application_state import pdf_statblock_review
    from apps.live_control_server.routes import agent

    def authorize(request):
        if request.headers.get("authorization") != "Bearer fixture":
            raise HTTPException(status_code=401)

    monkeypatch.setattr(agent, "enforce_native_graph_gm", authorize)
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)

    class Region:
        page = 1
        def model_dump(self, *, mode):
            return {"schema_version": "dm_native_pdf_region_v1", **locator}

    locator = {"source_revision_id": "srev:one", "content_sha256": "a" * 64,
               "page": 1, "left": 0.0, "top": 0.0, "right": 1.0, "bottom": 1.0}
    monkeypatch.setattr(agent, "_authorized_build_pdf_region", lambda *args: (b"PDF", Region()))
    monkeypatch.setattr(agent, "_render_build_pdf_region", lambda *args: b"PNG")
    monkeypatch.setattr(agent, "read_crop", lambda crop: {"text": "partial transcription"})

    async def incomplete(transcriptions, instruction):
        return extraction.StatblockExtractionOutput(
            status="incomplete", definition=None, missing_details=["Hit Points", "ability scores"],
        )

    monkeypatch.setattr(extraction, "extract_statblock", incomplete)
    writes = []
    monkeypatch.setattr(pdf_statblock_review, "save_review", lambda **kwargs: writes.append(kwargs))
    monkeypatch.setattr(pdf_statblock_review, "read_review", lambda **kwargs: None)

    app = FastAPI()
    app.include_router(agent.router)
    path = "/agent/worlds/world-a/build-pdf-sources/statblock-reviews/00000000-0000-4000-8000-000000000089/from-regions"
    with TestClient(app) as client:
        response = client.post(path, json={"regions": [locator], "instruction": ""},
                               headers={"Authorization": "Bearer fixture"})
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "pdf_statblock_extraction_incomplete",
        "missing_details": ["Hit Points", "ability scores"],
    }
    assert writes == []


@pytest.mark.parametrize("failure", ["invalid_region", "ocr", "model"])
def test_pdf_statblock_failures_never_save_a_review(monkeypatch, failure):
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from application_state import pdf_statblock_review
    from apps.live_control_server.routes import agent

    monkeypatch.setattr(agent, "enforce_native_graph_gm", lambda request: None)
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    locator = {"source_revision_id": "srev:one", "content_sha256": "a" * 64,
               "page": 1, "left": 0.0, "top": 0.0, "right": 1.0, "bottom": 1.0}
    calls = []

    if failure == "invalid_region":
        def reject_region(*args):
            calls.append("region")
            raise HTTPException(status_code=403, detail={"code": "pdf_source_not_authorized"})

        monkeypatch.setattr(agent, "_authorized_build_pdf_region", reject_region)
    else:
        class Region:
            page = 1

            def model_dump(self, *, mode):
                return {"schema_version": "dm_native_pdf_region_v1", **locator}

        monkeypatch.setattr(agent, "_authorized_build_pdf_region", lambda *args: (b"PDF", Region()))
        monkeypatch.setattr(agent, "_render_build_pdf_region", lambda *args: b"PNG")
        if failure == "ocr":
            def reject_ocr(crop):
                calls.append("ocr")
                raise HTTPException(status_code=503, detail={"code": "pdf_statblock_ocr_unavailable"})

            monkeypatch.setattr(agent, "read_crop", reject_ocr)
        else:
            monkeypatch.setattr(agent, "read_crop", lambda crop: {"text": "Ironhide Brute"})

            async def reject_model(transcriptions, instruction):
                calls.append("model")
                raise extraction.StatblockExtractionError("pdf_statblock_generation_unavailable")

            monkeypatch.setattr(extraction, "extract_statblock", reject_model)

    writes = []
    monkeypatch.setattr(pdf_statblock_review, "save_review", lambda **kwargs: writes.append(kwargs))
    monkeypatch.setattr(pdf_statblock_review, "read_review", lambda **kwargs: None)
    app = FastAPI()
    app.include_router(agent.router)
    path = "/agent/worlds/world-a/build-pdf-sources/statblock-reviews/00000000-0000-4000-8000-000000000090/from-regions"

    with TestClient(app) as client:
        response = client.post(path, json={"regions": [locator], "instruction": ""})

    assert response.status_code == (403 if failure == "invalid_region" else 503)
    assert writes == []
    assert calls == ({"invalid_region": ["region"], "ocr": ["ocr"], "model": ["model"]}[failure])
