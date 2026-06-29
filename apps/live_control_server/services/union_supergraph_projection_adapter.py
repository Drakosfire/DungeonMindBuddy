from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.live_control_server.config import repo_root
from graph_memory.ingestion.graph_ingest_run import (
    GraphIngestArtifactKind,
    GraphIngestRunManifest,
    GraphIngestRunStatus,
)
from graph_memory.ingestion.graph_ingest_validate import (
    FORBIDDEN_DIAGNOSTIC_FLAGS,
    validate_graph_ingest_run_manifest,
)
from graph_memory.projection import RecapGraphProjection, build_recap_graph_projection
from graph_memory.projection.recap_projection import RecapProjectionSourceSpan
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
    parse_union_supergraph_store,
)
from graph_memory.union_supergraph.preview_import import (
    CandidateGraphInput,
    build_preview_union_supergraph,
)

SESSION_22_ANCHOR_QUOTE_N3_RUN2_REL = (
    "evals/graph_memory_layer/artifacts/category_graph_model_study/2026-06-26/"
    "anchor_quote_n3/session_22_gpt-5-4-mini_run2/candidate_output.json"
)
SESSION_22_RECAP_REL = (
    "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/"
    "_normalized/Session 22 - Mireward Road and Lysandro.md"
)
SESSION_23_GOLD_REL = (
    "evals/graph_memory_layer/examples/session_23_candidate_graph_gold/candidate_graph_gold.json"
)
SESSION_23_RECAP_REL = (
    "evals/graph_memory_layer/examples/session_23_recap_ingest/expected_normalized_recap.md"
)
TWO_SESSION_PREVIEW_SOURCE = "s22-anchor-quote-n3-s23-gold"


def build_plan_union_supergraph_projection(
    *,
    session_id: str,
    store_path: Path | None = None,
    preview_source: str | None = None,
    graph_run_manifest_path: Path | None = None,
    preview_union_store_path: Path | None = None,
) -> RecapGraphProjection:
    """Build a backend-neutral graph projection for a /plan session lens."""

    if graph_run_manifest_path is not None:
        store = load_preview_union_store_from_graph_run_manifest(graph_run_manifest_path)
    elif preview_union_store_path is not None:
        store = load_preview_union_store(preview_union_store_path)
    elif store_path is not None:
        store = load_union_supergraph_store(store_path)
    elif preview_source:
        store = _build_preview_store(preview_source, focus_session_id=session_id)
    else:
        store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    markdown = _load_focus_recap_markdown_from_store(store, session_id=session_id)
    source_spans = _load_manifest_source_spans(graph_run_manifest_path) if graph_run_manifest_path is not None else []
    return build_recap_graph_projection(store, session_id=session_id, markdown=markdown, source_spans=source_spans)



def _load_manifest_source_spans(graph_run_manifest_path: Path) -> list[RecapProjectionSourceSpan]:
    root = repo_root().resolve()
    payload = json.loads(_resolve_repo_contained_path(graph_run_manifest_path, root).read_text(encoding="utf-8"))
    uri = ((payload.get("source") or {}).get("source_span_index_uri"))
    if not isinstance(uri, str) or not uri:
        return []
    index_path = _resolve_repo_contained_path(root / uri, root)
    if not index_path.is_file():
        return []
    index = json.loads(index_path.read_text(encoding="utf-8"))
    spans: list[RecapProjectionSourceSpan] = []
    for span in index.get("spans", []):
        if not isinstance(span, dict):
            continue
        span_id = span.get("span_id") or span.get("source_span_ref_id")
        if not isinstance(span_id, str):
            continue
        spans.append(
            RecapProjectionSourceSpan(
                span_id=span_id,
                kind=str(span.get("kind") or "span"),
                ordinal=span.get("ordinal") if isinstance(span.get("ordinal"), int) else None,
                text_excerpt=str(span.get("text_excerpt") or span.get("text") or "")[:240] or None,
                line_start=span.get("line_start") if isinstance(span.get("line_start"), int) else None,
                line_end=span.get("line_end") if isinstance(span.get("line_end"), int) else None,
            )
        )
    return spans

def load_preview_union_store_from_graph_run_manifest(
    graph_run_manifest_path: Path,
) -> Any:
    """Load a preview-only union-supergraph store referenced by a graph-ingest manifest."""

    root = repo_root().resolve()
    manifest_path = _resolve_repo_contained_path(graph_run_manifest_path, root)
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = GraphIngestRunManifest.model_validate(manifest_payload)
    validation = validate_graph_ingest_run_manifest(manifest_payload)
    non_path_errors = [
        error
        for error in validation["errors"]
        if not (
            error.startswith("unsafe repo-relative path at $")
            and _manifest_path_error_is_repo_contained(error, root)
        )
    ]
    if non_path_errors:
        raise ValueError("invalid graph-ingest manifest: " + "; ".join(non_path_errors))
    if manifest.status != GraphIngestRunStatus.PREVIEW_UNION_STORE_READY:
        raise ValueError(
            "graph-ingest manifest must be preview_union_store_ready, "
            f"got {manifest.status.value}"
        )
    _reject_forbidden_lifecycle_flags(
        manifest.diagnostics.model_dump(mode="json"), "manifest diagnostics"
    )

    artifact = manifest.artifacts.get(GraphIngestArtifactKind.PREVIEW_UNION_STORE.value)
    if artifact is None:
        raise ValueError("graph-ingest manifest is missing artifacts.preview_union_store")
    if artifact.preview_only is not True:
        raise ValueError("artifacts.preview_union_store must be preview_only")
    store_path = _resolve_repo_contained_path(Path(artifact.uri), root)
    return load_preview_union_store(store_path)


