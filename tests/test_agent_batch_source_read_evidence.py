import hashlib
import json
import pytest
from apps.live_control_server.services.agent_source_read_telemetry import (
    BATCH_V1,
    BATCH_V2,
    READ_SCHEMA,
    summarize_source_reads,
)
from apps.live_control_server.services.hermes_graph_agent import (
    _summarize_tool_result,
    _ToolEventCollector,
)
from apps.live_control_server.services.hermes_graph_agent_contract import (
    HermesGraphAgentTurnResult,
    serialize_hermes_graph_agent_turn_result,
    deserialize_hermes_graph_agent_turn_result,
)
from graph_memory.hermes_graph_plugin import (
    HermesGraphScope,
    default_graph_only_capability_policy,
)

BODY = "PRIVATE-SYNTHETIC-PASSAGE-not-to-be-retained"
SECRET = "SECRET-KEY-not-to-be-retained"


def packet(version=BATCH_V2, outcome="enough"):
    result = {
        "schema": READ_SCHEMA,
        "anchorId": "anchor:synthetic",
        "sourceArtifactId": "artifact:synthetic",
        "sourceSpanRefId": "span:1",
        "evidenceRefId": "evidence:1",
        "outcome": outcome,
        "content": BODY,
        "truncated": False,
    }
    row = (
        {
            "result": result,
            "receipt": {
                "source_revision_id": "source:rev1",
                "graph_revision": "rev:1",
                "secret": SECRET,
            },
            "secret": SECRET,
        }
        if version == BATCH_V2
        else result
    )
    return {"schema": version, "reads": [row], "secret": SECRET}


@pytest.mark.parametrize("version", [BATCH_V1, BATCH_V2])
def test_batch_completion_retains_source_evidence_without_body_or_secret(version):
    summary = _summarize_tool_result(json.dumps(packet(version)))
    assert summary["source_anchor_ids"] == ["anchor:synthetic"]
    metadata = summary["source_read_metadata"]
    row = metadata["sourceRead0"]
    assert row["opened"] == "true" and row["returnedChars"] == str(len(BODY))
    assert row["returnedContentSha256"] == hashlib.sha256(BODY.encode()).hexdigest()
    assert BODY not in json.dumps(summary) and SECRET not in json.dumps(summary)
    assert summary["outcome"] is None  # Telemetry does not invent aggregate acceptance.


@pytest.mark.parametrize("outcome", ["denied", "unavailable", "empty", "unknown"])
def test_failed_read_never_claims_opened_despite_returned_text(outcome):
    meta, _ = summarize_source_reads(packet(outcome=outcome))
    assert meta["sourceRead0"]["opened"] == "false"


def test_unknown_and_malformed_packets_are_not_source_evidence():
    p = packet()
    p["schema"] = "unknown"
    assert summarize_source_reads(p) == ({}, [])
    p = packet()
    p["reads"] = [None, {"result": "not a result"}]
    meta, ids = summarize_source_reads(p)
    assert ids == [] and meta["sourceRead0"]["malformed"] == "true"


def test_limits_report_truncation_and_mixed_outcomes_individually():
    p = packet()
    p["reads"] *= 9
    p["reads"][1] = {
        "result": {
            "schema": "dmb_world_graph_retrieval_error_v1",
            "anchorId": "anchor:bad",
            "code": "source_unavailable",
        }
    }
    meta, ids = summarize_source_reads(p)
    assert meta["sourceReadCount"] == 9 and meta["sourceReadTelemetryTruncated"] is True
    assert "sourceRead7" in meta and "sourceRead8" not in meta
    assert (
        meta["sourceRead1"]["opened"] == "false"
        and meta["sourceRead1"]["code"] == "source_unavailable"
    )
    assert ids == ["anchor:synthetic", "anchor:bad"]


def test_actual_hermes_callbacks_and_ipc_preserve_requested_and_read_receipts():
    policy = default_graph_only_capability_policy(
        HermesGraphScope(
            world_id="world:test",
            campaign_id="",
            focus={"kind": "none"},
            admissibility="gm",
            revision_pin="rev:1",
            scope_mode="world",
        )
    )
    collector = _ToolEventCollector(policy)
    args = {"anchorIds": ["anchor:synthetic"], "maxChars": 4000}
    collector.on_start("call:1", "read_graph_source", args)
    collector.on_complete("call:1", "read_graph_source", args, json.dumps(packet()))
    assert collector.events[0].bounded_ids["anchorIds"] == ["anchor:synthetic"]
    result = HermesGraphAgentTurnResult(
        status="ok",
        final_response="Answer",
        messages=[],
        hermes_session_id="session:test",
        tool_events=collector.events,
    )
    restored = deserialize_hermes_graph_agent_turn_result(
        serialize_hermes_graph_agent_turn_result(result)
    )
    event = restored.tool_events[-1]
    assert (
        event.revision_pin == "rev:1"
        and event.bounded_ids["sourceRead0"]["opened"] == "true"
    )
    assert event.bounded_ids["sourceRead0"]["source_revision_id"] == "source:rev1"
    assert BODY not in json.dumps(serialize_hermes_graph_agent_turn_result(result))


