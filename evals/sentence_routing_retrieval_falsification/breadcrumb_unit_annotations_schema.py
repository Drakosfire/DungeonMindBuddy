"""Structured output schema for single-pass recap unit annotations (``dmb_recap_unit_annotations_v1``).

The model annotates pre-captured sentence units with route tags, beat membership,
location context, and population mentions. Deterministic code compiles breadcrumb
markdown, session-memory rows, and location-beat population indexes.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from evals.sentence_routing_retrieval_falsification.breadcrumb_route_schema import (
    RouteTagAssignment,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import (
    ALLOWED_TAG_TYPES,
    normalize_corpus_route,
)

SCHEMA_UNIT_ANNOTATIONS_V1 = "dmb_recap_unit_annotations_v1"
SCHEMA_LOCATION_BEAT_POPULATION_V1 = "dmb_location_beat_population_v1"
RECORD_KIND_LOCATION_BEAT_POPULATION = "location_beat_population"

PRESENCE_KINDS = frozenset({"explicit", "carried", "mentioned_only"})
POPULATION_SUBJECT_CLASSES = frozenset({"PC", "NPC", "Party", "NewHubCandidate"})

BEAT_ID_RE = re.compile(
    r"^c(?P<campaign>\d+)s(?P<session>\d+)-b(?P<ordinal>\d{3})(?P<suffix>[a-z]?)-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$"
)


class BeatIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    beat_id: str
    summary: str


class LocationMention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location_route: str | None = None
    location_label: str | None = None
    presence_kind: Literal["explicit", "carried", "mentioned_only"]


class PopulationMention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_route: str | None = None
    entity_label: str | None = None
    subject_class: str | None = None
    presence_kind: Literal["explicit", "carried", "mentioned_only"]
    entity_state: str | None = None
    support_unit_ids: list[str] = Field(default_factory=list)


class UnitAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_id: str
    beat_id: str | None = None
    tags: list[RouteTagAssignment] = Field(default_factory=list)
    location_mentions: list[LocationMention] = Field(default_factory=list)
    population_mentions: list[PopulationMention] = Field(default_factory=list)


class RecapUnitAnnotationsV1(BaseModel):
    """OpenAI ``responses.parse`` / strict JSON output shape."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_discriminator: Literal["dmb_recap_unit_annotations_v1"] = Field(alias="schema")
    source_recap_path: str
    campaign_id: str
    session_number: int
    beat_index: list[BeatIndexEntry] = Field(default_factory=list)
    unit_annotations: list[UnitAnnotation] = Field(default_factory=list)


def beat_id_matches_grammar(beat_id: str) -> bool:
    return bool(BEAT_ID_RE.match(str(beat_id or "").strip()))


def validate_unit_annotations_shape(
    payload: RecapUnitAnnotationsV1,
    *,
    expected_source_recap_path: str,
    expected_campaign_id: str,
    expected_session_number: int,
    known_unit_ids: list[str],
    route_allowlist_normalized: set[str],
) -> None:
    """Fail closed on envelope drift, unit coverage, routes, and support_unit_ids."""
    from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
        BreadcrumbNormalizeError,
    )

    src = str(payload.source_recap_path or "").strip()
    if src != str(expected_source_recap_path or "").strip():
        raise BreadcrumbNormalizeError(
            "unit annotations source_recap_path mismatch: "
            f"model={src!r} expected={expected_source_recap_path!r}"
        )
    if str(payload.campaign_id or "").strip() != str(expected_campaign_id or "").strip():
        raise BreadcrumbNormalizeError(
            "unit annotations campaign_id mismatch: "
            f"model={payload.campaign_id!r} expected={expected_campaign_id!r}"
        )
    if int(payload.session_number) != int(expected_session_number):
        raise BreadcrumbNormalizeError(
            "unit annotations session_number mismatch: "
            f"model={payload.session_number!r} expected={expected_session_number!r}"
        )

    known = list(known_unit_ids)
    known_set = set(known)
    if len(payload.unit_annotations) != len(known):
        raise BreadcrumbNormalizeError(
            "unit_annotations length mismatch: "
            f"model={len(payload.unit_annotations)} expected={len(known)}"
        )
    seen_units: set[str] = set()
    for idx, row in enumerate(payload.unit_annotations):
        uid = str(row.unit_id or "").strip()
        if uid in seen_units:
            raise BreadcrumbNormalizeError(f"duplicate unit_annotations entry for unit_id={uid!r}")
        seen_units.add(uid)
        if uid not in known_set:
            raise BreadcrumbNormalizeError(f"unknown unit_id in unit_annotations: {uid!r}")
        if known[idx] != uid:
            raise BreadcrumbNormalizeError(
                "unit_annotations order mismatch at index "
                f"{idx}: model={uid!r} expected={known[idx]!r}"
            )
        for t in row.tags:
            tt = str(t.tag_type or "").strip()
            if tt not in ALLOWED_TAG_TYPES:
                raise BreadcrumbNormalizeError(f"disallowed tag_type: {tt!r}")
            nr = normalize_corpus_route(t.route)
            if nr not in route_allowlist_normalized:
                raise BreadcrumbNormalizeError(
                    f"route not in frontmatter allowlist (normalized): {nr!r}"
                )
        for loc in row.location_mentions:
            has_route = bool(str(loc.location_route or "").strip())
            has_label = bool(str(loc.location_label or "").strip())
            if has_route == has_label:
                raise BreadcrumbNormalizeError(
                    "location_mention requires exactly one of location_route or location_label"
                )
            if has_route:
                nr = normalize_corpus_route(str(loc.location_route))
                if nr not in route_allowlist_normalized:
                    raise BreadcrumbNormalizeError(
                        f"location_route not in allowlist (normalized): {nr!r}"
                    )
            if str(loc.presence_kind) not in PRESENCE_KINDS:
                raise BreadcrumbNormalizeError(f"invalid location presence_kind: {loc.presence_kind!r}")
        for pop in row.population_mentions:
            has_route = bool(str(pop.entity_route or "").strip())
            has_label = bool(str(pop.entity_label or "").strip())
            if has_route == has_label:
                raise BreadcrumbNormalizeError(
                    "population_mention requires exactly one of entity_route or entity_label"
                )
            if has_route:
                nr = normalize_corpus_route(str(pop.entity_route))
                if nr not in route_allowlist_normalized:
                    raise BreadcrumbNormalizeError(
                        f"entity_route not in allowlist (normalized): {nr!r}"
                    )
            if str(pop.presence_kind) not in PRESENCE_KINDS:
                raise BreadcrumbNormalizeError(f"invalid population presence_kind: {pop.presence_kind!r}")
            for sid in pop.support_unit_ids:
                if str(sid).strip() not in known_set:
                    raise BreadcrumbNormalizeError(
                        f"unknown support_unit_id in population_mention: {sid!r}"
                    )


