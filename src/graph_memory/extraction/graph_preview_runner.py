"""Production source-domain-neutral graph extraction controller."""

from __future__ import annotations

import hashlib
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
from graph_memory.source_span import (
    build_source_span_index_for_text,
    source_span_index_to_dict,
)
from src.graph_memory.candidate_graph_preview import (
    candidate_graph_preview_from_dict,
    validate_candidate_graph_preview,
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
    known_entity_mentions: Mapping[str, Any] | None = None
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


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_uri(repo_root: Path, path: Path) -> str:
    root = repo_root.resolve()
    resolved = path.resolve()
    relpath = resolved.relative_to(root).as_posix()
    return f"repo://{relpath}"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _component(
    kind: ExtractionRunComponentKind,
    *,
    uri: str,
    sha256: str,
    exists: bool = True,
) -> ExtractionRunComponentRef:
    return ExtractionRunComponentRef(kind=kind, uri=uri, exists=exists, sha256=sha256)


def _create_draft_run(
    repo_root: Path,
    source: NormalizedExtractionSource,
    *,
    profile_id: str | None,
    diagnostics: ExtractionRunDiagnostics | None = None,
    lineage: dict[str, Any] | None = None,
) -> ExtractionRun:
    from apps.live_control_server.services.graph_run_registry import create_extraction_run

    return create_extraction_run(
        repo_root,
        source_artifact_id=source.source_artifact_id,
        source_domain=source.source_domain,
        campaign_id=source.campaign_id,
        session_id=source.session_id,
        profile_id=profile_id,
        status=ExtractionRunStatus.DRAFT,
        diagnostics=diagnostics,
        lineage=lineage,
    )


def _advance_run(
    repo_root: Path,
    run: ExtractionRun,
    *,
    status: ExtractionRunStatus,
    components: dict[str, ExtractionRunComponentRef] | None = None,
    diagnostics: ExtractionRunDiagnostics | None = None,
    lineage: dict[str, Any] | None = None,
) -> ExtractionRun:
    from apps.live_control_server.services.graph_run_registry import (
        update_extraction_run_status,
    )

    return update_extraction_run_status(
        repo_root,
        run.run_id,
        status=status,
        expected_revision=run.revision,
        components=components,
        diagnostics=diagnostics,
        lineage=lineage,
    )


def _fail_run(
    repo_root: Path,
    run: ExtractionRun,
    *,
    message: str,
    failure_kind: str,
    components: dict[str, ExtractionRunComponentRef] | None = None,
    lineage: dict[str, Any] | None = None,
    incomplete_components: list[str] | None = None,
) -> ExtractionRun:
    diagnostics = ExtractionRunDiagnostics(
        messages=[message],
        errors=[message],
        incomplete_components=list(incomplete_components or []),
    )
    next_lineage = {
        **(run.lineage or {}),
        **(lineage or {}),
        "failure_kind": failure_kind,
    }
    return _advance_run(
        repo_root,
        run,
        status=ExtractionRunStatus.FAILED,
        components=components,
        diagnostics=diagnostics,
        lineage=next_lineage,
    )


def _run_output_dir(repo_root: Path, run_id: str, output_dir: Path | None) -> Path:
    base = output_dir or (repo_root / "out" / "graph_memory" / "runs" / "extraction")
    return base / run_id


def _build_prepared_components(
    repo_root: Path,
    source: NormalizedExtractionSource,
    output_dir: Path,
) -> tuple[dict[str, ExtractionRunComponentRef], dict[str, Any]]:
    digest = source.source_sha256.removeprefix("sha256:")
    index = build_source_span_index_for_text(
        source_artifact_id=source.source_artifact_id,
        content_sha256=digest,
        text=source.source_text,
    )
    span_payload = source_span_index_to_dict(index)
    span_path = output_dir / "source_span_index.json"
    _write_json(span_path, span_payload)
    components = {
        "source_artifact": _component(
            ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri=source.source_uri,
            sha256=digest,
        ),
        "source_span_index": _component(
            ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri=_repo_uri(repo_root, span_path),
            sha256=_file_sha256(span_path),
        ),
    }
    return components, span_payload


def run_production_extraction(
    request: ProductionExtractionRequest,
) -> ProductionExtractionResult:
    """Execute an exact profile-selected extraction and persist an ExtractionRun."""
    from apps.live_control_server.services.graph_run_registry import get_extraction_run

    source = request.source
    profile_qualified: str | None = None
    try:
        profile = require_admitted_profile(
            profile_id=request.profile_id,
            profile_version=request.profile_version,
            source_domain=source.source_domain,
            document_class=source.document_class,
            session_id=source.session_id,
        )
        profile_qualified = profile.qualified_id
    except (UnknownExtractionProfileError, InadmissibleExtractionProfileError) as exc:
        draft = _create_draft_run(
            request.repo_root,
            source,
            profile_id=f"{request.profile_id}@{request.profile_version}",
            diagnostics=ExtractionRunDiagnostics(messages=[str(exc)], errors=[str(exc)]),
            lineage={"failure_kind": "profile"},
        )
        failed = _fail_run(
            request.repo_root,
            draft,
            message=str(exc),
            failure_kind="profile",
            lineage={"failure_kind": "profile"},
        )
        loaded = get_extraction_run(request.repo_root, failed.run_id)
        return ProductionExtractionResult(
            run=loaded,
            failure_kind="profile",
            diagnostics=[str(exc)],
            profile_id=request.profile_id,
            profile_version=request.profile_version,
        )

    draft = _create_draft_run(
        request.repo_root,
        source,
        profile_id=profile_qualified,
        lineage={
            "profile_id": profile.profile_id,
            "profile_version": profile.profile_version,
            "source_sha256": source.source_sha256,
        },
    )
    output_dir = _run_output_dir(request.repo_root, draft.run_id, request.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    components, span_payload = _build_prepared_components(
        request.repo_root, source, output_dir
    )
    prepared = _advance_run(
        request.repo_root,
        draft,
        status=ExtractionRunStatus.PREPARED,
        components=components,
        lineage={
            "profile_id": profile.profile_id,
            "profile_version": profile.profile_version,
            "source_sha256": source.source_sha256,
            "output_dir": _repo_uri(request.repo_root, output_dir),
        },
    )

    if not request.allow_llm and request.category_client is None:
        loaded = get_extraction_run(request.repo_root, prepared.run_id)
        return ProductionExtractionResult(
            run=loaded,
            source_span_index=span_payload,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
        )

    model_id = resolve_category_graph_model(request.model_id)
    options = CategoryGraphExtractionOptions(
        campaign_id=source.campaign_id or "",
        session_id=source.session_id,
        session_number=_session_number(source.session_id),
        source_span_index=span_payload,
        source_text=source.source_text,
        source_artifact_id=source.source_artifact_id,
        source_ref_id=str(span_payload.get("source_ref_id") or "") or None,
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
        failed = _fail_run(
            request.repo_root,
            prepared,
            message=message,
            failure_kind=failure_kind,
            components=components,
            lineage={
                "profile_id": profile.profile_id,
                "profile_version": profile.profile_version,
                "model_id": model_id,
            },
        )
        loaded = get_extraction_run(request.repo_root, failed.run_id)
        return ProductionExtractionResult(
            run=loaded,
            source_span_index=span_payload,
            failure_kind=failure_kind,
            diagnostics=[message],
            model_id=model_id,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
        )
    except Exception as exc:  # noqa: BLE001 - persist unexpected model/API failures
        message = str(exc)
        failed = _fail_run(
            request.repo_root,
            prepared,
            message=message,
            failure_kind="model",
            components=components,
            lineage={
                "profile_id": profile.profile_id,
                "profile_version": profile.profile_version,
                "model_id": model_id,
            },
        )
        loaded = get_extraction_run(request.repo_root, failed.run_id)
        return ProductionExtractionResult(
            run=loaded,
            source_span_index=span_payload,
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
            uri=_repo_uri(request.repo_root, candidate_path),
            sha256=_file_sha256(candidate_path),
        ),
    }
    extracted = _advance_run(
        request.repo_root,
        prepared,
        status=ExtractionRunStatus.EXTRACTED,
        components=components,
        lineage={
            "profile_id": profile.profile_id,
            "profile_version": profile.profile_version,
            "model_id": model_id,
            "source_sha256": source.source_sha256,
        },
    )

    nodes = extraction.candidate_graph.get("nodes") or []
    missing_evidence = [
        node.get("node_id")
        for node in nodes
        if isinstance(node, Mapping) and not (node.get("evidence_refs") or [])
    ]
    if missing_evidence:
        message = f"candidates missing evidence_refs: {missing_evidence[:5]}"
        failed = _fail_run(
            request.repo_root,
            extracted,
            message=message,
            failure_kind="validation",
            components=components,
            incomplete_components=["evidence"],
            lineage={
                "profile_id": profile.profile_id,
                "profile_version": profile.profile_version,
                "model_id": model_id,
                "reviewable": False,
            },
        )
        loaded = get_extraction_run(request.repo_root, failed.run_id)
        return ProductionExtractionResult(
            run=loaded,
            candidate_graph=extraction.candidate_graph,
            source_span_index=span_payload,
            failure_kind="validation",
            diagnostics=[message],
            model_id=model_id,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
        )

    try:
        preview = candidate_graph_preview_from_dict(extraction.candidate_graph)
        typed_report = validate_candidate_graph_preview(preview)
    except Exception as exc:  # noqa: BLE001 - treat malformed IR as validation failure
        message = f"candidate graph preview parse failed: {exc}"
        failed = _fail_run(
            request.repo_root,
            extracted,
            message=message,
            failure_kind="validation",
            components=components,
            incomplete_components=["candidate_graph"],
            lineage={
                "profile_id": profile.profile_id,
                "profile_version": profile.profile_version,
                "model_id": model_id,
                "reviewable": False,
            },
        )
        loaded = get_extraction_run(request.repo_root, failed.run_id)
        return ProductionExtractionResult(
            run=loaded,
            candidate_graph=extraction.candidate_graph,
            source_span_index=span_payload,
            failure_kind="validation",
            diagnostics=[message],
            model_id=model_id,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
        )

    typed_errors = [
        issue
        for issue in typed_report.issues
        if str(getattr(issue, "severity", "error") or "error") == "error"
    ]
    if typed_errors:
        sample = "; ".join(
            f"{issue.code}: {issue.message}" for issue in typed_errors[:5]
        )
        message = f"candidate graph typed validation failed: {sample}"
        failed = _fail_run(
            request.repo_root,
            extracted,
            message=message,
            failure_kind="validation",
            components=components,
            incomplete_components=["candidate_graph"],
            lineage={
                "profile_id": profile.profile_id,
                "profile_version": profile.profile_version,
                "model_id": model_id,
                "reviewable": False,
                "typed_issue_count": len(typed_errors),
            },
        )
        loaded = get_extraction_run(request.repo_root, failed.run_id)
        return ProductionExtractionResult(
            run=loaded,
            candidate_graph=extraction.candidate_graph,
            source_span_index=span_payload,
            failure_kind="validation",
            diagnostics=[message],
            model_id=model_id,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
        )

    validated = _advance_run(
        request.repo_root,
        extracted,
        status=ExtractionRunStatus.VALIDATED,
        components=components,
        lineage={
            "profile_id": profile.profile_id,
            "profile_version": profile.profile_version,
            "model_id": model_id,
            "source_sha256": source.source_sha256,
        },
    )
    reviewable = _advance_run(
        request.repo_root,
        validated,
        status=ExtractionRunStatus.REVIEWABLE,
        components=components,
        lineage={
            "profile_id": profile.profile_id,
            "profile_version": profile.profile_version,
            "model_id": model_id,
            "source_sha256": source.source_sha256,
            "reviewable": True,
        },
    )
    loaded = get_extraction_run(request.repo_root, reviewable.run_id)
    return ProductionExtractionResult(
        run=loaded,
        candidate_graph=extraction.candidate_graph,
        source_span_index=span_payload,
        known_entity_mentions=extraction.known_entity_mentions,
        model_id=model_id,
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
    )
