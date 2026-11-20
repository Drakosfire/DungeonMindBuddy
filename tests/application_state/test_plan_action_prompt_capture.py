"""Actual APP action persistence, V1 compatibility, and private projection boundaries."""
from uuid import uuid4

import pytest
from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
from application_state.plan_action_dialogue.types import (
    ActionPromptReferenceV1, decode_consultation, public_consultation,
)
from application_state.plan_action_dialogue.service import PlanActionDialogueService
from tests.application_state.test_plan_action_consultation import (
    reservation, frozen_inputs, consultation_events, attributed_result,
)


@pytest.fixture
def application_state_dsn(monkeypatch):
    from tests.application_state import test_plan_action_consultation as cases
    yield from cases.application_state_dsn.__wrapped__(monkeypatch)


def reference(action, event):
    return ActionPromptReferenceV1(
        world_id=action.basis.world_id, action_id=action.action_id, dispatch_fence=action.fence,
        authorization_event_id=event.event_id, provider_attempt_id=event.provider_attempt_id,
        evidence_id=uuid4(), provider=event.provider, model=event.model, api_mode=event.api_mode,
        serializer_version=event.serializer_version, payload_sha256=event.envelope_sha256,
        payload_utf8_bytes=42,
    )


def frozen():
    store = PlanActionDialogueService()
    action, _ = store.reserve(reservation())
    receipt, policy = frozen_inputs(action)
    action, _ = store.freeze_consultation(action_id=action.action_id, token=action.dispatch_token,
                                         fence=action.fence, receipt=receipt, policy=policy)
    return store, action, receipt, consultation_events(receipt, policy)


def append(store, action, event):
    return store.append_consultation_event(action_id=action.action_id, token=action.dispatch_token,
                                          fence=action.fence, event=event)[0]


@pytest.mark.parametrize("terminal", ["completed", "failed"])
def test_two_captures_survive_events_terminal_reload_and_public_projection(application_state_dsn, terminal):
    store, action, receipt, events = frozen()
    legacy = action.consultation.model_dump_json()
    assert decode_consultation(action.consultation.model_dump(by_alias=True)).model_dump_json() == legacy
    refs = []
    for event in events:
        action = append(store, action, event)
        if event.kind.startswith("provider_attempt_authorized"):
            ref = reference(action, event)
            refs.append(ref)
            action, fresh = store.append_prompt_reference(action_id=action.action_id,
                token=action.dispatch_token, fence=action.fence, reference=ref)
            assert fresh
            same, fresh = store.append_prompt_reference(action_id=action.action_id,
                token=action.dispatch_token, fence=action.fence, reference=ref)
            assert not fresh and same.consultation == action.consultation
    assert action.consultation.prompt_references == refs
    if terminal == "completed":
        action = store.finish_consultation(action_id=action.action_id, token=action.dispatch_token,
            fence=action.fence, result=attributed_result(receipt, events))
    else:
        action = store.finish(status="failed", action_id=action.action_id, token=action.dispatch_token,
                            fence=action.fence, failure_code="synthetic_failure")
    reread = PlanActionDialogueService().read_prompt_action(world_id=action.basis.world_id, action_id=action.action_id)
    assert reread.consultation.prompt_references == refs
    assert reread.status == terminal
    import json
    import os
    import subprocess
    import sys
    script = """import json; from uuid import UUID; from application_state.plan_action_dialogue.service import PlanActionDialogueService; a=PlanActionDialogueService().read_prompt_action(world_id='synthetic-world',action_id=UUID(%r)); print(json.dumps([r.model_dump(mode='json') for r in a.consultation.prompt_references]))""" % str(action.action_id)
    output = subprocess.check_output([sys.executable, "-c", script], env=dict(os.environ), text=True)
    assert json.loads(output) == [ref.model_dump(mode="json") for ref in refs]
    if terminal == "completed":
        assert "prompt_references" not in store.completed_context(action.basis)[0].model_dump_json()
    for projection in (store._projection(reread),):
        assert "prompt_references" not in projection.model_dump_json()
        assert projection.consultation.schema_version == "dmb_plan_action_consultation_v1"
    assert public_consultation(reread.consultation).receipt == receipt
    assert len(store.list_conversation_status(receipt.basis.world_id, receipt.origin_conversation_id).actions) == 1
    with pytest.raises(ApplicationStateValidationError):
        store.read_prompt_action(world_id="other-world", action_id=action.action_id)


