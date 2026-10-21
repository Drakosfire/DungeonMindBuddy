"""Real native persistence gates. No SDK/provider or live database is a fixture."""
from datetime import UTC,datetime
from hashlib import sha256
from importlib import import_module
import json
from uuid import uuid4

from alembic import command
import psycopg
from psycopg.types.json import Jsonb
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.play_graph_authority import play_source_frame,play_graph_execution_policy_digest
from application_state.agent_conversation.play_graph_context import prepare_play_source_provider_inclusion
from application_state.cli import alembic_config,_current_and_head,upgrade_to_head
from application_state.errors import ApplicationStateConflictError,ApplicationStateValidationError,ApplicationStateNotFoundError
from application_state.play.service import create_world_play_run,replace_world_play_run_progress
from application_state.play.edition_service import read_content,commit_content,read_context_snapshot
from application_state.play.edition_types import ContentCommit
from tests.application_state.test_agent_conversation_postgres import _new
from tests.application_state.test_play_runtime_world_runs_postgres import _create_world_plan
from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN
from tests.test_play_graph_context import fixture as pure_fixture,seal_receipt
from tests.test_play_graph_records import provenance
from tests.test_play_graph_authority import intent_wire,native_provider


HEAD='20261020_0042'


def make_submission(*,edition=False):
    service=AgentConversationService();world='native-pg-'+uuid4().hex
    conversation=_new(service,world)
    obj,revision=_create_world_plan(world,markdown=V2_SOURCE_MARKDOWN)
    created=create_world_play_run(world_id=world,run_id=str(uuid4()),playable_artifact_id=obj.work_object_id,
        expected_playable_revision=revision.revision_n,expected_playable_content_sha256=revision.content_sha256)
    note='Saved native note 🦉.'
    replace_world_play_run_progress(world_id=world,run_id=created.run.run_id,expected_run_revision=created.run.run_revision,
        progress=dict(current_beat_id='beat:arrival',current_scene_id='scene:gate',resolved_beat_ids=[],selections={},notes_by_element_id={'scene:gate':note}))
    if edition:
        origin=read_content(run_id=str(created.run.run_id),world_id=world)
        commit_content(run_id=str(created.run.run_id),world_id=world,command_id=str(uuid4()),request=ContentCommit(
            schema_version='dmb_world_play_run_content_commit_v1',expected_origin=origin.origin,
            expected_edition_revision=origin.edition_revision,expected_content_sha256=origin.content_sha256,
            markdown=origin.markdown+'\nSaved session copy.\n'))
    run,content=read_context_snapshot(run_id=str(created.run.run_id),world_id=world)
    basis=t.PlayRunTurnContextReceiptV2(world_id=world,run_id=str(run.run_id),run_revision=run.run_revision,
        runbook_object_id=str(run.playable_work_object_id),runbook_object_revision=obj.object_revision,
        runbook_work_revision_id=run.playable_work_revision_id,runbook_revision_n=run.playable_revision_n,
        runbook_content_sha256=run.playable_content_sha256,beat_id='beat:arrival',scene_id='scene:gate',
        edition_revision=content.edition_revision,edition_revision_id=content.edition_revision_id,content_sha256=content.content_sha256,
        scene_note=note,scene_note_sha256=sha256(note.encode()).hexdigest())
    frame=play_source_frame((t.PlaySourcePayloadV1(source_kind='scene_note',locator=t.play_source_locator(basis),text=note),))
    r,e,_=pure_fixture();wire=r.model_dump(mode='json',by_alias=True)
    wire.update(play_basis=basis.model_dump(mode='json',by_alias=True),play_sources=frame.manifest.model_dump(mode='json',by_alias=True),play_source_frame_sha256=t.canonical_sha256(frame))
    wire['graph_authority'].update(managed_world_id=world,native_world_id='native-'+world)
    wire['assembled_input']['assembled_input_sha256']=sha256(json.dumps({'fixture':'native-pg','run':str(run.run_id)},sort_keys=True).encode()).hexdigest()
    r=seal_receipt(wire)
    policy=e.policy.model_dump(mode='json',by_alias=True);policy['source_read_scope']['world_id']=world
    policy=t.NativePlayGraphPolicyV1.model_validate_json(json.dumps(policy))
    e=t.PlayWorldGraphExecutionV1(context_receipt_sha256=r.context_receipt_sha256,execution_policy_sha256=play_graph_execution_policy_digest(r.context_receipt_sha256,policy),policy=policy,events=[])
    intent=intent_wire();intent['world_id']=world;intent['graph_request']['world_id']=world
    intent['primary_work'].update(object_id=str(run.run_id),expected_revision=run.run_revision,play_content_basis=t.PlayContentBasis(
        edition_revision=basis.edition_revision,edition_revision_id=basis.edition_revision_id,content_sha256=basis.content_sha256).model_dump(mode='json'))
    intent['play_target'].update(beat_id=basis.beat_id,scene_id=basis.scene_id)
    intent=t.PlayGraphIntentV1.model_validate_json(json.dumps(intent))
    p=provenance(r)
    sub=t.TurnSubmission(world_id=world,conversation_id=conversation.conversation_id,idempotency_key=uuid4(),expected_conversation_revision=1,
        user_text=intent.message,provenance=p,submitted_intent_v2=intent,graph_context_receipt=r,graph_context_execution=e,play_context_receipt=basis)
    return service,sub,frame


