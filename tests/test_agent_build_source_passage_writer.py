"""Real mocked SDK → broker → source-only writer → disposable APP/readback."""

import json
from hashlib import sha256
from uuid import uuid4

import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from apps.live_control_server.services import agent_turn_service as owner
from tests.test_agent_build_jev_controller_exposure import (
    _start,
    _acquire,
    build_case as _build_case,
)
from tests.test_agent_build_jev_single_writer import WriterWire, invoke, prepared


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def stage(build_case, monkeypatch, *, bundle=False, sections=False):
    adapter, calls, text = _start(build_case, monkeypatch)
    selected = []
    if sections:
        selected = [
            json.loads(adapter.read_build_section(line_start=1, line_end=2))["read_id"]
        ]
    graph, source = _acquire(adapter, bundle=bundle)
    projection = adapter.stage_build_source_writer(
        graph_payloads=(graph,),
        source_payloads=(source,) if source else (),
        section_read_ids=selected,
    )
    return adapter, projection, calls, text


def answer(projection, **changes):
    packet = json.loads(projection.input_json)
    value = {
        "answer_context_status": "source_grounded",
        "answer_segments": [
            {
                "kind": "source_passage_claim",
                "text": "Frank believes the western gate is haunted.",
                "passage_handles": [packet["opened_passages"][0]["handle"]],
            }
        ],
    }
    value.update(changes)
    return json.dumps(value)


def fresh(adapter):
    return AgentConversationService().list_turns(
        adapter.turn.world_id, adapter.turn.conversation_id
    )[0]


@pytest.mark.parametrize("bundle", [False, True])
def test_sdk_source_only_wire_durable_completion_and_fresh_projection(
    build_case, monkeypatch, bundle
):
    adapter, projection, calls, text = stage(build_case, monkeypatch, bundle=bundle)
    packet = json.loads(projection.input_json)
    assert packet["opened_passages"][0]["text"] == text
    assert not any(
        key in packet for key in ["initialClaimPacket", "discovery", "observations"]
    )
    wire = WriterWire(adapter, text=answer(projection))
    result = invoke(adapter, projection, wire)
    assert adapter.failure is None, adapter.failure
    assert len(wire.calls) == 1 and calls == {"graph": 1, "source": 1}
    body = json.loads(wire.calls[0].content)
    assert body["tools"] == []
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert "observation-one" not in json.dumps(body) and "review-one" not in json.dumps(
        body
    )
    completed = adapter.complete_build_writer(result)
    loaded = fresh(adapter)
    assert loaded.completion == completed.completion and loaded.status == "completed"
    assert isinstance(loaded.completion, t.BuildGraphCompletionV2)
    (citation,) = loaded.completion.source_citations
    writer = next(
        e
        for e in loaded.graph_context_execution.events
        if isinstance(e, t.ProviderAttemptAuthorizedEventV3)
        and e.provider_attempt_id == citation.provider_attempt_id
    )
    assert citation.envelope_sha256 == sha256(wire.calls[0].content).hexdigest()
    assert (
        writer.included_graph_event_ids
        == writer.included_assertion_ids
        == writer.included_evidence_ref_ids
        == []
    )
    assert citation.read_event_id in writer.included_source_read_event_ids
    assert citation.receipt.content_sha256 == sha256(text.encode()).hexdigest()
    assert citation.receipt.source_revision_id == "source-rev-one"
    assert not hasattr(citation.receipt, "content")
    context = owner.project_plan_turn_context(loaded, delivery_replay=True)
    assert context.completion == loaded.completion
    assert (
        context.source_open_targets == []
    )  # Distinct public/UI reader is a required consumer.


@pytest.mark.parametrize(
    "segments",
    [
        [
            {
                "kind": "graph_claim",
                "claim_id": "fabricated",
                "text": "invented",
                "target_kind": "assertion",
                "target_id": "observation-one",
            }
        ],
        [
            {
                "kind": "source_passage_claim",
                "text": "invented",
                "passage_handles": ["foreign"],
            }
        ],
        [{"kind": "source_passage_claim", "text": "invented", "passage_handles": []}],
        [
            {
                "kind": "source_passage_claim",
                "text": "invented",
                "passage_handles": ["foreign"],
                "receipt": {},
            }
        ],
    ],
)
def test_bad_model_handles_or_graph_claims_are_captured_not_persisted(
    build_case, monkeypatch, segments
):
    adapter, projection, _, _ = stage(build_case, monkeypatch)
    wire = WriterWire(adapter, text=answer(projection, answer_segments=segments))
    result = invoke(adapter, projection, wire)
    with pytest.raises(ValueError):
        adapter.complete_build_writer(result)
    assert fresh(adapter).completion is None
    traces = AgentConversationService().list_context_trace_attempts(
        world_id=adapter.turn.world_id, turn_id=adapter.turn.turn_id
    )
    assert any(
        getattr(o, "kind", None) == "context_snapshot"
        and any(
            m.item_id.startswith("unvalidated-provider-answer:") for m in o.materials
        )
        for trace in traces
        for o in trace.observations
    )


