from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from graph_memory.ingestion import (
    GRAPH_INGEST_RUN_MANIFEST_SCHEMA,
    GRAPH_INGEST_RUN_MANIFEST_VERSION,
    GraphIngestArtifactKind,
    GraphIngestArtifactRef,
    GraphIngestDiagnostics,
    GraphIngestHealth,
    GraphIngestRunManifest,
    GraphIngestRunStatus,
    GraphIngestSource,
    GraphIngestStepState,
    GraphIngestStepStatus,
)

ComparisonMode = Literal["none", "gold_if_available", "required_gold"]


@dataclass(frozen=True)
class GraphPreviewRunnerOptions:
    campaign_id: str
    session_id: str
    normalized_recap_path: Path
    output_dir: Path
    source_label: str | None = None
    model_id: str | None = None
    allow_llm: bool = False
    comparison_mode: ComparisonMode = "none"
    gold_path: Path | None = None
    source_domain: str = "recap"
    run_id: str | None = None
    candidate_graph_path: Path | None = None


@dataclass(frozen=True)
class GraphPreviewRunnerResult:
    manifest_path: Path
    candidate_graph_path: Path | None
    validation_report_path: Path | None
    source_span_bundle_dir: Path | None
    output_dir: Path
    status: GraphIngestRunStatus


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _repo_root() -> Path:
    return Path.cwd().resolve()


def _validate_safe_relative_path(path: Path, *, field_name: str) -> None:
    if path.is_absolute():
        raise ValueError(f"{field_name} must be repo-relative, not absolute: {path}")
    if ".." in PurePosixPath(path.as_posix()).parts:
        raise ValueError(f"{field_name} must not contain path traversal: {path}")


def safe_relative_artifact_uri(path: Path, repo_root: Path | None = None) -> str:
    root = (repo_root or _repo_root()).resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"artifact path is outside repository root: {path}") from exc
    _validate_safe_relative_path(relative, field_name="artifact uri")
    return relative.as_posix()


def ensure_output_dir(path: Path) -> Path:
    _validate_safe_relative_path(path, field_name="output_dir")
    output_dir = (_repo_root() / path).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    if not slug:
        raise ValueError("campaign_id and session_id must not be blank")
    return slug


def _copy_source_recap(source: Path, output_dir: Path) -> Path:
    target = output_dir / "normalized_recap_source.md"
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    return target


def _write_source_span_bundle(
    *,
    recap_text: str,
    output_dir: Path,
    campaign_id: str,
    session_id: str,
    source_uri: str,
    source_sha256: str,
) -> tuple[Path, Path, Path]:
    source_spans_dir = output_dir / "source_spans"
    source_spans_dir.mkdir(parents=True, exist_ok=True)
    source_span_path = source_spans_dir / "recap_full_text.md"
    source_span_path.write_text(recap_text)

    source_span_index = {
        "schema": "dmb_source_span_index_v0",
        "version": "0.1",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "source_sha256": source_sha256,
        "spans": [
            {
                "span_id": f"{session_id}:recap:full_text",
                "source_uri": source_uri,
                "local_uri": safe_relative_artifact_uri(source_span_path),
                "char_start": 0,
                "char_end": len(recap_text),
                "preview_only": True,
            }
        ],
    }
    source_span_index_path = output_dir / "source_span_index.json"
    write_json(source_span_index_path, source_span_index)

    provenance_index = {
        "schema": "dmb_source_provenance_index_v0",
        "version": "0.1",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "source_artifacts": [
            {
                "artifact_id": f"artifact:recap:{campaign_id}:{session_id}",
                "uri": source_uri,
                "sha256": source_sha256,
                "preview_only": True,
            }
        ],
    }
    provenance_index_path = output_dir / "provenance_index.json"
    write_json(provenance_index_path, provenance_index)
    return source_spans_dir, source_span_index_path, provenance_index_path


def _candidate_counts(candidate_graph: dict[str, Any]) -> GraphIngestHealth:
    ignored = candidate_graph.get("ignored_or_deferred_candidates", [])
    ignored_count = len(ignored) if isinstance(ignored, list) else 0
    evidence_refs = candidate_graph.get("evidence_refs", [])
    evidence_ref_count = len(evidence_refs) if isinstance(evidence_refs, list) else 0
    return GraphIngestHealth(
        candidate_graph_valid=True,
        node_count=len(candidate_graph.get("candidate_nodes", [])),
        edge_count=len(candidate_graph.get("candidate_edges", [])),
        beat_count=len(candidate_graph.get("session_beats", [])),
        ignored_count=ignored_count,
        deferred_count=0,
        evidence_ref_count=evidence_ref_count,
        resolvable_evidence_ref_count=evidence_ref_count,
        openable_evidence_ref_count=evidence_ref_count,
        highlightable_evidence_ref_count=evidence_ref_count,
    )


