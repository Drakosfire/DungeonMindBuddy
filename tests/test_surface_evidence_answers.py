"""Actual captured writer → sealed APP completion; synthetic source prose only."""
import asyncio
import json
import pytest
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.surface_evidence_answer import POLICY
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_plan_jev_writer import WriterWire, stage_graph
from tests.test_surface_source_answers import stage


def wire_answer(segments):
    return dict(schema=POLICY, answer_segments=segments, limitations=[], requested_detail_gaps=[])


def test_actual_mixed_source_and_literal_plan_quote_persist(plan_adapter,application_state_dsn):
    writer = stage(plan_adapter)
    frame = writer.projection.frame
    quote = frame['committed_plan_blocks'][1]['text']
    payload = wire_answer([
        dict(kind='source_passage_claim', text='The journal describes a wooden walkway.',
            passage_handles=[frame['opened_passages'][0]['passage_handle']]),
        dict(kind='authored_excerpt',block_handle=frame['committed_plan_blocks'][1]['block_handle']),
        dict(kind='proposal', text='We could begin beside the pond.', label='invented_idea')])
    wire = WriterWire(plan_adapter, json.dumps(payload))
    completed = asyncio.run(writer.run(transport=wire, api_key='synthetic-not-secret'))
    assert completed.status == 'completed' and len(wire.calls) == 1
    assert isinstance(completed.completion, t.SurfaceEvidenceCompletionV1)
    assert len(completed.completion.source_citations) == 1
    assert completed.completion.answer_segments[1].text == quote
    assert frame['authored_sources'][0]['body_path'] == ['committed_plan_blocks']
    reopened = AgentConversationService().inspect_turn(world_id=completed.world_id, turn_id=completed.turn_id)
    assert reopened.completion == completed.completion
    # SQL admits the current shape but rejects reintroducing an old claim kind.
    import psycopg
    from psycopg.types.json import Jsonb
    forged=completed.completion.model_dump(mode='json',by_alias=True)
    forged['answer_segments'][0]['kind']='plan_claim'
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute('UPDATE agent.turn SET completion=%s WHERE turn_id=%s',(Jsonb(forged),completed.turn_id))
    assert AgentConversationService().inspect_turn(world_id=completed.world_id,turn_id=completed.turn_id).completion==completed.completion
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    migration=import_module('application_state.migrations.versions.20261022_0048_authored_excerpt_blocks')
    engine=create_engine(application_state_dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError,match='retained authored block'):
                    migration.downgrade()
    finally: engine.dispose()


@pytest.mark.parametrize('kind', ['plan_claim','session_evidence_claim','play_context_claim','connective','authored_quote'])
def test_source_facts_cannot_be_laundered_as_authored_material(plan_adapter, kind):
    writer = stage(plan_adapter)
    row = dict(kind=kind, text='The source-only secret is a purple bridge.')
    if kind == 'authored_quote': row['source_handle'] = writer.projection.frame['authored_sources'][0]['handle']
    wire = WriterWire(plan_adapter, json.dumps(wire_answer([row])))
    with pytest.raises(Exception):
        asyncio.run(writer.run(transport=wire, api_key='synthetic-not-secret'))
    turn = plan_adapter.service.inspect_turn(world_id=plan_adapter.world_id, turn_id=plan_adapter.turn.turn_id)
    assert turn.status != 'completed' and turn.completion is None and len(wire.calls) == 1


@pytest.mark.parametrize('opened', [False, True])
def test_graph_uses_only_explicit_selected_passages(plan_adapter, opened):
    writer = stage_graph(plan_adapter)
    frame = writer.projection.frame
    row = dict(kind='graph_claim', claim_id='claim:1', text='The pond has a wooden walkway.',
        target_kind='assertion', target_id='assertion:pond',
        passage_handles=[frame['opened_passages'][0]['passage_handle']] if opened else [])
    completed = asyncio.run(writer.run(transport=WriterWire(plan_adapter, json.dumps(wire_answer([row]))), api_key='synthetic-not-secret'))
    entry = completed.completion.citation_map.entries[0]
    assert entry.source_opened == opened
    assert len(completed.completion.source_citations) == int(opened)


@pytest.mark.parametrize('bad', [[], ['foreign'], [['unhashable']], [None]])
def test_current_source_claim_rejects_missing_or_invalid_handles(plan_adapter, bad):
    writer = stage(plan_adapter)
    row=dict(kind='source_passage_claim',text='A journal fact.',passage_handles=bad)
    wire=WriterWire(plan_adapter,json.dumps(wire_answer([row])))
    with pytest.raises(Exception):
        asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    assert plan_adapter.service.inspect_turn(world_id=plan_adapter.world_id,turn_id=plan_adapter.turn.turn_id).completion is None


def test_current_writer_refuses_old_wire_even_with_real_opened_passage(plan_adapter):
    writer=stage(plan_adapter)
    payload=dict(schema='dmb_surface_source_answer_v1',answer_context_status='source_grounded',answer_segments=[
        dict(kind='source_passage_claim',text='A journal fact.',passage_handles=[writer.projection.frame['opened_passages'][0]['passage_handle']])])
    with pytest.raises(Exception):
        asyncio.run(writer.run(transport=WriterWire(plan_adapter,json.dumps(payload)),api_key='synthetic-not-secret'))


