"""Read and validate one MIND World/campaign ingestion observation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote, urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apps.live_control_server.services.managed_world_graph_projection import (
    resolve_managed_world_binding,
)


BASE_URL_ENV = "DUNGEONMIND_PUBLICATION_BASE_URL"
TOKEN_ENV = "DUNGEONMIND_PUBLICATION_BEARER_TOKEN"
CONTEXT_SCHEMA = "dm_world_campaign_ingest_context_v1"


class WorldCampaignIngestContextV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(pattern=r"^dm_world_campaign_ingest_context_v1$")
    world_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    membership: str = Field(pattern=r"^member$")
    head_revision_id: str = Field(min_length=1)
    graph_schema: str = Field(min_length=1)
    graph_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RecapIngestContextError(RuntimeError):
    def __init__(self, message: str, *, code: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class RecapContextSnapshot:
    schema: str
    managed_world_id: str
    native_world_id: str
    binding_version: int
    campaign_id: str
    head_revision_id: str
    graph_schema: str
    graph_payload_sha256: str

    def as_lineage(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "managed_world_id": self.managed_world_id,
            "native_world_id": self.native_world_id,
            "binding_version": self.binding_version,
            "campaign_id": self.campaign_id,
            "head_revision_id": self.head_revision_id,
            "graph_schema": self.graph_schema,
            "graph_payload_sha256": self.graph_payload_sha256,
        }


def read_recap_ingest_context(
    *, managed_world_id: str, campaign_id: str, client: httpx.Client | None = None
) -> RecapContextSnapshot:
    """Resolve the managed binding, then ask MIND to verify membership and head."""
    try:
        binding = resolve_managed_world_binding(managed_world_id)
    except Exception as exc:  # noqa: BLE001
        raise RecapIngestContextError(
            "Selected managed World has no verified active native Graph binding.",
            code="publication_target_unavailable",
            status_code=getattr(exc, "status_code", 409),
        ) from exc

    base_url = (os.environ.get(BASE_URL_ENV) or "").strip().rstrip("/")
    token = (os.environ.get(TOKEN_ENV) or "").strip()
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
        raise RecapIngestContextError(
            f"{BASE_URL_ENV} must be an HTTP(S) origin for the DungeonMind publication host.",
            code="ingest_context_not_configured",
        )
    if not token or any(ch.isspace() for ch in token):
        raise RecapIngestContextError(
            f"{TOKEN_ENV} is required for the DungeonMind publication host.",
            code="ingest_context_not_configured",
        )

    # quote IDs as single path segments; server contracts reject padded values.
    url = (
        f"{base_url}/v1/worlds/{quote(binding.native_world_id, safe='')}"
        f"/campaigns/{quote(campaign_id, safe='')}/ingest-context"
    )
    owns_client = client is None
    transport = client or httpx.Client(timeout=10.0, follow_redirects=False)
    try:
        response = transport.get(url, headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError as exc:
        raise RecapIngestContextError(
            "DungeonMind ingestion context could not be read.",
            code="ingest_context_unavailable",
            status_code=503,
        ) from exc
    finally:
        if owns_client:
            transport.close()

    if response.status_code != 200:
        try:
            payload = (
                response.json()
                if response.headers.get("content-type", "").startswith("application/json")
                else {}
            )
        except ValueError:
            payload = {}
        error = payload.get("error") if isinstance(payload, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        message = error.get("message") if isinstance(error, dict) else None
        status = response.status_code if response.status_code in {404, 409, 503} else 503
        raise RecapIngestContextError(
            str(message or "DungeonMind rejected the World/campaign ingestion context."),
            code=str(code or "ingest_context_unavailable"),
            status_code=status,
        )
    try:
        context = WorldCampaignIngestContextV1.model_validate(response.json())
    except (ValidationError, ValueError) as exc:
        raise RecapIngestContextError(
            "DungeonMind ingestion context response failed validation.",
            code="ingest_context_invalid",
            status_code=502,
        ) from exc
    if context.world_id != binding.native_world_id or context.campaign_id != campaign_id:
        raise RecapIngestContextError(
            "DungeonMind returned a different World/campaign ingestion context.",
            code="ingest_context_mismatch",
            status_code=502,
        )
    return RecapContextSnapshot(
        schema=context.schema_version,
        managed_world_id=binding.managed_world_id,
        native_world_id=binding.native_world_id,
        binding_version=binding.binding_version,
        campaign_id=context.campaign_id,
        head_revision_id=context.head_revision_id,
        graph_schema=context.graph_schema,
        graph_payload_sha256=context.graph_payload_sha256,
    )