def test_prepared_body_mutation_and_stale_projection_rejected(build_case, monkeypatch):
    adapter, projection, _, _ = stage(build_case, monkeypatch)
    view = prepared(projection)
    from dataclasses import replace

    changed = json.loads(view.body)
    changed["input"] = changed["input"].replace("western", "eastern")
    body = json.dumps(changed).encode()
    assert not adapter.authorize_prepared_build_writer(
        replace(
            view, body=body, body_sha256=sha256(body).hexdigest(), body_size=len(body)
        )
    )
    # A later completed read changes the event sequence; old writer cannot dispatch.
    adapter.read_build_section(line_start=1, line_end=2)
    assert not adapter.authorize_prepared_build_writer(view)


def test_source_and_saved_section_claims_remain_distinct(build_case, monkeypatch):
    adapter, projection, _, _ = stage(build_case, monkeypatch, sections=True)
    packet = json.loads(projection.input_json)
    value = json.loads(answer(projection))
    value["answer_segments"].append(
        {
            "kind": "saved_source_claim",
            "text": "The saved page offers authored context.",
            "section_read_ids": [packet["exposure"]["saved_sections"][0]["read_id"]],
        }
    )
    result = invoke(adapter, projection, WriterWire(adapter, text=json.dumps(value)))
    loaded = adapter.complete_build_writer(result)
    assert loaded.completion.answer_basis == "saved_source_and_opened_passages"
    assert len(loaded.completion.source_citations) == 1
    assert isinstance(loaded.completion.answer_segments[1], t.SavedSourceClaimV1)
    assert fresh(adapter).completion == loaded.completion


