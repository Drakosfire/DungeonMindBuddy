"""Actual SDK capture → APP completion → exact native section history; no network."""
import asyncio
import json
from hashlib import sha256
from uuid import uuid4

import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.surface_evidence_answer import SELECTOR_POLICY
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_plan_jev_writer import stage_graph,WriterWire
from tests.application_state import test_native_source_catalog_postgres as catalogs
from tests.application_state.test_native_source_sections_postgres import authorize,extract


@pytest.fixture
def native_writer(plan_adapter,monkeypatch):
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    original_accept = AgentConversationService.accept_turn
    def accept(service,sub):
        execution = sub.graph_context_execution
        policy = t.PlanNativeSourceSectionsPolicyV1.model_validate(execution.policy.model_dump(mode='json',by_alias=True) | {
            'native_source_section_policy':'exact_native_source_sections_v1'})
        wire = execution.model_dump(mode='json',by_alias=True)
        wire['policy'] = policy.model_dump(mode='json',by_alias=True)
        wire['execution_policy_sha256'] = t.canonical_sha256({'schema':execution.schema_,
            'context_receipt_sha256':execution.context_receipt_sha256,'policy':wire['policy']})
        return original_accept(service,sub.model_copy(update={'graph_context_execution':type(execution).model_validate(wire)}))
    monkeypatch.setattr(AgentConversationService,'accept_turn',accept)
    def named(turn,donor,pin):
        execution,authority = turn.graph_context_execution,turn.graph_context_receipt.graph_authority
        scope = {'world_id':authority.native_world_id,'campaign_id':None,'admissibility':'gm',
            'scope_mode':'world_cross_campaign','focus':{'kind':'none','session_id':None}}
        identity = {'source_artifact_id':pin.source_artifact_id,'source_revision_id':pin.source_revision_id}
        anchor = ('dm-source-anchor:v1:'+pin.anchor_id[len('source-anchor:v1:'):]
            if pin.anchor_id.startswith('source-anchor:v1:') else pin.anchor_id)
        proof = {'schema':'dmb_native_source_origin_proof_v1','donor':donor.model_dump(mode='json'),
            'donor_sha256':t.canonical_sha256(donor.model_dump(mode='json')),'pin':pin.model_dump(mode='json'),
            'projection':scope|{'revision_pin':donor.graph_revision},
            'resolution':identity|{'evidence_ref_id':pin.evidence_ref_id,'anchor_id':anchor,'can_open_source':True,
                'snapshot':scope|{'revision_id':donor.graph_revision},
                'artifact':{'source_artifact_id':pin.source_artifact_id,'world_id':authority.native_world_id,
                    'source_domain':'worldbuilding','status':'active','visibility':'gm',
                    'lineage':{'source_name':'Synthetic marsh adventure'}},
                'evidence':identity|{'evidence_ref_id':pin.evidence_ref_id,'source_domain':'worldbuilding'}},
            'revision':identity|{'content_sha256':'c'*64}}
        provider = next(e for e in reversed(execution.events) if isinstance(e,t.ProviderAttemptAuthorizedEventV1))
        return t.NativeSourceNavigationAuthorizedV1(kind='native_source_navigation_authorized_v1',
            event_id=uuid4(),sequence=len(execution.events),navigation_id=uuid4(),provider_attempt_id=provider.provider_attempt_id,
            context_receipt_sha256=execution.context_receipt_sha256,execution_policy_sha256=execution.execution_policy_sha256,
            world_id=turn.world_id,native_world_id=authority.native_world_id,binding_version=authority.binding_version,
            origin_proof_json=json.dumps(proof),origin_proof_sha256=t.canonical_sha256(proof))
    monkeypatch.setattr(catalogs,'authorization',named)
    original_read = PlanJevDriver._read_new_sources
    def read(driver,operations):
        original_read(driver,operations)
        a = driver.adapter
        with a.fence.renewer._lock:
            turn = a.fence.renewer._turn
            if any(isinstance(e,t.NativeSourceCatalogObservedV1) for e in turn.graph_context_execution.events):return
            donor = next(e for e in reversed(turn.graph_context_execution.events)
                if isinstance(e,t.ValidatedGraphOperationEventV3) and e.returned_source_pins)
            case = catalogs.grant((a.service,turn,donor,donor.returned_source_pins[0]))
            turn,_,material = catalogs.read(case)
            catalog = turn.graph_context_execution.events[-1]
            turn,_ = authorize((a.service,turn,catalog,material))
            turn,_,_ = extract((a.service,turn,catalog,material),turn.graph_context_execution.events[-1])
            a.fence.renewer._turn = turn
            a.turn = turn
    monkeypatch.setattr(PlanJevDriver,'_read_new_sources',read)
    return stage_graph(plan_adapter)


