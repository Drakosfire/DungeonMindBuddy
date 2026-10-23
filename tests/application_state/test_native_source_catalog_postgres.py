"""Real APP immutable source/catalog boundary; no model or retained corpus IO."""
from hashlib import sha256
from uuid import uuid4
import json

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation import native_source_catalog as catalog
from application_state.source import service as sources
from application_state.errors import ApplicationStateValidationError, ApplicationStateConflictError
from tests.application_state.test_native_source_navigation_postgres import nav_case, authorization, persist  # noqa: F401

TEXT = "# Synthetic road\r\nA quiet marsh 🦉.\r\n## Appendix A\r\nTree mechanics.\r\n"


def grant(nav_case, *, markdown=TEXT, source_values=None, reference=None):
    service, turn, donor, pin = nav_case
    digest = sha256(markdown.encode("utf-8")).hexdigest()
    options = dict(source_artifact_id=pin.source_artifact_id, source_domain="worldbuilding",
        world_id=turn.world_id, campaign_id=None, session_id=None, markdown=markdown,
        content_sha256=digest, lineage={})
    options.update(source_values or {})
    stored = sources.persist_source_markdown(**options)
    event = authorization(turn, donor, pin)
    proof = json.loads(event.origin_proof_json)
    proof["revision"]["content_sha256"] = digest
    if reference is not None:
        proof["resolution"]["artifact"]["workspace_document_ref"] = reference
    event = t.NativeSourceNavigationAuthorizedV1.model_validate(event.model_dump(mode="json") | {
        "origin_proof_json": json.dumps(proof), "origin_proof_sha256": t._canonical_sha256(proof)})
    turn, _ = persist(service, turn, event)
    return service, turn, event, stored


def read(case, *, event_id=None, **overrides):
    service, turn, nav, _ = case
    return service.materialize_native_source_catalog(turn.world_id, turn.conversation_id, turn.turn_id,
        **(dict(expected_revision=turn.revision, expected_attempt=turn.attempt,
                navigation_id=nav.navigation_id, event_id=event_id or uuid4()) | overrides))


def test_authorize_materialize_reload_exact_replay_without_another_read(nav_case, monkeypatch):
    case = grant(nav_case)
    service, turn, nav, stored = case
    event_id = uuid4()
    updated, fresh, material = read(case, event_id=event_id)
    assert fresh and material.markdown == TEXT
    event = updated.graph_context_execution.events[-1]
    assert isinstance(event, t.NativeSourceCatalogObservedV1)
    assert event.outcome == "complete" and event.failure_code is None
    assert event.app_source_revision_id == stored.source_revision_id
    assert material.app_source_revision_id == stored.source_revision_id
    assert material.catalog_event_id == event.event_id and material.navigation_id == nav.navigation_id
    assert material.content_sha256 == event.content_sha256 and TEXT not in repr(material)
    assert event.native_source_revision_id == "native-revision:proof"
    assert event.body_read_chars == len(TEXT) and event.body_read_bytes == len(TEXT.encode("utf-8"))
    assert [e.label for e in event.sections] == ["Synthetic road", "Synthetic road › Appendix A"]
    assert "markdown" not in event.model_dump() and "text" not in event.model_dump()
    reopened = service.list_turns(turn.world_id, turn.conversation_id)[-1]
    assert reopened.graph_context_execution.events[-1] == event
    monkeypatch.setattr(catalog.sources, "get_source_artifact", lambda *a, **kw: pytest.fail("replay performed metadata IO"))
    monkeypatch.setattr(catalog.sources, "get_source_markdown", lambda *a, **kw: pytest.fail("replay performed body IO"))
    retried, fresh, material = read((service, updated, nav, stored), event_id=event_id)
    assert not fresh and material is None and retried.revision == updated.revision
    with pytest.raises(ApplicationStateValidationError):
        read((service, updated, nav, stored))
    with pytest.raises(ApplicationStateValidationError):
        read((service, updated, nav, stored), event_id=event_id, navigation_id=uuid4())


def test_unadmitted_or_stale_read_never_loads_source(nav_case, monkeypatch):
    case = grant(nav_case)
    monkeypatch.setattr(catalog.sources, "get_source_artifact", lambda *a, **kw: pytest.fail("unadmitted read reached source"))
    with pytest.raises(ApplicationStateValidationError):
        read(case, navigation_id=uuid4())
    with pytest.raises(ApplicationStateConflictError):
        read(case, expected_revision=case[1].revision-1)
    with pytest.raises(ApplicationStateConflictError):
        read(case, expected_attempt=case[1].attempt+1)


