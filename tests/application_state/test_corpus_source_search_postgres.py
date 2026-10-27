"""The actual APP persistence/downgrade boundary, using disposable PostgreSQL."""
import asyncio
from importlib import import_module
import psycopg
import pytest
from sqlalchemy import create_engine
from alembic.migration import MigrationContext
from alembic.operations import Operations
from application_state.agent_conversation import types as t
from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
from tests.test_plan_jev_dispatch import plan_adapter  # noqa:F401
from tests.test_corpus_source_navigation import corpus, Decisions  # noqa:F401


def stage(corpus):
    adapter,_=corpus
    asyncio.run(PlanJevDriver(adapter).run(transport=Decisions(),api_key='synthetic-not-secret'))
    return adapter,adapter.fence.turn


def test_corpus_events_require_explicit_frozen_capability_in_database(corpus, application_state_dsn):
    _,turn=stage(corpus)
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("UPDATE agent.turn SET graph_context_execution=graph_context_execution #- '{policy,corpus_source_policy}' WHERE turn_id=%s",(turn.turn_id,))


def test_populated_corpus_downgrade_refuses_authority_loss(corpus, application_state_dsn):
    stage(corpus)
    engine=create_engine(application_state_dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError,match='recover forward'):
                    import_module('application_state.migrations.versions.20261027_0079_corpus_source_search').downgrade()
    finally:engine.dispose()


def test_exact_search_receipts_replay_without_another_scan(corpus, monkeypatch):
    from apps.live_control_server.services import corpus_source_navigation
    adapter,turn=stage(corpus)
    monkeypatch.setattr(corpus_source_navigation,'collect_source_view',lambda *a,**kw:pytest.fail('receipt replay scanned sources'))
    grant=next(e for e in turn.graph_context_execution.events if isinstance(e,t.CorpusSourceSearchAuthorizedV1))
    replay,fresh=adapter.service.authorize_corpus_source_search(turn.world_id,turn.conversation_id,turn.turn_id,
        expected_revision=turn.revision,expected_attempt=turn.attempt,authorization=grant)
    assert not fresh and replay.revision==turn.revision
    result=next(e for e in turn.graph_context_execution.events if isinstance(e,t.CorpusSourceSearchObservedV1))
    replay,fresh=adapter.service.record_corpus_source_search(turn.world_id,turn.conversation_id,turn.turn_id,
        expected_revision=turn.revision,expected_attempt=turn.attempt,observation=result)
    assert not fresh and replay.revision==turn.revision
