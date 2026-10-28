"""Shared real mocked SDK → proposal APP → authoring completion/reload; synthetic."""

import asyncio
import json
from hashlib import sha256
from importlib import import_module
from types import SimpleNamespace
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.types.json import Jsonb
from generationengine.text_dispatch import TextDispatchGate

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.build_authoring import (
    completion_for_proposal,
    proposal_result_digest,
)
from application_state.build_proposal.service import BuildProposalService
from application_state.build_proposal.types import BuildProposalOrigin
from application_state.errors import (
    ApplicationStateIntegrityError,
    ApplicationStateValidationError,
)
from apps.live_control_server.models.build_document_proposal import (
    BuildDocumentProposalRequest,
)
from apps.live_control_server.services import build_document_proposal as owner
from tests.test_agent_build_jev_dispatch import (
    _adapter,
    _invoke,
    Wire as DecisionWire,
    build_case as _build_case,
)
from tests.test_build_document_proposal import Wire


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def prepare(build_case, monkeypatch):
    source, request, _ = build_case
    adapter, state = _adapter(build_case)
    _invoke(adapter, state, DecisionWire(adapter), [])
    service = AgentConversationService()
    holder = SimpleNamespace(turn=adapter.turn)
    from apps.live_control_server.routes import agent

    root = agent._managed_world_root()
    # This fixture's managed-World resolution is synthetic; source registry and
    # immutable source/proposal/conversation storage remain actual APP owners.
    monkeypatch.setattr(
        owner, "get_world_container", lambda *_: SimpleNamespace(world_id="elderwyld")
    )
    monkeypatch.setattr(owner, "managed_world_data_root", lambda: root)
    monkeypatch.setattr(owner, "_model", lambda: "gpt-6-luna")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-only")
    monkeypatch.setenv("DMB_AGENT_PROMPT_CAPTURE", "1")
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(root))
    instruction = "Suggest an invented NPC table."
    args_sha = sha256(
        json.dumps(
            {"instruction": instruction}, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    proposal_request = BuildDocumentProposalRequest(
        idempotency_key=uuid4(),
        conversation_id=holder.turn.conversation_id,
        expected_pointer_revision=service.get_world_pointer("elderwyld").revision,
        instruction=instruction,
        draft_markdown=source.markdown,
        basis=dict(
            world_id="elderwyld",
            document_id=source.record.document_id,
            registry_revision=source.loaded_revision,
            content_sha256=source.content_sha256,
            visibility="internal",
            draft_sha256=sha256(source.markdown.encode()).hexdigest(),
            caret=0,
            draft_generation=0,
            selection_generation=0,
        ),
        origin=BuildProposalOrigin(
            client_turn_id=UUID(request.turn_id),
            durable_turn_id=holder.turn.turn_id,
            turn_attempt=holder.turn.attempt,
            broker_operation_id="host:propose-one",
            arguments_sha256=args_sha,
        ),
    )

    async def authorize(prepared):
        turn = holder.turn
        first = turn.graph_context_execution.events[0]
        event = t.ProviderAttemptAuthorizedEventV3.model_validate(
            {
                **first.model_dump(mode="json"),
                "event_id": str(uuid4()),
                "sequence": len(turn.graph_context_execution.events),
                "provider_attempt_id": prepared.attempt_id,
                "provider": prepared.provider,
                "model": prepared.model,
                "api_mode": prepared.api_mode,
                "envelope_sha256": prepared.body_sha256,
                "serializer_version": "openai-sdk-json-v1",
                "tool_schema_sha256": sha256(b"[]").hexdigest(),
                "input_tokens": len(prepared.body),
                "output_token_reserve": 4096,
            }
        )
        holder.turn, fresh = service.authorize_provider_attempt_v2(
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
            expected_attempt=turn.attempt,
            provider_attempt_event=event,
        )
        return fresh

    async def lifecycle(event):
        turn = holder.turn
        outcome = t.ProviderOutcomeEventV1(
            event_id=uuid4(),
            sequence=len(turn.graph_context_execution.events),
            kind="provider_outcome",
            provider_attempt_id=UUID(event.request.attempt_id),
            outcome={"sending": "sdk_entered"}.get(event.outcome, event.outcome),
            status_code=event.http_status,
        )
        holder.turn, fresh = service.record_provider_outcome(
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
            expected_attempt=turn.attempt,
            outcome=outcome,
        )
        return fresh

    wire = Wire(proposal_request)
    record = asyncio.run(
        owner.compose_with_writer(
            proposal_request, TextDispatchGate(authorize, lifecycle),
            writer_model=holder.turn.graph_context_execution.policy.provider_roles.writer.model, transport=wire
        )
    )
    completion = completion_for_proposal(record, holder.turn.graph_context_receipt)
    result = t.TurnResult(
        world_id=holder.turn.world_id,
        conversation_id=holder.turn.conversation_id,
        turn_id=holder.turn.turn_id,
        expected_revision=holder.turn.revision,
        assistant_text=t.BUILD_PROPOSAL_READY_TEXT,
        completion=completion,
        producing_provider_attempt_id=record.authorization.provider_attempt_id,
        claim_graph_event_ids={},
    )
    return service, holder.turn, record, result, wire


def test_shared_sdk_proposal_completes_reloads_and_recovers_without_another_call(
    build_case, monkeypatch
):
    service, turn, record, result, wire = prepare(build_case, monkeypatch)
    assert record.state == "proposed" and len(wire.calls) == 1
    # Proposal persisted but turn completion missing: only APP completion remains.
    assert (
        service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id).completion
        is None
    )
    done = service.complete_turn(result)
    from apps.live_control_server.models.agent_turn import (
        AgentBuildGraphContextResponseV1,
    )

    response = AgentBuildGraphContextResponseV1(
        saved_source_name=None,
        receipt=done.graph_context_receipt,
        completion=done.completion,
        execution=None,
        delivery_replay=True,
    )
    assert (
        AgentBuildGraphContextResponseV1.model_validate_json(
            response.model_dump_json(by_alias=True)
        ).completion
        == done.completion
    )
    assert (
        done.completion == result.completion
        and done.assistant_text == t.BUILD_PROPOSAL_READY_TEXT
    )
    assert service.complete_turn(result) == done and len(wire.calls) == 1
    assert service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id) == done
    before = proposal_result_digest(record)
    inserted = BuildProposalService().report_inserted(
        turn.world_id, record.action_id, expected_revision=record.revision
    )
    assert inserted.inserted_in_draft and proposal_result_digest(inserted) == before
    assert (
        service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id).completion
        == done.completion
    )


