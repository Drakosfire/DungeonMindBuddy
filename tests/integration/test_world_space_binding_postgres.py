"""End-to-end World binding witness against disposable MIND PostgreSQL."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from dungeonmind.infrastructure.postgres.database import PostgresDatabase
from dungeonmind.infrastructure.postgres.vnext_knowledge import (
    PostgresKnowledgeRevisionRepository,
)

from apps.live_control_server.services.world_container_registry import (
    create_world_container,
    get_world_container,
    world_containers_path,
)
from apps.live_control_server.services.world_space_binding import provision_world_space

pytestmark = pytest.mark.integration
MIND_PIN = "619329c2c8586572ffd04558a79b3555c2ca3764"


def _database_name(dsn: str) -> str:
    return urlsplit(dsn).path.removeprefix("/")


def _database_url(admin_dsn: str, name: str) -> str:
    parsed = urlsplit(admin_dsn)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise ValueError("J3 requires a PostgreSQL admin DSN with a host")
    if parsed.query or parsed.fragment:
        raise ValueError("J3 admin DSN must not contain routing overrides")
    return urlunsplit((parsed.scheme, parsed.netloc, f"/{name}", "", ""))


def _check_safe_admin(admin: str) -> None:
    parsed = urlsplit(admin)
    live_dsns = {
        os.getenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "").strip(),
        os.getenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", "").strip(),
    }
    if not admin or admin in live_dsns or parsed.query or parsed.fragment:
        raise ValueError("J3 admin DSN is missing or aliases a configured live authority")
    if _database_name(admin) not in {"postgres", "template1"}:
        raise ValueError("J3 admin DSN must target postgres or template1")


@pytest.fixture(scope="module")
def mind_database() -> Iterator[str]:
    admin = os.getenv("DMB_J3_PG_ADMIN_DSN", "").strip()
    raw_source = os.getenv("DMB_J3_DUNGEONMIND_SOURCE", "").strip()
    if not admin or not raw_source:
        pytest.skip("explicit J3 disposable PostgreSQL authority and MIND source required")
    _check_safe_admin(admin)
    source = Path(raw_source).resolve()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, check=True, capture_output=True, text=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "alembic.ini", "migrations"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if (
        head != MIND_PIN
        or dirty
        or not (source / "alembic.ini").is_file()
        or not (source / "migrations").is_dir()
    ):
        raise ValueError("J3 migration source is not a clean checkout at the accepted MIND #96 pin")

    name = f"dmb_j3_test_{uuid.uuid4().hex}"
    dsn = _database_url(admin, name)
    with psycopg.connect(admin, autocommit=True) as connection:
        connection.execute(f'CREATE DATABASE "{name}"')
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=source,
            env={**os.environ, "DUNGEONMIND_DATABASE_URL": dsn},
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            details = f"{result.stdout[-2000:]}\n{result.stderr[-2000:]}".replace(
                dsn, "<disposable DSN redacted>"
            )
            pytest.fail(f"MIND #96 migrations failed ({result.returncode}):\n{details}")
        yield dsn
    finally:
        with psycopg.connect(admin, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname=%s AND pid<>pg_backend_pid()",
                (name,),
            )
            connection.execute(f'DROP DATABASE IF EXISTS "{name}"')


def test_persisted_world_binding_is_empty_mind_genesis_after_process_restart(
    mind_database: str, tmp_path: Path
) -> None:
    world = create_world_container(tmp_path, name="Disposable Genesis")
    active = provision_world_space(tmp_path, world.world_id, database_url=mind_database)
    assert active.space_binding_status == "active"
    assert active.space_binding_version == 1
    assert active.space_id
    assert active.space_id != world.world_id

    repo = PostgresKnowledgeRevisionRepository(PostgresDatabase(mind_database))
    head = repo.get_head(active.space_id)
    assert head is not None
    revision = repo.get_revision(active.space_id, head.head_revision_id)
    assert revision is not None
    assert revision.revision.parent_revision_id is None
    assert revision.graph_payload == {
        "entities": [],
        "assertions": [],
        "aliases": [],
        "evidence": [],
    }

    # A fresh interpreter reopens both authorities and verifies the same
    # ACTIVE binding and native empty genesis. No Python-side object is reused.
    env = {
        **os.environ,
        "DMB_J3_REGISTRY_ROOT": str(tmp_path),
        "DMB_J3_WORLD_ID": world.world_id,
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL": mind_database,
    }
    script = """
import json, os
from pathlib import Path
from apps.live_control_server.services.world_container_registry import get_world_container
from dungeonmind.infrastructure.postgres.database import PostgresDatabase
from dungeonmind.infrastructure.postgres.vnext_knowledge import PostgresKnowledgeRevisionRepository
r = get_world_container(Path(os.environ['DMB_J3_REGISTRY_ROOT']), os.environ['DMB_J3_WORLD_ID'])
repo = PostgresKnowledgeRevisionRepository(PostgresDatabase(os.environ['DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL']))
h = repo.get_head(r.space_id)
rev = repo.get_revision(r.space_id, h.head_revision_id)
print(json.dumps({'status': r.space_binding_status, 'version': r.space_binding_version, 'space_id': r.space_id, 'allocation_id': r.space_allocation_id, 'receipt': r.space_provisioning_receipt, 'parent': rev.revision.parent_revision_id, 'graph_payload': rev.graph_payload}, sort_keys=True))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        output = f"{result.stdout}\n{result.stderr}".replace(
            mind_database, "<disposable DSN redacted>"
        )
        pytest.fail(f"fresh-process binding read failed ({result.returncode}):\n{output}")
    reconstructed = json.loads(result.stdout)
    assert reconstructed["status"] == "active"
    assert reconstructed["version"] == 1
    assert reconstructed["space_id"] == active.space_id
    assert reconstructed["allocation_id"] == active.space_allocation_id
    assert reconstructed["receipt"] == active.space_provisioning_receipt
    assert reconstructed["parent"] is None
    assert reconstructed["graph_payload"] == revision.graph_payload
    assert get_world_container(tmp_path, world.world_id).space_id == active.space_id
    assert world_containers_path(tmp_path).is_file()
