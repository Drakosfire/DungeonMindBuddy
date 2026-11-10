#!/usr/bin/env python3
"""Run only a task-owned native DungeonMind demo, never the normal Buddy server.

No DSN option or ambient database fallback exists. PostgreSQL is private to the
specified data directory and accepts Unix-socket peer authentication only.
"""

from __future__ import annotations

import argparse
from contextlib import closing
import fcntl
import hashlib
import pwd
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
from urllib.parse import quote

CORE_PIN = "430c1a6db631d097dfa0a273f8933067f708bc56"
WK_PIN = "ef9c50f2d6aa89a35e9408f83fc4d0ba47825ca2"
DATABASE = "dmb_native_graph_demo"
ROOT = Path(__file__).resolve().parents[1]


class LaunchBlocked(RuntimeError):
    pass


def postgres_tools(directory: Path | None = None):
    result = {}
    for name in ("initdb", "pg_ctl"):
        value = str(directory / name) if directory else shutil.which(name)
        if not value or not Path(value).is_file() or not os.access(value, os.X_OK):
            raise LaunchBlocked(
                "Dedicated PostgreSQL server tools are unavailable. Provide an authorized PostgreSQL installation with pgvector; no Docker, remote database or production fallback will be used."
            )
        result[name] = value
    return result


def verified_source(source: Path):
    source = source.resolve(strict=True)
    git_environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(Path.home()),
        "LANG": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True, env=git_environment
    ).strip()
    if sha != CORE_PIN:
        raise LaunchBlocked(
            "DungeonMind migrations must be the exact pinned source checkout."
        )
    entries = subprocess.check_output(
        ["git", "ls-tree", "-rz", CORE_PIN, "--", "migrations", "alembic.ini"],
        cwd=source,
        env=git_environment,
    )
    expected = {}
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        metadata, encoded_path = entry.split(b"\t", 1)
        mode, kind, digest = metadata.split()
        if kind != b"blob" or mode not in (b"100644", b"100755"):
            raise LaunchBlocked("Migration inputs must be ordinary pinned files.")
        expected[encoded_path.decode()] = digest.decode()
    if (source / "migrations").is_symlink():
        raise LaunchBlocked("Migration inputs cannot contain symlinks.")
    actual = {"alembic.ini"}
    for path in (source / "migrations").rglob("*"):
        if path.is_symlink():
            raise LaunchBlocked("Migration inputs cannot contain symlinks.")
        if path.is_file():
            actual.add(path.relative_to(source).as_posix())
    if not expected or actual != set(expected):
        raise LaunchBlocked(
            "Migration file inventory differs from the pinned source (including ignored files)."
        )
    for relative, digest in expected.items():
        path = source / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size > 2 * 1024 * 1024
        ):
            raise LaunchBlocked("Migration input is missing, linked or oversized.")
        body = path.read_bytes()
        if (
            hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
            != digest
        ):
            raise LaunchBlocked(
                "Migration input bytes differ from the exact source pin."
            )
    return source


def verified_dependencies():
    from importlib.metadata import distribution

    for name, pin in (("dungeonmind", CORE_PIN), ("worldkeeper", WK_PIN)):
        raw = distribution(name).read_text("direct_url.json")
        if raw is None or json.loads(raw).get("vcs_info", {}).get("commit_id") != pin:
            raise LaunchBlocked(
                f"Installed {name} must match Buddy's exact native source pin."
            )


