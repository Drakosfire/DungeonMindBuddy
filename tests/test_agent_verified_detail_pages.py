"""Larger detail pages preserve real SDK budgets and exact parent admission."""
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.live_control_server.services.graph_tool_transport import GraphToolPageCache, PAGE_BYTES
from apps.live_control_server.services.graph_tool_presentation import GraphToolPresentation
from apps.live_control_server.services.hermes_graph_dispatch_adapter import verify_graph_page_capacity, install_graph_serial_dispatch
from apps.live_control_server.services.hermes_graph_agent import hermes_import_namespace, _GraphOperationReservation
from apps.live_control_server.services.hermes_graph_agent_contract import _serialize_request_budget
from tests.test_graph_tool_transport import ARGS, SCOPE, _raw
from tests.test_graph_tool_presentation import detail_pages
from tests.test_hermes_graph_dispatch_adapter import _agent, _call


def test_large_details_keep_overview_compact_and_exact_parent_records():
    raw = _raw()
    counts = []
    for limit in (8_000, 32_000):
        parent = GraphToolPresentation(SCOPE, cache=GraphToolPageCache(page_bytes=limit))
        first = parent.present('expand_graph_retrieval', ARGS, raw, uuid4())
        assert len(first.encode()) <= PAGE_BYTES
        assert not parent.inclusion('expand_graph_retrieval', [first])[0].assertion_ids
        pages = detail_pages(parent, first)
        assert all(len(page.encode()) <= limit for page in pages)
        exposure = parent.inclusion('expand_graph_retrieval', pages)[0]
        assert exposure.assertion_ids == frozenset(f'a:{i}' for i in range(80))
        assert json.loads(raw)['reviewedSourceObservations'][0]['epistemicKind'] == 'belief'
        counts.append(len(pages))
    assert counts[1] < counts[0]


@pytest.mark.parametrize('limit', [None, 0, True, 7999, 32001, '32000'])
def test_page_limit_rejects_invalid_values(limit):
    with pytest.raises(ValueError):
        GraphToolPageCache(page_bytes=limit)


def test_request_budget_roundtrip_and_rejects_forged_capacity():
    budget = dict(schema='dmb_agent_request_budget_uncapped_v1', provider='openai-api', model='gpt-6-luna',
                  apiMode='codex_responses', estimator='utf8_json_bytes_plus_64_per_node_v1',
                  contextLimitTokens=1_050_000, outputReserveTokens=2048,
                  maxProviderAttempts=None, maxToolCapableAttempts=None, maxGraphOperations=None)
    assert 'graphToolPageBytes' not in _serialize_request_budget(budget)
    assert _serialize_request_budget({**budget, 'graphToolPageBytes':32000})['graphToolPageBytes']==32000
    for value in [True, 32768, 0, '32000']:
        with pytest.raises(ValueError):
            _serialize_request_budget({**budget, 'graphToolPageBytes':value})


@pytest.mark.parametrize('context, accepted', [(1_050_000, True), (16_000, False), (None, False)])
def test_constructed_sdk_agent_capacity_is_verified(tmp_path, monkeypatch, context, accepted):
    agent = _agent(tmp_path, monkeypatch)
    agent.context_compressor.context_length = context
    with hermes_import_namespace():
        if accepted:
            verify_graph_page_capacity(agent,32000)
        else:
            with pytest.raises(ValueError):
                verify_graph_page_capacity(agent,32000)
        verify_graph_page_capacity(agent,8000)


def test_worker_honors_frozen_detail_limit_and_keeps_overview_bound():
    parent = GraphToolPresentation(SCOPE, cache=GraphToolPageCache(page_bytes=32000))
    first=parent.present('expand_graph_retrieval',ARGS,_raw(),uuid4())
    pages=detail_pages(parent,first)
    page=next(p for p in pages if len(p.encode())>8000)
    for limit, accepted in [(8000,False),(32000,True)]:
        reservation=_GraphOperationReservation(None,lambda *_:None,scope=SCOPE,page_bytes=limit)
        assert bool(reservation._presentation_schema(json.loads(page),'expand_graph_retrieval',ARGS,page)) is accepted
    oversized=json.loads(first)
    oversized['padding']='x'*9000
    encoded=json.dumps(oversized)
    assert reservation._presentation_schema(oversized,'expand_graph_retrieval',ARGS,encoded) is None


@pytest.mark.parametrize('kind', ['chat','responses'])
def test_large_pages_survive_real_serial_dispatch_budgets_and_transport(tmp_path, monkeypatch, kind):
    agent=_agent(tmp_path,monkeypatch)
    agent.context_compressor.context_length=1_050_000
    raw=json.dumps({'schema':'dmb_world_graph_source_anchor_read_v1','content':'Ω'*17000,'anchorId':'opaque:one'},ensure_ascii=False)
    content=GraphToolPageCache(page_bytes=32000).present('read_graph_source',{'anchorIds':['opaque:one']},SCOPE,raw)
    assert 8000<len(content.encode())<=32000
    with hermes_import_namespace():
        import run_agent
        verify_graph_page_capacity(agent,32000)
        monkeypatch.setattr(run_agent,'handle_function_call',lambda *_a,**_k:content)
        install_graph_serial_dispatch(agent)
        batch=SimpleNamespace(tool_calls=[_call(i) for i in range(12)],content=None)
        assistant={'role':'assistant','tool_calls':[{'id':c.id,'type':'function','function':{'name':c.function.name,'arguments':c.function.arguments}} for c in batch.tool_calls]}
        messages=[assistant]
        agent._execute_tool_calls(batch,messages,'task:large',0)
        assert [m['content'] for m in messages[1:]]==[content]*12
        assert sum(len(m['content']) for m in messages[1:])>200000
        if kind=='chat':
            from agent.transports.chat_completions import ChatCompletionsTransport
            transport=ChatCompletionsTransport()
        else:
            from agent.transports.codex import ResponsesApiTransport
            transport=ResponsesApiTransport()
        request=transport.build_kwargs(model='gpt-6-luna',messages=messages,request_overrides={'parallel_tool_calls':False})
        serialized=json.dumps(request,ensure_ascii=False)
        # Both provider serializers preserve every exact tool JSON content.
        assert serialized.count(json.dumps(content,ensure_ascii=False))==12
        assert request['parallel_tool_calls'] is False


def test_real_luna_constructor_supplies_sufficient_capacity(tmp_path, monkeypatch):
    agent = _agent(tmp_path, monkeypatch)
    with hermes_import_namespace():
        verify_graph_page_capacity(agent,32000)


def test_registry_tool_threshold_cannot_be_bypassed(tmp_path, monkeypatch):
    agent = _agent(tmp_path, monkeypatch)
    agent.context_compressor.context_length=1_050_000
    with hermes_import_namespace():
        from tools.registry import registry
        monkeypatch.setattr(registry,'get_max_result_size',lambda *_a,**_k:16000)
        with pytest.raises(ValueError,match='capacity_insufficient'):
            verify_graph_page_capacity(agent,32000)
