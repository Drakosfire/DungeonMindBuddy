"""Real transactional work-store ownership/CAS, independent of native publication."""
from uuid import uuid4
import pytest
from application_state.statement_proposals import service as store
from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError


def test_claim_and_cas_preserve_original(application_state_dsn):
    key = uuid4()
    intent = {"managed_world_id": "world", "campaign_id": "c1"}
    record, fresh = store.claim(key, "owner", intent, {"source": "body"})
    assert fresh
    assert store.claim(key, "owner", intent, {"source": "body"}) == (record, False)
    with pytest.raises(ApplicationStateConflictError):
        store.claim(key, "owner", intent | {"campaign_id": "c2"}, {"source": "body"})
    entered = store.change(record, state="entered", wire="{}")
    with pytest.raises(ApplicationStateConflictError):
        store.change(record, state="failed", failure="loser")
    failed = store.change(entered, state="failed", raw_output="bad", failure="parse_failed")
    assert failed["wire"] == "{}" and failed["raw_output"] == "bad"
    with pytest.raises(ApplicationStateConflictError):
        store.change(failed, state="entered", wire="{}")
    with pytest.raises(ApplicationStateConflictError):
        store.read(key, "other", "world")


def test_invalid_stored_wire_fails_closed(application_state_dsn):
    from application_state.unit_of_work import unit_of_work
    key = uuid4()
    record, _ = store.claim(key, "owner", {"managed_world_id": "world"}, {})
    store.change(record, state="entered", wire="original")
    with unit_of_work(application_state_dsn) as conn:
        conn.execute("UPDATE ingest.statement_proposal_operation SET payload=jsonb_set(payload,'{wire}','\"altered\"') WHERE operation_id=%s", (key,))
    with pytest.raises(ApplicationStateIntegrityError):
        store.read(key, "owner", "world")


def test_simultaneous_claims_dispatch_only_once(application_state_dsn):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    gate = Barrier(2)
    key = uuid4()
    def claim():
        gate.wait()
        return store.claim(key, "owner", {"managed_world_id": "world"}, {"source": "body"})
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: claim(), range(2)))
    assert sorted(fresh for _, fresh in results) == [False, True]
    assert results[0][0] == results[1][0]
