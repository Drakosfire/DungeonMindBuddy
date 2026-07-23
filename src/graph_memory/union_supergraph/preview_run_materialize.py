from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from graph_memory.ingestion.graph_ingest_run import (
    GraphIngestArtifactKind,
    GraphIngestArtifactRef,
    GraphIngestRunManifest,
    GraphIngestRunStatus,
    GraphIngestStepState,
    GraphIngestStepStatus,
)
from graph_memory.ingestion.graph_ingest_validate import (
    FORBIDDEN_DIAGNOSTIC_FLAGS,
    PREVIEW_UNION_VALIDATION_REPORT_SCHEMA,
    PREVIEW_UNION_VALIDATION_REPORT_VERSION,
    validate_graph_ingest_run_manifest,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore
from graph_memory.union_supergraph.preview_import import (
    PREVIEW_UNION_SCHEMA,
    CandidateGraphInput,
    build_preview_union_supergraph,
)

_ALLOWED_SOURCE_STATUSES = {GraphIngestRunStatus.CANDIDATE_VALIDATION_READY}


@dataclass(frozen=True)
class PreviewUnionMaterializeOptions:
    manifest_path: Path
    output_path: Path | None = None
    update_manifest: bool = True
    repo_root: Path | None = None


@dataclass(frozen=True)
class PreviewUnionMaterializeResult:
    manifest_path: Path
    preview_union_store_path: Path
    status: GraphIngestRunStatus
    node_count: int
    edge_count: int
    evidence_ref_count: int


def materialize_preview_union_store_from_graph_ingest_run(
    options: PreviewUnionMaterializeOptions,
) -> PreviewUnionMaterializeResult:
    manifest_path = options.manifest_path.resolve()
    run_dir = manifest_path.parent
    repo_root = (options.repo_root or Path.cwd()).resolve()
    manifest_payload = _load_json(manifest_path)
    _require_valid_manifest(manifest_payload, context="input graph-ingest manifest")
    manifest = GraphIngestRunManifest.model_validate(manifest_payload)
    if manifest.status not in _ALLOWED_SOURCE_STATUSES:
        raise ValueError(
            "graph-ingest manifest must be candidate_validation_ready to materialize "
            f"preview union store, got {manifest.status.value}"
        )
    _reject_forbidden_diagnostics(
        manifest.diagnostics.model_dump(mode="json"), "manifest diagnostics"
    )

    candidate_artifact = manifest.artifacts.get("candidate_graph")
    if candidate_artifact is None:
        raise ValueError("graph-ingest manifest is missing artifacts.candidate_graph")
    from graph_memory.ingestion.graph_ingest_validate import assert_candidate_ready_evidence

    assert_candidate_ready_evidence(repo_root, manifest_payload)
    candidate_graph_path = _resolve_repo_relative_uri(candidate_artifact.uri, repo_root)
    normalized_recap_path = _resolve_required_source_path(manifest, repo_root)
    candidate_graph = _load_json(candidate_graph_path)
    _reject_forbidden_diagnostics(
        _extract_diagnostics(candidate_graph), "candidate graph diagnostics"
    )

    output_path = _default_or_safe_output_path(options.output_path, run_dir)
    report_path = output_path.with_name("preview_union_validation_report.json")

    import_input_path = run_dir / "candidate_graph_import_input.json"

    try:
        _write_json(
            import_input_path,
            _normalize_candidate_graph_for_import(candidate_graph, manifest),
        )
        store_payload = build_preview_union_supergraph(
            [
                CandidateGraphInput(
                    path=import_input_path,
                    session_id=manifest.session_id,
                    recap_path=normalized_recap_path,
                )
            ],
            focus_session_id=manifest.session_id,
            graph_id=f"{manifest.campaign_id}:preview-union-supergraph",
        )
        _rewrite_store_source_artifact_paths(
            store_payload,
            repo_root=repo_root,
        )
        store_payload["campaign_id"] = manifest.campaign_id
        store_payload.setdefault("diagnostics", {})["preview_only"] = True
        _reject_forbidden_diagnostics(
            store_payload.get("diagnostics", {}), "preview union diagnostics"
        )
        store = UnionSupergraphStore.model_validate(store_payload)
        _write_json(output_path, store.model_dump(mode="json", by_alias=True))
        validation_report = _validation_report(
            manifest, output_path, repo_root, store_payload, valid=True
        )
        _write_json(report_path, validation_report)
    except Exception:
        output_path.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)
        import_input_path.unlink(missing_ok=True)
        raise

    updated_manifest = _updated_manifest(
        manifest,
        output_path=output_path,
        report_path=report_path,
        repo_root=repo_root,
        store_payload=store_payload,
    )
    updated_manifest_path = (
        manifest_path
        if options.update_manifest
        else manifest_path.with_name(
            "graph_ingest_run_manifest.preview_union_ready.json"
        )
    )
    updated_payload = updated_manifest.model_dump(mode="json", by_alias=True)
    _require_valid_manifest(updated_payload, context="updated graph-ingest manifest")
    _write_json(updated_manifest_path, updated_payload)

    return PreviewUnionMaterializeResult(
        manifest_path=updated_manifest_path,
        preview_union_store_path=output_path,
        status=GraphIngestRunStatus.PREVIEW_UNION_STORE_READY,
        node_count=len(store_payload.get("nodes", {})),
        edge_count=len(store_payload.get("edges", {})),
        evidence_ref_count=len(store_payload.get("evidence", {})),
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _require_valid_manifest(payload: Mapping[str, Any], *, context: str) -> None:
    report = validate_graph_ingest_run_manifest(payload)
    if not report["valid"]:
        raise ValueError(f"invalid {context}: " + "; ".join(report["errors"]))


def _is_safe_relative(value: str) -> bool:
    return (
        not value.startswith(("/", "file:")) and ".." not in PurePosixPath(value).parts
    )


def _resolve_repo_relative_uri(uri: str, repo_root: Path) -> Path:
    if not _is_safe_relative(uri):
        raise ValueError(f"unsafe repo-relative artifact uri: {uri}")
    path = (repo_root / uri).resolve()
    try:
        path.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"artifact path is outside repo root: {uri}") from exc
    if not path.exists():
        raise FileNotFoundError(f"artifact path does not exist: {uri}")
    return path


