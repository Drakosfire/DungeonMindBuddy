"""Progress is real observation of one command, never a retry/publication owner."""
import asyncio
import json
import threading

from fastapi import HTTPException
import pytest

from apps.live_control_server.services import build_construction_stream as stream

TABLE = '| Name | Work |\n| --- | --- |\n| Nia | Lantern \\| repair |\n'


@pytest.mark.parametrize('size', [1, 2, 3, 7, 19, 4096])
def test_decoder_partitions_json_escapes_and_completed_lines(size):
    markdown = TABLE + '| 雪😀 | "Dusk" \\ dawn |'
    raw = json.dumps({'summary':'decoy replacement_markdown', 'nested':{'replacement_markdown':'wrong'},
                      'replacement_markdown':markdown, 'assumptions':['not a table']}, ensure_ascii=True)
    decoder = stream.MarkdownStringProgress()
    observed = []
    for start in range(0, len(raw), size):
        if decoder.feed(raw[start:start+size]):
            observed.append(decoder.markdown)
    assert observed[-1] == markdown
    assert not decoder.invalid
    assert all(markdown.startswith(value) for value in observed)
    assert all(value.endswith('\n') for value in observed[:-1])
    assert len(observed) > 1 if size == 1 else True


def test_decoder_exposes_rows_inside_open_json_string_and_holds_partial_escape():
    decoder = stream.MarkdownStringProgress()
    assert decoder.feed('{"replacement_markdown":"| N |\\n| --- |\\n| A |\\n| B \\u')
    assert decoder.markdown.endswith('| A |\n')
    assert not decoder.feed('D83D')
    assert not decoder.feed('\\uDE')
    assert not decoder.feed('00 |')
    assert decoder.feed('\\n')
    assert decoder.markdown.endswith('| B 😀 |\n')
    assert decoder.in_string


@pytest.mark.parametrize('tail', ['"replacement_markdown":"again"}', '"x":"\\q"}', '"x":"\\uZZZZ"}'])
def test_decoder_flags_invalid_output_without_inventing_rows(tail):
    decoder = stream.MarkdownStringProgress()
    decoder.feed('{"replacement_markdown":"| N |\\n| --- |\\n| A |\\n",')
    saved = decoder.markdown
    decoder.feed(tail)
    assert decoder.invalid and decoder.markdown == saved


def test_one_command_progress_precedes_terminal_and_mailbox_coalesces():
    async def run():
        release = threading.Event()
        calls = []
        def work():
            calls.append(1)
            stream.observe({'sequence':1, 'markdown':'first'})
            release.wait(2)
            for sequence in range(2, 100):
                stream.observe({'sequence':sequence, 'markdown':'next'})
            return {'answer':'saved'}
        response=stream.turn_stream(work, 'turn')
        iterator=response.body_iterator
        first=json.loads((await anext(iterator)).removeprefix('data: '))
        assert first['kind']=='construction' and first['progress']['sequence']==1
        release.set()
        values=[json.loads(frame.removeprefix('data: ')) async for frame in iterator]
        assert values[-1]['kind']=='result' and values[-1]['response']=={'answer':'saved'}
        assert len(calls)==1
        sequences=[v['progress']['sequence'] for v in values if v['kind']=='construction']
        assert sequences[-1]==99 and sequences==sorted(set(sequences))
        for task in tuple(stream._running):
            await task
        await asyncio.sleep(0)
        assert not stream._running
    asyncio.run(run())


