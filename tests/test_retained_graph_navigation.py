"""Real APP metadata projection; prior model/source text is never navigation input."""
from copy import deepcopy
import psycopg
from psycopg.types.json import Jsonb
import pytest
from application_state.config import load_runtime_dsn
from application_state.agent_conversation import repository as repo
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_source_passage_reuse import complete_origin


def navigation(adapter, origin, page=None, authority=None):
    service = adapter.service
    if page is None:
        page = service.list_turns(origin.world_id, origin.conversation_id)
    return service.retained_graph_navigation(world_id=origin.world_id,
        conversation_id=origin.conversation_id,
        authority=authority or origin.graph_context_receipt.graph_authority, previous_turns=page)


def test_navigation_projects_one_existing_history_page_and_deduplicates(plan_adapter, monkeypatch):
    origin, trace = complete_origin(plan_adapter)
    page = plan_adapter.service.list_turns(origin.world_id, origin.conversation_id)
    calls=[]
    original=repo.list_retained_graph_tools
    def counted(conn, world_id, conversation_id, turn_ids, authority):
        calls.append(tuple(turn_ids))
        rows=original(conn, world_id, conversation_id, turn_ids, authority)
        assert all(raw['kind']=='graph_tool' and 'text' not in raw for _,_,raw in rows)
        return rows
    monkeypatch.setattr(repo,'list_retained_graph_tools',counted)
    subjects=navigation(plan_adapter,origin,page)
    assert [subject.node_id for subject in subjects]==['bridge','pond']
    assert [subject.label for subject in subjects]==['Footbridge','Park pond']
    assert len(calls)==1 and calls[0]==(origin.turn_id,)
    assert not any(hasattr(subject,'text') or hasattr(subject,'evidence_ref_ids') for subject in subjects)


@pytest.mark.parametrize('damage',['incomplete','open','world','conversation','attempt','event','request_hash','result_hash','revision'])
def test_invalid_or_unjoined_navigation_is_not_offered(plan_adapter,damage):
    origin,trace=complete_origin(plan_adapter)
    raw=deepcopy(trace.model_dump(mode='json',by_alias=True))
    if damage=='incomplete':raw['capture_status']='incomplete'
    if damage=='open':raw['closed_at']=None
    if damage=='world':raw['world_id']='another-world'
    if damage=='conversation':raw['conversation_id']='00000000-0000-4000-8000-000000000001'
    if damage=='attempt':raw['attempt']+=1
    for row in raw['observations']:
        if row['kind']!='graph_tool':continue
        if damage=='event':row['execution_event_id']='00000000-0000-4000-8000-000000000001'
        if damage=='request_hash':row['request_arguments_sha256']='0'*64
        if damage=='result_hash':row['result_packet_sha256']='0'*64
        if damage=='revision':row['revision_pin']=row['result']['graph_revision']='another-revision'
    if damage=='attempt':
        with pytest.raises(psycopg.errors.CheckViolation), psycopg.connect(load_runtime_dsn()) as conn:
            conn.execute('UPDATE agent.turn_context_trace SET payload=%s WHERE turn_id=%s AND attempt=%s',
                         (Jsonb(raw),origin.turn_id,origin.attempt))
        return
    with psycopg.connect(load_runtime_dsn()) as conn:
        conn.execute('UPDATE agent.turn_context_trace SET payload=%s WHERE turn_id=%s AND attempt=%s',
                     (Jsonb(raw),origin.turn_id,origin.attempt))
    assert navigation(plan_adapter,origin)==()


def test_foreign_history_and_stale_authority_do_not_supply_navigation(plan_adapter):
    origin,_=complete_origin(plan_adapter)
    authority=origin.graph_context_receipt.graph_authority.model_copy(update={'graph_revision':'new-revision'})
    assert navigation(plan_adapter,origin,authority=authority)==()
    foreign=origin.model_copy(update={'world_id':'another-world'})
    assert navigation(plan_adapter,origin,page=[foreign])==()
