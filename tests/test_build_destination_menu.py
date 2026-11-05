"""Destination instructions evolve without reinterpreting stored controller proof."""
import json

import pytest

from application_state.agent_conversation import build_intentional_response as semantic
from tests.test_surface_native_build_decision import sdk_case
from tests.test_surface_native_execution import component, execution

PREVIOUS_MENU = "a1bb5a599710fd3ca21503959ff1dad5f182d1ed943be4e4fcf9c46d74efbb68"
RESOLVER = "5ac8ed975419055aed1a24be9586dc3c613857449ab9c159affe53ca3cc014cc"


def test_current_menu_changes_destination_guidance_without_changing_capability_semantics():
    assert semantic.MENU_DIGEST != PREVIOUS_MENU
    assert semantic.RESOLVER_DIGEST == RESOLVER
    assert semantic.known_menu(PREVIOUS_MENU)
    assert not semantic.known_menu("f" * 64)
    assert "retain the previously requested artifact and destination" in semantic.decision_instructions()
    assert "current-page writing, including" not in semantic.decision_instructions()
    assert "current-page writing, including" in semantic.decision_instructions(PREVIOUS_MENU)
    with pytest.raises(ValueError, match="Unknown frozen"):
        semantic.decision_instructions("f" * 64)


@pytest.mark.parametrize("requested", ["discuss", "write_current_page", "review_connected_page"])
@pytest.mark.parametrize("previous", [False, True])
def test_actual_sdk_proof_uses_its_captured_menu_after_reload(monkeypatch, requested, previous):
    context, record = component("build", unavailable=True)
    if previous:
        action = record.policy.action.model_copy(update={"requested_work_menu_sha256": PREVIOUS_MENU})
        record = execution(context.context_receipt_sha256, record.policy.model_copy(update={"action": action}))
    instructions = semantic.decision_instructions
    with monkeypatch.context() as old_producer:
        if previous:
            old_producer.setattr(semantic, "decision_instructions", lambda: instructions(PREVIOUS_MENU))
        context, record, event, proof, trace, work = sdk_case(
            requested, capable=True, context_record=(context, record))
    if previous:
        event = event.model_copy(update={"menu_sha256": PREVIOUS_MENU})
    # JSON round trips exercise the strict retained reader, not model_copy only.
    record = type(record).model_validate_json(record.model_dump_json(by_alias=True))
    event = type(event).model_validate_json(event.model_dump_json(by_alias=True))
    semantic.validate_selection_records(record, event, proof, trace,
        user_text=record.policy.action.intent.message, turn_id=work["turn_id"], attempt=1)
    semantic.validate_resolution_metadata(event, record.policy)
    wire = json.loads(proof["request_json"])["questions"]["requested_work"]
    assert wire["instructions"] == instructions(event.menu_sha256)
    with pytest.raises(ValueError, match="actual admitted request/response"):
        semantic.validate_selection_records(record, event.model_copy(update={
            "menu_sha256": semantic.MENU_DIGEST if previous else PREVIOUS_MENU,
        }), proof, trace, user_text=record.policy.action.intent.message,
            turn_id=work["turn_id"], attempt=1)
    assert event.resolution["requested_work"] == requested
    assert event.operation == ("propose_build_insertion" if requested == "write_current_page" else "answer_from_sources")


def test_unknown_captured_menu_is_not_admitted_as_history():
    _, record = component("build", unavailable=True)
    action = record.policy.action.model_dump(mode="json", by_alias=True)
    action["requested_work_menu_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="Unknown frozen"):
        type(record.policy.action).model_validate_json(json.dumps(action))


def test_installed_reader_fence_requires_forward_recovery(application_state_dsn):
    from importlib import import_module
    import psycopg
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute(
            "SELECT version_num FROM application_state.schema_migrations"
        ).fetchone()[0] == "20261105_0115"
    with pytest.raises(RuntimeError, match="rejects retained destination-aware decisions"):
        import_module(
            "application_state.migrations.versions.20261105_0115_build_destination_menu"
        ).downgrade()
