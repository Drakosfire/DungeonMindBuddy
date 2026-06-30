from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .extraction_diagnostics import ExtractedVocabularyEdge, ExtractedVocabularyNode
from .model import ContextVocabularyPacket

BASELINE_VARIANT = "baseline"
EDGE_PACKET_VARIANT = "edge_packet"
NODE_PACKET_VARIANT = "node_packet"
EDGE_AND_NODE_PACKET_VARIANT = "edge_and_node_packet"

KNOWN_ABLATION_VARIANTS = (
    BASELINE_VARIANT,
    EDGE_PACKET_VARIANT,
    NODE_PACKET_VARIANT,
    EDGE_AND_NODE_PACKET_VARIANT,
)

SCORE_NOTE = "Heuristic review score; not benchmark truth."
SYNTHETIC_NOTE = "Synthetic tests do not prove model improvement."


@dataclass(slots=True)
class VocabularyAblationVariant:
    variant_name: str
    extraction_diagnostics: dict[str, Any]
    extracted_nodes: list[ExtractedVocabularyNode] | None = None
    extracted_edges: list[ExtractedVocabularyEdge] | None = None
    extraction_run_diagnostics: dict[str, Any] | None = None
    notes: list[str] | None = None

    def __post_init__(self) -> None:
        if not self.variant_name or not self.variant_name.strip():
            raise ValueError("variant_name must be non-empty")
        if not isinstance(self.extraction_diagnostics, dict):
            raise ValueError("extraction_diagnostics must be a dict")
        if self.extracted_nodes is not None and not isinstance(self.extracted_nodes, list):
            raise ValueError("extracted_nodes must be a list when provided")
        if self.extracted_edges is not None and not isinstance(self.extracted_edges, list):
            raise ValueError("extracted_edges must be a list when provided")
        if self.notes is None:
            self.notes = []


@dataclass(slots=True)
class VocabularyAblationComparisonResult:
    comparison: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.comparison


