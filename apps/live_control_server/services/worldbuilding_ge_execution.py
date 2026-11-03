"""GenerationEngine execution adapter for the approved Gazetteer profile."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

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
SUPPORTED_PROFILE_VERSIONS = frozenset({"1.5", "1.6", "1.7", "1.8", "1.9", "1.10", "1.11", "1.12", "1.13"})


class WorldbuildingExecutionInputError(ValueError):
    """The registered input is not the exact committed Build source requested."""


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
    execution_limits: RecapExecutionLimits | None = None,
) -> ProductionExtractionResult:
    """Run an exact registered Build revision through the selected bounded GE target.

    This creates reviewable extraction evidence only; it does not publish to a World.
    """
    if execution_limits is not None and not isinstance(execution_limits, RecapExecutionLimits):
        raise WorldbuildingExecutionInputError(
            "execution limits must be an explicit bounded GE configuration"
        )
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

    limits = execution_limits if execution_limits is not None else RecapExecutionLimits(
        provider="openrouter",
        model=DEEPSEEK_MODEL,
        max_calls=8,
        max_output_tokens=8192,
        edge_max_output_tokens=8192,
    )
    client = BoundedRecapPassClient(
        limits,
        request_context_hashes=_source_context_hashes(
            document_id=document_id,
            revision=document_revision,
            source_artifact_id=source_artifact_id,
            source_sha256=expected_sha,
            profile_version=profile_version,
        ),
    )
    return run_production_extraction(
        ProductionExtractionRequest(
            repo_root=root,
            source=source,
            profile_id=PROFILE_ID,
            profile_version=profile_version,
            model_id=limits.model,
            allow_llm=True,
            category_client=client,
        )
    )
