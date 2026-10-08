"""Create a private paired Buddy/Core backup for a reviewed rollout lease.

This helper makes only backups. It does not migrate, stop services, or deploy.
Current scope: Buddy0018/Core0013 preservation for a separately activated
Core0013→0014 operational lease. Never use it as test-data replication authority.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

import psycopg
from psycopg.conninfo import conninfo_to_dict
from dotenv import dotenv_values


STATE = Path("/home/drakosfire/.local/state/dungeonmindbuddy")
RUNTIME = STATE / "runtime"
CONFIG = Path("/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/.env")
BACKUP_ROOT = STATE / "rollout-backups"
SHARED_ENV = CONFIG.parent.parent / ".env.development"
IDENTITY_FILE = STATE / "rollout-candidates/current-main-db-identities.json"
MANAGED_ROOT = Path("/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy")
DMS_ROOT = Path("/home/drakosfire/Projects/DungeonOverMind/DungeonMindServer")
BUDDY_DATABASE_NAME = "dungeonbuddy_application_state"
CORE_DATABASE_NAME = "dungeonmind_cutover_live"
BUDDY_SCHEMA = "20261007_0018"
CORE_SCHEMA = "0013_adopted_withdrawal_v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _private_root() -> Path:
    BACKUP_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    stat = BACKUP_ROOT.stat()
    if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise RuntimeError(
            "backup root must be owned by this user and inaccessible to others"
        )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(tempfile.mkdtemp(prefix=f"current-main-{stamp}-", dir=BACKUP_ROOT))


def _configured_dsn(key: str, database_name: str) -> str:
    raw = dotenv_values(CONFIG).get(key)
    if not isinstance(raw, str) or not raw:
        raise RuntimeError(f"the configured {database_name} DSN is unavailable")
    fields = conninfo_to_dict(raw)
    if fields.get("dbname") != database_name:
        raise RuntimeError(f"the configured database is not {database_name}")
    return raw


def _expected_identities() -> dict[str, dict[str, str]]:
    stat = IDENTITY_FILE.stat()
    if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise RuntimeError("database identity inventory must be owner-only")
    data = json.loads(IDENTITY_FILE.read_text(encoding="utf-8"))
    if set(data) != {"buddy", "core"}:
        raise RuntimeError("database identity inventory must name Buddy and Core")
    for item in data.values():
        if set(item) != {"host", "port", "system_identifier"}:
            raise RuntimeError("database identity inventory has unexpected fields")
        if not all(isinstance(value, str) and value for value in item.values()):
            raise RuntimeError("database identity inventory has invalid fields")
    return data


def _pg_environment(dsn: str) -> dict[str, str]:
    fields = conninfo_to_dict(dsn)
    names = {
        "host": "PGHOST",
        "hostaddr": "PGHOSTADDR",
        "port": "PGPORT",
        "user": "PGUSER",
        "dbname": "PGDATABASE",
        "password": "PGPASSWORD",
        "sslmode": "PGSSLMODE",
        "sslrootcert": "PGSSLROOTCERT",
        "sslcert": "PGSSLCERT",
        "sslkey": "PGSSLKEY",
    }
    unsupported = set(fields) - set(names)
    if unsupported:
        raise RuntimeError(
            f"configured connection uses unsupported libpq fields: {sorted(unsupported)}"
        )
    env = os.environ.copy()
    for key in tuple(env):
        if key.startswith("PG"):
            env.pop(key)
    for key, name in names.items():
        if fields.get(key):
            env[name] = fields[key]
    return env


def _database_preflight(
    dsn: str,
    database_name: str,
    version_table: str,
    expected_schema: str,
    expected_identity: dict[str, str],
) -> tuple[str, int, dict[str, str]]:
    fields = conninfo_to_dict(dsn)
    if (
        fields.get("host") != expected_identity["host"]
        or fields.get("port") != expected_identity["port"]
    ):
        raise RuntimeError(
            "configured database endpoint differs from the reviewed lease"
        )
    with psycopg.connect(dsn, options="-c default_transaction_read_only=on") as conn:
        database = conn.execute("SELECT current_database()").fetchone()[0]
        schema = conn.execute(f"SELECT version_num FROM {version_table}").fetchone()[0]
        version = conn.execute("SHOW server_version_num").fetchone()[0]
        size = conn.execute("SELECT pg_database_size(current_database())").fetchone()[0]
        system_identifier = str(
            conn.execute(
                "SELECT system_identifier FROM pg_control_system()"
            ).fetchone()[0]
        )
    if database != database_name or schema != expected_schema:
        raise RuntimeError(
            "database identity or pre-migration schema differs from the lease"
        )
    if system_identifier != expected_identity["system_identifier"]:
        raise RuntimeError(
            "PostgreSQL cluster identity differs from the reviewed lease"
        )
    if not str(version).startswith("16"):
        raise RuntimeError(
            "PostgreSQL server major differs from the reviewed 16.x backup tool"
        )
    return str(schema), int(size), expected_identity


def _state_subjects() -> tuple[tuple[Path, str], ...]:
    return (
        (STATE / "live-session", "state/live-session"),
        (STATE / "local-operator.env", "state/local-operator.env"),
        (CONFIG, "config/buddy.env"),
        (SHARED_ENV, "config/shared.env.development"),
        (STATE / "local_graph_sessions.json", "state/local_graph_sessions.json"),
        (
            STATE / "runtime-artifact-inventory.json",
            "state/runtime-artifact-inventory.json",
        ),
        (RUNTIME / "out", "runtime/out"),
        (RUNTIME / "corpus", "runtime/corpus"),
        (
            MANAGED_ROOT / "corpus/elderwyld-markdown",
            "managed/corpus/elderwyld-markdown",
        ),
        (
            MANAGED_ROOT / "out/registries/world_containers.json",
            "managed/out/registries/world_containers.json",
        ),
        (DMS_ROOT / ".env.development", "dms/.env.development"),
        (DMS_ROOT / "serviceAccountKey.json", "dms/serviceAccountKey.json"),
    )


def _state_bytes() -> int:
    total = 0
    for source, _ in _state_subjects():
        if not source.exists():
            raise RuntimeError(f"required backup subject is absent: {source}")
        paths = source.rglob("*") if source.is_dir() else (source,)
        for path in paths:
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
    return total


def _archive_state(path: Path) -> int:
    subjects = _state_subjects()
    for source, _ in subjects:
        if not source.exists():
            raise RuntimeError(f"required backup subject is absent: {source}")
    if not (STATE / "live-session").is_dir() or not (RUNTIME / "out").is_dir():
        raise RuntimeError("expected live-session and runtime/out directories")
    with tarfile.open(path, mode="w", dereference=False) as archive:
        for source, name in subjects:
            archive.add(source, arcname=name, recursive=True)
    with tarfile.open(path, mode="r") as archive:
        return len(archive.getmembers())


def _source_environment_snapshot() -> dict[str, dict[str, str | None]]:
    result = {}
    for name, root in (("buddy", RUNTIME), ("dms", DMS_ROOT)):

        def git(*args: str) -> str:
            return subprocess.run(
                ["git", *args], cwd=root, check=True, text=True, capture_output=True
            ).stdout.strip()

        if git("status", "--porcelain"):
            raise RuntimeError(f"{name} source checkout is dirty")
        venv = root / ".venv"
        if not venv.is_dir():
            raise RuntimeError(f"{name} environment is unavailable")
        result[name] = {
            "root": str(root),
            "head": git("rev-parse", "HEAD"),
            "tree": git("rev-parse", "HEAD^{tree}"),
            "branch": git("branch", "--show-current"),
            "venv_link": os.readlink(venv) if venv.is_symlink() else None,
            "venv_resolved": str(venv.resolve()),
            "pyproject_sha256": _sha256(root / "pyproject.toml"),
            "lock_sha256": _sha256(root / "uv.lock"),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="create the private backup set under an activated PRIME lease",
    )
    args = parser.parse_args()
    if not args.execute:
        parser.error("backup writes require --execute under PRIME's activated lease")
    os.umask(0o077)
    identities = _expected_identities()
    buddy_dsn = _configured_dsn(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        BUDDY_DATABASE_NAME,
    )
    core_dsn = _configured_dsn(
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL",
        CORE_DATABASE_NAME,
    )
    buddy_schema, buddy_size, buddy_identity = _database_preflight(
        buddy_dsn,
        BUDDY_DATABASE_NAME,
        "application_state.schema_migrations",
        BUDDY_SCHEMA,
        identities["buddy"],
    )
    core_schema, core_size, core_identity = _database_preflight(
        core_dsn,
        CORE_DATABASE_NAME,
        "dungeonmind.alembic_version",
        CORE_SCHEMA,
        identities["core"],
    )
    version_output = subprocess.run(
        ["/usr/bin/pg_dump", "--version"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    if re.search(r"\b16\.", version_output) is None:
        raise RuntimeError("pg_dump major must match the reviewed PostgreSQL 16 server")
    required_bytes = max(
        256 * 1024 * 1024, 3 * (buddy_size + core_size + _state_bytes())
    )
    if shutil.disk_usage(STATE).free < required_bytes:
        raise RuntimeError(
            "backup destination has insufficient free space for both databases and preserved files"
        )
    source_environment = _source_environment_snapshot()
    destination = _private_root()
    incomplete = destination / "INCOMPLETE"
    incomplete.write_text(
        "Backup is not valid for rollback until manifest is complete.\n"
    )
    buddy_dump = destination / "buddy-application-state.dump"
    core_dump = destination / "dungeonmind-graph-authority.dump"
    state_archive = destination / "buddy-preserved-files.tar"
    inventories: list[Path] = []
    try:
        for dsn, dump in ((buddy_dsn, buddy_dump), (core_dsn, core_dump)):
            subprocess.run(
                ["/usr/bin/pg_dump", "--format=custom", "--file", str(dump)],
                env=_pg_environment(dsn),
                check=True,
            )
            inventory = destination / f"{dump.stem}.inventory.txt"
            with inventory.open("x", encoding="utf-8") as stream:
                subprocess.run(
                    ["/usr/bin/pg_restore", "--list", str(dump)],
                    stdout=stream,
                    check=True,
                )
            inventories.append(inventory)
        archived_entries = _archive_state(state_archive)
        manifest = {
            "schema": "dmb_core_a501_rollout_backup_v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_environment": source_environment,
            "databases": {
                "buddy": {
                    "name": BUDDY_DATABASE_NAME,
                    "schema_before": buddy_schema,
                    "size_bytes_before": buddy_size,
                    "identity": buddy_identity,
                },
                "core": {
                    "name": CORE_DATABASE_NAME,
                    "schema_before": core_schema,
                    "size_bytes_before": core_size,
                    "identity": core_identity,
                },
            },
            "pg_dump_version": version_output,
            "free_space_bytes_required": required_bytes,
            "archived_entries": archived_entries,
            "files": {
                path.name: {"bytes": path.stat().st_size, "sha256": _sha256(path)}
                for path in (buddy_dump, core_dump, state_archive, *inventories)
            },
        }
        with (destination / "manifest.json").open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, sort_keys=True, indent=2)
            stream.write("\n")
        incomplete.unlink()
    except Exception:
        print(f"incomplete_backup_directory {destination}", file=sys.stderr)
        raise
    print("backup_directory", destination)
    print("database_schemas_before", buddy_schema, core_schema)
    print("archived_entries", archived_entries)
    for name, item in manifest["files"].items():
        print(name, item["bytes"], item["sha256"])


if __name__ == "__main__":
    main()
