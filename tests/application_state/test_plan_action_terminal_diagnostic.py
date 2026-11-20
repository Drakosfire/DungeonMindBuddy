"""Actual fenced APP storage, projection and migration witnesses."""
import importlib
import json
from uuid import uuid4
import pytest
from application_state.errors import ApplicationStateError
from application_state.plan_action_dialogue.service import PlanActionDialogueService
from application_state.plan_action_dialogue.types import ActionTerminalDiagnosticV1, decode_consultation
from tests.application_state.test_plan_action_prompt_capture import frozen, append, reference


@pytest.fixture
def application_state_dsn(monkeypatch):
    from tests.application_state import test_plan_action_consultation as cases
    yield from cases.application_state_dsn.__wrapped__(monkeypatch)


def diagnostic(action, **changes):
    data = dict(world_id=action.basis.world_id, action_id=action.action_id,
        dispatch_fence=action.fence, attribution="action_only", availability="unavailable",
        unavailable_reason="missing_or_not_retained", runtime_status="error",
        error_origin="runtime_result", error_category="other")
    data.update(changes)
    return ActionTerminalDiagnosticV1(**data)


def retain(store, action, value):
    return store.append_terminal_diagnostic(action_id=action.action_id,
        token=action.dispatch_token, fence=action.fence, diagnostic=value)


FAILURE = dict(phase="provider_lifecycle", reason="provider_response_incomplete",
               transition="outcome_unknown", acknowledged=True,
               responseStatus="incomplete", incompleteReason="max_output_tokens")


def test_v3_survives_refs_failure_fresh_read_and_public_redaction(application_state_dsn):
    store, action, _, events = frozen()
    legacy = action.consultation.model_dump_json()
    assert decode_consultation(action.consultation.model_dump(by_alias=True)).model_dump_json() == legacy
    action = append(store, action, events[0])
    value = diagnostic(action)
    action, fresh = retain(store, action, value)
    assert fresh
    assert retain(store, action, value)[1] is False
    action, _ = store.append_prompt_reference(action_id=action.action_id,
        token=action.dispatch_token, fence=action.fence, reference=reference(action, events[0]))
    assert action.consultation.schema_version == "dmb_plan_action_consultation_v3"
    action = append(store, action, events[1])
    action = store.finish(action_id=action.action_id, token=action.dispatch_token,
        fence=action.fence, status="failed", failure_code="synthetic_failure")
    fresh = PlanActionDialogueService().read_prompt_action(world_id=action.basis.world_id, action_id=action.action_id)
    assert fresh.consultation.terminal_diagnostic == value
    import os
    import subprocess
    import sys
    script = ("from uuid import UUID; from application_state.plan_action_dialogue.service import PlanActionDialogueService; "
        "a=PlanActionDialogueService().read_prompt_action(world_id='synthetic-world', action_id=UUID(%r)); "
        "print(a.consultation.terminal_diagnostic.model_dump_json())") % str(action.action_id)
    assert json.loads(subprocess.check_output([sys.executable, "-c", script], env=dict(os.environ), text=True)) == value.model_dump(mode="json")
    assert len(fresh.consultation.prompt_references) == 1
    assert "terminal_diagnostic" not in store._projection(fresh).model_dump_json()
    with pytest.raises(ApplicationStateError):
        retain(store, action, value)
    with pytest.raises(ApplicationStateError):
        store.read_prompt_action(world_id="other-world", action_id=action.action_id)


@pytest.mark.parametrize("mutation", ["world_id", "action_id", "dispatch_fence", "token", "conflict"])
def test_owner_fence_and_conflicts_refuse(application_state_dsn, mutation):
    store, action, _, _ = frozen()
    good = diagnostic(action)
    if mutation == "conflict":
        action, _ = retain(store, action, good)
        bad = good.model_copy(update={"error_category": "unavailable"})
    else:
        bad = good.model_copy(update={"world_id": "other-world"} if mutation == "world_id"
            else {"action_id": uuid4()} if mutation == "action_id"
            else {"dispatch_fence": action.fence + 1} if mutation == "dispatch_fence" else {})
    with pytest.raises((ValueError, ApplicationStateError)):
        store.append_terminal_diagnostic(action_id=action.action_id,
            token=uuid4() if mutation == "token" else action.dispatch_token,
            fence=action.fence, diagnostic=bad)


