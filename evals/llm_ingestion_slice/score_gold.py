from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EVAL_DIR = ROOT / "evals" / "llm_ingestion_slice"
GOLD_PATH = EVAL_DIR / "gold" / "manual_entity_extraction_gold.json"
DEFAULT_ARTIFACTS_DIR = EVAL_DIR / "output" / "current"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_entity_class(value: Any) -> str:
    raw = _norm(value)
    legacy_map = {
        "npc": "actor",
        "location": "place",
        "faction": "group",
        "item": "object",
        "other": "concept",
    }
    return legacy_map.get(raw, raw)


@dataclass(frozen=True)
class GoldEntityExpectation:
    display_name: str
    entity_class: str
    importance: str
    aliases_suggested: tuple[str, ...]

    @property
    def key(self) -> tuple[str, str]:
        return (_norm(self.display_name), _norm(self.entity_class))


@dataclass(frozen=True)
class StageEntity:
    display_name: str
    entity_class: str
    aliases: tuple[str, ...]


def _iter_gold_expected_entities(gold: dict[str, Any]) -> list[GoldEntityExpectation]:
    rows: list[GoldEntityExpectation] = []
    for source in gold.get("sources", []):
        for segment in source.get("segments", []):
            for entity in segment.get("expected_entities", []):
                rows.append(
                    GoldEntityExpectation(
                        display_name=str(entity.get("display_name", "")),
                        entity_class=_normalize_entity_class(
                            entity.get("entity_class", entity.get("entity_type", ""))
                        ),
                        importance=str(entity.get("importance") or "optional"),
                        aliases_suggested=tuple(str(a) for a in entity.get("aliases_suggested", [])),
                    )
                )
    return rows


def _unique_gold_entities_for_tier(
    gold_entities: list[GoldEntityExpectation],
    tier: str,
) -> list[GoldEntityExpectation]:
    if tier == "core":
        allowed = {"core"}
    elif tier == "core_supporting":
        allowed = {"core", "supporting"}
    else:
        allowed = {"core", "supporting", "optional"}

    dedup: dict[tuple[str, str], GoldEntityExpectation] = {}
    for row in gold_entities:
        if row.importance not in allowed:
            continue
        dedup.setdefault(row.key, row)
    return list(dedup.values())


def _parse_stage_entities(stage_entities: list[dict[str, Any]]) -> list[StageEntity]:
    parsed: list[StageEntity] = []
    for row in stage_entities:
        parsed.append(
            StageEntity(
                display_name=str(row.get("display_name", "")),
                entity_class=_normalize_entity_class(
                    row.get("entity_class", row.get("entity_type", ""))
                ),
                aliases=tuple(str(a) for a in row.get("aliases", [])),
            )
        )
    return parsed


def _entity_match_score(gold_entity: GoldEntityExpectation, stage_entity: StageEntity) -> tuple[int, int]:
    gold_name = _norm(gold_entity.display_name)
    if not gold_name:
        return (0, 0)

    stage_name = _norm(stage_entity.display_name)
    stage_aliases = {_norm(a) for a in stage_entity.aliases if _norm(a)}
    gold_aliases = {_norm(a) for a in gold_entity.aliases_suggested if _norm(a)}
    stage_all_names = {stage_name, *stage_aliases}

    if gold_name in stage_all_names:
        return (3, len(gold_name))
    if any(alias in stage_all_names for alias in gold_aliases):
        best_alias_len = max((len(alias) for alias in gold_aliases if alias in stage_all_names), default=0)
        return (2, best_alias_len)

    if stage_name and (gold_name in stage_name or stage_name in gold_name):
        return (1, min(len(gold_name), len(stage_name)))

    return (0, 0)


