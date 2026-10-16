"""Compact evidence is exact presentation, never a second source authority."""

import json
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.live_control_server.services.graph_evidence_bundle import (
    build_evidence_packet,
)
from apps.live_control_server.services.graph_tool_presentation import (
    GraphToolPresentation,
)
from apps.live_control_server.services.graph_tool_transport import (
    GraphToolPageCache,
    TransportScope,
)
from graph_memory.interaction.expansion_executor import execute_expand_graph_retrieval

SCOPE = TransportScope("session", "world", "rev")


def fixture_packet():
    graph = {
        "schema": "dmb_world_graph_retrieval_result_v1",
        "retrievalSessionId": "session",
        "snapshot": {"worldId": "world", "revisionId": "rev"},
        "outcome": "enough",
        "nodes": [{"nodeId": "npc", "label": "A named person", "kind": "npc"}],
        "reviewedSourceObservations": [
            {
                "assertionId": "assertion:stance",
                "subjectNodeId": "npc",
                "text": "She believes the tunnel might be used; she plans to investigate.",
                "epistemicKind": "belief",
                "temporalScope": {"kind": "future"},
                "visibility": "gm",
                "evidenceRefIds": ["evidence:long-canonical"],
                "reviewId": "review:original",
            }
        ],
        "attributes": [],
        "relationships": [],
        "sourceAnchors": [
            {
                "anchorId": "anchor",
                "evidenceRefId": "evidence:long-canonical",
                "readable": True,
            }
        ],
        "coverage": {"state": "complete"},
    }
    source = {
        "schema": "dmb_world_graph_source_anchor_read_v1",
        "anchorId": "anchor",
        "evidenceRefId": "evidence:long-canonical",
        "content": "She might investigate the tunnel.",
        "outcome": "enough",
        "truncated": False,
        "lineStart": 3,
        "lineEnd": 3,
    }
    return graph, source


def test_exact_compact_record_qualifications_and_current_envelope_exposure():
    graph, source = fixture_packet()
    original = deepcopy(graph)
    parent = GraphToolPresentation(SCOPE)
    graph_id, source_id = uuid4(), uuid4()
    raw = parent.present_bundle(
        json.dumps(graph),
        graph_id,
        [(source_id, json.dumps(source))],
        compact_refs=True,
    )
    packet = json.loads(raw)
    record = packet["records"][0]["record"]
    assert record["text"] == graph["reviewedSourceObservations"][0]["text"]
    assert record["epistemicKind"] == "belief" and record["temporalScope"] == {
        "kind": "future"
    }
    assert record["evidence"] == ["e1"]
    assert "evidence:long-canonical" not in raw and "review:original" not in raw
    assert graph == original
    assert parent.inclusion("expand_graph_retrieval", []) == []
    assert parent.bundled_source_inclusion([]) == []
    (exposure,) = parent.inclusion("expand_graph_retrieval", [raw])
    assert exposure.event_id == graph_id
    assert exposure.assertion_ids == {"assertion:stance"}
    assert exposure.claim_evidence == (
        ("assertion", "assertion:stance", ("evidence:long-canonical",)),
    )
    assert parent.bundled_source_inclusion([raw])[0].event_id == source_id


@pytest.mark.parametrize(
    "change", ["claim", "qualification", "body", "scope", "omission"]
)
def test_changed_or_partial_packet_cannot_supply_hidden_authority(change):
    graph, source = fixture_packet()
    parent = GraphToolPresentation(SCOPE)
    raw = parent.present_bundle(
        json.dumps(graph), uuid4(), [(uuid4(), json.dumps(source))]
    )
    packet = json.loads(raw)
    if change == "claim":
        packet["records"][0]["record"]["assertionId"] = "foreign"
    elif change == "qualification":
        del packet["records"][0]["record"]["epistemicKind"]
    elif change == "body":
        packet["sources"][0]["content"] = "invented"
    elif change == "scope":
        packet["revisionId"] = "foreign"
    else:
        packet["records"] = []
    changed = json.dumps(packet, separators=(",", ":"))
    with pytest.raises(ValueError):
        parent.inclusion("expand_graph_retrieval", [changed])
    assert parent.bundled_source_inclusion([changed]) == []
    with pytest.raises(ValueError):
        GraphToolPresentation(SCOPE).inclusion("expand_graph_retrieval", [raw])


