"""Browse catalog: campaign/session rows derived from active World Graph contributions."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from apps.live_control_server.config import world_graph_root
from apps.live_control_server.services.union_supergraph_projection_adapter import (
    CorpusNormalizedRecapLoadError,
    load_corpus_normalized_recap_markdown,
)
from graph_memory.kernel.contribution_models import GraphContribution

DEFAULT_WORLD_ID = "eldyrwild"

_RECAP_ARTIFACT_SESSION = re.compile(
    r"^artifact:recap:(?P<campaign>[^:]+):(?P<session>session-\d+)\b"
)
_SESSION_ID = re.compile(r"^session-\d+$")


class WorldGraphSessionSummary(BaseModel):
    world_id: str
    campaign_id: str
    session_id: str
    session_number: int | None = None
    contribution_count: int = 0
    contribution_ids: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)
    head_revision_id: str | None = None
    recap_available: bool = False
    browseable: bool = True


class WorldGraphSessionsResponse(BaseModel):
    schema_version: Literal["dmb_world_graph_sessions_v1"] = "dmb_world_graph_sessions_v1"
    version: str = "0.1"
    world_id: str
    head_revision_id: str | None = None
    sessions: list[WorldGraphSessionSummary] = Field(default_factory=list)


def _parse_session_number(session_id: str) -> int | None:
    match = re.fullmatch(r"session-(\d+)", session_id.strip())
    if not match:
        return None
    value = int(match.group(1))
    return value if value > 0 else None


def _session_from_artifact_id(
    source_artifact_id: str | None,
) -> tuple[str | None, str | None]:
    if not source_artifact_id or not source_artifact_id.strip():
        return None, None
    match = _RECAP_ARTIFACT_SESSION.match(source_artifact_id.strip())
    if not match:
        return None, None
    return match.group("campaign"), match.group("session")


def _session_from_temporal_scope(temporal_scope: object) -> str | None:
    if not isinstance(temporal_scope, dict):
        return None
    raw = temporal_scope.get("session_id")
    if not isinstance(raw, str):
        return None
    session_id = raw.strip()
    if not _SESSION_ID.fullmatch(session_id):
        return None
    return session_id


def contribution_campaign_session(
    contribution: GraphContribution,
) -> tuple[str, str] | None:
    """Resolve (campaign_id, session_id) for a contribution when browseable."""
    campaign_id = (contribution.campaign_scope or "").strip() or None
    session_id: str | None = None

    art_campaign, art_session = _session_from_artifact_id(contribution.source_artifact_id)
    if art_campaign and art_session:
        campaign_id = campaign_id or art_campaign
        session_id = art_session

    if session_id is None:
        for assertion in contribution.accepted_assertions:
            scoped = _session_from_temporal_scope(assertion.temporal_scope)
            if scoped:
                session_id = scoped
                if not campaign_id:
                    assertion_campaign = (assertion.campaign_scope or "").strip() or None
                    campaign_id = assertion_campaign
                break

    if not campaign_id or not session_id:
        return None
    return campaign_id, session_id


def _probe_recap_available(*, campaign_id: str, session_id: str) -> bool:
    try:
        markdown = load_corpus_normalized_recap_markdown(
            campaign_id=campaign_id,
            session_id=session_id,
            on_ambiguous="fail",
        )
    except CorpusNormalizedRecapLoadError:
        return False
    return bool((markdown or "").strip())


def list_world_graph_sessions(
    *,
    world_id: str = DEFAULT_WORLD_ID,
    campaign_id: str | None = None,
    root: Path | None = None,
) -> WorldGraphSessionsResponse:
    """List campaign/session pairs present in active World Graph contributions."""
    from graph_memory.world_supergraph.contribution_store import (
        load_contribution_index,
        load_contribution_record,
    )
    import graph_memory.kernel as kernel

    world_root = (root if root is not None else world_graph_root()).resolve()
    resolved_world_id = (world_id or DEFAULT_WORLD_ID).strip() or DEFAULT_WORLD_ID
    campaign_filter = (campaign_id or "").strip() or None

    head_revision_id: str | None = None
    try:
        head, _revision, _store = kernel.open_current_world_graph(
            world_root, resolved_world_id
        )
        head_revision_id = getattr(head, "head_revision_id", None)
    except Exception:
        head_revision_id = None

    index = load_contribution_index(world_root, resolved_world_id)
    aggregated: dict[tuple[str, str], WorldGraphSessionSummary] = {}

    for contribution_id in index.active_contribution_ids:
        try:
            contribution = load_contribution_record(
                world_root, resolved_world_id, contribution_id
            )
        except FileNotFoundError:
            continue
        if contribution.status != "active":
            continue
        resolved = contribution_campaign_session(contribution)
        if resolved is None:
            continue
        row_campaign, row_session = resolved
        if campaign_filter and row_campaign != campaign_filter:
            continue
        key = (row_campaign, row_session)
        existing = aggregated.get(key)
        artifact = (contribution.source_artifact_id or "").strip()
        if existing is None:
            aggregated[key] = WorldGraphSessionSummary(
                world_id=resolved_world_id,
                campaign_id=row_campaign,
                session_id=row_session,
                session_number=_parse_session_number(row_session),
                contribution_count=1,
                contribution_ids=[contribution.contribution_id],
                source_artifact_ids=[artifact] if artifact else [],
                head_revision_id=head_revision_id,
                recap_available=False,
                browseable=True,
            )
            continue
        existing.contribution_count += 1
        existing.contribution_ids.append(contribution.contribution_id)
        if artifact and artifact not in existing.source_artifact_ids:
            existing.source_artifact_ids.append(artifact)

    sessions = sorted(
        aggregated.values(),
        key=lambda row: (
            row.campaign_id,
            row.session_number if row.session_number is not None else 10**9,
            row.session_id,
        ),
    )
    for row in sessions:
        row.recap_available = _probe_recap_available(
            campaign_id=row.campaign_id,
            session_id=row.session_id,
        )

    return WorldGraphSessionsResponse(
        world_id=resolved_world_id,
        head_revision_id=head_revision_id,
        sessions=sessions,
    )