def _match_gold_entities_to_stage(
    gold_entities: list[GoldEntityExpectation],
    stage_entities: list[StageEntity],
) -> dict[str, Any]:
    stage_used: set[int] = set()
    matched_gold: list[dict[str, str]] = []
    unmatched_gold: list[str] = []

    for gold_entity in gold_entities:
        best_stage_idx: int | None = None
        best_score: tuple[int, int] = (0, 0)
        for idx, stage_entity in enumerate(stage_entities):
            if idx in stage_used:
                continue
            score = _entity_match_score(gold_entity, stage_entity)
            if score > best_score:
                best_score = score
                best_stage_idx = idx

        if best_stage_idx is None or best_score[0] == 0:
            unmatched_gold.append(gold_entity.display_name)
            continue

        stage_used.add(best_stage_idx)
        matched_gold.append(
            {
                "gold_display_name": gold_entity.display_name,
                "gold_entity_class": gold_entity.entity_class,
                "stage_display_name": stage_entities[best_stage_idx].display_name,
                "stage_entity_class": stage_entities[best_stage_idx].entity_class,
                "match_strength": best_score[0],
            }
        )

    return {
        "matched_gold": matched_gold,
        "unmatched_gold": unmatched_gold,
        "matched_stage_indices": sorted(stage_used),
    }


def _safe_f1(recall: float, precision: float) -> float:
    if recall <= 0.0 or precision <= 0.0:
        return 0.0
    return (2.0 * recall * precision) / (recall + precision)


def _compute_entity_metrics_for_tier(
    *,
    tier: str,
    gold_entities: list[GoldEntityExpectation],
    stage_entities: list[StageEntity],
) -> dict[str, Any]:
    tier_gold = _unique_gold_entities_for_tier(gold_entities, tier)
    match = _match_gold_entities_to_stage(tier_gold, stage_entities)
    matched_gold_count = len(match["matched_gold"])
    gold_count = len(tier_gold)
    stage_count = len(stage_entities)
    matched_stage_count = len(match["matched_stage_indices"])
    recall = float(matched_gold_count) / float(gold_count) if gold_count > 0 else 0.0
    precision = float(matched_stage_count) / float(stage_count) if stage_count > 0 else 0.0
    return {
        "tier": tier,
        "counts": {
            "gold_entities": gold_count,
            "stage_entities": stage_count,
            "matched_gold_entities": matched_gold_count,
            "matched_stage_entities": matched_stage_count,
        },
        "metrics": {
            "recall": recall,
            "precision": precision,
            "f1": _safe_f1(recall, precision),
        },
        "details": match,
    }


def _negative_violations(gold: dict[str, Any], stage_entities: list[StageEntity]) -> list[str]:
    forbidden = {_norm(name) for name in gold["negative_examples"]["must_not_extract_as_entities"]}
    display_names = {_norm(entity.display_name) for entity in stage_entities}
    return sorted(name for name in forbidden if name in display_names)


