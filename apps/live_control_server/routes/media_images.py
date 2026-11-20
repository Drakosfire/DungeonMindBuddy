"""Owner-scoped image generation, library and explicit public CDN save."""
from __future__ import annotations

import base64
import os
from typing import Literal
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from generationengine import FailureCode, GenerationClient, GenerationEngineError, ImageOptions, ImageRequest
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
def image_capabilities(request: Request, response: Response, world_id: str | None = None):
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    if world_id is None:
        enforce_native_graph_gm(request)
    else:
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
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
    world_id: str | None = None,
):
    """Explicit provider discovery; never inference, storage or document writes."""
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    if world_id is None:
        enforce_native_graph_gm(request)
    else:
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
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
    if world_id is not None:
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    return result



def _image_failure_message(error: GenerationEngineError, unavailable: str) -> str:
    if error.failure.code is FailureCode.PROVIDER_REFUSED:
        return "The image provider declined this request under its content policy. Edit the prompt before trying again. Your existing images are unchanged."
    return unavailable


@router.post("/generate")
async def generate_image_preview(
    body: ImagePreviewRequest, request: Request, response: Response, world_id: str | None = None,
):
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import (
        conversation_graph_principal, hosted_world_media_owner, require_conversation_access,
    )

    hosted = hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT
    if hosted:
        if world_id is None:
            raise HTTPException(403, detail="Select a World before generating artwork.")
        principal = conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
        asset_owner = hosted_world_media_owner(world_id)
    else:
        principal = enforce_native_graph_gm(request)
        asset_owner = principal.subject
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
            if world_id is not None and preparation.reservation.basis.world_id != world_id:
                raise HTTPException(404, detail="Image preparation unavailable.")
        except ApplicationStateError as error:
            raise HTTPException(error.status_code, detail='Image preparation unavailable.') from error
    effective_prompt = MAP_FRAMING + "\n\n" + body.prompt if body.purpose == "map" else body.prompt
    client = None
    try:
        client = _image_client()
        if hosted and world_id is not None:
            require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
        result = await client.generate_image(ImageRequest(
            prompt=effective_prompt, model=body.model, width=body.width, height=body.height,
            num_images=1, options=body.options, deadline_ms=180000,
        ))
    except GenerationEngineError as error:
        raise HTTPException(502, detail={"code": error.failure.code.value, "message": _image_failure_message(error, "Image generation did not complete. Your previous preview is unchanged.")}) from error
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
        if hosted and world_id is not None:
            require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
        try:
            row = media.stage_image(image.content, asset_owner, {
                "kind": "generation", "prompt": effective_prompt, "authored_prompt": body.prompt, "model": body.model,
                "settings": body.model_dump(mode="json", exclude={"prompt"}),
                "observation": result.observation.model_dump(mode="json"),
                "preparation": preparation.model_dump(mode="json", exclude={'owner_id'}) if preparation else None,
            })
        except ApplicationStateError as error:
            raise HTTPException(error.status_code, detail="The image could not be retained in the media library. No CDN save is claimed.") from error
        images.append({"data_url": f"data:{row['mime_type']};base64,{base64.b64encode(image.content).decode('ascii')}", "media_type": row["mime_type"], "asset_id": str(row["asset_id"]), "state": row["state"]})
    return {"images": images, "model": body.model, "prompt": effective_prompt,
            "settings": body.model_dump(mode="json", exclude={"prompt"}), "observation": result.observation.model_dump(mode="json")}


class ContextualImageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["image_to_image", "new"]
    instructions: str = Field(min_length=1, max_length=16000)
    expected_content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def nonempty_instructions(self):
        if not self.instructions.strip():
            raise ValueError("Write image instructions first.")
        return self


