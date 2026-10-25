"""Reviewed author action through the actual host/SDK with disposable APP state."""
from uuid import uuid4
import pytest
from application_state.agent_conversation import AgentConversationService, work_plan as w
from application_state.agent_conversation.types import TurnSubmission, TurnResult, BuildAuthoringCompletionV1
from application_state.agent_conversation.build_draft_context import BuildDraftSnapshotV1, BuildDraftContextRequestV1
from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.application_state.test_reviewed_work_plan import provenance
from tests.application_state.test_agent_conversation_service import _submitted_intent
from tests.test_agent_build_jev_ordinary_harness import build_case as _build_case, ordinary_case, DecisionWire, WriterWire
from tests.test_agent_build_governed_graph import execute
from tests.test_build_jev_estimated_continuations import counter


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def reviewed_case(build_case, monkeypatch, kind="prepare_insertion"):
    (source, request, bootstrap), _ = ordinary_case(build_case, monkeypatch, authoring=True)
    if kind == "discuss":
        from tests.test_build_world_context import world_case
        (source,request,bootstrap), _ = world_case((source,request,bootstrap),monkeypatch)
    service = AgentConversationService()
    cid = request.build_write_capability.conversation_id
    plan_turn = service.accept_turn(TurnSubmission(world_id='elderwyld', conversation_id=cid,
        idempotency_key=uuid4(), expected_conversation_revision=service.get_conversation('elderwyld',cid).revision,
        user_text='Plan a proposed addition.', provenance=provenance('elderwyld',source.record.document_id),
        submitted_intent_v1=_submitted_intent('elderwyld','Plan a proposed addition.',surface_id='build')))
    running=service.begin_turn('elderwyld',cid,plan_turn.turn_id,expected_revision=plan_turn.revision)
    plan_turn=service.complete_turn(TurnResult(world_id='elderwyld',conversation_id=cid,turn_id=running.turn_id,expected_revision=running.revision,assistant_text='Prepare a proposed NPC table.'))
    step = w.Step(step_id=uuid4(),text='Prepare a proposed NPC table.',selected=True,kind=kind)
    plan = w.save('elderwyld',cid,plan_turn.turn_id,w.Review(expected_revision=0,steps=[step]))
    continued = w.continue_step('elderwyld',cid,plan_turn.turn_id,w.Continue(expected_revision=plan['revision'],step_id=step.step_id,command_id=uuid4()))
    d=continued['dispatch']
    cap=request.build_write_capability
    cap=cap.model_copy(update={'basis':cap.basis.model_copy(update={'editor_sha256':'b'*64})})
    snap=BuildDraftSnapshotV1(**{k:getattr(cap.basis,k) for k in ('world_id','document_id','registry_revision','content_sha256','visibility','draft_sha256','editor_sha256','draft_generation')},draft_markdown=cap.draft_markdown)
    draft=BuildDraftContextRequestV1(snapshot=snap,conversation_id=cid,expected_pointer_revision=cap.expected_pointer_revision)
    request=AgentTurnRequest.model_validate({**request.model_dump(mode='json',by_alias=True),
        'client_thread_id':d['client_thread_id'],'turn_id':d['client_turn_id'],'message':d['message'],
        'reviewed_step':continued['reviewed_step'],'build_write_capability':cap.model_dump(mode='json'),
        'build_draft_context':draft.model_dump(mode='json',by_alias=True)})
    from dataclasses import replace
    bootstrap=replace(bootstrap,navigation_candidates=(("frank","Frank"),),completed_discovery_query=request.message)
    return source,request,bootstrap


@pytest.mark.parametrize("with_empty_catalog",[False,True])
def test_reviewed_insertion_does_not_ask_the_model_to_choose_its_operation(build_case,monkeypatch,tmp_path,with_empty_catalog):
    import json
    case=reviewed_case(build_case,monkeypatch)
    # If an operation question leaks through, this deliberately votes discussion.
    decisions=DecisionWire(operation='answer_from_sources')
    if with_empty_catalog:
        from apps.live_control_server.services import build_related_pages
        monkeypatch.setattr(build_related_pages,'discover',lambda _:[])
    harness=BuildJevHarness(world_context=True,named_citations=True,related_pages=with_empty_catalog,accounting=counter(),
        decision_transport=decisions,writer_transport=WriterWire())
    response=execute(case,tmp_path,harness)
    assert isinstance(response.knowledge_context.completion,BuildAuthoringCompletionV1)
    assert all('operation' not in json.loads(call.content)['questions'] for call in decisions.calls)


