"""APP authorize→exact cached excerpt→reload, with no new source body IO."""
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation import native_source_catalog as catalog_owner
from application_state.agent_conversation.native_source_sections import validate_section_events
from application_state.errors import ApplicationStateValidationError, ApplicationStateConflictError
from tests.application_state.test_native_source_navigation_postgres import nav_case  # noqa: F401
from tests.application_state.test_native_source_catalog_postgres import grant, read as read_catalog, TEXT


@pytest.fixture
def selected(nav_case):
    case = grant(nav_case)
    turn, fresh, material = read_catalog(case)
    assert fresh
    return case[0], turn, turn.graph_context_execution.events[-1], material


def authorize(case, *, index=1, event_id=None, read_id=None, **overrides):
    service, turn, catalog, _ = case
    return service.authorize_native_source_section(turn.world_id, turn.conversation_id, turn.turn_id,
        **(dict(expected_revision=turn.revision, expected_attempt=turn.attempt,
            event_id=event_id or uuid4(), read_id=read_id or uuid4(),
            catalog_event_id=catalog.event_id, section_id=catalog.sections[index].section_id) | overrides))


def extract(case, auth, *, event_id=None, material="original", **overrides):
    service, turn, _, original = case
    return service.materialize_native_source_section(turn.world_id, turn.conversation_id, turn.turn_id,
        **(dict(expected_revision=turn.revision, expected_attempt=turn.attempt, event_id=event_id or uuid4(),
                read_id=auth.read_id, material=original if material == "original" else material) | overrides))


def test_authorize_extract_reload_and_replay_exact_text_without_source_io(selected, monkeypatch):
    service, turn, catalog, material = selected
    monkeypatch.setattr(catalog_owner.sources,"get_source_artifact",lambda *a,**kw:pytest.fail("section performed metadata IO"))
    monkeypatch.setattr(catalog_owner.sources,"get_source_markdown",lambda *a,**kw:pytest.fail("section reread the source"))
    auth_id, read_id, receipt_id = uuid4(), uuid4(), uuid4()
    turn, fresh = authorize(selected, event_id=auth_id, read_id=read_id)
    auth = turn.graph_context_execution.events[-1]
    assert fresh and auth.authorized_chars == len("## Appendix A\r\nTree mechanics.\r\n")
    assert t.source_read_character_usage(turn.graph_context_execution.policy,turn.graph_context_execution.events) == auth.authorized_chars
    retried, fresh = authorize((service,turn,catalog,material),event_id=auth_id,read_id=read_id)
    assert not fresh and retried.revision == turn.revision
    updated, fresh, observed = extract((service,turn,catalog,material),auth,event_id=receipt_id)
    assert fresh and observed.outcome == "complete" and observed.text == "## Appendix A\r\nTree mechanics.\r\n"
    assert observed.excerpt_sha256 == sha256(observed.text.encode()).hexdigest()
    assert observed.content_sha256 == sha256(TEXT.encode()).hexdigest()
    assert observed.app_source_revision_id == material.app_source_revision_id
    assert observed.fresh_body_read_bytes == 0 and observed.returned_chars == auth.authorized_chars
    reopened = service.list_turns(turn.world_id,turn.conversation_id)[-1]
    assert reopened.graph_context_execution.events[-1] == observed
    retried, fresh, replay = extract((service,updated,catalog,material),auth,event_id=receipt_id,material=None)
    assert not fresh and replay == observed and retried.revision == updated.revision
    assert t.source_read_character_usage(updated.graph_context_execution.policy,updated.graph_context_execution.events) == auth.authorized_chars


def test_sibling_sections_are_acquired_once_from_same_body(selected,monkeypatch):
    service,turn,catalog,material=selected
    monkeypatch.setattr(catalog_owner.sources,"get_source_markdown",lambda *a,**kw:pytest.fail("sibling reread the source"))
    results=[]
    for index in range(len(catalog.sections)):
        turn,_=authorize((service,turn,catalog,material),index=index)
        auth=turn.graph_context_execution.events[-1]
        turn,_,observed=extract((service,turn,catalog,material),auth)
        results.append(observed)
    assert ''.join(e.text for e in results)==TEXT
    assert t.source_read_character_usage(turn.graph_context_execution.policy,turn.graph_context_execution.events)==len(TEXT)
    with pytest.raises(ApplicationStateValidationError):authorize((service,turn,catalog,material),index=0)


@pytest.mark.parametrize("change",["missing","hash","identity","uuid","catalog"])
def test_unavailable_cache_settles_reservation_without_evidence(selected,change):
    service,turn,catalog,material=selected
    turn,_=authorize(selected)
    auth=turn.graph_context_execution.events[-1]
    bad={"missing":None,"hash":replace(material,markdown=material.markdown+"forged"),
         "identity":replace(material,native_source_revision_id="foreign"),
         "uuid":replace(material,app_source_revision_id=uuid4()),"catalog":replace(material,catalog_event_id=uuid4())}[change]
    turn, fresh, observed=extract((service,turn,catalog,material),auth,material=bad)
    assert fresh and observed.outcome=="unavailable" and observed.text is None and observed.excerpt_sha256 is None
    assert observed.returned_chars==0 and observed.fresh_body_read_bytes==0
    assert t.source_read_character_usage(turn.graph_context_execution.policy,turn.graph_context_execution.events)==0


