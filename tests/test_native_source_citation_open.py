"""Exact citation reopen over APP bytes; fresh access precedes body loading."""
from hashlib import sha256
from types import SimpleNamespace

import pytest

from tests.application_state.test_native_source_citations_postgres import native_writer,finish  # noqa: F401
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from application_state.source import service as sources
from application_state.agent_conversation import types as t
from apps.live_control_server.services import agent_native_source_sections as owner
from apps.live_control_server.services.agent_source_passages import SourcePassageOpenError


@pytest.fixture
def opened_case(native_writer,monkeypatch):
    completed = finish(native_writer)
    citation = completed.completion.native_source_citations[0]
    authority = completed.graph_context_receipt.graph_authority
    calls = []
    monkeypatch.setattr(owner,'resolve_managed_world_binding',lambda world:SimpleNamespace(
        managed_world_id=world,native_world_id=authority.native_world_id,binding_version=authority.binding_version))
    monkeypatch.setattr(owner,'direct_services_from_config',lambda world:('native-services',world))
    def verify(services,*,projection,donor,pin):
        calls.append('access')
        assert services == ('native-services',authority.native_world_id)
        assert projection.world_id == authority.native_world_id and projection.revision_pin == authority.graph_revision
        assert pin in donor.returned_source_pins and pin.source_artifact_id == citation.source_artifact_id
        return SimpleNamespace(source_artifact_id=citation.source_artifact_id,
            native_source_revision_id=citation.native_source_revision_id,content_sha256=citation.content_sha256)
    monkeypatch.setattr(owner,'verify_native_source_origin',verify)
    original = owner.get_source_markdown
    def read(**selectors):
        calls.append('body')
        assert selectors == dict(source_artifact_id=citation.source_artifact_id,
            content_sha256=citation.content_sha256,source_revision_id=citation.app_source_revision_id)
        return original(**selectors)
    monkeypatch.setattr(owner,'get_source_markdown',read)
    return completed,citation,calls


def read(case,**changes):
    completed,_,_ = case
    return owner.open_native_source_section(**(dict(world_id=completed.world_id,
        turn_id=completed.turn_id,citation_index=0)|changes))


def test_reopen_uses_old_immutable_bytes_after_new_source_revision(opened_case):
    completed,citation,calls = opened_case
    newer = '# Updated source\nNo original appendix remains.\n'
    sources.persist_source_markdown(source_artifact_id=citation.source_artifact_id,
        source_domain='worldbuilding',world_id=completed.world_id,campaign_id=None,session_id=None,
        markdown=newer,content_sha256=sha256(newer.encode()).hexdigest(),lineage={})
    result = read(opened_case)
    assert result.citation == citation and result.content == '## Appendix A\r\nTree mechanics.\r\n'
    assert calls == ['access','body']


@pytest.mark.parametrize('change',['binding','native_denial','native_hash'])
def test_current_access_failure_does_not_read_body(opened_case,monkeypatch,change):
    _,_,calls = opened_case
    if change == 'binding':
        monkeypatch.setattr(owner,'resolve_managed_world_binding',lambda world:SimpleNamespace(
            managed_world_id=world,native_world_id='foreign',binding_version=999))
    elif change == 'native_denial':
        def deny(*a,**kw):raise ValueError('Source retracted or visibility denied')
        monkeypatch.setattr(owner,'verify_native_source_origin',deny)
    else:
        monkeypatch.setattr(owner,'verify_native_source_origin',lambda *a,**kw:SimpleNamespace(
            source_artifact_id='foreign',native_source_revision_id='changed',content_sha256='f'*64))
    with pytest.raises(SourcePassageOpenError,match='access_unavailable'):read(opened_case)
    assert 'body' not in calls


@pytest.mark.parametrize('change',['missing','corrupt','world','revision','lineage'])
def test_missing_or_mismatched_bytes_never_fall_back(opened_case,monkeypatch,change):
    _,_,calls = opened_case
    original = owner.get_source_markdown
    def damaged(**kw):
        record = original(**kw)
        if change == 'missing':return None
        from uuid import uuid4
        values = {'corrupt':{'markdown':record.markdown+'changed'},'world':{'world_id':'foreign'},
            'revision':{'source_revision_id':uuid4()},'lineage':{'encoding':'latin-1'}}[change]
        return record.model_copy(update=values)
    monkeypatch.setattr(owner,'get_source_markdown',damaged)
    with pytest.raises(SourcePassageOpenError,match='bytes_unavailable'):read(opened_case)
    assert calls[0] == 'access'


def test_selector_and_completed_turn_ownership_are_closed(opened_case):
    for index in (True,-1,16384):
        with pytest.raises(SourcePassageOpenError,match='selector_invalid'):read(opened_case,citation_index=index)
    with pytest.raises(SourcePassageOpenError,match='not_found'):read(opened_case,citation_index=1)


def test_route_enforces_auth_before_source_access(monkeypatch):
    from fastapi import HTTPException
    from starlette.requests import Request
    from uuid import uuid4
    from apps.live_control_server.routes import agent
    def deny(_):raise HTTPException(status_code=403,detail='Denied')
    monkeypatch.setattr(agent,'enforce_native_graph_gm',deny)
    monkeypatch.setattr(owner,'open_native_source_section',lambda **kw:pytest.fail('Unauthenticated body access'))
    with pytest.raises(HTTPException) as error:
        agent.get_world_turn_native_source_section('world',uuid4(),0,
            Request({'type':'http','headers':[],'query_string':b''}))
    assert error.value.status_code == 403


def test_route_rejects_caller_source_selectors(monkeypatch):
    from fastapi import HTTPException
    from starlette.requests import Request
    from uuid import uuid4
    from apps.live_control_server.routes import agent
    monkeypatch.setattr(agent,'enforce_native_graph_gm',lambda _:None)
    monkeypatch.setattr(agent,'_verified_world_id',lambda world:world)
    monkeypatch.setattr(owner,'open_native_source_section',lambda **kw:pytest.fail('Caller source lookup'))
    with pytest.raises(HTTPException) as error:
        agent.get_world_turn_native_source_section('world',uuid4(),0,
            Request({'type':'http','headers':[],'query_string':b'source_revision_id=latest'}))
    assert error.value.status_code == 422


@pytest.mark.parametrize('changed_lineage',[False,True])
def test_registered_build_citation_reopens_exact_projected_source(request,monkeypatch,plan_adapter,changed_lineage):
    from tests.application_state import test_native_source_catalog_postgres as catalogs
    original=catalogs.grant
    def registered(case,**kwargs):
        kwargs.update(source_values={'campaign_id':case[1].world_id,
            'lineage':{'workspace_document_id':'build','workspace_document_revision':2}},
            reference={'document_id':'build','revision':2})
        return original(case,**kwargs)
    monkeypatch.setattr(catalogs,'grant',registered)
    case=request.getfixturevalue('opened_case')
    if changed_lineage:
        original_body=owner.get_source_markdown
        def corrupt(**kw):
            record=original_body(**kw)
            return record.model_copy(update={'lineage':{'workspace_document_id':'foreign','workspace_document_revision':2}})
        monkeypatch.setattr(owner,'get_source_markdown',corrupt)
        with pytest.raises(SourcePassageOpenError,match='bytes_unavailable'):read(case)
    else:
        result=read(case)
        assert result.content=='## Appendix A\r\nTree mechanics.\r\n'
        assert result.citation==case[1] and case[2]==['access','body']