@pytest.mark.parametrize(
    "field",
    [
        "action_id",
        "reservation_sha256",
        "proposal_result_sha256",
        "envelope_sha256",
        "provider_attempt_id",
    ],
)
def test_wrong_proposal_completion_identity_is_refused(build_case, monkeypatch, field):
    service, _, _, result, wire = prepare(build_case, monkeypatch)
    data = result.completion.model_dump(mode="json", by_alias=True)
    data[field] = (
        str(uuid4()) if field in {"action_id", "provider_attempt_id"} else "f" * 64
    )
    altered = result.model_copy(
        update={"completion": t.BuildAuthoringCompletionV1.model_validate(data)}
    )
    with pytest.raises(
        (ApplicationStateIntegrityError, ApplicationStateValidationError, ValueError)
    ):
        service.complete_turn(altered)
    assert len(wire.calls) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "body",
        "origin",
        "source",
        "state",
        "conversation",
        "client",
        "arguments",
        "provider",
    ],
)
def test_owner_record_drift_is_rejected_at_completion(
    build_case, monkeypatch, application_state_dsn, mutation
):
    service, turn, record, result, _ = prepare(build_case, monkeypatch)
    data = record.model_dump(mode="json")
    if mutation == "body":
        data["proposal"]["replacement_markdown"] += "\nForged fact"
    elif mutation == "state":
        data["state"], data["proposal"] = "unknown", None
    elif mutation == "provider":
        data["authorization"]["model"] = "unrelated-model"
    elif mutation in {"conversation", "client", "arguments"}:
        if mutation == "conversation":
            data["reservation"]["conversation_id"] = str(uuid4())
        else:
            field = "client_turn_id" if mutation == "client" else "arguments_sha256"
            data["reservation"]["origin"][field] = (
                str(uuid4()) if mutation == "client" else "f" * 64
            )
        from application_state.build_proposal.types import BuildProposalReservation

        data["request_fingerprint"] = BuildProposalReservation.model_validate(
            data["reservation"]
        ).fingerprint
    else:
        key = "origin" if mutation == "origin" else "basis"
        field = "turn_attempt" if mutation == "origin" else "registry_revision"
        data["reservation"][key][field] += 1
        from application_state.build_proposal.types import BuildProposalReservation

        data["request_fingerprint"] = BuildProposalReservation.model_validate(
            data["reservation"]
        ).fingerprint
    with psycopg.connect(application_state_dsn) as conn:
        if mutation == "conversation":
            # The proposal's existing SQL invariant already rejects this before
            # the completion owner can encounter an inconsistent record.
            with pytest.raises(psycopg.errors.CheckViolation):
                conn.execute(
                    "UPDATE agent.build_proposal SET payload=%s WHERE action_id=%s",
                    (Jsonb(data), record.action_id),
                )
            return
        conn.execute(
            "UPDATE agent.build_proposal SET payload=%s WHERE action_id=%s",
            (Jsonb(data), record.action_id),
        )
    with pytest.raises(ApplicationStateIntegrityError):
        service.complete_turn(result)
    assert (
        service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id).completion
        is None
    )


