"""Owning tests for the PR010B Rung 2 Hermes graph-read model tool adapter."""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
from typing import Any

import pytest

from apps.live_control_server.services.hermes_graph_read_tool_adapter import (
    execute_hermes_graph_read_tool_json,
    hermes_graph_read_tool_definitions,
)
from apps.live_control_server.services.hermes_graph_read_tools import (
    HERMES_GRAPH_READ_TOOL_NAMES,
    hermes_graph_read_tool_request_models,
)
from apps.live_control_server.services.world_graph_retrieval import (
    WorldGraphRetrievalServiceError,
)
from graph_memory.retrieval.models import (
    RETRIEVAL_ERROR_SCHEMA,
    RETRIEVAL_RESULT_SCHEMA,
    RETRIEVAL_SEARCH_REQUEST_SCHEMA,
    RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
    RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA,
    WorldGraphRetrievalDiagnostic,
    WorldGraphRetrievalResult,
    WorldGraphSourceAnchorReadResult,
)

ADAPTER_MODULE = (
    Path(__file__).resolve().parents[1]
    / "apps"
    / "live_control_server"
    / "services"
    / "hermes_graph_read_tool_adapter.py"
)

RUNG1_MODULE = (
    Path(__file__).resolve().parents[1]
    / "apps"
    / "live_control_server"
    / "services"
    / "hermes_graph_read_tools.py"
)

FORBIDDEN_IMPORT_TOKENS = (
    "src.live_play",
    "live_play",
    "integrations.hermes.plugins.dungeonbuddy",
    "manifest_context_query",
    "live_query_context",
    "source_bundle",
    "sentence_routing_retrieval_falsification",
    "live_agent_loop",
    "openai",
    "subprocess",
)

FORBIDDEN_LITERALS = (
    "dungeon_search",
    "dungeon_context_lookup",
    "dungeon_manifest_index",
    "dungeon_get_document",
    "dungeon_check_continuity",
    "--oneshot",
)

OLD_TOOL_NAMES = (
    "dungeon_context_lookup",
    "dungeon_manifest_index",
    "dungeon_get_document",
    "dungeon_search",
    "dungeon_check_continuity",
)

FORBIDDEN_ARGUMENT_FIELDS = (
    "manifestPath",
    "manifest_path",
    "path",
    "uri",
    "locator",
    "corpusPath",
    "breadcrumbPath",
    "breadcrumbIndex",
    "routeIndex",
    "runDirectory",
    "storePath",
    "latestIngest",
    "fallback",
)

OUTCOMES = (
    "enough",
    "partial",
    "empty",
    "denied",
    "truncated",
    "unavailable",
)

ORDERED_TOOL_NAMES = (
    "search_campaign_graph",
    "get_campaign_object",
    "get_object_neighborhood",
    "get_object_evidence",
    "read_source_anchor",
)


def _base_context(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "worldId": "world:eldyrwild",
        "campaignId": "campaign:c1",
        "focus": {"kind": "none", "sessionId": None},
        "admissibility": "gm",
        "revisionPin": None,
    }
    payload.update(overrides)
    return payload


def _search_args(**overrides: Any) -> dict[str, Any]:
    payload = _base_context(
        schema=RETRIEVAL_SEARCH_REQUEST_SCHEMA,
        queryText="Tripod Null-Calf",
    )
    payload.update(overrides)
    return payload


def _anchor_args(**overrides: Any) -> dict[str, Any]:
    payload = _base_context(
        schema=RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
        anchorId="source-anchor:v1:example",
        maxChars=4000,
    )
    payload.update(overrides)
    return payload


def _stub_retrieval_result(outcome: str = "enough") -> WorldGraphRetrievalResult:
    return WorldGraphRetrievalResult(operation="search", outcome=outcome)  # type: ignore[arg-type]


def _stub_anchor_result(outcome: str = "enough") -> WorldGraphSourceAnchorReadResult:
    return WorldGraphSourceAnchorReadResult(
        outcome=outcome,  # type: ignore[arg-type]
        anchor_id="source-anchor:v1:example",
    )