@pytest.mark.parametrize("mutation", ["world_id", "action_id", "dispatch_fence", "authorization_event_id", "payload_sha256", "provider_attempt_id", "serializer_version"])
def test_reference_mismatch_and_stale_fence_refuse(application_state_dsn, mutation):
    store, action, _, events = frozen()
    action = append(store, action, events[0])
    ref = reference(action, events[0])
    values = dict(world_id="other-world", action_id=uuid4(), dispatch_fence=action.fence + 1,
                  authorization_event_id=uuid4(), payload_sha256="0" * 64,
                  provider_attempt_id=uuid4(), serializer_version="openai-sdk-json-v1")
    bad = ActionPromptReferenceV1.model_validate({**ref.model_dump(), mutation: values[mutation]})
    with pytest.raises((ValueError, ApplicationStateValidationError, ApplicationStateConflictError)):
        store.append_prompt_reference(action_id=action.action_id, token=action.dispatch_token,
                                      fence=action.fence, reference=bad)
    assert not hasattr(store.read_prompt_action(world_id=action.basis.world_id, action_id=action.action_id).consultation, "prompt_references")


def test_conflicting_retry_and_late_append_refuse(application_state_dsn):
    store, action, _, events = frozen()
    action = append(store, action, events[0])
    ref = reference(action, events[0])
    action, _ = store.append_prompt_reference(action_id=action.action_id, token=action.dispatch_token, fence=action.fence, reference=ref)
    with pytest.raises(ApplicationStateConflictError):
        store.append_prompt_reference(action_id=action.action_id, token=action.dispatch_token,
            fence=action.fence, reference=ref.model_copy(update={"evidence_id": uuid4()}))
    assert len(action.consultation.prompt_references) == 1
    store, action, _, events = frozen()
    action = append(store, action, events[0])
    ref = reference(action, events[0])
    action = append(store, action, events[1])
    with pytest.raises(ApplicationStateConflictError):
        store.append_prompt_reference(action_id=action.action_id, token=action.dispatch_token, fence=action.fence, reference=ref)


def test_migration_guard_and_malformed_records_fail_closed(application_state_dsn):
    import json
    import psycopg
    from psycopg.types.json import Jsonb
    from alembic import command
    from application_state.cli import alembic_config
    store, action, _, events = frozen()
    action = append(store, action, events[0])
    action, _ = store.append_prompt_reference(action_id=action.action_id,
        token=action.dispatch_token, fence=action.fence, reference=reference(action, events[0]))
    def snapshot():
        with psycopg.connect(application_state_dsn) as conn:
            return (conn.execute("SELECT consultation FROM plan_action.action WHERE action_id=%s", (action.action_id,)).fetchone()[0],
                    conn.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='plan_action_consultation_check'").fetchone()[0],
                    conn.execute("SELECT version_num FROM application_state.schema_migrations").fetchone()[0])
    before = snapshot()
    with pytest.raises(RuntimeError, match="refusing to discard"):
        command.downgrade(alembic_config(), "20261017_0032")
    assert snapshot() == before
    good = before[0]
    malformed = []
    for value in (None, {}, "wrong", [None] * 513):
        malformed.append({**good, "prompt_references": value})
    missing = dict(good); missing.pop("prompt_references"); malformed.append(missing)
    malformed.append({**good, "schema_version": "unknown"})
    wrong_owner = json.loads(json.dumps(good)); wrong_owner["receipt"]["basis"]["world_id"] = "foreign"
    malformed.append(wrong_owner)
    for value in malformed:
        with psycopg.connect(application_state_dsn) as conn:
            with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
                conn.execute("UPDATE plan_action.action SET consultation=%s WHERE action_id=%s", (Jsonb(value), action.action_id))
    assert snapshot() == before


def test_v1_migration_roundtrip_retains_exact_content(application_state_dsn):
    import psycopg
    from alembic import command
    from application_state.cli import alembic_config
    store, action, _, events = frozen()
    action = append(store, action, events[0])
    expected = action.consultation.model_dump(mode="json", by_alias=True)
    command.downgrade(alembic_config(), "20261017_0032")
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT consultation FROM plan_action.action WHERE action_id=%s", (action.action_id,)).fetchone()[0] == expected
    command.upgrade(alembic_config(), "head")
    assert store.read_prompt_action(world_id=action.basis.world_id, action_id=action.action_id).consultation.model_dump(mode="json", by_alias=True) == expected
