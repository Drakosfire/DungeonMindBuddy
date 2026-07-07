"""Append-only graph authoring event log writer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphAssertion,
    GraphAuthoringOverlayModel,
    GraphAuthoringProvenance,
    GraphVisibilityPolicy,
    isoformat_z,
)

GRAPH_AUTHORING_EVENT_SCHEMA = "dmb.graph_authoring_event.v1"

GraphAuthoringEventKind = Literal[
    "authored_graph_assertions_committed",
    "authored_graph_object_committed",
    "authored_graph_link_existing_committed",
    "authored_graph_relationship_committed",
    "authored_graph_merge_objects_committed",
]


class GraphAuthoringEvent(GraphAuthoringOverlayModel):
    schema_version: Literal["dmb.graph_authoring_event.v1"] = GRAPH_AUTHORING_EVENT_SCHEMA
    event_id: str
    event_kind: GraphAuthoringEventKind

    campaign_id: str
    session_id: str | None = None

    assertion_id: str | None = None
    assertion_kind: str | None = None
    operation: str | None = None

    overlay_path: str
    overlay_token_before: str
    overlay_token_after: str

    source_run_id: str | None = None
    source_graph_id: str | None = None
    source_projection_id: str | None = None

    provenance: GraphAuthoringProvenance
    visibility: GraphVisibilityPolicy | None = None

    local_proposal_id: str | None = None
    selected_text: str | None = None
    summary: str | None = None


class GraphAuthoringEventLogError(OSError):
    """Raised when the event log append fails."""


def _event_kind_for_assertion(assertion: AuthoredGraphAssertion) -> GraphAuthoringEventKind:
    if assertion.assertion_kind == "object":
        return "authored_graph_object_committed"
    if assertion.assertion_kind == "link_existing":
        return "authored_graph_link_existing_committed"
    if assertion.assertion_kind == "merge_objects":
        return "authored_graph_merge_objects_committed"
    return "authored_graph_relationship_committed"


def _assertion_summary(assertion: AuthoredGraphAssertion) -> str:
    if assertion.assertion_kind == "object":
        return f"Object: {assertion.object_ref.label}"
    if assertion.assertion_kind == "link_existing":
        return (
            f"Link existing: {assertion.selected_text} → "
            f"{assertion.existing_object_ref.label}"
        )
    if assertion.assertion_kind == "merge_objects":
        merged_labels = ", ".join(ref.label for ref in assertion.merged_object_refs)
        return f"Merge: {assertion.survivor_object_ref.label} ← {merged_labels}"
    return (
        f"Relationship: {assertion.source_object_ref.label} "
        f"{assertion.relationship_type} {assertion.target_object_ref.label}"
    )


def build_graph_authoring_events(
    *,
    campaign_id: str,
    session_id: str | None,
    overlay_path: str,
    overlay_token_before: str,
    overlay_token_after: str,
    assertions: list[AuthoredGraphAssertion],
    local_proposal_ids: list[str],
    source_run_id: str | None = None,
    source_graph_id: str | None = None,
    source_projection_id: str | None = None,
    batch_event_id: str,
) -> list[GraphAuthoringEvent]:
    if not assertions:
        return []

    batch_provenance = assertions[0].provenance.model_copy(
        update={"updated_at": isoformat_z()},
    )
    events: list[GraphAuthoringEvent] = [
        GraphAuthoringEvent(
            event_id=batch_event_id,
            event_kind="authored_graph_assertions_committed",
            campaign_id=campaign_id,
            session_id=session_id,
            overlay_path=overlay_path,
            overlay_token_before=overlay_token_before,
            overlay_token_after=overlay_token_after,
            source_run_id=source_run_id,
            source_graph_id=source_graph_id,
            source_projection_id=source_projection_id,
            provenance=batch_provenance,
            summary=f"Committed {len(assertions)} authored graph assertion(s).",
        )
    ]

    for assertion, local_proposal_id in zip(assertions, local_proposal_ids, strict=False):
        selected_text = None
        if assertion.assertion_kind == "link_existing":
            selected_text = assertion.selected_text
        elif assertion.source_anchor is not None:
            selected_text = assertion.source_anchor.selected_text

        events.append(
            GraphAuthoringEvent(
                event_id=f"{batch_event_id}:{assertion.assertion_id}",
                event_kind=_event_kind_for_assertion(assertion),
                campaign_id=campaign_id,
                session_id=session_id,
                assertion_id=assertion.assertion_id,
                assertion_kind=assertion.assertion_kind,
                operation=assertion.operation,
                overlay_path=overlay_path,
                overlay_token_before=overlay_token_before,
                overlay_token_after=overlay_token_after,
                source_run_id=source_run_id,
                source_graph_id=source_graph_id,
                source_projection_id=source_projection_id,
                provenance=assertion.provenance.model_copy(update={"updated_at": isoformat_z()}),
                visibility=assertion.visibility,
                local_proposal_id=local_proposal_id,
                selected_text=selected_text,
                summary=_assertion_summary(assertion),
            )
        )

    return events


def append_graph_authoring_events(events_path: Path, events: list[GraphAuthoringEvent]) -> None:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(event.model_dump(mode="json"), ensure_ascii=False) for event in events]
    try:
        with events_path.open("a", encoding="utf-8") as handle:
            for line in lines:
                handle.write(line + "\n")
    except OSError as exc:
        raise GraphAuthoringEventLogError(f"failed to append graph authoring events: {exc}") from exc
