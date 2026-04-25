"""Stage B: hub manifest + strict ``sentence_hub_routes_v1`` envelope (Pydantic).

Spec: ``Docs/Plans/DESIGN-Sentence-Routing-Stage-B-Hub-Routing.md`` §3–4.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_SENTENCE_HUB_ROUTES_V1 = "sentence_hub_routes_v1"

_SUBJECT_CLASSES = frozenset(
    {
        "npc",
        "pc",
        "location",
        "faction",
        "session",
        "campaign",
        "item",
        "event",
        "world",
    }
)
_SLUG_RE = re.compile(r"^[a-z0-9_]+$")

_CONFIDENCE = frozenset({"high", "medium", "low"})


class HubManifestEntry(BaseModel):
    slug: str
    path: str
    subject_class: str
    campaign_id: str | None = None
    label: str | None = None

    @field_validator("slug")
    @classmethod
    def slug_shape(cls, v: str) -> str:
        s = str(v).strip()
        if not _SLUG_RE.match(s):
            raise ValueError(f"slug must match ^[a-z0-9_]+$: {s!r}")
        return s

    @field_validator("subject_class")
    @classmethod
    def subject_ok(cls, v: str) -> str:
        s = str(v).strip()
        if s not in _SUBJECT_CLASSES:
            raise ValueError(f"invalid subject_class {s!r}; expected one of {sorted(_SUBJECT_CLASSES)}")
        return s


class RouteRow(BaseModel):
    unit_id: str
    assigned_hubs: list[str] = Field(default_factory=list)
    confidence: str
    rationale: str
    needs_new_hub_candidate: bool

    @field_validator("assigned_hubs")
    @classmethod
    def unique_hubs(cls, hubs: list[str]) -> list[str]:
        out = [str(h).strip() for h in hubs if str(h).strip()]
        if len(out) != len(set(out)):
            raise ValueError("assigned_hubs must not contain duplicate slugs")
        return out

    @field_validator("confidence")
    @classmethod
    def confidence_ok(cls, v: str) -> str:
        s = str(v).strip().lower()
        if s not in _CONFIDENCE:
            raise ValueError(f"confidence must be one of {sorted(_CONFIDENCE)}")
        return s

    @model_validator(mode="after")
    def hub_vs_candidate(self) -> RouteRow:
        if self.needs_new_hub_candidate and self.assigned_hubs:
            raise ValueError("needs_new_hub_candidate true requires empty assigned_hubs")
        return self


class RoutesEnvelope(BaseModel):
    """Wire JSON uses the key ``schema`` (alias); Python field avoids shadowing ``BaseModel.schema``."""

    model_config = ConfigDict(populate_by_name=True)

    envelope_schema: str = Field(alias="schema")
    routes: list[RouteRow]

    @field_validator("envelope_schema")
    @classmethod
    def schema_ok(cls, v: str) -> str:
        if str(v) != SCHEMA_SENTENCE_HUB_ROUTES_V1:
            raise ValueError(f"schema must be {SCHEMA_SENTENCE_HUB_ROUTES_V1!r}")
        return str(v)


def parse_routes_envelope(payload: dict[str, Any]) -> RoutesEnvelope:
    """Validate and return routes envelope; raises ``pydantic.ValidationError`` on failure."""
    return RoutesEnvelope.model_validate(payload)


def validate_hub_manifest(
    entries: list[dict[str, Any] | HubManifestEntry] | None,
    *,
    corpus_root: Path,
    validate_paths: bool,
    max_manifest_entries: int = 64,
) -> list[str]:
    """
    Pre-LLM manifest checks. Returns list of violation strings (empty if ok).
    """
    violations: list[str] = []
    if not entries:
        violations.append("M0: hub_manifest is empty or missing")
        return violations
    if len(entries) > max_manifest_entries:
        violations.append(f"M0: hub_manifest has {len(entries)} entries > max {max_manifest_entries}")

    seen: set[str] = set()
    normalized: list[HubManifestEntry] = []
    for i, raw in enumerate(entries):
        try:
            row = raw if isinstance(raw, HubManifestEntry) else HubManifestEntry.model_validate(raw)
        except Exception as exc:
            violations.append(f"M0: hub_manifest[{i}] invalid: {exc}")
            continue
        if row.slug in seen:
            violations.append(f"M0: duplicate manifest slug {row.slug!r}")
        seen.add(row.slug)
        normalized.append(row)

    if validate_paths and normalized:
        root = corpus_root.resolve()
        for row in normalized:
            p = root / row.path
            if not p.is_file():
                violations.append(f"M1: manifest path missing for slug={row.slug!r}: {row.path}")

    return violations


def manifest_slug_set(entries: list[HubManifestEntry] | list[dict[str, Any]]) -> set[str]:
    slugs: set[str] = set()
    for raw in entries:
        if isinstance(raw, HubManifestEntry):
            slugs.add(raw.slug)
        else:
            s = str((raw or {}).get("slug") or "").strip()
            if s:
                slugs.add(s)
    return slugs
