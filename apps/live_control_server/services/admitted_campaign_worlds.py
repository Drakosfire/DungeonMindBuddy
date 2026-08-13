"""Admitted campaign→world overlay for non-Eldyrwild worlds (local seed).

Default product mapping remains longmont-c1/c2 → eldyrwild. Seeded worlds
(e.g. of-conks-cons) are recorded under ``out/registries/admitted_campaign_worlds.json``
and exposed to the UI so Build/Plan can resolve campaign→world without hardcoding.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from apps.live_control_server.config import repo_root
from src.live_play.live_store import load_json, write_json

DEFAULT_REGISTRY_REL = "out/registries/admitted_campaign_worlds.json"
REGISTRY_SCHEMA = "dmb_admitted_campaign_worlds_v1"


class AdmittedCampaignWorld(BaseModel):
    campaign_id: str
    world_id: str
    label: str | None = None
    source: Literal["seed", "operator"] = "seed"


class AdmittedCampaignWorldsDocument(BaseModel):
    schema_version: Literal["dmb_admitted_campaign_worlds_v1"] = REGISTRY_SCHEMA
    mappings: list[AdmittedCampaignWorld] = Field(default_factory=list)


def admitted_campaign_worlds_path(root: Path | None = None) -> Path:
    base = root if root is not None else repo_root()
    return base / DEFAULT_REGISTRY_REL


def load_admitted_campaign_worlds(
    root: Path | None = None,
) -> AdmittedCampaignWorldsDocument:
    path = admitted_campaign_worlds_path(root)
    if not path.is_file():
        return AdmittedCampaignWorldsDocument()
    raw = load_json(path)
    if not isinstance(raw, dict):
        return AdmittedCampaignWorldsDocument()
    return AdmittedCampaignWorldsDocument.model_validate(raw)


def upsert_admitted_campaign_world(
    *,
    campaign_id: str,
    world_id: str,
    label: str | None = None,
    source: Literal["seed", "operator"] = "seed",
    root: Path | None = None,
) -> AdmittedCampaignWorldsDocument:
    cleaned_campaign = campaign_id.strip()
    cleaned_world = world_id.strip()
    if not cleaned_campaign or not cleaned_world:
        raise ValueError("campaign_id and world_id are required")
    doc = load_admitted_campaign_worlds(root)
    remaining = [m for m in doc.mappings if m.campaign_id != cleaned_campaign]
    remaining.append(
        AdmittedCampaignWorld(
            campaign_id=cleaned_campaign,
            world_id=cleaned_world,
            label=label,
            source=source,
        )
    )
    remaining.sort(key=lambda m: m.campaign_id)
    updated = AdmittedCampaignWorldsDocument(mappings=remaining)
    path = admitted_campaign_worlds_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, updated.model_dump(mode="json"))
    return updated


def campaign_world_map(root: Path | None = None) -> dict[str, str]:
    return {
        item.campaign_id: item.world_id
        for item in load_admitted_campaign_worlds(root).mappings
    }