def _write_validation_report(
    *,
    output_dir: Path,
    campaign_id: str,
    session_id: str,
    candidate_graph_path: Path,
    candidate_graph: dict[str, Any],
) -> Path:
    errors: list[str] = []
    warnings: list[str] = []
    if not candidate_graph_path.exists():
        errors.append("candidate graph file does not exist")
    has_candidates = bool(candidate_graph.get("candidate_nodes")) or bool(
        candidate_graph.get("candidate_edges")
    )
    if has_candidates and "evidence_refs" not in candidate_graph:
        warnings.append("candidate graph has candidates but no evidence_refs section")
    diagnostics = candidate_graph.get("diagnostics", {})
    for flag in (
        "canon_promotion",
        "approved_memory_write",
        "corpus_mutation",
        "production_retrieval",
    ):
        if isinstance(diagnostics, dict) and diagnostics.get(flag):
            errors.append(f"forbidden lifecycle flag is true: {flag}")
    report = {
        "schema": "dmb_candidate_graph_validation_report_v0",
        "version": "0.1",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "candidate_graph_path": safe_relative_artifact_uri(candidate_graph_path),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "diagnostics": {
            "preview_only": True,
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
        },
    }
    report_path = output_dir / "candidate_validation_report.json"
    write_json(report_path, report)
    return report_path


def _artifact(
    kind: GraphIngestArtifactKind,
    path: Path,
    schema: str | None = None,
    sha256: str | None = None,
) -> GraphIngestArtifactRef:
    return GraphIngestArtifactRef(
        kind=kind,
        uri=safe_relative_artifact_uri(path),
        schema=schema,
        sha256=sha256,
        exists=path.exists(),
        preview_only=True,
    )


