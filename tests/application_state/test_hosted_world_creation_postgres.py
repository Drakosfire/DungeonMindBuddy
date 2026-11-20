"""PostgreSQL ownership boundary for hosted World creation."""

import psycopg
import pytest
from concurrent.futures import ThreadPoolExecutor

from application_state.errors import ApplicationStateConflictError, ApplicationStateError
from application_state.world_catalog.hosted_creation import create_owned_world
from application_state.world_catalog import service as catalog
from application_state.world_catalog.service import create_world


def _enable(dsn, *, owner_world_limit=3, global_world_limit=12, owner_rate_limit=20, global_rate_limit=40):
    with psycopg.connect(dsn) as conn:
        conn.execute("""
            UPDATE workspace.hosted_world_creation_policy
            SET enabled=true, owner_world_limit=%s, global_world_limit=%s,
                owner_rate_limit=%s, global_rate_limit=%s, rate_window_seconds=60
        """, (owner_world_limit, global_world_limit, owner_rate_limit, global_rate_limit))


def test_creation_policy_starts_disabled_and_requires_complete_positive_limits(application_state_dsn):
    with psycopg.connect(application_state_dsn) as conn:
        row = conn.execute(
            "SELECT enabled, owner_world_limit, global_world_limit FROM workspace.hosted_world_creation_policy"
        ).fetchone()
        assert row == (False, None, None)
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.transaction():
                conn.execute("UPDATE workspace.hosted_world_creation_policy SET enabled = true")
        conn.execute("""
            UPDATE workspace.hosted_world_creation_policy
            SET enabled=true, owner_world_limit=3, global_world_limit=12,
                owner_rate_limit=4, global_rate_limit=20, rate_window_seconds=60
        """)
        assert conn.execute("SELECT enabled FROM workspace.hosted_world_creation_policy").fetchone() == (True,)


def test_admission_cannot_reference_an_unregistered_world(application_state_dsn):
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with conn.transaction():
                conn.execute(
                    "INSERT INTO workspace.hosted_world_admission (world_id, creator_subject) VALUES (%s, %s)",
                    ("missing-world", "owner"),
                )


def test_creation_is_atomic_idempotent_and_conflicts_are_charged(application_state_dsn):
    _enable(application_state_dsn)
    args = dict(subject="alice", name="Carnival", request_key="request_key_0001")
    created = create_owned_world(**args)
    assert created.record.owner_subject == "alice"
    assert create_owned_world(**args) == created
    with pytest.raises(ApplicationStateConflictError):
        create_owned_world(**{**args, "name": "Another name"})
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM workspace.hosted_world_creation_attempt").fetchone()[0] == 3
        assert conn.execute("SELECT count(*) FROM workspace.hosted_world_admission").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM workspace.hosted_world_creation_receipt").fetchone()[0] == 1


def test_revoked_receipt_cannot_be_reactivated_and_still_counts_against_quota(application_state_dsn):
    _enable(application_state_dsn, owner_world_limit=1)
    args = dict(subject="alice", name="Carnival", request_key="request_key_0001")
    created = create_owned_world(**args)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE workspace.hosted_world_admission SET revoked_at=now() WHERE world_id=%s", (created.record.world_id,))
    with pytest.raises(ApplicationStateConflictError):
        create_owned_world(**args)
    with pytest.raises(ApplicationStateError) as error:
        create_owned_world(subject="alice", name="Another", request_key="request_key_0002")
    assert error.value.status_code == 429


def test_concurrent_same_key_converges_and_charges_both_attempts(application_state_dsn):
    _enable(application_state_dsn)
    args = dict(subject="alice", name="Carnival", request_key="request_key_0001")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create_owned_world(**args), range(2)))
    assert results[0] == results[1]
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM workspace.hosted_world_creation_attempt").fetchone()[0] == 2
        assert conn.execute("SELECT count(*) FROM workspace.hosted_world_admission").fetchone()[0] == 1


def test_historical_same_name_is_not_adopted(application_state_dsn):
    _enable(application_state_dsn)
    create_world(name="Carnival", owner_subject="alice")
    with pytest.raises(ApplicationStateConflictError):
        create_owned_world(subject="alice", name="Carnival", request_key="request_key_0001")
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM workspace.hosted_world_admission").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM workspace.hosted_world_creation_attempt").fetchone()[0] == 1


def test_retry_denied_after_ownership_change(application_state_dsn):
    _enable(application_state_dsn)
    args = dict(subject="alice", name="Carnival", request_key="request_key_0001")
    created = create_owned_world(**args)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE workspace.managed_world SET owner_subject='bob' WHERE world_id=%s", (created.record.world_id,))
    with pytest.raises(ApplicationStateConflictError):
        create_owned_world(**args)


def test_global_allocation_limit_is_atomic_for_distinct_users(application_state_dsn):
    _enable(application_state_dsn, global_world_limit=1)
    def attempt(subject):
        try:
            return create_owned_world(subject=subject, name="Carnival", request_key="request_key_0001")
        except ApplicationStateError as exc:
            return exc
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["alice", "bob"]))
    assert sum(isinstance(result, ApplicationStateError) and result.status_code == 429 for result in results) == 1
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM workspace.hosted_world_admission").fetchone()[0] == 1


def test_failure_after_world_insert_rolls_back_world_but_retains_rate_charge(application_state_dsn, monkeypatch):
    _enable(application_state_dsn)
    original = catalog._write
    def fail_after_write(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("synthetic interrupted creation")
    monkeypatch.setattr(catalog, "_write", fail_after_write)
    with pytest.raises(RuntimeError, match="synthetic interrupted"):
        create_owned_world(subject="alice", name="Carnival", request_key="request_key_0001")
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM workspace.managed_world").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM workspace.hosted_world_admission").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM workspace.hosted_world_creation_receipt").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM workspace.hosted_world_creation_attempt").fetchone()[0] == 1


def test_global_rate_limit_applies_across_subjects(application_state_dsn):
    _enable(application_state_dsn, global_rate_limit=1)
    create_owned_world(subject="alice", name="Carnival", request_key="request_key_0001")
    with pytest.raises(ApplicationStateError) as error:
        create_owned_world(subject="bob", name="Another", request_key="request_key_0001")
    assert error.value.status_code == 429
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM workspace.hosted_world_admission").fetchone()[0] == 1
