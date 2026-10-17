"""Prompt-only media previews. No document, Graph or asset publication writes."""
from __future__ import annotations

import base64
import os
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from generationengine import GenerationClient, GenerationEngineError, ImageOptions, ImageRequest
from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm

router = APIRouter(prefix="/api/live/media/images", tags=["media"])


class ImagePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=16000)
    model: Literal["flux-2-pro", "gpt-image-1.5"]
    width: Literal[1024, 1536] = 1024
    height: Literal[1024, 1536] = 1024
    options: ImageOptions = Field(default_factory=ImageOptions)

    @model_validator(mode="after")
    def supported_settings(self):
        if not self.prompt.strip():
            raise ValueError("Write an image prompt first.")
        if (self.width, self.height) not in {(1024, 1024), (1536, 1024), (1024, 1536)}:
            raise ValueError("Choose square, landscape or portrait.")
        explicit = set(self.options.model_dump(exclude_none=True))
        allowed = {"quality", "background", "output_format"} if self.model == "gpt-image-1.5" else {"seed", "output_format"}
        if explicit - allowed or (self.model == "flux-2-pro" and self.options.output_format == "webp"):
            raise ValueError("These settings are not supported by the selected model.")
        return self


@router.get("/capabilities")
def image_capabilities(request: Request, response: Response):
    enforce_native_graph_gm(request)
    response.headers["Cache-Control"] = "no-store"
    return {"configured": bool(os.environ.get("FAL_KEY")), "models": [
        {"id": "flux-2-pro", "label": "FLUX 2 Pro", "formats": ["png", "jpeg"], "controls": ["seed"]},
        {"id": "gpt-image-1.5", "label": "GPT Image 1.5", "formats": ["png", "jpeg", "webp"], "controls": ["quality", "background"]},
    ]}


@router.post("/generate")
async def generate_image_preview(body: ImagePreviewRequest, request: Request, response: Response):
    enforce_native_graph_gm(request)
    response.headers["Cache-Control"] = "no-store"
    if not os.environ.get("FAL_KEY"):
        raise HTTPException(503, detail="Image generation needs the server's fal credential.")
    client = GenerationClient.from_env()
    try:
        result = await client.generate_image(ImageRequest(
            prompt=body.prompt, model=body.model, width=body.width, height=body.height,
            num_images=1, options=body.options, deadline_ms=180000,
        ))
    except GenerationEngineError as error:
        raise HTTPException(502, detail={"code": error.failure.code.value, "message": "Image generation did not complete. Your previous preview is unchanged."}) from error
    except (ValueError, ImportError) as error:
        raise HTTPException(503, detail="Image generation is not configured on this server.") from error
    finally:
        await client.aclose()
    if not result.images:
        raise HTTPException(502, detail="The model returned no image.")
    images = []
    for image in result.images:
        if image.media_type not in {"image/png", "image/jpeg", "image/webp"} or len(image.content) > 20 * 1024 * 1024:
            raise HTTPException(502, detail="The returned image could not be previewed.")
        images.append({"data_url": f"data:{image.media_type};base64,{base64.b64encode(image.content).decode('ascii')}", "media_type": image.media_type})
    return {"images": images, "model": body.model, "prompt": body.prompt,
            "settings": body.model_dump(exclude={"prompt"}), "observation": result.observation.model_dump(mode="json")}