@pytest.mark.parametrize('edition',[False,True])
def test_native_accept_reopen_reconcile_and_idempotence(application_state_dsn,monkeypatch,edition):
    service,sub,frame=make_submission(edition=edition)
    accepted=service.accept_turn(sub)
    assert isinstance(accepted.graph_context_execution,t.PlayWorldGraphExecutionV1)
    assert accepted.play_context_receipt==sub.play_context_receipt
    reopened=AgentConversationService().list_turns(sub.world_id,sub.conversation_id)[0]
    assert reopened.model_dump(mode='json',by_alias=True)==accepted.model_dump(mode='json',by_alias=True)
    from application_state.agent_conversation import play_graph_persistence
    monkeypatch.setattr(play_graph_persistence,'lock_and_validate_native_play_basis',lambda *args:pytest.fail('Replay reread mutable Run'))
    assert service.accept_turn(sub).turn_id==accepted.turn_id
    routed=sub.submitted_intent_v2.model_copy(update={'client_thread_id':'new-routing-thread'})
    assert AgentConversationService().reconcile_turn(sub.world_id,sub.idempotency_key,routed).turn_id==accepted.turn_id
    with pytest.raises(ApplicationStateConflictError):service.reconcile_turn(sub.world_id,sub.idempotency_key,routed.model_copy(update={'message':'Different question'}))


@pytest.mark.parametrize('change',['revision','note','edition','target','origin','world','trash'])
def test_fresh_native_acceptance_rechecks_source_before_conversation_changes(application_state_dsn,change):
    service,sub,frame=make_submission()
    with psycopg.connect(application_state_dsn) as conn:
        before=conn.execute('SELECT revision,next_turn_sequence FROM agent.conversation WHERE conversation_id=%s',(sub.conversation_id,)).fetchone()
        if change=='revision':conn.execute('UPDATE play.run SET run_revision=run_revision+1 WHERE run_id=%s',(sub.play_context_receipt.run_id,))
        if change=='note':conn.execute("UPDATE play.run SET progress=jsonb_set(progress,'{notes_by_element_id,scene:gate}',%s) WHERE run_id=%s",(Jsonb('Changed note'),sub.play_context_receipt.run_id))
        if change=='origin':conn.execute("UPDATE play.run SET playable_content_sha256=%s WHERE run_id=%s",('f'*64,sub.play_context_receipt.run_id))
        if change=='world':conn.execute("UPDATE play.run SET world_id='foreign-world' WHERE run_id=%s",(sub.play_context_receipt.run_id,))
        if change=='trash':conn.execute("UPDATE play.run SET lifecycle_status='trashed' WHERE run_id=%s",(sub.play_context_receipt.run_id,))
        if change=='target':conn.execute("UPDATE play.run_manifest SET manifest=jsonb_set(manifest,'{scenes}','[]') WHERE run_id=%s",(sub.play_context_receipt.run_id,))
    if change=='edition':
        current=read_content(run_id=sub.play_context_receipt.run_id,world_id=sub.world_id)
        commit_content(run_id=sub.play_context_receipt.run_id,world_id=sub.world_id,command_id=str(uuid4()),request=ContentCommit(
            schema_version='dmb_world_play_run_content_commit_v1',expected_origin=current.origin,expected_edition_revision=0,
            expected_content_sha256=current.content_sha256,markdown=current.markdown+'\nNew saved copy.\n'))
    with pytest.raises((ApplicationStateConflictError,ApplicationStateNotFoundError)):
        service.accept_turn(sub)
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute('SELECT revision,next_turn_sequence FROM agent.conversation WHERE conversation_id=%s',(sub.conversation_id,)).fetchone()==before
        assert conn.execute('SELECT count(*) FROM agent.turn WHERE idempotency_key=%s',(sub.idempotency_key,)).fetchone()==(0,)


