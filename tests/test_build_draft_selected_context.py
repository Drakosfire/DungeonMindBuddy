"""Full draft plus selected saved authority at actual SDK and APP boundaries."""

import json
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4

import httpx
import httpx2
import pytest

from application_state.agent_conversation import AgentConversationService, types as t
from application_state.agent_conversation import build_primary_context as primary
from application_state.agent_conversation.build_draft_context import (
    BuildDraftContextRequestV1,
    BuildDraftSnapshotV1,
)
from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.services import build_jev_writer as writer
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.test_build_draft_context import draft_build_case as _draft_build_case
from tests.test_build_jev_estimated_continuations import counter
from tests.test_build_writer_selection import SelectionWire
from tests.test_agent_build_jev_ordinary_harness import WriterWire, ordinary_case
from tests.test_agent_build_governed_graph import execute


@pytest.fixture
def draft_build_case(tmp_path, monkeypatch, application_state_dsn):
    return _draft_build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


class FiveReads(SelectionWire):
    def __init__(self):
        super().__init__("saved_only")
        self.read_count = 0

    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        body, data = json.loads(request.content), response.json()
        selecting = body["state"].get("writer_selection_policy")
        for key, answer in data["answers"].items():
            if selecting:
                source_id = (
                    body["questions"][key]["instructions"]
                    .removeprefix("Classify source ")
                    .removesuffix(" for the exact user question.")
                )
                source = body["state"]["sources"][source_id]
                choice = (
                    "direct_support"
                    if source["text"].startswith("Selected saved fact.")
                    else "irrelevant"
                )
            elif key == "next":
                choice = next(
                    (
                        x
                        for x in body["questions"][key]["criteria"]
                        if x.startswith("saved:")
                    ),
                    "none",
                )
                if choice != "none":
                    self.read_count += 1
            elif key == "sufficiency":
                choice = "sufficient" if self.read_count >= 5 else "more_evidence"
            else:
                continue
            answer.update(
                choice=choice,
                probabilities={
                    x: float(x == choice) for x in body["questions"][key]["criteria"]
                },
            )
        return httpx2.Response(200, request=request, json=data)


class SelectedWriter(WriterWire):
    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        packet = json.loads(json.loads(request.content)["input"])
        (row,) = primary.packet_rows(packet)
        data = response.json()
        data["output"][0]["content"][0]["text"] = json.dumps(
            {
                "answer_context_status": "authored_grounded",
                "answer_segments": [
                    {
                        "kind": "saved_source_claim",
                        "text": "Selected saved fact.",
                        "section_read_ids": [row["read_id"]],
                    }
                ],
                "limitations": ["partial_retrieval"],
                "requested_detail_gaps": [],
            }
        )
        return httpx.Response(200, request=request, json=data)


@pytest.fixture
def selected_turn(draft_build_case, monkeypatch, tmp_path):
    from apps.live_control_server.services.workspace_document_registry import (
        get_workspace_document_snapshot,
    )
    from tests.application_state.test_agent_conversation_postgres import _new

    source, request, bootstrap = draft_build_case
    lines = ["Selected saved fact. " + "a" * 10300 + "\n"] + [
        f"Other section {i}. " + str(i) * 10300 + "\n" for i in range(4)
    ]
    saved = "".join(lines)
    (tmp_path / source.record.target_relpath).write_text(saved)
    source = get_workspace_document_snapshot(tmp_path, source.record.document_id)
    request = request.model_copy(
        update={
            "primary_work": request.primary_work.model_copy(
                update={"expected_content_sha256": source.content_sha256}
            )
        }
    )
    service = AgentConversationService()
    conversation = _new(service, "elderwyld")
    # Similar content, different formatting: exact-body alias cannot remove it.
    draft = "# Working page\n" + saved.replace("Other section", "Revised section")
    snap = BuildDraftSnapshotV1(
        world_id="elderwyld",
        document_id=source.record.document_id,
        registry_revision=source.loaded_revision,
        content_sha256=source.content_sha256,
        visibility="internal",
        draft_markdown=draft,
        draft_sha256=sha256(draft.encode()).hexdigest(),
        editor_sha256="b" * 64,
        draft_generation=1,
    )
    context = BuildDraftContextRequestV1(
        snapshot=snap,
        conversation_id=conversation.conversation_id,
        expected_pointer_revision=service.get_world_pointer("elderwyld").revision,
    )
    request = AgentTurnRequest.model_validate(
        {
            **request.model_dump(mode="json", by_alias=True),
            "turn_id": str(uuid4()),
            "build_write_capability": None,
            "build_draft_context": context.model_dump(mode="json", by_alias=True),
        }
    )
    case, reads = ordinary_case((source, request, bootstrap), monkeypatch)
    decisions, transport = FiveReads(), SelectedWriter()
    harness = BuildJevHarness(
        world_context=True,
        named_citations=True,
        accounting=counter(),
        decision_transport=decisions,
        writer_transport=transport,
    )
    result = execute(case, tmp_path, harness)
    (turn,) = service.list_turns("elderwyld", conversation.conversation_id)
    packet = json.loads(json.loads(transport.calls[0].content)["input"])
    return service, turn, packet, transport, result, draft


