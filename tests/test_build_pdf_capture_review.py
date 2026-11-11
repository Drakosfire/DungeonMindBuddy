import asyncio
import json

import httpx
import pytest
from generationengine import GenerationEngineError

from apps.live_control_server.services import build_pdf_capture_review as review


@pytest.mark.parametrize("instruction", ["Only extract AC.", ""])
def test_capture_review_sends_exact_crop_and_instruction(monkeypatch, instruction):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(review, "_model", lambda: "gpt-6-luna")
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(400, json={"error": {"message": "fixture stop"}})

    with pytest.raises(GenerationEngineError):
        asyncio.run(review.review_capture(
            b"fixture", instruction, transport=httpx.MockTransport(handle),
        ))

    assert len(requests) == 1
    body = requests[0]
    assert body["input"] == [{
        "role": "user",
        "content": [
            {"type": "input_text", "text": instruction or
             "Extract the visible content and preserve its structure."},
            {"type": "input_image", "image_url": "data:image/png;base64,Zml4dHVyZQ==",
             "detail": "high"},
        ],
    }]
    assert body["instructions"] == review.INSTRUCTIONS
    assert not body.get("tools")