def _resolve_required_source_path(
    manifest: GraphIngestRunManifest, repo_root: Path
) -> Path:
    if not manifest.source.normalized_recap_path:
        raise ValueError(
            "graph-ingest manifest is missing source.normalized_recap_path"
        )
    return _resolve_repo_relative_uri(manifest.source.normalized_recap_path, repo_root)


def _default_or_safe_output_path(output_path: Path | None, run_dir: Path) -> Path:
    path = (output_path or (run_dir / "preview_union_supergraph.json")).resolve()
    try:
        path.relative_to(run_dir.resolve())
    except ValueError as exc:
        raise ValueError(
            "preview union output_path must stay within manifest directory"
        ) from exc
    return path


def _extract_diagnostics(candidate_graph: Mapping[str, Any]) -> Mapping[str, Any]:
    graph = candidate_graph.get("candidate_graph")
    if isinstance(graph, Mapping) and isinstance(graph.get("diagnostics"), Mapping):
        return graph["diagnostics"]
    diagnostics = candidate_graph.get("diagnostics")
    return diagnostics if isinstance(diagnostics, Mapping) else {}


def _reject_forbidden_diagnostics(diagnostics: Mapping[str, Any], context: str) -> None:
    for flag in FORBIDDEN_DIAGNOSTIC_FLAGS:
        if diagnostics.get(flag) is True:
            raise ValueError(f"forbidden lifecycle flag is true in {context}: {flag}")


