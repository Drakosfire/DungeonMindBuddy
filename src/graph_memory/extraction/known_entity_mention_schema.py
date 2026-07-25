"""Sidecar schema for deterministic known-entity mentions (PC / companion).

Mentions are keyed to existing ``source_span_ref_id`` values. Surface text and
offsets refer to the *exact* span text — they never rewrite recap prose.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

KNOWN_ENTITY_MENTION_SIDECAR_SCHEMA = "dmb_known_entity_mention_sidecar_v0"
KNOWN_ENTITY_MENTION_SIDECAR_VERSION = "0.1"
KNOWN_ENTITY_ALLOWED_KINDS = frozenset({"pc", "companion"})
KNOWN_ENTITY_ALLOWED_MATCH_METHODS = frozenset({"canonical", "alias"})


@dataclass(frozen=True)
class KnownEntityMention:
    source_span_ref_id: str
    start_offset: int
    end_offset: int
    surface_text: str
    canonical_entity_id: str
    entity_slug: str
    entity_kind: str  # "pc" | "companion"
    match_method: str  # "canonical" | "alias"
    display_name: str
    registry_version: str = KNOWN_ENTITY_MENTION_SIDECAR_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> KnownEntityMention:
        source_span_ref_id = str(raw["source_span_ref_id"]).strip()
        if not source_span_ref_id:
            raise ValueError("source_span_ref_id is required")
        start_offset = int(raw["start_offset"])
        end_offset = int(raw["end_offset"])
        if start_offset < 0 or end_offset < 0:
            raise ValueError("mention offsets must be nonnegative")
        if start_offset >= end_offset:
            raise ValueError("start_offset must be less than end_offset")
        surface_text = str(raw["surface_text"])
        if not surface_text:
            raise ValueError("surface_text is required")
        canonical_entity_id = str(raw["canonical_entity_id"]).strip()
        entity_slug = str(raw["entity_slug"]).strip()
        if not canonical_entity_id:
            raise ValueError("canonical_entity_id is required")
        if not entity_slug:
            raise ValueError("entity_slug is required")
        entity_kind = str(raw["entity_kind"]).strip()
        match_method = str(raw["match_method"]).strip()
        if entity_kind not in KNOWN_ENTITY_ALLOWED_KINDS:
            raise ValueError(
                f"entity_kind must be one of {sorted(KNOWN_ENTITY_ALLOWED_KINDS)}"
            )
        if match_method not in KNOWN_ENTITY_ALLOWED_MATCH_METHODS:
            raise ValueError(
                "match_method must be one of "
                f"{sorted(KNOWN_ENTITY_ALLOWED_MATCH_METHODS)}"
            )
        display_name = str(raw.get("display_name") or entity_slug).strip()
        if not display_name:
            raise ValueError("display_name is required")
        return cls(
            source_span_ref_id=source_span_ref_id,
            start_offset=start_offset,
            end_offset=end_offset,
            surface_text=surface_text,
            canonical_entity_id=canonical_entity_id,
            entity_slug=entity_slug,
            entity_kind=entity_kind,
            match_method=match_method,
            display_name=display_name,
            registry_version=str(
                raw.get("registry_version") or KNOWN_ENTITY_MENTION_SIDECAR_VERSION
            ),
        )


@dataclass(frozen=True)
class KnownEntityMentionSidecar:
    schema: str = KNOWN_ENTITY_MENTION_SIDECAR_SCHEMA
    version: str = KNOWN_ENTITY_MENTION_SIDECAR_VERSION
    campaign_id: str = ""
    session_id: str = ""
    registry_relpath: str | None = None
    roster_session_key: str | None = None
    roster_carry_forward: bool = False
    mentions: tuple[KnownEntityMention, ...] = ()
    ambiguous_surfaces: tuple[str, ...] = ()
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "campaign_id": self.campaign_id,
            "session_id": self.session_id,
            "registry_relpath": self.registry_relpath,
            "roster_session_key": self.roster_session_key,
            "roster_carry_forward": self.roster_carry_forward,
            "mentions": [m.to_dict() for m in self.mentions],
            "ambiguous_surfaces": list(self.ambiguous_surfaces),
            "diagnostics": dict(self.diagnostics),
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> KnownEntityMentionSidecar:
        mentions_raw = raw.get("mentions") or []
        if not isinstance(mentions_raw, list):
            raise ValueError("mentions must be a list")
        mentions: list[KnownEntityMention] = []
        for index, item in enumerate(mentions_raw):
            if not isinstance(item, Mapping):
                raise ValueError(f"mentions[{index}] must be an object")
            mentions.append(KnownEntityMention.from_mapping(item))
        ambiguous_raw = raw.get("ambiguous_surfaces") or []
        if not isinstance(ambiguous_raw, list):
            raise ValueError("ambiguous_surfaces must be a list")
        ambiguous: list[str] = []
        for index, surface in enumerate(ambiguous_raw):
            if not isinstance(surface, str):
                raise ValueError(f"ambiguous_surfaces[{index}] must be a string")
            if surface.strip():
                ambiguous.append(surface)
        return cls(
            schema=str(raw.get("schema") or KNOWN_ENTITY_MENTION_SIDECAR_SCHEMA),
            version=str(raw.get("version") or KNOWN_ENTITY_MENTION_SIDECAR_VERSION),
            campaign_id=str(raw.get("campaign_id") or ""),
            session_id=str(raw.get("session_id") or ""),
            registry_relpath=(
                str(raw["registry_relpath"])
                if raw.get("registry_relpath") is not None
                else None
            ),
            roster_session_key=(
                str(raw["roster_session_key"])
                if raw.get("roster_session_key") is not None
                else None
            ),
            roster_carry_forward=bool(raw.get("roster_carry_forward")),
            mentions=tuple(mentions),
            ambiguous_surfaces=tuple(ambiguous),
            diagnostics=dict(raw.get("diagnostics") or {}),
        )


def mentions_by_span(
    mentions: Sequence[KnownEntityMention],
) -> dict[str, list[KnownEntityMention]]:
    grouped: dict[str, list[KnownEntityMention]] = {}
    for mention in mentions:
        grouped.setdefault(mention.source_span_ref_id, []).append(mention)
    for items in grouped.values():
        items.sort(key=lambda item: (item.start_offset, -item.end_offset))
    return grouped


def known_entity_ids(mentions: Sequence[KnownEntityMention]) -> set[str]:
    return {m.canonical_entity_id for m in mentions}


def known_entity_slugs(mentions: Sequence[KnownEntityMention]) -> set[str]:
    return {m.entity_slug for m in mentions}
