"""Owner-scoped image generation, library and explicit public CDN save."""
from __future__ import annotations

import base64
import os
from typing import Literal
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from generationengine import GenerationClient, GenerationEngineError, ImageOptions, ImageRequest
from generationengine.providers.fal_provider import FalProvider
from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
from apps.live_control_server.services import media_storage
from application_state import media
from application_state.cli import assert_at_head
from application_state.errors import ApplicationStateError

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


def _fal_key() -> str:
    return os.environ.get("DUNGEONBUDDY_FAL_KEY", "").strip() or os.environ.get("FAL_KEY", "").strip()


def _image_client() -> GenerationClient:
    return GenerationClient(image_provider=FalProvider(api_key=_fal_key()))


@router.get("/capabilities")
def image_capabilities(request: Request, response: Response):
    enforce_native_graph_gm(request)
    response.headers["Cache-Control"] = "no-store"
    try:
        assert_at_head()
        library_ready = True
    except ApplicationStateError:
        library_ready = False
    return {"configured": bool(_fal_key()), "library_ready": library_ready,
            "storage_configured": media_storage.configured(), "models": [
        {"id": "flux-2-pro", "label": "FLUX 2 Pro", "formats": ["png", "jpeg"], "controls": ["seed"]},
        {"id": "gpt-image-1.5", "label": "GPT Image 1.5", "formats": ["png", "jpeg", "webp"], "controls": ["quality", "background"]},
    ]}


@router.post("/generate")
async def generate_image_preview(body: ImagePreviewRequest, request: Request, response: Response):
    principal = enforce_native_graph_gm(request)
    response.headers["Cache-Control"] = "no-store"
    if not _fal_key():
        raise HTTPException(503, detail="Image generation needs the server's fal credential.")
    try:
        assert_at_head()
    except ApplicationStateError as error:
        raise HTTPException(503, detail="The media library needs database setup before image generation.") from error
    client = None
    try:
        client = _image_client()
        result = await client.generate_image(ImageRequest(
            prompt=body.prompt, model=body.model, width=body.width, height=body.height,
            num_images=1, options=body.options, deadline_ms=180000,
        ))
    except GenerationEngineError as error:
        raise HTTPException(502, detail={"code": error.failure.code.value, "message": "Image generation did not complete. Your previous preview is unchanged."}) from error
    except (ValueError, ImportError) as error:
        raise HTTPException(503, detail="Image generation is not configured on this server.") from error
    finally:
        if client is not None:
            await client.aclose()
    if not result.images:
        raise HTTPException(502, detail="The model returned no image.")
    images = []
    for image in result.images:
        if image.media_type not in {"image/png", "image/jpeg", "image/webp"} or len(image.content) > 20 * 1024 * 1024:
            raise HTTPException(502, detail="The returned image could not be previewed.")
        try:
            row = media.stage_image(image.content, principal.subject, {
                "kind": "generation", "prompt": body.prompt, "model": body.model,
                "settings": body.model_dump(exclude={"prompt"}),
                "observation": result.observation.model_dump(mode="json"),
            })
        except ApplicationStateError as error:
            raise HTTPException(error.status_code, detail="The image could not be retained in the media library. No CDN save is claimed.") from error
        images.append({"data_url": f"data:{row['mime_type']};base64,{base64.b64encode(image.content).decode('ascii')}", "media_type": row["mime_type"], "asset_id": str(row["asset_id"]), "state": row["state"]})
    return {"images": images, "model": body.model, "prompt": body.prompt,
            "settings": body.model_dump(exclude={"prompt"}), "observation": result.observation.model_dump(mode="json")}


def _public_record(row: dict) -> dict:
    return {key: row[key] for key in ['asset_id', 'created_at', 'mime_type', 'width', 'height', 'byte_length', 'content_sha256', 'provenance', 'state']} | {
        'delivery_url': row['receipt']['delivery_url'] if row['state'] == 'ready' else None,
    }


@router.get('/library')
def image_library(request: Request, response: Response, before_time: datetime | None = None, before_id: UUID | None = None):
    principal = enforce_native_graph_gm(request)
    response.headers['Cache-Control'] = 'no-store'
    if (before_time is None) != (before_id is None):
        raise HTTPException(422, detail='Both media cursor fields are required.')
    try:
        rows = media.list_assets(principal.subject, before=(before_time, before_id) if before_time is not None else None)
        return {'items': [_public_record(row) for row in rows]}
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail='Media library is unavailable.') from error


@router.get('/{asset_id}')
def image_record(asset_id: UUID, request: Request, response: Response):
    principal = enforce_native_graph_gm(request)
    response.headers['Cache-Control'] = 'no-store'
    try:
        row = media.get_asset(asset_id, principal.subject)
        record = _public_record(row)
        # Original preview remains owner-authorized even before CDN Save.
        content = media.read_staged_bytes(asset_id, principal.subject)
        record['data_url'] = f"data:{row['mime_type']};base64,{base64.b64encode(content).decode('ascii')}"
        return record
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail='Media asset could not be opened.') from error


@router.post('/{asset_id}/save')
async def save_image(asset_id: UUID, request: Request, response: Response):
    principal = enforce_native_graph_gm(request)
    response.headers['Cache-Control'] = 'no-store'
    try:
        return _public_record(await media_storage.save_asset(asset_id, principal.subject))
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail=str(error)) from error