def answer(writer,**changes):
    section = writer.projection.frame['native_source_sections']['sections'][0]
    row = {'kind':'native_source_claim','text':'The appendix describes the tree mechanics.',
        'section_handles':[section['section_handle']]}
    row.update(changes)
    return {'schema':SELECTOR_POLICY,'answer_segments':[row],'limitations':[],'requested_detail_gaps':[]}


def finish(writer,payload=None):
    return asyncio.run(writer.run(transport=WriterWire(writer.adapter,json.dumps(payload or answer(writer))),
        api_key='synthetic-not-secret'))


def test_actual_writer_native_section_citation_persists_and_reopens(native_writer):
    completed = finish(native_writer)
    assert completed.status == 'completed'
    assert isinstance(completed.completion,t.SurfaceEvidenceCompletionV3)
    assert completed.completion.source_citations == []
    citation = completed.completion.native_source_citations[0]
    assert citation.source_name == 'Synthetic marsh adventure'
    assert citation.section_title.endswith('Appendix A')
    assert citation.line_start == 3 and citation.line_end == 4
    assert citation.excerpt_sha256 == sha256('## Appendix A\r\nTree mechanics.\r\n'.encode()).hexdigest()
    assert citation.content_sha256 != citation.excerpt_sha256
    reopened = AgentConversationService().inspect_turn(world_id=completed.world_id,turn_id=completed.turn_id)
    assert reopened.completion == completed.completion and reopened.assistant_text == completed.assistant_text
    history = AgentConversationService().list_turns(completed.world_id,completed.conversation_id)[-1]
    assert history.completion == completed.completion
    from application_state.agent_conversation.repository import _plan_ask_history_attribution
    attribution = _plan_ask_history_attribution(reopened)
    assert isinstance(attribution,t.PlanEvidenceHistoryAttributionV3)
    assert attribution.native_source_citations == completed.completion.native_source_citations


@pytest.mark.parametrize('change',['foreign','empty','metadata','graph','old_policy'])
def test_unexposed_or_mislabeled_native_claim_is_not_completed(native_writer,change):
    payload = answer(native_writer)
    row = payload['answer_segments'][0]
    if change == 'foreign':row['section_handles'] = ['n'+'f'*64]
    elif change == 'empty':row['section_handles'] = []
    elif change == 'metadata':row['source_name'] = 'Caller label'
    elif change == 'graph':row.update(kind='graph_claim',claim_id='claim:1',target_kind='assertion',target_id='assertion:pond')
    else:payload['schema'] = 'dmb_surface_evidence_answer_v2'
    with pytest.raises(Exception):finish(native_writer,payload)
    current = native_writer.adapter.service.inspect_turn(world_id=native_writer.adapter.world_id,
        turn_id=native_writer.adapter.turn.turn_id)
    assert current.completion is None


@pytest.mark.parametrize('field',['source_name','line_start','content_sha256','read_event_id','provider_attempt_id'])
def test_completion_seal_rejects_native_citation_tamper(native_writer,field):
    completed = finish(native_writer)
    wire = completed.model_dump(mode='json',by_alias=True)
    row = wire['completion']['native_source_citations'][0]
    if field == 'source_name':row[field] = 'Different source'
    elif field == 'line_start':row[field] += 1
    elif field == 'content_sha256':row[field] = 'f'*64
    else:row[field] = str(uuid4())
    with pytest.raises(ValueError):type(completed).model_validate(wire)


def test_populated_native_citation_downgrade_refuses_loss(native_writer,application_state_dsn):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    finish(native_writer)
    engine = create_engine(application_state_dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError,match='retained native source citations'):
                    import_module('application_state.migrations.versions.20261023_0057_native_source_citations').downgrade()
    finally:engine.dispose()


def test_native_graph_passage_and_authored_block_keep_separate_support(native_writer):
    frame = native_writer.projection.frame
    payload = answer(native_writer)
    payload['answer_segments'] += [
        {'kind':'source_passage_claim','text':'The journal describes a walkway.',
            'passage_handles':[frame['opened_passages'][0]['passage_handle']]},
        {'kind':'graph_claim','claim_id':'claim:1','text':'The pond has a walkway.',
            'target_kind':'assertion','target_id':'assertion:pond','passage_handles':[]},
        {'kind':'authored_excerpt','selection_id':frame['committed_plan_blocks'][1]['selection_id']}]
    completed = finish(native_writer,payload)
    assert len(completed.completion.native_source_citations) == 1
    assert completed.completion.native_source_citations[0].segment_index == 0
    assert completed.completion.source_citations[0].segment_index == 1
    assert completed.completion.citation_map.entries[0].source_opened is False
    assert completed.completion.answer_segments[3].kind == 'authored_excerpt'


