"""Canonical APP-STATE ExtractionRun catalog adapter.

This is a presentation adapter over ``list_extraction_runs()``. It does not
consult the legacy GraphIngest file registry and does not invent collection
revisions or manifest identity.
"""

from __future__ import annotations

from typing import Any

from application_state.errors import (
    ApplicationStateError,
    ApplicationStateIntegrityError,
    ApplicationStateMigrationError,
    ApplicationStateUnavailableError,
)
from application_state.ingest.service import list_extraction_runs

INGEST_RUN_CATALOG_SCHEMA = "dmb_extraction_run_catalog_v1"

CODE_UNAVAILABLE = "ingest_run_catalog_unavailable"
CODE_SCHEMA_UNAVAILABLE = "ingest_run_catalog_schema_unavailable"
CODE_INTEGRITY = "ingest_run_catalog_integrity_error"
CODE_ERROR = "ingest_run_catalog_error"


class IngestRunCatalogError(Exception):
    def __init__(self, message: str, *, code: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _sort_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("campaign_id") or ""),
        str(row.get("session_id") or ""),
        str(row.get("run_id") or ""),
    )


def list_canonical_extraction_runs() -> dict[str, Any]:
    """Return unfiltered APP-STATE ExtractionRun records.

    Ordering is deterministic for rendering/tests only. It is not identity or
    a "latest" authority.
    """
    try:
        records = list_extraction_runs()
    except ApplicationStateUnavailableError as exc:
        raise IngestRunCatalogError(
            str(exc),
            code=CODE_UNAVAILABLE,
            status_code=exc.status_code,
        ) from exc
    except ApplicationStateMigrationError as exc:
        raise IngestRunCatalogError(
            str(exc),
            code=CODE_SCHEMA_UNAVAILABLE,
            status_code=exc.status_code,
        ) from exc
    except ApplicationStateIntegrityError as exc:
        raise IngestRunCatalogError(
            str(exc),
            code=CODE_INTEGRITY,
            status_code=exc.status_code,
        ) from exc
    except ApplicationStateError as exc:
        raise IngestRunCatalogError(
            str(exc),
            code=CODE_ERROR,
            status_code=exc.status_code,
        ) from exc

    runs = [record.model_dump(mode="json") for record in records]
    runs.sort(key=_sort_key)
    return {"schema_version": INGEST_RUN_CATALOG_SCHEMA, "runs": runs}