def test_actual_pydantic_collector_uses_same_safe_metadata():
    from apps.live_control_server.services.pydantic_ai_agent_runtime import (
        _TurnCollector,
    )
    from tests.test_pydantic_ai_agent_runtime import _invocation

    collector = _TurnCollector(_invocation())
    collector.emit_start("read_graph_source", {"anchorIds": ["anchor:synthetic"]})
    collector.emit_finish(
        "read_graph_source",
        {"anchorIds": ["anchor:synthetic"]},
        duration_ms=1,
        raw_result=json.dumps(packet()),
    )
    event = collector.tool_events[-1]
    assert event.attributes["bounded_ids"]["sourceRead0"]["opened"] == "true"
    assert event.source_anchor_ids == ["anchor:synthetic"]
    assert BODY not in json.dumps(event.attributes) and SECRET not in json.dumps(
        event.attributes
    )


@pytest.mark.parametrize(
    "damage", ["schema_list", "outcome_map", "missing_anchor", "invalid_unicode"]
)
def test_malformed_results_do_not_break_telemetry_or_claim_opening(damage):
    p = packet()
    if damage == "schema_list":
        p["schema"] = []
        assert summarize_source_reads(p) == ({}, [])
        return
    result = p["reads"][0]["result"]
    if damage == "outcome_map":
        result["outcome"] = {}
    if damage == "missing_anchor":
        result.pop("anchorId")
    if damage == "invalid_unicode":
        result["content"] = chr(0xD800)
    meta, _ = summarize_source_reads(p)
    assert meta["sourceRead0"]["opened"] == "false"


def test_oversized_ids_are_omitted_not_prefixes_through_collector_and_ipc():
    long_id = "X" * 10000
    p = packet()
    p["reads"][0]["result"]["anchorId"] = long_id
    p["reads"][0]["result"]["sourceArtifactId"] = long_id
    summary = _summarize_tool_result(json.dumps(p))
    assert summary["source_anchor_ids"] == []
    row = summary["source_read_metadata"]["sourceRead0"]
    assert "anchorId" not in row and "sourceArtifactId" not in row
    assert row["opened"] == "false"
    assert row["anchorIdSha256"] == hashlib.sha256(long_id.encode()).hexdigest()
    assert "anchorId" in row["identityFieldsOmitted"]
    policy = default_graph_only_capability_policy(
        HermesGraphScope(
            world_id="world:test",
            campaign_id="",
            focus={"kind": "none"},
            admissibility="gm",
            revision_pin="rev:1",
            scope_mode="world",
        )
    )
    collector = _ToolEventCollector(policy)
    args = {"anchorIds": [long_id, "anchor:normal"]}
    collector.on_start("call:long", "read_graph_source", args)
    collector.on_complete("call:long", "read_graph_source", args, json.dumps(p))
    result = HermesGraphAgentTurnResult(
        status="ok",
        final_response="Answer",
        messages=[],
        hermes_session_id="session:test",
        tool_events=collector.events,
    )
    wire = serialize_hermes_graph_agent_turn_result(result)
    restored = deserialize_hermes_graph_agent_turn_result(wire)
    assert restored.tool_events[0].bounded_ids["anchorIds"] == ["anchor:normal"]
    assert restored.tool_events[-1].source_anchor_ids == []
    assert long_id not in json.dumps(wire) and long_id[:256] not in json.dumps(wire)


def test_pydantic_collector_never_exports_oversized_exact_identity():
    from apps.live_control_server.services.pydantic_ai_agent_runtime import (
        _TurnCollector,
    )
    from tests.test_pydantic_ai_agent_runtime import _invocation

    p = packet()
    p["reads"][0]["result"]["anchorId"] = "X" * 10000
    collector = _TurnCollector(_invocation())
    collector.emit_finish(
        "read_graph_source",
        {"anchorIds": ["X" * 10000]},
        duration_ms=1,
        raw_result=json.dumps(p),
    )
    event = collector.tool_events[-1]
    assert event.source_anchor_ids == [] and event.bounded_ids["anchorIds"] == []
    assert event.bounded_ids["sourceRead0"]["opened"] == "false"


@pytest.mark.parametrize("damage", [None,"missing_content","empty_content","missing_anchor","denied"])
def test_single_read_uses_the_same_private_opened_summary(damage):
    raw = packet(BATCH_V1)["reads"][0]
    raw["snapshot"] = {"revisionId":"rev:exact"}
    if damage == "missing_content":
        raw.pop("content")
    elif damage == "empty_content":
        raw["content"] = ""
    elif damage == "missing_anchor":
        raw.pop("anchorId")
    elif damage == "denied":
        raw["outcome"] = "denied"
    summary = _summarize_tool_result(json.dumps(raw))
    metadata = summary["source_read_metadata"]
    assert metadata["sourceReadCount"] == 1
    assert metadata["sourceRead0"]["opened"] == ("true" if damage is None else "false")
    assert metadata["sourceRead0"]["graph_revision"] == "rev:exact"
    assert BODY not in json.dumps(summary) and SECRET not in json.dumps(summary)
