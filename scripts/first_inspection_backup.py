"""Create a private pre-migration Buddy backup for a reviewed operator lease.

This helper makes only backups. It does not migrate, stop services, or deploy.
Run it only after PRIME activates the first-inspection operational lease.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

import psycopg
from psycopg.conninfo import conninfo_to_dict
from dotenv import dotenv_values


STATE = Path("/home/drakosfire/.local/state/dungeonmindbuddy")
RUNTIME = STATE / "runtime"
CONFIG = Path("/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/.env")
BACKUP_ROOT = STATE / "rollout-backups"
DATABASE_NAME = "dungeonbuddy_application_state"
EXPECTED_SCHEMA = "20261005_0017"


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
        raise RuntimeError("backup root must be owned by this user and inaccessible to others")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(tempfile.mkdtemp(prefix=f"first-inspection-{stamp}-", dir=BACKUP_ROOT))


def _configured_dsn() -> str:
    raw = dotenv_values(CONFIG).get("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL")
    if not isinstance(raw, str) or not raw:
        raise RuntimeError("the configured Buddy application-state DSN is unavailable")
    fields = conninfo_to_dict(raw)
    if fields.get("dbname") != DATABASE_NAME:
        raise RuntimeError("the configured database is not the separate Buddy application-state database")
    return raw


def _pg_environment(dsn: str) -> dict[str, str]:
    fields = conninfo_to_dict(dsn)
    names = {
        "host": "PGHOST", "hostaddr": "PGHOSTADDR", "port": "PGPORT",
        "user": "PGUSER", "dbname": "PGDATABASE", "password": "PGPASSWORD",
        "sslmode": "PGSSLMODE", "sslrootcert": "PGSSLROOTCERT",
        "sslcert": "PGSSLCERT", "sslkey": "PGSSLKEY",
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


def _database_preflight(dsn: str) -> tuple[str, int]:
    with psycopg.connect(dsn, options="-c default_transaction_read_only=on") as conn:
        database = conn.execute("SELECT current_database()").fetchone()[0]
        schema = conn.execute(
            "SELECT version_num FROM application_state.schema_migrations"
        ).fetchone()[0]
        version = conn.execute("SHOW server_version_num").fetchone()[0]
        size = conn.execute("SELECT pg_database_size(current_database())").fetchone()[0]
    if database != DATABASE_NAME or schema != EXPECTED_SCHEMA:
        raise RuntimeError("database identity or pre-migration schema differs from the lease")
    if not str(version).startswith("16"):
        raise RuntimeError("PostgreSQL server major differs from the reviewed 16.x backup tool")
    return str(schema), int(size)


def _archive_state(path: Path) -> int:
    subjects = (
        (STATE / "live-session", "state/live-session"),
        (STATE / "local_graph_sessions.json", "state/local_graph_sessions.json"),
        (STATE / "runtime-artifact-inventory.json", "state/runtime-artifact-inventory.json"),
        (RUNTIME / "out", "runtime/out"),
    )
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute", action="store_true",
        help="create the private backup set under an activated PRIME lease",
    )
    args = parser.parse_args()
    if not args.execute:
        parser.error("backup writes require --execute under PRIME's activated lease")
    os.umask(0o077)
    dsn = _configured_dsn()
    schema, database_size = _database_preflight(dsn)
    version_output = subprocess.run(
        ["/usr/bin/pg_dump", "--version"], check=True,
        text=True, capture_output=True,
    ).stdout.strip()
    if re.search(r"\b16\.", version_output) is None:
        raise RuntimeError("pg_dump major must match the reviewed PostgreSQL 16 server")
    destination = _private_root()
    database_dump = destination / "buddy-application-state.dump"
    state_archive = destination / "buddy-preserved-files.tar"
    inventory = destination / "pg-restore-inventory.txt"
    subprocess.run(
        ["/usr/bin/pg_dump", "--format=custom", "--file", str(database_dump)],
        env=_pg_environment(dsn), check=True,
    )
    with inventory.open("x", encoding="utf-8") as stream:
        subprocess.run(
            ["/usr/bin/pg_restore", "--list", str(database_dump)],
            stdout=stream, check=True,
        )
    archived_entries = _archive_state(state_archive)
    manifest = {
        "schema": "dmb_first_inspection_backup_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "database_name": DATABASE_NAME,
        "database_schema_before": schema,
        "database_size_bytes_before": database_size,
        "pg_dump_version": version_output,
        "archived_entries": archived_entries,
        "files": {
            path.name: {"bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in (database_dump, state_archive, inventory)
        },
    }
    with (destination / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print("backup_directory", destination)
    print("database_schema_before", schema)
    print("archived_entries", archived_entries)
    for name, item in manifest["files"].items():
        print(name, item["bytes"], item["sha256"])


if __name__ == "__main__":
    main()