def owned_state(path: Path):
    if path.is_symlink():
        raise LaunchBlocked("The demo state directory must not be a symlink.")
    path = path.absolute()
    if not path.exists():
        path.mkdir(mode=0o700, parents=False)
    stat = path.stat()
    if not path.is_dir() or stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise LaunchBlocked(
            "The demo state directory must be privately owned by this user."
        )
    path = path.resolve(strict=True)
    marker = path / "native-demo-owner.json"
    expected = {
        "version": 1,
        "uid": os.getuid(),
        "data_directory": str(path / "pgdata"),
        "database": DATABASE,
    }
    if not marker.exists():
        if any(path.iterdir()):
            raise LaunchBlocked(
                "Refusing an existing unowned directory; choose an empty demo directory."
            )
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(expected, stream)
            stream.flush()
            os.fsync(stream.fileno())
    elif marker.is_symlink() or json.loads(marker.read_text()) != expected:
        raise LaunchBlocked(
            "The native demo ownership marker does not match this directory."
        )
    for name in ("pgdata", "s", "commands"):
        candidate = path / name
        if candidate.is_symlink() or (candidate.exists() and not candidate.is_dir()):
            raise LaunchBlocked(
                "Demo runtime paths must be owned directories, not links or files."
            )
    if len(os.fsencode(str(path / "s" / ".s.PGSQL.5432"))) >= 104:
        raise LaunchBlocked(
            "The owned PostgreSQL socket path is too long; use a shorter task-owned directory."
        )
    return path