def test_failed_truncated_and_unopened_are_not_conflated():
    graph, source = fixture_packet()
    packet = build_evidence_packet(
        graph,
        [],
        bundle_id=uuid4(),
        session_id="session",
        world_id="world",
        revision_id="rev",
    )
    assert packet["coverage"]["openedSources"] == 0
    assert packet["sources"][0]["outcome"] == "not_opened"
    source.update(outcome="truncated", truncated=True, content="partial")
    packet = build_evidence_packet(
        graph,
        [source],
        bundle_id=uuid4(),
        session_id="session",
        world_id="world",
        revision_id="rev",
    )
    assert packet["coverage"]["truncatedSources"] == 1
    source.update(outcome="unavailable", truncated=False, content=None)
    packet = build_evidence_packet(
        graph,
        [source],
        bundle_id=uuid4(),
        session_id="session",
        world_id="world",
        revision_id="rev",
    )
    assert (
        packet["coverage"]["openedSources"] == 0
        and packet["sources"][0]["outcome"] == "unavailable"
    )


def test_scope_closure_and_transport_bounds_fail_closed():
    graph, source = fixture_packet()
    parent = GraphToolPresentation(SCOPE, cache=GraphToolPageCache(page_bytes=8000))
    source["content"] = "large body " * 1000
    with pytest.raises(ValueError, match="overflow"):
        parent.present_bundle(
            json.dumps(graph), uuid4(), [(uuid4(), json.dumps(source))]
        )
    graph["snapshot"]["revisionId"] = "foreign"
    with pytest.raises(ValueError, match="scope"):
        parent.present_bundle(json.dumps(graph), uuid4(), [])
    graph, source = fixture_packet()
    source["anchorId"] = "foreign"
    with pytest.raises(ValueError, match="unknown"):
        build_evidence_packet(
            graph,
            [source],
            bundle_id=uuid4(),
            session_id="session",
            world_id="world",
            revision_id="rev",
        )
    source["anchorId"] = "anchor"
    source["evidenceRefId"] = "foreign"
    with pytest.raises(ValueError, match="evidence"):
        build_evidence_packet(
            graph,
            [source],
            bundle_id=uuid4(),
            session_id="session",
            world_id="world",
            revision_id="rev",
        )


def test_non_parent_opt_in_rejects_before_session_or_source_io():
    result = execute_expand_graph_retrieval(
        {"retrievalSessionId": "unknown", "operation": "object", "includeSources": True}
    )
    assert result["code"] == "parent_evidence_bundle_required"


def test_worker_accepts_only_exact_scoped_size_bounded_bundle():
    from apps.live_control_server.services.hermes_graph_agent import (
        _GraphOperationReservation,
    )

    graph, source = fixture_packet()
    parent = GraphToolPresentation(SCOPE)
    raw = parent.present_bundle(
        json.dumps(graph), uuid4(), [(uuid4(), json.dumps(source))]
    )
    args = {
        "retrievalSessionId": "session",
        "operation": "object",
        "includeSources": True,
    }
    gate = _GraphOperationReservation(None, lambda *_: (raw, None), scope=SCOPE)
    assert gate("expand_graph_retrieval", args)[0] == raw and not gate.indeterminate
    wrong = _GraphOperationReservation(
        None, lambda *_: (raw, None), scope=TransportScope("other", "world", "rev")
    )
    wrong("expand_graph_retrieval", args)
    assert wrong.indeterminate


