from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
import os
import subprocess
import sys
import uuid
from contextlib import closing
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from psycopg.rows import dict_row

from application_state.engine import connect
from application_state.index_graph.sessions import (
    IndexGraphSessionError,
    create_session,
    lookup_session,
)
from application_state.index_graph.store import IndexGraphStore
from apps.live_control_server.native_graph_demo import NativeGraphDemoService
from dungeonmind.infrastructure.memory.vnext_sources import (
    InMemoryNativeSourceEvidenceRepository,
)


def _request(graph: dict[str, Any], name: str) -> dict[str, str]:
    return {
        "operation_id": str(uuid.uuid4()),
        "expected_revision_id": graph["revision_id"],
        "kind": "create_object",
        "name": name,
        "object_kind": "person",
    }


def _service(repository, session_id: str, allocation_id: str) -> NativeGraphDemoService:
    return NativeGraphDemoService(
        repository,
        storage_label="postgres",
        store=IndexGraphStore(session_id, allocation_id),
        allocation_id=allocation_id,
    )


def _fresh_process_status(
    session_id: str, allocation_id: str, operation_id: str
) -> str:
    code = "\n".join(
        (
            "import sys",
            "from application_state.index_graph.store import IndexGraphStore",
            "store = IndexGraphStore(sys.argv[1], sys.argv[2])",
            "try:",
            "    with store.atomic():",
            "        record = store.get_operation(sys.argv[3])",
            "        print('missing' if record is None else record['status'])",
            "finally:",
            "    store.close()",
        )
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = ".:src"
    for name in (
        "PGHOST",
        "PGPORT",
        "PGDATABASE",
        "PGUSER",
        "PGPASSWORD",
        "PGSSLMODE",
        "PGOPTIONS",
        "PGSERVICE",
        "PGSERVICEFILE",
        "PGPASSFILE",
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL",
        "DUNGEONMIND_DATABASE_URL",
    ):
        env.pop(name, None)
    result = subprocess.run(
        [sys.executable, "-c", code, session_id, allocation_id, operation_id],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError("fresh-process APP-STATE journal read failed")
    return result.stdout.strip()


def test_credentials_are_hashed_sessions_are_bounded_and_expiry_retains_binding(
    application_state_dsn: str,
) -> None:
    credential, session = create_session()
    second_credential, second = create_session()
    assert credential != second_credential
    assert session.session_id != second.session_id
    assert session.allocation_id != second.allocation_id
    assert lookup_session(credential) == session

    with (
        closing(connect(application_state_dsn)) as connection,
        connection.transaction(),
    ):
        connection.row_factory = dict_row
        row = connection.execute(
            "SELECT credential_hash, allocation_id FROM application_state.index_graph_sessions "
            "WHERE session_id = %s::uuid",
            (session.session_id,),
        ).fetchone()
        assert (
            bytes(row["credential_hash"])
            == hashlib.sha256(credential.encode("ascii")).digest()
        )
        assert credential.encode("ascii") not in bytes(row["credential_hash"])
        assert row["allocation_id"] == session.allocation_id
        connection.execute(
            "UPDATE application_state.index_graph_sessions SET expires_at = %s "
            "WHERE session_id = %s::uuid",
            (datetime.now(UTC) - timedelta(seconds=1), session.session_id),
        )

    with pytest.raises(IndexGraphSessionError) as expired:
        lookup_session(credential)
    assert expired.value.code == "session_expired"
    with closing(connect(application_state_dsn)) as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM application_state.index_graph_sessions "
                "WHERE session_id = %s::uuid",
                (session.session_id,),
            ).fetchone()[0]
            == 1
        )


def test_session_advisory_lock_survives_journal_checkpoint(
    application_state_dsn: str,
) -> None:
    _credential, session = create_session()
    store = IndexGraphStore(session.session_id, session.allocation_id)
    verifier = connect(application_state_dsn)
    verifier.autocommit = True
    verifier.row_factory = dict_row
    key = store._advisory_key()
    try:
        with store.atomic():
            store.set_metadata("checkpoint", "durable")
            with store.checkpoint():
                pass
            locked = verifier.execute(
                "SELECT pg_try_advisory_lock(%s, %s) AS acquired", key
            ).fetchone()["acquired"]
            assert locked is False
        acquired_after_release = verifier.execute(
            "SELECT pg_try_advisory_lock(%s, %s) AS acquired", key
        ).fetchone()["acquired"]
        assert acquired_after_release is True
        verifier.execute("SELECT pg_advisory_unlock(%s, %s)", key)
    finally:
        store.close()
        verifier.close()

    restarted = IndexGraphStore(session.session_id, session.allocation_id)
    try:
        with restarted.atomic():
            assert restarted.get_metadata("checkpoint") == "durable"
    finally:
        restarted.close()


