from uuid import uuid4, uuid5, NAMESPACE_URL
from concurrent.futures import ThreadPoolExecutor
import importlib
import pytest
from application_state.agent_conversation import (
    AgentConversationService,
    work_plan as w,
)
from application_state.agent_conversation.types import (
    TurnSubmission,
    TurnResult,
    TurnProvenance,
    HistoricalReference,
)
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
)
from tests.application_state.test_conversation_library import new
from tests.application_state.test_agent_conversation_service import _submitted_intent


def provenance(world="world-one", document="source-one"):
    return TurnProvenance(
        world_id=world,
        surface_resolution="resolved",
        surface_id="build",
        primary_work=HistoricalReference(
            resolution="resolved",
            kind="build",
            object_id=document,
            revision="2",
            content_sha256="a" * 64,
        ),
        supporting_work=[],
        selected_object=HistoricalReference(resolution="absent"),
    )


def parse_dispatch(value):
    from pydantic import TypeAdapter
    return TypeAdapter(w.DispatchV3 | w.DispatchV2 | w.Dispatch).validate_python(value)


def accept(service, cid, message, key=None, document="source-one"):
    return service.accept_turn(
        TurnSubmission(
            world_id="world-one",
            conversation_id=cid,
            idempotency_key=key or uuid4(),
            expected_conversation_revision=service.get_conversation(
                "world-one", cid
            ).revision,
            user_text=message,
            provenance=provenance(document=document),
            submitted_intent_v1=_submitted_intent(
                "world-one", message, surface_id="build"
            ),
        )
    )


def finish(service, cid, turn, text):
    running = service.begin_turn(
        "world-one", cid, turn.turn_id, expected_revision=turn.revision
    )
    return service.complete_turn(
        TurnResult(
            world_id="world-one",
            conversation_id=cid,
            turn_id=turn.turn_id,
            expected_revision=running.revision,
            assistant_text=text,
        )
    )


@pytest.fixture
def case(application_state_dsn):
    service = AgentConversationService()
    cid = new(service)
    t = accept(service, cid, "Help me plan the shop.")
    t = finish(
        service, cid, t, "1. Discuss the owner.\n2. Prepare the shop description."
    )
    steps = [
        w.Step(step_id=uuid4(), text="Discuss the owner.", selected=True),
        w.Step(
            step_id=uuid4(),
            text="Write the description.",
            selected=False,
            kind="prepare_insertion",
        ),
    ]
    p = w.save("world-one", cid, t.turn_id, w.ReviewV2(objective="Develop a useful shop description for author review.", expected_revision=0, steps=steps))
    return service, cid, t, steps, p


def test_review_cas_retry_and_read_in_archived_conversation(case):
    service, cid, t, steps, p = case
    assert (
        w.save("world-one", cid, t.turn_id, w.ReviewV2(objective="Develop a useful shop description for author review.", expected_revision=0, steps=steps))
        == p
    )
    changed = [steps[0].model_copy(update={"text": "Changed owner question"}), steps[1]]
    updated = w.save(
        "world-one", cid, t.turn_id, w.ReviewV2(objective="Develop a useful shop description for author review.", expected_revision=1, steps=changed)
    )
    assert updated["revision"] == 2
    with pytest.raises(ApplicationStateConflictError):
        w.save("world-one", cid, t.turn_id, w.ReviewV2(objective="Develop a useful shop description for author review.", expected_revision=1, steps=steps))
    new(service)
    assert w.read("world-one", cid, t.turn_id)["plan"] == updated
    with pytest.raises(ApplicationStateConflictError):
        w.save("world-one", cid, t.turn_id, w.ReviewV2(objective="Develop a useful shop description for author review.", expected_revision=2, steps=steps))
    with pytest.raises(ApplicationStateNotFoundError):
        w.read("foreign", cid, t.turn_id)


