"""Backfill evidence-unit session metadata from existing corpus/index hints (no API)."""

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

EVIDENCE_PATH = STORE_DIR / "evidence_units.json"
INGEST_INDEX_PATH = STORE_DIR / "ingest_index.json"
OUT_EVIDENCE_PATH = STORE_DIR / "evidence_units_session_backfilled.json"
OUT_REPORT_PATH = OUTPUT_DIR / "phase6_evidence_session_backfill_report.json"

SESSION_RE = re.compile(r"\bsession\s*[:#-]?\s*(\d+)\b", re.IGNORECASE)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_session_from_text(text: str) -> int | None:
    match = SESSION_RE.search(text or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _extract_frontmatter_session(markdown_path: Path) -> int | None:
    try:
        raw = markdown_path.read_text(encoding="utf-8")
    except Exception:
        return None
    if not raw.startswith("---\n"):
        return None
    end = raw.find("\n---", 4)
    if end == -1:
        return None
    frontmatter = raw[4:end]
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() == "session":
            return _to_int_or_none(value.strip().strip('"'))
    return None


def _build_document_source_map(ingest_index: dict[str, Any]) -> dict[str, list[str]]:
    by_doc_id: dict[str, list[str]] = defaultdict(list)
    for _key, payload in ingest_index.items():
        if not isinstance(payload, dict):
            continue
        doc_id = str(payload.get("document_id", ""))
        source_path = str(payload.get("source_path", ""))
        if doc_id and source_path:
            by_doc_id[doc_id].append(source_path)
    return by_doc_id


def run(
    *,
    evidence_path: Path,
    ingest_index_path: Path,
    out_evidence_path: Path,
    out_report_path: Path,
) -> dict[str, Any]:
    evidence_units = _read_json(evidence_path)
    ingest_index = _read_json(ingest_index_path)
    source_map = _build_document_source_map(ingest_index)

    # Build optional doc_session hints from source markdown frontmatter.
    document_frontmatter_session: dict[str, int] = {}
    for doc_id, source_paths in source_map.items():
        for source_path in source_paths:
            path = Path(source_path)
            if not path.is_absolute():
                path = PROJECT_ROOT / source_path
            session = _extract_frontmatter_session(path)
            if session is not None:
                document_frontmatter_session[doc_id] = session
                break

    updated: list[dict[str, Any]] = []
    fill_reason_counts: Counter[str] = Counter()

    before_inferred = sum(1 for unit in evidence_units if _to_int_or_none(unit.get("inferred_session")) is not None)
    before_document = sum(1 for unit in evidence_units if _to_int_or_none(unit.get("document_session")) is not None)

    for unit in evidence_units:
        row = dict(unit)
        inferred = _to_int_or_none(row.get("inferred_session"))
        document_session = _to_int_or_none(row.get("document_session"))
        if inferred is not None:
            updated.append(row)
            continue

        doc_id = str(row.get("document_id", ""))
        section_path = row.get("section_path", []) or []
        section_blob = " | ".join(str(part) for part in section_path)
        title = str(row.get("document_title", ""))
        text = str(row.get("text", ""))
        source_path_blob = " ".join(source_map.get(doc_id, []))

        inferred_candidate = None
        reason = ""

        if document_session is not None:
            inferred_candidate = document_session
            reason = "from_document_session"
        elif doc_id in document_frontmatter_session:
            inferred_candidate = document_frontmatter_session[doc_id]
            reason = "from_source_frontmatter"
        else:
            for candidate_text, candidate_reason in (
                (section_blob, "from_section_path"),
                (title, "from_document_title"),
                (source_path_blob, "from_source_path"),
                (text[:300], "from_text_prefix"),
            ):
                session = _extract_session_from_text(candidate_text)
                if session is not None:
                    inferred_candidate = session
                    reason = candidate_reason
                    break

        if inferred_candidate is not None:
            row["inferred_session"] = inferred_candidate
            fill_reason_counts[reason] += 1
        updated.append(row)

    after_inferred = sum(1 for unit in updated if _to_int_or_none(unit.get("inferred_session")) is not None)
    after_document = sum(1 for unit in updated if _to_int_or_none(unit.get("document_session")) is not None)

    out_evidence_path.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    report = {
        "evidence_source": str(evidence_path),
        "ingest_index_source": str(ingest_index_path),
        "output_evidence": str(out_evidence_path),
        "evidence_units_total": len(evidence_units),
        "inferred_session": {
            "before_non_null": before_inferred,
            "after_non_null": after_inferred,
            "filled_count": max(0, after_inferred - before_inferred),
        },
        "document_session": {
            "before_non_null": before_document,
            "after_non_null": after_document,
        },
        "fill_reason_counts": dict(fill_reason_counts),
        "notes": [
            "No API calls were made.",
            "Backfill priority: document_session -> source frontmatter -> section/title/path/text regex.",
            "Regex pattern: session <number> (case-insensitive, tolerant punctuation).",
        ],
    }
    out_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill inferred_session in evidence units without API.")
    parser.add_argument("--evidence", type=Path, default=EVIDENCE_PATH, help="Input evidence units JSON.")
    parser.add_argument("--ingest-index", type=Path, default=INGEST_INDEX_PATH, help="Input ingest index JSON.")
    parser.add_argument("--out-evidence", type=Path, default=OUT_EVIDENCE_PATH, help="Output evidence JSON.")
    parser.add_argument("--out-report", type=Path, default=OUT_REPORT_PATH, help="Output report JSON.")
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                evidence_path=args.evidence,
                ingest_index_path=args.ingest_index,
                out_evidence_path=args.out_evidence,
                out_report_path=args.out_report,
            ),
            indent=2,
        )
    )