def clean_env(state: Path):
    # In particular, never inherit PG*, DATABASE_URL, dotenv, or provider settings.
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(Path.home()),
        "LANG": "C.UTF-8",
        "TMPDIR": str(state),
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def isolated_database(state: Path, tools, source: Path):
    import psycopg
    from psycopg import sql

    socket = state / "s"
    socket.mkdir(mode=0o700, exist_ok=True)
    data = state / "pgdata"
    environment = clean_env(state)
    start_requested = False
    if not data.exists():
        subprocess.run(
            [
                tools["initdb"],
                "-D",
                str(data),
                "--auth-local=peer",
                "--auth-host=reject",
                "--username",
                pwd.getpwuid(os.getuid()).pw_name,
                "--encoding=UTF8",
            ],
            env=environment,
            check=True,
        )
    # The launcher never adopts an already-running service, even one pointing at
    # a plausible socket. It owns this process from start until normal shutdown.
    status = subprocess.run(
        [tools["pg_ctl"], "-D", str(data), "status"],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if status.returncode == 0:
        raise LaunchBlocked(
            "The demo PostgreSQL process is already running. Stop its owning launcher before starting another."
        )
    if status.returncode != 3:
        raise LaunchBlocked(
            "The owned PostgreSQL stopped state could not be verified; do not retry startup blindly."
        )
    if any(ch in str(socket) for ch in ("'", '"', "\n", "\r", "\\")):
        raise LaunchBlocked("Unsupported characters in the owned socket path.")
    try:
        start_requested = True
        subprocess.run(
            [
                tools["pg_ctl"],
                "-D",
                str(data),
                "-l",
                str(state / "postgres.log"),
                "-o",
                f"-k '{socket}' -h '' -p 5432 -c unix_socket_permissions=0700",
                "-w",
                "start",
            ],
            env=environment,
            check=True,
        )

        def connection(db=DATABASE):
            return psycopg.connect(
                host=str(socket),
                port=5432,
                dbname=db,
                user=pwd.getpwuid(os.getuid()).pw_name,
                connect_timeout=5,
                autocommit=True,
            )

        with connection("postgres") as conn:
            actual_data = Path(
                conn.execute("SHOW data_directory").fetchone()[0]
            ).resolve()
            if (
                actual_data != data.resolve()
                or conn.execute("SHOW listen_addresses").fetchone()[0] != ""
            ):
                raise LaunchBlocked(
                    "PostgreSQL identity does not match the isolated demo runtime."
                )
            if not conn.execute(
                "SELECT 1 FROM pg_available_extensions WHERE name='vector'"
            ).fetchone():
                raise LaunchBlocked(
                    "This PostgreSQL installation lacks pgvector, required by the existing DungeonMind migrations."
                )
            names = {
                row[0]
                for row in conn.execute(
                    "SELECT datname FROM pg_database WHERE NOT datistemplate"
                )
            }
            if names - {"postgres", DATABASE}:
                raise LaunchBlocked("Refusing a cluster containing non-demo databases.")
            if DATABASE not in names:
                conn.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(DATABASE),
                        sql.Identifier(pwd.getpwuid(os.getuid()).pw_name),
                    )
                )
        url = f"postgresql://{quote(pwd.getpwuid(os.getuid()).pw_name, safe='')}@/{DATABASE}?host={quote(str(socket), safe='')}&port=5432&options={quote('-c statement_timeout=15000 -c lock_timeout=5000', safe='')}"
        migration_env = {**environment, "DUNGEONMIND_DATABASE_URL": url}
        subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                str(source / "alembic.ini"),
                "upgrade",
                "head",
            ],
            cwd=source,
            env=migration_env,
            check=True,
        )
        yield url
    finally:
        if start_requested:
            # A failed/interrupted pg_ctl start can still have launched the
            # postmaster. The exclusive launcher lease and pre-start stopped
            # check bind this cleanup to the owned data directory.
            current = subprocess.run(
                [tools["pg_ctl"], "-D", str(data), "status"],
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if current.returncode == 0:
                subprocess.run(
                    [tools["pg_ctl"], "-D", str(data), "-m", "fast", "-w", "stop"],
                    env=environment,
                    check=True,
                )
            elif current.returncode != 3:
                raise LaunchBlocked(
                    "The owned PostgreSQL startup/cleanup outcome is uncertain; inspect this task's runtime before retrying."
                )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--dungeonmind-source", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--postgres-bin", type=Path)
    parser.add_argument("--port", type=int, default=4183)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only dependency/preflight check; do not create or start anything",
    )
    args = parser.parse_args(argv)
    previous_sigterm = None
    try:
        tools = postgres_tools(args.postgres_bin)
        source = verified_source(args.dungeonmind_source)
        verified_dependencies()
        assets = args.assets.resolve(strict=True)
        if not (assets / "native-demo.html").is_file():
            raise LaunchBlocked(
                "Build the isolated native-demo Vite entry before launch."
            )
        if args.check:
            print(
                "Native dependencies and assets are present. Database initialization and restart qualification have not run."
            )
            return 0
        # Check loopback availability before creating a database or graph.
        import socket

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", args.port))

        def stop(signum, frame):
            raise KeyboardInterrupt

        previous_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, stop)
        state = owned_state(args.state_dir)
        with (state / "launcher.lock").open("a") as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise LaunchBlocked(
                    "Another launcher owns this demo directory."
                ) from exc
            from contextlib import contextmanager

            with contextmanager(isolated_database)(state, tools, source) as url:
                sys.path[:0] = [str(ROOT), str(ROOT / "src")]
                from dungeonmind.infrastructure.postgres import (
                    PostgresDatabase,
                    PostgresNativeSourceEvidenceRepository,
                )
                from apps.live_control_server.native_graph_demo.service import (
                    NativeGraphDemoService,
                )
                from apps.live_control_server.native_graph_demo.server import (
                    DemoHTTPServer,
                )

                service = NativeGraphDemoService(
                    PostgresNativeSourceEvidenceRepository(PostgresDatabase(url)),
                    state / "commands",
                    storage_label="postgres",
                )
                with (
                    closing(service),
                    DemoHTTPServer(args.port, service, assets) as server,
                ):
                    print(
                        f"Native DungeonMind demo: {server.origin} (isolated durable database; local only)",
                        flush=True,
                    )
                    try:
                        server.serve_forever()
                    except KeyboardInterrupt:
                        pass
        return 0
    except KeyboardInterrupt:
        print("Native demo stopped; startup was interrupted.", file=sys.stderr)
        return 130
    except (LaunchBlocked, OSError, subprocess.CalledProcessError) as exc:
        print(f"Native demo launch blocked: {exc}", file=sys.stderr)
        return 2
    finally:
        if previous_sigterm is not None:
            signal.signal(signal.SIGTERM, previous_sigterm)


if __name__ == "__main__":
    raise SystemExit(main())