def test_native_reconciliation_survives_changed_and_trashed_run(application_state_dsn):
    service,sub,frame=make_submission();accepted=service.accept_turn(sub)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE play.run SET run_revision=run_revision+1,lifecycle_status='trashed' WHERE run_id=%s",(sub.play_context_receipt.run_id,))
    assert service.reconcile_turn(sub.world_id,sub.idempotency_key,sub.submitted_intent_v2).turn_id==accepted.turn_id
    assert service.accept_turn(sub).turn_id==accepted.turn_id


def test_native_graph_operation_replay_is_exact_and_claim_fenced(application_state_dsn):
    service,sub,frame=make_submission();turn=service.accept_turn(sub)
    turn=service.claim_turn(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision).turn
    event=t.ValidatedGraphOperationEventV3(kind='validated_graph_operation_v3',event_id=uuid4(),sequence=0,operation_id=uuid4(),
        operation='expand_graph_retrieval',request_arguments_sha256='a'*64,graph_revision='graph-one',result_packet_sha256='b'*64,
        assertion_ids=['assertion-one'],relationship_ids=[],evidence_ref_ids=['e0'],evidence_sufficiency_status='sufficient',coverage_status='complete',truncated=False,source_opened=False,returned_source_pins=[])
    turn,fresh=service.append_validated_graph_operation(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision,expected_attempt=turn.attempt,operation_event=event)
    assert fresh
    again,fresh=service.append_validated_graph_operation(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision,expected_attempt=turn.attempt,operation_event=event)
    assert not fresh and again.revision==turn.revision
    with pytest.raises(ApplicationStateConflictError):service.append_validated_graph_operation(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision,expected_attempt=turn.attempt,operation_event=event.model_copy(update={'result_packet_sha256':'c'*64}))
    with pytest.raises(ApplicationStateConflictError):service.append_validated_graph_operation(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision-1,expected_attempt=turn.attempt,operation_event=event)
    included=prepare_play_source_provider_inclusion(sub.graph_context_receipt,turn.graph_context_execution,frame,event_id=uuid4(),provider_attempt_id=uuid4(),envelope_sha256='c'*64,owner_resolved_current_moment_text=None)
    with pytest.raises(ApplicationStateValidationError,match='actual prepared-input proof'):
        service._append_graph_execution_event(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision,expected_attempt=turn.attempt,event=included,duplicate_key='event_id')


def test_native_provider_authorization_is_one_shot_and_expiry_does_not_repost(application_state_dsn):
    service,sub,frame=make_submission();turn=service.accept_turn(sub)
    turn=service.claim_turn(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision).turn
    auth=native_provider().model_copy(update={'envelope_sha256':sub.graph_context_receipt.assembled_input.assembled_input_sha256})
    turn,fresh=service.authorize_provider_attempt_v2(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision,expected_attempt=turn.attempt,provider_attempt_event=auth)
    assert fresh
    same,fresh=service.authorize_provider_attempt_v2(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision,expected_attempt=turn.attempt,provider_attempt_event=auth)
    assert not fresh and same.revision==turn.revision
    with psycopg.connect(application_state_dsn) as conn:conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",(turn.turn_id,))
    with pytest.raises(ApplicationStateConflictError):service.claim_turn(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision)
    after=service.reconcile_turn(sub.world_id,sub.idempotency_key,sub.submitted_intent_v2)
    assert after.status=='interrupted' and after.graph_context_execution.events[-1].outcome=='outcome_unknown'


