"""Estimate how many phase6 coverage misses are recoverable without API ingestion.

This script uses existing facts only. It checks whether missing question target
attributes could be approximated from already-extracted state and timeline signals.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "evals" / "mirathorn_vertical_slice" / "output"
STORE_DIR = OUTPUT_DIR / "phase_d_store"

CANDIDATES_PATH = OUTPUT_DIR / "phase6_candidate_questions.json"
FACTS_PATH = STORE_DIR / "facts.json"
REPORT_PATH = OUTPUT_DIR / "phase6_temporal_recoverability.json"

TEMPORAL_PROXY_ATTRS = {
    "physical_condition",
    "mental_state",
    "operational_status",
    "goals",
    "history",
    "relationship_tags",
    "portrayal_notes",
}

MISSING_ATTR_PROXY_MAP: dict[str, set[str]] = {
    "status": {"physical_condition", "mental_state", "operational_status"},
    "combat_outcome": {"physical_condition", "operational_status", "history", "goals"},
    "event_sequence": {"goals", "history", "operational_status", "relationship_tags"},
    "ritual": {"goals", "history", "operational_status"},
    "methods": {"goals", "operational_status", "portrayal_notes"},
}

TEMPORAL_KEYWORDS = (
    "before",
    "after",
    "then",
    "eventually",
    "end of",
    "at the end",
    "escape",
    "killed",
    "dead",
    "decap",
    "ritual",
    "summon",
    "countdown",
    "deliberation",
    "stall",
    "chase",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _value_text(fact: dict[str, Any]) -> str:
    value = fact.get("value", {})
    label = str(value.get("label", "")).lower()
    normalized = str(value.get("normalized") or "").lower()
    return f"{label} {normalized}".strip()


def _has_temporal_keyword(text: str) -> bool:
    return any(keyword in text for keyword in TEMPORAL_KEYWORDS)


def _build_entity_attr_index(facts: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    index: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for fact in facts:
        entity_id = str(fact.get("subject_entity_id", ""))
        attr = str(fact.get("attribute", ""))
        if not entity_id or not attr:
            continue
        index[entity_id][attr].append(fact)
    return index


def _recoverability_for_missing_pair(
    *,
    entity_id: str,
    missing_attr: str,
    entity_attr_index: dict[str, dict[str, list[dict[str, Any]]]],
    require_asserted_session: bool,
) -> dict[str, Any]:
    entity_facts = entity_attr_index.get(entity_id, {})
    proxy_attrs = MISSING_ATTR_PROXY_MAP.get(missing_attr, set())
    proxy_hits: list[dict[str, Any]] = []

    for proxy_attr in sorted(proxy_attrs):
        for fact in entity_facts.get(proxy_attr, []):
            text = _value_text(fact)
            has_sequence = fact.get("sequence_index_within_session") is not None
            has_asserted = fact.get("asserted_in_session") is not None
            temporal_signal = has_sequence or _has_temporal_keyword(text)
            if require_asserted_session and not has_asserted:
                continue
            if not temporal_signal:
                continue
            proxy_hits.append(
                {
                    "proxy_attribute": proxy_attr,
                    "fact_id": fact.get("fact_id"),
                    "label": fact.get("value", {}).get("label", ""),
                    "sequence_index_within_session": fact.get("sequence_index_within_session"),
                    "asserted_in_session": fact.get("asserted_in_session"),
                }
            )

    return {
        "recoverable": bool(proxy_hits),
        "proxy_hits": proxy_hits[:6],
    }


def run(*, facts_path: Path, report_path: Path, require_asserted_session: bool) -> dict[str, Any]:
    candidates = _read_json(CANDIDATES_PATH)
    facts = _read_json(facts_path)
    entity_attr_index = _build_entity_attr_index(facts)

    missing_pairs = 0
    recoverable_pairs = 0
    by_missing_attr: Counter[str] = Counter()
    recoverable_by_attr: Counter[str] = Counter()
    per_question: list[dict[str, Any]] = []

    for row in candidates:
        missing_details: list[dict[str, Any]] = []
        coverage_details = row.get("coverage_details", [])
        for detail in coverage_details:
            if int(detail.get("fact_count", 0)) > 0:
                continue
            entity_id = str(detail.get("subject_entity_id", ""))
            attr = str(detail.get("attribute", ""))
            missing_pairs += 1
            by_missing_attr[attr] += 1

            recovery = _recoverability_for_missing_pair(
                entity_id=entity_id,
                missing_attr=attr,
                entity_attr_index=entity_attr_index,
                require_asserted_session=require_asserted_session,
            )
            if recovery["recoverable"]:
                recoverable_pairs += 1
                recoverable_by_attr[attr] += 1

            missing_details.append(
                {
                    "subject_entity_id": entity_id,
                    "missing_attribute": attr,
                    "recoverable_via_temporal_proxy": recovery["recoverable"],
                    "proxy_hits": recovery["proxy_hits"],
                }
            )

        if missing_details:
            per_question.append(
                {
                    "id": row.get("id"),
                    "coverage_status": row.get("coverage_status"),
                    "preflight_support_status": row.get("preflight_support_status"),
                    "missing_pairs": len(missing_details),
                    "recoverable_missing_pairs": sum(
                        1 for item in missing_details if item["recoverable_via_temporal_proxy"]
                    ),
                    "missing_details": missing_details,
                }
            )

    facts_with_sequence = sum(1 for fact in facts if fact.get("sequence_index_within_session") is not None)
    facts_with_asserted_session = sum(1 for fact in facts if fact.get("asserted_in_session") is not None)

    report = {
        "totals": {
            "candidate_questions": len(candidates),
            "missing_entity_attribute_pairs": missing_pairs,
            "recoverable_pairs_via_temporal_proxy": recoverable_pairs,
            "recoverable_ratio": 0.0 if missing_pairs == 0 else recoverable_pairs / missing_pairs,
        },
        "temporal_metadata_coverage": {
            "facts_total": len(facts),
            "facts_with_sequence_index_within_session": facts_with_sequence,
            "facts_with_asserted_in_session": facts_with_asserted_session,
            "asserted_session_coverage_ratio": 0.0
            if len(facts) == 0
            else facts_with_asserted_session / len(facts),
        },
        "missing_pairs_by_attribute": dict(by_missing_attr),
        "recoverable_pairs_by_attribute": dict(recoverable_by_attr),
        "question_level": per_question,
        "notes": [
            "No API calls were made; this is derived from existing phase_d_store facts only.",
            "Recoverable means at least one temporal/state proxy fact exists for the entity with sequence or temporal lexical signal.",
            "Low asserted_in_session coverage limits true cross-session transition confidence.",
            f"facts_source: {facts_path}",
            f"require_asserted_session: {require_asserted_session}",
        ],
    }

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze no-API temporal recoverability for Phase 6 candidates.")
    parser.add_argument(
        "--facts",
        type=Path,
        default=FACTS_PATH,
        help="Facts JSON path (defaults to phase_d_store/facts.json).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPORT_PATH,
        help="Output report path.",
    )
    parser.add_argument(
        "--require-asserted-session",
        action="store_true",
        help="Only count proxy hits with non-null asserted_in_session.",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                facts_path=args.facts,
                report_path=args.out,
                require_asserted_session=args.require_asserted_session,
            ),
            indent=2,
        )
    )