@pytest.mark.parametrize("parent_ack", [True, False])
def test_matching_event_and_latest_outcome_are_distinct(application_state_dsn, parent_ack):
    from application_state.agent_conversation.types import ProviderOutcomeEventV1
    store, action, _, events = frozen()
    for event in events[:8]:
        action = append(store, action, event)
    event = ProviderOutcomeEventV1(event_id=uuid4(), sequence=8, kind="provider_outcome",
                                 provider_attempt_id=events[6].provider_attempt_id, outcome="outcome_unknown")
    action = append(store, action, event)
    value = diagnostic(action, availability="captured", unavailable_reason=None, failure=FAILURE,
        attribution="provider_attempt", authorization_event_id=events[6].event_id,
        provider_attempt_id=event.provider_attempt_id, callback_sequence=8,
        parent_acknowledged=parent_ack)
    if not parent_ack:
        value = value.model_copy(update={"failure": value.failure.model_copy(update={"acknowledged": False})})
    action, _ = retain(store, action, value)
    assert retain(store, action, value)[1] is False
    saved = action.consultation.terminal_diagnostic
    assert saved.matching_transition_event_id == event.event_id
    assert saved.latest_durable_outcome_event_id == event.event_id
    assert saved.latest_durable_outcome == "outcome_unknown"
    bad = json.loads(action.consultation.model_dump_json(by_alias=True))
    bad["terminal_diagnostic"]["authorization_event_id"] = str(events[0].event_id)
    with pytest.raises(ValueError):
        decode_consultation(bad)


def test_migration_guards_every_v3_and_restores_exact_0033(application_state_dsn):
    import psycopg
    from psycopg.types.json import Jsonb
    from alembic import command
    from application_state.cli import alembic_config
    store, action, _, _ = frozen()
    action, _ = retain(store, action, diagnostic(action))
    def snapshot():
        with psycopg.connect(application_state_dsn) as conn:
            return (conn.execute("SELECT consultation FROM plan_action.action WHERE action_id=%s", (action.action_id,)).fetchone()[0],
                conn.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='plan_action_consultation_check'").fetchone()[0],
                conn.execute("SELECT version_num FROM application_state.schema_migrations").fetchone()[0])
    before = snapshot()
    with pytest.raises(RuntimeError, match="refusing to discard"):
        command.downgrade(alembic_config(), "20261018_0033")
    assert snapshot() == before
    for change in (None, {}, [], {"schema_version": "wrong"}):
        with psycopg.connect(application_state_dsn) as conn:
            with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
                conn.execute("UPDATE plan_action.action SET consultation=%s WHERE action_id=%s",
                    (Jsonb({**before[0], "terminal_diagnostic": change}), action.action_id))
    old = importlib.import_module("application_state.migrations.versions.20261018_0033_plan_action_prompt_capture")
    new = importlib.import_module("application_state.migrations.versions.20261018_0034_plan_action_terminal_diagnostic")
    assert new._PREVIOUS_CHECK == old._CAPTURE_CHECK


def test_v1_v2_roundtrip_no_rewrite(application_state_dsn):
    from alembic import command
    from application_state.cli import alembic_config
    store, first, _, _ = frozen()
    _, second, _, events = frozen()
    second = append(store, second, events[0])
    second, _ = store.append_prompt_reference(action_id=second.action_id,
        token=second.dispatch_token, fence=second.fence, reference=reference(second, events[0]))
    snapshots = [a.consultation.model_dump_json() for a in (first, second)]
    command.downgrade(alembic_config(), "20261018_0033")
    command.upgrade(alembic_config(), "head")
    assert [store.read_prompt_action(world_id=a.basis.world_id, action_id=a.action_id).consultation.model_dump_json()
            for a in (first, second)] == snapshots


def test_pending_expired_lease_refuses_retention(application_state_dsn):
    import psycopg
    store, action, _, _ = frozen()
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE plan_action.action SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE action_id=%s", (action.action_id,))
    with pytest.raises(ApplicationStateError):
        retain(store, action, diagnostic(action))
