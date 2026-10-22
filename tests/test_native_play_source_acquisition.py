"""Actual native Play adapter and APP acquisition; only native corpus IO is synthetic."""

from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from apps.live_control_server.services import agent_turn_service as owner
from apps.live_control_server.services.agent_runtime import AgentWorldScope
from apps.live_control_server.integrations.dungeonmind import (
    world_graph_reads as direct,
)
from graph_memory.interaction.session import GraphRetrievalSession, SessionSnapshot
from graph_memory.interaction.session_store import create_session, clear_sessions
from tests.application_state.test_native_play_input_postgres import (
    prepared_native,
    append,
)
from tests.test_agent_turn_service import _request


@pytest.fixture
def acquired(application_state_dsn, monkeypatch):
    service, sub, turn, provider, raw = prepared_native(application_state_dsn)
    turn, _ = append(service, sub, turn, provider, raw)
    for value in ("sdk_entered", "response_received"):
        turn, _ = service.record_provider_outcome(
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
            expected_attempt=turn.attempt,
            outcome=t.ProviderOutcomeEventV1(
                kind="provider_outcome",
                event_id=uuid4(),
                sequence=len(turn.graph_context_execution.events),
                provider_attempt_id=provider.provider_attempt_id,
                outcome=value,
            ),
        )
    receipt = turn.graph_context_receipt
    authority = receipt.graph_authority
    session = GraphRetrievalSession(
        id=receipt.retrieval_session_id,
        snapshot=SessionSnapshot(
            world_id=authority.native_world_id,
            campaign_id="",
            focus={"kind": "none"},
            admissibility="gm",
            revision_id=authority.graph_revision,
            scope_mode="world",
        ),
        question="Describe the bridge from its source.",
    )
    clear_sessions()
    create_session(session)
    bootstrap = owner.AgentPlanWorldGraphBootstrap(
        graph_envelope={},
        world_scope=AgentWorldScope(
            world_id=authority.native_world_id,
            campaign_id="",
            focus={"kind": "none"},
            admissibility="gm",
            revision_id=authority.graph_revision,
            scope_mode="world",
        ),
        retrieval_session=session,
        binding_version=authority.binding_version,
        source_root_relpath="corpus",
        candidate_assertion_ids=(),
        candidate_relationship_ids=(),
        candidate_evidence_ref_ids=(),
        evidence_by_anchor_id={},
    )
    adapter = owner._PolicyExecutionAdapter(
        service=service,
        request=_request(),
        world_id=turn.world_id,
        work=None,
        bootstrap=bootstrap,
        playable_target=None,
        submitted_intent=None,
        existing_turn=turn,
        budget={},
    )

    class Fence:
        def __init__(self):
            self.turn = turn

        def append(self, method, key, event, **extras):
            self.turn, fresh = getattr(service, method)(
                self.turn.world_id,
                self.turn.conversation_id,
                self.turn.turn_id,
                expected_revision=self.turn.revision,
                expected_attempt=self.turn.attempt,
                **{key: event},
                **extras,
            )
            return self.turn, fresh

    adapter.fence = Fence()
    adapter.last_provider_attempt_id = provider.provider_attempt_id
    calls = []
    pin = t.GraphSourceScopeAnchorV2(
        anchor_id="anchor:new",
        evidence_ref_id="evidence:new",
        source_artifact_id="source:new",
        source_revision_id="revision:new",
    )
    text = "The bridge keeper lights three lanterns."
    payload = {
        "schema": "dmb_world_graph_retrieval_result_v1",
        "outcome": "enough",
        "snapshot": {
            "worldId": authority.native_world_id,
            "revisionId": authority.graph_revision,
        },
        "nodes": [{"nodeId": "bridge", "label": "Bridge", "kind": "location"}],
        "attributes": [],
        "relationships": [],
        "sourceAnchors": [
            {
                "anchorId": pin.anchor_id,
                "evidenceRefId": pin.evidence_ref_id,
                "readable": True,
            }
        ],
        "coverage": {"state": "complete"},
    }
    result = SimpleNamespace(
        snapshot=SimpleNamespace(
            world_id=authority.native_world_id, revision_id=authority.graph_revision
        ),
        attributes=(),
        relationships=(),
        source_anchors=(
            SimpleNamespace(
                anchor_id=pin.anchor_id,
                evidence_ref_id=pin.evidence_ref_id,
                readable=True,
                locator_kind="source_span",
            ),
        ),
        coverage=SimpleNamespace(truncated_fields=()),
        outcome="enough",
        model_dump=lambda **_: payload,
    )

    def graph(_services, request, **kwargs):
        calls.append("graph")
        assert (
            request.world_id == authority.native_world_id
            and request.revision_pin == authority.graph_revision
        )
        return SimpleNamespace(
            result=result,
            source_pins=(
                SimpleNamespace(
                    **pin.model_dump(), graph_revision=authority.graph_revision
                ),
            ),
            reviewed_source_observations=(),
            observation_gap_codes=(),
            observation_missing_ids=(),
        )

    monkeypatch.setattr(direct, "direct_services_from_config", lambda *_: object())
    monkeypatch.setattr(direct, "get_object_with_reviewed_sources_direct_v3", graph)
    monkeypatch.setattr(
        direct,
        "get_object_direct",
        lambda *_: pytest.fail("Native Play selected a predecessor read"),
    )

    def source(arguments, *, receipt_version, root):
        calls.append("source")
        assert receipt_version == 2 and arguments["anchorIds"] == [pin.anchor_id]
        rid = "synthetic-source-read"
        return {
            "schema": "dmb_internal_read_graph_source_batch_v2",
            "retrievalSessionId": session.id,
            "reads": [
                {
                    "sourceReadId": rid,
                    "result": {
                        "schema": "dmb_world_graph_source_anchor_read_v1",
                        "outcome": "enough",
                        "anchorId": pin.anchor_id,
                        "evidenceRefId": pin.evidence_ref_id,
                        "sourceArtifactId": pin.source_artifact_id,
                        "sourceName": "Bridge journal",
                        "content": text,
                        "contentSha256": "a" * 64,
                        "lineStart": 3,
                        "lineEnd": 3,
                        "truncated": False,
                    },
                    "receipt": {
                        "source_read_id": rid,
                        "retrieval_session_id": session.id,
                        "graph_revision": authority.graph_revision,
                        **pin.model_dump(),
                        "read_content_sha256": "a" * 64,
                        "outcome": "enough",
                        "truncated": False,
                    },
                }
            ],
        }

    monkeypatch.setattr(
        "graph_memory.interaction.expansion_executor.execute_read_graph_source", source
    )
    yield SimpleNamespace(
        adapter=adapter, pin=pin, text=text, calls=calls, session=session
    )
    clear_sessions()


