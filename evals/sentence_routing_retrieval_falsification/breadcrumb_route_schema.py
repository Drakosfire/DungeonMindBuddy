"""Structured output schema for routing-only breadcrumb ingest (``dmb_breadcrumb_route_assignments_v1``).

The model assigns corpus routes to pre-captured sentence units; deterministic code
injects ``[TagType][route]`` suffixes into the source recap body.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import (
    ALLOWED_TAG_TYPES,
    normalize_corpus_route,
)


class RouteTagAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tag_type: str = Field(
        ...,
        description="One of PC, NPC, Location, Party, NewHubCandidate.",
    )
    route: str = Field(
        ...,
        description="Exact corpus-relative hub route from the allowlist (slashes matter).",
    )


class UnitRouteAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_id: str
    tags: list[RouteTagAssignment] = Field(default_factory=list)


class BreadcrumbRouteAssignmentsV1(BaseModel):
    """OpenAI ``responses.parse`` / strict JSON output shape."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    schema_discriminator: Literal["dmb_breadcrumb_route_assignments_v1"] = Field(
        alias="schema",
    )
    source_recap_path: str
    assignments: list[UnitRouteAssignment] = Field(default_factory=list)


def validate_route_assignments(
    payload: BreadcrumbRouteAssignmentsV1,
    *,
    expected_source_recap_path: str,
    known_unit_ids: set[str],
    route_allowlist_normalized: set[str],
) -> None:
    """Fail closed on path drift, unknown units, bad tag types, or routes off-allowlist."""
    from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
        BreadcrumbNormalizeError,
    )

    src = str(payload.source_recap_path or "").strip()
    if src != str(expected_source_recap_path or "").strip():
        raise BreadcrumbNormalizeError(
            "route assignment source_recap_path mismatch: "
            f"model={src!r} expected={expected_source_recap_path!r}"
        )

    seen: set[tuple[str, str, str]] = set()
    seen_units: set[str] = set()
    for row in payload.assignments:
        uid = str(row.unit_id or "").strip()
        if uid in seen_units:
            raise BreadcrumbNormalizeError(f"duplicate assignments entry for unit_id={uid!r}")
        seen_units.add(uid)
        if uid not in known_unit_ids:
            raise BreadcrumbNormalizeError(f"unknown unit_id in route assignments: {uid!r}")
        for t in row.tags:
            tt = str(t.tag_type or "").strip()
            if tt not in ALLOWED_TAG_TYPES:
                raise BreadcrumbNormalizeError(f"disallowed tag_type: {tt!r}")
            nr = normalize_corpus_route(t.route)
            if nr not in route_allowlist_normalized:
                raise BreadcrumbNormalizeError(
                    f"route not in frontmatter allowlist (normalized): {nr!r}"
                )
            key = (uid, tt, nr)
            if key in seen:
                raise BreadcrumbNormalizeError(
                    f"duplicate assignment for unit/tag/route: {key!r}"
                )
            seen.add(key)