def test_history_rechecks_owner_result_even_if_turn_digest_is_untouched(
    build_case, monkeypatch, application_state_dsn
):
    service, turn, record, result, _ = prepare(build_case, monkeypatch)
    service.complete_turn(result)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE agent.build_proposal SET payload=jsonb_set(payload, '{proposal,summary}', '\"changed\"') WHERE action_id=%s",
            (record.action_id,),
        )
    with pytest.raises(ApplicationStateIntegrityError):
        service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)


def test_no_model_authored_ack_or_direct_sql_grounding(
    build_case, monkeypatch, application_state_dsn
):
    service, turn, _, result, _ = prepare(build_case, monkeypatch)
    with pytest.raises(ValueError, match="derived by the host"):
        t.BuildAuthoringCompletionV1.model_validate(
            {
                **result.completion.model_dump(by_alias=True),
                "answer_segments": [
                    {"kind": "connective", "text": "I saved and published it."}
                ],
            }
        )
    service.complete_turn(result)
    forged = result.completion.model_dump(mode="json", by_alias=True)
    forged["answer_context_status"] = "graph_grounded"
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "UPDATE agent.turn SET completion=%s WHERE turn_id=%s",
                (Jsonb(forged), turn.turn_id),
            )


def test_downgrade_refuses_retained_authoring_completion(
    build_case, monkeypatch, application_state_dsn
):
    service, _, _, result, _ = prepare(build_case, monkeypatch)
    service.complete_turn(result)
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine

    migration = import_module(
        "application_state.migrations.versions.20261017_0030_build_authoring_completion"
    )
    engine = create_engine(
        application_state_dsn.replace("postgresql://", "postgresql+psycopg://")
    )
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError, match="retained Build authoring"):
                    migration.downgrade()
    finally:
        engine.dispose()


def test_migration_can_downgrade_and_upgrade_without_retained_authoring(
    application_state_dsn,
):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine

    migration = import_module(
        "application_state.migrations.versions.20261017_0030_build_authoring_completion"
    )
    engine = create_engine(
        application_state_dsn.replace("postgresql://", "postgresql+psycopg://")
    )
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                migration.downgrade()
                migration.upgrade()
    finally:
        engine.dispose()
