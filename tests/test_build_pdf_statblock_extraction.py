import asyncio
import json
from pathlib import Path

import httpx
import pytest
from generationengine.failures import FailureCode

from apps.live_control_server.services import build_pdf_statblock_extraction as extraction


def _inline_openai_platform_lookup(monkeypatch):
    # The SDK runs this host-only lookup in asyncio.to_thread. The local Python
    # runtime returns its result but leaves the selector loop asleep, so keep
    # this unrelated metadata lookup inline in provider-wire tests.
    import openai._base_client

    def asyncify(function):
        async def call(*args, **kwargs):
            return function(*args, **kwargs)
        return call

    monkeypatch.setattr(openai._base_client, "asyncify", asyncify)


def test_model_request_contains_transcriptions_and_guidance_only(monkeypatch):
    _inline_openai_platform_lookup(monkeypatch)
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
    wire_schema = body["text"]["format"]["schema"]
    assert '"$ref"' not in json.dumps(wire_schema)
    assert "$defs" not in wire_schema



def test_valid_structured_response_becomes_a_complete_candidate(monkeypatch):
    _inline_openai_platform_lookup(monkeypatch)
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


@pytest.mark.parametrize("failure_code", list(FailureCode))
def test_generation_failure_is_observed_without_exposing_prompt(monkeypatch, caplog, failure_code):
    from generationengine import GenerationEngineError
    from generationengine.failures import InferenceFailure
    from generationengine.observation import InferenceObservation, ObservationState

    monkeypatch.setenv("OPENAI_API_KEY", "fixture-key")
    monkeypatch.setattr(extraction, "_model", lambda: "gpt-6-luna")
    error = GenerationEngineError(
        InferenceFailure.from_code(failure_code, message="private fixture diagnostic"),
        InferenceObservation(
            provider="openai", requested_model="gpt-6-luna", resolved_model="gpt-6-luna",
            response_model="gpt-6-luna-2026-10-01", provider_response_id="resp-safe-id",
            provider_request_id="req-safe-id", provider_transport="openai-responses",
            provider_attempt_count=1,
            latency_ms=1, retry_count=0, state=ObservationState.FAILED,
            failure_code=failure_code,
        ),
    )

    class FailedClient:
        async def generate_structured(self, *_args, **_kwargs):
            raise error

        async def aclose(self):
            return None

    monkeypatch.setattr(extraction, "GenerationClient", lambda **_kwargs: FailedClient())
    with pytest.raises(extraction.StatblockExtractionError) as captured:
        asyncio.run(extraction.extract_statblock(["OCR text"], "Keep printed values."))

    expected = (
        "pdf_statblock_output_invalid"
        if failure_code is FailureCode.STRUCTURED_OUTPUT_INVALID
        else f"pdf_statblock_generation_{failure_code.value.lower()}"
    )
    assert captured.value.code == expected
    assert str(captured.value) == expected
    assert "private fixture diagnostic" not in str(captured.value)
    assert f"code={failure_code.value}" in caplog.text
    assert "provider=openai" in caplog.text
    assert "requested_model=gpt-6-luna" in caplog.text
    assert "response_model=gpt-6-luna-2026-10-01" in caplog.text
    assert "response_id=resp-safe-id" in caplog.text
    assert "request_id=req-safe-id" in caplog.text
    assert "provider_transport=openai-responses" in caplog.text
    assert "provider_attempt_count=1" in caplog.text
    assert "OCR text" not in caplog.text
    assert "Keep printed values." not in caplog.text


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
    from fastapi import HTTPException
    from application_state import pdf_statblock_review
    from apps.live_control_server.integrations.dungeonmind_statblocks.generated import StatblockDefinitionV1Input
    from apps.live_control_server.routes import agent
    from uuid import UUID

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

    review_id = "00000000-0000-4000-8000-000000000088"
    regions = [
        {"source_revision_id": "srev:one", "content_sha256": "a" * 64,
         "page": 1, "left": 0.0, "top": 0.0, "right": 0.5, "bottom": 1.0},
        {"source_revision_id": "srev:one", "content_sha256": "a" * 64,
         "page": 2, "left": 0.1, "top": 0.0, "right": 0.9, "bottom": 1.0},
    ]
    payload = {"regions": regions, "instruction": "Keep the printed names."}
    class Request:
        def __init__(self, authorization=None):
            self.headers = {} if authorization is None else {"authorization": authorization}

    with pytest.raises(HTTPException) as unauthorized:
        agent.post_extract_pdf_statblock_review("world-a", UUID(review_id), payload, Request())
    assert unauthorized.value.status_code == 401
    assert calls == []

    response = agent.post_extract_pdf_statblock_review(
        "world-a", UUID(review_id), payload, Request("Bearer fixture"),
    )
    assert response["revision"] == 1
    assert response["definition"] == candidate.model_dump(mode="json", by_alias=True)
    assert response["regions"] == [
        {"schema_version": "dm_native_pdf_region_v1", **region} for region in regions
    ]
    assert calls[:4] == [("open", 1), ("ocr", "dmVyaWZpZWQgY3JvcA=="),
                         ("open", 2), ("ocr", "dmVyaWZpZWQgY3JvcA==")]
    assert calls[4] == ("extract", ["OCR for region 2", "OCR for region 4"],
                        "Keep the printed names.")
    assert len(saved) == 1
    repeated = agent.post_extract_pdf_statblock_review(
        "world-a", UUID(review_id), payload, Request("Bearer fixture"),
    )
    assert repeated == response
    assert len([call for call in calls if call[0] == "extract"]) == 1


