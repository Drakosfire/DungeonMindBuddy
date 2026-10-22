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
    quote = frame['committed_plan_markdown'].splitlines()[1]
    payload = wire_answer([
        dict(kind='source_passage_claim', text='The journal describes a wooden walkway.',
            passage_handles=[frame['opened_passages'][0]['passage_handle']]),
        dict(kind='authored_quote', text=quote, source_handle=frame['authored_sources'][0]['handle']),
        dict(kind='proposal', text='We could begin beside the pond.', label='invented_idea')])
    wire = WriterWire(plan_adapter, json.dumps(payload))
    completed = asyncio.run(writer.run(transport=wire, api_key='synthetic-not-secret'))
    assert completed.status == 'completed' and len(wire.calls) == 1
    assert isinstance(completed.completion, t.SurfaceEvidenceCompletionV1)
    assert len(completed.completion.source_citations) == 1
    assert completed.completion.answer_segments[1].text == quote
    assert frame['authored_sources'][0]['body_path'] == ['committed_plan_markdown']
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
    migration=import_module('application_state.migrations.versions.20261022_0046_surface_evidence_answers')
    engine=create_engine(application_state_dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError,match='retained mixed evidence'):
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


def test_current_mixed_contract_includes_rules_without_another_writer(plan_adapter):
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
    rules=PlanRulesRuntime(a,rules_capability(graph=True))
    proof=asyncio.run(PlanJevDriver(a,rules=rules).run(transport=Decisions(),api_key='synthetic-not-secret'))
    writer=PlanJevWriter(a,proof,rules)
    capsule=rules.frame().supports[0]
    quoted=writer.projection.frame['committed_plan_markdown'].splitlines()[0]
    base=wire_answer([dict(kind='authored_quote',text=quoted,source_handle=writer.projection.frame['authored_sources'][0]['handle'])])
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
