"""Owning tests for the PR010B Rung 1 Hermes graph-read tool executor.

Superseded by the two-tool interaction catalog (``expand_graph_retrieval``,
``read_graph_source``). Kernel-facing ``hermes_graph_read_tools`` remains for
internal dispatch; model-visible contract tests live in interaction-tool tests.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason=(
        "Obsolete five-tool model catalog; kernel read_tools unchanged but "
        "Hermes plugin registers expand_graph_retrieval + read_graph_source only."
    ),
)

import ast
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest

from apps.live_control_server.services.hermes_graph_read_tools import (
    HERMES_GRAPH_READ_TOOL_NAMES,
    HermesGraphReadToolContractError,
    execute_hermes_graph_read_tool,
)
from apps.live_control_server.services.world_graph_retrieval import (
    WorldGraphRetrievalServiceError,
)
from graph_memory.retrieval.models import (
    RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
    RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
    RETRIEVAL_OBJECT_REQUEST_SCHEMA,
    RETRIEVAL_SEARCH_REQUEST_SCHEMA,
    RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
    WorldGraphEvidenceRequest,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphRetrievalResult,
    WorldGraphSearchRequest,
    WorldGraphSourceAnchorReadRequest,
    WorldGraphSourceAnchorReadResult,
)

PRODUCTION_MODULE = (
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
    "corpus",
    "breadcrumb",
    "sentence_routing_retrieval_falsification",
)

OLD_HERMES_TOOL_NAMES = (
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


def _object_args(**overrides: Any) -> dict[str, Any]:
    payload = _base_context(
        schema=RETRIEVAL_OBJECT_REQUEST_SCHEMA,
        nodeId="threat:tripod-null-calf",
    )
    payload.update(overrides)
    return payload


def _neighborhood_args(**overrides: Any) -> dict[str, Any]:
    payload = _base_context(
        schema=RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
        seedNodeIds=["threat:tripod-null-calf"],
        maxDepth=1,
    )
    payload.update(overrides)
    return payload


def _evidence_args(**overrides: Any) -> dict[str, Any]:
    payload = _base_context(
        schema=RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
        target={"kind": "node", "id": "threat:tripod-null-calf"},
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


TOOL_CASES: list[tuple[str, dict[str, Any], type, str]] = [
    (
        "search_campaign_graph",
        _search_args(),
        WorldGraphSearchRequest,
        "search_campaign_graph",
    ),
    (
        "get_campaign_object",
        _object_args(),
        WorldGraphObjectRequest,
        "get_campaign_object",
    ),
    (
        "get_object_neighborhood",
        _neighborhood_args(),
        WorldGraphNeighborhoodRequest,
        "get_object_neighborhood",
    ),
    (
        "get_object_evidence",
        _evidence_args(),
        WorldGraphEvidenceRequest,
        "get_object_evidence",
    ),
    (
        "read_source_anchor",
        _anchor_args(),
        WorldGraphSourceAnchorReadRequest,
        "read_source_anchor",
    ),
]


def _stub_retrieval_result(outcome: str = "enough") -> WorldGraphRetrievalResult:
    return WorldGraphRetrievalResult(operation="search", outcome=outcome)  # type: ignore[arg-type]


def _stub_anchor_result(outcome: str = "enough") -> WorldGraphSourceAnchorReadResult:
    return WorldGraphSourceAnchorReadResult(
        outcome=outcome,  # type: ignore[arg-type]
        anchor_id="source-anchor:v1:example",
    )


def _install_service_spy(
    monkeypatch: pytest.MonkeyPatch,
    service_name: str,
    *,
    result: Any | None = None,
    raises: BaseException | None = None,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def _spy(request: Any, *, root: Path | None = None) -> Any:
        calls.append({"request": request, "root": root})
        if raises is not None:
            raise raises
        assert result is not None
        return result

    import apps.live_control_server.services.world_graph_retrieval as wgr

    monkeypatch.setattr(wgr, service_name, _spy)
    return calls


def test_registry_contains_exactly_five_canonical_names() -> None:
    assert HERMES_GRAPH_READ_TOOL_NAMES == {
        "search_campaign_graph",
        "get_campaign_object",
        "get_object_neighborhood",
        "get_object_evidence",
        "read_source_anchor",
    }


@pytest.mark.parametrize(
    "tool_name,arguments,request_type,service_name",
    TOOL_CASES,
    ids=[case[0] for case in TOOL_CASES],
)
def test_dispatch_invokes_exact_service_with_validated_request(
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
    arguments: dict[str, Any],
    request_type: type,
    service_name: str,
) -> None:
    expected = (
        _stub_anchor_result()
        if tool_name == "read_source_anchor"
        else _stub_retrieval_result()
    )
    root = Path("/tmp/graph-root-for-hermes-executor")
    calls = _install_service_spy(monkeypatch, service_name, result=expected)

    returned = execute_hermes_graph_read_tool(tool_name, arguments, root=root)

    assert returned is expected
    assert len(calls) == 1
    assert isinstance(calls[0]["request"], request_type)
    assert calls[0]["root"] == root


def test_unknown_tool_raises_unknown_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    invoked: list[str] = []

    def _fail(*_args: Any, **_kwargs: Any) -> None:
        invoked.append("called")
        raise AssertionError("service must not be invoked")

    for name in HERMES_GRAPH_READ_TOOL_NAMES:
        monkeypatch.setattr(
            f"apps.live_control_server.services.world_graph_retrieval.{name}",
            _fail,
        )

    with pytest.raises(HermesGraphReadToolContractError) as exc_info:
        execute_hermes_graph_read_tool("not_a_graph_tool", _search_args())

    assert exc_info.value.code == "unknown_tool"
    assert invoked == []


@pytest.mark.parametrize("old_name", OLD_HERMES_TOOL_NAMES)
def test_old_hermes_tool_names_rejected(old_name: str) -> None:
    with pytest.raises(HermesGraphReadToolContractError) as exc_info:
        execute_hermes_graph_read_tool(old_name, _search_args())
    assert exc_info.value.code == "unknown_tool"


def test_non_mapping_arguments_raise_invalid_arguments() -> None:
    with pytest.raises(HermesGraphReadToolContractError) as exc_info:
        execute_hermes_graph_read_tool(
            "search_campaign_graph",
            "not-a-mapping",  # type: ignore[arg-type]
        )
    assert exc_info.value.code == "invalid_arguments"


def test_snake_case_request_fields_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_service_spy(
        monkeypatch,
        "search_campaign_graph",
        result=_stub_retrieval_result(),
    )
    with pytest.raises(HermesGraphReadToolContractError) as exc_info:
        execute_hermes_graph_read_tool(
            "search_campaign_graph",
            {
                "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                "world_id": "world:eldyrwild",
                "campaign_id": "campaign:c1",
                "query_text": "Tripod",
            },
        )
    assert exc_info.value.code == "invalid_arguments"
    assert calls == []


@pytest.mark.parametrize("forbidden_field", FORBIDDEN_ARGUMENT_FIELDS)
def test_forbidden_path_manifest_breadcrumb_fields_rejected(
    monkeypatch: pytest.MonkeyPatch,
    forbidden_field: str,
) -> None:
    calls = _install_service_spy(
        monkeypatch,
        "search_campaign_graph",
        result=_stub_retrieval_result(),
    )
    args = _search_args(**{forbidden_field: "/some/path"})
    with pytest.raises(HermesGraphReadToolContractError) as exc_info:
        execute_hermes_graph_read_tool("search_campaign_graph", args)
    assert exc_info.value.code == "invalid_arguments"
    assert calls == []


def test_invalid_arguments_do_not_invoke_any_retrieval_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invoked: list[str] = []

    def _track(name: str) -> Callable[..., Any]:
        def _spy(*_args: Any, **_kwargs: Any) -> Any:
            invoked.append(name)
            raise AssertionError(f"{name} must not be invoked")

        return _spy

    import apps.live_control_server.services.world_graph_retrieval as wgr

    for name in HERMES_GRAPH_READ_TOOL_NAMES:
        monkeypatch.setattr(wgr, name, _track(name))

    with pytest.raises(HermesGraphReadToolContractError) as exc_info:
        execute_hermes_graph_read_tool(
            "search_campaign_graph",
            {"schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA},
        )
    assert exc_info.value.code == "invalid_arguments"
    assert invoked == []


def test_service_error_propagates_same_exception_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_error = WorldGraphRetrievalServiceError(
        "integrity failure",
        code="retrieval_integrity_error",
        status_code=409,
    )
    _install_service_spy(
        monkeypatch,
        "search_campaign_graph",
        raises=service_error,
    )

    with pytest.raises(WorldGraphRetrievalServiceError) as exc_info:
        execute_hermes_graph_read_tool("search_campaign_graph", _search_args())

    assert exc_info.value is service_error


@pytest.mark.parametrize("outcome", OUTCOMES)
def test_retrieval_outcomes_preserved_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    expected = _stub_retrieval_result(outcome)
    _install_service_spy(
        monkeypatch,
        "search_campaign_graph",
        result=expected,
    )
    returned = execute_hermes_graph_read_tool("search_campaign_graph", _search_args())
    assert returned is expected
    assert returned.outcome == outcome


@pytest.mark.parametrize("outcome", OUTCOMES)
def test_source_anchor_outcomes_preserved_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    expected = _stub_anchor_result(outcome)
    _install_service_spy(
        monkeypatch,
        "read_source_anchor",
        result=expected,
    )
    returned = execute_hermes_graph_read_tool("read_source_anchor", _anchor_args())
    assert returned is expected
    assert returned.outcome == outcome


def test_replay_same_call_without_executor_owned_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = [_stub_retrieval_result("enough"), _stub_retrieval_result("partial")]
    calls: list[dict[str, Any]] = []

    def _spy(request: Any, *, root: Path | None = None) -> Any:
        calls.append({"request": request, "root": root})
        return results[len(calls) - 1]

    import apps.live_control_server.services.world_graph_retrieval as wgr

    monkeypatch.setattr(wgr, "search_campaign_graph", _spy)

    first = execute_hermes_graph_read_tool("search_campaign_graph", _search_args())
    second = execute_hermes_graph_read_tool("search_campaign_graph", _search_args())

    assert first is results[0]
    assert second is results[1]
    assert first is not second
    assert len(calls) == 2
    assert isinstance(calls[0]["request"], WorldGraphSearchRequest)
    assert isinstance(calls[1]["request"], WorldGraphSearchRequest)


def test_production_module_has_no_forbidden_imports() -> None:
    source = PRODUCTION_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(PRODUCTION_MODULE))
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

    for token in FORBIDDEN_IMPORT_TOKENS:
        assert token not in imported, f"forbidden import present: {token}"
        assert not any(
            token == name or name.startswith(f"{token}.") for name in imported
        ), f"forbidden import present: {token}"

    assert any(
        name == "apps.live_control_server.services.world_graph_retrieval"
        or name.endswith(".world_graph_retrieval")
        for name in imported
    )
    assert "graph_memory.kernel" not in imported
    assert any(name.startswith("graph_memory.retrieval") for name in imported)
    assert "httpx" not in imported
    assert "requests" not in imported
    assert "urllib" not in imported
    assert "os.environ" not in source
    assert "importlib" not in imported


def test_mapping_protocol_arguments_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _stub_retrieval_result()
    calls = _install_service_spy(
        monkeypatch,
        "search_campaign_graph",
        result=expected,
    )

    class _Args(Mapping[str, Any]):
        def __init__(self, data: dict[str, Any]) -> None:
            self._data = data

        def __getitem__(self, key: str) -> Any:
            return self._data[key]

        def __iter__(self):
            return iter(self._data)

        def __len__(self) -> int:
            return len(self._data)

    returned = execute_hermes_graph_read_tool(
        "search_campaign_graph",
        _Args(_search_args()),
    )
    assert returned is expected
    assert len(calls) == 1