def _manifest_path_error_is_repo_contained(error: str, root: Path) -> bool:
    _prefix, _separator, value = error.rpartition(": ")
    if not value:
        return False
    try:
        _resolve_repo_contained_path(Path(value), root)
    except (FileNotFoundError, ValueError):
        return False
    return True


def load_preview_union_store(preview_union_store_path: Path) -> Any:
    root = repo_root().resolve()
    store_path = _resolve_repo_contained_path(preview_union_store_path, root)
    payload = json.loads(store_path.read_text(encoding="utf-8"))
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise ValueError("preview union store is missing diagnostics")
    if diagnostics.get("preview_only") is not True:
        raise ValueError("preview union store diagnostics.preview_only must be true")
    _reject_forbidden_lifecycle_flags(diagnostics, "preview union store diagnostics")
    return parse_union_supergraph_store(payload)


def _resolve_repo_contained_path(path: Path, root: Path) -> Path:
    value = str(path).replace("\\", "/")
    if value.startswith("file:"):
        raise ValueError(f"unsafe repo-contained path: {path}")
    if ".." in Path(value).parts:
        raise ValueError(f"unsafe repo-contained path: {path}")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path is outside repo root: {path}") from exc
    if not resolved.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    return resolved


def _reject_forbidden_lifecycle_flags(diagnostics: dict[str, Any], context: str) -> None:
    for flag in FORBIDDEN_DIAGNOSTIC_FLAGS:
        if diagnostics.get(flag) is True:
            raise ValueError(f"forbidden lifecycle flag is true in {context}: {flag}")


def _load_focus_recap_markdown(*, session_id: str, store_path: Path) -> str | None:
    store = load_union_supergraph_store(store_path)
    return _load_focus_recap_markdown_from_store(store, session_id=session_id)


def _load_focus_recap_markdown_from_store(
    store: Any,
    *,
    session_id: str,
) -> str | None:
    recap_artifact = next(
        (
            artifact
            for artifact in store.source_artifacts.values()
            if artifact.source_domain == "recap" and artifact.session_id == session_id
        ),
        None,
    )
    if recap_artifact is None:
        return None

    root = repo_root().resolve()
    recap_path = getattr(recap_artifact, "recap_path", None)
    if recap_path:
        path = _resolve_repo_contained_path(Path(str(recap_path)), root)
        return _strip_yaml_frontmatter(path.read_text(encoding="utf-8"))
    if not recap_artifact.ingest_run_bundle_uri:
        return None
    manifest_path = _resolve_repo_contained_path(
        Path(str(recap_artifact.ingest_run_bundle_uri)), root
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    input_path = _resolve_repo_contained_path(
        Path(str(manifest["source"]["input_path_record"])), root
    )
    return _strip_yaml_frontmatter(input_path.read_text(encoding="utf-8"))


def _strip_yaml_frontmatter(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return markdown
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1 :]).lstrip("\n")
    return markdown


def build_plan_union_supergraph_projection_payload(
    *,
    session_id: str,
    store_path: Path | None = None,
    preview_source: str | None = None,
    graph_run_manifest_path: Path | None = None,
    preview_union_store_path: Path | None = None,
) -> dict[str, Any]:
    """Build a JSON-safe projection payload for future API route integration."""

    projection = build_plan_union_supergraph_projection(
        session_id=session_id,
        store_path=store_path,
        preview_source=preview_source,
        graph_run_manifest_path=graph_run_manifest_path,
        preview_union_store_path=preview_union_store_path,
    )
    return projection.model_dump(mode="json")


def _build_preview_store(preview_source: str, *, focus_session_id: str) -> Any:
    if preview_source != TWO_SESSION_PREVIEW_SOURCE:
        raise ValueError(f"unknown union supergraph preview_source: {preview_source}")
    root = repo_root()
    payload = build_preview_union_supergraph(
        [
            CandidateGraphInput(
                path=root / SESSION_22_ANCHOR_QUOTE_N3_RUN2_REL,
                session_id="session-22",
                recap_path=root / SESSION_22_RECAP_REL,
            ),
            CandidateGraphInput(
                path=root / SESSION_23_GOLD_REL,
                session_id="session-23",
                recap_path=root / SESSION_23_RECAP_REL,
            ),
        ],
        focus_session_id=focus_session_id,
    )
    return parse_union_supergraph_store(payload)