@pytest.mark.parametrize('mutation',['message','thread','turn','command','page','placement'])
def test_changed_reviewed_request_never_reaches_a_provider(build_case,monkeypatch,tmp_path,mutation):
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    source,request,bootstrap=reviewed_case(build_case,monkeypatch)
    if mutation=='command':
        request=request.model_copy(update={'reviewed_step':request.reviewed_step.model_copy(update={'command_id':uuid4()})})
    elif mutation=='page':
        request=request.model_copy(update={'primary_work':request.primary_work.model_copy(update={'object_id':'another-page'})})
    else:
        field={'message':'message','thread':'client_thread_id','turn':'turn_id','placement':'build_write_capability'}[mutation]
        request=request.model_copy(update={field:None if mutation=='placement' else 'changed' if mutation=='message' else str(uuid4())})
    decisions,writer=DecisionWire(),WriterWire()
    harness=BuildJevHarness(world_context=True,named_citations=True,accounting=counter(),decision_transport=decisions,writer_transport=writer)
    with pytest.raises(AgentTurnServiceError):
        execute((source,request,bootstrap),tmp_path,harness)
    assert not decisions.calls and not writer.calls


def test_bound_insertion_replays_after_archive_without_another_call(build_case,monkeypatch,tmp_path):
    from application_state.agent_conversation.types import ArchiveCommand
    case=reviewed_case(build_case,monkeypatch)
    decisions,writer=DecisionWire(),WriterWire()
    harness=BuildJevHarness(world_context=True,named_citations=True,accounting=counter(),decision_transport=decisions,writer_transport=writer)
    first=execute(case,tmp_path,harness)
    service=AgentConversationService();pointer=service.get_world_pointer('elderwyld')
    service.archive_conversation(ArchiveCommand(world_id='elderwyld',command_id=uuid4(),expected_pointer_revision=pointer.revision,
        expected_active_conversation_id=pointer.active_conversation_id,conversation_id=pointer.active_conversation_id))
    calls=(len(decisions.calls),len(writer.calls))
    replay=execute(case,tmp_path,harness)
    assert replay.knowledge_context.completion == first.knowledge_context.completion
    assert (len(decisions.calls),len(writer.calls)) == calls


def test_bound_action_prevents_downgrade(build_case,monkeypatch,tmp_path,application_state_dsn):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    case=reviewed_case(build_case,monkeypatch)
    harness=BuildJevHarness(world_context=True,named_citations=True,accounting=counter(),decision_transport=DecisionWire(),writer_transport=WriterWire())
    execute(case,tmp_path,harness)
    engine=create_engine(application_state_dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError,match='recovery forward'):
                import_module('application_state.migrations.versions.20261025_0068_reviewed_action_binding').downgrade()
    finally:engine.dispose()


def test_bound_discussion_cannot_become_a_page_proposal(build_case,monkeypatch,tmp_path):
    from tests.test_build_world_context import WorldDecisions
    case=reviewed_case(build_case,monkeypatch,kind='discuss')
    decisions=WorldDecisions();decisions.operation='propose_build_insertion'
    harness=BuildJevHarness(world_context=True,named_citations=True,accounting=counter(),decision_transport=decisions,writer_transport=WriterWire())
    response=execute(case,tmp_path,harness)
    assert not isinstance(response.knowledge_context.completion,BuildAuthoringCompletionV1)
    assert all('operation' not in __import__('json').loads(call.content)['questions'] for call in decisions.calls)


def test_reviewed_insertion_retains_actual_auxiliary_page_decisions(build_case,monkeypatch,tmp_path):
    import json
    from hashlib import sha256
    from application_state.agent_conversation.build_related_pages import PagePointer
    from apps.live_control_server.services import build_related_pages as pages
    from tests.test_build_related_pages import PagesDecision
    case=reviewed_case(build_case,monkeypatch)
    page=PagePointer(world_id='elderwyld',document_id=uuid4(),registry_revision=1,title='Quarry Households',visibility='internal')
    body='# Quarry Households\nCopper House has an unfinished lantern repair.'
    monkeypatch.setattr(pages,'discover',lambda request:[page.model_dump(mode='json')])
    reads=[]
    def materialize(pointer):
        assert pointer==page
        reads.append(pointer.document_id)
        return {**page.model_dump(mode='json'),'content_sha256':sha256(body.encode()).hexdigest(),'markdown':body}
    monkeypatch.setattr(pages,'materialize',materialize)
    decisions,writer=PagesDecision(operation='answer_from_sources'),WriterWire()
    harness=BuildJevHarness(world_context=True,named_citations=True,related_pages=True,accounting=counter(),decision_transport=decisions,writer_transport=writer)
    response=execute(case,tmp_path,harness)
    assert isinstance(response.knowledge_context.completion,BuildAuthoringCompletionV1)
    assert len(decisions.calls)==1
    # Source-owner acquisition and its APP admission revalidation share one read receipt.
    assert reads==[page.document_id,page.document_id]
    assert set(json.loads(decisions.calls[0].content)['questions'])=={'related_page_0'}
    assert json.loads(json.loads(writer.calls[0].content)['input'])['related_authored_pages']['pages'][0]['markdown']==body


