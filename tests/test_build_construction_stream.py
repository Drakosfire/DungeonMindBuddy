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
        assembled = []
        def snapshot(sequence):
            assembled.append(sequence)
            return {'sequence': sequence, 'markdown': 'x' * sequence}

        def work():
            for sequence in range(1, 1001):
                stream.observe_deferred(lambda sequence=sequence: snapshot(sequence))
            emitted.set()
            return {'answer': 'saved'}
        iterator = stream.turn_stream(work, 'turn').body_iterator
        first = asyncio.create_task(anext(iterator))
        assert await asyncio.to_thread(emitted.wait, 2)
        for task in tuple(stream._running):
            await task
        assert assembled == []
        assert len(held) == 1
        callback, args, kwargs = held.pop()
        original(callback, *args, **kwargs)
        frame = json.loads((await first).removeprefix('data: '))
        assert assembled == [1000]
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
        reply = stream.reply_sink.get()
        if reply is not None:
            reply(None)
            reply("Answer")
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
            assert [frame["kind"] for frame in frames] == ["construction", "result"]
            enabled = await client.post('/agent/turn', json=payload,
                headers={'accept': 'text/event-stream', 'x-buddy-reply-stream': '1'})
            assert enabled.status_code == 200
            frames = [json.loads(line[6:]) for line in enabled.text.splitlines() if line.startswith('data: ')]
            assert [frame["kind"] for frame in frames] == [
                "construction", "reply_context_ready", "reply_text", "result",
            ]
            def deny(_):
                raise HTTPException(403,detail='forbidden')
            monkeypatch.setattr(agent,'enforce_native_graph_gm',deny)
            refused=await client.post('/agent/turn',json=payload,headers={'accept':'text/event-stream'})
            assert refused.status_code==403 and len(calls)==2
    asyncio.run(run())


def test_opt_in_reply_text_is_ordered_and_does_not_replace_construction_or_result():
    async def run():
        release = threading.Event()

        def work():
            stream.observe({"sequence": 1})
            reply = stream.reply_sink.get()
            if reply is not None:
                reply(None)
                reply("A lantern")
                release.wait(2)
                reply(" lights the path.")
            return {"answer": "The canonical saved reply", "citations": ["saved"]}

        def parse(frame):
            return json.loads(frame.removeprefix("data: "))

        old = [parse(frame) async for frame in stream.turn_stream(work, "turn").body_iterator]
        assert [frame["kind"] for frame in old] == ["construction", "result"]

        reader = stream.turn_stream(work, "turn", include_reply=True).body_iterator
        first = [parse(await asyncio.wait_for(anext(reader), 2)) for _ in range(3)]
        assert [frame["kind"] for frame in first] == ["construction", "reply_context_ready", "reply_text"]
        assert first[2]["sequence"] == 1 and first[2]["text"] == "A lantern"
        release.set()
        rest = [parse(frame) async for frame in reader]
        assert [(frame["kind"], frame.get("sequence")) for frame in rest] == [
            ("reply_text", 2), ("result", None),
        ]
        assert rest[0]["text"] == " lights the path."
        assert rest[1]["response"] == {"answer": "The canonical saved reply", "citations": ["saved"]}

    asyncio.run(run())


@pytest.mark.parametrize("failed", [False, True])
def test_guarded_sdk_projects_only_the_assistant_final_answer_item(failed):
    import httpx
    from generationengine import GenerationClient, GenerationEngineError, TextRequest
    from generationengine.text_dispatch import TextDispatchGate
    from apps.live_control_server.services.build_reply_writer import BuildAnswerObserver, generate_build_reply
    from apps.live_control_server.services.plan_jev_writer import PlanWriterProvider

    commentary = '{"answer_segments":[{"text":"Private commentary"}]}'
    chunks = ['{"answer_segments":[{"text":"The lantern', ' lit the gate."}]}']
    model = "gpt-6-luna"
    answer = dict(type="message", role="assistant", id="answer", status="in_progress",
                  phase="final_answer", content=[])
    comment = dict(type="message", role="assistant", id="comment", status="in_progress",
                   phase="commentary", content=[])
    output = [
        {**item, "status": "completed", "content": [
            {"type": "output_text", "text": text, "annotations": []},
        ]}
        for item, text in [(comment, commentary), (answer, "".join(chunks))]
    ]

    async def run():
        observed = []
        lifecycle = []
        requests = []

        class Events(httpx.AsyncByteStream):
            async def __aiter__(self):
                frames = [
                    ("response.output_item.added", dict(item=comment, output_index=0)),
                    ("response.output_text.delta", dict(item_id="comment", output_index=0,
                                                       content_index=0, delta=commentary)),
                    ("response.output_item.added", dict(item=answer, output_index=1)),
                    *[("response.output_text.delta", dict(item_id="answer", output_index=1,
                                                         content_index=0, delta=text)) for text in chunks],
                ]
                for index, (kind, fields) in enumerate(frames):
                    yield ("data: " + json.dumps(dict(type=kind, sequence_number=index, **fields))
                           + "\n\n").encode()
                assert observed == ["The lantern", " lit the gate."]  # Before provider completion.
                if not failed:
                    result = dict(id="rsp", object="response", created_at=1, status="completed",
                                  model=model, output=output)
                    yield ("data: " + json.dumps(dict(type="response.completed",
                                                       sequence_number=len(frames), response=result))
                           + "\n\n").encode()

        async def authorize(prepared):
            assert json.loads(prepared.body)["stream"] is True
            lifecycle.append("authorized")
            return True

        async def record(event):
            lifecycle.append(event.outcome)
            return True

        def handle(request):
            requests.append(request)
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=Events())

        provider = PlanWriterProvider(api_key="synthetic", transport=httpx.MockTransport(handle),
            dispatch_gate=TextDispatchGate(authorize, record),
            sdk_event_observer=BuildAnswerObserver(observed.append))
        client = GenerationClient(text_providers={"openai": provider})
        schema = {
            "type": "object", "additionalProperties": False, "required": ["answer_segments"],
            "properties": {"answer_segments": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["text"],
                "properties": {"text": {"type": "string"}},
            }}},
        }
        request = TextRequest(provider="openai", model=model, json_schema=schema, schema_name="reply_test",
                              user_prompt='[{"role":"user","content":"Test"}]',
                              max_transport_retries=0, max_conformance_retries=0)
        try:
            if failed:
                with pytest.raises(GenerationEngineError):
                    await generate_build_reply(client, request)
                assert provider.actual_response is None
            else:
                result = await generate_build_reply(client, request)
                assert result.text == "".join(chunks)
                assert provider.consume_completed_text(provider.actual_response, model) == result.text
            assert len(requests) == 1 and lifecycle[:2] == ["authorized", "sending"]
            assert observed == ["The lantern", " lit the gate."]
        finally:
            await client.aclose()

    asyncio.run(run())