def validate_unit_annotations_semantic(payload: RecapUnitAnnotationsV1) -> None:
    """Content gates: beat grammar, contiguity, carry chains, mentioned_only roster exclusion."""
    from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
        BreadcrumbNormalizeError,
    )

    beat_ids_in_index = {str(b.beat_id).strip() for b in payload.beat_index}
    unit_order = [str(row.unit_id).strip() for row in payload.unit_annotations]
    unit_index = {uid: i for i, uid in enumerate(unit_order)}
    beat_to_indices: dict[str, list[int]] = {}

    for row in payload.unit_annotations:
        bid = str(row.beat_id or "").strip() or None
        if bid is None:
            continue
        if bid not in beat_ids_in_index:
            raise BreadcrumbNormalizeError(f"beat_id not listed in beat_index: {bid!r}")
        if not beat_id_matches_grammar(bid):
            raise BreadcrumbNormalizeError(f"beat_id does not match grammar: {bid!r}")
        beat_to_indices.setdefault(bid, []).append(unit_index[row.unit_id])

    for bid, indices in beat_to_indices.items():
        if not indices:
            continue
        lo, hi = min(indices), max(indices)
        if indices != list(range(lo, hi + 1)):
            raise BreadcrumbNormalizeError(f"beat_id {bid!r} is not contiguous over units")

    seen_beats: list[str | None] = []
    for row in payload.unit_annotations:
        bid = str(row.beat_id or "").strip() or None
        seen_beats.append(bid)

    current_beat: str | None = None
    finished_beats: set[str] = set()
    for bid in seen_beats:
        if bid == current_beat:
            continue
        if bid is None:
            current_beat = None
            continue
        if bid in finished_beats:
            raise BreadcrumbNormalizeError(f"beat_id {bid!r} reopens after a different beat")
        if current_beat is not None:
            finished_beats.add(current_beat)
        current_beat = bid

    for row in payload.unit_annotations:
        uid = str(row.unit_id).strip()
        bid = str(row.beat_id or "").strip() or None
        for pop in row.population_mentions:
            if str(pop.presence_kind) == "carried":
                supports = [str(s).strip() for s in pop.support_unit_ids]
                if uid not in supports:
                    raise BreadcrumbNormalizeError(
                        f"carried population on {uid!r} must include current unit in support_unit_ids"
                    )
                if bid is None:
                    raise BreadcrumbNormalizeError(
                        f"carried population on {uid!r} requires a non-null beat_id"
                    )
                prior_same_beat = False
                for sid in supports:
                    if sid == uid:
                        continue
                    other = next(
                        (r for r in payload.unit_annotations if str(r.unit_id).strip() == sid),
                        None,
                    )
                    if other is None:
                        continue
                    if str(other.beat_id or "").strip() == bid:
                        prior_same_beat = True
                        break
                if not prior_same_beat:
                    raise BreadcrumbNormalizeError(
                        f"carried population on {uid!r} lacks same-beat support_unit_ids"
                    )


def validate_unit_annotations(
    payload: RecapUnitAnnotationsV1,
    *,
    expected_source_recap_path: str,
    expected_campaign_id: str,
    expected_session_number: int,
    known_unit_ids: list[str],
    route_allowlist_normalized: set[str],
    run_semantic: bool = True,
) -> None:
    validate_unit_annotations_shape(
        payload,
        expected_source_recap_path=expected_source_recap_path,
        expected_campaign_id=expected_campaign_id,
        expected_session_number=expected_session_number,
        known_unit_ids=known_unit_ids,
        route_allowlist_normalized=route_allowlist_normalized,
    )
    if run_semantic:
        validate_unit_annotations_semantic(payload)
