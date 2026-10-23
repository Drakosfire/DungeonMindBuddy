"""Real APP navigation persistence/fences; synthetic trusted native proof."""
from uuid import uuid4
import json

import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.errors import ApplicationStateValidationError, ApplicationStateConflictError
from tests.application_state.test_plan_jev_decision_admission import prepare_case, append as append_decision
from tests.application_state.test_native_play_input_postgres import prepared_native, append
from tests.test_native_source_origin import origin as core_origin  # noqa: F401


@pytest.fixture(params=["plan", "play"])
def nav_case(application_state_dsn, monkeypatch, request):
    original = AgentConversationService.accept_turn
    def accept(service, sub):
        execution = sub.graph_context_execution
        cls = t.PlanNativeSourceSectionsPolicyV1 if request.param == "plan" else t.PlayNativeSourceSectionsPolicyV1
        policy = cls.model_validate(execution.policy.model_dump(mode="json", by_alias=True) | {
            "native_source_section_policy": "exact_native_source_sections_v1"})
        wire = execution.model_dump(mode="json", by_alias=True)
        wire["policy"] = policy.model_dump(mode="json", by_alias=True)
        wire["execution_policy_sha256"] = t._canonical_sha256({
            "schema": execution.schema_, "context_receipt_sha256": execution.context_receipt_sha256,
            "policy": wire["policy"]})
        execution = type(execution).model_validate(wire)
        return original(service, sub.model_copy(update={"graph_context_execution": execution}))
    monkeypatch.setattr(AgentConversationService, "accept_turn", accept)
    if request.param == "plan":
        case = prepare_case(application_state_dsn)
        append_decision(case)
        service, turn = case.service, case.turn
        service.nav_test_controller = case
    else:
        service, sub, turn, provider, raw = prepared_native(application_state_dsn, moment=False)
        turn, _ = append(service, sub, turn, provider, raw)
        for outcome in ("sdk_entered", "response_received"):
            turn, _ = service.record_provider_outcome(turn.world_id, turn.conversation_id, turn.turn_id,
                expected_revision=turn.revision, expected_attempt=turn.attempt,
                outcome=t.ProviderOutcomeEventV1(kind="provider_outcome", event_id=uuid4(),
                    sequence=len(turn.graph_context_execution.events),
                    provider_attempt_id=provider.provider_attempt_id, outcome=outcome))
    execution, receipt = turn.graph_context_execution, turn.graph_context_receipt
    pin = t.GraphSourceScopeAnchorV2(anchor_id="source-anchor:v1:proof", evidence_ref_id="evidence:proof",
        source_artifact_id="source:proof", source_revision_id="native-revision:proof")
    donor = t.ValidatedGraphOperationEventV3(kind="validated_graph_operation_v3", event_id=uuid4(),
        sequence=len(execution.events), operation_id=uuid4(), operation=execution.policy.allowed_graph_operations[0],
        request_arguments_sha256="a"*64, result_packet_sha256="b"*64,
        graph_revision=receipt.graph_authority.graph_revision, assertion_ids=[], relationship_ids=[],
        evidence_ref_ids=[pin.evidence_ref_id], returned_source_pins=[pin],
        evidence_sufficiency_status="sufficient", coverage_status="complete", truncated=False, source_opened=False)
    turn, _ = service.append_validated_graph_operation(turn.world_id, turn.conversation_id, turn.turn_id,
        expected_revision=turn.revision, expected_attempt=turn.attempt, operation_event=donor)
    execution = turn.graph_context_execution
    scope, authority = execution.policy.source_read_scope, receipt.graph_authority
    extension = t.SourceScopeExtensionEventV3(kind="source_scope_extension_v3", event_id=uuid4(),
        sequence=len(execution.events), origin_graph_event_id=donor.event_id,
        context_receipt_sha256=execution.context_receipt_sha256, execution_policy_sha256=execution.execution_policy_sha256,
        world_id=turn.world_id, native_world_id=authority.native_world_id, binding_version=authority.binding_version,
        campaign_id=None, graph_revision=scope.graph_revision, retrieval_session_id=scope.retrieval_session_id, pins=[pin])
    turn, _ = service.extend_source_scope(turn.world_id, turn.conversation_id, turn.turn_id,
        expected_revision=turn.revision, expected_attempt=turn.attempt, extension=extension)
    return service, turn, donor, pin


