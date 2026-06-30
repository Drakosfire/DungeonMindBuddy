from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .lexical_observation import normalize_observed_text
from .model import ContextVocabularyPacket, EntityKind


@dataclass(slots=True)
class ExtractedVocabularyNode:
    """Small adapter record for passive vocabulary extraction diagnostics."""

    node_id: str
    label: str
    entity_kind: EntityKind = "unknown"
    source: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.node_id, "node_id")
        _require_non_empty(self.label, "label")


@dataclass(slots=True)
class ExtractedVocabularyEdge:
    """Small adapter record for passive vocabulary edge diagnostics."""

    edge_id: str
    source_label: str
    predicate: str
    target_label: str
    source_node_id: str | None = None
    target_node_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.edge_id, "edge_id")
        _require_non_empty(self.source_label, "source_label")
        _require_non_empty(self.predicate, "predicate")
        _require_non_empty(self.target_label, "target_label")


@dataclass(slots=True)
class VocabularyExtractionDiagnosticsResult:
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.diagnostics


def _require_non_empty(value: str | None, field_name: str) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")


def _sort_labels(labels: Iterable[str]) -> list[str]:
    return sorted(labels, key=lambda label: (label.lower(), label))


def _sort_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(records, key=lambda item: (str(item.get("label", "")).lower(), str(item.get("predicate", ""))))


