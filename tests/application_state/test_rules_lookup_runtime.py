"""Actual claim locks, concurrent cache reuse and commit-before-delivery."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from threading import Barrier, Event, Lock
from time import monotonic

import psycopg
from psycopg.types.json import Jsonb
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_types import RulesScopeV1
from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError, ApplicationStateValidationError
from apps.live_control_server.services import rules_lookup as reader
from apps.live_control_server.services import rules_lookup_broker as broker
from tests.application_state.test_rules_authority_store import admitted


def ready():
    turn, original = admitted()
    data = original.model_dump(mode="json", by_alias=True)
    data.update(ruleset_id=broker.RULESET, corpus_sha256=reader.SEED_DIGEST)
    scope = RulesScopeV1.model_validate_json(json.dumps(data))
    service = AgentConversationService()
    record = service.begin_rules_execution(scope, expected_turn_revision=turn.revision)
    return service, turn, scope, record


def args():
    return broker.LookupRulesArguments(question="Can I end my move in an occupied space?", ruleset_id=broker.RULESET)


def authorize(service, turn, scope, record, call_id):
    event = broker.prepare_authorization(record.execution, call_id, args())
    return service.authorize_rules_lookup(scope, expected_turn_revision=turn.revision,
        expected_ledger_revision=record.revision, event=event)


def deliver(service, turn, scope, call_id, local_reader=None):
    return service.execute_rules_lookup(scope, expected_turn_revision=turn.revision,
        call_id=call_id, local_reader=local_reader or (lambda current: broker.prepare_lookup(current, call_id, args())))


def stored(dsn, turn):
    with psycopg.connect(dsn) as conn:
        return conn.execute("SELECT revision,payload FROM agent.turn_rules_execution WHERE turn_id=%s", (turn.turn_id,)).fetchone()


def test_commit_precedes_delivery_and_exact_replay_does_not_read_or_count(application_state_dsn, monkeypatch):
    service, turn, scope, record = ready()
    record = authorize(service, turn, scope, record, "call:1")
    reads = []
    actual = reader.query_rules
    def query(*a, **kw):
        reads.append(1)
        return actual(*a, **kw)
    monkeypatch.setattr(reader, "query_rules", query)
    result = deliver(service, turn, scope, "call:1")
    # A separate connection sees the sealed packet immediately after return.
    revision, payload = stored(application_state_dsn, turn)
    assert revision == result.record.revision and payload["events"][-1]["packet_sha256"] == sha256(result.prepared.raw_output.encode()).hexdigest()
    replay = deliver(service, turn, scope, "call:1", lambda _: pytest.fail("replay invoked reader"))
    assert replay.replayed and not result.replayed and replay.prepared.raw_output == result.prepared.raw_output
    assert replay.prepared.new_supports == () and len(reads) == 1
    assert stored(application_state_dsn, turn) == (revision, payload)


@pytest.mark.parametrize("same_call", [False, True])
def test_concurrent_calls_reload_and_read_source_once(application_state_dsn, monkeypatch, same_call):
    service, turn, scope, record = ready()
    record = authorize(service, turn, scope, record, "call:1")
    if not same_call:
        record = authorize(service, turn, scope, record, "call:2")
    call_ids = ("call:1", "call:1" if same_call else "call:2")
    start = Barrier(3)
    entered, release = Event(), Event()
    reads, guard = [], Lock()
    actual = reader.query_rules
    def query(*a, **kw):
        with guard:
            reads.append(1)
        entered.set()
        assert release.wait(10), "test did not release first local read"
        return actual(*a, **kw)
    monkeypatch.setattr(reader, "query_rules", query)
    def run(call_id):
        start.wait(10)
        return deliver(service, turn, scope, call_id)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, cid) for cid in call_ids]
        start.wait(10)
        assert entered.wait(10)
        # Prove a second real connection is waiting on the owning row while
        # the first local read is held; a scheduling coincidence is not enough.
        waiting = False
        deadline = monotonic() + 5
        try:
            with psycopg.connect(application_state_dsn, autocommit=True) as conn:
                while monotonic() < deadline:
                    waiting = bool(conn.execute("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE '%%agent.turn%%')").fetchone()[0])
                    if waiting:
                        break
                    Event().wait(0.01)
        finally:
            release.set()
        assert waiting, "second lookup never exercised the actual owning row lock"
        results = [f.result(timeout=10) for f in futures]
    assert reads == [1]
    refs = [r.prepared.observation.support_refs for r in results]
    assert refs[0] == refs[1]
    _, payload = stored(application_state_dsn, turn)
    assert payload["budget_use"]["calls"] == (1 if same_call else 2) and payload["budget_use"]["distinct_questions"] == 1
    assert len(payload["supports"]) == 1
    assert sum(r.replayed for r in results) == (1 if same_call else 0)
    assert payload["budget_use"]["presentation_utf8"] == sum(len(r.prepared.raw_output.encode()) for r in results if not r.replayed)
    if same_call:
        assert results[0].prepared.raw_output == results[1].prepared.raw_output
        assert sum(e["kind"] == "query_observed" for e in payload["events"]) == 1


def test_reader_failure_rolls_back_observation_without_returning_packet(application_state_dsn):
    service, turn, scope, record = ready()
    record = authorize(service, turn, scope, record, "call:1")
    before = stored(application_state_dsn, turn)
    def fail(current):
        broker.prepare_lookup(current, "call:1", args())
        raise RuntimeError("local read failed before sealing")
    with pytest.raises(RuntimeError, match="before sealing"):
        deliver(service, turn, scope, "call:1", fail)
    assert stored(application_state_dsn, turn) == before
    assert deliver(service, turn, scope, "call:1").prepared.observation.status == "evidence"


def test_changed_callback_packet_cannot_be_delivered_or_persisted(application_state_dsn):
    service, turn, scope, record = ready()
    record = authorize(service, turn, scope, record, "call:1")
    before = stored(application_state_dsn, turn)
    def corrupt(current):
        good = broker.prepare_lookup(current, "call:1", args())
        return good.model_copy(update={"raw_output": good.raw_output + " "})
    with pytest.raises(ApplicationStateValidationError):
        deliver(service, turn, scope, "call:1", corrupt)
    assert stored(application_state_dsn, turn) == before


def test_expired_claim_denies_reader_and_preserves_authorization(application_state_dsn):
    service, turn, scope, record = ready()
    record = authorize(service, turn, scope, record, "call:1")
    before = stored(application_state_dsn, turn)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s", (turn.turn_id,))
    with pytest.raises(ApplicationStateConflictError, match="expired"):
        deliver(service, turn, scope, "call:1", lambda _: pytest.fail("expired claim read source"))
    assert stored(application_state_dsn, turn) == before


def test_claim_expiring_during_local_read_rolls_back_and_returns_no_packet(application_state_dsn):
    service, turn, scope, record = ready()
    record = authorize(service, turn, scope, record, "call:1")
    before = stored(application_state_dsn, turn)
    # The parent lock intentionally protects the row. Move expiry within the
    # owning transaction using a trusted fixture wrapper, then verify the store
    # rechecks wall-clock time before its append (not only before callback).
    from application_state.agent_conversation.rules_authority_runtime import execute_local_lookup_locked
    with pytest.raises(ApplicationStateConflictError, match="expired"):
        with psycopg.connect(application_state_dsn) as conn:
            def expire(current):
                prepared = broker.prepare_lookup(current, "call:1", args())
                conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s", (turn.turn_id,))
                return prepared
            execute_local_lookup_locked(conn, scope, expected_turn_revision=turn.revision,
                call_id="call:1", local_reader=expire)
    assert stored(application_state_dsn, turn) == before


def test_unsealed_call_and_changed_scope_fail_before_read(application_state_dsn):
    service, turn, scope, record = ready()
    with pytest.raises(ApplicationStateValidationError, match="authorization"):
        deliver(service, turn, scope, "call:1", lambda _: pytest.fail("unsealed call read source"))
    data = scope.model_dump(mode="json", by_alias=True)
    data["authorization_id"] = "00000000-0000-0000-0000-000000000001"
    changed = RulesScopeV1.model_validate_json(json.dumps(data))
    with pytest.raises(ApplicationStateConflictError, match="scope"):
        deliver(service, turn, changed, "call:1", lambda _: pytest.fail("changed scope read source"))


def test_noncanonical_historical_packet_is_integrity_failure_not_reinterpretation(application_state_dsn):
    service, turn, scope, record = ready()
    record = authorize(service, turn, scope, record, "call:1")
    result = deliver(service, turn, scope, "call:1")
    _, payload = stored(application_state_dsn, turn)
    padded = result.prepared.raw_output + " "
    payload["events"][-1].update(packet_sha256=sha256(padded.encode()).hexdigest(), presentation_utf8=len(padded.encode()))
    payload["budget_use"]["presentation_utf8"] += 1
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE agent.turn_rules_execution SET payload=%s WHERE turn_id=%s", (Jsonb(payload), turn.turn_id))
    before = stored(application_state_dsn, turn)
    with pytest.raises(ApplicationStateIntegrityError, match="canonical"):
        deliver(service, turn, scope, "call:1", lambda _: pytest.fail("corrupt replay read source"))
    assert stored(application_state_dsn, turn) == before


def test_deferred_commit_failure_returns_no_delivery_and_rolls_back(application_state_dsn):
    service, turn, scope, record = ready()
    record = authorize(service, turn, scope, record, "call:1")
    before = stored(application_state_dsn, turn)
    # Real PostgreSQL failure at COMMIT, after the packet was prepared/sealed.
    # The fixture database alone owns this temporary deferred constraint.
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("""CREATE FUNCTION public.reject_rules_delivery_commit() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'fixture rejects Rules commit'; END $$""")
        conn.execute("""CREATE CONSTRAINT TRIGGER reject_rules_delivery_commit
        AFTER UPDATE ON agent.turn_rules_execution DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION public.reject_rules_delivery_commit()""")
    with pytest.raises(psycopg.errors.RaiseException, match="rejects Rules commit"):
        deliver(service, turn, scope, "call:1")
    assert stored(application_state_dsn, turn) == before


def test_provider_port_requires_exact_actual_request_before_dispatch(application_state_dsn):
    from uuid import uuid4
    from application_state.agent_conversation.rules_authority_events import (
        RulesProviderAuthorizedV1, RulesProviderIncludedV1, RulesProviderOutcomeV1, RulesOutputRefV1,
    )
    service, turn, scope, record = ready()
    record = authorize(service, turn, scope, record, "call:1")
    delivered = deliver(service, turn, scope, "call:1")
    record = delivered.record
    raw = json.dumps(dict(input=[dict(type="function_call", call_id="call:1", name="lookup_rules",
        arguments=args().model_dump_json()), dict(type="function_call_output", call_id="call:1",
        output=delivered.prepared.raw_output)]))
    producer = uuid4()
    fields = dict(provider_attempt_id=producer, request_envelope_sha256=sha256(raw.encode()).hexdigest(),
        matched_outputs=(RulesOutputRefV1(call_id="call:1", packet_sha256=delivered.prepared.observation.packet_sha256),))
    auth = RulesProviderAuthorizedV1(kind="provider_authorized", event_id=uuid4(), sequence=len(record.execution.events),
        execution_id=scope.execution_id, declared_support_refs=delivered.prepared.observation.support_refs, **fields)
    before = stored(application_state_dsn, turn)
    with pytest.raises(ApplicationStateValidationError):
        service.append_rules_provider_event(scope, expected_turn_revision=turn.revision,
            expected_ledger_revision=record.revision, event=auth, prepared_request_json=raw + " ")
    assert stored(application_state_dsn, turn) == before
    record = service.append_rules_provider_event(scope, expected_turn_revision=turn.revision,
        expected_ledger_revision=record.revision, event=auth, prepared_request_json=raw)
    included = RulesProviderIncludedV1(kind="provider_included", event_id=uuid4(), sequence=len(record.execution.events),
        execution_id=scope.execution_id, support_refs=delivered.prepared.observation.support_refs, **fields)
    record = service.append_rules_provider_event(scope, expected_turn_revision=turn.revision,
        expected_ledger_revision=record.revision, event=included, prepared_request_json=raw)
    outcome = RulesProviderOutcomeV1(kind="provider_outcome", event_id=uuid4(), sequence=len(record.execution.events),
        execution_id=scope.execution_id, provider_attempt_id=producer,
        request_envelope_sha256=fields["request_envelope_sha256"], status="answered")
    record = service.append_rules_provider_event(scope, expected_turn_revision=turn.revision,
        expected_ledger_revision=record.revision, event=outcome)
    revision, payload = stored(application_state_dsn, turn)
    assert revision == record.revision and payload["budget_use"]["provider_requests"] == 1
    assert [e["kind"] for e in payload["events"]][-3:] == ["provider_authorized", "provider_included", "provider_outcome"]