def test_unknown_target_and_read_before_authorization_are_refused(selected):
    service,turn,catalog,material=selected
    for bad in ({"catalog_event_id":uuid4()},{"section_id":"f"*64}):
        with pytest.raises(ApplicationStateValidationError):authorize(selected,**bad)
    with pytest.raises(ApplicationStateValidationError):
        extract(selected,SimpleNamespace(read_id=uuid4()))
    assert service.list_turns(turn.world_id,turn.conversation_id)[-1].revision==turn.revision


def test_stale_and_changed_retry_refuse_without_materialization(selected):
    service,turn,catalog,material=selected
    with pytest.raises(ApplicationStateConflictError):authorize(selected,expected_revision=turn.revision-1)
    auth_id,read_id=uuid4(),uuid4()
    turn,_=authorize(selected,event_id=auth_id,read_id=read_id)
    auth=turn.graph_context_execution.events[-1]
    with pytest.raises(ApplicationStateValidationError):
        authorize((service,turn,catalog,material),index=0,event_id=auth_id,read_id=read_id)
    with pytest.raises(ApplicationStateConflictError):
        extract((service,turn,catalog,material),auth,expected_attempt=turn.attempt+1)


def test_pending_reservation_blocks_next_provider(selected):
    service,turn,catalog,material=selected
    turn,_=authorize(selected)
    latest=next(e for e in reversed(turn.graph_context_execution.events) if isinstance(e,t.ProviderAttemptAuthorizedEventV1))
    next_provider=latest.model_copy(update={"event_id":uuid4(),"provider_attempt_id":uuid4(),"sequence":len(turn.graph_context_execution.events)})
    with pytest.raises(ValueError,match="unresolved native section"):
        validate_section_events(SimpleNamespace(policy=turn.graph_context_execution.policy,
            context_receipt_sha256=turn.graph_context_execution.context_receipt_sha256,
            execution_policy_sha256=turn.graph_context_execution.execution_policy_sha256,
            events=turn.graph_context_execution.events+[next_provider]))


@pytest.mark.parametrize("limit",["aggregate","per_read"])
def test_existing_character_budget_is_enforced_on_selected_section(selected,limit):
    service,turn,catalog,material=selected
    turn,_=authorize(selected)
    execution=turn.graph_context_execution
    chars=execution.events[-1].authorized_chars
    wire=execution.model_dump(mode="json",by_alias=True)
    wire["policy"]["max_source_read_chars" if limit=="aggregate" else "max_chars_per_source_read"]=chars-1
    digest=t._canonical_sha256({"schema":execution.schema_,"context_receipt_sha256":execution.context_receipt_sha256,"policy":wire["policy"]})
    wire["execution_policy_sha256"]=digest
    for row in wire["events"]:
        if "execution_policy_sha256" in row:row["execution_policy_sha256"]=digest
    with pytest.raises(ValueError,match="budget|character"):
        type(execution).model_validate(wire)


def test_raw_receipt_and_range_tamper_cannot_bypass_owner(selected):
    service,turn,catalog,material=selected
    turn,_=authorize(selected)
    auth=turn.graph_context_execution.events[-1]
    turn,_,observed=extract((service,turn,catalog,material),auth)
    forged=observed.model_copy(update={"event_id":uuid4(),"sequence":len(turn.graph_context_execution.events)})
    with pytest.raises(ApplicationStateValidationError,match="transaction owner"):
        service._append_graph_execution_event(turn.world_id,turn.conversation_id,turn.turn_id,
            expected_revision=turn.revision,expected_attempt=turn.attempt,event=forged,duplicate_key="event_id")
    wire=turn.graph_context_execution.model_dump(mode="json",by_alias=True)
    wire["events"][-1]["section"]["line_start"]+=1
    with pytest.raises(ValueError):type(turn.graph_context_execution).model_validate(wire)


def test_concurrent_receipt_commits_once(selected):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    service,turn,catalog,material=selected
    turn,_=authorize(selected)
    auth=turn.graph_context_execution.events[-1]
    receipt_id,barrier=uuid4(),Barrier(2)
    def run():
        barrier.wait(timeout=5)
        try:return extract((service,turn,catalog,material),auth,event_id=receipt_id)
        except ApplicationStateConflictError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:run(),range(2)))
    assert sum(r is not None for r in results)==1
    reopened=service.list_turns(turn.world_id,turn.conversation_id)[-1]
    assert sum(isinstance(e,t.NativeSourceSectionObservedV1) for e in reopened.graph_context_execution.events)==1


def test_populated_downgrade_refuses_section_loss(selected,application_state_dsn):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    authorize(selected)
    engine=create_engine(application_state_dsn.replace("postgresql://","postgresql+psycopg://"))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError,match="retained native source section"):
                    import_module("application_state.migrations.versions.20261022_0055_native_source_sections").downgrade()
    finally:engine.dispose()
