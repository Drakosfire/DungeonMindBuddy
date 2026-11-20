"""Hydrate selected observations using the existing native retrieval boundary."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from graph_memory.interaction.expansion_executor import execute_expand_graph_retrieval
from graph_memory.interaction.session import GraphRetrievalSession
from graph_memory.interaction.session_store import replace_session


def hydrate_selected_observations(
    session: GraphRetrievalSession, envelope: Mapping[str, Any], *, root: Path
) -> None:
    rows = envelope.get("reviewed_source_observations") or []
    ids = envelope.get("matched_node_ids") or []
    if (
        envelope.get("excerpt_policy") != "provenance_context_not_citation"
        or envelope.get("admissibility") != "gm"
        or len(ids) != 1
        or not rows
    ):
        return
    node_id = ids[0]
    if any(
        not isinstance(row, Mapping) or row.get("subject_node_id") != node_id
        for row in rows
    ):
        return
    before = session.model_copy(deep=True)
    result = execute_expand_graph_retrieval(
        {
            "retrievalSessionId": session.id,
            "operation": "object",
            "targets": [{"kind": "node", "id": node_id}],
        },
        root=root,
    )
    for event in session.operations[len(before.operations) :]:
        event.requested_by = "server_initial"
    snapshot = result.get("snapshot") or {}
    coverage = result.get("reviewedSourceObservationCoverage") or {}
    valid = (
        result.get("outcome") == "enough"
        and snapshot.get("worldId") == session.snapshot.world_id
        and snapshot.get("revisionId") == session.snapshot.revision_id
        and snapshot.get("campaignId") == session.snapshot.campaign_id
        and snapshot.get("scopeMode") == session.snapshot.scope_mode
        and snapshot.get("admissibility") == session.snapshot.admissibility
        and not coverage.get("gapCodes")
        and not coverage.get("missingIds")
    )
    expected = {row.get("assertion_id") for row in rows}
    admitted = {
        claim.claim_id
        for claim in session.claims
        if claim.claim_kind == "source_observation"
    }
    if not valid or not expected.issubset(admitted):
        # Retain failure telemetry, but none of the incomplete read's new claims/support.
        session.claims = before.claims
        session.source_anchors = before.source_anchors
        code = "selected_observation_initial_support_unavailable"
        for event in session.operations[len(before.operations) :]:
            event.status = "failed"
            event.added_claim_ids = []
            event.added_anchor_ids = []
            event.diagnostic_codes.append(code)
        session.diagnostics.append(code)
        session.coverage.gap_codes.append(code)
        session.coverage.state = "partial_coverage"
    replace_session(session)
