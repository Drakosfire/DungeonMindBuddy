"""Production source-domain-neutral graph extraction controller."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunDiagnostics,
    ExtractionRunStatus,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
    CategoryGraphExtractionOptions,
    CategoryGraphPassClient,
    extract_category_candidate_graph,
    resolve_category_graph_model,
)
from src.graph_memory.extraction.extraction_profile import (
    InadmissibleExtractionProfileError,
    UnknownExtractionProfileError,
    require_admitted_profile,
)
from src.graph_memory.extraction.source_adapter import NormalizedExtractionSource
from src.graph_memory.vocabulary.model import ContextVocabularyPacket

# Ensure profiles register on import.
from src.graph_memory.extraction import recap_extraction_profile as _recap_profiles  # noqa: F401
from src.graph_memory.extraction import worldbuilding_plumbing_profile as _wb_profiles  # noqa: F401
from src.graph_memory.extraction import (  # noqa: F401
    worldbuilding_extraction_profile as _wb_bounded_profiles,
)


@dataclass(frozen=True)
class ProductionExtractionRequest:
    repo_root: Path
    source: NormalizedExtractionSource
    profile_id: str
    profile_version: str
    model_id: str | None = None
    allow_llm: bool = False
    category_client: CategoryGraphPassClient | None = None
    output_dir: Path | None = None
    context_vocabulary_packet: ContextVocabularyPacket | None = None
    enable_node_vocabulary_packet: bool = False
    enable_edge_vocabulary_packet: bool = False


@dataclass
class ProductionExtractionResult:
    run: ExtractionRun
    candidate_graph: dict[str, Any] | None = None
    source_span_index: Mapping[str, Any] | None = None
    failure_kind: str | None = None
    diagnostics: list[str] = field(default_factory=list)
    model_id: str | None = None
    profile_id: str | None = None
    profile_version: str | None = None


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _session_number(session_id: str | None) -> int | None:
    if session_id is None:
        return None
    match = re.match(r"session-(\d+)", session_id.strip())
    if not match:
        raise ValueError(f"session_id must look like session-N, got {session_id!r}")
    return int(match.group(1))


def _component(
    kind: ExtractionRunComponentKind,
    *,
    uri: str,
    exists: bool,
    sha256: str | None = None,
) -> ExtractionRunComponentRef:
    return ExtractionRunComponentRef(kind=kind, uri=uri, exists=exists, sha256=sha256)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _persist_run(repo_root: Path, run: ExtractionRun) -> ExtractionRun:
    from apps.live_control_server.services.graph_run_registry import (
        create_extraction_run,
        update_extraction_run_status,
        get_extraction_run,
    )

    created = create_extraction_run(
        repo_root,
        source_artifact_id=run.source_artifact_id,
        source_domain=run.source_domain,
        campaign_id=run.campaign_id,
        session_id=run.session_id,
        profile_id=run.profile_id,
        components=run.components,
        status=ExtractionRunStatus.DRAFT,
    )
    # Stamp identity from controller-assigned run_id when provided.
    if run.run_id and run.run_id != created.run_id:
        # Registry owns IDs; keep created identity.
        pass
    updated = update_extraction_run_status(
        repo_root,
        created.run_id,
        status=run.status,
        components=run.components,
    )
    # Preserve diagnostics/lineage on the in-memory result even if registry omits them.
    return updated.model_copy(
        update={
            "diagnostics": run.diagnostics,
            "lineage": run.lineage,
            "created_at": created.created_at,
            "updated_at": updated.updated_at,
        }
    )


def run_production_extraction(
    request: ProductionExtractionRequest,
) -> ProductionExtractionResult:
    """Execute an exact profile-selected extraction and persist an ExtractionRun."""

    diagnostics: list[str] = []
    source = request.source
    try:
        profile = require_admitted_profile(
            profile_id=request.profile_id,
            profile_version=request.profile_version,
            source_domain=source.source_domain,
            document_class=source.document_class,
            session_id=source.session_id,
        )
    except (UnknownExtractionProfileError, InadmissibleExtractionProfileError) as exc:
        failed = ExtractionRun(
            run_id="pending",
            source_artifact_id=source.source_artifact_id,
            source_domain=source.source_domain,
            status=ExtractionRunStatus.FAILED,
            campaign_id=source.campaign_id,
            session_id=source.session_id,
            profile_id=f"{request.profile_id}@{request.profile_version}",
            created_at=_now_iso(),
            updated_at=_now_iso(),
            diagnostics=ExtractionRunDiagnostics(
                messages=[str(exc)],
                errors=[str(exc)],
            ),
            lineage={"failure_kind": "profile"},
        )
        persisted = _persist_run(request.repo_root, failed)
        return ProductionExtractionResult(
            run=persisted,
            source_span_index=source.source_span_index,
            failure_kind="profile",
            diagnostics=[str(exc)],
            profile_id=request.profile_id,
            profile_version=request.profile_version,
        )

    output_dir = request.output_dir or (
        request.repo_root
        / "out"
        / "graph_memory"
        / "runs"
        / "extraction"
        / source.source_artifact_id.replace(":", "_")
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    span_index_path = output_dir / "source_span_index.json"
    _write_json(span_index_path, dict(source.source_span_index))
    components = {
        "source_artifact": _component(
            ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri=source.source_uri,
            exists=True,
            sha256=source.source_sha256,
        ),
        "source_span_index": _component(
            ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri=span_index_path.as_posix(),
            exists=True,
        ),
    }

    if not request.allow_llm and request.category_client is None:
        prepared = ExtractionRun(
            run_id="pending",
            source_artifact_id=source.source_artifact_id,
            source_domain=source.source_domain,
            status=ExtractionRunStatus.PREPARED,
            campaign_id=source.campaign_id,
            session_id=source.session_id,
            profile_id=profile.qualified_id,
            created_at=_now_iso(),
            updated_at=_now_iso(),
            components=components,
            lineage={
                "profile_id": profile.profile_id,
                "profile_version": profile.profile_version,
                "source_sha256": source.source_sha256,
            },
        )
        persisted = _persist_run(request.repo_root, prepared)
        return ProductionExtractionResult(
            run=persisted,
            source_span_index=source.source_span_index,
            diagnostics=diagnostics,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
        )

    model_id = resolve_category_graph_model(request.model_id)
    options = CategoryGraphExtractionOptions(
        campaign_id=source.campaign_id or "",
        session_id=source.session_id,
        session_number=_session_number(source.session_id),
        source_span_index=source.source_span_index,
        model_id=model_id,
        profile=profile,
        enable_encounter_job_pass=profile.enable_encounter_job_pass,
        enable_party_participation_attachment=profile.enable_party_participation_attachment,
        enable_encounter_job_edge_guidance=profile.enable_encounter_job_edge_guidance,
        enable_dynamic_node_vocabulary_packet=profile.enable_dynamic_node_vocabulary_packet,
        enable_node_vocabulary_packet=(
            request.enable_node_vocabulary_packet
            and request.context_vocabulary_packet is not None
        ),
        node_vocabulary_packet=(
            request.context_vocabulary_packet
            if request.enable_node_vocabulary_packet
            else None
        ),
        enable_edge_vocabulary_packet=(
            request.enable_edge_vocabulary_packet
            and request.context_vocabulary_packet is not None
        ),
        edge_vocabulary_packet=(
            request.context_vocabulary_packet
            if request.enable_edge_vocabulary_packet
            else None
        ),
    )

    try:
        extraction = extract_category_candidate_graph(
            options,
            client=request.category_client,
        )
    except CategoryGraphExtractionError as exc:
        message = str(exc)
        failure_kind = "extraction"
        lowered = message.lower()
        if "refus" in lowered:
            failure_kind = "refusal"
        elif "incomplete" in lowered:
            failure_kind = "incomplete"
        elif "schema" in lowered or "json" in lowered:
            failure_kind = "schema"
        failed = ExtractionRun(
            run_id="pending",
            source_artifact_id=source.source_artifact_id,
            source_domain=source.source_domain,
            status=ExtractionRunStatus.FAILED,
            campaign_id=source.campaign_id,
            session_id=source.session_id,
            profile_id=profile.qualified_id,
            created_at=_now_iso(),
            updated_at=_now_iso(),
            components=components,
            diagnostics=ExtractionRunDiagnostics(messages=[message], errors=[message]),
            lineage={
                "failure_kind": failure_kind,
                "profile_id": profile.profile_id,
                "profile_version": profile.profile_version,
                "model_id": model_id,
            },
        )
        persisted = _persist_run(request.repo_root, failed)
        return ProductionExtractionResult(
            run=persisted,
            source_span_index=source.source_span_index,
            failure_kind=failure_kind,
            diagnostics=[message],
            model_id=model_id,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
        )
    except Exception as exc:  # noqa: BLE001 - persist unexpected model/API failures
        message = str(exc)
        failed = ExtractionRun(
            run_id="pending",
            source_artifact_id=source.source_artifact_id,
            source_domain=source.source_domain,
            status=ExtractionRunStatus.FAILED,
            campaign_id=source.campaign_id,
            session_id=source.session_id,
            profile_id=profile.qualified_id,
            created_at=_now_iso(),
            updated_at=_now_iso(),
            components=components,
            diagnostics=ExtractionRunDiagnostics(messages=[message], errors=[message]),
            lineage={
                "failure_kind": "model",
                "profile_id": profile.profile_id,
                "profile_version": profile.profile_version,
                "model_id": model_id,
            },
        )
        persisted = _persist_run(request.repo_root, failed)
        return ProductionExtractionResult(
            run=persisted,
            source_span_index=source.source_span_index,
            failure_kind="model",
            diagnostics=[message],
            model_id=model_id,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
        )

    candidate_path = output_dir / "candidate_graph.json"
    _write_json(candidate_path, extraction.candidate_graph)
    components = {
        **components,
        "candidate_graph": _component(
            ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri=candidate_path.as_posix(),
            exists=True,
        ),
    }

    nodes = extraction.candidate_graph.get("nodes") or []
    missing_evidence = [
        node.get("node_id")
        for node in nodes
        if isinstance(node, Mapping) and not (node.get("evidence_refs") or [])
    ]
    if missing_evidence:
        message = f"candidates missing evidence_refs: {missing_evidence[:5]}"
        failed = ExtractionRun(
            run_id="pending",
            source_artifact_id=source.source_artifact_id,
            source_domain=source.source_domain,
            status=ExtractionRunStatus.VALIDATED,
            campaign_id=source.campaign_id,
            session_id=source.session_id,
            profile_id=profile.qualified_id,
            created_at=_now_iso(),
            updated_at=_now_iso(),
            components=components,
            diagnostics=ExtractionRunDiagnostics(
                messages=[message],
                errors=[message],
                incomplete_components=["evidence"],
            ),
            lineage={
                "failure_kind": "validation",
                "profile_id": profile.profile_id,
                "profile_version": profile.profile_version,
                "model_id": model_id,
                "reviewable": False,
            },
        )
        persisted = _persist_run(request.repo_root, failed)
        return ProductionExtractionResult(
            run=persisted,
            candidate_graph=extraction.candidate_graph,
            source_span_index=source.source_span_index,
            failure_kind="validation",
            diagnostics=[message],
            model_id=model_id,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
        )

    reviewable = ExtractionRun(
        run_id="pending",
        source_artifact_id=source.source_artifact_id,
        source_domain=source.source_domain,
        status=ExtractionRunStatus.REVIEWABLE,
        campaign_id=source.campaign_id,
        session_id=source.session_id,
        profile_id=profile.qualified_id,
        created_at=_now_iso(),
        updated_at=_now_iso(),
        components=components,
        lineage={
            "profile_id": profile.profile_id,
            "profile_version": profile.profile_version,
            "model_id": model_id,
            "source_sha256": source.source_sha256,
        },
    )
    persisted = _persist_run(request.repo_root, reviewable)
    return ProductionExtractionResult(
        run=persisted,
        candidate_graph=extraction.candidate_graph,
        source_span_index=source.source_span_index,
        model_id=model_id,
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
    )