def test_closed_limitation_text_is_derived_by_host(plan_adapter):
    writer=stage(plan_adapter)
    payload=wire_answer([]);payload['limitations']=['unresolved_conflict']
    completed=asyncio.run(writer.run(transport=WriterWire(plan_adapter,json.dumps(payload)),api_key='synthetic-not-secret'))
    from application_state.agent_conversation.source_writer_output import LIMITATIONS
    assert completed.assistant_text==LIMITATIONS['unresolved_conflict']
    assert completed.completion.answer_context_status=='insufficient_evidence'


@pytest.mark.parametrize('with_graph',[False,True])
def test_current_mixed_contract_includes_rules_without_another_writer(plan_adapter,monkeypatch,with_graph):
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from tests.test_plan_jev_driver import Decisions
    from tests.test_rules_lookup_broker import args
    from apps.live_control_server.services import agent_turn_service as owner
    a=plan_adapter
    a.request=a.request.model_copy(update={'message':args().question})
    a.submitted_intent=owner._submitted_turn_intent(a.request,world_id=a.world_id)
    if with_graph:
        from graph_memory.interaction.session import GraphReferent
        from tests.test_plan_jev_driver import fixture_reads
        a.bootstrap.retrieval_session.referents=[GraphReferent(id='pond',label='Park pond')]
        fixture_reads(a)
    rules=PlanRulesRuntime(a,rules_capability(graph=True))
    proof=asyncio.run(PlanJevDriver(a,rules=rules).run(transport=Decisions(),api_key='synthetic-not-secret'))
    writer=PlanJevWriter(a,proof,rules)
    capsule=rules.frame().supports[0]
    quoted=writer.projection.frame['committed_plan_blocks'][0]['text']
    base=wire_answer([dict(kind='authored_excerpt',block_handle=writer.projection.frame['committed_plan_blocks'][0]['block_handle'])])
    if with_graph:
        handle=writer.projection.frame['opened_passages'][0]['passage_handle']
        base['answer_segments'] += [dict(kind='graph_claim',claim_id='claim:1',text='The pond has a wooden walkway.',
            target_kind='assertion',target_id='assertion:pond',passage_handles=[handle]),
            dict(kind='source_passage_claim',text='The journal describes a wooden walkway.',passage_handles=[handle])]
    payload=dict(schema='dmb_rules_mixed_answer_v1',base_output=base,
        rules_segments=[dict(kind='rules_claim',text=capsule.excerpt_text,support_ids=[str(capsule.support_id)])],
        ordered_refs=[dict(domain='base',segment_index=None),dict(domain='rules',segment_index=0)])
    wire=WriterWire(a,json.dumps(payload))
    completed=asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    assert completed.envelope.status=='completed' and len(wire.calls)==1
    stored=AgentConversationService().inspect_turn(world_id=a.world_id,turn_id=a.turn.turn_id)
    assert isinstance(stored.base_projection.turn.completion,t.SurfaceEvidenceCompletionV1)
    assert stored.base_projection.turn.completion.answer_segments[0].text==quoted
    pairs=AgentConversationService().list_completed_plan_ask_context(a.world_id,stored.base_projection.turn.graph_context_receipt.plan_basis)
    assert pairs[-1].history_attribution.base_attribution.answer_segments[0].text==quoted
    assert stored.accepted_binding.graph_used==with_graph
    if with_graph:
        from types import SimpleNamespace
        from apps.live_control_server.services.agent_source_passages import open_source_passage
        from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
        turn=stored.base_projection.turn
        citation=turn.completion.source_citations[1];r=citation.receipt
        authority=turn.graph_context_receipt.graph_authority
        body=writer.projection.frame['opened_passages'][0]['text']
        snapshot=SimpleNamespace(world_id=authority.native_world_id,revision_id=authority.graph_revision,
            scope_mode='world',campaign_id='',admissibility='gm',focus=SimpleNamespace(kind='none',session_id=None,campaign_id=None))
        result=SimpleNamespace(snapshot=snapshot,anchor_id=r.anchor_id,evidence_ref_id=r.evidence_ref_id,
            source_artifact_id=r.source_artifact_id,outcome='enough',truncated=False,content=body,
            content_sha256='f'*64,line_start=r.line_start,line_end=r.line_end)
        opened=SimpleNamespace(result=result,graph_revision=authority.graph_revision,source_revision_id=r.source_revision_id,
            source_artifact_id=r.source_artifact_id,evidence_ref_id=r.evidence_ref_id,source_revision_sha256='f'*64)
        calls=[]
        monkeypatch.setattr(direct,'direct_services_from_config',lambda *_:object())
        def read(_services,request,**_kwargs): calls.append(request);return opened
        monkeypatch.setattr(direct,'read_source_anchor_direct_v2',read)
        response=open_source_passage(world_id=a.world_id,turn_id=a.turn.turn_id,citation_index=1)
        assert response.citation==citation and response.content==body and response.target.citation_index==1
        assert len(calls)==1 and calls[0].revision_pin==authority.graph_revision