def test_foreign_source_metadata_denies_before_body_query(nav_case, monkeypatch):
    case = grant(nav_case, source_values={"world_id": "another-managed-world"})
    monkeypatch.setattr(catalog.sources, "get_source_markdown", lambda *a, **kw: pytest.fail("foreign metadata loaded a body"))
    updated, fresh, material = read(case)
    event = updated.graph_context_execution.events[-1]
    assert fresh and material is None and event.outcome == "unavailable"
    assert event.failure_code == "source_scope_mismatch" and event.body_read_bytes == 0
    assert event.sections == [] and event.app_source_revision_id is None


@pytest.mark.parametrize("change,code", [("missing","source_unavailable"), ("corrupt","source_hash_mismatch"),
    ("encoding","source_encoding_mismatch"), ("lineage","source_lineage_mismatch")])
def test_failed_catalog_is_durable_and_does_not_expose_sections(nav_case, monkeypatch, change, code):
    case = grant(nav_case, reference={"document_id":"exact-document", "revision":2} if change == "lineage" else None)
    original = catalog.sources.get_source_markdown
    def get(*a, **kw):
        source = original(*a, **kw)
        if change == "missing": return None
        if change == "corrupt": return source.model_copy(update={"markdown":"changed bytes"})
        if change == "encoding": return source.model_copy(update={"encoding":"latin-1"})
        return source
    monkeypatch.setattr(catalog.sources, "get_source_markdown", get)
    updated, fresh, material = read(case)
    event = updated.graph_context_execution.events[-1]
    assert fresh and material is None and event.outcome == "unavailable" and event.failure_code == code
    assert not event.sections and event.app_source_revision_id is None
    assert event.body_read_bytes == (0 if change == "missing" else len(("changed bytes" if change == "corrupt" else TEXT).encode()))
    assert case[0].list_turns(updated.world_id, updated.conversation_id)[-1].graph_context_execution.events[-1] == event


def test_exact_old_source_survives_another_stored_body(nav_case):
    case = grant(nav_case)
    stored = case[3]
    newer = sources.persist_source_markdown(source_artifact_id=stored.source_artifact_id,
        source_domain=stored.source_domain, world_id=stored.world_id, campaign_id=None, session_id=None,
        markdown="# Replacement\nDifferent source bytes.\n", lineage={})
    assert newer.source_revision_id != stored.source_revision_id
    updated, _, material = read(case)
    assert material.markdown == TEXT
    assert updated.graph_context_execution.events[-1].app_source_revision_id == stored.source_revision_id


def test_workspace_lineage_is_exact_when_native_reference_exists(nav_case):
    case = grant(nav_case, reference={"document_id":"exact-document", "revision":2}, source_values={
        "lineage":{"workspace_document_id":"exact-document", "workspace_document_revision":2}})
    updated, _, material = read(case)
    assert material.markdown == TEXT and updated.graph_context_execution.events[-1].outcome == "complete"


def test_raw_catalog_receipt_cannot_bypass_transaction_owner(nav_case):
    case = grant(nav_case)
    updated, _, _ = read(case)
    event = updated.graph_context_execution.events[-1].model_copy(update={"event_id":uuid4(), "sequence":len(updated.graph_context_execution.events)})
    with pytest.raises(ApplicationStateValidationError, match="transaction owner"):
        case[0]._append_graph_execution_event(updated.world_id, updated.conversation_id, updated.turn_id,
            expected_revision=updated.revision, expected_attempt=updated.attempt, event=event, duplicate_key="event_id")


def test_populated_downgrade_refuses_catalog_loss(nav_case, application_state_dsn):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    read(grant(nav_case))
    engine = create_engine(application_state_dsn.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError, match="retained native source catalog"):
                    import_module("application_state.migrations.versions.20261022_0054_native_source_catalog").downgrade()
    finally: engine.dispose()