@router.post('/{asset_id}/regenerate')
async def regenerate_image(asset_id: UUID, body: ContextualImageRequest, request: Request, response: Response):
    """Retain a new candidate; never mutate the source or its occurrences."""
    from apps.live_control_server.services import hosted_auth

    owner = _saved_artwork_owner(request, asset_id)
    hosted = hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT
    response.headers['Cache-Control'] = 'no-store'
    try:
        assert_at_head()
        parent = media.get_asset(asset_id, owner)
        if parent['state'] not in {'staged', 'ready'} or parent['content_sha256'] != body.expected_content_sha256:
            raise HTTPException(409, detail="The image changed or is not ready. Reopen its edit menu.")
        original = media.read_staged_bytes(asset_id, owner)
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail="The original image is unavailable or failed integrity verification.") from error
    if not _fal_key():
        raise HTTPException(503, detail="Image generation needs the server's fal credential.")
    model = 'flux-2-pro' if body.mode == 'image_to_image' else DEFAULT_IMAGE_MODEL
    source = f"data:{parent['mime_type']};base64,{base64.b64encode(original).decode('ascii')}" if body.mode == 'image_to_image' else None
    client = None
    try:
        client = _image_client()
        image_request = ImageRequest(prompt=body.instructions, model=model,
            width=parent['width'], height=parent['height'], num_images=1,
            base_image_base64=source, deadline_ms=180000)
        if hosted and _saved_artwork_owner(request, asset_id) != owner:
            raise HTTPException(403, detail="Image access denied.")
        result = await (client.edit_image(image_request) if body.mode == 'image_to_image' else client.generate_image(image_request))
    except GenerationEngineError as error:
        raise HTTPException(502, detail={"code": error.failure.code.value,
            "message": _image_failure_message(error, "Generation could not be confirmed. Your original is unchanged; check the library before trying again.")}) from error
    except (ValueError, ImportError) as error:
        raise HTTPException(503, detail="Image generation is unavailable. Your original is unchanged.") from error
    finally:
        if client is not None:
            await client.aclose()
    if len(result.images) != 1:
        raise HTTPException(502, detail="A single image result could not be confirmed. Your original is unchanged.")
    image = result.images[0]
    if image.media_type not in {'image/png', 'image/jpeg', 'image/webp'} or len(image.content) > 20 * 1024 * 1024:
        raise HTTPException(502, detail="The generated image could not be retained. Your original is unchanged.")
    if hosted and _saved_artwork_owner(request, asset_id) != owner:
        raise HTTPException(403, detail="Image access denied.")
    try:
        child = media.stage_image(image.content, owner, {
            'kind': 'contextual_image_generation_v1', 'parent_asset_id': str(asset_id),
            'parent_content_sha256': parent['content_sha256'], 'mode': body.mode,
            'instructions': body.instructions, 'prompt': body.instructions, 'authored_prompt': body.instructions,
            'model': model, 'observation': result.observation.model_dump(mode='json'),
        })
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail="Generated-image retention could not be confirmed. Your original is unchanged; check the library before trying again.") from error
    return {'asset_id': str(child['asset_id']), 'state': child['state'], 'model': model, 'parent_asset_id': str(asset_id)}


def _public_record(row: dict) -> dict:
    return {key: row[key] for key in ['asset_id', 'created_at', 'mime_type', 'width', 'height', 'byte_length', 'content_sha256', 'provenance', 'state']} | {
        'delivery_url': row['receipt']['delivery_url'] if row['state'] == 'ready' else None,
    }


@router.get('/library')
def image_library(request: Request, response: Response, before_time: datetime | None = None, before_id: UUID | None = None, world_id: str | None = None):
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import (
        hosted_world_media_owner, require_hosted_plan_world_context,
    )

    if hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT:
        require_hosted_plan_world_context(request, world_id)
        owner = hosted_world_media_owner(world_id)
    else:
        owner = enforce_native_graph_gm(request).subject
    response.headers['Cache-Control'] = 'no-store'
    if (before_time is None) != (before_id is None):
        raise HTTPException(422, detail='Both media cursor fields are required.')
    try:
        rows = media.list_assets(owner, before=(before_time, before_id) if before_time is not None else None)
        result = {'items': [_public_record(row) for row in rows]}
        if hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT:
            require_hosted_plan_world_context(request, world_id)
        return result
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail='Media library is unavailable.') from error


def _preparation_record(record):
    return record.model_dump(mode='json', exclude={'owner_id'})


@router.get('/preparations/list')
def image_preparations(request: Request, response: Response, world_id: str, conversation_id: UUID):
    from apps.live_control_server.services.hosted_native_graph_access import conversation_graph_principal

    principal = conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
    response.headers['Cache-Control'] = 'no-store'
    try:
        return {'items': [_preparation_record(record) for record in BuildImageService().list(world_id, conversation_id, principal.subject)]}
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail='Image preparations unavailable.') from error