def test_explicit_continuation_stable_receipt_and_actual_reply(case):
    service, cid, t, steps, p = case
    command = w.Continue(
        expected_revision=1, step_id=steps[0].step_id, command_id=uuid4()
    )
    first = w.continue_step("world-one", cid, t.turn_id, command)
    assert w.continue_step("world-one", cid, t.turn_id, command) == first
    assert first["plan"]["execution"][0]["status"] == "awaiting_dispatch"
    assert (
        w.continue_step(
            "world-one",
            cid,
            t.turn_id,
            command.model_copy(update={"command_id": uuid4(), "expected_revision": 2}),
        )["dispatch"]
        == first["dispatch"]
    )
    d = parse_dispatch(first["dispatch"])
    assert "dispatches" not in d.message
    key = uuid5(NAMESPACE_URL, f"dmb-agent-turn:world-one:{d.client_turn_id}")
    actual = accept(service, cid, d.message, key)
    assert (
        w.read("world-one", cid, t.turn_id)["plan"]["execution"][0]["status"]
        == "accepted"
    )
    done = finish(service, cid, actual, "The owner repairs lantern fittings.")
    result = w.read("world-one", cid, t.turn_id)["plan"]["execution"][0]
    assert (
        result["status"] == "completed"
        and result["turn_id"] == str(done.turn_id)
        and result["result"]["kind"] == "reply"
    )
    with pytest.raises(ApplicationStateConflictError):
        w.continue_step(
            "world-one",
            cid,
            t.turn_id,
            w.Continue(
                expected_revision=2, step_id=steps[0].step_id, command_id=uuid4()
            ),
        )
    with pytest.raises(ApplicationStateConflictError):
        w.save(
            "world-one",
            cid,
            t.turn_id,
            w.ReviewV2(objective="Develop a useful shop description for author review.",
                expected_revision=2,
                steps=[
                    steps[0].model_copy(update={"text": "Rewrite done work"}),
                    steps[1],
                ],
            ),
        )


def test_unselected_and_concurrent_continuations_are_not_authority(case):
    _, cid, t, steps, p = case
    with pytest.raises(ApplicationStateConflictError):
        w.continue_step(
            "world-one",
            cid,
            t.turn_id,
            w.Continue(
                expected_revision=1, step_id=steps[1].step_id, command_id=uuid4()
            ),
        )

    def start(_):
        try:
            return w.continue_step(
                "world-one",
                cid,
                t.turn_id,
                w.Continue(
                    expected_revision=1, step_id=steps[0].step_id, command_id=uuid4()
                ),
            )["dispatch"]["client_turn_id"]
        except ApplicationStateConflictError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(start, range(2)))
    assert len(set(x for x in results if x)) == 1
    assert len(w.read("world-one", cid, t.turn_id)["plan"]["dispatches"]) == 1


@pytest.mark.parametrize("wrong", ["message", "document"])
def test_receipt_key_does_not_bypass_exact_message_and_scope(case, wrong):
    service, cid, t, steps, p = case
    d = parse_dispatch(
        w.continue_step(
            "world-one",
            cid,
            t.turn_id,
            w.Continue(
                expected_revision=1, step_id=steps[0].step_id, command_id=uuid4()
            ),
        )["dispatch"]
    )
    key = uuid5(NAMESPACE_URL, f"dmb-agent-turn:world-one:{d.client_turn_id}")
    accept(
        service,
        cid,
        "Different request" if wrong == "message" else d.message,
        key,
        "other" if wrong == "document" else "source-one",
    )
    assert (
        w.read("world-one", cid, t.turn_id)["plan"]["execution"][0]["status"]
        == "needs_attention"
    )


def test_prepare_insertion_requires_real_proposal_not_discussion(case):
    service, cid, t, steps, p = case
    step = steps[1].model_copy(update={"selected": True})
    p = w.save(
        "world-one",
        cid,
        t.turn_id,
        w.ReviewV2(objective="Develop a useful shop description for author review.", expected_revision=1, steps=[steps[0], step]),
    )
    d = parse_dispatch(
        w.continue_step(
            "world-one",
            cid,
            t.turn_id,
            w.Continue(
                expected_revision=p["revision"],
                step_id=step.step_id,
                command_id=uuid4(),
            ),
        )["dispatch"]
    )
    actual = accept(
        service,
        cid,
        d.message,
        uuid5(NAMESPACE_URL, f"dmb-agent-turn:world-one:{d.client_turn_id}"),
    )
    finish(service, cid, actual, "Here is another work plan.")
    result = w.read("world-one", cid, t.turn_id)["plan"]["execution"][0]
    assert result["status"] == "needs_attention" and result["result"]["kind"] == "reply"


def test_downgrade_refuses_retained_reviewed_plan(case):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine
    from application_state.engine import sqlalchemy_url
    from application_state.agent_conversation.service import _ready_dsn

    migration = importlib.import_module(
        "application_state.migrations.versions.20261025_0064_reviewed_work_plans"
    )
    engine = create_engine(sqlalchemy_url(_ready_dsn()))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError, match="recovery forward"):
                    migration.downgrade()
    finally:
        engine.dispose()