def acquisition_fixture(*, source_failure=False):
    from apps.live_control_server.services.graph_evidence_bundle import (
        acquire_evidence_bundle,
    )
    from tests.test_settled_source_read_accounting import fixture_execution

    execution = fixture_execution()
    scope = execution.policy.source_read_scope
    graph, source = fixture_packet()
    graph["snapshot"] = {"worldId": scope.world_id, "revisionId": scope.graph_revision}
    graph["sourceAnchors"][0].update(anchorId="a0", evidenceRefId="e0")
    graph["reviewedSourceObservations"][0]["evidenceRefIds"] = ["e0"]
    source.update(anchorId="a0", evidenceRefId="e0")
    presenter = GraphToolPresentation(
        TransportScope(scope.retrieval_session_id, scope.world_id, scope.graph_revision)
    )
    calls = []
    adapter = SimpleNamespace(
        failure=None,
        fence=object(),
        last_provider_attempt_id=uuid4(),
        operation_payloads={},
        source_payloads={},
        evidence_bundle_cache={},
        bootstrap=SimpleNamespace(
            retrieval_session=SimpleNamespace(id=scope.retrieval_session_id),
            world_scope=SimpleNamespace(
                world_id=scope.world_id, revision_id=scope.graph_revision
            ),
            binding_version=1,
        ),
        world_id=scope.world_id,
        _broker_receipt=lambda: SimpleNamespace(
            graph_authority=SimpleNamespace(
                native_world_id=scope.world_id,
                managed_world_id=scope.world_id,
                binding_version=1,
            )
        ),
        _broker_execution=lambda: execution,
        _tool_presentation=lambda: presenter,
    )

    def graph_read(message):
        assert message["arguments"]["includeSources"] is False
        calls.append("graph")
        adapter.operation_payloads[uuid4()] = json.dumps(graph)
        return {
            "resultJson": json.dumps(graph),
            "retrievalSession": {"synthetic": True},
        }

    def source_read(message):
        calls.append("source")
        assert message["arguments"]["anchorIds"] == ["a0"]
        if source_failure:
            raise RuntimeError("interrupted source response")
        adapter.source_payloads[uuid4()] = json.dumps(source)
        return {"resultJson": json.dumps(source)}

    adapter.broker_graph_operation = graph_read
    adapter.broker_source_read = source_read
    message = {
        "toolName": "expand_graph_retrieval",
        "arguments": {
            "retrievalSessionId": scope.retrieval_session_id,
            "operation": "object",
            "targets": [{"kind": "node", "id": "npc"}],
            "includeSources": True,
        },
    }
    return acquire_evidence_bundle, adapter, message, calls


def test_host_acquires_once_and_reuses_only_successful_immutable_bundle():
    acquire, adapter, message, calls = acquisition_fixture()
    first = acquire(adapter, message)
    assert json.loads(first["resultJson"])["coverage"]["openedSources"] == 1
    cached = acquire(adapter, message)
    assert (
        cached["resultJson"] == first["resultJson"]
        and cached["retrievalSession"] is None
    )
    assert calls == ["graph", "source"]


def test_interrupted_bundle_never_repeats_source_or_graph_io():
    acquire, adapter, message, calls = acquisition_fixture(source_failure=True)
    with pytest.raises(RuntimeError):
        acquire(adapter, message)
    with pytest.raises(ValueError, match="do not repeat"):
        acquire(adapter, message)
    assert calls == ["graph", "source"]


@pytest.mark.parametrize(
    "failure", ["not_admitted", "foreign_session", "unsupported_mode"]
)
def test_bundle_rejects_before_io(failure):
    acquire, adapter, message, calls = acquisition_fixture()
    if failure == "not_admitted":
        adapter.last_provider_attempt_id = None
    elif failure == "foreign_session":
        message["arguments"]["retrievalSessionId"] = "foreign"
    else:
        message["arguments"]["operation"] = "search"
    with pytest.raises(ValueError):
        acquire(adapter, message)
    assert calls == []