@pytest.mark.parametrize(
    "change",
    [
        "foreign_attempt",
        "foreign_envelope",
        "foreign_event",
        "foreign_receipt",
        "omitted_read",
        "controller_only",
        "wrong_text",
    ],
)
def test_app_reload_independently_rejects_citation_forgery(
    build_case, monkeypatch, change
):
    adapter, projection, _, _ = stage(build_case, monkeypatch)
    adapter.complete_build_writer(
        invoke(adapter, projection, WriterWire(adapter, text=answer(projection)))
    )
    data = fresh(adapter).model_dump(mode="json", by_alias=True)
    citation = data["completion"]["source_citations"][0]
    if change == "foreign_attempt":
        citation["provider_attempt_id"] = str(uuid4())
    elif change == "foreign_envelope":
        citation["envelope_sha256"] = "f" * 64
    elif change == "foreign_event":
        citation["read_event_id"] = str(uuid4())
    elif change == "foreign_receipt":
        citation["receipt"]["source_artifact_id"] = "another-source"
    elif change == "wrong_text":
        citation["text_sha256"] = "f" * 64
    elif change in {"omitted_read", "controller_only"}:
        attempts = [
            e
            for e in data["graph_context_execution"]["events"]
            if e["kind"] == "provider_attempt_authorized_v3"
        ]
        attempts[-1]["included_source_read_event_ids"] = []
        if change == "controller_only":
            citation["provider_attempt_id"] = attempts[0]["provider_attempt_id"]
    # Keep completion binding's content hash current to exercise receipt validation,
    # rather than relying on the outer completion digest to catch the forgery.
    binding = data["graph_context_execution"]["events"][-1]
    binding["completion_sha256"] = sha256(
        json.dumps(
            data["completion"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    with pytest.raises(ValueError):
        t.Turn.model_validate(data)


def test_repeated_complete_reads_deduplicate_body_preserve_all_receipts(
    build_case, monkeypatch
):
    adapter, _, text = _start(build_case, monkeypatch)
    graph, source = _acquire(adapter)
    from graph_memory.interaction import expansion_executor

    original = expansion_executor.execute_read_graph_source

    def another(*args, **kwargs):
        value = original(*args, **kwargs)
        value["reads"][0]["sourceReadId"] = "source-read-two"
        value["reads"][0]["receipt"]["source_read_id"] = "source-read-two"
        return value

    monkeypatch.setattr(expansion_executor, "execute_read_graph_source", another)
    adapter.broker_source_read(
        {
            "toolName": "read_graph_source",
            "arguments": {
                "retrievalSessionId": adapter.bootstrap.retrieval_session.id,
                "anchorIds": ["anchor-one"],
                "maxChars": 4000,
            },
        }
    )["resultJson"]
    assert adapter.failure is None, adapter.failure
    projection = adapter.stage_build_source_writer(
        graph_payloads=(graph,), source_read_event_ids=tuple(adapter.source_payloads)
    )
    packet = json.loads(projection.input_json)
    assert (
        len(packet["opened_passages"]) == 1
        and packet["opened_passages"][0]["text"] == text
    )
    loaded = adapter.complete_build_writer(
        invoke(adapter, projection, WriterWire(adapter, text=answer(projection)))
    )
    assert {c.receipt.source_read_id for c in loaded.completion.source_citations} == {
        "source-read-one",
        "source-read-two",
    }
    assert len({c.read_event_id for c in loaded.completion.source_citations}) == 2
    assert fresh(adapter).completion == loaded.completion


def test_truncated_source_refuses_before_writer_dispatch(build_case, monkeypatch):
    adapter, _, _ = _start(build_case, monkeypatch, truncated=True)
    graph, source = _acquire(adapter)
    with pytest.raises(ValueError, match="partial or unadmitted"):
        adapter.stage_build_source_writer(
            graph_payloads=(graph,), source_payloads=(source,)
        )


def test_unselected_source_read_cannot_enter_writer_citations(build_case, monkeypatch):
    adapter, projection, _, _ = stage(build_case, monkeypatch)
    # Projection selects exactly one event. Host completion cannot cite an
    # arbitrary existing/read-capable identifier supplied by the model.
    data = json.loads(answer(projection))
    data["answer_segments"][0]["passage_handles"] = ["source-read-one"]
    result = invoke(adapter, projection, WriterWire(adapter, text=json.dumps(data)))
    with pytest.raises(ValueError):
        adapter.complete_build_writer(result)
    assert fresh(adapter).completion is None


def test_exact_completion_replay_requires_no_new_provider_call(build_case, monkeypatch):
    adapter, projection, _, _ = stage(build_case, monkeypatch)
    wire = WriterWire(adapter, text=answer(projection))
    completed = adapter.complete_build_writer(invoke(adapter, projection, wire))
    binding = completed.graph_context_execution.events[-1]
    command = t.TurnResult(
        world_id=completed.world_id,
        conversation_id=completed.conversation_id,
        turn_id=completed.turn_id,
        expected_revision=completed.revision - 1,
        assistant_text=completed.assistant_text,
        completion=completed.completion,
        producing_provider_attempt_id=binding.provider_attempt_id,
        claim_graph_event_ids={},
    )
    assert AgentConversationService().complete_turn(command) == completed
    assert len(wire.calls) == 1


def test_historical_attribution_survives_work_edit_without_latest_lookup(
    build_case, monkeypatch
):
    adapter, projection, _, text = stage(build_case, monkeypatch)
    completed = adapter.complete_build_writer(
        invoke(adapter, projection, WriterWire(adapter, text=answer(projection)))
    )
    receipt = completed.completion.source_citations[0].receipt
    # A later authoring working copy is not allowed to replace historical text.
    from dataclasses import replace

    later = "The eastern gate is not haunted."
    adapter.work = replace(
        adapter.work,
        build_source=replace(
            adapter.work.build_source,
            markdown=later,
            content_sha256=sha256(later.encode()).hexdigest(),
        ),
    )
    loaded = fresh(adapter)
    pinned = loaded.completion.source_citations[0].receipt
    assert (
        pinned == receipt and pinned.content_sha256 == sha256(text.encode()).hexdigest()
    )
    assert pinned.source_revision_id == "source-rev-one"
    assert pinned.content_sha256 != sha256(later.encode()).hexdigest()


def test_writer_can_abstain_when_opened_passages_do_not_answer(build_case, monkeypatch):
    adapter, projection, _, _ = stage(build_case, monkeypatch)
    output = json.dumps(
        {
            "answer_context_status": "source_insufficient_evidence",
            "answer_segments": [
                {
                    "kind": "connective",
                    "text": "The opened sources do not establish who operates the radio.",
                }
            ],
        }
    )
    loaded = adapter.complete_build_writer(
        invoke(adapter, projection, WriterWire(adapter, text=output))
    )
    assert loaded.completion.source_citations == []
    assert loaded.completion.answer_context_status == "source_insufficient_evidence"
    assert fresh(adapter).completion == loaded.completion


@pytest.mark.parametrize(
    "field,value",
    [
        ("sourceArtifactId", "another-subject-source"),
        ("evidenceRefId", "foreign-evidence"),
        ("anchorId", "foreign-anchor"),
        ("lineStart", 99),
        ("content", "A different unsupported passage."),
    ],
)
def test_parent_source_mapping_mismatch_cannot_cross_into_projection(
    build_case, monkeypatch, field, value
):
    adapter, _, _ = _start(build_case, monkeypatch)
    graph, source = _acquire(adapter)
    (event_id,) = adapter.source_payloads
    raw = json.loads(adapter.source_payloads[event_id])
    raw[field] = value
    adapter.source_payloads[event_id] = json.dumps(raw)
    with pytest.raises(ValueError):
        adapter.stage_build_source_writer(
            graph_payloads=(graph,), source_payloads=(source,)
        )


@pytest.mark.parametrize("change", ["partial", "truncated", "insufficient"])
def test_app_citation_model_rejects_incomplete_receipt(build_case, monkeypatch, change):
    adapter, projection, _, _ = stage(build_case, monkeypatch)
    adapter.complete_build_writer(
        invoke(adapter, projection, WriterWire(adapter, text=answer(projection)))
    )
    data = fresh(adapter).completion.model_dump(mode="json", by_alias=True)
    receipt = data["source_citations"][0]["receipt"]
    if change == "partial":
        receipt["outcome"] = "partial"
    elif change == "truncated":
        receipt["truncated"] = True
    else:
        receipt["evidence_sufficiency_status"] = "insufficient"
    with pytest.raises(ValueError, match="complete, sufficient"):
        t.BuildGraphCompletionV2.model_validate(data)
