"""Deterministic compile: ``dmb_recap_unit_annotations_v1`` → breadcrumb / memory / location beats."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    normalize_for_alignment,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_route_schema import (
    BreadcrumbRouteAssignmentsV1,
    UnitRouteAssignment,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import (
    normalize_corpus_route,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_schema import (
    RECORD_KIND_LOCATION_BEAT_POPULATION,
    SCHEMA_LOCATION_BEAT_POPULATION_V1,
    RecapUnitAnnotationsV1,
)


def to_route_assignments(payload: RecapUnitAnnotationsV1) -> BreadcrumbRouteAssignmentsV1:
    return BreadcrumbRouteAssignmentsV1(
        schema_discriminator="dmb_breadcrumb_route_assignments_v1",
        source_recap_path=payload.source_recap_path,
        assignments=[
            UnitRouteAssignment(unit_id=row.unit_id, tags=list(row.tags))
            for row in payload.unit_annotations
        ],
    )


def derive_beat_spans(payload: RecapUnitAnnotationsV1) -> list[dict[str, Any]]:
    """Per beat_id: ordered unit_ids plus start/end unit_id (from beat_index order)."""
    by_beat: dict[str, list[str]] = defaultdict(list)
    for row in payload.unit_annotations:
        bid = str(row.beat_id or "").strip()
        if not bid:
            continue
        by_beat[bid].append(str(row.unit_id).strip())
    summaries = {str(b.beat_id).strip(): str(b.summary) for b in payload.beat_index}
    out: list[dict[str, Any]] = []
    for entry in payload.beat_index:
        bid = str(entry.beat_id).strip()
        unit_ids = by_beat.get(bid, [])
        out.append(
            {
                "beat_id": bid,
                "summary": summaries.get(bid, entry.summary),
                "unit_ids": unit_ids,
                "start_unit_id": unit_ids[0] if unit_ids else None,
                "end_unit_id": unit_ids[-1] if unit_ids else None,
            }
        )
    return out


def enrich_records_with_beat_ids(
    records: list[dict[str, Any]],
    payload: RecapUnitAnnotationsV1,
) -> list[dict[str, Any]]:
    beat_by_unit = {
        str(row.unit_id).strip(): str(row.beat_id).strip() if row.beat_id else None
        for row in payload.unit_annotations
    }
    enriched: list[dict[str, Any]] = []
    for rec in records:
        row = dict(rec)
        uid = str(row.get("unit_id") or "").strip()
        if uid in beat_by_unit:
            row["beat_id"] = beat_by_unit[uid]
        enriched.append(row)
    return enriched


def _location_key(loc_route: str | None, loc_label: str | None) -> tuple[str, str]:
    if loc_route:
        return ("route", normalize_corpus_route(loc_route))
    return ("label", str(loc_label or "").strip().lower())


def _entity_key(pop: Any) -> tuple[str, str]:
    if pop.entity_route:
        return ("route", normalize_corpus_route(str(pop.entity_route)))
    return ("label", str(pop.entity_label or "").strip().lower())


def _population_row_key(
    *,
    beat_id: str,
    loc_route: str | None,
    loc_label: str | None,
) -> tuple[str, tuple[str, str]]:
    return (beat_id, _location_key(loc_route, loc_label))


def compile_location_beat_rows(payload: RecapUnitAnnotationsV1) -> list[dict[str, Any]]:
    """Group by (beat_id, location) and aggregate present population evidence."""
    work: dict[tuple[str, tuple[str, str]], dict[str, Any]] = {}

    for row in payload.unit_annotations:
        bid = str(row.beat_id or "").strip()
        if not bid:
            continue
        uid = str(row.unit_id).strip()
        for loc in row.location_mentions:
            loc_route = str(loc.location_route).strip() if loc.location_route else None
            loc_label = str(loc.location_label).strip() if loc.location_label else None
            key = _population_row_key(beat_id=bid, loc_route=loc_route, loc_label=loc_label)
            if key not in work:
                work[key] = {
                    "schema": SCHEMA_LOCATION_BEAT_POPULATION_V1,
                    "record_kind": RECORD_KIND_LOCATION_BEAT_POPULATION,
                    "beat_id": bid,
                    "campaign_id": payload.campaign_id,
                    "session_number": payload.session_number,
                    "source_recap_path": payload.source_recap_path,
                    "location_routes": [],
                    "location_labels": [],
                    "entity_routes_present": [],
                    "unit_ids": [],
                    "population_evidence": [],
                    "_entity_present": set(),
                    "_entity_evidence": {},
                }
            bucket = work[key]
            if loc_route:
                nr = normalize_corpus_route(loc_route)
                if nr not in bucket["location_routes"]:
                    bucket["location_routes"].append(nr)
            elif loc_label and loc_label not in bucket["location_labels"]:
                bucket["location_labels"].append(loc_label)
            if uid not in bucket["unit_ids"]:
                bucket["unit_ids"].append(uid)

        for pop in row.population_mentions:
            if str(pop.presence_kind) == "mentioned_only":
                continue
            for loc in row.location_mentions:
                loc_route = str(loc.location_route).strip() if loc.location_route else None
                loc_label = str(loc.location_label).strip() if loc.location_label else None
                key = _population_row_key(beat_id=bid, loc_route=loc_route, loc_label=loc_label)
                if key not in work:
                    work[key] = {
                        "schema": SCHEMA_LOCATION_BEAT_POPULATION_V1,
                        "record_kind": RECORD_KIND_LOCATION_BEAT_POPULATION,
                        "beat_id": bid,
                        "campaign_id": payload.campaign_id,
                        "session_number": payload.session_number,
                        "source_recap_path": payload.source_recap_path,
                        "location_routes": [],
                        "location_labels": [],
                        "entity_routes_present": [],
                        "unit_ids": [],
                        "population_evidence": [],
                        "_entity_present": set(),
                        "_entity_evidence": {},
                    }
                bucket = work[key]
                ent_key = _entity_key(pop)
                ev = bucket["_entity_evidence"].setdefault(
                    ent_key,
                    {
                        "entity_route": normalize_corpus_route(str(pop.entity_route))
                        if pop.entity_route
                        else None,
                        "entity_label": str(pop.entity_label).strip()
                        if pop.entity_label
                        else None,
                        "presence_kind": str(pop.presence_kind),
                        "entity_state": pop.entity_state,
                        "evidence_unit_ids": [],
                    },
                )
                for sid in pop.support_unit_ids or [uid]:
                    sid_s = str(sid).strip()
                    if sid_s and sid_s not in ev["evidence_unit_ids"]:
                        ev["evidence_unit_ids"].append(sid_s)
                if ent_key[0] == "route" and ent_key[1] not in bucket["_entity_present"]:
                    bucket["_entity_present"].add(ent_key[1])
                    bucket["entity_routes_present"].append(ent_key[1])

    rows: list[dict[str, Any]] = []
    for bucket in work.values():
        bucket["population_evidence"] = list(bucket.pop("_entity_evidence").values())
        bucket.pop("_entity_present", None)
        lexical_parts = [
            bucket["beat_id"].replace("-", " "),
            *bucket["location_routes"],
            *bucket["location_labels"],
        ]
        for ev in bucket["population_evidence"]:
            if ev.get("entity_route"):
                lexical_parts.append(str(ev["entity_route"]).split("/")[-2])
            if ev.get("entity_label"):
                lexical_parts.append(str(ev["entity_label"]))
            lexical_parts.append(str(ev.get("presence_kind") or ""))
        bucket["lexical_plain"] = normalize_for_alignment(" ".join(lexical_parts))
        rows.append(bucket)

    rows.sort(key=lambda r: (str(r["beat_id"]), str(r.get("location_routes")), str(r.get("location_labels"))))
    return rows


def compile_unit_annotations_artifacts(
    payload: RecapUnitAnnotationsV1,
    *,
    session_memory_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Bundle route assignments, beat spans, location rows, and optional enriched records."""
    out: dict[str, Any] = {
        "route_assignments": to_route_assignments(payload),
        "beat_spans": derive_beat_spans(payload),
        "location_beat_rows": compile_location_beat_rows(payload),
    }
    if session_memory_records is not None:
        out["session_memory_records"] = enrich_records_with_beat_ids(
            session_memory_records,
            payload,
        )
    return out
