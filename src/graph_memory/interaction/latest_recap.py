"""Server-owned latest-recap comparison context for Hermes S1."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.services.recap_artifacts import (
    RecapArtifactRecord,
    list_recap_artifact_records,
)
from graph_memory.world_supergraph.storage import load_current_world_graph

LATEST_RECAP_CHANGE_SCHEMA = "dmb_latest_recap_change_context_v1"

LatestRecapOutcome = Literal[
    "changed",
    "no_change",
    "memory_lag",
    "unknown",
    "source_unavailable",
]
LatestRecapContextStatus = Literal["ready", "unknown", "source_unavailable"]


class LatestRecapReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    campaign_id: str
    session_id: str
    source_artifact_id: str | None = None
    source_recap_path: str
    source_sha256: str | None = None


class LatestRecapComparisonBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["latest_admitted_recap_to_graph_head"] = (
        "latest_admitted_recap_to_graph_head"
    )
    recap_session_id: str
    graph_revision_id: str | None = None
    graph_latest_session_id: str | None = None


class LatestRecapChangeContext(BaseModel):
    """Bounded metadata for a latest-recap sensemaking turn.

    This context identifies the comparison boundary. It deliberately does not
    include recap prose, corpus paths for model discovery, or any write handle.
    """

    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_latest_recap_change_context_v1"] = Field(
        default=LATEST_RECAP_CHANGE_SCHEMA,
        alias="schema",
    )
    status: LatestRecapContextStatus
    campaign_id: str
    latest_recap: LatestRecapReference | None = None
    comparison_boundary: LatestRecapComparisonBoundary | None = None
    outcome: LatestRecapOutcome
    memory_lag: bool = False
    graph_session_ids: list[str] = Field(default_factory=list)
    graph_object_ids: list[str] = Field(default_factory=list)
    diagnostic_codes: list[str] = Field(default_factory=list)


_SESSION_NUMBER = re.compile(r"(?:^|[-_ ])(\d+)$")


def _session_number(session_id: Any) -> int | None:
    raw = str(session_id or "").strip()
    match = _SESSION_NUMBER.search(raw)
    return int(match.group(1)) if match else None


def _normalize_session_id(session_id: Any) -> str | None:
    raw = str(session_id or "").strip()
    if not raw:
        return None
    number = _session_number(raw)
    return f"session-{number}" if number is not None else raw


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="json", by_alias=True)
        if isinstance(dumped, Mapping):
            return dumped
    return {}


def _record_session_number(record: RecapArtifactRecord) -> int | None:
    return _session_number(record.session_id)


def _latest_record(records: Sequence[RecapArtifactRecord]) -> RecapArtifactRecord | None:
    numeric = [record for record in records if _record_session_number(record) is not None]
    if not numeric:
        return None
    return max(
        numeric,
        key=lambda record: (_record_session_number(record) or -1, record.session_id),
    )


def _source_path(root: Path, source_recap_path: str) -> Path:
    candidate = Path(source_recap_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    resolved.relative_to(root.resolve())
    return resolved


def read_admitted_recap_excerpt(
    *,
    root: Path,
    source_recap_path: str,
    max_chars: int = 3500,
) -> str | None:
    """Server-owned read of a registry-admitted recap path (never model-supplied).

    Returns frontmatter-stripped body text truncated at a paragraph boundary.
    Returns None when the path is outside root, missing, or empty.
    """
    try:
        path = _source_path(root, source_recap_path)
        if not path.is_file():
            return None
        raw = path.read_text(encoding="utf-8")
    except (OSError, ValueError, UnicodeError):
        return None

    from src.ingestion.frontmatter import FrontmatterParseError, split_frontmatter

    try:
        _, body = split_frontmatter(raw)
    except FrontmatterParseError:
        body = raw

    body = body.strip()
    if not body:
        return None
    if len(body) <= max_chars:
        return body

    clipped = body[:max_chars]
    paragraph_break = clipped.rfind("\n\n")
    if paragraph_break >= max_chars // 2:
        clipped = clipped[:paragraph_break]
    return clipped.rstrip() + "\n\n[… admitted recap excerpt truncated …]"


def _graph_session_ids(store: Mapping[str, Any], campaign_id: str) -> list[str]:
    sessions: set[str] = set()
    source_artifacts = _as_mapping(store.get("source_artifacts"))
    for raw_artifact in source_artifacts.values():
        artifact = _as_mapping(raw_artifact)
        if str(artifact.get("campaign_id") or campaign_id) != campaign_id:
            continue
        session_id = _normalize_session_id(artifact.get("session_id"))
        if session_id is not None:
            sessions.add(session_id)

    for raw_edge in _as_mapping(store.get("edges")).values():
        edge = _as_mapping(raw_edge)
        if str(edge.get("state", {}).get("campaign_scope") or campaign_id) != campaign_id:
            continue
        for value in edge.get("session_ids") or []:
            session_id = _normalize_session_id(value)
            if session_id is not None:
                sessions.add(session_id)

    return sorted(
        sessions,
        key=lambda session_id: (_session_number(session_id) or -1, session_id),
    )


def _object_ids_for_session(store: Mapping[str, Any], session_id: str) -> list[str]:
    evidence_by_id = {
        str(evidence_id): _as_mapping(evidence)
        for evidence_id, evidence in _as_mapping(store.get("evidence")).items()
    }

    def evidence_matches(evidence_ids: Sequence[Any]) -> bool:
        for evidence_id in evidence_ids:
            evidence = evidence_by_id.get(str(evidence_id), {})
            if _normalize_session_id(evidence.get("session_id")) == session_id:
                return True
            source_artifact_id = evidence.get("source_artifact_id")
            artifact = _as_mapping(
                _as_mapping(store.get("source_artifacts")).get(source_artifact_id)
            )
            if _normalize_session_id(artifact.get("session_id")) == session_id:
                return True
        return False

    object_ids: list[str] = []
    for node_id, raw_node in _as_mapping(store.get("nodes")).items():
        if evidence_matches(_as_mapping(raw_node).get("evidence_ref_ids") or []):
            object_ids.append(str(node_id))
    for edge_id, raw_edge in _as_mapping(store.get("edges")).items():
        edge = _as_mapping(raw_edge)
        if session_id in {
            normalized
            for normalized in (
                _normalize_session_id(value) for value in edge.get("session_ids") or []
            )
            if normalized is not None
        } or evidence_matches(edge.get("evidence_ref_ids") or []):
            object_ids.append(str(edge_id))
    return sorted(dict.fromkeys(object_ids))


def _unknown_context(
    *,
    campaign_id: str,
    outcome: Literal["unknown", "source_unavailable"],
    diagnostic_code: str,
) -> LatestRecapChangeContext:
    status: LatestRecapContextStatus = (
        "source_unavailable" if outcome == "source_unavailable" else "unknown"
    )
    return LatestRecapChangeContext(
        status=status,
        campaign_id=campaign_id,
        outcome=outcome,
        diagnostic_codes=[diagnostic_code],
    )


def build_latest_recap_change_context(
    *,
    root: Path,
    campaign_id: str,
    graph_revision_id: str | None,
    graph_store: Mapping[str, Any],
    records: Sequence[RecapArtifactRecord],
) -> LatestRecapChangeContext:
    """Build an S1 comparison context without reading or mutating corpus prose."""
    latest = _latest_record(records)
    if latest is None:
        return _unknown_context(
            campaign_id=campaign_id,
            outcome="unknown",
            diagnostic_code="latest_admitted_recap_not_found",
        )

    try:
        if not _source_path(root, latest.source_recap_path).is_file():
            return _unknown_context(
                campaign_id=campaign_id,
                outcome="source_unavailable",
                diagnostic_code="latest_recap_source_unavailable",
            )
    except (OSError, ValueError):
        return _unknown_context(
            campaign_id=campaign_id,
            outcome="source_unavailable",
            diagnostic_code="latest_recap_source_unavailable",
        )

    recap_session_id = _normalize_session_id(latest.session_id)
    assert recap_session_id is not None
    graph_sessions = _graph_session_ids(graph_store, campaign_id)
    graph_latest_session_id = graph_sessions[-1] if graph_sessions else None
    if graph_latest_session_id is None:
        outcome: LatestRecapOutcome = "unknown"
        diagnostic_codes = ["graph_comparison_boundary_unavailable"]
    elif (_session_number(graph_latest_session_id) or -1) < (
        _session_number(recap_session_id) or -1
    ):
        outcome = "memory_lag"
        diagnostic_codes = ["latest_recap_not_in_graph_head"]
    elif graph_latest_session_id == recap_session_id:
        outcome = "no_change"
        diagnostic_codes = ["comparison_completed_no_later_graph_session"]
    else:
        outcome = "changed"
        diagnostic_codes = ["graph_contains_post_recap_session"]

    return LatestRecapChangeContext(
        status="ready",
        campaign_id=campaign_id,
        latest_recap=LatestRecapReference(
            artifact_id=latest.artifact_id,
            campaign_id=latest.campaign_id,
            session_id=recap_session_id,
            source_artifact_id=latest.source_artifact_id,
            source_recap_path=latest.source_recap_path,
            source_sha256=latest.source_sha256,
        ),
        comparison_boundary=LatestRecapComparisonBoundary(
            recap_session_id=recap_session_id,
            graph_revision_id=graph_revision_id,
            graph_latest_session_id=graph_latest_session_id,
        ),
        outcome=outcome,
        memory_lag=outcome == "memory_lag",
        graph_session_ids=graph_sessions,
        graph_object_ids=_object_ids_for_session(graph_store, recap_session_id),
        diagnostic_codes=diagnostic_codes,
    )


def resolve_latest_recap_change_context(
    *,
    root: Path | None = None,
    graph_root: Path | None = None,
    world_id: str,
    campaign_id: str,
    graph_revision_id: str | None,
) -> LatestRecapChangeContext:
    """Resolve the latest registry record against the immutable graph head."""
    repo = (root or repo_root()).resolve()
    graph_base = (graph_root or world_graph_root()).resolve()
    records = list_recap_artifact_records(repo, campaign_id=campaign_id)
    try:
        _, _, store = load_current_world_graph(graph_base, world_id)
    except Exception:
        return _unknown_context(
            campaign_id=campaign_id,
            outcome="unknown",
            diagnostic_code="graph_head_unavailable",
        )
    return build_latest_recap_change_context(
        root=repo,
        campaign_id=campaign_id,
        graph_revision_id=graph_revision_id,
        graph_store=_as_mapping(store),
        records=records,
    )


def is_latest_recap_change_question(question: str) -> bool:
    """Detect the canonical S1 question without replacing free-form routing."""
    lowered = " ".join(question.lower().split())
    return (
        ("latest" in lowered and "recap" in lowered and "chang" in lowered)
        or "what changed after the latest ingested recap" in lowered
    )


__all__ = [
    "LATEST_RECAP_CHANGE_SCHEMA",
    "LatestRecapChangeContext",
    "build_latest_recap_change_context",
    "is_latest_recap_change_question",
    "read_admitted_recap_excerpt",
    "resolve_latest_recap_change_context",
]
