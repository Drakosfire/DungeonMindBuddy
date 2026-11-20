"""V2's SQL/reload boundary preserves older Build completion contracts."""

import json
from hashlib import sha256
from importlib import import_module

import psycopg
import pytest
from psycopg.types.json import Jsonb
from alembic.migration import MigrationContext
from alembic.operations import Operations

from application_state.agent_conversation import AgentConversationService
from tests.test_agent_build_source_passage_writer import (
    stage,
    answer,
    fresh,
    build_case as _build_case,
)
from tests.test_agent_build_jev_single_writer import WriterWire, invoke


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def complete(build_case, monkeypatch):
    adapter, projection, _, _ = stage(build_case, monkeypatch)
    adapter.complete_build_writer(
        invoke(adapter, projection, WriterWire(adapter, text=answer(projection)))
    )
    return adapter


def test_direct_sql_rejects_graph_disguised_as_source_claim(
    build_case, monkeypatch, application_state_dsn
):
    adapter = complete(build_case, monkeypatch)
    data = fresh(adapter).completion.model_dump(mode="json", by_alias=True)
    data["answer_segments"][0]["kind"] = "graph_claim"
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "UPDATE agent.turn SET completion=%s WHERE turn_id=%s",
                (Jsonb(data), adapter.turn.turn_id),
            )
    assert fresh(adapter).completion.answer_segments[0].kind == "source_passage_claim"


def test_downgrade_refuses_retained_v2(build_case, monkeypatch, application_state_dsn):
    complete(build_case, monkeypatch)
    migration = import_module(
        "application_state.migrations.versions.20261017_0029_build_source_passage_completion"
    )
    from sqlalchemy import create_engine

    engine = create_engine(
        application_state_dsn.replace("postgresql://", "postgresql+psycopg://")
    )
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError, match="retained source-passage"):
                    migration.downgrade()
    finally:
        engine.dispose()


def test_fresh_repository_rejects_sql_receipt_forgery(
    build_case, monkeypatch, application_state_dsn
):
    adapter = complete(build_case, monkeypatch)
    loaded = fresh(adapter)
    data = loaded.completion.model_dump(mode="json", by_alias=True)
    data["source_citations"][0]["receipt"]["source_revision_id"] = (
        "latest-unrelated-revision"
    )
    execution = loaded.graph_context_execution.model_dump(mode="json", by_alias=True)
    execution["events"][-1]["completion_sha256"] = sha256(
        json.dumps(
            data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    # Shape-correct SQL can never replace the independent APP receipt checks.
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET completion=%s, graph_context_execution=%s WHERE turn_id=%s",
            (Jsonb(data), Jsonb(execution), loaded.turn_id),
        )
    with pytest.raises(ValueError, match="Passage citation was not included") as caught:
        AgentConversationService().list_turns(loaded.world_id, loaded.conversation_id)
    assert caught.value is not None
