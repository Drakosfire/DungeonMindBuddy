from __future__ import annotations

import json
import re
from pathlib import Path

from src.contracts.npc_registry import NpcRegistryRecord, load_npc_registry

from .schemas import EntityKind, RouteEquivalenceRecord

_CAMPAIGN_SEGMENT_RE = re.compile(r"/Longmont Campaign/Campaign (?P<num>\d+)/")
_KIND_SEGMENTS: list[tuple[str, EntityKind]] = [
    ("/npcs/", "npc"),
    ("/locations/", "location"),
    ("/factions/", "faction"),
    ("/institutions/", "institution"),
    ("/organizations/", "organization"),
]


def _slugify(text: str) -> str:
    value = text.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _normalize_campaign_id(registry_path: Path) -> str:
    text = str(registry_path).replace("\\", "/")
    m = _CAMPAIGN_SEGMENT_RE.search(f"/{text}")
    if not m:
        raise ValueError(f"unable to infer campaign id from registry path: {registry_path}")
    return f"longmont-c{int(m.group('num'))}"


def _is_campaign_path(path: str) -> bool:
    return "/Longmont Campaign/" in path.replace("\\", "/")


def _infer_entity_kind(path: str) -> EntityKind:
    lowered = f"/{path.replace('\\', '/').strip('/').lower()}/"
    for segment, kind in _KIND_SEGMENTS:
        if segment in lowered:
            return kind
    return "unknown"


def _path_to_route_id(path: str, campaign_id: str) -> tuple[str, EntityKind]:
    normalized = path.replace("\\", "/").strip("/")
    route_path = Path(normalized)
    slug = _slugify(route_path.parent.name)
    prefix = campaign_id if _is_campaign_path(normalized) else "elderwyld"
    entity_kind = _infer_entity_kind(normalized)
    return f"route:{prefix}:{entity_kind}:{slug}", entity_kind


def _record_to_edge(record: NpcRegistryRecord, campaign_id: str) -> RouteEquivalenceRecord | None:
    if not record.hub_path or not record.setting_hub_path:
        return None
    from_route_id, from_kind = _path_to_route_id(record.hub_path, campaign_id)
    to_route_id, to_kind = _path_to_route_id(record.setting_hub_path, campaign_id)
    entity_kind = from_kind if from_kind != "unknown" else to_kind
    return RouteEquivalenceRecord(
        record_id=f"route-eq:{campaign_id}:{entity_kind}:{record.slug}",
        campaign_id=campaign_id,
        entity_kind=entity_kind,
        display_name=record.display_name,
        from_route_id=from_route_id,
        to_route_id=to_route_id,
    )


def build_route_equivalence_manifest(registry_path: Path) -> list[RouteEquivalenceRecord]:
    campaign_id = _normalize_campaign_id(registry_path)
    records = load_npc_registry(registry_path)
    edges = [_record_to_edge(rec, campaign_id) for rec in records]
    return [edge for edge in edges if edge is not None]


def write_route_equivalence_manifest(records: list[RouteEquivalenceRecord], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for record in sorted(records, key=lambda r: r.record_id):
            f.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False) + "\n")