def test_plan_contract_retains_canonical_refs_while_build_can_factor_them():
    graph, source = fixture_packet()
    plan = build_evidence_packet(
        graph,
        [source],
        bundle_id=uuid4(),
        session_id="session",
        world_id="world",
        revision_id="rev",
    )
    build = build_evidence_packet(
        graph,
        [source],
        bundle_id=uuid4(),
        session_id="session",
        world_id="world",
        revision_id="rev",
        compact_refs=True,
    )
    assert plan["records"][0]["record"]["evidenceRefIds"] == ["evidence:long-canonical"]
    assert "evidenceRefIds" not in build["records"][0]["record"]
    assert plan["records"][0]["record"]["text"] == build["records"][0]["record"]["text"]


def test_known_read_refusal_remains_visible_and_is_not_repeated():
    acquire, adapter, message, calls = acquisition_fixture()

    def refusal(_message):
        calls.append("source-refused")
        return {
            "resultJson": json.dumps(
                {
                    "schema": "dmb_world_graph_retrieval_error_v1",
                    "statusCode": 413,
                    "code": "source_read_over_budget",
                    "message": "known refusal",
                }
            )
        }

    adapter.broker_source_read = refusal
    result = acquire(adapter, message)
    coverage = json.loads(result["resultJson"])["coverage"]
    assert (
        coverage["sourceReadStopCode"] == "source_read_over_budget"
        and coverage["openedSources"] == 0
    )
    assert acquire(adapter, message)["resultJson"] == result["resultJson"]
    assert calls == ["graph", "source-refused"]


def test_source_capture_failure_does_not_deliver_a_successful_bundle():
    acquire, adapter, message, calls = acquisition_fixture()

    def failure(_message):
        calls.append("capture-failed")
        return {
            "resultJson": json.dumps(
                {
                    "schema": "dmb_world_graph_retrieval_error_v1",
                    "statusCode": 503,
                    "code": "source_capture_incomplete",
                    "message": "capture unavailable",
                }
            )
        }

    adapter.broker_source_read = failure
    result = acquire(adapter, message)
    assert json.loads(result["resultJson"])["code"] == "source_capture_incomplete"
    with pytest.raises(ValueError, match="do not repeat"):
        acquire(adapter, message)
    assert calls == ["graph", "capture-failed"]


def test_overflow_after_acquisition_never_replays_or_delivers_hidden_rows():
    acquire, adapter, message, calls = acquisition_fixture()
    scope = adapter._broker_execution().policy.source_read_scope
    presenter = GraphToolPresentation(
        TransportScope(
            scope.retrieval_session_id, scope.world_id, scope.graph_revision
        ),
        cache=GraphToolPageCache(page_bytes=8000),
    )
    adapter._tool_presentation = lambda: presenter
    original_read = adapter.broker_graph_operation

    def large_graph(message):
        result = original_read(message)
        for event_id, raw in adapter.operation_payloads.items():
            value = json.loads(raw)
            value["reviewedSourceObservations"][0]["text"] = (
                "Long qualified source description. " * 1000
            )
            adapter.operation_payloads[event_id] = json.dumps(value)
        return result

    adapter.broker_graph_operation = large_graph
    with pytest.raises(ValueError, match="overflow"):
        acquire(adapter, message)
    with pytest.raises(ValueError, match="do not repeat"):
        acquire(adapter, message)
    assert calls == ["graph", "source"]
    assert presenter.inclusion("expand_graph_retrieval", []) == []