def test_two_windows_sharing_graph_evidence_only_bind_the_selected_passage(plan_adapter):
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from graph_memory.interaction.session import GraphReferent
    from tests.test_plan_jev_driver import Decisions,fixture_reads
    a=plan_adapter;a.bootstrap.retrieval_session.referents=[GraphReferent(id='pond',label='Park pond')]
    fixture_reads(a,anchors=2,shared_ref=True)
    rules=PlanRulesRuntime(a,rules_capability(graph=True))
    proof=asyncio.run(PlanJevDriver(a).run(transport=Decisions(),api_key='synthetic-not-secret'))
    writer=PlanJevWriter(a,proof,rules)
    passages=writer.projection.frame['opened_passages']
    assert len(passages)==2 and passages[0]['evidence']==passages[1]['evidence']
    payload=wire_answer([dict(kind='graph_claim',claim_id='claim:1',text='The pond has a wooden walkway.',
        target_kind='assertion',target_id='assertion:pond',passage_handles=[passages[1]['passage_handle']])])
    completed=asyncio.run(writer.run(transport=WriterWire(a,json.dumps(payload)),api_key='synthetic-not-secret'))
    assert len(completed.completion.source_citations)==1
    selected=completed.completion.source_citations[0].receipt
    assert selected.anchor_id=='anchor:park:1'
    assert completed.completion.citation_map.entries[0].source_read_ids==[selected.source_read_id]


@pytest.mark.parametrize('change',['model_text','unknown','duplicate','legacy_wire'])
def test_current_authored_selector_rejects_generated_or_unexposed_material(plan_adapter,change):
    writer=stage(plan_adapter)
    block=writer.projection.frame['committed_plan_blocks'][0]
    segment=dict(kind='authored_excerpt',block_handle=block['block_handle'])
    if change=='model_text':segment['text']=block['text']
    if change=='unknown':segment['block_handle']='b'+'e'*64
    payload=wire_answer([segment,segment] if change=='duplicate' else [segment])
    if change=='legacy_wire':payload['schema']='dmb_surface_evidence_answer_v1'
    wire=WriterWire(plan_adapter,json.dumps(payload))
    with pytest.raises(Exception):asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    stored=plan_adapter.service.inspect_turn(world_id=plan_adapter.world_id,turn_id=plan_adapter.turn.turn_id)
    assert stored.completion is None and len(wire.calls)==1


@pytest.mark.parametrize('explicit_flag', [False, True])
def test_current_typed_gaps_derive_limitation_and_reopen(plan_adapter, explicit_flag):
    writer = stage(plan_adapter)
    phrase = plan_adapter.fence.turn.user_text
    payload = wire_answer([dict(kind='source_passage_claim', text='The journal describes a walkway.',
        passage_handles=[writer.projection.frame['opened_passages'][0]['passage_handle']])])
    payload['requested_detail_gaps'] = [{'question_phrase': phrase}]
    payload['limitations'] = ['missing_requested_details'] if explicit_flag else []
    wire = WriterWire(plan_adapter, json.dumps(payload))
    completed = asyncio.run(writer.run(transport=wire, api_key='synthetic-not-secret'))
    assert completed.status == 'completed' and len(wire.calls) == 1
    gaps = [s for s in completed.completion.answer_segments
            if getattr(s, 'code', None) == 'missing_requested_details']
    assert len(gaps) == 2  # closed summary plus exact requested-detail selection
    assert len(completed.completion.source_citations) == 1
    reopened = AgentConversationService().inspect_turn(world_id=completed.world_id, turn_id=completed.turn_id)
    assert reopened.completion == completed.completion


@pytest.mark.parametrize('bad', ['string', 'foreign', 'repeat', 'overlap', 'unknown_flag', 'duplicate_flag'])
def test_gap_derivation_does_not_relax_validation(plan_adapter, bad):
    writer = stage(plan_adapter)
    phrase = plan_adapter.fence.turn.user_text
    payload = wire_answer([])
    payload['requested_detail_gaps'] = [{'question_phrase': phrase}]
    if bad == 'string': payload['requested_detail_gaps'] = [phrase]
    if bad == 'foreign': payload['requested_detail_gaps'] = [{'question_phrase': 'Not present in the question.'}]
    if bad == 'repeat': payload['requested_detail_gaps'] *= 2
    if bad == 'overlap': payload['requested_detail_gaps'].append({'question_phrase': phrase.split()[0]})
    if bad == 'unknown_flag': payload['limitations'] = ['unrecognized']
    if bad == 'duplicate_flag': payload['limitations'] = ['partial_retrieval', 'partial_retrieval']
    wire = WriterWire(plan_adapter, json.dumps(payload))
    with pytest.raises(Exception):
        asyncio.run(writer.run(transport=wire, api_key='synthetic-not-secret'))
    assert len(wire.calls) == 1
    assert plan_adapter.service.inspect_turn(world_id=plan_adapter.world_id,
        turn_id=plan_adapter.turn.turn_id).completion is None