from tests.application_state.test_native_source_input_postgres import input_case,prepare,admit  # noqa: F401,E402
from tests.application_state.test_native_source_navigation_postgres import nav_case  # noqa: F401,E402


def test_shared_plan_play_normalization_uses_actual_admitted_section_input(input_case):
    from types import SimpleNamespace
    from application_state.agent_conversation.native_source_answer import producing_sections
    from application_state.agent_conversation.native_answer_output import normalize_native_answer
    from application_state.agent_conversation.surface_evidence_answer import SELECTOR_INSTRUCTIONS,require_current_policy
    service,_,_ = input_case
    turn,auth,raw,proof = prepare(input_case)
    if turn.provenance.surface_id == 'play':
        body = json.loads(raw)
        carrier = json.loads(body['messages'][0]['content'])
        from application_state.agent_conversation.play_graph_input import unpack_play_frame,pack_selector_play_frame
        carrier['source_frame']=pack_selector_play_frame(unpack_play_frame(carrier['source_frame']),str(turn.idempotency_key))
        carrier.update(schema='dmb_native_play_input_v5',answer_policy=SELECTOR_POLICY,answer_instructions=SELECTOR_INSTRUCTIONS)
        body['messages'][0]['content'] = json.dumps(carrier)
        raw = json.dumps(body,ensure_ascii=False)
        auth = auth.model_copy(update={'envelope_sha256':sha256(raw.encode()).hexdigest()})
    turn,_ = admit(service,turn,auth,raw,proof)
    for outcome in ('sdk_entered','response_received'):
        turn,_ = service.record_provider_outcome(turn.world_id,turn.conversation_id,turn.turn_id,
            expected_revision=turn.revision,expected_attempt=turn.attempt,
            outcome=t.ProviderOutcomeEventV1(kind='provider_outcome',event_id=uuid4(),
                sequence=len(turn.graph_context_execution.events),provider_attempt_id=auth.provider_attempt_id,outcome=outcome))
    sections = producing_sections(turn,auth,raw)
    support = SimpleNamespace(provider_attempt_id=auth.provider_attempt_id,envelope_sha256=auth.envelope_sha256,
        context_receipt_sha256=turn.graph_context_receipt.context_receipt_sha256,
        graph_revision=turn.graph_context_receipt.graph_authority.graph_revision,closures=(),passages=(),authored=(),
        native_sections=sections,current_policy=require_current_policy(turn,auth,raw),source_partial=False)
    completion,bindings,text = normalize_native_answer({'schema':support.current_policy,'limitations':[],
        'requested_detail_gaps':[],'answer_segments':[{'kind':'native_source_claim',
            'text':'The appendix describes a tree.','section_handles':[sections[0].handle]}]},
        turn,auth.provider_attempt_id,support=support)
    assert isinstance(completion,t.SurfaceEvidenceCompletionV3)
    assert completion.surface_id == turn.provenance.surface_id
    assert completion.native_source_citations[0].read_event_id == sections[0].read.event_id
    assert not bindings and text == 'The appendix describes a tree.'


def test_actual_completed_reply_survives_public_response_roundtrip(native_writer):
    from apps.live_control_server.services.agent_turn_service import _completed_turn_replay
    completed = finish(native_writer)
    response = _completed_turn_replay(native_writer.adapter.request,
        owner={'kind':'world','id':completed.world_id,'name':'Synthetic World'},turn=completed)
    decoded = type(response).model_validate_json(response.model_dump_json(by_alias=True))
    assert isinstance(decoded.plan_context.completion,t.SurfaceEvidenceCompletionV3)
    assert decoded.plan_context.completion.native_source_citations == completed.completion.native_source_citations
    from apps.live_control_server.models.agent_turn import AgentPlayWorldGraphContextResponseV1
    # The native Play public envelope must preserve the same typed citation through
    # a dict/JSON boundary too; its input/completion joins are tested separately.
    from tests.test_play_graph_context import fixture
    receipt,_,_ = fixture()
    completion = completed.completion.model_copy(update={'surface_id':'play',
        'context_receipt_sha256':receipt.context_receipt_sha256})
    play = AgentPlayWorldGraphContextResponseV1(receipt=receipt,completion=completion,
        execution=None,delivery_replay=False)
    reopened = AgentPlayWorldGraphContextResponseV1.model_validate_json(play.model_dump_json(by_alias=True))
    assert reopened.completion == completion