@pytest.mark.parametrize('change',['receipt_schema','extra_receipt','world','frame_missing','basis','execution_schema','policy','uncapped','unknown_event','scope_world','completion_without_shape','completed_without_completion'])
def test_native_sql_rejects_wrong_shape_and_cross_domain_fallback(application_state_dsn,change):
    service,sub,frame=make_submission();turn=service.accept_turn(sub)
    r=turn.graph_context_receipt.model_dump(mode='json',by_alias=True);e=turn.graph_context_execution.model_dump(mode='json',by_alias=True)
    extra=''
    if change=='receipt_schema':r['schema']='dmb_agent_plan_world_graph_context_receipt_v1'
    if change=='extra_receipt':r['legacy_alias']={}
    if change=='world':r['graph_authority']['managed_world_id']='foreign'
    if change=='frame_missing':r.pop('play_source_frame_sha256')
    if change=='basis':r['play_basis']['run_id']=str(uuid4())
    if change=='execution_schema':e['schema']='dmb_agent_plan_world_graph_execution_v3'
    if change=='policy':e['policy']['policy_version']='world_graph_execution_uncapped_v1'
    if change=='uncapped':e['policy']['max_provider_attempts']=None
    if change=='unknown_event':e['events']=[{'kind':'legacy_anything','event_id':str(uuid4()),'sequence':0}]
    if change=='scope_world':e['policy']['source_read_scope']['world_id']='foreign'
    if change=='completion_without_shape':extra=",status='completed',assistant_text='Unsupported',completion='{}'::jsonb"
    if change=='completed_without_completion':extra=",status='completed',assistant_text='Unsupported'"
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute('UPDATE agent.turn SET graph_context_receipt=%s,graph_context_execution=%s'+extra+' WHERE turn_id=%s',(Jsonb(r),Jsonb(e),turn.turn_id))


@pytest.mark.parametrize('state',['accepted','running','failed','interrupted','completed'])
def test_downgrade_refuses_any_retained_native_state(application_state_dsn,state):
    service,sub,frame=make_submission();turn=service.accept_turn(sub)
    if state!='accepted':
        turn=service.claim_turn(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision).turn
        if state in {'failed','interrupted'}:
            turn=service.fail_turn(t.TurnFailure(world_id=sub.world_id,conversation_id=sub.conversation_id,turn_id=turn.turn_id,
                expected_revision=turn.revision,failure_code='native-fixture'),interrupted=state=='interrupted')
    if state=='completed':
        # SQL-shape fixture only: deliberately does not claim an actual SDK reply
        # or bypass the APP service's mandatory raw-output proof gate.
        from tests.test_play_graph_completion import acknowledge, complete
        from tests.test_play_graph_authority import native_events
        auth=native_provider(0).model_copy(update={'envelope_sha256':sub.graph_context_receipt.assembled_input.assembled_input_sha256})
        execution=native_events(turn.graph_context_execution,[auth])
        execution=acknowledge(execution,auth)
        completion=complete(sub.graph_context_receipt,[t.PlanWorldGraphConnectiveSegmentV1(kind='connective',text='Which scene next?')])
        binding=t.CompletionBindingEventV1(kind='completion_binding',event_id=uuid4(),sequence=len(execution.events),
            provider_attempt_id=auth.provider_attempt_id,completion_sha256=t.canonical_sha256(completion),claim_graph_event_ids={})
        execution=native_events(execution,[*execution.events,binding])
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute("UPDATE agent.turn SET status='completed',assistant_text='Which scene next?',completed_at=clock_timestamp(),claim_expires_at=NULL,completion=%s,graph_context_execution=%s WHERE turn_id=%s",
                (Jsonb(completion.model_dump(mode='json',by_alias=True)),Jsonb(execution.model_dump(mode='json',by_alias=True)),turn.turn_id))
    with pytest.raises(RuntimeError,match='retained native Play'):
        command.downgrade(alembic_config(),'20261020_0041')
    assert _current_and_head(application_state_dsn)==(HEAD,HEAD)
    assert service.reconcile_turn(sub.world_id,sub.idempotency_key,sub.submitted_intent_v2).turn_id==turn.turn_id


