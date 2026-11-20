"""Native source inclusion owns exact Plan/Play input, not model output claims."""
from hashlib import sha256
from importlib import import_module
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_source_input import project_sections, prove_input, SCHEMA, TOOL
from application_state.errors import ApplicationStateValidationError, ApplicationStateConflictError
from tests.application_state.test_native_source_navigation_postgres import nav_case  # noqa: F401
from tests.application_state import test_native_source_catalog_postgres as catalog_tests
from tests.application_state.test_native_source_sections_postgres import authorize, extract


@pytest.fixture
def input_case(nav_case,monkeypatch):
    original = catalog_tests.authorization
    def named(*args):
        event = original(*args)
        proof = json.loads(event.origin_proof_json)
        proof['resolution']['artifact']['lineage'] = {'source_name':'Synthetic marsh adventure'}
        return type(event).model_validate(event.model_dump(mode='json') | {
            'origin_proof_json':json.dumps(proof),'origin_proof_sha256':t.canonical_sha256(proof)})
    monkeypatch.setattr(catalog_tests,'authorization',named)
    service,turn,nav,_ = catalog_tests.grant(nav_case)
    turn,_,material = catalog_tests.read((service,turn,nav,None))
    catalog = turn.graph_context_execution.events[-1]
    turn,_ = authorize((service,turn,catalog,material))
    turn,_,read = extract((service,turn,catalog,material),turn.graph_context_execution.events[-1])
    return service,turn,read


def prepare(case):
    service,turn,read = case
    if turn.provenance.surface_id == 'plan':
        from tests.application_state.test_plan_jev_writer_packet import writer_request,evidence
        from tests.application_state.test_plan_jev_decision_admission import append
        controller = service.nav_test_controller
        controller.turn = turn
        controller.redecide('finish_retrieval')
        append(controller)
        proof = evidence(controller)
        auth,raw = writer_request(controller,proof)
        return controller.turn,auth,raw,proof
    from application_state.agent_conversation.play_graph_authority import play_source_frame
    from application_state.agent_conversation.play_graph_input import NativePlayInputV3,pack_play_frame
    from application_state.agent_conversation.surface_evidence_answer import INSTRUCTIONS
    from tests.test_play_graph_authority import native_provider
    basis = turn.play_context_receipt
    frame = play_source_frame((t.PlaySourcePayloadV1(source_kind='scene_note',
        locator=t.play_source_locator(basis),text=basis.scene_note),))
    carrier = NativePlayInputV3(submission_id=turn.idempotency_key,message=turn.user_text,
        source_frame=pack_play_frame(frame),answer_instructions=INSTRUCTIONS)
    raw = json.dumps({'model':'synthetic','tools':[],'messages':[
        {'role':'user','content':carrier.model_dump_json(by_alias=True)},
        {'role':'assistant','tool_calls':[{'id':'selected-native-section','type':'function',
            'function':{'name':TOOL,'arguments':'{}'}}]},
        {'role':'tool','tool_call_id':'selected-native-section',
            'content':json.dumps(project_sections(turn.graph_context_execution))}]},ensure_ascii=False)
    auth = native_provider(len(turn.graph_context_execution.events)+1).model_copy(update={
        'envelope_sha256':sha256(raw.encode()).hexdigest(),'api_mode':'chat_completions'})
    return turn,auth,raw,None


def admit(service,turn,auth,raw,proof,**overrides):
    common = dict(expected_revision=turn.revision,expected_attempt=turn.attempt) | overrides
    if turn.provenance.surface_id == 'plan':
        return service.authorize_plan_jev_writer(turn.world_id,turn.conversation_id,turn.turn_id,
            authorization=auth,producer_proof={'prepared_request_json':raw,'evidence':proof},**common)
    return service.authorize_native_play_provider(turn.world_id,turn.conversation_id,turn.turn_id,
        provider_attempt_event=auth,prepared_request_json=raw,**common)


def test_exact_input_commits_with_provider_and_reopens(input_case):
    service,_,read = input_case
    turn,auth,raw,proof = prepare(input_case)
    updated,fresh = admit(service,turn,auth,raw,proof)
    assert fresh
    inclusion = updated.graph_context_execution.events[-1]
    assert isinstance(inclusion,t.NativeSourceProviderInclusionV1)
    assert inclusion.provider_attempt_id == auth.provider_attempt_id
    assert inclusion.envelope_sha256 == sha256(raw.encode()).hexdigest()
    assert inclusion.read_event_ids == [read.event_id]
    assert inclusion.selected_chars == read.returned_chars
    assert service.list_turns(turn.world_id,turn.conversation_id)[-1] == updated
    replay,fresh = admit(service,updated,auth,raw,proof)
    assert not fresh and replay == updated
    with pytest.raises(ApplicationStateConflictError):admit(service,turn,auth,raw,proof)


@pytest.mark.parametrize('change',['text','name','range','handle','duplicate','missing','envelope'])
def test_exact_prepared_input_rejects_changed_section(input_case,change):
    service,_,_ = input_case
    turn,auth,raw,proof = prepare(input_case)
    body = json.loads(raw)
    if proof is not None:
        frame = json.loads(body['input'][0]['content'])
        native = frame['native_source_sections']
    else:
        native = json.loads(body['messages'][-1]['content'])
    row = native['sections'][0]
    if change == 'text':row['text'] += ' fabricated'
    elif change == 'name':row['source_name'] = 'Different adventure'
    elif change == 'range':row['line_start'] += 1
    elif change == 'handle':row['section_handle'] = 'n'+'f'*64
    elif change == 'duplicate':native['sections'].append(dict(row))
    elif change == 'missing':native['sections'] = []
    if proof is not None:
        body['input'][0]['content'] = json.dumps(frame)
    else:body['messages'][-1]['content'] = json.dumps(native)
    changed = json.dumps(body,ensure_ascii=False)
    auth = auth.model_copy(update={'envelope_sha256':sha256(changed.encode()).hexdigest()})
    if change == 'envelope':changed += ' '
    with pytest.raises((ApplicationStateValidationError,ValueError)):
        admit(service,turn,auth,changed,proof)
    assert service.list_turns(turn.world_id,turn.conversation_id)[-1].revision == turn.revision