def test_five_acquired_sections_full_draft_one_selected_saved_citation(selected_turn):
    service, turn, packet, transport, result, draft = selected_turn
    execution = turn.graph_context_execution
    acquired = [
        e for e in execution.events if isinstance(e, t.ValidatedBuildSectionReadV1)
    ]
    assert len(acquired) == 5 and len(primary.records(execution)) == 1
    assert execution.policy.primary_work_context_policy == primary.DRAFT_POLICY
    assert packet["schema"] == primary.DRAFT_SCHEMA
    assert packet["working_draft_context"]["draft_markdown"] == draft
    assert len(transport.calls) == 1 and len(transport.calls[0].content) < 128000
    chosen = primary.selection(execution)
    assert {str(x) for x in chosen.section_read_ids} == {
        x["read_id"] for x in primary.packet_rows(packet)
    }
    assert result.answer.status == "ok"
    from apps.live_control_server.services.agent_saved_sections import (
        saved_section_targets,
        open_saved_section,
    )

    (target,) = saved_section_targets(turn)
    opened = open_saved_section(
        world_id=turn.world_id,
        turn_id=turn.turn_id,
        segment_index=target.segment_index,
        section_event_id=target.section_event_id,
        service=service,
    )
    assert opened.content == primary.records(execution)[0].text
    assert t.Turn.model_validate_json(turn.model_dump_json(by_alias=True)) == turn
    historical = execution.policy.model_dump(mode="json", by_alias=True)
    historical["primary_work_context_policy"] = primary.POLICY
    parsed = type(execution.policy).model_validate(historical)
    assert parsed.model_dump(mode="json", by_alias=True) == historical
    old = execution.model_copy(update={"policy": parsed})
    assert len(primary.records(old)) == 5


@pytest.mark.parametrize(
    "fault",
    [
        "missing_draft",
        "wrong_schema",
        "unselected",
        "changed_text",
        "basis",
        "late",
        "missing_capture",
        "foreign_selection",
    ],
)
def test_new_projection_refuses_invalid_authority(selected_turn, fault):
    _, turn, packet, _, _, _ = selected_turn
    packet = deepcopy(packet)
    ex = turn.graph_context_execution
    basis = turn.graph_context_receipt.source_basis
    if fault == "missing_draft":
        packet.pop("working_draft_context")
    elif fault == "wrong_schema":
        packet["schema"] = primary.SCHEMA
    elif fault == "unselected":
        row = next(
            e
            for e in ex.events
            if isinstance(e, t.ValidatedBuildSectionReadV1)
            and e.read_id not in primary.selection(ex).section_read_ids
        )
        packet["artifact_under_edit"]["sections"].append(
            {
                "read_id": str(row.read_id),
                "line_start": row.line_start,
                "line_end": row.line_end,
                "text": row.text,
            }
        )
    elif fault == "changed_text":
        packet["artifact_under_edit"]["sections"][0]["text"] = "Unsent claim"
    elif fault == "basis":
        basis = basis.model_copy(update={"content_sha256": "f" * 64})
    else:
        events = list(ex.events)
        if fault == "missing_capture":
            events = [
                e for e in events if not isinstance(e, t.BuildDraftContextCapturedV1)
            ]
        elif fault == "foreign_selection":
            events = [
                e.model_copy(update={"section_read_ids": [uuid4()]})
                if isinstance(e, t.BuildWriterEvidenceSelectionV1)
                else e
                for e in events
            ]
        else:
            boundary = primary.selection(ex).sequence
            selected = primary.selection(ex).section_read_ids[0]
            row = next(
                e
                for e in events
                if isinstance(e, t.ValidatedBuildSectionReadV1)
                and e.read_id == selected
            )
            events = [e for e in events if e is not row]
            events.insert(boundary + 1, row)
        ex = ex.model_copy(update={"events": events})
    with pytest.raises(ValueError):
        primary.validate_packet(packet, ex, basis)