def authorization(turn, donor, pin):
    execution, authority = turn.graph_context_execution, turn.graph_context_receipt.graph_authority
    scope = {"world_id": authority.native_world_id, "campaign_id": None,
        "admissibility": "gm", "scope_mode": "world_cross_campaign", "focus": {"kind": "none", "session_id": None}}
    source = {"source_artifact_id": pin.source_artifact_id, "source_revision_id": pin.source_revision_id}
    proof = {"schema": "dmb_native_source_origin_proof_v1", "donor": donor.model_dump(mode="json"),
        "donor_sha256": t._canonical_sha256(donor.model_dump(mode="json")), "pin": pin.model_dump(mode="json"),
        "projection": scope | {"revision_pin": donor.graph_revision},
        "resolution": source | {"evidence_ref_id": pin.evidence_ref_id, "anchor_id": "dm-source-anchor:v1:proof", "can_open_source": True,
            "snapshot": scope | {"revision_id": donor.graph_revision},
            "artifact": {"source_artifact_id": pin.source_artifact_id, "world_id": authority.native_world_id,
                "source_domain": "worldbuilding", "status": "active", "visibility": "gm"},
            "evidence": source | {"evidence_ref_id": pin.evidence_ref_id, "source_domain": "worldbuilding"}},
        "revision": source | {"content_sha256": "c"*64}}
    provider = next(e for e in reversed(execution.events) if isinstance(e, t.ProviderAttemptAuthorizedEventV1))
    return t.NativeSourceNavigationAuthorizedV1(kind="native_source_navigation_authorized_v1",
        event_id=uuid4(), sequence=len(execution.events), navigation_id=uuid4(), provider_attempt_id=provider.provider_attempt_id,
        context_receipt_sha256=execution.context_receipt_sha256, execution_policy_sha256=execution.execution_policy_sha256,
        world_id=turn.world_id, native_world_id=authority.native_world_id, binding_version=authority.binding_version,
        origin_proof_json=json.dumps(proof), origin_proof_sha256=t._canonical_sha256(proof))


def persist(service, turn, event, **overrides):
    return service.authorize_native_source_navigation(turn.world_id, turn.conversation_id, turn.turn_id,
        **(dict(expected_revision=turn.revision, expected_attempt=turn.attempt, authorization=event) | overrides))


def test_persist_reload_and_exact_retry_grants_no_read(nav_case):
    service, turn, donor, pin = nav_case
    event = authorization(turn, donor, pin)
    updated, fresh = persist(service, turn, event)
    assert fresh
    reopened = service.list_turns(turn.world_id, turn.conversation_id)[-1]
    assert reopened.graph_context_execution.events[-1] == event
    assert reopened.graph_context_execution.execution_policy_sha256 == turn.graph_context_execution.execution_policy_sha256
    replayed, fresh = persist(service, updated, event)
    assert not fresh and replayed.revision == updated.revision
    assert not any(isinstance(e, t.SOURCE_PASSAGE_EVENTS) for e in reopened.graph_context_execution.events)
    with pytest.raises(ApplicationStateConflictError):
        persist(service, updated, event.model_copy(update={"navigation_id": uuid4()}))


@pytest.mark.parametrize("change", ["world_id", "native_world_id", "binding_version", "context_receipt_sha256", "execution_policy_sha256", "provider_attempt_id"])
def test_wrong_scope_is_not_committed(nav_case, change):
    service, turn, donor, pin = nav_case
    event = authorization(turn, donor, pin)
    value = uuid4() if change == "provider_attempt_id" else 999 if change == "binding_version" else "d"*64
    with pytest.raises((ApplicationStateValidationError, ValueError)):
        persist(service, turn, event.model_copy(update={change: value}))
    assert service.list_turns(turn.world_id, turn.conversation_id)[-1].revision == turn.revision