def _segments_with_temporal_expectations(gold: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in gold.get("sources", []):
        for segment in source.get("segments", []):
            if "expected_fact_temporal" in segment:
                rows.append(
                    {
                        "source_key": source.get("key"),
                        "segment_id": segment.get("segment_id"),
                        "aligns_with_slice_evidence_id": segment.get("aligns_with_slice_evidence_id"),
                        "anchor_substrings": segment.get("anchor_substrings", []),
                        "expected_fact_temporal": segment.get("expected_fact_temporal"),
                    }
                )
    return rows


def _align_segment_to_evidence_ids(
    segment: dict[str, Any],
    stage_chunks: list[dict[str, Any]],
) -> list[str]:
    aligned = segment.get("aligns_with_slice_evidence_id")
    if aligned:
        return [str(aligned)]

    anchors = [_norm(value) for value in segment.get("anchor_substrings", []) if _norm(value)]
    if not anchors:
        return []

    matched: list[str] = []
    for chunk in stage_chunks:
        text = _norm(chunk.get("text"))
        if text and all(anchor in text for anchor in anchors):
            matched.append(str(chunk.get("evidence_id")))
    return matched


def _check_temporal_accuracy(
    *,
    gold: dict[str, Any],
    stage_facts: list[dict[str, Any]],
    stage_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    expectations = _segments_with_temporal_expectations(gold)
    fact_by_evidence: dict[str, list[dict[str, Any]]] = {}
    for fact in stage_facts:
        for evidence_id in fact.get("evidence_ids", []):
            fact_by_evidence.setdefault(str(evidence_id), []).append(fact)

    field_mismatches: list[dict[str, Any]] = []
    checked_fields = 0
    matched_fields = 0
    missing_fact_expectations = 0

    for row in expectations:
        expected = row["expected_fact_temporal"]
        evidence_ids = _align_segment_to_evidence_ids(row, stage_chunks)
        for evidence_id in evidence_ids:
            facts = fact_by_evidence.get(evidence_id, [])
            if not facts:
                missing_fact_expectations += 1
                field_mismatches.append(
                    {
                        "segment_id": row["segment_id"],
                        "evidence_id": evidence_id,
                        "fact_id": None,
                        "field": "__fact_presence__",
                        "expected": ">=1 fact for evidence_id",
                        "actual": "none",
                    }
                )
                continue
            for fact in facts:
                for field in ("asserted_in_session", "sequence_index_within_session"):
                    checked_fields += 1
                    actual = fact.get(field)
                    expected_value = expected.get(field)
                    if actual == expected_value:
                        matched_fields += 1
                    else:
                        field_mismatches.append(
                            {
                                "segment_id": row["segment_id"],
                                "evidence_id": evidence_id,
                                "fact_id": fact.get("fact_id"),
                                "field": field,
                                "expected": expected_value,
                                "actual": actual,
                            }
                        )

    accuracy = float(matched_fields) / float(checked_fields) if checked_fields > 0 else 0.0
    return {
        "counts": {
            "segments_with_temporal_expectations": len(expectations),
            "checked_fields": checked_fields,
            "matched_fields": matched_fields,
            "missing_fact_expectations": missing_fact_expectations,
            "mismatch_count": len(field_mismatches),
        },
        "metrics": {"field_accuracy": accuracy},
        "mismatches": field_mismatches,
    }


def _compute_catalog_recall(gold: dict[str, Any], stage_entities: list[StageEntity]) -> dict[str, Any]:
    catalog_rows = [
        GoldEntityExpectation(
            display_name=str(row.get("display_name", "")),
            entity_class=_normalize_entity_class(
                row.get("entity_class", row.get("entity_type", ""))
            ),
            importance="core",
            aliases_suggested=(),
        )
        for row in gold["slice_evidence_catalog_entities"]["entities"]
    ]
    match = _match_gold_entities_to_stage(catalog_rows, stage_entities)
    total = len(catalog_rows)
    matched = len(match["matched_gold"])
    recall = float(matched) / float(total) if total > 0 else 0.0
    return {
        "counts": {"gold_catalog_entities": total, "matched_catalog_entities": matched},
        "metrics": {"recall": recall},
        "details": match,
    }


def _concept_event_confusion(
    gold_entities: list[GoldEntityExpectation],
    stage_entities: list[StageEntity],
) -> dict[str, Any]:
    """For each gold entity classified as event or concept, check if stage classified it as the other."""
    confusion_pairs: list[dict[str, str]] = []
    confusable_classes = {"event", "concept"}

    gold_deduped = _unique_gold_entities_for_tier(gold_entities, "all")
    match_result = _match_gold_entities_to_stage(gold_deduped, stage_entities)

    for matched in match_result["matched_gold"]:
        gold_class = _norm(matched["gold_entity_class"])
        stage_class = _norm(matched["stage_entity_class"])
        if gold_class in confusable_classes and stage_class in confusable_classes and gold_class != stage_class:
            confusion_pairs.append({
                "display_name": matched["gold_display_name"],
                "gold_class": gold_class,
                "stage_class": stage_class,
            })

    return {
        "confusion_count": len(confusion_pairs),
        "confusion_pairs": confusion_pairs,
    }


def _exclude_path_metrics(
    stage_entities_payload: list[dict[str, Any]],
    excluded_candidates: list[dict[str, Any]] | None,
    gold: dict[str, Any],
) -> dict[str, Any]:
    """Compute false positive rates for entities that should have been excluded."""
    forbidden_names = {_norm(name) for name in gold.get("negative_examples", {}).get("must_not_extract_as_entities", [])}

    stage_names_in_output = {_norm(e.get("display_name", "")) for e in stage_entities_payload}
    false_positives_in_output = sorted(name for name in forbidden_names if name in stage_names_in_output)

    doc_structure_fps = 0
    mechanic_fps = 0
    total_excluded = 0
    if excluded_candidates:
        total_excluded = len(excluded_candidates)
        for c in excluded_candidates:
            reason = _norm(c.get("exclude_reason", ""))
            if reason == "document_structure":
                doc_structure_fps += 1
            elif reason == "game_mechanic":
                mechanic_fps += 1

    heuristic_count = sum(
        1 for e in stage_entities_payload if e.get("extraction_method") == "heuristic"
    )
    llm_count = sum(
        1 for e in stage_entities_payload if e.get("extraction_method", "llm") == "llm"
    )

    return {
        "non_entity_false_positives": false_positives_in_output,
        "non_entity_false_positive_count": len(false_positives_in_output),
        "total_excluded_candidates": total_excluded,
        "document_structure_excluded": doc_structure_fps,
        "game_mechanic_excluded": mechanic_fps,
        "extraction_method_counts": {
            "llm": llm_count,
            "heuristic": heuristic_count,
        },
    }


def _evaluate_gates(
    *,
    tier_metrics: dict[str, Any],
    temporal: dict[str, Any],
    catalog: dict[str, Any],
    negative_violations: list[str],
    min_core_recall: float,
    min_temporal_accuracy: float,
    min_catalog_recall: float,
) -> dict[str, Any]:
    core_recall = float(tier_metrics["core"]["metrics"]["recall"])
    temporal_accuracy = float(temporal["metrics"]["field_accuracy"])
    catalog_recall = float(catalog["metrics"]["recall"])
    gates = [
        {
            "name": "core_entity_recall",
            "pass": core_recall >= min_core_recall,
            "value": core_recall,
            "threshold": min_core_recall,
        },
        {
            "name": "temporal_field_accuracy",
            "pass": temporal_accuracy >= min_temporal_accuracy,
            "value": temporal_accuracy,
            "threshold": min_temporal_accuracy,
        },
        {
            "name": "catalog_entity_recall",
            "pass": catalog_recall >= min_catalog_recall,
            "value": catalog_recall,
            "threshold": min_catalog_recall,
        },
        {
            "name": "negative_entity_violations",
            "pass": len(negative_violations) == 0,
            "value": len(negative_violations),
            "threshold": 0,
        },
    ]
    return {"overall_pass": all(gate["pass"] for gate in gates), "gates": gates}


def _render_summary(report: dict[str, Any]) -> str:
    lines = ["# Gold Scoring Report", ""]
    lines.append(f"OVERALL: {'PASS' if report['pass_fail']['overall_pass'] else 'FAIL'}")
    lines.append("")
    lines.append("## Entity Metrics")
    for tier in ("core", "core_supporting", "all"):
        block = report["entity_metrics"][tier]
        lines.append(
            "- "
            f"{tier}: recall={block['metrics']['recall']:.3f}, "
            f"precision={block['metrics']['precision']:.3f}, "
            f"f1={block['metrics']['f1']:.3f}, "
            f"gold={block['counts']['gold_entities']}, stage={block['counts']['stage_entities']}"
        )
    lines.append("")
    lines.append(
        "## Temporal Accuracy\n"
        f"- field_accuracy={report['temporal']['metrics']['field_accuracy']:.3f}, "
        f"checked_fields={report['temporal']['counts']['checked_fields']}, "
        f"mismatches={report['temporal']['counts']['mismatch_count']}"
    )
    lines.append("")
    lines.append(
        "## Catalog Recall\n"
        f"- recall={report['catalog_recall']['metrics']['recall']:.3f}, "
        f"matched={report['catalog_recall']['counts']['matched_catalog_entities']}/"
        f"{report['catalog_recall']['counts']['gold_catalog_entities']}"
    )
    lines.append("")
    lines.append("## Negative Entity Check")
    if report["negative_examples"]["violations"]:
        lines.append("- violations: " + ", ".join(report["negative_examples"]["violations"]))
    else:
        lines.append("- violations: none")
    return "\n".join(lines)


def score(
    *,
    gold: dict[str, Any],
    stage_entities_payload: list[dict[str, Any]],
    stage_facts: list[dict[str, Any]],
    stage_chunks: list[dict[str, Any]],
    eval_mode: str = "full_ingest",
    min_core_recall: float,
    min_temporal_accuracy: float,
    min_catalog_recall: float,
    excluded_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    stage_entities = _parse_stage_entities(stage_entities_payload)
    gold_entities = _iter_gold_expected_entities(gold)
    tier_metrics = {
        "core": _compute_entity_metrics_for_tier(
            tier="core",
            gold_entities=gold_entities,
            stage_entities=stage_entities,
        ),
        "core_supporting": _compute_entity_metrics_for_tier(
            tier="core_supporting",
            gold_entities=gold_entities,
            stage_entities=stage_entities,
        ),
        "all": _compute_entity_metrics_for_tier(
            tier="all",
            gold_entities=gold_entities,
            stage_entities=stage_entities,
        ),
    }
    temporal = _check_temporal_accuracy(gold=gold, stage_facts=stage_facts, stage_chunks=stage_chunks)
    catalog = _compute_catalog_recall(gold=gold, stage_entities=stage_entities)
    negatives = _negative_violations(gold=gold, stage_entities=stage_entities)
    concept_event = _concept_event_confusion(gold_entities, stage_entities)
    exclude_metrics = _exclude_path_metrics(stage_entities_payload, excluded_candidates, gold)
    pass_fail = _evaluate_gates(
        tier_metrics=tier_metrics,
        temporal=temporal,
        catalog=catalog,
        negative_violations=negatives,
        min_core_recall=min_core_recall,
        min_temporal_accuracy=min_temporal_accuracy,
        min_catalog_recall=min_catalog_recall,
    )
    return {
        "eval_mode": eval_mode,
        "thresholds": {
            "min_core_recall": min_core_recall,
            "min_temporal_accuracy": min_temporal_accuracy,
            "min_catalog_recall": min_catalog_recall,
        },
        "entity_metrics": tier_metrics,
        "catalog_recall": catalog,
        "temporal": temporal,
        "negative_examples": {"violations": negatives},
        "concept_event_confusion": concept_event,
        "exclude_path_metrics": exclude_metrics,
        "pass_fail": pass_fail,
    }


def main(
    artifacts_dir: Path | None = None,
    *,
    eval_mode: str = "full_ingest",
    min_core_recall: float = 0.0,
    min_temporal_accuracy: float = 1.0,
    min_catalog_recall: float = 1.0,
) -> int:
    if artifacts_dir is None:
        artifacts_dir = DEFAULT_ARTIFACTS_DIR

    gold = _load_json(GOLD_PATH)
    stage_entities = _load_json(artifacts_dir / "stage_entities.json")
    stage_facts = _load_json(artifacts_dir / "stage_facts.json")
    stage_chunks = _load_json(artifacts_dir / "stage_chunks.json")

    excluded_path = artifacts_dir / "excluded_candidates.json"
    excluded_candidates = _load_json(excluded_path) if excluded_path.exists() else None

    report = score(
        gold=gold,
        stage_entities_payload=stage_entities,
        stage_facts=stage_facts,
        stage_chunks=stage_chunks,
        eval_mode=eval_mode,
        min_core_recall=min_core_recall,
        min_temporal_accuracy=min_temporal_accuracy,
        min_catalog_recall=min_catalog_recall,
        excluded_candidates=excluded_candidates,
    )
    _write_json(artifacts_dir / "gold_score.json", report)
    print(_render_summary(report))
    return 0 if report["pass_fail"]["overall_pass"] else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score stage artifacts against manual gold.")
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=DEFAULT_ARTIFACTS_DIR,
        help="Path containing stage_entities.json, stage_facts.json, stage_chunks.json",
    )
    parser.add_argument("--min-core-recall", type=float, default=0.0)
    parser.add_argument("--min-temporal-accuracy", type=float, default=1.0)
    parser.add_argument("--min-catalog-recall", type=float, default=1.0)
    parser.add_argument(
        "--eval-mode",
        type=str,
        default="full_ingest",
        help="Label for evaluation context (for example: deterministic_slice, full_ingest).",
    )
    parser.add_argument(
        "--run-slice-first",
        action="store_true",
        help="Run evals.llm_ingestion_slice.run_slice.main() before scoring.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.run_slice_first:
        run_slice_module = __import__("evals.llm_ingestion_slice.run_slice", fromlist=["main"])
        run_exit_code = int(run_slice_module.main())
        if run_exit_code != 0:
            raise SystemExit(run_exit_code)
    raise SystemExit(
        main(
            artifacts_dir=args.artifacts_dir,
            eval_mode=args.eval_mode,
            min_core_recall=args.min_core_recall,
            min_temporal_accuracy=args.min_temporal_accuracy,
            min_catalog_recall=args.min_catalog_recall,
        )
    )