def diagnose_vocabulary_extraction_baseline(
    *,
    packet: ContextVocabularyPacket,
    extracted_nodes: Iterable[ExtractedVocabularyNode],
    extracted_edges: Iterable[ExtractedVocabularyEdge] = (),
    diagnostics_method: str = "post_extraction_vocabulary_diagnostics_v1",
    vocab_id_to_label: Mapping[str, str] | None = None,
) -> VocabularyExtractionDiagnosticsResult:
    nodes = list(extracted_nodes)
    edges = list(extracted_edges)

    labels_by_normalized: dict[str, list[ExtractedVocabularyNode]] = {}
    first_label_by_normalized: dict[str, str] = {}
    for node in nodes:
        normalized = normalize_observed_text(node.label)
        labels_by_normalized.setdefault(normalized, []).append(node)
        first_label_by_normalized.setdefault(normalized, node.label)

    extracted_label_norms = set(labels_by_normalized)

    matched_known = [label for label in packet.known_names if normalize_observed_text(label) in extracted_label_norms]
    missed_known = [label for label in packet.known_names if normalize_observed_text(label) not in extracted_label_norms]
    known_name_count = len(packet.known_names)
    match_count = len(matched_known)
    miss_count = len(missed_known)
    pickup_rate = round(match_count / known_name_count, 3) if known_name_count else 0.0

    type_matched: list[dict[str, Any]] = []
    type_mismatched: list[dict[str, Any]] = []
    type_missing: list[dict[str, Any]] = []
    for label, expected in sorted(packet.type_hints.items(), key=lambda item: (item[0].lower(), item[0])):
        matched_nodes = labels_by_normalized.get(normalize_observed_text(label), [])
        if not matched_nodes:
            type_missing.append({"label": label, "expected": expected})
            continue
        actual_kinds = sorted({node.entity_kind for node in matched_nodes})
        if expected in actual_kinds:
            type_matched.append({"label": label, "expected": expected, "actual": expected})
        else:
            type_mismatched.append({"label": label, "expected": expected, "actual": actual_kinds})

    matched_combat = [label for label in packet.combat_encounter_hints if normalize_observed_text(label) in extracted_label_norms]
    missed_combat = [label for label in packet.combat_encounter_hints if normalize_observed_text(label) not in extracted_label_norms]

    edge_touches = {
        (normalize_observed_text(edge.source_label), edge.predicate) for edge in edges
    } | {(normalize_observed_text(edge.target_label), edge.predicate) for edge in edges}
    predicate_matched: list[dict[str, Any]] = []
    predicate_missed: list[dict[str, Any]] = []
    for label, predicates in packet.predicate_hints.items():
        normalized_label = normalize_observed_text(label)
        for predicate in predicates:
            record = {"label": label, "predicate": predicate}
            if (normalized_label, predicate) in edge_touches:
                predicate_matched.append(record)
            else:
                predicate_missed.append(record)

    duplicate_labels: list[dict[str, Any]] = []
    conflicting_kinds: list[dict[str, Any]] = []
    for normalized_label in sorted(labels_by_normalized, key=lambda value: (first_label_by_normalized[value].lower(), value)):
        grouped_nodes = labels_by_normalized[normalized_label]
        if len(grouped_nodes) > 1:
            duplicate_labels.append(
                {"label": first_label_by_normalized[normalized_label], "node_ids": sorted(node.node_id for node in grouped_nodes)}
            )
        kinds = sorted({node.entity_kind for node in grouped_nodes})
        if len(kinds) > 1:
            conflicting_kinds.append({"label": first_label_by_normalized[normalized_label], "kinds": kinds})

    potentially_collapsed = _do_not_merge_collapses(packet, extracted_label_norms, vocab_id_to_label)

    diagnostics: dict[str, Any] = {
        "diagnostics_method": diagnostics_method,
        "packet_id": packet.packet_id,
        "scope": packet.scope,
        "known_name_count": known_name_count,
        "extracted_node_count": len(nodes),
        "extracted_edge_count": len(edges),
        "known_name_pickup": {
            "matched": _sort_labels(matched_known),
            "missed": _sort_labels(missed_known),
            "match_count": match_count,
            "miss_count": miss_count,
            "pickup_rate": pickup_rate,
        },
        "type_hint_alignment": {"matched": type_matched, "mismatched": type_mismatched, "missing": type_missing},
        "combat_encounter_pickup": {"matched": _sort_labels(matched_combat), "missed": _sort_labels(missed_combat)},
        "predicate_hint_pickup": {"matched": _sort_records(predicate_matched), "missed": _sort_records(predicate_missed)},
        "collision_diagnostics": {
            "duplicate_extracted_labels": duplicate_labels,
            "conflicting_kind_labels": conflicting_kinds,
        },
        "do_not_merge_diagnostics": {
            "hint_count": len(packet.do_not_merge_hints),
            "potentially_collapsed": potentially_collapsed,
        },
        "summary": {
            "has_known_name_misses": bool(missed_known),
            "has_type_mismatches": bool(type_mismatched),
            "has_combat_encounter_misses": bool(missed_combat),
            "has_predicate_misses": bool(predicate_missed),
            "has_duplicate_label_collisions": bool(duplicate_labels),
            "has_conflicting_kind_collisions": bool(conflicting_kinds),
            "has_do_not_merge_collisions": bool(potentially_collapsed),
        },
    }
    return VocabularyExtractionDiagnosticsResult(diagnostics=diagnostics)


def _do_not_merge_collapses(
    packet: ContextVocabularyPacket,
    extracted_label_norms: set[str],
    vocab_id_to_label: Mapping[str, str] | None,
) -> list[dict[str, Any]]:
    if not vocab_id_to_label:
        return []
    records: list[dict[str, Any]] = []
    for hint in packet.do_not_merge_hints:
        left_label = vocab_id_to_label.get(hint.left_vocab_id)
        right_label = vocab_id_to_label.get(hint.right_vocab_id)
        if not left_label or not right_label:
            continue
        left_normalized = normalize_observed_text(left_label)
        right_normalized = normalize_observed_text(right_label)
        if left_normalized != right_normalized or left_normalized not in extracted_label_norms:
            continue
        records.append(
            {
                "left_vocab_id": hint.left_vocab_id,
                "right_vocab_id": hint.right_vocab_id,
                "left_label": left_label,
                "right_label": right_label,
                "normalized_label": left_normalized,
            }
        )
    return sorted(records, key=lambda item: (item["normalized_label"], item["left_vocab_id"], item["right_vocab_id"]))


def vocabulary_extraction_diagnostics_to_payload(
    result: VocabularyExtractionDiagnosticsResult,
) -> dict[str, Any]:
    return result.to_dict()
