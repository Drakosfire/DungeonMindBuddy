"""Live-control wiring for the production graph extraction controller."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from application_state.errors import ApplicationStateError

from src.graph_memory.extraction.bounded_recap_execution import (
    BoundedRecapPassClient,
    DEEPSEEK_MODEL,
    RecapExecutionLimits,
)

from apps.live_control_server.config import artifact_data_root
from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    load_registered_source_artifact_text,
    load_source_span_index,
)
from graph_memory.source_span import source_span_index_to_dict
from src.graph_memory.extraction.graph_preview_runner import (
    ProductionExtractionRequest,
    ProductionExtractionResult,
    run_production_extraction,
)
from src.graph_memory.extraction.recap_extraction_profile import (
    resolve_legacy_graph_extraction_profile,
)
from src.graph_memory.extraction.source_adapter import NormalizedExtractionSource
from src.graph_memory.extraction.worldbuilding_extraction_profile import (
    WORLDBUILDING_PROFILE_ID,
    WORLDBUILDING_PROFILE_VERSION,
)
from src.graph_memory.vocabulary.model import ContextVocabularyPacket


def _normalized_from_registered(
    root: Path,
    source_artifact_id: str,
) -> NormalizedExtractionSource:
    artifact, text = load_registered_source_artifact_text(root, source_artifact_id)
    index = load_source_span_index(root, source_artifact_id)
    return NormalizedExtractionSource(
        source_artifact_id=artifact.source_artifact_id,
        source_domain=str(artifact.source_domain),
        world_id=artifact.world_id,
        source_text=text,
        source_sha256=artifact.content_sha256 or "",
        source_uri=artifact.uri,
        campaign_id=artifact.campaign_id,
        session_id=artifact.session_id,
        document_class=artifact.document_class,
        source_span_index=source_span_index_to_dict(index),
    )


def _source_scope_lineage(
    ingest_context: Any,
    *,
    campaign_id: str,
) -> tuple[str, dict[str, Any]]:
    """Freeze only the existing source identity model; no Graph observation."""
    from graph_memory.ingestion.native_recap_source import SourceScope
    from pydantic import ValidationError

    if not isinstance(ingest_context, SourceScope):
        raise SourceArtifactRegistryError(
            "verified World/campaign source scope is required for a fresh recap source",
            status_code=422,
        )
    try:
        scope = SourceScope.model_validate(ingest_context.model_dump())
    except ValidationError as exc:
        raise SourceArtifactRegistryError("invalid recap source scope", status_code=422) from exc
    if scope.campaign_id != campaign_id:
        raise SourceArtifactRegistryError(
            "verified World/campaign source scope belongs to a different campaign",
            status_code=409,
        )
    return scope.native_world_id, scope.model_dump()


def run_recap_production_extraction(
    *,
    repo_root: Path,
    campaign_id: str,
    session_id: str,
    source_artifact_id: str,
    profile: str | None = None,
    model_id: str | None = None,
    allow_llm: bool = False,
    category_client: Any | None = None,
    context_vocabulary_packet: ContextVocabularyPacket | None = None,
    enable_node_vocabulary_packet: bool = False,
    enable_edge_vocabulary_packet: bool = False,
    execution_limits: RecapExecutionLimits | None = None,
    ingest_context: Any | None = None,
    supplemental_evidence: dict | None = None,
    reserved_run: Any | None = None,
) -> ProductionExtractionResult:
    profile_id, profile_version = resolve_legacy_graph_extraction_profile(profile)
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    selected_profile = get_extraction_profile(profile_id, profile_version)
    repo_root = artifact_data_root(repo_root)
    native_world_id, frozen_context = _source_scope_lineage(
        ingest_context,
        campaign_id=campaign_id,
    )
    if supplemental_evidence is not None:
        from apps.live_control_server.models.session_evidence import SessionEvidenceRef
        from apps.live_control_server.services.session_evidence import resolve_evidence_refs

        if not isinstance(supplemental_evidence, dict) or supplemental_evidence.get("world_id") != frozen_context["managed_world_id"]:
            raise ValueError("Session supplement belongs to another managed World")
        try:
            sessions = supplemental_evidence["sessions"]
            if not isinstance(sessions, list):
                raise TypeError("session evidence must be a list")
            pins = [SessionEvidenceRef.model_validate({
                key: item[key] for key in ("run_id", "review_revision", "sha256")
            }).model_dump() for item in sessions]
        except (KeyError, TypeError, ValueError):
            raise ValueError("Session supplement has invalid pinned review revisions") from None
        try:
            resolved = resolve_evidence_refs(frozen_context["managed_world_id"], pins)
        except ApplicationStateError as exc:
            raise ApplicationStateError(
                "Pinned session supplement could not be reopened.", status_code=exc.status_code,
            ) from exc
        try:
            exact = json.dumps(resolved, sort_keys=True, allow_nan=False) == json.dumps(
                supplemental_evidence, sort_keys=True, allow_nan=False,
            )
        except (TypeError, ValueError):
            exact = False
        if not exact:
            raise ValueError("Session supplement differs from its pinned review revisions")
        supplemental_evidence = resolved
    source = _normalized_from_registered(repo_root, source_artifact_id)
    if (source.source_domain, source.world_id, source.campaign_id, source.session_id) != (
        "recap", native_world_id, campaign_id, session_id,
    ):
        raise SourceArtifactRegistryError(
            "registered Recap source does not match the selected World/campaign/session",
            status_code=409,
        )
    from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_source_identity
    binding = resolve_managed_source_identity(frozen_context["managed_world_id"])
    if (binding.native_world_id, binding.binding_version) != (
        frozen_context["native_world_id"], frozen_context["binding_version"],
    ):
        raise SourceArtifactRegistryError("Managed World binding changed before extraction", status_code=409)

    default_ge = allow_llm and category_client is None and execution_limits is None
    if default_ge:
        if model_id not in (None, DEEPSEEK_MODEL):
            raise ValueError(
                "ordinary recap extraction requires the configured DeepSeek GenerationEngine route"
            )
        model_id = DEEPSEEK_MODEL
        # Each configured source extraction pass runs once.
        # This is an execution plan budget, not a provider authorization cap.
        pass_budget = (
            len(selected_profile.node_passes)
            + int(selected_profile.beat_pass is not None)
            + int(
                selected_profile.enable_encounter_job_pass
                and selected_profile.encounter_job_pass is not None
            )
            + 1  # relationship pass
            + int(selected_profile.edge_review_pass is not None)
        )
        execution_limits = RecapExecutionLimits(
            provider="openrouter",
            model=DEEPSEEK_MODEL,
            max_calls=pass_budget,
            # Reasoning shares the total output allowance with the JSON result.
            max_output_tokens=16384,
            reasoning_effort="low",
        )
    bounded = None
    if execution_limits is not None:
        if (
            category_client is not None
            or not allow_llm
            or model_id != execution_limits.model
        ):
            raise ValueError(
                "bounded extraction requires its exact model and owning client"
            )
        if not default_ge:
            bounded = BoundedRecapPassClient(execution_limits)
            category_client = bounded
    supplement_context=None
    supplement_lineage={}
    if supplemental_evidence is not None:
        from apps.live_control_server.services.session_evidence import render_session_evidence
        supplement_context=("Supplemental GM session evidence: use for context and discrepancies, never as a quotation or source span from the external recap. "
            "Extract only claims supported by the actual recap source; do not turn GM preferences or reflections into recap events.\n"+render_session_evidence(supplemental_evidence))
        supplement_lineage={"session_evidence":{"sha256":supplemental_evidence["sha256"],
            "sources":[{"run_id":item["run_id"],"review_revision":item["review_revision"],"sha256":item["sha256"],"citation_url":item["citation_url"]} for item in supplemental_evidence["sessions"]]}}
    if default_ge:
        context_hashes = {
            "source_content": source.source_sha256,
            "source_identity": hashlib.sha256(
                source.source_artifact_id.encode()
            ).hexdigest(),
            "profile_identity": hashlib.sha256(
                f"{profile_id}@{profile_version}".encode()
            ).hexdigest(),
        }
        bounded = BoundedRecapPassClient(
            execution_limits,
            request_context_hashes={**context_hashes,**({"session_evidence":supplemental_evidence["sha256"]} if supplemental_evidence else {})},
            supplemental_context=supplement_context,
        )
        category_client = bounded
    if supplement_context and not default_ge and category_client is not None:
        if not isinstance(category_client, BoundedRecapPassClient):
            raise ValueError("Session supplements require the owned bounded recap client")
        category_client.supplemental_context=supplement_context
    return run_production_extraction(
        ProductionExtractionRequest(
            repo_root=repo_root,
            source=source,
            profile_id=profile_id,
            profile_version=profile_version,
            model_id=model_id,
            allow_llm=allow_llm,
            category_client=category_client,
            context_vocabulary_packet=context_vocabulary_packet,
            enable_node_vocabulary_packet=enable_node_vocabulary_packet,
            enable_edge_vocabulary_packet=enable_edge_vocabulary_packet,
            initial_lineage={**(reserved_run.lineage if reserved_run is not None else {}),
                "world_campaign_ingest_context": frozen_context,**supplement_lineage},
            reserved_run=reserved_run,
        )
    )


def run_worldbuilding_production_extraction(
    *,
    repo_root: Path,
    source_artifact_id: str,
    profile_id: str = WORLDBUILDING_PROFILE_ID,
    profile_version: str = WORLDBUILDING_PROFILE_VERSION,
    model_id: str | None = None,
    allow_llm: bool = False,
    category_client: Any | None = None,
) -> ProductionExtractionResult:
    """Extract from an already-registered worldbuilding SourceArtifact only."""
    repo_root = artifact_data_root(repo_root)
    source = _normalized_from_registered(repo_root, source_artifact_id)
    if source.source_domain != "worldbuilding":
        raise SourceArtifactRegistryError(
            "worldbuilding extraction requires a worldbuilding SourceArtifact",
            status_code=422,
        )
    return run_production_extraction(
        ProductionExtractionRequest(
            repo_root=repo_root,
            source=source,
            profile_id=profile_id,
            profile_version=profile_version,
            model_id=model_id,
            allow_llm=allow_llm,
            category_client=category_client,
        )
    )
