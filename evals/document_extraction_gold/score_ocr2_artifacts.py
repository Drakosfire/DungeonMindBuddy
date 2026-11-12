#!/usr/bin/env python3
"""Score retained page-level OCR artifacts against source-pinned PDF gold.

This is an offline evaluator: it never runs OCR or changes a source. It reports
only metrics supported by the retained artifact shape. Page OCR can establish
source identity and page location, but not a selected-region location or visual
map coverage. Missing classification/structure outputs are reported as
unavailable instead of being inferred from successful transcription.

Example:
  python3 evals/document_extraction_gold/score_ocr2_artifacts.py \
    --artifact-root conks=/path/to/conks/output \
    --artifact-root sheep=/path/to/sheep/output
"""

from __future__ import annotations

import argparse
from collections import Counter
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any


GOLD_PATH = Path(__file__).with_name("adventure_pdf_source_gold_v1.json")


def normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    if text.strip() in {"-", "–", "—", "−"}:
        return "dash"
    return "".join(char for char in text if char.isalnum())


def tokens(value: str) -> list[str]:
    return [normalize(token) for token in re.findall(r"[\w]+(?:['’][\w]+)?", value)]


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def _artifact_roots(values: list[str]) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for value in values:
        source_id, separator, raw_path = value.partition("=")
        if not separator or not source_id or not raw_path:
            raise ValueError(f"Invalid --artifact-root {value!r}; expected SOURCE_ID=PATH")
        if source_id in roots:
            raise ValueError(f"Duplicate artifact root for source {source_id!r}")
        roots[source_id] = Path(raw_path).expanduser().resolve()
    return roots


