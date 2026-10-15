"""GenerationEngine execution adapter for the approved Gazetteer profile."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

from apps.live_control_server.config import artifact_data_root
from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    load_registered_source_artifact_text,
    load_source_span_index,
)
from graph_memory.source_span import source_span_index_to_dict
from src.graph_memory.extraction.bounded_recap_execution import (
    BoundedRecapPassClient,
    DEEPSEEK_MODEL,
    RecapExecutionLimits,
)
from src.graph_memory.extraction.graph_preview_runner import (
    ProductionExtractionRequest,
    ProductionExtractionResult,
    run_production_extraction,
)
from src.graph_memory.extraction.source_adapter import NormalizedExtractionSource


PROFILE_ID = "worldbuilding_gazetteer_v1"
SUPPORTED_PROFILE_VERSIONS = frozenset({"1.5", "1.6", "1.7", "1.8"})


class WorldbuildingExecutionInputError(ValueError):
    """The registered input is not the exact committed Build source requested."""


class WorldbuildingExecutionEvidenceError(RuntimeError):
    """Provider usage evidence could not be durably recorded."""


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".ledger-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception as exc:  # preserve a safe, non-content-bearing failure
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise WorldbuildingExecutionEvidenceError(
            "could not persist worldbuilding GenerationEngine ledger"
        ) from exc


def _fail_reviewable_run_after_ledger_error(
    repo_root: Path, result: ProductionExtractionResult
) -> None:
    """Prevent a candidate from remaining reviewable without its required usage ledger."""
    from apps.live_control_server.services.graph_run_registry import (
        update_extraction_run_status,
    )
    from src.graph_memory.ingestion.extraction_run import ExtractionRunStatus

    if result.run.status != ExtractionRunStatus.REVIEWABLE:
        return
    diagnostics = result.run.diagnostics.model_copy(deep=True)
    diagnostics.messages.append(
        "GenerationEngine usage evidence could not be persisted; run was failed."
    )
    diagnostics.errors.append("inference_call_ledger_persistence_failed")
    lineage = {
        **result.run.lineage,
        "reviewable": False,
        "usage_ledger_state": "missing",
    }
    update_extraction_run_status(
        repo_root,
        result.run.run_id,
        status=ExtractionRunStatus.FAILED,
        expected_revision=result.run.revision,
        diagnostics=diagnostics,
        lineage=lineage,
    )


def _source_context_hashes(
    *, document_id: str, revision: int, source_artifact_id: str,
    source_sha256: str, profile_version: str,
) -> dict[str, str]:
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    return {
        "document_identity": digest(f"{document_id}@{revision}"),
        "profile_identity": digest(f"{PROFILE_ID}@{profile_version}"),
        "source_artifact_identity": digest(source_artifact_id),
        "source_content": source_sha256,
    }


def run_gazetteer_with_generation_engine(
    *,
    repo_root: Path,
    source_artifact_id: str,
    document_id: str,
    document_revision: int,
    expected_content_sha256: str,
    profile_version: str,
) -> ProductionExtractionResult:
    """Run an exact registered Build revision through GE/OpenRouter DeepSeek.

    This creates reviewable extraction evidence only; it does not publish to a World.
    """
    root = artifact_data_root(repo_root)
    if profile_version not in SUPPORTED_PROFILE_VERSIONS:
        raise WorldbuildingExecutionInputError("unsupported Gazetteer profile version")
    expected_sha = expected_content_sha256.removeprefix("sha256:").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        raise WorldbuildingExecutionInputError("invalid expected source digest")

    try:
        artifact, text = load_registered_source_artifact_text(root, source_artifact_id)
        span_index = load_source_span_index(root, source_artifact_id)
    except SourceArtifactRegistryError as exc:
        raise WorldbuildingExecutionInputError(
            "registered worldbuilding source is unavailable"
        ) from exc
    if (
        artifact.source_domain != "worldbuilding"
        or artifact.workspace_document_id != document_id
        or artifact.workspace_document_revision != document_revision
        or artifact.content_sha256 != expected_sha
        or hashlib.sha256(text.encode("utf-8")).hexdigest() != expected_sha
    ):
        raise WorldbuildingExecutionInputError(
            "registered source does not match the committed Build revision"
        )

    span_payload = source_span_index_to_dict(span_index)
    source = NormalizedExtractionSource(
        source_artifact_id=artifact.source_artifact_id,
        source_domain=str(artifact.source_domain),
        source_text=text,
        source_sha256=artifact.content_sha256 or "",
        source_uri=artifact.uri,
        campaign_id=artifact.campaign_id,
        session_id=artifact.session_id,
        document_class=artifact.document_class,
        source_span_index=span_payload,
    )

    artifact_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", source_artifact_id)
    output_root = root / "out" / "graph_memory" / "runs" / "extraction" / artifact_key
    output_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    run_output = output_root / f"ge-{uuid.uuid4().hex}"
    run_output.mkdir(mode=0o700)

    limits = RecapExecutionLimits(
        provider="openrouter",
        model=DEEPSEEK_MODEL,
        max_calls=8,
        max_output_tokens=8192,
        edge_max_output_tokens=8192,
    )
    client = BoundedRecapPassClient(
        limits,
        response_artifact_dir=run_output / "generationengine_attempts",
        request_context_hashes=_source_context_hashes(
            document_id=document_id,
            revision=document_revision,
            source_artifact_id=source_artifact_id,
            source_sha256=expected_sha,
            profile_version=profile_version,
        ),
    )
    result: ProductionExtractionResult | None = None
    try:
        result = run_production_extraction(
            ProductionExtractionRequest(
                repo_root=root,
                source=source,
                profile_id=PROFILE_ID,
                profile_version=profile_version,
                model_id=DEEPSEEK_MODEL,
                allow_llm=True,
                category_client=client,
                output_dir=run_output,
            )
        )
        return result


    finally:
        try:
            _write_private_json(
                run_output / "inference_call_ledger.json",
                {
                    "schema_version": "dmb_worldbuilding_generationengine_ledger_v1",
                    "document_id": document_id,
                    "document_revision": document_revision,
                    "source_artifact_id": source_artifact_id,
                    "source_sha256": expected_sha,
                    "profile_id": f"{PROFILE_ID}@{profile_version}",
                    "provider": "openrouter",
                    "model": DEEPSEEK_MODEL,
                    "run_id": result.run.run_id if result is not None else None,
                    "run_status": result.run.status.value if result is not None else None,
                    "execution": client.ledger(),
                },
            )
        except WorldbuildingExecutionEvidenceError as exc:
            if result is not None:
                try:
                    _fail_reviewable_run_after_ledger_error(root, result)
                except Exception:
                    raise WorldbuildingExecutionEvidenceError(
                        "could not persist usage evidence or revoke run reviewability"
                    ) from exc
            raise