def test_actual_harness_responses_builder_preserves_exact_bundle_bytes(
    tmp_path, monkeypatch
):
    import hashlib
    import importlib
    from unittest.mock import patch
    from apps.live_control_server.services.hermes_graph_agent import (
        hermes_import_namespace,
    )
    from apps.live_control_server.services.hermes_graph_interaction_tools import (
        hermes_graph_interaction_tool_definitions,
    )

    home = tmp_path / "harness-home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    graph, source = fixture_packet()
    parent = GraphToolPresentation(SCOPE)
    raw = parent.present_bundle(
        json.dumps(graph), uuid4(), [(uuid4(), json.dumps(source))], compact_refs=True
    )
    definitions = hermes_graph_interaction_tool_definitions()
    schema = next(
        d["function"]["parameters"]
        for d in definitions
        if d["function"]["name"] == "expand_graph_retrieval"
    )
    assert schema["properties"]["includeSources"]["type"] == "boolean"
    with hermes_import_namespace():
        runtime = importlib.import_module("run_agent")
        runtime._hermes_home = home
        with patch("run_agent.OpenAI"):
            agent = runtime.AIAgent(
                api_key="synthetic-test-key",
                base_url="https://api.openai.com/v1",
                provider="openai-api",
                model="gpt-6-luna",
                max_tokens=100,
                max_iterations=1,
                enabled_toolsets=[],
                quiet_mode=True,
                skip_context_files=True,
                skip_memory=True,
            )
        agent.api_request_budget_guard = lambda _view: True
        agent.tools = []
        messages = [
            {"role": "system", "content": "Use the supplied evidence."},
            {"role": "user", "content": "What does the person believe?"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "bundle-call",
                        "type": "function",
                        "function": {
                            "name": "expand_graph_retrieval",
                            "arguments": json.dumps(
                                {
                                    "retrievalSessionId": "session",
                                    "operation": "object",
                                    "includeSources": True,
                                }
                            ),
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "bundle-call", "content": raw},
        ]
        request = agent._build_api_kwargs(messages)
        budget = importlib.import_module("agent.api_request_budget")
        view = budget.build_api_request_budget_view(
            provider=agent.provider,
            model=agent.model,
            api_mode=agent.api_mode,
            base_url=agent.base_url,
            request=request,
        )
    payload = json.loads(view.payload_json)
    included = [
        item["output"]
        for item in payload["input"]
        if item.get("type") == "function_call_output"
    ]
    assert included == [raw]
    assert hashlib.sha256(view.payload_json.encode()).hexdigest() == view.payload_sha256
    assert parent.inclusion("expand_graph_retrieval", included)[0].assertion_ids == {
        "assertion:stance"
    }
    assert parent.bundled_source_inclusion(included)[0].complete


@pytest.mark.parametrize("change", ["revision", "binding"])
def test_cached_bundle_cannot_cross_changed_parent_authority(change):
    acquire, adapter, message, calls = acquisition_fixture()
    acquire(adapter, message)
    if change == "revision":
        adapter.bootstrap.world_scope.revision_id = "foreign"
    else:
        adapter.bootstrap.binding_version = 2
    with pytest.raises(ValueError, match="authority differs"):
        acquire(adapter, message)
    assert calls == ["graph", "source"]


@pytest.mark.parametrize("case,code", [
    ("too_many", "evidence_bundle_invalid_request"),
    ("extra", "evidence_bundle_invalid_request"),
    ("unsupported", "evidence_bundle_unsupported_operation"),
    ("turn", "evidence_bundle_turn_unavailable"),
    ("policy", "evidence_bundle_policy_unavailable"),
    ("scope", "evidence_bundle_scope_mismatch"),
    ("unresolved", "evidence_bundle_prior_attempt_unresolved"),
])
def test_known_bundle_refusals_have_safe_reasons_before_io(case, code):
    from apps.live_control_server.services.graph_evidence_bundle import EvidenceBundleRefusal

    acquire, adapter, message, calls = acquisition_fixture()
    args = message["arguments"]
    secret = "private-invalid-value-never-release"
    if case == "too_many":
        args.update(operation="observations", targets=[], observationIds=[secret+str(n) for n in range(9)])
    elif case == "extra":
        args[secret] = secret
    elif case == "unsupported":
        args.update(operation="neighborhood")
    elif case == "turn":
        adapter.fence = None
    elif case == "policy":
        adapter._broker_execution = lambda: object()
    elif case == "scope":
        args["retrievalSessionId"] = secret
    else:
        adapter.evidence_bundle_cache[json.dumps(args, sort_keys=True, separators=(",", ":"))] = None
    with pytest.raises(EvidenceBundleRefusal) as error:
        acquire(adapter, message)
    assert error.value.code == code
    assert secret not in error.value.message
    assert calls == []