def _normalize_candidate_graph_for_import(
    candidate_graph: Mapping[str, Any], manifest: GraphIngestRunManifest
) -> dict[str, Any]:
    if "nodes" in candidate_graph or "candidate_graph" in candidate_graph:
        graph = dict(candidate_graph.get("candidate_graph") or candidate_graph)
    else:
        evidence_by_id = {
            str(ref.get("id")): ref
            for ref in candidate_graph.get("evidence_refs", [])
            if isinstance(ref, Mapping) and ref.get("id")
        }
        nodes = []
        for node in candidate_graph.get("candidate_nodes", []):
            if not isinstance(node, Mapping):
                continue
            nodes.append(
                {
                    "node_id": node.get("node_id") or node.get("id"),
                    "node_type": node.get("node_type") or node.get("kind"),
                    "label": node.get("label"),
                    "description": node.get("description"),
                    "evidence_refs": [
                        _normalize_evidence_ref(ref, evidence_by_id)
                        for ref in node.get("evidence_refs", [])
                    ],
                }
            )
        edges = []
        for edge in candidate_graph.get("candidate_edges", []):
            if not isinstance(edge, Mapping):
                continue
            edges.append(
                {
                    "edge_id": edge.get("edge_id") or edge.get("id"),
                    "from_node_id": edge.get("from_node_id")
                    or edge.get("source")
                    or edge.get("source_node_id"),
                    "to_node_id": edge.get("to_node_id")
                    or edge.get("target")
                    or edge.get("target_node_id"),
                    "relationship_type": edge.get("relationship_type")
                    or edge.get("kind"),
                    "label": edge.get("label"),
                    "evidence_refs": [
                        _normalize_evidence_ref(ref, evidence_by_id)
                        for ref in edge.get("evidence_refs", [])
                    ],
                }
            )
        graph = {"nodes": nodes, "edges": edges}
    graph["campaign_id"] = graph.get("campaign_id") or manifest.campaign_id
    graph["session_id"] = graph.get("session_id") or manifest.session_id
    graph["source_artifact_ids"] = graph.get("source_artifact_ids") or [
        manifest.source.source_artifact_id
        or f"artifact:recap:{manifest.campaign_id}:{manifest.session_id}"
    ]
    return graph


def _normalize_evidence_ref(
    ref: Any, evidence_by_id: Mapping[str, Any]
) -> dict[str, Any]:
    ref_map = evidence_by_id.get(str(ref), {}) if not isinstance(ref, Mapping) else ref
    span_id = (
        ref_map.get("source_span_ref_id")
        or ref_map.get("span_id")
        or ref_map.get("source_anchor_id")
    )
    return {
        "source_span_ref_id": span_id,
        "source_anchor_id": span_id,
        "can_open_source": ref_map.get("can_open_source", True),
        "can_highlight_span": ref_map.get("can_highlight_span", True),
        "anchor_quotes": ref_map.get("anchor_quotes", []),
        "label": ref_map.get("text_excerpt") or ref_map.get("label"),
    }


def _rewrite_store_source_artifact_paths(
    store_payload: dict[str, Any], *, repo_root: Path
) -> None:
    source_artifacts = store_payload.get("source_artifacts")
    if not isinstance(source_artifacts, dict):
        return
    for artifact in source_artifacts.values():
        if not isinstance(artifact, dict):
            continue
        for key in ("uri", "recap_path"):
            value = artifact.get(key)
            if not isinstance(value, str):
                continue
            path = Path(value)
            if not path.is_absolute():
                continue
            artifact[key] = _safe_artifact_uri(path, repo_root)


def _validation_report(
    manifest: GraphIngestRunManifest,
    output_path: Path,
    repo_root: Path,
    store_payload: Mapping[str, Any],
    *,
    valid: bool,
) -> dict[str, Any]:
    import hashlib

    store_digest = f"sha256:{hashlib.sha256(output_path.read_bytes()).hexdigest()}"
    return {
        "schema": PREVIEW_UNION_VALIDATION_REPORT_SCHEMA,
        "version": PREVIEW_UNION_VALIDATION_REPORT_VERSION,
        "campaign_id": manifest.campaign_id,
        "session_id": manifest.session_id,
        "preview_union_store_path": _safe_artifact_uri(output_path, repo_root),
        "preview_union_store_sha256": store_digest,
        "valid": valid,
        "errors": [],
        "warnings": [],
        "diagnostics": {
            "preview_only": True,
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
            "preview_import": bool(
                store_payload.get("diagnostics", {}).get("preview_import")
            ),
        },
    }