def _count_items(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _number(value: Any, default: int | float = 0) -> int | float:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def summarize_variant_metrics(variant: VocabularyAblationVariant) -> dict[str, Any]:
    diagnostics = variant.extraction_diagnostics
    known = diagnostics.get("known_name_pickup", {}) if isinstance(diagnostics.get("known_name_pickup"), dict) else {}
    type_hint = diagnostics.get("type_hint_alignment", {}) if isinstance(diagnostics.get("type_hint_alignment"), dict) else {}
    combat = diagnostics.get("combat_encounter_pickup", {}) if isinstance(diagnostics.get("combat_encounter_pickup"), dict) else {}
    predicate = diagnostics.get("predicate_hint_pickup", {}) if isinstance(diagnostics.get("predicate_hint_pickup"), dict) else {}
    collisions = diagnostics.get("collision_diagnostics", {}) if isinstance(diagnostics.get("collision_diagnostics"), dict) else {}
    do_not_merge = diagnostics.get("do_not_merge_diagnostics", {}) if isinstance(diagnostics.get("do_not_merge_diagnostics"), dict) else {}

    metrics: dict[str, Any] = {
        "known_name_pickup_rate": _number(known.get("pickup_rate"), 0.0),
        "known_name_match_count": int(_number(known.get("match_count"), _count_items(known.get("matched")))),
        "known_name_miss_count": int(_number(known.get("miss_count"), _count_items(known.get("missed")))),
        "type_hint_match_count": _count_items(type_hint.get("matched")),
        "type_hint_mismatch_count": _count_items(type_hint.get("mismatched")),
        "type_hint_missing_count": _count_items(type_hint.get("missing")),
        "combat_encounter_match_count": _count_items(combat.get("matched")),
        "combat_encounter_miss_count": _count_items(combat.get("missed")),
        "predicate_hint_match_count": _count_items(predicate.get("matched")),
        "predicate_hint_miss_count": _count_items(predicate.get("missed")),
        "duplicate_label_collision_count": _count_items(collisions.get("duplicate_extracted_labels")),
        "conflicting_kind_collision_count": _count_items(collisions.get("conflicting_kind_labels")),
        "do_not_merge_collision_count": _count_items(do_not_merge.get("potentially_collapsed")),
    }
    metrics.update(summarize_extraction_run_diagnostics(variant.extraction_run_diagnostics))
    return metrics


def summarize_extraction_run_diagnostics(run_diagnostics: Mapping[str, Any] | None) -> dict[str, Any]:
    reasons: Counter[str] = Counter()
    if not isinstance(run_diagnostics, Mapping):
        return {
            "endpoint_binding_success_count": 0,
            "endpoint_binding_failure_count": 0,
            "edge_drop_count": 0,
            "edge_drop_reasons": {},
            "cross_class_merged_count": 0,
            "cross_class_blocked_count": 0,
            "unsafe_cross_class_blocked_count": 0,
            "edge_predicate_issue_count": 0,
        }

    consolidation = run_diagnostics.get("consolidation_diagnostics", {})
    if not isinstance(consolidation, Mapping):
        consolidation = {}
    dropped_missing = consolidation.get("dropped_edges_missing_endpoints", [])
    missing_count = _count_items(dropped_missing)
    if missing_count:
        reasons["missing_endpoint"] += missing_count

    blocked = consolidation.get("cross_class_blocked_nodes", [])
    unsafe_blocked = sum(
        1 for item in blocked if isinstance(item, Mapping) and item.get("reason") == "unsafe_cross_class_exact_label"
    ) if isinstance(blocked, list) else 0

    assembly = run_diagnostics.get("assembly_diagnostics", {})
    if not isinstance(assembly, Mapping):
        assembly = {}
    drop_counts = assembly.get("drop_counts_by_reason", {})
    if isinstance(drop_counts, Mapping):
        for reason, count in drop_counts.items():
            if isinstance(count, int):
                reasons[str(reason)] += count

    failures = int(sum(reasons.values()))
    success = int(_number(run_diagnostics.get("endpoint_binding_success_count"), 0))
    return {
        "endpoint_binding_success_count": success,
        "endpoint_binding_failure_count": int(_number(run_diagnostics.get("endpoint_binding_failure_count"), failures)),
        "edge_drop_count": failures,
        "edge_drop_reasons": dict(sorted(reasons.items())),
        "cross_class_merged_count": _count_items(consolidation.get("cross_class_merged_nodes")),
        "cross_class_blocked_count": _count_items(blocked),
        "unsafe_cross_class_blocked_count": unsafe_blocked,
        "edge_predicate_issue_count": _count_items(consolidation.get("edge_predicate_issues")),
    }


def compute_variant_delta(baseline_metrics: Mapping[str, Any], variant_metrics: Mapping[str, Any]) -> dict[str, Any]:
    pairs = {
        "known_name_pickup_rate_delta": "known_name_pickup_rate",
        "known_name_match_count_delta": "known_name_match_count",
        "known_name_miss_count_delta": "known_name_miss_count",
        "type_hint_match_count_delta": "type_hint_match_count",
        "type_hint_mismatch_count_delta": "type_hint_mismatch_count",
        "combat_encounter_match_count_delta": "combat_encounter_match_count",
        "combat_encounter_miss_count_delta": "combat_encounter_miss_count",
        "predicate_hint_match_count_delta": "predicate_hint_match_count",
        "predicate_hint_miss_count_delta": "predicate_hint_miss_count",
        "edge_drop_count_delta": "edge_drop_count",
        "cross_class_blocked_count_delta": "cross_class_blocked_count",
        "unsafe_cross_class_blocked_count_delta": "unsafe_cross_class_blocked_count",
        "duplicate_label_collision_count_delta": "duplicate_label_collision_count",
        "conflicting_kind_collision_count_delta": "conflicting_kind_collision_count",
        "do_not_merge_collision_count_delta": "do_not_merge_collision_count",
    }
    return {delta: _number(variant_metrics.get(metric), 0) - _number(baseline_metrics.get(metric), 0) for delta, metric in pairs.items()}


def score_variant_metrics(metrics: Mapping[str, Any]) -> dict[str, Any]:
    components = {
        "known_name_match_count": int(_number(metrics.get("known_name_match_count"), 0)),
        "type_hint_match_count": int(_number(metrics.get("type_hint_match_count"), 0)),
        "combat_encounter_match_count_x2": int(_number(metrics.get("combat_encounter_match_count"), 0)) * 2,
        "predicate_hint_match_count": int(_number(metrics.get("predicate_hint_match_count"), 0)),
        "known_name_miss_count_penalty": -int(_number(metrics.get("known_name_miss_count"), 0)),
        "type_hint_mismatch_count_x2_penalty": -int(_number(metrics.get("type_hint_mismatch_count"), 0)) * 2,
        "combat_encounter_miss_count_x2_penalty": -int(_number(metrics.get("combat_encounter_miss_count"), 0)) * 2,
        "predicate_hint_miss_count_penalty": -int(_number(metrics.get("predicate_hint_miss_count"), 0)),
        "edge_drop_count_penalty": -int(_number(metrics.get("edge_drop_count"), 0)),
        "unsafe_cross_class_blocked_count_x3_penalty": -int(_number(metrics.get("unsafe_cross_class_blocked_count"), 0)) * 3,
        "duplicate_label_collision_count_penalty": -int(_number(metrics.get("duplicate_label_collision_count"), 0)),
        "conflicting_kind_collision_count_x2_penalty": -int(_number(metrics.get("conflicting_kind_collision_count"), 0)) * 2,
        "do_not_merge_collision_count_x3_penalty": -int(_number(metrics.get("do_not_merge_collision_count"), 0)) * 3,
    }
    return {"score": sum(components.values()), "components": components}


def compare_vocabulary_ablation_variants(
    *,
    packet: ContextVocabularyPacket,
    variants: Iterable[VocabularyAblationVariant],
    baseline_variant_name: str = BASELINE_VARIANT,
    comparison_method: str = "vocabulary_ablation_comparison_v1",
) -> VocabularyAblationComparisonResult:
    variant_list = list(variants)
    if not variant_list:
        raise ValueError("at least one vocabulary ablation variant is required")
    by_name = {variant.variant_name: variant for variant in variant_list}
    if len(by_name) != len(variant_list):
        raise ValueError("variant names must be unique")
    if baseline_variant_name not in by_name:
        raise ValueError(f"baseline variant {baseline_variant_name!r} is required")

    ordered_names = [name for name in KNOWN_ABLATION_VARIANTS if name in by_name] + sorted(
        name for name in by_name if name not in KNOWN_ABLATION_VARIANTS
    )
    metrics = {name: summarize_variant_metrics(by_name[name]) for name in ordered_names}
    baseline = metrics[baseline_variant_name]
    deltas = {name: compute_variant_delta(baseline, metrics[name]) for name in ordered_names if name != baseline_variant_name}
    scores = {name: score_variant_metrics(metrics[name]) for name in ordered_names}
    warnings = _comparison_warnings(ordered_names, by_name, baseline_variant_name, metrics)

    best_variant = min(
        ordered_names,
        key=lambda name: (
            -int(scores[name]["score"]),
            -int(metrics[name]["combat_encounter_match_count"]),
            -float(metrics[name]["known_name_pickup_rate"]),
            name,
        ),
    )

    comparison = {
        "comparison_method": comparison_method,
        "packet_id": packet.packet_id,
        "scope": packet.scope,
        "baseline_variant_name": baseline_variant_name,
        "variant_order": ordered_names,
        "metrics_by_variant": metrics,
        "deltas_vs_baseline": deltas,
        "scores_by_variant": scores,
        "best_variant": best_variant,
        "summary": {
            "known_name_pickup_best_variant": _best_by_metric(ordered_names, metrics, "known_name_pickup_rate"),
            "combat_encounter_best_variant": _best_by_metric(ordered_names, metrics, "combat_encounter_match_count"),
            "predicate_hint_best_variant": _best_by_metric(ordered_names, metrics, "predicate_hint_match_count"),
            "safest_collision_variant": _best_by_metric(ordered_names, metrics, "unsafe_cross_class_blocked_count", lower_is_better=True),
            "score_note": SCORE_NOTE,
        },
        "warnings": warnings,
    }
    return VocabularyAblationComparisonResult(comparison=comparison)


def _best_by_metric(names: list[str], metrics: Mapping[str, Mapping[str, Any]], metric: str, *, lower_is_better: bool = False) -> str:
    return min(names, key=lambda name: ((_number(metrics[name].get(metric), 0) if lower_is_better else -_number(metrics[name].get(metric), 0)), name))


def _comparison_warnings(
    ordered_names: list[str],
    by_name: Mapping[str, VocabularyAblationVariant],
    baseline_name: str,
    metrics: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    missing = [name for name in KNOWN_ABLATION_VARIANTS if name not in by_name]
    if missing:
        warnings.append(f"missing expected variants: {', '.join(missing)}")
    baseline = metrics[baseline_name]
    for name in ordered_names:
        variant = by_name[name]
        if variant.extracted_nodes is None:
            warnings.append(f"{name}: no extracted nodes supplied")
        if variant.extracted_edges is None:
            warnings.append(f"{name}: no extracted edges supplied")
        if variant.extraction_run_diagnostics is None:
            warnings.append(f"{name}: no extraction run diagnostics supplied")
        if name == baseline_name:
            continue
        current = metrics[name]
        if current["unsafe_cross_class_blocked_count"] > baseline["unsafe_cross_class_blocked_count"]:
            warnings.append(f"{name}: unsafe cross-class collision regression vs baseline")
        if current["known_name_pickup_rate"] < baseline["known_name_pickup_rate"]:
            warnings.append(f"{name}: lower known-name pickup than baseline")
        if (
            current["duplicate_label_collision_count"] > baseline["duplicate_label_collision_count"]
            or current["conflicting_kind_collision_count"] > baseline["conflicting_kind_collision_count"]
            or current["do_not_merge_collision_count"] > baseline["do_not_merge_collision_count"]
        ):
            warnings.append(f"{name}: collision regression vs baseline")
    return warnings


def render_vocabulary_ablation_comparison_markdown(result: VocabularyAblationComparisonResult) -> str:
    payload = result.to_dict()
    lines = [
        "# Vocabulary ablation comparison",
        "",
        f"Packet: `{payload.get('packet_id', '')}`",
        f"Best variant by heuristic score: `{payload.get('best_variant', '')}`",
        "",
        "| Variant | Score | Known pickup | Combat matched | Predicate matched | Edge drops | Unsafe blocked |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    metrics_by_variant = payload.get("metrics_by_variant", {})
    scores_by_variant = payload.get("scores_by_variant", {})
    for name in payload.get("variant_order", []):
        metrics = metrics_by_variant.get(name, {})
        score = scores_by_variant.get(name, {}).get("score", 0)
        lines.append(
            f"| {name} | {score} | {float(metrics.get('known_name_pickup_rate', 0.0)):.3f} | "
            f"{metrics.get('combat_encounter_match_count', 0)} | {metrics.get('predicate_hint_match_count', 0)} | "
            f"{metrics.get('edge_drop_count', 0)} | {metrics.get('unsafe_cross_class_blocked_count', 0)} |"
        )
    lines.extend(["", "Notes:", f"- {SCORE_NOTE}", f"- {SYNTHETIC_NOTE}"])
    return "\n".join(lines)


def vocabulary_ablation_comparison_to_payload(result: VocabularyAblationComparisonResult) -> dict[str, Any]:
    return result.to_dict()