def test_genuine_admitted_page_proposal_is_prepared_not_saved(
    tmp_path, monkeypatch, application_state_dsn
):
    from types import SimpleNamespace
    from hashlib import sha256
    from tests.test_build_related_pages import build_case, completed
    from application_state.build_proposal.service import BuildProposalService
    from application_state.unit_of_work import unit_of_work
    from application_state.agent_conversation.service import _ready_dsn

    inputs = build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)
    turn, *_ = completed.__wrapped__(
        inputs, monkeypatch, tmp_path, SimpleNamespace(param="propose_build_insertion")
    )
    receipt = BuildProposalService().get(turn.world_id, turn.completion.action_id)
    step = w.Step(
        step_id=uuid4(),
        text="Prepare page writing",
        selected=True,
        kind="prepare_insertion",
    )
    d = w.Dispatch(
        command_id=uuid4(),
        step_id=step.step_id,
        client_thread_id=uuid4(),
        client_turn_id=receipt.reservation.origin.client_turn_id,
        message=turn.user_text,
    )
    p = w.Plan(
        world_id=turn.world_id,
        conversation_id=turn.conversation_id,
        source_turn_id=turn.turn_id,
        source_answer_sha256=sha256(turn.assistant_text.encode()).hexdigest(),
        document_id=turn.provenance.primary_work.object_id,
        revision=1,
        steps=[step],
        dispatches=[d],
    )
    with unit_of_work(_ready_dsn()) as conn:
        result = w._result(conn, p, d)
    assert result["status"] == "prepared" and result["result"] == {
        "kind": "page_proposal",
        "action_id": str(receipt.action_id),
    }
    assert receipt.state == "proposed" and not receipt.inserted_in_draft


def test_readable_continuation_preserves_review_and_result_without_internal_ids(case):
    service, cid, t, steps, p = case
    response = w.continue_step(
        "world-one",
        cid,
        t.turn_id,
        w.Continue(expected_revision=1, step_id=steps[0].step_id, command_id=uuid4()),
    )
    first = parse_dispatch(response["dispatch"])
    assert steps[0].text in first.message and steps[1].text not in first.message
    assert first.scope.task.text == steps[0].text
    assert first.scope.sibling_context[0].text == steps[1].text
    assert first.scope.sibling_context[0].status == 'deferred'
    for identifier in (
        cid,
        t.turn_id,
        steps[0].step_id,
        steps[1].step_id,
        first.command_id,
        first.client_turn_id,
    ):
        assert str(identifier) not in first.message
    actual = accept(
        service,
        cid,
        first.message,
        uuid5(NAMESPACE_URL, f"dmb-agent-turn:world-one:{first.client_turn_id}"),
    )
    finish(service, cid, actual, "The owner repairs lantern fittings.")
    p = w.save(
        "world-one",
        cid,
        t.turn_id,
        w.ReviewV2(objective="Develop a useful shop description for author review.",
            expected_revision=2,
            steps=[steps[0], steps[1].model_copy(update={"selected": True})],
        ),
    )
    second = parse_dispatch(
        w.continue_step(
            "world-one",
            cid,
            t.turn_id,
            w.Continue(
                expected_revision=p["revision"],
                step_id=steps[1].step_id,
                command_id=uuid4(),
            ),
        )["dispatch"]
    )
    assert (
        "The owner repairs lantern fittings." in second.message
        and "reply received" in second.message
    )
    assert (
        first.message not in second.message
        and "reviewed_plan" not in second.message
        and "source_answer_sha256" not in second.message
    )
    assert "Selected · Discuss ·" not in first.message
    assert "Selected · Discuss ·" in second.message
    assert "Prepare an insertion ·" in second.message
    assert "editable on-page insertion" in second.message


