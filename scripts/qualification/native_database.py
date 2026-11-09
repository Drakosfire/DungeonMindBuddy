"""Own a separate canonical Core test database for the full qualification run."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

import psycopg

from scripts.qualification.bootstrap_core import prepare_checkout
from scripts.qualification.image_probe import POSTGRES_IMAGE, QualificationFailure

ROOT = Path(__file__).resolve().parents[2]


class NativeTestDatabase:
    def __init__(self, output: Path):
        self.output = output.resolve()
        self.output.mkdir(parents=True, exist_ok=False)
        self.name = "dmb-qualification-native-test-" + secrets.token_hex(6)
        self.report = {"container": self.name, "owned": False, "cleaned": False}
        self.sequence = 0

    def command(self, argv: list[str], **kwargs) -> subprocess.CompletedProcess:
        self.sequence += 1
        result = subprocess.run(argv, text=True, capture_output=True, **kwargs)
        (self.output / f"command-{self.sequence:03}.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise QualificationFailure(f"native test setup command {self.sequence} failed; retained log")
        return result

    def __enter__(self) -> str:
        # No caller-supplied DSN, retained volume or network target is accepted.
        # The named RAM-only cluster is independent of Buddy's clone fixture.
        self.report["owned"] = True  # cleanup also covers partial docker-run failure
        try:
            self.command(["docker", "run", "--detach", "--name", self.name,
                          "--tmpfs", "/var/lib/postgresql/data:rw,size=1g",
                          "--publish", "127.0.0.1::5432", "--env", "POSTGRES_USER=qualification_native_test",
                          "--env", "POSTGRES_DB=qualification_native_test", "--env", "POSTGRES_HOST_AUTH_METHOD=trust", POSTGRES_IMAGE])
            for _ in range(60):
                ready = subprocess.run(["docker", "exec", self.name, "pg_isready", "-h", "127.0.0.1",
                                        "-U", "qualification_native_test", "-d", "qualification_native_test"], capture_output=True)
                if ready.returncode == 0:
                    break
                time.sleep(1)
            else:
                raise QualificationFailure("native_test_postgres_unavailable")
            endpoint = self.command(["docker", "port", self.name, "5432/tcp"]).stdout.strip()
            if not endpoint.startswith("127.0.0.1:") or not endpoint.removeprefix("127.0.0.1:").isdigit():
                raise QualificationFailure("native test database must be loopback only")
            dsn = f"postgresql://qualification_native_test@{endpoint}/qualification_native_test"
            with psycopg.connect(dsn, autocommit=True) as connection:
                assert connection.execute("SELECT current_database()").fetchone()[0] == "qualification_native_test"
                connection.execute("CREATE EXTENSION vector")
            checkout = self.output / "canonical-core"
            self.report["core_source_sha"] = prepare_checkout(checkout)
            self.command([sys.executable, "-m", "alembic", "-c", str(checkout / "alembic.ini"), "upgrade", "head"],
                         cwd=checkout, env={**os.environ, "DUNGEONMIND_DATABASE_URL": dsn})
            with psycopg.connect(dsn) as connection:
                self.report["schema_revision"] = connection.execute("SELECT version_num FROM dungeonmind.alembic_version").fetchone()[0]
                assert connection.execute("SELECT to_regclass('dungeonmind.reviewed_world_initializations')").fetchone()[0]
            self.report["migrated"] = True
            return dsn
        except BaseException:
            self.__exit__(*sys.exc_info())
            raise

    def __exit__(self, kind, error, traceback):
        logs = subprocess.run(["docker", "logs", self.name], capture_output=True, text=True)
        (self.output / "postgres.log").write_text(logs.stdout + logs.stderr)
        removed = subprocess.run(["docker", "rm", "--force", "--volumes", self.name], capture_output=True, text=True)
        self.report["cleaned"] = removed.returncode == 0
        self.report["cleanup_result"] = removed.stdout + removed.stderr
        (self.output / "result.json").write_text(json.dumps(self.report, indent=2) + "\n")
        if not self.report["cleaned"]:
            raise QualificationFailure("native test database cleanup failed") from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--partition", type=int, choices=range(4))
    args = parser.parse_args()
    if args.partition is not None and any(os.environ.get(name) for name in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS")):
        parser.error("partitioned qualification forbids inherited pytest options before database allocation")
    with NativeTestDatabase(args.output) as dsn:
        command = [sys.executable, str(ROOT / "scripts/ci_contract.py"), "run",
                   "full-regression" if args.partition is None else "full-backend"]
        if args.partition is not None:
            command += ["--partition", str(args.partition), "--partition-report", str(args.output.parent / "collection.json")]
        result = subprocess.run(command, cwd=ROOT, env={**os.environ, "DMB_CUTOVER_TEST_DATABASE_URL": dsn})
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
