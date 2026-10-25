"""Installed migration and transaction boundaries, using disposable PostgreSQL."""

from copy import deepcopy
from importlib import import_module
import psycopg
from psycopg.types.json import Jsonb
import pytest
from application_state.agent_conversation import build_intentional_response as c
from application_state.agent_conversation import types as t
from tests.test_build_intentional_response import run_no_editor


def test_installed_lifecycle_retains_object_only_turn_and_rejects_empty_or_historical_shape(
    tmp_path, monkeypatch, application_state_dsn
):
    turn, service, _, _ = run_no_editor(
        tmp_path, monkeypatch, application_state_dsn, "clarify_request"
    )
    with psycopg.connect(application_state_dsn) as conn:
        installed = conn.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='agent.turn'::regclass AND conname='agent_turn_lifecycle_check'"
        ).fetchone()[0]
        assert c.COMPLETION in installed
        row = conn.execute(
            "SELECT assistant_text, completion FROM agent.turn WHERE turn_id=%s",
            (turn.turn_id,),
        ).fetchone()
        assert row[0] == "" and row[1]["collaboration"]["kind"] == "questions"
        for mutate in (
            lambda x: x.update(collaboration=None),
            lambda x: x.update(schema="dmb_build_collaboration_completion_v1"),
            lambda x: x.update(
                answer_segments=[], collaboration={"kind": "questions", "questions": []}
            ),
        ):
            changed = deepcopy(row[1])
            mutate(changed)
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    conn.execute(
                        "UPDATE agent.turn SET completion=%s WHERE turn_id=%s",
                        (Jsonb(changed), turn.turn_id),
                    )
        assert (
            service.list_turns("elderwyld", turn.conversation_id)[0].assistant_text
            == ""
        )
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    engine = create_engine(
        application_state_dsn.replace("postgresql://", "postgresql+psycopg://")
    )
    try:
        with (
            engine.begin() as conn,
            Operations.context(MigrationContext.configure(conn)),
        ):
            with pytest.raises(RuntimeError, match="recovery forward"):
                import_module(
                    "application_state.migrations.versions.20261025_0070_intentional_build_response"
                ).downgrade()
    finally:
        engine.dispose()


def test_actual_selection_proof_rejects_changed_bytes_missing_capture_and_changed_argument_joins(
    tmp_path, monkeypatch, application_state_dsn
):
    turn, _, decisions, _ = run_no_editor(
        tmp_path, monkeypatch, application_state_dsn, "discuss"
    )
    selection = next(
        e
        for e in turn.graph_context_execution.events
        if isinstance(e, t.BuildRequestedWorkResolutionV1)
    )
    with psycopg.connect(application_state_dsn) as conn:
        trace = conn.execute(
            "SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s",
            (turn.turn_id, turn.attempt),
        ).fetchone()[0]
    captured = [
        m
        for o in trace["observations"]
        if o["kind"] == "context_snapshot"
        for m in o["materials"]
        if m["item_id"].startswith(
            f"unvalidated-controller-decision:{selection.controller_attempt_id}:"
        )
    ]
    proof = {
        "request_json": decisions.calls[0].content.decode(),
        "response_json": captured[0]["text"],
    }
    c.validate_selection(turn, selection, proof, trace)
    for changed in (
        {**proof, "request_json": proof["request_json"] + " "},
        {**proof, "response_json": proof["response_json"] + " "},
    ):
        with pytest.raises(ValueError):
            c.validate_selection(turn, selection, changed, trace)
    with pytest.raises(ValueError, match="not captured"):
        c.validate_selection(turn, selection, proof, {})
    with pytest.raises(ValueError):
        c.validate_selection(
            turn,
            selection.model_copy(update={"arguments_sha256": "0" * 64}),
            proof,
            trace,
        )
    changed = turn.model_dump(mode="json", by_alias=True)
    next(
        e
        for e in changed["graph_context_execution"]["events"]
        if e["kind"] == "build_requested_work_resolved_v1"
    )["arguments_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="exact turn arguments"):
        t.Turn.model_validate(changed)