def test_reviewed_reference_resolves_immutable_step_without_plan_revision_pin(case):
    from application_state.agent_conversation.reviewed_action import ReviewedStepReference
    from application_state.unit_of_work import unit_of_work
    service, cid, source, steps, plan = case
    command = w.Continue(expected_revision=plan['revision'], step_id=steps[0].step_id, command_id=uuid4())
    response = w.continue_step('world-one', cid, source.turn_id, command)
    reference = ReviewedStepReference.model_validate(response['reviewed_step'])
    d = parse_dispatch(response['dispatch'])
    def resolve():
        with unit_of_work(w._ready_dsn()) as conn:
            return w.resolve_action(conn, 'world-one', reference, document_id='source-one',
                client_thread_id=str(d.client_thread_id), client_turn_id=str(d.client_turn_id), message=d.message)
    binding = resolve()
    assert binding.kind == 'discuss' and binding.operation == 'answer_from_sources'
    # Changing another unstarted step must not invalidate the immutable command.
    w.save('world-one', cid, source.turn_id, w.ReviewV2(objective="Develop a useful shop description for author review.", expected_revision=response['plan']['revision'],
        steps=[steps[0], steps[1].model_copy(update={'text':'Another future description'})]))
    assert resolve() == binding
    actual = accept(service, cid, d.message, uuid5(NAMESPACE_URL, f'dmb-agent-turn:world-one:{d.client_turn_id}'))
    finish(service, cid, actual, 'Historical unbound response')
    # Never retrofit new authority to a previously admitted unbound request.
    assert w.continue_step('world-one', cid, source.turn_id, command)['reviewed_step'] is None


@pytest.mark.parametrize('mutation', ['world','page','conversation','source','command','thread','turn','message'])
def test_reviewed_reference_rejects_foreign_dispatch_inputs(case, mutation):
    from application_state.agent_conversation.reviewed_action import ReviewedStepReference
    from application_state.unit_of_work import unit_of_work
    from application_state.errors import ApplicationStateError
    _, cid, source, steps, plan = case
    response = w.continue_step('world-one', cid, source.turn_id,
        w.Continue(expected_revision=plan['revision'], step_id=steps[0].step_id, command_id=uuid4()))
    reference = ReviewedStepReference.model_validate(response['reviewed_step'])
    d = parse_dispatch(response['dispatch'])
    args = dict(document_id='source-one', client_thread_id=str(d.client_thread_id), client_turn_id=str(d.client_turn_id), message=d.message)
    if mutation in {'conversation','source','command'}:
        field = {'conversation':'conversation_id','source':'source_turn_id','command':'command_id'}[mutation]
        reference = reference.model_copy(update={field:uuid4()})
    elif mutation != 'world':
        field = {'page':'document_id','thread':'client_thread_id','turn':'client_turn_id','message':'message'}[mutation]
        args[field] = 'changed'
    with unit_of_work(w._ready_dsn()) as conn, pytest.raises(ApplicationStateError):
        w.resolve_action(conn, 'other-world' if mutation == 'world' else 'world-one', reference, **args)


def test_outcome_only_save_cas_and_dispatch_snapshot_survive_later_edit(case):
    service,cid,t,steps,p=case
    outcome='A small shop scene with useful choices and no invented played events.'
    p=w.save('world-one',cid,t.turn_id,w.ReviewV2(expected_revision=1,steps=steps,objective=outcome))
    assert p['revision']==2 and p['objective']==outcome
    with pytest.raises(ApplicationStateConflictError):
        w.save('world-one',cid,t.turn_id,w.ReviewV2(expected_revision=1,steps=steps,objective='A conflicting outcome.'))
    command=w.Continue(expected_revision=2,step_id=steps[0].step_id,command_id=uuid4())
    first=w.continue_step('world-one',cid,t.turn_id,command)
    assert first['dispatch']['scope']['objective_context']==outcome
    assert outcome not in first['dispatch']['message']
    changed=w.save('world-one',cid,t.turn_id,w.ReviewV2(expected_revision=3,steps=steps,objective='A newly edited intended outcome.'))
    assert changed['dispatches']==first['plan']['dispatches']
    recovered=w.continue_step('world-one',cid,t.turn_id,command)
    assert recovered['dispatch']==first['dispatch']
    assert recovered['dispatch']['scope']['objective_context']==outcome
    assert 'newly edited' not in recovered['dispatch']['message']
    assert w.read('world-one',cid,t.turn_id)['plan']==changed