def test_operation_quota_counts_reservations_in_the_session_store(
    application_state_dsn: str,
) -> None:
    _credential, session = create_session()
    store = IndexGraphStore(session.session_id, session.allocation_id, max_operations=1)
    try:
        with store.atomic():
            store.reserve_operation(
                operation_id=str(uuid.uuid4()),
                request_json='{"kind":"create_object"}',
                parent_revision_id="revision:test",
                updated_at="test",
            )
            assert store.operation_count() == 1
            with pytest.raises(OverflowError):
                store.reserve_operation(
                    operation_id=str(uuid.uuid4()),
                    request_json='{"kind":"connect"}',
                    parent_revision_id="revision:test",
                    updated_at="test",
                )
    finally:
        store.close()


def test_concurrent_session_bootstrap_assigns_unique_guest_allocations(
    application_state_dsn: str,
) -> None:
    with ThreadPoolExecutor(max_workers=6) as pool:
        sessions = list(pool.map(lambda _index: create_session(), range(6)))
    credentials = [credential for credential, _session in sessions]
    records = [session for _credential, session in sessions]
    assert len(set(credentials)) == len(credentials)
    assert len({record.session_id for record in records}) == len(records)
    assert len({record.allocation_id for record in records}) == len(records)


def test_concurrent_prepare_and_confirm_are_serialized_per_guest(
    application_state_dsn: str,
) -> None:
    _credential, session = create_session()
    repository = InMemoryNativeSourceEvidenceRepository()
    first = _service(repository, session.session_id, session.allocation_id)
    second = _service(repository, session.session_id, session.allocation_id)
    try:
        graph = first.graph()
        request = _request(graph, "Seli")
        with ThreadPoolExecutor(max_workers=2) as pool:
            prepared_results = list(
                pool.map(lambda service: service.prepare(request), (first, second))
            )
        assert [result["status"] for result in prepared_results] == [
            "prepared",
            "prepared",
        ]
        with ThreadPoolExecutor(max_workers=2) as pool:
            confirmed_results = list(
                pool.map(
                    lambda service: service.confirm(request["operation_id"]),
                    (first, second),
                )
            )
        assert [result["status"] for result in confirmed_results] == [
            "committed",
            "committed",
        ]
        final = first.graph()
        assert len([node for node in final["nodes"] if node["name"] == "Seli"]) == 1
        source_id = "native-graph-demo:operation-source:" + request[
            "operation_id"
        ].replace("-", "")
        assert (
            repository.get_native_source_admission_receipt(graph["world_id"], source_id)
            is not None
        )
    finally:
        first.close()
        second.close()


def test_native_graph_restart_replays_and_unknown_state_stays_unknown(
    application_state_dsn: str,
) -> None:
    _credential, session = create_session()
    repository = InMemoryNativeSourceEvidenceRepository()
    service = _service(repository, session.session_id, session.allocation_id)
    try:
        graph = service.graph()
        create = _request(graph, "Ari")
        prepared = service.prepare(create)
        assert prepared["status"] == "prepared"
        journal_head = service.graph()["revision_id"]
        assert (
            _fresh_process_status(
                session.session_id, session.allocation_id, create["operation_id"]
            )
            == "prepared"
        )
    finally:
        service.close()

    restarted = _service(repository, session.session_id, session.allocation_id)
    try:
        assert restarted.graph()["revision_id"] == journal_head
        assert restarted.operation(create["operation_id"])["status"] == "prepared"
        committed = restarted.confirm(create["operation_id"])
        assert committed["status"] == "committed"
        committed_revision = committed["graph"]["revision_id"]
    finally:
        restarted.close()

    replay = _service(repository, session.session_id, session.allocation_id)
    try:
        assert replay.operation(create["operation_id"])["status"] == "committed"
        assert (
            replay.confirm(create["operation_id"])["graph"]["revision_id"]
            == committed_revision
        )
        next_request = _request(replay.graph(), "Bex")
        assert replay.prepare(next_request)["status"] == "prepared"

        class ProcessStopped(BaseException):
            pass

        class CrashAfterUnknownCheckpoint:
            def commit_prepared_change(self, *_args: Any, **_kwargs: Any) -> Any:
                raise ProcessStopped()

        replay._runtime = lambda **_kwargs: CrashAfterUnknownCheckpoint()
        with pytest.raises(ProcessStopped):
            replay.confirm(next_request["operation_id"])
        record = replay._store.get_operation(next_request["operation_id"])
        assert record is not None and record["status"] == "unknown"
        assert (
            _fresh_process_status(
                session.session_id,
                session.allocation_id,
                next_request["operation_id"],
            )
            == "unknown"
        )
    finally:
        replay.close()

    recovery = _service(repository, session.session_id, session.allocation_id)
    try:
        recovery._runtime = lambda **_kwargs: pytest.fail(
            "an unknown native outcome must not be redispatched"
        )
        assert recovery.operation(next_request["operation_id"])["status"] == "unknown"
        assert recovery.confirm(next_request["operation_id"])["status"] == "unknown"
        assert (
            len([node for node in recovery.graph()["nodes"] if node["name"] == "Bex"])
            == 0
        )
    finally:
        recovery.close()