def _updated_manifest(
    manifest: GraphIngestRunManifest,
    *,
    output_path: Path,
    report_path: Path,
    repo_root: Path,
    store_payload: Mapping[str, Any],
) -> GraphIngestRunManifest:
    import hashlib

    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    artifacts = dict(manifest.artifacts)
    store_digest = f"sha256:{hashlib.sha256(output_path.read_bytes()).hexdigest()}"
    report_digest = f"sha256:{hashlib.sha256(report_path.read_bytes()).hexdigest()}"
    store_ref = GraphIngestArtifactRef(
        kind=GraphIngestArtifactKind.PREVIEW_UNION_STORE,
        uri=_safe_artifact_uri(output_path, repo_root),
        schema=PREVIEW_UNION_SCHEMA,
        exists=True,
        preview_only=True,
        sha256=store_digest,
    )
    report_ref = GraphIngestArtifactRef(
        kind=GraphIngestArtifactKind.PREVIEW_UNION_VALIDATION_REPORT,
        uri=_safe_artifact_uri(report_path, repo_root),
        schema=PREVIEW_UNION_VALIDATION_REPORT_SCHEMA,
        exists=True,
        preview_only=True,
        sha256=report_digest,
    )
    artifacts["preview_union_store"] = store_ref
    artifacts["preview_union_validation_report"] = report_ref
    steps = [
        s
        for s in manifest.steps
        if s.id not in {"build_preview_union_store", "validate_preview_union_store"}
    ]
    steps.extend(
        [
            GraphIngestStepStatus(
                id="build_preview_union_store",
                label="Build preview union store",
                state=GraphIngestStepState.COMPLETE,
                started_at=now,
                completed_at=now,
                summary="Preview union-supergraph store materialized from candidate graph.",
                artifact_refs=[store_ref],
            ),
            GraphIngestStepStatus(
                id="validate_preview_union_store",
                label="Validate preview union store",
                state=GraphIngestStepState.COMPLETE,
                started_at=now,
                completed_at=now,
                summary="Preview union-supergraph store validated as preview-only.",
                artifact_refs=[report_ref],
            ),
        ]
    )
    evidence = (
        store_payload.get("evidence", {})
        if isinstance(store_payload.get("evidence"), Mapping)
        else {}
    )
    manifest.status = GraphIngestRunStatus.PREVIEW_UNION_STORE_READY
    manifest.updated_at = now
    manifest.artifacts = artifacts
    manifest.steps = steps
    manifest.health.preview_union_store_valid = True
    manifest.health.node_count = len(store_payload.get("nodes", {}))
    manifest.health.edge_count = len(store_payload.get("edges", {}))
    manifest.health.evidence_ref_count = len(evidence)
    manifest.health.resolvable_evidence_ref_count = len(evidence)
    manifest.health.openable_evidence_ref_count = sum(
        1 for item in evidence.values() if item.get("can_open_source")
    )
    manifest.health.highlightable_evidence_ref_count = sum(
        1 for item in evidence.values() if item.get("can_highlight_span")
    )
    manifest.diagnostics.preview_only = True
    manifest.diagnostics.candidate_extraction = True
    manifest.diagnostics.preview_import = True
    manifest.diagnostics.canon_promotion = False
    manifest.diagnostics.approved_memory_write = False
    manifest.diagnostics.corpus_mutation = False
    manifest.diagnostics.production_retrieval = False
    manifest.diagnostics.agent_interaction_connected = False
    manifest.diagnostics.runtime_projection_connected = False
    manifest.projection = None
    manifest.next_actions = ["open_projection_preview"]
    manifest.errors = []
    return manifest


def _safe_artifact_uri(path: Path, repo_root: Path) -> str:
    relative = path.resolve().relative_to(repo_root.resolve())
    if not _is_safe_relative(relative.as_posix()):
        raise ValueError(f"unsafe artifact path: {path}")
    return relative.as_posix()