def test_stale_fence_and_duplicate_source_do_not_admit(nav_case):
    service, turn, donor, pin = nav_case
    event = authorization(turn, donor, pin)
    with pytest.raises(ApplicationStateConflictError):
        persist(service, turn, event, expected_revision=turn.revision-1)
    with pytest.raises(ApplicationStateConflictError):
        persist(service, turn, event, expected_attempt=turn.attempt+1)
    updated, _ = persist(service, turn, event)
    with pytest.raises(ApplicationStateValidationError):
        persist(service, updated, authorization(updated, donor, pin))


def test_changed_donor_and_terminal_provider_cannot_rebind(nav_case):
    service, turn, donor, pin = nav_case
    changed = donor.model_copy(update={"result_packet_sha256": "e"*64})
    with pytest.raises(ApplicationStateValidationError):
        persist(service, turn, authorization(turn, changed, pin))
    event = authorization(turn, donor, pin)
    with pytest.raises(ApplicationStateValidationError):
        service.record_provider_outcome(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt,
            outcome=t.ProviderOutcomeEventV1(kind="provider_outcome", event_id=uuid4(),
                sequence=len(turn.graph_context_execution.events), provider_attempt_id=event.provider_attempt_id,
                outcome="outcome_unknown"))
    from types import SimpleNamespace
    from application_state.agent_conversation.native_source_navigation import validate_navigation_events
    events = [e.model_copy(update={"outcome": "outcome_unknown"})
              if isinstance(e, t.ProviderOutcomeEventV1) and e.outcome == "response_received" else e
              for e in turn.graph_context_execution.events]
    with pytest.raises(ValueError):
        validate_navigation_events(SimpleNamespace(policy=turn.graph_context_execution.policy, events=events+[event]))


@pytest.mark.parametrize("change", ["missing", "digest", "source", "inactive", "scope"])
def test_malformed_or_changed_structured_proof_is_rejected(nav_case, change):
    _, turn, donor, pin = nav_case
    event = authorization(turn, donor, pin)
    proof = json.loads(event.origin_proof_json)
    if change == "missing": del proof["resolution"]["artifact"]
    elif change == "digest": proof["revision"]["content_sha256"] = "bad"
    elif change == "source": proof["revision"]["source_artifact_id"] = "foreign"
    elif change == "inactive": proof["resolution"]["artifact"]["status"] = "retracted"
    else: proof["projection"]["scope_mode"] = "world"
    wire = event.model_dump(mode="json") | {"origin_proof_json": json.dumps(proof), "origin_proof_sha256": t._canonical_sha256(proof)}
    with pytest.raises(ValueError):
        t.NativeSourceNavigationAuthorizedV1.model_validate(wire)


def test_old_policy_cannot_accept_navigation(nav_case):
    _, turn, donor, pin = nav_case
    event = authorization(turn, donor, pin)
    execution = turn.graph_context_execution
    wire = execution.model_dump(mode="json", by_alias=True)
    del wire["policy"]["native_source_section_policy"]
    wire["execution_policy_sha256"] = t._canonical_sha256({"schema": execution.schema_,
        "context_receipt_sha256": execution.context_receipt_sha256, "policy": wire["policy"]})
    wire["events"].append(event.model_dump(mode="json") | {"execution_policy_sha256": wire["execution_policy_sha256"]})
    # Earlier decisions/extensions retain their policy digest too; rewrite only
    # this synthetic candidate so failure isolates the missing capability.
    for row in wire["events"]:
        if "execution_policy_sha256" in row:
            row["execution_policy_sha256"] = wire["execution_policy_sha256"]
    with pytest.raises(ValueError):
        type(execution).model_validate(wire)


