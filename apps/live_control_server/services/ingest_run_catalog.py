"""Canonical APP-STATE ExtractionRun catalog adapter.

This is a presentation adapter over ``list_extraction_runs()``. It does not
consult the legacy GraphIngest file registry and does not invent collection
revisions or manifest identity.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from application_state.errors import (
    ApplicationStateError,
    ApplicationStateIntegrityError,
    ApplicationStateMigrationError,
    ApplicationStateUnavailableError,
)
from application_state.ingest.service import list_extraction_runs
from apps.live_control_server.services.native_recap_source_admission import public_run
from apps.live_control_server.services import graph_run_registry as runs
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunStatus,
    normalize_content_digest,
)
from src.graph_memory.candidate_document_integrity import (
    classify_candidate_document_integrity,
)

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


def _catalog_records(**filters: str) -> list[ExtractionRun]:
    try:
        records = list_extraction_runs(**filters)
    except ApplicationStateUnavailableError as exc:
        raise IngestRunCatalogError(
            "The extraction database is unavailable.",
            code=CODE_UNAVAILABLE,
            status_code=exc.status_code,
        ) from exc
    except ApplicationStateMigrationError as exc:
        raise IngestRunCatalogError(
            "The extraction database schema is unavailable.",
            code=CODE_SCHEMA_UNAVAILABLE,
            status_code=exc.status_code,
        ) from exc
    except ApplicationStateIntegrityError as exc:
        raise IngestRunCatalogError(
            "The saved extraction catalog failed integrity checks.",
            code=CODE_INTEGRITY,
            status_code=exc.status_code,
        ) from exc
    except ApplicationStateError as exc:
        raise IngestRunCatalogError(
            "The extraction catalog could not be read.",
            code=CODE_ERROR,
            status_code=exc.status_code,
        ) from exc

    return records


def list_canonical_extraction_runs() -> dict[str, Any]:
    """Return the APP catalog, deterministically ordered for presentation only."""
    records = _catalog_records()
    runs = [public_run(record) for record in records]
    runs.sort(key=_sort_key)
    return {"schema_version": INGEST_RUN_CATALOG_SCHEMA, "runs": runs}


def _same_recap_ingest_context_authority(
    extracted: Any, current: Mapping[str, Any]
) -> bool:
    """A recap extraction depends on its source, not the Graph head it observed."""
    if not isinstance(extracted, Mapping):
        return False
    return all(
        extracted.get(key) == current.get(key)
        for key in (
            "schema",
            "managed_world_id",
            "native_world_id",
            "binding_version",
            "campaign_id",
        )
    )


def inspect_recap_extraction_status(
    *,
    root: Path,
    campaign_id: str,
    session_id: str,
    context: Mapping[str, Any],
    source_content_sha256: str | None,
) -> dict[str, Any] | None:
    """Project saved extraction status; this grants no admission/publication authority.

    Exact bytes are resolved by the existing run/source owners. Operational file
    copies are neither a catalog nor a substitute for missing database evidence.
    """
    records = [
        record
        for record in _catalog_records(campaign_id=campaign_id, session_id=session_id)
        if record.source_domain == "recap"
        and _same_recap_ingest_context_authority(
            record.lineage.get("world_campaign_ingest_context"), context
        )
    ]
    # Latest is a presentation choice over the complete scoped catalog. A failed
    # or corrupt newest attempt must not silently fall back to an older success.
    records.sort(
        key=lambda record: (record.created_at or "", record.run_id), reverse=True
    )
    try:
        for run in records:
            data = None
            if run.status == ExtractionRunStatus.REVIEWABLE:
                data = runs.load_reviewable_extraction_data(root, run.run_id)
                run = data.run
                if not _same_recap_ingest_context_authority(
                    run.lineage.get("world_campaign_ingest_context"), context
                ):
                    raise runs.GraphRunRegistryError(
                        "Saved extraction scope changed", status_code=409
                    )
                artifact = data.source_artifact
            else:
                artifact, _ = runs.load_run_source_input(root, run)
            if artifact.world_id != context["native_world_id"]:
                raise runs.GraphRunRegistryError(
                    "Saved source is outside the selected World", status_code=409
                )
            if source_content_sha256 and normalize_content_digest(
                artifact.content_sha256
            ) != normalize_content_digest(source_content_sha256):
                continue
            result = {
                "status": run.status.value,
                "extraction_run_id": run.run_id,
                "extraction_run_status": run.status.value,
                "source_artifact_id": artifact.source_artifact_id,
                "model_id": run.lineage.get("model_id"),
                "source_match_mode": "content_digest"
                if source_content_sha256
                else "retained_database",
                "next_actions": [],
                "blocked_reason": None,
            }
            if data is not None:
                candidate = json.loads(data.candidate_bytes)
                if not isinstance(candidate, dict):
                    raise ValueError("Candidate must be an object")
                classification = classify_candidate_document_integrity(candidate)
                if (
                    classification.is_document_integrity_failure
                    or classification.preview is None
                ):
                    raise ValueError("Saved candidate failed document integrity")
                preview = classification.preview
                result.update(
                    {
                        "status": "candidate_validation_ready",
                        "node_count": len(preview.nodes),
                        "edge_count": len(preview.edges),
                        "candidate_node_count": len(preview.nodes),
                        "candidate_edge_count": len(preview.edges),
                        "candidate_beat_count": len(preview.beats),
                        "evidence_ref_count": sum(
                            len(row.evidence_refs)
                            for row in (
                                *preview.nodes,
                                *preview.edges,
                                *preview.beats,
                                *preview.source_observations,
                            )
                        ),
                        "next_actions": ["review_candidate"],
                    }
                )
            elif run.status in {
                ExtractionRunStatus.FAILED,
                ExtractionRunStatus.INCOMPLETE,
            }:
                result.update(
                    {
                        "status": "failed",
                        "extraction_mode": "llm_blocked",
                        "blocked_reason": "The saved extraction did not complete. Review the attempt before retrying.",
                        "next_actions": ["force_graph_run"],
                    }
                )
            return result
    except (runs.GraphRunRegistryError, ValueError, TypeError, KeyError) as exc:
        raise IngestRunCatalogError(
            "Saved extraction evidence is unavailable or failed integrity checks.",
            code=CODE_INTEGRITY,
            status_code=getattr(exc, "status_code", 409),
        ) from exc
    return None