def test_no_native_migration_roundtrip_preserves_exact_rows_and_old_constraints(application_state_dsn):
    from tests.application_state.test_rules_authority_migration import turn_fixture
    turn=turn_fixture()
    def snapshot():
        with psycopg.connect(application_state_dsn) as conn:
            row=conn.execute("SELECT (to_jsonb(t)-'submitted_intent_schema')::text FROM agent.turn t WHERE turn_id=%s",(turn.turn_id,)).fetchone()[0]
            constraints=dict(conn.execute("SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='agent.turn'::regclass AND conname IN ('agent_turn_graph_context_receipt_check','agent_turn_graph_context_execution_check','agent_turn_graph_completion_check')").fetchall())
            return row,constraints
    command.downgrade(alembic_config(),'20261020_0041');row,old=snapshot()
    upgrade_to_head(dsn=application_state_dsn);assert snapshot()[0]==row
    command.downgrade(alembic_config(),'20261020_0041');assert snapshot()==(row,old)
    upgrade_to_head(dsn=application_state_dsn);assert snapshot()[0]==row


def test_native_admission_does_not_materialize_other_scene_notes(application_state_dsn):
    service,sub,_=make_submission()
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE play.run SET progress=jsonb_set(progress,'{notes_by_element_id,scene:unselected}',%s) WHERE run_id=%s",
            (Jsonb('Unrelated note. '*150000),sub.play_context_receipt.run_id))
    # Current source admission transfers just the selected bounded note, rather
    # than the session's entire notes collection or full Run progress.
    accepted=service.accept_turn(sub)
    assert accepted.play_context_receipt.scene_note==sub.play_context_receipt.scene_note


@pytest.mark.parametrize('field',['object','revision','sha'])
def test_native_admission_binds_revision_to_its_exact_source_object(application_state_dsn,field):
    service,sub,_=make_submission()
    from application_state.content.service import create_world_plan
    other=create_world_plan(title='Other source owner',world_id=sub.world_id)
    # Deliberately inconsistent immutable metadata in this disposable database:
    # the Run and receipt still agree, and both source records own this World.
    # Admission must additionally join the actual revision's object/number/hash.
    with psycopg.connect(application_state_dsn) as conn:
        if field=='object':
            conn.execute('UPDATE content.work_revision SET work_object_id=%s WHERE work_revision_id=%s',
                (other.work_object_id,sub.play_context_receipt.runbook_work_revision_id))
        if field=='revision':
            conn.execute('UPDATE content.work_revision SET revision_n=revision_n+1 WHERE work_revision_id=%s',
                (sub.play_context_receipt.runbook_work_revision_id,))
        if field=='sha':
            conn.execute('UPDATE content.work_revision SET content_sha256=%s WHERE work_revision_id=%s',
                ('f'*64,sub.play_context_receipt.runbook_work_revision_id))
        before=conn.execute('SELECT revision,next_turn_sequence FROM agent.conversation WHERE conversation_id=%s',
            (sub.conversation_id,)).fetchone()
    with pytest.raises(ApplicationStateConflictError,match='revision/origin changed'):
        service.accept_turn(sub)
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute('SELECT revision,next_turn_sequence FROM agent.conversation WHERE conversation_id=%s',
            (sub.conversation_id,)).fetchone()==before
        assert conn.execute('SELECT count(*) FROM agent.turn WHERE conversation_id=%s',(sub.conversation_id,)).fetchone()==(0,)