def request(f, *, bundle=True):
    return {
        "toolName": "expand_graph_retrieval",
        "arguments": {
            "retrievalSessionId": f.session.id,
            "operation": "object",
            "targets": [{"kind": "node", "id": "bridge"}],
            "includeSources": bundle,
        },
    }


def test_native_play_bundle_uses_v3_pins_and_settled_reads_once_and_reopens(acquired):
    f = acquired
    first = f.adapter.broker_graph_operation(request(f))
    assert f.adapter.failure is None, f.adapter.failure
    packet = json.loads(first["resultJson"])
    assert (
        packet["schema"] == "dmb_graph_evidence_packet_v1"
        and packet["sources"][0]["sourceName"] == "Bridge journal"
    )
    assert (
        packet["sources"][0]["content"] == f.text
        and packet["sources"][0]["passageHandle"]
    )
    execution = f.adapter.fence.turn.graph_context_execution
    assert execution.effective_source_pins()[f.pin.anchor_id] == f.pin
    assert isinstance(execution.events[-4], t.ValidatedGraphOperationEventV3)
    assert isinstance(execution.events[-3], t.SourceScopeExtensionEventV3)
    assert isinstance(execution.events[-2], t.SourceReadAuthorizationEventV2)
    assert isinstance(execution.events[-1], t.ValidatedSourceReadEventV2)
    assert (
        execution.events[-1].receipts[0].content_sha256
        == sha256(f.text.encode()).hexdigest()
    )
    again = f.adapter.broker_graph_operation(request(f))
    assert again["resultJson"] == first["resultJson"] and f.calls == ["graph", "source"]
    turn = f.adapter.fence.turn
    reopened = AgentConversationService().inspect_turn(
        world_id=turn.world_id, turn_id=turn.turn_id
    )
    assert reopened.graph_context_execution == execution


@pytest.mark.parametrize("change", ["session", "outside", "duplicate", "budget"])
def test_native_play_source_read_refuses_before_io(acquired, change):
    f = acquired
    reply = f.adapter.broker_graph_operation(request(f, bundle=False))
    assert f.adapter.failure is None, reply
    args = {
        "retrievalSessionId": f.session.id,
        "anchorIds": [f.pin.anchor_id],
        "maxChars": 4000,
    }
    if change == "session":
        args["retrievalSessionId"] = "foreign"
    if change == "outside":
        args["anchorIds"] = ["anchor:foreign"]
    if change == "duplicate":
        args["anchorIds"] *= 2
    if change == "budget":
        args["maxChars"] = (
            f.adapter._broker_execution().policy.max_chars_per_source_read + 1
        )
    refused = f.adapter.broker_source_read(
        {"toolName": "read_graph_source", "arguments": args}
    )
    assert json.loads(refused["resultJson"])["statusCode"] >= 400
    assert f.calls == ["graph"] and f.adapter.failure is None


def test_play_total_character_reservation_blocks_read_before_io(acquired):
    from tests.test_settled_source_read_accounting import authorization

    f = acquired
    f.adapter.broker_graph_operation(request(f, bundle=False))
    execution = f.adapter._broker_execution()
    # Reserve the actual total across the eight frozen anchors before any body IO.
    total = execution.policy.max_source_read_chars
    assert total == 8 * execution.policy.max_chars_per_source_read
    auth = authorization(
        execution,
        len(execution.events),
        count=8,
        max_chars=execution.policy.max_chars_per_source_read,
    )
    f.adapter.turn, _ = f.adapter.fence.append(
        "authorize_source_read", "authorization", auth
    )
    reply = f.adapter.broker_source_read(
        {
            "toolName": "read_graph_source",
            "arguments": {
                "retrievalSessionId": f.session.id,
                "anchorIds": [f.pin.anchor_id],
                "maxChars": 1,
            },
        }
    )
    assert json.loads(reply["resultJson"])["code"] == "source_read_over_budget"
    assert f.calls == ["graph"]


def test_native_play_uncertain_bundle_never_repeats_corpus_io(acquired, monkeypatch):
    f = acquired
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise TimeoutError("Synthetic uncertain native read")

    monkeypatch.setattr(
        "graph_memory.interaction.expansion_executor.execute_read_graph_source", fail
    )
    first = f.adapter.broker_graph_operation(request(f))
    assert (
        f.adapter.failure is not None
        and json.loads(first["resultJson"])["statusCode"] >= 500
    )
    second = f.adapter.broker_graph_operation(request(f))
    assert (
        json.loads(second["resultJson"])["code"] == "evidence_bundle_turn_unavailable"
    )
    assert f.calls == ["graph"] and calls == [1]