@pytest.mark.parametrize("context_only", [False, True])
def test_real_sdk_capacity_refusal_has_no_writer_send_and_keeps_cause(
    draft_build_case, monkeypatch, tmp_path, context_only
):
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
    )

    original = writer.validate_body

    def capacity(payload, expected, **kwargs):
        original(payload, expected, **kwargs)
        raise writer.WriterCapacityError(
            "Synthetic owning-boundary capacity refusal",
            code="build_writer_context_over_budget"
            if context_only
            else "build_writer_request_over_budget",
            actual=128001,
            limit=128000,
        )

    monkeypatch.setattr(writer, "validate_body", capacity)
    case, _ = ordinary_case(draft_build_case, monkeypatch)
    transport = WriterWire()
    harness = BuildJevHarness(
        accounting=counter(),
        decision_transport=SelectionWire("saved_only"),
        writer_transport=transport,
    )
    with pytest.raises(AgentTurnServiceError) as error:
        execute(case, tmp_path, harness)
    assert error.value.code == (
        "build_writer_context_over_budget"
        if context_only
        else "build_writer_request_over_budget"
    )
    assert transport.calls == []
    service = AgentConversationService()
    (turn,) = service.list_turns(
        "elderwyld", service.get_world_pointer("elderwyld").active_conversation_id
    )
    assert turn.status == "interrupted" and turn.completion is None
    traces = service.list_context_trace_attempts(
        world_id="elderwyld", turn_id=turn.turn_id
    )
    assert any(
        e.kind == "failure"
        and e.phase == "context_build"
        and e.code == error.value.code
        for trace in traces
        for e in trace.observations
    )
    assert any(
        e.kind == "failure" and e.phase == "delivery" and e.code == error.value.code
        for trace in traces
        for e in trace.observations
    )
    assert all(
        (e.provider, e.model, e.api_mode)
        != turn.graph_context_execution.policy.provider_roles.writer.identity()
        for e in turn.graph_context_execution.events
        if isinstance(e, t.ProviderAttemptAuthorizedEventV1)
    )


def test_current_writer_refuses_historical_draft_policy_and_distinguishes_contract_failure(
    monkeypatch,
):
    from types import SimpleNamespace
    from apps.live_control_server.services.agent_turn_service import (
        _PolicyExecutionAdapter,
    )

    policy = SimpleNamespace(
        working_draft_context_policy="captured_build_working_draft_context_v1",
        primary_work_context_policy=primary.POLICY,
    )
    adapter = SimpleNamespace(
        _is_build_turn=lambda: True,
        failure=None,
        fence=object(),
        _build_writer_projection=SimpleNamespace(
            event_sequence=0, prior_provider_attempt_id=None
        ),
        _broker_execution=lambda: SimpleNamespace(events=[], policy=policy),
        last_provider_attempt_id=None,
        _frozen_build_writer_budget=lambda: writer.role_budget(),
        context_capture=None,
    )
    assert not _PolicyExecutionAdapter.authorize_prepared_build_writer(
        adapter, object()
    )
    policy.primary_work_context_policy = primary.DRAFT_POLICY

    def invalid(*args, **kwargs):
        raise ValueError("Exact body or schema differs")

    monkeypatch.setattr(writer, "prepared_view", invalid)
    assert not _PolicyExecutionAdapter.authorize_prepared_build_writer(
        adapter, object()
    )
    assert adapter.writer_admission_failure is None
    from pydantic import TypeAdapter

    with pytest.raises(ValueError):
        TypeAdapter(
            t.BuildNamedWorldContextPolicyV1.model_fields[
                "primary_work_context_policy"
            ].annotation
        ).validate_python(primary.DRAFT_POLICY)


def test_metadata_fence_preserves_every_disposable_row(
    selected_turn, application_state_dsn
):
    import psycopg
    from psycopg import sql
    from importlib import import_module

    def rows():
        with psycopg.connect(application_state_dsn) as conn:
            tables = conn.execute(
                "SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY schemaname,tablename"
            ).fetchall()
            return {
                (schema, name): conn.execute(
                    sql.SQL(
                        "SELECT row_to_json(t)::text FROM {}.{} t ORDER BY row_to_json(t)::text"
                    ).format(sql.Identifier(schema), sql.Identifier(name))
                ).fetchall()
                for schema, name in tables
            }

    before = rows()
    migration = import_module(
        "application_state.migrations.versions.20261028_0084_build_draft_selected_context"
    )
    migration.upgrade()
    with pytest.raises(RuntimeError, match="recovery forward"):
        migration.downgrade()
    assert rows() == before
