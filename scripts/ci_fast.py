"""Additive PR contracts; no selection or change to existing required gates."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DATABASE_WITNESSES = (
    "tests/test_world_access_control.py::test_owner_has_normal_world_use_and_new_world_is_private",
    "tests/test_world_access_control.py::test_stale_world_cas_cannot_overwrite_serialized_access_state",
    "tests/application_state/test_authored_pages_postgres.py::test_failed_commit_rolls_back_body_pointer_draft_and_revision",
    "tests/application_state/test_authored_pages_postgres.py::test_page_draft_save_history_and_database_only_reads",
)
CONTRACTS = {
    "frontend-tests": ("apps/live-control-ui", ("npm", "test")),
    "frontend-build": ("apps/live-control-ui", ("npm", "run", "build")),
    "auth-database": (".", ("{python}", "-m", "pytest", "-q", "--durations=10",
        "tests/test_dms_principal.py", "tests/test_hosted_auth_login.py", *DATABASE_WITNESSES)),
}


def execute(name: str) -> int:
    cwd, command = CONTRACTS[name]
    if name == "auth-database" and any(os.environ.get(key) for key in
            ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD")):
        raise ValueError("additive database verification forbids inherited pytest selection controls")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    argv = [sys.executable if value == "{python}" else value for value in command]
    started = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT / cwd, check=False)
    print(json.dumps({"version": 1, "contract": name, "source_sha": source,
        "elapsed_seconds": round(time.monotonic() - started, 3), "exit_code": result.returncode,
        "coverage": "all discovered Vitest" if name == "frontend-tests" else
            "full type/build" if name == "frontend-build" else "auth and four real database witnesses"}), flush=True)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", choices=CONTRACTS)
    return execute(parser.parse_args().contract)


if __name__ == "__main__":
    raise SystemExit(main())
