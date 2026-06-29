from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "projection_safe_source_unit_minimal.json"
REPORT_PATH = REPO_ROOT / "Docs" / "Reports" / "archive" / "2026-06-28" / "graph-memory" / "GRAPH-MEMORY-PROJECTION-SAFE-SOURCE-UNIT.md"
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
FORBIDDEN_INTERNALS = ("_normalized/", "_breadcrumbed/", ".records_meta.jsonl", "corpus_impact")
FORBIDDEN_TEXT_FIELDS = {"lexical_plain", "full_text", "markdown_body", "raw_text", "recap_text"}


def _fixture() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
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


def test_projection_safe_source_unit_fixture_exists() -> None:
    assert FIXTURE_PATH.is_file()


def test_projection_safe_source_unit_validator_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.validate_projection_safe_source_unit"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- projection-safe source unit: ready" in result.stdout


def test_projection_safe_source_unit_schema_and_version_are_correct() -> None:
    fixture = _fixture()
    assert fixture["schema"] == "dmb_projection_safe_source_unit_fixture_v0"
    assert fixture["version"] == "0.1"


def test_every_payload_includes_required_semantic_envelope() -> None:
    for payload in _fixture()["payloads"]:
        assert REQUIRED_PAYLOAD_FIELDS.issubset(payload)


def test_source_anchor_has_artifact_anchor_ids_and_locator() -> None:
    for payload in _fixture()["payloads"]:
        source_anchor = payload["source_anchor"]
        assert source_anchor["source_artifact_id"]
        assert source_anchor["source_anchor_id"]
        assert source_anchor["source_kind"]
        assert source_anchor["source_layer"]
        assert {"locator_id", "scheme", "value"}.issubset(source_anchor["locator"])


def test_source_refs_and_provenance_are_present() -> None:
    for payload in _fixture()["payloads"]:
        assert payload["source_ref"]["source_ref_id"]
        assert payload["source_ref"]["source_artifact_id"]
        assert payload["source_ref"]["source_anchor_id"]
        assert payload["provenance"]
        assert payload["provenance"][0]["source_ref_id"] == payload["source_ref"]["source_ref_id"]


def test_display_summary_is_not_evidence() -> None:
    for payload in _fixture()["payloads"]:
        assert payload["display_summary"]
        assert payload["evidence_role"] not in {"source_evidence", "derived_summary"}


def test_no_forbidden_raw_ingestion_internals_appear_in_fixture_json() -> None:
    serialized = FIXTURE_PATH.read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_INTERNALS:
        assert forbidden not in serialized


def test_no_absolute_local_filesystem_paths_appear() -> None:
    for path, value in _walk(_fixture()):
        if isinstance(value, str):
            assert not re.match(r"^/[A-Za-z0-9._~/-]*", value), ".".join(path)


def test_no_full_text_fields_appear() -> None:
    for path, _value in _walk(_fixture()):
        assert not path or path[-1] not in FORBIDDEN_TEXT_FIELDS


def test_graph_node_ids_appear_only_under_diagnostics() -> None:
    for payload in _fixture()["payloads"]:
        for path, value in _walk(payload):
            if isinstance(value, str) and ("graph-node" in value or (path and "graph_node" in path[-1])):
                assert path[0] == "diagnostics"


def test_projection_safe_source_unit_report_exists() -> None:
    assert REPORT_PATH.is_file()


def test_report_explicitly_says_no_adapter_runtime_or_ui_change() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "does not implement an adapter" in report
    assert "does not change runtime behavior" in report
    assert "without exposing graph internals as the public UI contract" in report


def test_report_says_display_summary_is_never_evidence() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "`display_summary` is a UI/display convenience. It is never evidence." in report


def test_report_names_agent_interaction_and_future_surfaces() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "Agent Interaction" in report
    assert "future DungeonMindBuddy surfaces" in report


def test_report_names_required_semantic_envelope_including_canon_state() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")
    for field in [
        "`canon_state`",
        "`lifecycle_state`",
        "`evidence_role`",
        "`authority_state`",
        "`visibility_state`",
        "`source_anchor`",
        "`source_ref`",
        "`provenance`",
    ]:
        assert field in report
