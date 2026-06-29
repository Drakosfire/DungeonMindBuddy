"""Validate the no-LLM Graph Memory baseline case manifest."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "baseline_cases.json"

REQUIRED_TOP_LEVEL_FIELDS = {
    "version",
    "status",
    "workstream",
    "purpose",
    "cases",
}
REQUIRED_CASE_FIELDS = {
    "case_id",
    "title",
    "failure_family",
    "current_risk",
    "why_graph_native",
    "future_graph_expectation",
    "must_preserve",
    "must_improve_or_measure",
    "notes",
}
LIST_CASE_FIELDS = {
    "must_preserve",
    "must_improve_or_measure",
    "known_routes",
    "known_entities",
    "candidate_source_artifacts",
    "expected_future_trace",
}
NON_BLANK_CASE_FIELDS = {"case_id", "title", "failure_family"}


def _is_blank(value: Any) -> bool:
    return not isinstance(value, str) or not value.strip()


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    """Return validation errors for a loaded baseline case manifest."""
    errors: list[str] = []

    missing_top_level = sorted(REQUIRED_TOP_LEVEL_FIELDS - manifest.keys())
    for field in missing_top_level:
        errors.append(f"missing top-level field: {field}")

    cases = manifest.get("cases")
    if not isinstance(cases, list):
        errors.append("top-level field 'cases' must be a list")
        return errors
    if not cases:
        errors.append("top-level field 'cases' must be non-empty")
        return errors

    case_ids: list[str] = []
    for index, case in enumerate(cases):
        label = f"case[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{label} must be an object")
            continue

        case_id = case.get("case_id")
        if isinstance(case_id, str):
            case_ids.append(case_id)
        missing_case_fields = sorted(REQUIRED_CASE_FIELDS - case.keys())
        for field in missing_case_fields:
            errors.append(f"{label} missing required field: {field}")

        for field in NON_BLANK_CASE_FIELDS:
            if _is_blank(case.get(field)):
                errors.append(f"{label} field {field!r} must be a non-blank string")

        for field in sorted(LIST_CASE_FIELDS & case.keys()):
            if not isinstance(case[field], list):
                errors.append(f"{label} field {field!r} must be a list")

    duplicate_ids = sorted(
        case_id for case_id, count in Counter(case_ids).items() if count > 1
    )
    for case_id in duplicate_ids:
        errors.append(f"duplicate case_id: {case_id}")

    return errors


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    """Load a JSON baseline case manifest."""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a JSON object")
    return data


def main() -> int:
    print("Graph Memory baseline case validation")

    if not MANIFEST_PATH.is_file():
        print("- manifest: missing")
        print("- baseline case manifest: blocked")
        return 1

    print("- manifest: found")

    try:
        manifest = load_manifest()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"- manifest load: failed ({exc})")
        print("- baseline case manifest: blocked")
        return 1

    cases = manifest.get("cases")
    case_count = len(cases) if isinstance(cases, list) else 0
    errors = validate_manifest(manifest)
    duplicate_errors = [error for error in errors if error.startswith("duplicate case_id:")]
    required_errors = [error for error in errors if not error.startswith("duplicate case_id:")]

    print(f"- cases: {case_count}")
    print(f"- duplicate case ids: {'none' if not duplicate_errors else 'blocked'}")
    print(f"- required fields: {'ok' if not required_errors else 'blocked'}")

    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        print("- baseline case manifest: blocked")
        return 1

    print("- baseline case manifest: ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