@pytest.mark.parametrize('state', ['accepted', 'running', 'failed', 'interrupted'])
def test_downgrade_refuses_genuine_graph_off_play_intent(application_state_dsn, state):
    service, native, _ = make_submission()
    wire = native.submitted_intent_v2.model_dump(mode='json', by_alias=True)
    wire.pop('play_graph_policy')
    wire.update(schema='dmb_play_rules_intent_v1', graph_request={'mode':'none'})
    intent = t.PlayRulesIntentV1.model_validate_json(json.dumps(wire))
    p = native.provenance.model_copy(update={'supporting_work': [ref for ref in native.provenance.supporting_work
        if ref.kind not in {'world_graph_revision', 'dmb_play_graph_binding_v1'}]})
    sub = t.TurnSubmission(world_id=native.world_id, conversation_id=native.conversation_id,
        idempotency_key=native.idempotency_key, expected_conversation_revision=1, user_text=intent.message,
        provenance=p, submitted_intent_v1=intent, play_context_receipt=native.play_context_receipt)
    turn = service.accept_turn(sub)
    if state != 'accepted':
        turn = service.claim_turn(sub.world_id, sub.conversation_id, turn.turn_id, expected_revision=turn.revision).turn
        if state in {'failed', 'interrupted'}:
            turn = service.fail_turn(t.TurnFailure(world_id=sub.world_id, conversation_id=sub.conversation_id,
                turn_id=turn.turn_id, expected_revision=turn.revision, failure_code='rules-only-fixture'),
                interrupted=state == 'interrupted')
    with pytest.raises(RuntimeError, match='retained native Play'):
        command.downgrade(alembic_config(), '20261020_0041')
    assert _current_and_head(application_state_dsn) == (HEAD, HEAD)
    reopened = service.reconcile_turn(sub.world_id, sub.idempotency_key, intent)
    assert reopened.turn_id == turn.turn_id and reopened.status == state
    assert reopened.graph_context_receipt is None and reopened.graph_context_execution is None


@pytest.mark.parametrize('mode', ['supported', 'unused'])
def test_downgrade_refuses_completed_graph_off_play(application_state_dsn, tmp_path, monkeypatch, mode):
    from tests.test_rules_only_parent import case, RulesOnlyProvider
    request, service, execute, retained, read_retained = case(tmp_path, monkeypatch, 'play')
    response = execute(RulesOnlyProvider(mode))
    assert response.answer.status == 'ok'
    pointer = service.get_world_pointer(request.owner_scope.world_id)
    before = service.list_turns(request.owner_scope.world_id, pointer.active_conversation_id)[-1]
    assert (before.envelope.status if hasattr(before, 'envelope') else before.status) == 'completed'
    with pytest.raises(RuntimeError, match='retained native Play'):
        command.downgrade(alembic_config(), '20261020_0041')
    assert _current_and_head(application_state_dsn) == (HEAD, HEAD)
    after = service.list_turns(request.owner_scope.world_id, pointer.active_conversation_id)[-1]
    assert after == before and read_retained() == retained


def test_predecessor_play_receipt_survives_0042_roundtrip(application_state_dsn):
    service, native, _ = make_submission()
    wire = native.submitted_intent_v2.model_dump(mode='json', by_alias=True)
    wire.pop('play_graph_policy')
    wire.pop('play_target')
    wire.update(schema='dmb_agent_submitted_turn_intent_v1', graph_request={'mode':'none'})
    intent = t.SubmittedTurnIntentV1.model_validate_json(json.dumps(wire))
    p = native.provenance.model_copy(update={'supporting_work':[ref for ref in native.provenance.supporting_work
        if ref.kind not in {'world_graph_revision','dmb_play_graph_binding_v1'}]})
    sub = t.TurnSubmission(world_id=native.world_id, conversation_id=native.conversation_id,
        idempotency_key=native.idempotency_key, expected_conversation_revision=1, user_text=intent.message,
        provenance=p, submitted_intent_v1=intent, play_context_receipt=native.play_context_receipt)
    before = service.accept_turn(sub)
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute('SELECT submitted_intent_schema FROM agent.turn WHERE turn_id=%s',
            (before.turn_id,)).fetchone() == (None,)
    command.downgrade(alembic_config(), '20261020_0041')
    upgrade_to_head(dsn=application_state_dsn)
    after = service.reconcile_turn(sub.world_id, sub.idempotency_key, intent)
    assert after == before
