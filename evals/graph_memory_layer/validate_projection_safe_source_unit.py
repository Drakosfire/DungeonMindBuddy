from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "projection_safe_source_unit_minimal.json"

EXPECTED_SCHEMA = "dmb_projection_safe_source_unit_fixture_v0"
EXPECTED_VERSION = "0.1"
REQUIRED_PAYLOAD_FIELDS = {
    "adapter_key",
    "ref_id",
    "label",
    "source_anchor",
    "source_ref",
    "provenance",
    "evidence_role",
    "authority_state",
    "visibility_state",
    "lifecycle_state",
    "canon_state",
}
REQUIRED_SOURCE_ANCHOR_FIELDS = {"source_artifact_id", "source_anchor_id", "source_kind", "source_layer", "locator"}
REQUIRED_LOCATOR_FIELDS = {"locator_id", "scheme", "value"}
CANON_STATES = {
    "played_canon",
    "planning_scaffold",
    "generated_candidate",
    "candidate_extraction",
    "diagnostic_only",
    "reference_only",
    "unknown",
}
EVIDENCE_ROLES = {
    "source_evidence",
    "navigation_hint",
    "derived_summary",
    "diagnostic_only",
    "reference_tool",
    "not_evidence",
}
AUTHORITY_STATES = {"system_derived", "human_authored", "mixed", "unknown"}
VISIBILITY_STATES = {"internal_diagnostic", "surface_safe", "hidden", "unknown"}
LIFECYCLE_STATES = {"candidate", "active", "deprecated", "rejected", "unknown"}
FORBIDDEN_INTERNALS = ("_normalized/", "_breadcrumbed/", ".records_meta.jsonl", "corpus_impact")
FORBIDDEN_TEXT_FIELDS = {"lexical_plain", "full_text", "markdown_body", "raw_text", "recap_text"}
ABSOLUTE_PATH_PATTERN = re.compile(r"^/[A-Za-z0-9._~/-]*")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_fixture() -> dict[str, Any]:
    _require(FIXTURE_PATH.is_file(), "fixture missing")
    with FIXTURE_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    _require(isinstance(data, dict), "fixture must be a JSON object")
    return data


def _walk(value: Any, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any]]:
    entries = [(path, value)]
    if isinstance(value, dict):
        for key, child in value.items():
            entries.extend(_walk(child, (*path, key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            entries.extend(_walk(child, (*path, str(index))))
    return entries


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _require_no_forbidden_payload_values(payload: dict[str, Any]) -> None:
    for path, value in _walk(payload):
        if isinstance(value, str):
            for forbidden in FORBIDDEN_INTERNALS:
                _require(forbidden not in value, f"forbidden ingestion internal {forbidden!r} at {'.'.join(path)}")
            _require(not ABSOLUTE_PATH_PATTERN.match(value), f"absolute path at {'.'.join(path)}")
        if path and path[-1] in FORBIDDEN_TEXT_FIELDS:
            raise AssertionError(f"full text field forbidden: {'.'.join(path)}")


def _require_graph_ids_only_in_diagnostics(payload: dict[str, Any]) -> None:
    for path, value in _walk(payload):
        if isinstance(value, str) and ("graph-node" in value or "graph_node" in path[-1] or path[-1] == "graph_node_id"):
            _require(path and path[0] == "diagnostics", f"graph id outside diagnostics at {'.'.join(path)}")


def _validate_payload(payload: Any, index: int) -> None:
    _require(isinstance(payload, dict), f"payload {index} must be an object")
    missing = sorted(REQUIRED_PAYLOAD_FIELDS - payload.keys())
    _require(not missing, f"payload {index} missing required fields: {', '.join(missing)}")
    for field in REQUIRED_PAYLOAD_FIELDS:
        _require(not _is_empty(payload[field]), f"payload {index} required field {field} is empty")

    _require("display_summary" in payload and isinstance(payload["display_summary"], str) and payload["display_summary"].strip(), "display_summary must exist")
    _require(payload["evidence_role"] in EVIDENCE_ROLES, "unknown evidence_role")
    _require(payload["evidence_role"] not in {"source_evidence", "derived_summary"}, "display_summary must not be treated as evidence")
    _require(payload["canon_state"] in CANON_STATES, "unknown canon_state")
    _require(payload["authority_state"] in AUTHORITY_STATES, "unknown authority_state")
    _require(payload["visibility_state"] in VISIBILITY_STATES, "unknown visibility_state")
    _require(payload["lifecycle_state"] in LIFECYCLE_STATES, "unknown lifecycle_state")

    source_anchor = payload["source_anchor"]
    _require(isinstance(source_anchor, dict), "source_anchor must be an object")
    missing_anchor = sorted(REQUIRED_SOURCE_ANCHOR_FIELDS - source_anchor.keys())
    _require(not missing_anchor, f"source_anchor missing required fields: {', '.join(missing_anchor)}")
    locator = source_anchor["locator"]
    _require(isinstance(locator, dict), "locator must be an object")
    missing_locator = sorted(REQUIRED_LOCATOR_FIELDS - locator.keys())
    _require(not missing_locator, f"locator missing required fields: {', '.join(missing_locator)}")

    _require(isinstance(payload["source_ref"], dict) and payload["source_ref"], "source_ref must be a non-empty object")
    _require(isinstance(payload["provenance"], list) and payload["provenance"], "provenance must be a non-empty list")
    _require_no_forbidden_payload_values(payload)
    _require_graph_ids_only_in_diagnostics(payload)
    _require("surface_owned_projection_kind" not in REQUIRED_PAYLOAD_FIELDS, "surface projection kind must not override ontology fields")


def main() -> int:
    print("Graph Memory projection-safe source unit validation")
    fixture = _load_fixture()
    print("- fixture: found")
    _require(fixture.get("schema") == EXPECTED_SCHEMA, f"schema must be {EXPECTED_SCHEMA}")
    print(f"- schema: {EXPECTED_SCHEMA}")
    _require(fixture.get("version") == EXPECTED_VERSION, f"version must be {EXPECTED_VERSION}")
    payloads = fixture.get("payloads")
    _require(isinstance(payloads, list) and payloads, "fixture must include at least one payload")
    for index, payload in enumerate(payloads):
        _validate_payload(payload, index)
    print("- payloads: ready")
    print("- shared semantic envelope: ready")
    print("- source anchors: ready")
    print("- provenance: ready")
    print("- opaque locators: ready")
    print("- display summaries: non-evidence")
    print("- raw ingestion internals: absent")
    print("- projection-safe source unit: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, json.JSONDecodeError) as exc:
        print(f"- projection-safe source unit: blocked ({exc})")
        sys.exit(1)