def test_retained_bound_turn_rejects_forged_action_or_admission(build_case,monkeypatch,tmp_path):
    from copy import deepcopy
    from pydantic import ValidationError
    from application_state.agent_conversation.types import Turn
    case=reviewed_case(build_case,monkeypatch)
    harness=BuildJevHarness(world_context=True,named_citations=True,accounting=counter(),decision_transport=DecisionWire(),writer_transport=WriterWire())
    execute(case,tmp_path,harness)
    service=AgentConversationService();cid=case[1].reviewed_step.conversation_id
    turn=next(t for t in service.list_turns('elderwyld',cid) if t.user_text==case[1].message)
    original=turn.model_dump(mode='json',by_alias=True)
    for change in ['operation','binding','arguments','admission','capability']:
        payload=deepcopy(original)
        event=next(e for e in payload['graph_context_execution']['events'] if e['kind']=='build_reviewed_action_selected_v1')
        if change=='operation':event['operation']='answer_from_sources'
        elif change=='binding':event['intent']['reviewed_step']['reference']['command_id']=str(uuid4())
        elif change=='arguments':event['arguments_sha256']='f'*64
        elif change=='capability':event['capability_sha256']='f'*64
        else:event['intent']['message']='Another request'
        with pytest.raises(ValidationError):Turn.model_validate(payload)


def test_production_preset_keeps_real_rules_auxiliary_question_without_rerouting(build_case,monkeypatch,tmp_path):
    import json
    from apps.live_control_server.services.build_jev_runtime import PreparedBuildJevRuntime
    from tests.test_rules_build_parent import RulesDecisionWire
    case=reviewed_case(build_case,monkeypatch)
    decisions,writer=RulesDecisionWire(query=False),WriterWire()
    harness=PreparedBuildJevRuntime(accounting=counter(),unavailable_reason=None).create()
    harness.decision_transport,harness.writer_transport=decisions,writer
    response=execute(case,tmp_path,harness)
    assert isinstance(response.knowledge_context.completion,BuildAuthoringCompletionV1)
    assert len(decisions.calls)==1
    assert set(json.loads(decisions.calls[0].content)['questions'])=={'rules_query'}


def test_failed_author_admission_stops_the_claim_renewer(build_case,monkeypatch,tmp_path):
    from application_state.errors import ApplicationStateConflictError
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    case=reviewed_case(build_case,monkeypatch)
    decisions,writer=DecisionWire(),WriterWire()
    harness=BuildJevHarness(world_context=True,named_citations=True,accounting=counter(),decision_transport=decisions,writer_transport=writer)
    def refused(*args,**kwargs):
        raise ApplicationStateConflictError('Synthetic author event append conflict')
    monkeypatch.setattr(AgentConversationService,'record_build_reviewed_action_selection',refused)
    try:
        with pytest.raises(AgentTurnServiceError):execute(case,tmp_path,harness)
        assert not decisions.calls and not writer.calls
        assert not harness.adapter.fence.renewer._thread.is_alive()
    finally:
        # Clean the real renewal thread even when proving the pre-fix regression.
        harness.adapter.fence.renewer.stop_and_join()


def test_app_rejects_reviewed_capability_policy_mismatch_before_admission(build_case, monkeypatch, tmp_path):
    from pydantic import ValidationError
    from application_state.agent_conversation.types import graph_execution_policy_digest_v3
    case = reviewed_case(build_case, monkeypatch)
    original_accept = AgentConversationService.accept_turn
    checked = []

    def check_admission(service, submission):
        payload = submission.model_dump(mode="json", by_alias=True)
        execution = submission.graph_context_execution
        policy = execution.policy.model_copy(update={"action_capability_sha256": "f" * 64})
        assert submission.submitted_intent_v2.build_write_capability_sha256 != policy.action_capability_sha256
        payload["graph_context_execution"]["policy"] = policy.model_dump(mode="json", by_alias=True)
        payload["graph_context_execution"]["execution_policy_sha256"] = graph_execution_policy_digest_v3(
            execution.context_receipt_sha256, policy)
        before = service.list_turns(submission.world_id, submission.conversation_id)
        with pytest.raises(ValidationError, match="Reviewed action capability differs"):
            original_accept(service, TurnSubmission.model_validate(payload))
        assert service.list_turns(submission.world_id, submission.conversation_id) == before
        checked.append(True)
        return original_accept(service, submission)

    monkeypatch.setattr(AgentConversationService, "accept_turn", check_admission)
    harness = BuildJevHarness(world_context=True, named_citations=True, accounting=counter(),
        decision_transport=DecisionWire(), writer_transport=WriterWire())
    execute(case, tmp_path, harness)
    assert checked == [True]