def test_retained_v1_read_is_byte_stable_and_only_explicit_v2_save_upgrades(case,application_state_dsn):
    import psycopg
    from psycopg.types.json import Jsonb
    service,cid,t,steps,p=case
    legacy={k:v for k,v in p.items() if k not in {'objective','execution'}}
    legacy['schema']='dmb_reviewed_work_plan_v1'
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute('UPDATE agent.work_plan SET payload=%s WHERE source_turn_id=%s',(Jsonb(legacy),t.turn_id))
        original=conn.execute('SELECT payload::text FROM agent.work_plan WHERE source_turn_id=%s',(t.turn_id,)).fetchone()[0]
    read=w.read('world-one',cid,t.turn_id)['plan']
    assert 'objective' not in read and read['steps']==p['steps']
    replay=w.save('world-one',cid,t.turn_id,w.Review(expected_revision=1,steps=steps))
    assert replay==read
    with pytest.raises(ApplicationStateConflictError):
        w.save('world-one',cid,t.turn_id,w.Review(expected_revision=0,steps=steps))
    with pytest.raises(ApplicationStateConflictError,match='expected outcome'):
        w.continue_step('world-one',cid,t.turn_id,w.Continue(expected_revision=1,step_id=steps[0].step_id,command_id=uuid4()))
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute('SELECT payload::text FROM agent.work_plan WHERE source_turn_id=%s',(t.turn_id,)).fetchone()[0]==original
    upgraded=w.save('world-one',cid,t.turn_id,w.ReviewV2(expected_revision=1,steps=steps,objective='The author explicitly supplied this outcome.'))
    assert upgraded['schema']=='dmb_reviewed_work_plan_v2' and upgraded['steps']==read['steps']


def test_legacy_put_cannot_create_or_mutate_plan(case):
    service,cid,t,steps,p=case
    with pytest.raises(ApplicationStateConflictError,match='legacy writes'):
        w.save('world-one',cid,t.turn_id,w.Review(expected_revision=p['revision'],steps=steps))
    other=finish(service,cid,accept(service,cid,'Another plan'),'A proposed plan.')
    with pytest.raises(ApplicationStateConflictError,match='legacy writes'):
        w.save('world-one',cid,other.turn_id,w.Review(expected_revision=0,steps=steps))


@pytest.mark.parametrize('scoped',[False,True])
def test_scope_vocabulary_downgrade_preserves_rows_and_refuses_retained_dispatch(case,scoped):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine
    from application_state.engine import sqlalchemy_url
    service,cid,source,steps,plan=case
    if scoped:
        w.continue_step('world-one',cid,source.turn_id,w.Continue(expected_revision=plan['revision'],step_id=steps[0].step_id,command_id=uuid4()))
    before=w.read('world-one',cid,source.turn_id)
    migration=importlib.import_module('application_state.migrations.versions.20261026_0074_reviewed_discussion_scope')
    engine=create_engine(sqlalchemy_url(w._ready_dsn()))
    try:
        with engine.begin() as conn,Operations.context(MigrationContext.configure(conn)):
            if scoped:
                with pytest.raises(RuntimeError,match='recovery forward'):migration.downgrade()
            else:
                migration.downgrade()
    finally:engine.dispose()
    assert w.read('world-one',cid,source.turn_id)==before


def test_scope_upgrade_preserves_payloads_and_fences_previous_reader(case, application_state_dsn, monkeypatch):
    import psycopg
    from alembic import command
    from application_state import cli
    from application_state.errors import ApplicationStateMigrationError

    def retained_rows():
        with psycopg.connect(application_state_dsn) as conn:
            return {
                table: conn.execute(f'SELECT row_to_json(t)::text FROM agent.{table} t ORDER BY row_to_json(t)::text').fetchall()
                for table in ('conversation', 'turn', 'work_plan', 'turn_reviewed_action')
            }

    before = retained_rows()
    command.downgrade(cli.alembic_config(), '20261025_0073')
    assert cli._read_current_revision(application_state_dsn) == '20261025_0073'
    cli.upgrade_to_head(dsn=application_state_dsn)
    assert cli._read_current_revision(application_state_dsn) == '20261026_0074'
    assert retained_rows() == before
    monkeypatch.setattr(cli, '_alembic_head', lambda: '20261025_0073')
    with pytest.raises(ApplicationStateMigrationError):
        cli.assert_at_head(dsn=application_state_dsn)
    # The same head fence is reached by saved-plan admission and conversation reads.
    service, cid, source, steps, plan = case
    with pytest.raises(ApplicationStateMigrationError):
        w.continue_step('world-one', cid, source.turn_id,
            w.Continue(expected_revision=plan['revision'], step_id=steps[0].step_id, command_id=uuid4()))
    with pytest.raises(ApplicationStateMigrationError):
        service.get_conversation('world-one', cid)
