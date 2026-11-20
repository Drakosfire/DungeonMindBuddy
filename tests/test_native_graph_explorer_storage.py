"""Durable APP-STATE recovery journal tests on the disposable clone fixture."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from application_state.native_graph_explorer import NativeGraphExplorerStore
from application_state.native_graph_explorer.store import canonical_json


def _reserve(
    store, operation_id: str, *, native_world_id: str = "space:synthetic"
) -> None:
    now = datetime.now(UTC)
    store.reserve_operation(
        operation_id=operation_id,
        native_world_id=native_world_id,
        binding_version=1,
        expected_revision_id="rev:synthetic-parent",
        request_json=canonical_json({"kind": "create_object", "name": "Test"}),
        updated_at=now,
    )


def _try_advisory_lock(dsn: str, lock_key: tuple[int, int]) -> bool:
    with psycopg.connect(dsn, autocommit=True) as contender:
        acquired = contender.execute(
            "SELECT pg_try_advisory_lock(%s, %s)", lock_key
        ).fetchone()[0]
        if acquired:
            assert (
                contender.execute(
                    "SELECT pg_advisory_unlock(%s, %s)", lock_key
                ).fetchone()[0]
                is True
            )
        return acquired


def test_journal_round_trip_reopens_and_verifies_receipt_hashes(application_state_dsn):
    operation_id = str(uuid4())
    store = NativeGraphExplorerStore("operator-a", "managed-a")
    with store.atomic():
        _reserve(store, operation_id)
        store.mark_unknown(operation_id, updated_at=datetime.now(UTC))
        store.checkpoint()
        source = canonical_json(
            {"admission_id": "source:exact", "body_sha256": "a" * 64}
        )
        prepared = canonical_json({"schema": "prepared", "identity": operation_id})
        store.mark_prepared(
            operation_id,
            source_admission_id="source:exact",
            source_receipt_json=source,
            parent_revision_id="rev:source-parent",
            prepared_json=prepared,
            updated_at=datetime.now(UTC),
        )
        store.checkpoint()
        committed = canonical_json(
            {
                "publication_id": "publication:exact",
                "parent_revision_id": "rev:source-parent",
                "child_revision_id": "rev:child",
                "graph_sha256": "b" * 64,
                "created_node_id": "ent:receipt-bound",
            }
        )
        store.mark_committed(
            operation_id, committed_json=committed, updated_at=datetime.now(UTC)
        )
    store.close()

    reopened = NativeGraphExplorerStore("operator-a", "managed-a")
    try:
        with reopened.atomic():
            record = reopened.get_operation(operation_id)
        assert record is not None
        assert record["status"] == "committed"
        assert record["source_receipt"]["admission_id"] == "source:exact"
        assert record["prepared"]["identity"] == operation_id
        assert record["committed"]["created_node_id"] == "ent:receipt-bound"
    finally:
        reopened.close()


def test_session_advisory_lock_survives_checkpoint_and_is_world_scoped(
    application_state_dsn,
):
    operation_id = str(uuid4())
    store = NativeGraphExplorerStore("operator-lock", "managed-lock")
    lock_key = store._advisory_key()
    other_scope = NativeGraphExplorerStore("operator-lock", "managed-other")
    other_lock_key = other_scope._advisory_key()
    other_scope.close()
    assert lock_key != other_lock_key
    try:
        with store.atomic():
            _reserve(store, operation_id)
            store.mark_unknown(operation_id, updated_at=datetime.now(UTC))
            store.checkpoint()
            assert _try_advisory_lock(application_state_dsn, lock_key) is False
            assert _try_advisory_lock(application_state_dsn, other_lock_key) is True
        assert _try_advisory_lock(application_state_dsn, lock_key) is True
    finally:
        store.close()


@pytest.mark.parametrize(
    "checkpoint", [False, True], ids=["rollback", "checkpoint-then-rollback"]
)
def test_abort_rolls_back_after_checkpoint_and_releases_session_lock(
    application_state_dsn, checkpoint: bool
):
    operation_id = str(uuid4())
    store = NativeGraphExplorerStore("operator-abort", "managed-abort")
    lock_key = store._advisory_key()
    try:
        with pytest.raises(RuntimeError, match="simulated interrupted operation"):
            with store.atomic():
                _reserve(store, operation_id)
                if checkpoint:
                    store.mark_unknown(operation_id, updated_at=datetime.now(UTC))
                    store.checkpoint()
                    store.mark_prepared(
                        operation_id,
                        source_admission_id="source:after-checkpoint",
                        source_receipt_json=canonical_json(
                            {"admission_id": "source:after-checkpoint"}
                        ),
                        parent_revision_id="rev:source-parent",
                        prepared_json=canonical_json(
                            {"schema": "prepared", "phase": "after-checkpoint"}
                        ),
                        updated_at=datetime.now(UTC),
                    )
                raise RuntimeError("simulated interrupted operation")

        assert _try_advisory_lock(application_state_dsn, lock_key) is True
    finally:
        store.close()

    reopened = NativeGraphExplorerStore("operator-abort", "managed-abort")
    try:
        with reopened.atomic():
            record = reopened.get_operation(operation_id)
        if checkpoint:
            assert record is not None
            assert record["status"] == "unknown"
            assert record["prepared"] is None
        else:
            assert record is None
    finally:
        reopened.close()


def test_checkpoint_requires_an_outermost_locked_transaction(application_state_dsn):
    store = NativeGraphExplorerStore("operator-checkpoint", "managed-checkpoint")
    try:
        with pytest.raises(RuntimeError, match="outermost locked transaction"):
            store.checkpoint()
        with store.atomic():
            with store.atomic():
                with pytest.raises(RuntimeError, match="outermost locked transaction"):
                    store.checkpoint()
    finally:
        store.close()


def test_operation_uuid_isolated_by_principal_and_managed_world(application_state_dsn):
    operation_id = str(uuid4())
    scopes = (
        ("operator-a", "managed-a", "space:a"),
        ("operator-b", "managed-a", "space:a"),
        ("operator-a", "managed-b", "space:b"),
    )
    stores = []
    try:
        for subject, world, native_world in scopes:
            store = NativeGraphExplorerStore(subject, world)
            stores.append(store)
            with store.atomic():
                _reserve(store, operation_id, native_world_id=native_world)
                store.mark_unknown(operation_id, updated_at=datetime.now(UTC))
        for store, (_, _, native_world) in zip(stores, scopes, strict=True):
            with store.atomic():
                record = store.get_operation(operation_id)
            assert record is not None
            assert record["native_world_id"] == native_world
            assert record["status"] == "unknown"
        unrelated = NativeGraphExplorerStore("operator-c", "managed-a")
        try:
            with unrelated.atomic():
                assert unrelated.get_operation(operation_id) is None
        finally:
            unrelated.close()
    finally:
        for store in stores:
            store.close()


@pytest.mark.parametrize(
    ("column", "expected_error"),
    [
        ("request_json", "operation request journal integrity check failed"),
        (
            "source_receipt_json",
            "source_receipt operation journal integrity check failed",
        ),
        ("prepared_json", "prepared operation journal integrity check failed"),
        ("committed_json", "committed operation journal integrity check failed"),
        ("rejected_json", "rejected operation journal integrity check failed"),
    ],
)
def test_corrupted_journal_packet_fails_its_digest_check(
    application_state_dsn, column: str, expected_error: str
):
    operation_id = str(uuid4())
    store = NativeGraphExplorerStore("operator-integrity", "managed-integrity")
    try:
        with store.atomic():
            _reserve(store, operation_id)
            if column != "request_json":
                store.mark_prepared(
                    operation_id,
                    source_admission_id="source:integrity",
                    source_receipt_json=canonical_json(
                        {"admission_id": "source:integrity"}
                    ),
                    parent_revision_id="rev:source-parent",
                    prepared_json=canonical_json(
                        {"schema": "prepared", "identity": operation_id}
                    ),
                    updated_at=datetime.now(UTC),
                )
            if column == "committed_json":
                store.mark_committed(
                    operation_id,
                    committed_json=canonical_json(
                        {"publication_id": "publication:integrity"}
                    ),
                    updated_at=datetime.now(UTC),
                )
            elif column == "rejected_json":
                store.mark_rejected(
                    operation_id,
                    code="integrity_test",
                    error="synthetic rejection",
                    updated_at=datetime.now(UTC),
                )

        with psycopg.connect(application_state_dsn, autocommit=True) as conn:
            conn.execute(
                sql.SQL(
                    "UPDATE application_state.native_graph_explorer_operations "
                    "SET {} = %s WHERE principal_subject = %s "
                    "AND managed_world_id = %s AND operation_id = %s"
                ).format(sql.Identifier(column)),
                (
                    canonical_json({"tampered": True}),
                    "operator-integrity",
                    "managed-integrity",
                    operation_id,
                ),
            )

        with store.atomic():
            with pytest.raises(ValueError, match=expected_error):
                store.get_operation(operation_id)
    finally:
        store.close()


def test_operation_limit_counts_only_selected_scope_and_preserves_journal(
    application_state_dsn,
):
    operation_id = str(uuid4())
    store = NativeGraphExplorerStore("operator-cap", "managed-cap", max_operations=2)
    other_principal = NativeGraphExplorerStore("operator-other", "managed-cap")
    other_world = NativeGraphExplorerStore("operator-cap", "managed-other")
    try:
        with other_principal.atomic():
            _reserve(other_principal, operation_id)
        with other_world.atomic():
            _reserve(other_world, operation_id)
        assert store.operation_count() == 0

        committed_id = str(uuid4())
        rejected_id = str(uuid4())
        with store.atomic():
            _reserve(store, committed_id)
            store.mark_committed(
                committed_id,
                committed_json=canonical_json({"publication_id": "publication:cap"}),
                updated_at=datetime.now(UTC),
            )
        with store.atomic():
            _reserve(store, rejected_id)
            store.mark_rejected(
                rejected_id,
                code="test_rejection",
                error="synthetic rejected operation",
                updated_at=datetime.now(UTC),
            )

        assert store.operation_count() == 2
        with pytest.raises(OverflowError, match="journal is full"):
            with store.atomic():
                _reserve(store, str(uuid4()))

        with store.atomic():
            committed = store.get_operation(committed_id)
            rejected = store.get_operation(rejected_id)
        assert committed is not None and committed["status"] == "committed"
        assert rejected is not None and rejected["status"] == "rejected"
        assert store.operation_count() == 2
    finally:
        store.close()
        other_principal.close()
        other_world.close()


@pytest.mark.parametrize(
    ("column", "invalid_value", "constraint"),
    [
        ("binding_version", 0, "ck_native_graph_explorer_binding_version"),
        ("status", "not-a-status", "ck_native_graph_explorer_operation_status"),
        ("request_sha256", "too-short", "ck_native_graph_explorer_request_digest"),
    ],
)
def test_migrated_journal_rejects_invalid_rows(
    application_state_dsn, column: str, invalid_value, constraint: str
):
    operation_id = str(uuid4())
    store = NativeGraphExplorerStore("operator-ddl", "managed-ddl")
    try:
        with store.atomic():
            _reserve(store, operation_id)
        with psycopg.connect(application_state_dsn, autocommit=True) as conn:
            with pytest.raises(psycopg.errors.CheckViolation) as exc_info:
                conn.execute(
                    sql.SQL(
                        "UPDATE application_state.native_graph_explorer_operations "
                        "SET {} = %s WHERE principal_subject = %s "
                        "AND managed_world_id = %s AND operation_id = %s"
                    ).format(sql.Identifier(column)),
                    (invalid_value, "operator-ddl", "managed-ddl", operation_id),
                )
        assert exc_info.value.diag.constraint_name == constraint
        with store.atomic():
            record = store.get_operation(operation_id)
        assert record is not None and record["status"] == "reserved"
    finally:
        store.close()
