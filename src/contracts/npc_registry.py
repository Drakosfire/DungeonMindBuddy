"""Pydantic mirror + loader for the per-campaign NPC registry artifact.

The registry is the canonical "known NPCs in this campaign" surface. It lives
at ``<campaign>/_npc_registry.json`` (e.g.
``corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_npc_registry.json``)
and is consumed by Stage C (NPC candidate identification) and Stage D (entity
resolution) so they don't have to re-derive the list from the filesystem on
every run.

Distinct from :class:`src.store.FactStore.entities`, which carries per-run
extraction provenance — the registry is GM-curated campaign canon.

Schema: ``schemas/v0.1/npc_registry.schema.json``.
Lint: ``scripts/lint_npc_registry.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


NpcRegistryStatus = Literal["tracked", "background", "dormant", "candidate"]


class NpcRegistryRecord(BaseModel):
    """One record in a campaign's NPC registry."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    status: NpcRegistryStatus
    first_session: int = Field(ge=0)
    last_session: int = Field(ge=0)
    hub_path: Optional[str] = None
    setting_hub_path: Optional[str] = None
    notes: str = ""

    @model_validator(mode="after")
    def _check_session_bounds(self) -> "NpcRegistryRecord":
        if self.first_session > self.last_session:
            raise ValueError(
                f"first_session ({self.first_session}) > last_session "
                f"({self.last_session}) for slug={self.slug!r}"
            )
        return self

    @model_validator(mode="after")
    def _check_hub_path_for_status(self) -> "NpcRegistryRecord":
        # tracked / background / dormant must point at an existing hub.
        # Only candidate may have a null hub_path (not yet curated).
        if self.status != "candidate" and self.hub_path is None:
            raise ValueError(
                f"hub_path may only be null when status='candidate' "
                f"(slug={self.slug!r}, status={self.status!r})"
            )
        return self

    @model_validator(mode="after")
    def _check_hub_path_separation(self) -> "NpcRegistryRecord":
        hub = (self.hub_path or "").strip()
        setting = (self.setting_hub_path or "").strip()
        if hub and setting and hub.rstrip("/") == setting.rstrip("/"):
            raise ValueError(
                f"hub_path and setting_hub_path must not be identical (slug={self.slug!r})"
            )
        return self


def load_npc_registry(path: Path) -> list[NpcRegistryRecord]:
    """Load a registry JSON file from disk and return the parsed records.

    Parameters
    ----------
    path:
        Path to a registry JSON file (typically
        ``<campaign>/_npc_registry.json``).

    Returns
    -------
    list[NpcRegistryRecord]
        Parsed and validated records, preserving file order.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If the file does not parse as JSON, the top-level value is not an
        array, or any record fails Pydantic validation.
    """
    raw_text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON ({exc})") from exc

    if not isinstance(data, list):
        raise ValueError(
            f"{path}: top-level value must be a JSON array, got {type(data).__name__}"
        )

    records: list[NpcRegistryRecord] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(
                f"{path}: record[{index}] must be a JSON object, got {type(item).__name__}"
            )
        records.append(NpcRegistryRecord.model_validate(item))
    return records


def dump_npc_registry(records: list[NpcRegistryRecord]) -> str:
    """Serialize records back to the canonical on-disk JSON shape.

    Sorted by slug for diff stability; 2-space indentation; trailing newline.
    """
    payload = [r.model_dump(mode="json") for r in sorted(records, key=lambda r: r.slug)]
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