def _collect_imports(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported.add(module)
            for alias in node.names:
                imported.add(f"{module}.{alias.name}" if module else alias.name)
    return imported


def test_catalog_contains_exact_five_names_in_deterministic_order() -> None:
    definitions = hermes_graph_read_tool_definitions()
    names = [item["function"]["name"] for item in definitions]
    assert names == list(ORDERED_TOOL_NAMES)
    assert set(names) == set(HERMES_GRAPH_READ_TOOL_NAMES)
    assert all(item["type"] == "function" for item in definitions)


def test_catalog_schemas_derive_from_rung1_registry_metadata() -> None:
    registry = hermes_graph_read_tool_request_models()
    definitions = hermes_graph_read_tool_definitions()
    for item in definitions:
        name = item["function"]["name"]
        expected = registry[name].model_json_schema(by_alias=True, mode="validation")
        assert item["function"]["parameters"] == expected
        assert "schema" in item["function"]["parameters"].get("properties", {})
        assert "worldId" in item["function"]["parameters"].get("properties", {})
        assert "campaignId" in item["function"]["parameters"].get("properties", {})
        assert "world_id" not in item["function"]["parameters"].get("properties", {})
        assert item["function"]["parameters"].get("additionalProperties") is False


def test_adapter_has_no_second_name_to_model_table() -> None:
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(ADAPTER_MODULE))
    # The adapter must call hermes_graph_read_tool_request_models rather than
    # constructing its own name→model dict of the five request classes.
    call_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                call_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                call_names.add(func.attr)
    assert "hermes_graph_read_tool_request_models" in call_names
    assert "WorldGraphSearchRequest" not in source
    assert "WorldGraphObjectRequest" not in source
    assert "WorldGraphNeighborhoodRequest" not in source
    assert "WorldGraphEvidenceRequest" not in source
    assert "WorldGraphSourceAnchorReadRequest" not in source


def test_catalog_mutation_does_not_persist() -> None:
    first = hermes_graph_read_tool_definitions()
    first[0]["function"]["name"] = "mutated_tool"
    first[0]["function"]["parameters"]["properties"]["hacked"] = {"type": "string"}
    first[0]["function"]["description"] = "mutated"

    second = hermes_graph_read_tool_definitions()
    assert second[0]["function"]["name"] == "search_campaign_graph"
    assert "hacked" not in second[0]["function"]["parameters"].get("properties", {})
    assert second[0]["function"]["description"] != "mutated"
    assert second != first


def test_successful_search_returns_pr010a_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _stub_retrieval_result("enough")

    def _spy(request: Any, *, root: Path | None = None) -> Any:
        return expected

    import apps.live_control_server.services.world_graph_retrieval as wgr

    monkeypatch.setattr(wgr, "search_campaign_graph", _spy)

    payload = execute_hermes_graph_read_tool_json(
        "search_campaign_graph",
        _search_args(),
        root=Path("/tmp/graph-root"),
    )
    assert isinstance(payload, str)
    parsed = json.loads(payload)
    assert parsed == expected.model_dump(mode="json", by_alias=True)
    assert parsed["schema"] == RETRIEVAL_RESULT_SCHEMA
    assert parsed["operation"] == "search"
    assert parsed["outcome"] == "enough"
    assert "requestSummary" in parsed


def test_successful_anchor_read_returns_existing_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _stub_anchor_result("enough")

    def _spy(request: Any, *, root: Path | None = None) -> Any:
        return expected

    import apps.live_control_server.services.world_graph_retrieval as wgr

    monkeypatch.setattr(wgr, "read_source_anchor", _spy)

    payload = execute_hermes_graph_read_tool_json("read_source_anchor", _anchor_args())
    parsed = json.loads(payload)
    assert parsed == expected.model_dump(mode="json", by_alias=True)
    assert parsed["schema"] == RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA
    assert parsed["anchorId"] == "source-anchor:v1:example"
    assert "matchedNodeIds" not in parsed


def test_unknown_tool_returns_error_json_without_raising() -> None:
    payload = execute_hermes_graph_read_tool_json("not_a_graph_tool", _search_args())
    parsed = json.loads(payload)
    assert parsed["schema"] == RETRIEVAL_ERROR_SCHEMA
    assert parsed["code"] == "unknown_tool"
    assert parsed["statusCode"] == 404


@pytest.mark.parametrize("old_name", OLD_TOOL_NAMES)
def test_old_tool_names_return_unknown_tool(old_name: str) -> None:
    parsed = json.loads(execute_hermes_graph_read_tool_json(old_name, _search_args()))
    assert parsed["code"] == "unknown_tool"
    assert parsed["statusCode"] == 404


@pytest.mark.parametrize(
    "variant",
    (
        "SEARCH_CAMPAIGN_GRAPH",
        "Search_campaign_graph",
        " search_campaign_graph",
        "search_campaign_graph ",
        "search-campaign-graph",
    ),
)
def test_exact_tool_identity_rejects_normalization_variants(variant: str) -> None:
    payload = execute_hermes_graph_read_tool_json(variant, _search_args())
    parsed = json.loads(payload)
    assert parsed["schema"] == RETRIEVAL_ERROR_SCHEMA
    assert parsed["code"] == "unknown_tool"
    assert parsed["statusCode"] == 404


