"""Owner-scoped image generation, library and explicit public CDN save."""
from __future__ import annotations

import base64
import os
from typing import Literal
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from generationengine import GenerationClient, GenerationEngineError, ImageOptions, ImageRequest
from generationengine.providers.fal_provider import FalProvider
from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
from apps.live_control_server.services import media_storage
from application_state import media
from application_state.build_proposal.images import BuildImageService
from application_state.cli import assert_at_head
from application_state.errors import ApplicationStateError

router = APIRouter(prefix="/api/live/media/images", tags=["media"])


# Buddy owns curation and exposed controls; GE owns provider discovery/execution.
IMAGE_MODELS = [
    {"id": "gpt-image-2.5-flare", "label": "GPT Image 2.5 Flare", "formats": ["png", "jpeg", "webp"], "controls": ["quality", "background"], "description": "Recommended starting point for general image generation."},
    {"id": "nano-banana-2-lite", "label": "Nano Banana 2 Lite", "formats": ["png", "jpeg", "webp"], "controls": ["seed"], "description": "Uses the selected aspect ratio and provider-default resolution."},
    {"id": "gpt-image-2.5-sunburst", "label": "GPT Image 2.5 Sunburst", "formats": ["png", "jpeg", "webp"], "controls": ["quality", "background"], "description": "Premium detail option; may take longer than Flare."},
    {"id": "seedream-v5-pro", "label": "Seedream V5 Pro", "formats": ["png", "jpeg"], "controls": [], "description": "Explicit image dimensions; PNG or JPEG output."},
    {"id": "flux-2-pro", "label": "FLUX 2 Pro", "formats": ["png", "jpeg"], "controls": ["seed"]},
    {"id": "gpt-image-1.5", "label": "GPT Image 1.5", "formats": ["png", "jpeg", "webp"], "controls": ["quality", "background"]},
]
DEFAULT_IMAGE_MODEL = "gpt-image-2.5-flare"
MAP_FRAMING = "Create a top-down, orthographic map of the described place, with readable spatial layout. Prioritize cartography over an atmospheric perspective illustration. Use the supplied features; treat unspecified placements as proposals, not established geography."


class ImagePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preparation_id: UUID | None = None
    prompt: str = Field(min_length=1, max_length=16000)
    purpose: Literal["illustration", "map"] = "illustration"
    model: Literal["flux-2-pro", "gpt-image-1.5", "gpt-image-2.5-flare", "gpt-image-2.5-sunburst", "nano-banana-2-lite", "seedream-v5-pro"]
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
        selected = next(item for item in IMAGE_MODELS if item["id"] == self.model)
        allowed = set(selected["controls"]) | {"output_format"}
        if explicit - allowed or (self.options.output_format is not None and self.options.output_format not in selected["formats"]):
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
            "storage_configured": media_storage.configured(), "models": IMAGE_MODELS[:4],
            "default_model_id": DEFAULT_IMAGE_MODEL, "map_framing": MAP_FRAMING}


@router.get("/catalog")
async def image_model_catalog(
    request: Request, response: Response,
    cursor: str | None = Query(default=None, max_length=4096),
    limit: int = Query(default=100, ge=1, le=100),
):
    """Explicit provider discovery; never inference, storage or document writes."""
    enforce_native_graph_gm(request)
    response.headers["Cache-Control"] = "no-store"
    if not _fal_key():
        raise HTTPException(503, detail="The model catalog needs the server's fal credential.")
    client = None
    try:
        client = _image_client()
        page = await client.list_image_models(category="text-to-image", cursor=cursor, limit=limit)
    except GenerationEngineError as error:
        raise HTTPException(502, detail={"code": error.failure.code.value, "message": "The fal model catalog is unavailable. Your model selection is unchanged."}) from error
    except (ValueError, ImportError) as error:
        raise HTTPException(503, detail="Model discovery is not configured on this server.") from error
    finally:
        if client is not None:
            await client.aclose()
    selectable = {item["id"] for item in IMAGE_MODELS[:4]}
    result = page.model_dump(mode="json")
    for item in result["models"]:
        item["selectable"] = item["executable_model"] in selectable
    return result



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
    preparation = None
    if body.preparation_id is not None:
        try:
            preparation = BuildImageService().get(body.preparation_id, principal.subject)
        except ApplicationStateError as error:
            raise HTTPException(error.status_code, detail='Image preparation unavailable.') from error
    effective_prompt = MAP_FRAMING + "\n\n" + body.prompt if body.purpose == "map" else body.prompt
    client = None
    try:
        client = _image_client()
        result = await client.generate_image(ImageRequest(
            prompt=effective_prompt, model=body.model, width=body.width, height=body.height,
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
                "kind": "generation", "prompt": effective_prompt, "authored_prompt": body.prompt, "model": body.model,
                "settings": body.model_dump(exclude={"prompt"}),
                "observation": result.observation.model_dump(mode="json"),
                "preparation": preparation.model_dump(mode="json", exclude={'owner_id'}) if preparation else None,
            })
        except ApplicationStateError as error:
            raise HTTPException(error.status_code, detail="The image could not be retained in the media library. No CDN save is claimed.") from error
        images.append({"data_url": f"data:{row['mime_type']};base64,{base64.b64encode(image.content).decode('ascii')}", "media_type": row["mime_type"], "asset_id": str(row["asset_id"]), "state": row["state"]})
    return {"images": images, "model": body.model, "prompt": effective_prompt,
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


def _preparation_record(record):
    return record.model_dump(mode='json', exclude={'owner_id'})


@router.get('/preparations/list')
def image_preparations(request: Request, response: Response, world_id: str, conversation_id: UUID):
    principal = enforce_native_graph_gm(request)
    response.headers['Cache-Control'] = 'no-store'
    try:
        return {'items': [_preparation_record(record) for record in BuildImageService().list(world_id, conversation_id, principal.subject)]}
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail='Image preparations unavailable.') from error


@router.get('/preparations/{action_id}')
def image_preparation(action_id: UUID, request: Request, response: Response):
    principal = enforce_native_graph_gm(request)
    response.headers['Cache-Control'] = 'no-store'
    try:
        return _preparation_record(BuildImageService().get(action_id, principal.subject))
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail='Image preparation unavailable.') from error


class ImageAssociationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    asset_id: UUID
    expected_revision: int = Field(strict=True, ge=1)


@router.post('/preparations/{action_id}/asset')
def associate_image(action_id: UUID, body: ImageAssociationRequest, request: Request, response: Response):
    principal = enforce_native_graph_gm(request)
    response.headers['Cache-Control'] = 'no-store'
    try:
        preparation = BuildImageService().get(action_id, principal.subject)
        from apps.live_control_server.services.build_document_proposal import _source
        _source(preparation.reservation)
        return _preparation_record(BuildImageService().associate(action_id, body.asset_id, principal.subject, body.expected_revision))
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail=str(error)) from error


@router.get('/{asset_id}/metadata')
def image_metadata(asset_id: UUID, request: Request, response: Response):
    principal = enforce_native_graph_gm(request)
    response.headers['Cache-Control'] = 'no-store'
    try:
        return _public_record(media.get_asset(asset_id, principal.subject))
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail='Media asset unavailable.') from error


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
