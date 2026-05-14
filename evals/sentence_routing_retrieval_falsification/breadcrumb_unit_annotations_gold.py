"""Load manual beat-population gold and compare against unit-annotation ingest output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import (
    normalize_corpus_route,
    parse_frontmatter_and_body,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_schema import (
    RecapUnitAnnotationsV1,
)


@dataclass
class GoldPopulationEvidence:
    entity_route: str | None = None
    entity_label: str | None = None
    presence_kind: str = ""
    evidence_unit_ids: list[str] = field(default_factory=list)


@dataclass
class GoldBeatEntry:
    beat_id: str
    summary: str
    unit_ids: list[str] = field(default_factory=list)
    location_routes: list[str] = field(default_factory=list)
    location_labels: list[str] = field(default_factory=list)
    population_evidence: list[GoldPopulationEvidence] = field(default_factory=list)


_RE_BEAT_ID = re.compile(r"^\s*-\s*beat_id:\s*(\S+)\s*$", re.MULTILINE)
_RE_UNIT_IDS = re.compile(r"^\s*unit_ids:\s*\[([^\]]+)\]\s*$", re.MULTILINE)
_RE_LOCATION_ROUTE = re.compile(r'^\s*-\s*"([^"]+)"\s*$', re.MULTILINE)
_RE_LOCATION_LABELS = re.compile(r'^\s*location_labels:\s*\[([^\]]+)\]\s*$', re.MULTILINE)
_RE_POP_ENTITY_ROUTE = re.compile(r'^\s*entity_route:\s*"([^"]+)"\s*$', re.MULTILINE)
_RE_POP_ENTITY_LABEL = re.compile(r'^\s*entity_label:\s*"([^"]+)"\s*$', re.MULTILINE)
_RE_POP_PRESENCE = re.compile(r"^\s*presence_kind:\s*(\S+)\s*$", re.MULTILINE)
_RE_POP_EVIDENCE_UNITS = re.compile(r"^\s*evidence_unit_ids:\s*\[([^\]]+)\]\s*$", re.MULTILINE)


def _split_unit_id_list(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def _split_quoted_labels(raw: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r'"([^"]+)"', raw)]


def _parse_population_block(block: str) -> list[GoldPopulationEvidence]:
    entries: list[GoldPopulationEvidence] = []
    cur: GoldPopulationEvidence | None = None
    for line in block.splitlines():
        route_m = re.match(r'^\s+-\s+entity_route:\s*"([^"]+)"\s*$', line)
        label_m = re.match(r'^\s+-\s+entity_label:\s*"([^"]+)"\s*$', line)
        if route_m or label_m:
            if cur is not None:
                entries.append(cur)
            cur = GoldPopulationEvidence(
                entity_route=normalize_corpus_route(route_m.group(1)) if route_m else None,
                entity_label=label_m.group(1).strip() if label_m else None,
            )
            continue
        if cur is None:
            continue
        presence_m = re.match(r"^\s+presence_kind:\s*(\S+)\s*$", line)
        if presence_m:
            cur.presence_kind = presence_m.group(1).strip()
            continue
        evidence_m = re.match(r"^\s+evidence_unit_ids:\s*\[([^\]]+)\]\s*$", line)
        if evidence_m:
            cur.evidence_unit_ids = _split_unit_id_list(evidence_m.group(1))
    if cur is not None:
        entries.append(cur)
    return entries


def unit_beat_id_map_from_gold_beats(beats: Sequence[GoldBeatEntry]) -> dict[str, str]:
    """Map each ``unit_id`` to its ``beat_id`` (last wins if gold ever overlaps)."""
    out: dict[str, str] = {}
    for beat in beats:
        bid = str(beat.beat_id).strip()
        for uid in beat.unit_ids:
            out[str(uid).strip()] = bid
    return out


def load_gold_beat_index(path: Path) -> list[GoldBeatEntry]:
    text = path.read_text(encoding="utf-8")
    frontmatter, _body = parse_frontmatter_and_body(text)
    if frontmatter is None:
        raise ValueError(f"missing frontmatter in gold file: {path}")
    anchor = frontmatter.find("beat_index:")
    if anchor < 0:
        raise ValueError(f"gold file missing beat_index: {path}")
    section = frontmatter[anchor:]
    beat_starts = [m.start() for m in re.finditer(r"^\s*-\s*beat_id:", section, flags=re.MULTILINE)]
    if not beat_starts:
        raise ValueError(f"gold beat_index has no beats: {path}")
    beat_starts.append(len(section))
    beats: list[GoldBeatEntry] = []
    for i in range(len(beat_starts) - 1):
        block = section[beat_starts[i] : beat_starts[i + 1]]
        beat_id_m = _RE_BEAT_ID.search(block)
        if not beat_id_m:
            continue
        summary_m = re.search(r'^\s*summary:\s*"(.*)"\s*$', block, flags=re.MULTILINE)
        unit_ids_m = _RE_UNIT_IDS.search(block)
        loc_routes: list[str] = []
        loc_section = re.search(
            r"^\s*location_routes:\s*$([\s\S]*?)(?:^\s*location_labels:|^\s*population_evidence:|^\s*-\s*beat_id:|\Z)",
            block,
            flags=re.MULTILINE,
        )
        if loc_section:
            loc_routes = [
                normalize_corpus_route(m.group(1))
                for m in _RE_LOCATION_ROUTE.finditer(loc_section.group(1))
            ]
        labels_m = _RE_LOCATION_LABELS.search(block)
        location_labels = _split_quoted_labels(labels_m.group(1)) if labels_m else []
        pop_section = re.search(
            r"^\s*population_evidence:\s*$([\s\S]*?)(?:^\s*-\s*beat_id:|\Z)",
            block,
            flags=re.MULTILINE,
        )
        population = _parse_population_block(pop_section.group(1)) if pop_section else []
        beats.append(
            GoldBeatEntry(
                beat_id=beat_id_m.group(1).strip(),
                summary=summary_m.group(1).strip() if summary_m else "",
                unit_ids=_split_unit_id_list(unit_ids_m.group(1)) if unit_ids_m else [],
                location_routes=loc_routes,
                location_labels=location_labels,
                population_evidence=population,
            )
        )
    return beats


def _entity_key(route: str | None, label: str | None) -> str:
    if route:
        return f"route:{normalize_corpus_route(route)}"
    return f"label:{str(label or '').strip().lower()}"


def _payload_beat_unit_map(payload: RecapUnitAnnotationsV1) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for row in payload.unit_annotations:
        bid = str(row.beat_id or "").strip()
        if not bid:
            continue
        out.setdefault(bid, []).append(str(row.unit_id).strip())
    return out


def _payload_beat_population(
    payload: RecapUnitAnnotationsV1,
) -> dict[str, set[tuple[str, str]]]:
    """Per beat_id: (entity_key, presence_kind) from unit population_mentions."""
    by_beat: dict[str, set[tuple[str, str]]] = {}
    for row in payload.unit_annotations:
        bid = str(row.beat_id or "").strip()
        if not bid:
            continue
        bucket = by_beat.setdefault(bid, set())
        for pop in row.population_mentions:
            bucket.add(
                (
                    _entity_key(pop.entity_route, pop.entity_label),
                    str(pop.presence_kind),
                )
            )
    return by_beat


def _gold_present_population(beat: GoldBeatEntry) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for ev in beat.population_evidence:
        kind = str(ev.presence_kind or "").strip()
        if kind in {"mentioned_only", "absent"}:
            continue
        out.add((_entity_key(ev.entity_route, ev.entity_label), kind))
    return out


def _gold_mentioned_only(beat: GoldBeatEntry) -> set[str]:
    return {
        _entity_key(ev.entity_route, ev.entity_label)
        for ev in beat.population_evidence
        if str(ev.presence_kind) == "mentioned_only"
    }


def _unit_jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return 0.0 if not union else len(a & b) / len(union)


def _best_unit_span_match(
    gold_unit_ids: set[str],
    model_units: dict[str, list[str]],
) -> dict[str, Any] | None:
    candidates: list[tuple[float, int, str, set[str]]] = []
    for beat_id, unit_ids in model_units.items():
        model_set = set(unit_ids)
        intersection = gold_unit_ids & model_set
        candidates.append((_unit_jaccard(gold_unit_ids, model_set), len(intersection), beat_id, model_set))
    if not candidates:
        return None
    score, overlap_count, beat_id, model_set = max(candidates, key=lambda row: (row[0], row[1], row[2]))
    return {
        "beat_id": beat_id,
        "unit_jaccard": round(score, 4),
        "overlap_count": overlap_count,
        "unit_ids": sorted(model_set),
        "missing_unit_ids": sorted(gold_unit_ids - model_set),
        "extra_unit_ids": sorted(model_set - gold_unit_ids),
    }


def compare_unit_annotations_to_gold(
    payload: RecapUnitAnnotationsV1,
    gold_beats: list[GoldBeatEntry],
) -> dict[str, Any]:
    gold_by_id = {b.beat_id: b for b in gold_beats}
    model_units = _payload_beat_unit_map(payload)
    model_pop = _payload_beat_population(payload)

    beat_membership_matches = 0
    beat_membership_total = 0
    location_matches = 0
    location_total = 0
    present_matches = 0
    present_total = 0
    mentioned_matches = 0
    mentioned_total = 0
    per_beat: list[dict[str, Any]] = []
    exact_unit_span_matches = 0
    best_unit_jaccard_sum = 0.0

    for beat_id, gold in gold_by_id.items():
        model_unit_ids = model_units.get(beat_id, [])
        gold_set = set(gold.unit_ids)
        model_set = set(model_unit_ids)
        unit_ok = gold_set == model_set
        best_span_match = _best_unit_span_match(gold_set, model_units)
        if best_span_match is not None:
            best_unit_jaccard_sum += float(best_span_match["unit_jaccard"])
            if float(best_span_match["unit_jaccard"]) == 1.0:
                exact_unit_span_matches += 1
        beat_membership_total += 1
        if unit_ok:
            beat_membership_matches += 1

        gold_locs = set(gold.location_routes) | {lbl.strip().lower() for lbl in gold.location_labels}
        model_locs: set[str] = set()
        for row in payload.unit_annotations:
            if str(row.beat_id or "").strip() != beat_id:
                continue
            for loc in row.location_mentions:
                if loc.location_route:
                    model_locs.add(normalize_corpus_route(str(loc.location_route)))
                if loc.location_label:
                    model_locs.add(str(loc.location_label).strip().lower())
        loc_ok = gold_locs <= model_locs if gold_locs else True
        if gold_locs:
            location_total += 1
            if loc_ok:
                location_matches += 1

        gold_present = _gold_present_population(gold)
        model_present = {
            (k, kind)
            for k, kind in model_pop.get(beat_id, set())
            if kind != "mentioned_only"
        }
        present_total += 1
        present_ok = gold_present == model_present
        if present_ok:
            present_matches += 1

        gold_mentioned = _gold_mentioned_only(gold)
        model_mentioned = {
            k for k, kind in model_pop.get(beat_id, set()) if kind == "mentioned_only"
        }
        if gold_mentioned:
            mentioned_total += 1
            if gold_mentioned == model_mentioned:
                mentioned_matches += 1

        per_beat.append(
            {
                "beat_id": beat_id,
                "unit_ids_match": unit_ok,
                "gold_unit_ids": sorted(gold_set),
                "model_unit_ids": sorted(model_set),
                "missing_unit_ids": sorted(gold_set - model_set),
                "extra_unit_ids": sorted(model_set - gold_set),
                "location_gold": sorted(gold_locs),
                "location_model": sorted(model_locs),
                "present_population_match": present_ok,
                "gold_present_population": sorted(gold_present),
                "model_present_population": sorted(model_present),
                "mentioned_only_match": gold_mentioned == model_mentioned,
                "gold_mentioned_only": sorted(gold_mentioned),
                "model_mentioned_only": sorted(model_mentioned),
                "best_model_unit_span_match": best_span_match,
            }
        )

    extra_beats = sorted(set(model_units) - set(gold_by_id))
    missing_beats = sorted(set(gold_by_id) - set(model_units))

    def _rate(num: int, den: int) -> float | None:
        return None if den == 0 else round(num / den, 4)

    return {
        "gold_beat_count": len(gold_by_id),
        "model_beat_count": len(model_units),
        "missing_beats": missing_beats,
        "extra_beats": extra_beats,
        "dimension_pass_rates": {
            "beat_unit_membership": _rate(beat_membership_matches, beat_membership_total),
            "location_routes_and_labels": _rate(location_matches, location_total),
            "present_population": _rate(present_matches, present_total),
            "mentioned_only_population": _rate(mentioned_matches, mentioned_total),
        },
        "unit_span_alignment": {
            "exact_unit_span_matches": exact_unit_span_matches,
            "best_unit_jaccard_mean": _rate(best_unit_jaccard_sum, beat_membership_total),
        },
        "per_beat": per_beat,
    }