def test_raw_or_missing_inclusion_cannot_create_authority(input_case):
    service,_,_ = input_case
    turn,auth,raw,proof = prepare(input_case)
    inclusion = prove_input(turn,auth,raw,sequence=auth.sequence+1)
    with pytest.raises(ApplicationStateValidationError,match='transaction owner'):
        service._append_graph_execution_event(turn.world_id,turn.conversation_id,turn.turn_id,
            expected_revision=turn.revision,expected_attempt=turn.attempt,event=inclusion,duplicate_key='event_id')
    updated,_ = admit(service,turn,auth,raw,proof)
    wire = updated.graph_context_execution.model_dump(mode='json',by_alias=True)
    wire['events'].pop()
    with pytest.raises(ValueError,match='same transaction'):type(updated.graph_context_execution).model_validate(wire)


def test_populated_input_downgrade_refuses_loss(input_case,application_state_dsn):
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    service,_,_ = input_case
    turn,auth,raw,proof = prepare(input_case)
    admit(service,turn,auth,raw,proof)
    engine = create_engine(application_state_dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError,match='retained native source input'):
                    import_module('application_state.migrations.versions.20261022_0056_native_source_input').downgrade()
    finally:engine.dispose()


def test_source_names_have_no_identifier_fallback(input_case):
    from types import SimpleNamespace
    from application_state.agent_conversation.native_source_input import source_name
    _,turn,read = input_case
    events = []
    for event in turn.graph_context_execution.events:
        if isinstance(event,t.NativeSourceNavigationAuthorizedV1):
            proof = json.loads(event.origin_proof_json)
            proof['resolution']['artifact']['lineage'] = {}
            event = type(event).model_validate(event.model_dump(mode='json') | {
                'origin_proof_json':json.dumps(proof),'origin_proof_sha256':t.canonical_sha256(proof)})
        events.append(event)
    with pytest.raises(ValueError,match='registered source name'):
        source_name(SimpleNamespace(events=events),read)


@pytest.mark.parametrize('field',['selected_chars','frame_sha256','provider_attempt_id','read_event_ids'])
def test_historical_input_receipt_cannot_be_rebound(input_case,field):
    service,_,_ = input_case
    turn,auth,raw,proof = prepare(input_case)
    updated,_ = admit(service,turn,auth,raw,proof)
    wire = updated.graph_context_execution.model_dump(mode='json',by_alias=True)
    row = wire['events'][-1]
    if field == 'selected_chars':row[field] += 1
    elif field == 'frame_sha256':row[field] = 'f'*64
    elif field == 'provider_attempt_id':row[field] = str(uuid4())
    else:row[field] = [str(uuid4())]
    with pytest.raises(ValueError):type(updated.graph_context_execution).model_validate(wire)


@pytest.mark.parametrize("protocol",["chat_completions","codex_responses"])
def test_native_play_history_is_preserved_without_donating_current_authority(input_case,protocol):
    service,_,read = input_case
    turn,auth,raw,proof = prepare(input_case)
    if proof is not None:pytest.skip('Native Play retains SDK tool history; Plan projects dialogue separately')
    body = json.loads(raw)
    old = project_sections(turn.graph_context_execution)
    old['sections'][0]['section_handle'] = 'n'+'a'*64
    old['sections'][0]['text'] = 'Earlier turn, not current evidence.'
    history = [
        {'role':'assistant','tool_calls':[{'id':'old-read','type':'function',
            'function':{'name':TOOL,'arguments':'{}'}}]},
        {'role':'tool','tool_call_id':'old-read','content':json.dumps(old)}]
    body['messages'] = history + body['messages']
    if protocol == 'codex_responses':
        items = []
        for message in body.pop('messages'):
            if message['role'] == 'assistant':
                for call in message['tool_calls']:
                    items.append({'type':'function_call','call_id':call['id'],**call['function']})
            elif message['role'] == 'tool':
                items.append({'type':'function_call_output','call_id':message['tool_call_id'],
                    'output':message['content']})
            else:items.append(message)
        body['input'] = items
    raw = json.dumps(body,ensure_ascii=False)
    auth = auth.model_copy(update={'envelope_sha256':sha256(raw.encode()).hexdigest(),'api_mode':protocol})
    updated,fresh = admit(service,turn,auth,raw,proof)
    assert fresh and updated.graph_context_execution.events[-1].read_event_ids == [read.event_id]


def test_historical_tool_frame_cannot_replace_current_source_output(input_case):
    service,_,_ = input_case
    turn,auth,raw,proof = prepare(input_case)
    if proof is not None:pytest.skip('Native Play tool history only')
    body = json.loads(raw)
    user,call,output = body['messages']
    body['messages'] = [call,output,user]
    raw = json.dumps(body,ensure_ascii=False)
    auth = auth.model_copy(update={'envelope_sha256':sha256(raw.encode()).hexdigest()})
    with pytest.raises(ApplicationStateValidationError,match='lacks an exact successful section'):
        admit(service,turn,auth,raw,proof)
    assert service.list_turns(turn.world_id,turn.conversation_id)[-1].revision == turn.revision