def _page_artifact(root: Path, page_index: int) -> tuple[Path, dict[str, Any]] | None:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(root.glob("**/stageA.page.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("page_index") == page_index:
            matches.append((path, data))
    if len(matches) > 1:
        raise ValueError(
            f"Multiple OCR page artifacts for page_index={page_index} under {root}; "
            "pass a narrower artifact root"
        )
    return matches[0] if matches else None


def _region_artifact(root: Path, case_id: str) -> tuple[Path, dict[str, Any]] | None:
    """Find one retained crop result by its gold case id."""
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(root.glob(f"**/{case_id}/result.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("case_id") == case_id:
            matches.append((path, data))
    if len(matches) > 1:
        raise ValueError(
            f"Multiple OCR region artifacts for case_id={case_id!r} under {root}; "
            "pass a narrower artifact root"
        )
    return matches[0] if matches else None


def _region_run_metadata(path: Path) -> dict[str, Any] | None:
    """Read the run manifest adjacent to a retained region artifact, if present."""
    manifest = path.parent.parent / "run.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _expected_field_values(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            result.extend(_expected_field_values(child, f"{prefix}.{key}" if prefix else key))
    elif value is not None and str(value).strip():
        result.append((prefix, str(value)))
    return result


def _contains_field_value(text: str, value: str) -> bool:
    if str(value).strip() in {"-", "–", "—", "−"}:
        return bool(re.search(r"(?<![\w])[-–—−](?![\w])", text))
    return normalize(value) in normalize(text)


def _table_metrics(markdown: str, case: dict[str, Any]) -> dict[str, Any]:
    lines = markdown.splitlines()
    title = normalize(case["block_title"])
    start: int | None = None
    heading_level = 0
    for index, line in enumerate(lines):
        match = re.match(r"^\s*(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match and normalize(match.group(2)) == title:
            start = index + 1
            heading_level = len(match.group(1))
            break
    if start is None:
        return {
            "matching_tables": 0,
            "header_match": False,
            "rows_matched": 0,
            "rows_expected": len(case["rows"]),
            "reason": "gold table heading was not found in the OCR text",
        }
    end = len(lines)
    for index in range(start, len(lines)):
        match = re.match(r"^\s*(#{1,6})\s+", lines[index])
        if match and len(match.group(1)) <= heading_level:
            end = index
            break
    section = "\n".join(lines[start:end])

    parser = _TableParser()
    parser.feed(section)
    expected_columns = [normalize(column) for column in case["columns"]]
    candidates = [
        table for table in parser.tables
        if table and [normalize(cell) for cell in table[0]] == expected_columns
    ]
    if len(candidates) != 1:
        return {
            "matching_tables": len(candidates),
            "header_match": False,
            "rows_matched": 0,
            "rows_expected": len(case["rows"]),
        }

    rows = [[normalize(cell) for cell in row] for row in candidates[0][1:]]
    matched = 0
    missing_rows: list[str] = []
    for expected in case["rows"]:
        values = [str(expected.get("roll", "")), expected.get("name", ""), expected.get("notes", "")]
        target = [normalize(value) for value in values]
        if target in rows:
            matched += 1
        else:
            missing_rows.append(f"{expected.get('roll')}: {expected.get('name')}")
    return {
        "matching_tables": 1,
        "header_match": True,
        "rows_matched": matched,
        "rows_expected": len(case["rows"]),
        "missing_rows": missing_rows,
    }


def _score_region(case: dict[str, Any], path: Path, result: dict[str, Any], expected_hash: str) -> dict[str, Any]:
    """Score region-level OCR without treating OCR markup as a typed candidate."""
    text = str(result.get("text", ""))
    observed_region = result.get("region")
    expected_region = case.get("source_region")
    region_match = (
        isinstance(observed_region, dict)
        and isinstance(expected_region, dict)
        and all(
            observed_region.get(key) == expected_region.get(key)
            for key in ("coordinate_system", "x", "y", "width", "height")
        )
    )
    run_metadata = _region_run_metadata(path)
    run_source_hash = (
        run_metadata.get("input_pdf_sha256", {}).get(case["source_id"])
        if run_metadata and isinstance(run_metadata.get("input_pdf_sha256"), dict)
        else None
    )
    base: dict[str, Any] = {
        "case_id": case["case_id"],
        "block_type_expected": case["block_type"],
        "page_index_expected": case["physical_page"] - 1,
        "artifact_status": "present",
        "artifact": str(path),
        "inference_elapsed_sec": result.get("elapsed_seconds"),
        "model_id": run_metadata.get("model_id") if run_metadata else None,
        "model_snapshot": run_metadata.get("model_snapshot") if run_metadata else None,
        "classification": {"status": "unavailable", "reason": "OCR region markers are not a reviewed candidate classification"},
        "source_location": {
            "source_hash_match": result.get("source_pdf_sha256") == expected_hash,
            "run_manifest_hash_match": run_source_hash == expected_hash if run_source_hash else None,
            "page_match": result.get("page_index") == case["physical_page"] - 1,
            "region_match": region_match,
        },
    }
    if result.get("case_id") != case["case_id"] or result.get("source_id") != case["source_id"]:
        base["artifact_status"] = "identity_mismatch"
        return base

    markers = {item.casefold() for item in re.findall(r"<\|ref\|>(.*?)<\|/ref\|>", text, flags=re.I)}
    expected_marker = {"prose_region": "text", "table": "table", "map": "map", "statblock": "statblock"}[case["block_type"]]
    observed_marker = "image" if "image" in markers else "table" if "table" in markers else "text" if "text" in markers else None
    if expected_marker in {"text", "table"}:
        base["classification"] = {
            "status": "matched" if observed_marker == expected_marker else "mismatched",
            "observed": observed_marker,
            "expected": expected_marker,
            "scope": "OCR region marker only; not a reviewed or typed candidate",
        }
    elif expected_marker == "map":
        base["classification"] = {
            "status": "mismatched" if observed_marker else "unavailable",
            "observed": observed_marker,
            "expected": "map",
            "reason": "OCR image marker does not distinguish maps from other images",
        }

    if case["block_type"] == "prose_region":
        expected_tokens = Counter(tokens(case["expected_text"]))
        observed_tokens = Counter(tokens(text))
        matched = sum((expected_tokens & observed_tokens).values())
        total = sum(expected_tokens.values())
        base["transcription"] = {
            "normalized_exact_match": normalize(case["expected_text"]) in normalize(text),
            "expected_tokens_matched": matched,
            "expected_tokens_total": total,
            "scope": "selected OCR region",
        }
    elif case["block_type"] == "statblock":
        fields = _expected_field_values(case["expected_fields"])
        found = [key for key, value in fields if _contains_field_value(text, value)]
        missing = [key for key, value in fields if not _contains_field_value(text, value)]
        base["transcription"] = {
            "expected_field_values_present": len(found),
            "expected_field_values_total": len(fields),
            "missing_field_values": missing,
            "scope": "selected OCR region",
            "note": "Presence only; this does not verify value-to-label binding.",
        }
        base["structure"] = {
            "status": "unavailable",
            "reason": "OCR output is Markdown/HTML; no validated typed statblock candidate",
        }
    elif case["block_type"] == "table":
        table = _table_metrics(text, case)
        base["structure"] = table
        base["transcription"] = {
            "expected_rows_transcribed": table["rows_matched"],
            "expected_rows_total": table["rows_expected"],
            "scope": "selected OCR region",
        }
    elif case["block_type"] == "map":
        base["visual_coverage"] = {
            "status": "unscored",
            "expected_features": len(case.get("expected_visual_features", [])),
            "reason": "OCR text output does not describe or score map features",
        }
    return base


def score_case(case: dict[str, Any], roots: dict[str, Path], sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source_id = case["source_id"]
    root = roots.get(source_id)
    base: dict[str, Any] = {
        "case_id": case["case_id"],
        "block_type_expected": case["block_type"],
        "page_index_expected": case["physical_page"] - 1,
        "classification": {"status": "unavailable", "reason": "no region-level candidate label is available"},
        "source_location": {"page_match": False, "region_match": "unavailable"},
    }
    if root is None:
        base["artifact_status"] = "missing_source_root"
        return base

    region = _region_artifact(root, case["case_id"])
    if region is not None:
        return _score_region(case, region[0], region[1], sources[source_id]["pdf_sha256"])

    artifact = _page_artifact(root, case["physical_page"] - 1)
    if artifact is None:
        base["artifact_status"] = "missing_page_artifact"
        return base

    artifact_path, page = artifact
    markdown = page.get("raw_markdown", "")
    page_location = page.get("page_index") == case["physical_page"] - 1
    pdf_path = Path(str(page.get("source_pdf", ""))).expanduser()
    actual_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest() if pdf_path.is_file() else None
    expected_hash = sources[source_id]["pdf_sha256"]
    base.update({
        "artifact_status": "present",
        "artifact": str(artifact_path),
        "model_id": page.get("model_id"),
        "content_version": page.get("content_version"),
        "inference_elapsed_sec": page.get("inference_elapsed_sec"),
        "source_location": {
            "source_hash_match": actual_hash == expected_hash,
            "page_match": page_location,
            "region_match": "unavailable: artifact is page-level OCR, not a region candidate",
        },
    })

    if case["block_type"] == "prose_region":
        expected = case["expected_text"]
        expected_tokens = Counter(tokens(expected))
        observed_tokens = Counter(tokens(markdown))
        matched = sum((expected_tokens & observed_tokens).values())
        total = sum(expected_tokens.values())
        base["transcription"] = {
            "normalized_exact_match": normalize(expected) in normalize(markdown),
            "expected_tokens_matched": matched,
            "expected_tokens_total": total,
            "scope": "whole-page OCR text; region was not isolated",
        }
    elif case["block_type"] == "statblock":
        fields = _expected_field_values(case["expected_fields"])
        found = [key for key, value in fields if _contains_field_value(markdown, value)]
        missing = [key for key, value in fields if not _contains_field_value(markdown, value)]
        base["transcription"] = {
            "expected_field_values_present": len(found),
            "expected_field_values_total": len(fields),
            "missing_field_values": missing,
            "scope": "whole-page OCR text; region was not isolated",
            "note": "Presence only; this does not verify value-to-label binding.",
        }
        base["structure"] = {
            "status": "unavailable",
            "reason": "page OCR output does not provide a typed statblock candidate",
        }
    elif case["block_type"] == "table":
        table = _table_metrics(markdown, case)
        base["structure"] = table
        base["transcription"] = {
            "expected_rows_transcribed": table["rows_matched"],
            "expected_rows_total": table["rows_expected"],
            "scope": "heading-scoped table within whole-page OCR text; no region coordinates",
        }
    elif case["block_type"] == "map":
        base["visual_coverage"] = {
            "status": "unscored",
            "expected_features": len(case.get("expected_visual_features", [])),
            "reason": "retained artifact is OCR page text, not a map-feature description",
        }

    # The retained AST and evidence-unit files describe page structure, not a
    # geometrically selected region. Record only what the artifact exposes.
    ast_path = artifact_path.with_name("stageA.surface.ast.json")
    units_path = artifact_path.with_name("stageB.evidence_units.json")
    if ast_path.is_file():
        ast = json.loads(ast_path.read_text(encoding="utf-8"))
        base["page_structure"] = {"node_count": ast.get("node_count"), "table_count": ast.get("table_count")}
    if units_path.is_file():
        units = json.loads(units_path.read_text(encoding="utf-8")).get("units", [])
        title = case["block_title"].split("—", 1)[0].strip()
        observed_types = sorted({
            unit.get("unit_type", "unknown")
            for unit in units
            if normalize(title) and normalize(title) in normalize(unit.get("text", ""))
        })
        if case["block_type"] == "map":
            base["classification"] = {
                "status": "unavailable",
                "observed_page_unit_types": sorted({unit.get("unit_type", "unknown") for unit in units}),
                "reason": "page text units do not classify or describe the selected map region",
            }
        elif observed_types:
            expected_type = {"prose_region": "prose"}.get(case["block_type"], case["block_type"])
            matched_type = expected_type in observed_types
            base["classification"] = {
                "status": "matched" if matched_type else "mismatched",
                "observed_unit_types_for_title": observed_types,
                "scope": "title-matched page unit; not region-bound",
            }
        base["page_structure"] = {
            **base.get("page_structure", {}),
            "evidence_unit_types": dict(sorted(Counter(unit.get("unit_type", "unknown") for unit in units).items())),
        }
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=GOLD_PATH, help="source-pinned gold JSON")
    parser.add_argument(
        "--artifact-root", action="append", default=[], metavar="SOURCE_ID=PATH",
        help="retained OCR artifact root; repeat once per gold source",
    )
    args = parser.parse_args()
    try:
        roots = _artifact_roots(args.artifact_root)
        gold = json.loads(args.gold.read_text(encoding="utf-8"))
        results = [score_case(case, roots, {item["source_id"]: item for item in gold["sources"]}) for case in gold["cases"]]
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"scoring failed: {exc}", file=sys.stderr)
        return 2

    report = {
        "dataset_id": gold["dataset_id"],
        "evaluation_kind": "offline_retained_artifacts",
        "qualification": "evidence_only_not_acceptance",
        "provider_calls": 0,
        "cases": results,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    invalid = any(
        case.get("artifact_status") != "present"
        or not case.get("source_location", {}).get("source_hash_match")
        or not case.get("source_location", {}).get("page_match")
        or case.get("source_location", {}).get("region_match") is False
        or case.get("source_location", {}).get("run_manifest_hash_match") is False
        for case in results
    )
    return 1 if invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