def test_incomplete_pdf_statblock_extraction_does_not_save(monkeypatch):
    from fastapi import HTTPException
    from application_state import pdf_statblock_review
    from apps.live_control_server.routes import agent
    from uuid import UUID

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

    class Request:
        headers = {"authorization": "Bearer fixture"}

    review_id = UUID("00000000-0000-4000-8000-000000000089")
    with pytest.raises(HTTPException) as response:
        agent.post_extract_pdf_statblock_review(
            "world-a", review_id, {"regions": [locator], "instruction": ""}, Request(),
        )
    assert response.value.status_code == 422
    assert response.value.detail == {
        "code": "pdf_statblock_extraction_incomplete", "missing_details": ["Hit Points", "ability scores"],
    }
    assert writes == []


@pytest.mark.parametrize("failure", ["invalid_region", "ocr", "model"])
def test_pdf_statblock_failures_never_save_a_review(monkeypatch, failure):
    from fastapi import HTTPException
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
                raise extraction.StatblockExtractionError("pdf_statblock_generation_provider_error")

            monkeypatch.setattr(extraction, "extract_statblock", reject_model)
            from src.llm import generation_sync
            monkeypatch.setattr(generation_sync, "run_awaitable_sync", lambda factory: asyncio.run(factory()))

    writes = []
    monkeypatch.setattr(pdf_statblock_review, "save_review", lambda **kwargs: writes.append(kwargs))
    monkeypatch.setattr(pdf_statblock_review, "read_review", lambda **kwargs: None)
    try:
        agent.post_extract_pdf_statblock_review(
            "world-a", "00000000-0000-4000-8000-000000000090",
            {"regions": [locator], "instruction": ""}, object(),
        )
    except HTTPException as response:
        status_code, detail = response.status_code, response.detail
    else:
        pytest.fail("expected the route to reject the failed PDF statblock request")

    assert status_code == (403 if failure == "invalid_region" else 503)
    assert writes == []
    assert calls == ({"invalid_region": ["region"], "ocr": ["ocr"], "model": ["model"]}[failure])
    if failure == "model":
        assert detail == {"code": "pdf_statblock_generation_provider_error"}