def test_plan_finish_prevents_later_navigation(nav_case):
    service, turn, donor, pin = nav_case
    if not hasattr(service, "nav_test_controller"):
        pytest.skip("Play has its native provider lifecycle, no Plan decision")
    case = service.nav_test_controller
    case.turn = turn
    case.redecide("finish_retrieval")
    append_decision(case)
    with pytest.raises(ApplicationStateValidationError):
        persist(service, case.turn, authorization(case.turn, donor, pin))


def test_downgrade_refuses_retained_navigation(nav_case, application_state_dsn):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    service, turn, donor, pin = nav_case
    persist(service, turn, authorization(turn, donor, pin))
    engine = create_engine(application_state_dsn.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError, match="retained native source navigation"):
                    import_module("application_state.migrations.versions.20261022_0053_native_source_navigation").downgrade()
    finally:
        engine.dispose()


def test_migration_roundtrip_preserves_historical_play(application_state_dsn):
    import psycopg
    from alembic import command
    from application_state.cli import alembic_config
    service, sub, turn, provider, raw = prepared_native(application_state_dsn, moment=False)
    turn, _ = append(service, sub, turn, provider, raw)
    def snapshot():
        with psycopg.connect(application_state_dsn) as conn:
            return conn.execute("SELECT graph_context_receipt,graph_context_execution FROM agent.turn WHERE turn_id=%s", (turn.turn_id,)).fetchone()
    before = snapshot()
    command.downgrade(alembic_config(), "20261022_0052")
    assert snapshot() == before
    command.upgrade(alembic_config(), "head")
    assert snapshot() == before
    assert service.list_turns(turn.world_id, turn.conversation_id)[-1].graph_context_execution == turn.graph_context_execution


def test_real_native_verifier_proof_matches_app_wire_contract(core_origin):
    from tests.test_native_source_origin import verify
    proof = verify(core_origin)
    _, scope, _, _ = core_origin
    event = t.NativeSourceNavigationAuthorizedV1(kind="native_source_navigation_authorized_v1",
        event_id=uuid4(), navigation_id=uuid4(), sequence=0, provider_attempt_id=uuid4(),
        context_receipt_sha256="a"*64, execution_policy_sha256="b"*64,
        world_id="managed-test-world", native_world_id=scope.world_id, binding_version=1,
        origin_proof_json=proof.proof_json, origin_proof_sha256=proof.proof_sha256)
    assert event.origin_proof_sha256 == proof.proof_sha256


@pytest.mark.parametrize("target", ["resolution", "evidence"])
def test_foreign_evidence_is_not_admitted_by_rehashed_proof(nav_case, target):
    service, turn, donor, pin = nav_case
    event = authorization(turn, donor, pin)
    proof = json.loads(event.origin_proof_json)
    row = proof["resolution"] if target == "resolution" else proof["resolution"]["evidence"]
    row["evidence_ref_id"] = "foreign-evidence"
    forged = event.model_copy(update={"origin_proof_json": json.dumps(proof),
        "origin_proof_sha256": t._canonical_sha256(proof)})
    with pytest.raises(ApplicationStateValidationError):
        persist(service, turn, forged)
    assert service.list_turns(turn.world_id, turn.conversation_id)[-1].revision == turn.revision


def test_native_revision_cannot_acquire_another_digest(nav_case):
    service, turn, donor, pin = nav_case
    updated, _ = persist(service, turn, authorization(turn, donor, pin))
    event = authorization(updated, donor, pin)
    proof = json.loads(event.origin_proof_json)
    proof["revision"]["content_sha256"] = "e"*64
    changed = t.NativeSourceNavigationAuthorizedV1.model_validate(event.model_dump(mode="json") | {
        "origin_proof_json": json.dumps(proof), "origin_proof_sha256": t._canonical_sha256(proof)})
    with pytest.raises(ApplicationStateValidationError):
        persist(service, updated, changed)
    assert service.list_turns(turn.world_id, turn.conversation_id)[-1].revision == updated.revision
