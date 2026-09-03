#!/usr/bin/env python3
"""Explicit adoption of file-backed ExtractionRun records into APP-STATE.

Never runs during FastAPI startup. Does not delete the source file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from application_state.config import APPLICATION_STATE_DSN_ENV, load_runtime_dsn  # noqa: E402
from application_state.errors import (  # noqa: E402
    ApplicationStateConflictError,
    ApplicationStateError,
)
from application_state.ingest.import_legacy import import_extraction_runs_from_registry  # noqa: E402
from application_state.ingest.service import inspect_ingest_authority  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402


def _repo_root() -> Path:
    return _REPO_ROOT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import canonical ExtractionRun records into application-state PostgreSQL"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report imported/noop/conflict counts without writing",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root containing out/registries/extraction_runs.json",
    )
    args = parser.parse_args(argv)
    load_dungeonmindbuddy_dotenv()
    root = (args.root or _repo_root()).resolve()
    try:
        load_runtime_dsn()
        report = import_extraction_runs_from_registry(root, dry_run=args.dry_run)
        catalog = inspect_ingest_authority()
    except ApplicationStateConflictError as exc:
        print(f"CONFLICT: {exc}", file=sys.stderr)
        return 2
    except ApplicationStateError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    mode = "dry-run" if args.dry_run else "import"
    print(f"Ingest run adoption ({mode})")
    print(f"  source: {report.source_path}")
    print(f"  source_absent: {report.source_absent}")
    print(f"  source_count: {report.source_count}")
    print(f"  imported: {report.imported}")
    print(f"  noop: {report.noop}")
    print(f"  conflict: {report.conflict}")
    print(f"  db_run_count: {catalog.run_count}")
    print(f"  dsn_env: {APPLICATION_STATE_DSN_ENV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
