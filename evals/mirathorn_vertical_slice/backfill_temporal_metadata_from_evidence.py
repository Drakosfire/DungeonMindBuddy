"""Backfill temporal metadata in facts from existing evidence units (no API calls)."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "evals" / "mirathorn_vertical_slice" / "output"
STORE_DIR = OUTPUT_DIR / "phase_d_store"

FACTS_PATH = STORE_DIR / "facts.json"
EVIDENCE_PATH = STORE_DIR / "evidence_units.json"
OUT_FACTS_PATH = STORE_DIR / "facts_temporal_backfilled.json"
OUT_REPORT_PATH = OUTPUT_DIR / "phase6_temporal_backfill_report.json"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_evidence_lookup(evidence_units: list[dict[str, Any]]) -> dict[str, dict[str, int | None]]:
    lookup: dict[str, dict[str, int | None]] = {}
    for unit in evidence_units:
        evidence_id = str(unit.get("evidence_id", ""))
        if not evidence_id:
            continue
        inferred = _to_int_or_none(unit.get("document_session"))
        if inferred is None:
            inferred = _to_int_or_none(unit.get("inferred_session"))
        source_order = _to_int_or_none(unit.get("source_order_index"))
        lookup[evidence_id] = {
            "asserted_in_session": inferred,
            "sequence_index_within_session": source_order,
        }
    return lookup


def _derive_fact_temporal_fields(
    fact: dict[str, Any],
    evidence_lookup: dict[str, dict[str, int | None]],
) -> tuple[int | None, int | None]:
    evidence_ids = [str(eid) for eid in fact.get("evidence_ids", []) if eid]
    session_candidates: list[int] = []
    sequence_candidates: list[int] = []

    for evidence_id in evidence_ids:
        meta = evidence_lookup.get(evidence_id)
        if not meta:
            continue
        session_value = meta.get("asserted_in_session")
        if session_value is not None:
            session_candidates.append(session_value)
        sequence_value = meta.get("sequence_index_within_session")
        if sequence_value is not None:
            sequence_candidates.append(sequence_value)

    derived_session = None
    if session_candidates:
        # Majority vote; tie-break by smallest numeric session.
        counts = Counter(session_candidates)
        top_count = max(counts.values())
        winners = sorted(session for session, count in counts.items() if count == top_count)
        derived_session = winners[0]

    derived_sequence = min(sequence_candidates) if sequence_candidates else None
    return derived_session, derived_sequence


def run(*, facts_path: Path, evidence_path: Path, out_facts_path: Path, out_report_path: Path) -> dict[str, Any]:
    facts = _read_json(facts_path)
    evidence_units = _read_json(evidence_path)
    evidence_lookup = _build_evidence_lookup(evidence_units)

    updated_facts: list[dict[str, Any]] = []
    asserted_filled = 0
    sequence_filled = 0

    for fact in facts:
        row = dict(fact)
        current_asserted = _to_int_or_none(row.get("asserted_in_session"))
        current_sequence = _to_int_or_none(row.get("sequence_index_within_session"))
        derived_asserted, derived_sequence = _derive_fact_temporal_fields(row, evidence_lookup)

        if current_asserted is None and derived_asserted is not None:
            row["asserted_in_session"] = derived_asserted
            asserted_filled += 1
        if current_sequence is None and derived_sequence is not None:
            row["sequence_index_within_session"] = derived_sequence
            sequence_filled += 1

        updated_facts.append(row)

    out_facts_path.write_text(json.dumps(updated_facts, indent=2), encoding="utf-8")

    original_asserted = sum(1 for fact in facts if _to_int_or_none(fact.get("asserted_in_session")) is not None)
    updated_asserted = sum(
        1 for fact in updated_facts if _to_int_or_none(fact.get("asserted_in_session")) is not None
    )
    original_sequence = sum(
        1 for fact in facts if _to_int_or_none(fact.get("sequence_index_within_session")) is not None
    )
    updated_sequence = sum(
        1
        for fact in updated_facts
        if _to_int_or_none(fact.get("sequence_index_within_session")) is not None
    )

    report = {
        "facts_source": str(facts_path),
        "evidence_source": str(evidence_path),
        "output_facts": str(out_facts_path),
        "facts_total": len(facts),
        "asserted_in_session": {
            "before_non_null": original_asserted,
            "after_non_null": updated_asserted,
            "filled_count": asserted_filled,
        },
        "sequence_index_within_session": {
            "before_non_null": original_sequence,
            "after_non_null": updated_sequence,
            "filled_count": sequence_filled,
        },
        "notes": [
            "No API calls were made.",
            "asserted_in_session is inferred from evidence document_session, then inferred_session.",
            "sequence_index_within_session backfills from minimum source_order_index among evidence_ids.",
        ],
    }
    out_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill fact temporal metadata from evidence units.")
    parser.add_argument("--facts", type=Path, default=FACTS_PATH, help="Input facts JSON path.")
    parser.add_argument("--evidence", type=Path, default=EVIDENCE_PATH, help="Input evidence units JSON path.")
    parser.add_argument("--out-facts", type=Path, default=OUT_FACTS_PATH, help="Output patched facts JSON path.")
    parser.add_argument("--out-report", type=Path, default=OUT_REPORT_PATH, help="Output report JSON path.")
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                facts_path=args.facts,
                evidence_path=args.evidence,
                out_facts_path=args.out_facts,
                out_report_path=args.out_report,
            ),
            indent=2,
        )
    )