@pytest.mark.parametrize("text", [TEXT, "Title\n=====\nIntro\n\nAppendix\n--------\nTree 🦉.\n", "No heading 🦉\r\nMore text", "intro\n# A\n```md\n## not heading\n```\n## B\nend\n", "# A\n~~~\n## hidden\n~~~~\n# B\nend"])
def test_catalog_ranges_reconstruct_exact_unicode_and_line_endings(text):
    sections = catalog.section_catalog(text, source_artifact_id="artifact", native_source_revision_id="revision",
        content_sha256=sha256(text.encode()).hexdigest())
    lines = text.splitlines(keepends=True)
    assert ''.join(text[s.char_start:s.char_end] for s in sections) == text
    assert all(text[s.char_start:s.char_end] == ''.join(lines[s.line_start-1:s.line_end]) for s in sections)
    assert not any("not heading" in s.label or "hidden" in s.label for s in sections)
    assert catalog.section_catalog(text, source_artifact_id="artifact", native_source_revision_id="revision",
        content_sha256=sha256(text.encode()).hexdigest()) == sections


def test_final_rules_writer_fence_precedes_any_source_io(nav_case, monkeypatch):
    from types import SimpleNamespace
    from application_state.agent_conversation import rules_authority_store
    from application_state.agent_conversation.rules_authority_events import RulesPlanPacketProviderAuthorizedV1
    case = grant(nav_case)
    if not isinstance(case[1].graph_context_execution, t.PlanWorldGraphExecutionV3):
        pytest.skip("Plan Rules final-writer fence")
    monkeypatch.setattr(rules_authority_store, "load_turn_rules_locked", lambda *a: SimpleNamespace(
        execution=SimpleNamespace(events=[RulesPlanPacketProviderAuthorizedV1.model_construct()])))
    monkeypatch.setattr(catalog.sources, "get_source_artifact", lambda *a, **kw: pytest.fail("writer fence allowed source IO"))
    with pytest.raises(ApplicationStateValidationError, match="final writer"):
        read(case)


def test_concurrent_materialization_performs_one_body_read(nav_case, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Lock
    case = grant(nav_case)
    original = catalog.sources.get_source_markdown
    calls, lock, barrier = [], Lock(), Barrier(2)
    def get(*a, **kw):
        with lock: calls.append(kw)
        return original(*a, **kw)
    monkeypatch.setattr(catalog.sources, "get_source_markdown", get)
    event_id = uuid4()
    def run():
        barrier.wait(timeout=5)
        try: return read(case, event_id=event_id)
        except ApplicationStateConflictError: return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sum(result is not None for result in results) == 1
    assert len(calls) == 1
    accepted = next(result for result in results if result is not None)
    assert accepted[1] and accepted[2].markdown == TEXT


def test_expired_claim_refuses_before_source_io(nav_case, monkeypatch):
    from datetime import timedelta
    from application_state.agent_conversation import repository as turns
    case = grant(nav_case)
    monkeypatch.setattr(turns, "database_clock", lambda conn: case[1].claim_expires_at+timedelta(seconds=1))
    monkeypatch.setattr(catalog.sources, "get_source_artifact", lambda *a, **kw: pytest.fail("expired claim reached source"))
    with pytest.raises(ApplicationStateConflictError, match="expired"):
        read(case)


def test_catalog_storage_overflow_is_explicit_and_not_partial(nav_case):
    case = grant(nav_case, markdown="# "+("h"*1_100_000)+"\n")
    with pytest.raises(ApplicationStateValidationError, match="storage size limit"):
        read(case)
    reopened = case[0].list_turns(case[1].world_id, case[1].conversation_id)[-1]
    assert reopened.revision == case[1].revision
    assert not any(isinstance(e,t.NativeSourceCatalogObservedV1) for e in reopened.graph_context_execution.events)


def test_migration_preserves_existing_navigation_and_source(nav_case, application_state_dsn):
    import psycopg
    from alembic import command
    from application_state.cli import alembic_config
    case = grant(nav_case)
    def snapshot():
        with psycopg.connect(application_state_dsn) as conn:
            return conn.execute("SELECT graph_context_execution FROM agent.turn WHERE turn_id=%s", (case[1].turn_id,)).fetchone()[0]
    before = snapshot()
    command.downgrade(alembic_config(), "20261022_0053")
    assert snapshot() == before
    command.upgrade(alembic_config(), "head")
    assert snapshot() == before
    assert sources.get_source_markdown(source_artifact_id=case[3].source_artifact_id,
        content_sha256=case[3].content_sha256, source_revision_id=case[3].source_revision_id) == case[3]