def run_graph_preview_extraction(
    options: GraphPreviewRunnerOptions,
) -> GraphPreviewRunnerResult:
    campaign_id = _slug(options.campaign_id)
    session_id = _slug(options.session_id)
    if options.comparison_mode not in ("none", "gold_if_available", "required_gold"):
        raise ValueError(f"unsupported comparison_mode: {options.comparison_mode}")
    if options.comparison_mode == "required_gold" and (
        options.gold_path is None or not options.gold_path.exists()
    ):
        raise FileNotFoundError("required_gold mode requires an existing gold_path")
    if options.allow_llm:
        raise NotImplementedError(
            "live LLM category extraction is not wired in this preview runner yet"
        )
    normalized_recap_path = options.normalized_recap_path
    if not normalized_recap_path.exists():
        raise FileNotFoundError(
            f"normalized recap does not exist: {normalized_recap_path}"
        )

    output_dir = ensure_output_dir(options.output_dir)
    recap_text = normalized_recap_path.read_text()
    recap_sha256 = compute_sha256(normalized_recap_path)
    copied_recap_path = _copy_source_recap(normalized_recap_path, output_dir)
    copied_recap_sha256 = compute_sha256(copied_recap_path)
    source_uri = safe_relative_artifact_uri(copied_recap_path)
    source_spans_dir, source_span_index_path, provenance_index_path = (
        _write_source_span_bundle(
            recap_text=recap_text,
            output_dir=output_dir,
            campaign_id=campaign_id,
            session_id=session_id,
            source_uri=source_uri,
            source_sha256=recap_sha256,
        )
    )

    artifacts: dict[str, GraphIngestArtifactRef] = {
        "normalized_recap": _artifact(
            GraphIngestArtifactKind.NORMALIZED_RECAP,
            copied_recap_path,
            "dmb_normalized_recap_v0",
            copied_recap_sha256,
        ),
        "source_span_bundle": _artifact(
            GraphIngestArtifactKind.SOURCE_SPAN_BUNDLE,
            source_spans_dir,
            "dmb_source_span_bundle_v0",
        ),
        "source_span_index": _artifact(
            GraphIngestArtifactKind.SOURCE_SPAN_INDEX,
            source_span_index_path,
            "dmb_source_span_index_v0",
        ),
        "provenance_index": _artifact(
            GraphIngestArtifactKind.PROVENANCE_INDEX,
            provenance_index_path,
            "dmb_source_provenance_index_v0",
        ),
    }
    status = GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY
    candidate_graph_path: Path | None = None
    validation_report_path: Path | None = None
    health = GraphIngestHealth()
    candidate_extraction = False

    if options.candidate_graph_path is not None:
        if not options.candidate_graph_path.exists():
            raise FileNotFoundError(
                f"candidate graph does not exist: {options.candidate_graph_path}"
            )
        candidate_graph = json.loads(options.candidate_graph_path.read_text())
        candidate_graph_path = output_dir / "candidate_graph.json"
        write_json(candidate_graph_path, candidate_graph)
        validation_report_path = _write_validation_report(
            output_dir=output_dir,
            campaign_id=campaign_id,
            session_id=session_id,
            candidate_graph_path=candidate_graph_path,
            candidate_graph=candidate_graph,
        )
        artifacts["candidate_graph"] = _artifact(
            GraphIngestArtifactKind.CANDIDATE_GRAPH,
            candidate_graph_path,
            "dmb_candidate_graph_preview_ir_v0",
        )
        artifacts["candidate_validation_report"] = _artifact(
            GraphIngestArtifactKind.CANDIDATE_VALIDATION_REPORT,
            validation_report_path,
            "dmb_candidate_graph_validation_report_v0",
        )
        status = GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
        health = _candidate_counts(candidate_graph)
        candidate_extraction = True

    now = _now_iso()
    run_id = (
        options.run_id
        or f"graph-ingest:{campaign_id}:{session_id}:{now.replace('-', '').replace(':', '')}"
    )
    steps = [
        GraphIngestStepStatus(
            id="stage_or_select_source",
            label="Stage or select source",
            state=GraphIngestStepState.COMPLETE,
            started_at=now,
            completed_at=now,
            summary="Normalized recap source selected for parameterized preview ingestion.",
            artifact_refs=[artifacts["normalized_recap"]],
        ),
        GraphIngestStepStatus(
            id="build_source_span_bundle",
            label="Build source span bundle",
            state=GraphIngestStepState.COMPLETE,
            started_at=now,
            completed_at=now,
            summary="Lightweight source-span bundle generated from the normalized recap.",
            artifact_refs=[
                artifacts["source_span_bundle"],
                artifacts["source_span_index"],
                artifacts["provenance_index"],
            ],
        ),
    ]
    if candidate_graph_path is None:
        steps.append(
            GraphIngestStepStatus(
                id="extract_candidate_graph",
                label="Extract candidate graph",
                state=GraphIngestStepState.SKIPPED,
                summary="Skipped because allow_llm is false and no candidate graph fixture was supplied.",
            )
        )
    else:
        steps.extend(
            [
                GraphIngestStepStatus(
                    id="extract_candidate_graph",
                    label="Extract candidate graph",
                    state=GraphIngestStepState.COMPLETE,
                    started_at=now,
                    completed_at=now,
                    summary="Existing candidate graph artifact wrapped for preview ingestion.",
                    artifact_refs=[artifacts["candidate_graph"]],
                ),
                GraphIngestStepStatus(
                    id="validate_candidate_graph",
                    label="Validate candidate graph",
                    state=GraphIngestStepState.COMPLETE,
                    started_at=now,
                    completed_at=now,
                    summary="Shallow candidate graph validation report written.",
                    artifact_refs=[artifacts["candidate_validation_report"]],
                ),
            ]
        )

    manifest = GraphIngestRunManifest(
        schema=GRAPH_INGEST_RUN_MANIFEST_SCHEMA,
        version=GRAPH_INGEST_RUN_MANIFEST_VERSION,
        run_id=run_id,
        campaign_id=campaign_id,
        session_id=session_id,
        status=status,
        created_at=now,
        updated_at=now,
        source=GraphIngestSource(
            source_artifact_id=f"artifact:recap:{campaign_id}:{session_id}",
            source_domain=options.source_domain,
            normalized_recap_path=source_uri,
            normalized_recap_sha256=recap_sha256,
            source_label=options.source_label,
            source_span_bundle_uri=artifacts["source_span_bundle"].uri,
            source_span_index_uri=artifacts["source_span_index"].uri,
            provenance_index_uri=artifacts["provenance_index"].uri,
        ),
        steps=steps,
        artifacts=artifacts,
        health=health,
        diagnostics=GraphIngestDiagnostics(candidate_extraction=candidate_extraction),
        projection=None,
        warnings=[]
        if options.comparison_mode != "gold_if_available"
        or (options.gold_path and options.gold_path.exists())
        else [
            "gold comparison skipped because gold_path was not supplied or does not exist"
        ],
        errors=[],
        next_actions=["extract_candidate_graph"]
        if candidate_graph_path is None
        else ["materialize_preview_union_store"],
    )
    manifest_path = output_dir / "graph_ingest_run_manifest.json"
    write_json(manifest_path, manifest.model_dump(mode="json", by_alias=True))
    return GraphPreviewRunnerResult(
        manifest_path=manifest_path,
        candidate_graph_path=candidate_graph_path,
        validation_report_path=validation_report_path,
        source_span_bundle_dir=source_spans_dir,
        output_dir=output_dir,
        status=status,
    )