def test_mailbox_bounds_callbacks_before_event_loop_dispatch(monkeypatch):
    async def run():
        loop = asyncio.get_running_loop()
        original = loop.call_soon_threadsafe
        held = []
        emitted = threading.Event()
        def schedule(callback, *args, **kwargs):
            if isinstance(getattr(callback, '__self__', None), asyncio.Event):
                held.append((callback, args, kwargs))
                return None
            return original(callback, *args, **kwargs)
        monkeypatch.setattr(loop, 'call_soon_threadsafe', schedule)
        def work():
            for sequence in range(1, 1001):
                stream.observe({'sequence': sequence, 'markdown': 'x' * sequence})
            emitted.set()
            return {'answer': 'saved'}
        iterator = stream.turn_stream(work, 'turn').body_iterator
        first = asyncio.create_task(anext(iterator))
        assert await asyncio.to_thread(emitted.wait, 2)
        for task in tuple(stream._running):
            await task
        assert len(held) == 1
        callback, args, kwargs = held.pop()
        original(callback, *args, **kwargs)
        frame = json.loads((await first).removeprefix('data: '))
        assert frame['progress'] == {'sequence': 1000, 'markdown': 'x' * 1000}
        rest = [json.loads(value.removeprefix('data: ')) async for value in iterator]
        assert rest == [{'schema': 'dmb_build_turn_stream_v1', 'client_turn_id': 'turn',
                         'kind': 'result', 'response': {'answer': 'saved'}}]
        assert not held
    asyncio.run(run())


def test_disconnect_retires_only_delivery_and_the_command_finishes():
    async def run():
        release=threading.Event();finished=threading.Event();calls=[]
        def work():
            calls.append(1);stream.observe({'sequence':1})
            release.wait(2)
            stream.observe({'sequence':2});finished.set()
            return {'answer':'durably saved'}
        iterator=stream.turn_stream(work,'turn').body_iterator
        await anext(iterator)
        await iterator.aclose()
        assert not finished.is_set()
        release.set()
        assert await asyncio.to_thread(finished.wait,2)
        for task in tuple(stream._running):
            await task
        await asyncio.sleep(0)
        assert calls==[1] and not stream._running
    asyncio.run(run())


@pytest.mark.parametrize('error',[HTTPException(409,detail={'code':'stale'}), ValueError('private detail')])
def test_transport_error_is_one_safe_terminal_not_an_automatic_retry(error):
    async def run():
        calls=[]
        def work():
            calls.append(1);raise error
        values=[json.loads(frame.removeprefix('data: ')) async for frame in stream.turn_stream(work,'turn').body_iterator]
        assert len(values)==1 and values[0]['kind']=='error' and calls==[1]
        assert values[0]['status']==(409 if isinstance(error,HTTPException) else 500)
        assert 'private detail' not in json.dumps(values)
    asyncio.run(run())


def test_stream_route_authenticates_before_starting_owned_execution(monkeypatch):
    import httpx
    from fastapi import FastAPI
    from types import SimpleNamespace
    from apps.live_control_server.routes import agent
    from tests.test_agent_turn_route import _payload

    app=FastAPI();app.include_router(agent.router)
    calls=[]
    def execute(body, request):
        calls.append(body.turn_id)
        stream.observe({'sequence':1})
        return {'answer':'saved'}
    monkeypatch.setattr(agent,'_execute_agent_turn',execute)
    monkeypatch.setattr(agent,'enforce_native_graph_gm',lambda request:SimpleNamespace(subject='test'))
    payload={**_payload(), 'surface':{'surface_id':'build','instance_id':'build-test'},
        'owner_scope':{'kind':'world','world_id':'world'},
        'primary_work':{'kind':'build','object_id':'doc','expected_revision':1,'expected_content_sha256':'a'*64},
        'client_work_state':'saved_clean'}
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            response=await client.post('/agent/turn',json=payload,headers={'accept':'text/event-stream'})
            assert response.status_code==200, response.text
            frames=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
            assert frames[-1]['kind']=='result' and calls==[payload['turn_id']]
            def deny(_):
                raise HTTPException(403,detail='forbidden')
            monkeypatch.setattr(agent,'enforce_native_graph_gm',deny)
            refused=await client.post('/agent/turn',json=payload,headers={'accept':'text/event-stream'})
            assert refused.status_code==403 and len(calls)==1
    asyncio.run(run())