def test_invalid_arguments_fail_before_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invoked: list[str] = []

    def _track(*_args: Any, **_kwargs: Any) -> Any:
        invoked.append("called")
        raise AssertionError("service must not run")

    import apps.live_control_server.services.world_graph_retrieval as wgr

    monkeypatch.setattr(wgr, "search_campaign_graph", _track)

    parsed = json.loads(
        execute_hermes_graph_read_tool_json(
            "search_campaign_graph",
            {"schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA},
        )
    )
    assert parsed["code"] == "invalid_arguments"
    assert parsed["statusCode"] == 400
    assert invoked == []


def test_snake_case_arguments_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invoked: list[str] = []

    def _track(*_args: Any, **_kwargs: Any) -> Any:
        invoked.append("called")
        raise AssertionError("service must not run")

    import apps.live_control_server.services.world_graph_retrieval as wgr

    monkeypatch.setattr(wgr, "search_campaign_graph", _track)

    parsed = json.loads(
        execute_hermes_graph_read_tool_json(
            "search_campaign_graph",
            {
                "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                "world_id": "world:eldyrwild",
                "campaign_id": "campaign:c1",
                "query_text": "Tripod",
            },
        )
    )
    assert parsed["code"] == "invalid_arguments"
    assert invoked == []


@pytest.mark.parametrize("forbidden_field", FORBIDDEN_ARGUMENT_FIELDS)
def test_forbidden_legacy_fields_rejected(
    monkeypatch: pytest.MonkeyPatch,
    forbidden_field: str,
) -> None:
    invoked: list[str] = []

    def _track(*_args: Any, **_kwargs: Any) -> Any:
        invoked.append("called")
        raise AssertionError("service must not run")

    import apps.live_control_server.services.world_graph_retrieval as wgr

    monkeypatch.setattr(wgr, "search_campaign_graph", _track)

    parsed = json.loads(
        execute_hermes_graph_read_tool_json(
            "search_campaign_graph",
            _search_args(**{forbidden_field: "/some/path"}),
        )
    )
    assert parsed["code"] == "invalid_arguments"
    assert parsed["statusCode"] == 400
    assert invoked == []


def test_service_error_preserves_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_error = WorldGraphRetrievalServiceError(
        "integrity failure",
        code="retrieval_integrity_error",
        status_code=409,
        diagnostics=[
            WorldGraphRetrievalDiagnostic(
                code="retrieval_integrity_error",
                message="integrity failure",
                severity="error",
            )
        ],
    )

    def _raise(*_args: Any, **_kwargs: Any) -> Any:
        raise service_error

    import apps.live_control_server.services.world_graph_retrieval as wgr

    monkeypatch.setattr(wgr, "search_campaign_graph", _raise)

    parsed = json.loads(
        execute_hermes_graph_read_tool_json("search_campaign_graph", _search_args())
    )
    expected = service_error.response().model_dump(mode="json", by_alias=True)
    assert parsed == expected
    assert parsed["code"] == "retrieval_integrity_error"
    assert parsed["statusCode"] == 409


def test_service_error_response_failure_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BrokenServiceError(WorldGraphRetrievalServiceError):
        def response(self) -> Any:  # type: ignore[override]
            raise RuntimeError("/secret/path RESPONSE boom OPENAI_KEY=sk-leak")

    broken = _BrokenServiceError(
        "integrity failure",
        code="retrieval_integrity_error",
        status_code=409,
    )

    def _raise(*_args: Any, **_kwargs: Any) -> Any:
        raise broken

    import apps.live_control_server.services.world_graph_retrieval as wgr

    monkeypatch.setattr(wgr, "search_campaign_graph", _raise)

    payload = execute_hermes_graph_read_tool_json(
        "search_campaign_graph",
        _search_args(),
    )
    parsed = json.loads(payload)
    assert parsed["schema"] == RETRIEVAL_ERROR_SCHEMA
    assert parsed["code"] == "hermes_graph_read_tool_adapter_error"
    assert parsed["statusCode"] == 500
    assert "/secret/path" not in payload
    assert "OPENAI_KEY" not in payload
    assert "sk-leak" not in payload
    assert "boom" not in parsed["message"]
    assert parsed["message"] == "Hermes graph-read tool adapter failed unexpectedly."


def test_unexpected_adapter_failure_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("/secret/path stacktrace OPENAI_KEY=sk-test")

    monkeypatch.setattr(
        "apps.live_control_server.services.hermes_graph_read_tool_adapter"
        ".execute_hermes_graph_read_tool",
        _boom,
    )
    payload = execute_hermes_graph_read_tool_json(
        "search_campaign_graph",
        _search_args(),
    )
    parsed = json.loads(payload)
    assert parsed["schema"] == RETRIEVAL_ERROR_SCHEMA
    assert parsed["code"] == "hermes_graph_read_tool_adapter_error"
    assert parsed["statusCode"] == 500
    assert "/secret/path" not in payload
    assert "OPENAI_KEY" not in payload
    assert "sk-test" not in payload
    assert "Traceback" not in payload
    assert parsed["message"] == "Hermes graph-read tool adapter failed unexpectedly."


@pytest.mark.parametrize("outcome", OUTCOMES)
def test_outcomes_preserved_in_serialized_json(
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    expected = _stub_retrieval_result(outcome)

    def _spy(request: Any, *, root: Path | None = None) -> Any:
        return expected

    import apps.live_control_server.services.world_graph_retrieval as wgr

    monkeypatch.setattr(wgr, "search_campaign_graph", _spy)

    parsed = json.loads(
        execute_hermes_graph_read_tool_json("search_campaign_graph", _search_args())
    )
    assert parsed["outcome"] == outcome


def test_replay_produces_semantically_equivalent_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _stub_retrieval_result("partial")

    def _spy(request: Any, *, root: Path | None = None) -> Any:
        return copy.deepcopy(expected)

    import apps.live_control_server.services.world_graph_retrieval as wgr

    monkeypatch.setattr(wgr, "search_campaign_graph", _spy)

    first = execute_hermes_graph_read_tool_json("search_campaign_graph", _search_args())
    second = execute_hermes_graph_read_tool_json("search_campaign_graph", _search_args())
    assert json.loads(first) == json.loads(second)


def test_descriptions_are_graph_only_and_forbid_fallback_invitation() -> None:
    for item in hermes_graph_read_tool_definitions():
        description = item["function"]["description"].lower()
        assert "graph" in description
        assert "revision" in description or "revisionpin" in description.lower()
        # Must not advertise legacy tools as available.
        for literal in FORBIDDEN_LITERALS:
            assert literal not in description
        # Fallbacks must be framed as unavailable when mentioned.
        if "markdown" in description or "manifest" in description or "corpus" in description:
            assert (
                "do not" in description
                or "never" in description
                or "not" in description
                or "unavailable" in description
                or "absence" in description
            )


def test_read_source_anchor_description_requires_opaque_anchor() -> None:
    definitions = {
        item["function"]["name"]: item["function"]["description"]
        for item in hermes_graph_read_tool_definitions()
    }
    description = definitions["read_source_anchor"].lower()
    assert "anchorid" in description or "opaque" in description
    assert "path" in description  # to prohibit filesystem path
    assert "never" in description or "only" in description


def test_adapter_and_rung1_have_no_forbidden_imports() -> None:
    for path in (ADAPTER_MODULE, RUNG1_MODULE):
        imported = _collect_imports(path)
        for token in FORBIDDEN_IMPORT_TOKENS:
            assert token not in imported
            assert not any(
                token == name or name.startswith(f"{token}.") for name in imported
            ), f"{path.name}: forbidden import {token}"
        source = path.read_text(encoding="utf-8")
        for literal in FORBIDDEN_LITERALS:
            # Allowed only in comments/docs that prohibit the behavior, not as
            # callable identifiers. Adapter descriptions must not list old tool
            # names as available — ensure the exact old names are absent.
            assert literal not in source, f"{path.name} contains forbidden literal {literal}"
        assert "graph_memory.kernel" not in imported
        assert "httpx" not in imported
        assert "requests" not in imported


def test_non_mapping_arguments_return_invalid_arguments() -> None:
    parsed = json.loads(
        execute_hermes_graph_read_tool_json(
            "search_campaign_graph",
            "not-a-mapping",  # type: ignore[arg-type]
        )
    )
    assert parsed["code"] == "invalid_arguments"
    assert parsed["statusCode"] == 400


def test_registry_export_matches_frozen_name_set() -> None:
    registry = hermes_graph_read_tool_request_models()
    assert set(registry.keys()) == set(HERMES_GRAPH_READ_TOOL_NAMES)
    assert tuple(registry.keys()) == ORDERED_TOOL_NAMES