@router.get('/preparations/{action_id}')
def image_preparation(action_id: UUID, request: Request, response: Response, world_id: str | None = None):
    from apps.live_control_server.services.hosted_native_graph_access import conversation_graph_principal

    principal = (
        conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
        if world_id is not None else enforce_native_graph_gm(request)
    )
    response.headers['Cache-Control'] = 'no-store'
    try:
        record = BuildImageService().get(action_id, principal.subject)
        if world_id is not None and record.reservation.basis.world_id != world_id:
            raise HTTPException(404, detail='Image preparation unavailable.')
        result = _preparation_record(record)
        if world_id is not None:
            conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
        return result
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail='Image preparation unavailable.') from error


class ImageAssociationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    asset_id: UUID
    expected_revision: int = Field(strict=True, ge=1)


@router.post('/preparations/{action_id}/asset')
def associate_image(
    action_id: UUID, body: ImageAssociationRequest, request: Request, response: Response,
    world_id: str | None = None,
):
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import (
        conversation_graph_principal, hosted_world_media_owner, require_conversation_access,
    )

    hosted = hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT
    if hosted and world_id is None:
        raise HTTPException(403, detail="Select a World before placing artwork.")
    principal = (
        conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
        if world_id is not None else enforce_native_graph_gm(request)
    )
    def authorize_world(bound_world_id: str) -> None:
        require_conversation_access(request, bound_world_id, authorize_local=enforce_native_graph_gm)

    response.headers['Cache-Control'] = 'no-store'
    try:
        service = BuildImageService()
        preparation = service.get(action_id, principal.subject)
        if world_id is not None and preparation.reservation.basis.world_id != world_id:
            raise HTTPException(404, detail="Image preparation unavailable.")
        from apps.live_control_server.services.build_document_proposal import _source
        _source(preparation.reservation)
        return _preparation_record(service.associate(
            action_id, body.asset_id, principal.subject, body.expected_revision,
            asset_owner=hosted_world_media_owner(world_id) if hosted else None,
            authorize_world=authorize_world if hosted else None,
        ))
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail=str(error)) from error


def _saved_artwork_owner(request: Request, asset_id: UUID) -> str:
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import require_hosted_saved_artwork

    if hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT:
        return require_hosted_saved_artwork(request, asset_id)
    return enforce_native_graph_gm(request).subject


@router.get('/{asset_id}/metadata')
def image_metadata(asset_id: UUID, request: Request, response: Response):
    owner = _saved_artwork_owner(request, asset_id)
    response.headers['Cache-Control'] = 'no-store'
    try:
        return _public_record(media.get_asset(asset_id, owner))
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail='Media asset unavailable.') from error


@router.get('/{asset_id}/original', response_class=Response)
def image_original(asset_id: UUID, request: Request) -> Response:
    owner = _saved_artwork_owner(request, asset_id)
    try:
        row = media.get_asset(asset_id, owner)
        content = media.read_staged_bytes(asset_id, owner)
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail='Media asset could not be opened.') from error
    return Response(
        content,
        media_type=row['mime_type'],
        headers={
            'Cache-Control': 'no-store',
            'X-Content-Type-Options': 'nosniff',
            'X-Media-Content-SHA256': row['content_sha256'],
        },
    )


@router.get('/{asset_id}')
def image_record(asset_id: UUID, request: Request, response: Response):
    owner = _saved_artwork_owner(request, asset_id)
    response.headers['Cache-Control'] = 'no-store'
    try:
        row = media.get_asset(asset_id, owner)
        record = _public_record(row)
        # Original preview remains owner-authorized even before CDN Save.
        content = media.read_staged_bytes(asset_id, owner)
        record['data_url'] = f"data:{row['mime_type']};base64,{base64.b64encode(content).decode('ascii')}"
        if _saved_artwork_owner(request, asset_id) != owner:
            raise HTTPException(403, detail="Image access denied.")
        return record
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail='Media asset could not be opened.') from error


@router.post('/{asset_id}/save')
async def save_image(asset_id: UUID, request: Request, response: Response):
    owner = _saved_artwork_owner(request, asset_id)
    response.headers['Cache-Control'] = 'no-store'
    from apps.live_control_server.services import hosted_auth

    def authorize_write() -> None:
        if _saved_artwork_owner(request, asset_id) != owner:
            raise HTTPException(403, detail="Image access denied.")

    try:
        if hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT:
            return _public_record(await media_storage.save_asset(asset_id, owner, authorize_write=authorize_write))
        return _public_record(await media_storage.save_asset(asset_id, owner))
    except ApplicationStateError as error:
        raise HTTPException(error.status_code, detail=str(error)) from error
