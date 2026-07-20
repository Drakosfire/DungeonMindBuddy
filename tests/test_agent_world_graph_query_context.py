"""Unit tests for PR008B Agent World Graph query-context adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.services.agent_world_graph_query_context import (
    AGENT_RESPONSE_SCHEMA,
    AgentWorldGraphQueryContextError,
    AgentWorldGraphQueryContextRequest,
    adapt_projection_to_agent_envelope,
    build_projection_request,
    render_world_graph_prompt_block,
    resolve_agent_world_graph_query_context,
)
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
    project_world_graph,
)
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
)

BUNDLE_PATH = Path(
    "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-21"
TRIPOD_ID = "threat:tripod-null-calf"
EVENT_ID = "event:longmont-c2:session-23:mireward-gate-battle"
BUNDLE_DIGEST = (
    "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
)
APPROVED_MERGE_SHA = "65ae001e0852d827ecd680200a965a576c705b1d"
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


def _initialize(root: Path) -> None:
    bundle = load_contribution_bundle(BUNDLE_PATH)
    by_id = {item.contribution_id: item for item in bundle.contributions}
    plan = WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus_session_id="session-23",
        ordered_contributions=[
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(
                    by_id[contribution_id]
                ),
            )
            for contribution_id in ORDERED_CONTRIBUTION_IDS
        ],
        approval_attestation=WorldInitializationApprovalAttestation(
            bundle_id="eldyrwild-longmont-c2-initial-v1",
            bundle_digest=BUNDLE_DIGEST,
            approved_bundle_merge_sha=APPROVED_MERGE_SHA,
        ),
    )
    initialize_world_from_contributions(
        root,
        plan=plan,
        contributions=list(bundle.contributions),
        actor="gm",
    )


def _nested(
    *,
    revision_pin: str | None = None,
    campaign_id: str = CAMPAIGN_ID,
) -> AgentWorldGraphQueryContextRequest:
    return AgentWorldGraphQueryContextRequest.model_validate(
        {
            "schema": "dmb_agent_world_graph_query_context_request_v1",
            "world_id": WORLD_ID,
            "campaign_id": campaign_id,
            "focus": {"kind": "session", "session_id": FOCUS_SESSION_ID},
            "admissibility": "gm",
            "revision_pin": revision_pin,
        }
    )


def test_outer_question_becomes_projection_query_text() -> None:
    nested = _nested()
    request = build_projection_request(
        nested,
        query_text="What should I remember about the Tripod Null-Calf?",
    )
    assert request.query_text == "What should I remember about the Tripod Null-Calf?"
    assert request.schema_ == PROJECTION_REQUEST_SCHEMA
    assert request.world_id == WORLD_ID
    assert request.focus.session_id == FOCUS_SESSION_ID


def test_ready_match_returns_tripod_and_connected_battle(tmp_path: Path) -> None:
    _initialize(tmp_path)
    envelope = resolve_agent_world_graph_query_context(
        _nested(),
        outer_text="What should I remember about the Tripod Null-Calf and the North Gate pressure?",
        outer_campaign_id=CAMPAIGN_ID,
        root=tmp_path,
    )
    assert envelope["schema"] == AGENT_RESPONSE_SCHEMA
    assert envelope["status"] == "ready"
    assert TRIPOD_ID in envelope["matched_node_ids"]
    assert envelope["revision_id"]
    assert envelope["is_head"] is True
    assert envelope["focus"]["session_id"] == FOCUS_SESSION_ID
    assert envelope["trust_boundary"]["graph_citations_permitted"] is False
    edge_targets = {
        edge["target_node_id"] for edge in envelope["relationships"]
    } | {edge["source_node_id"] for edge in envelope["relationships"]}
    assert EVENT_ID in edge_targets or any(
        EVENT_ID in (edge["edge_id"] or "") for edge in envelope["relationships"]
    )
    # Evidence / source artifacts must not leak into the Agent envelope.
    assert "evidence" not in envelope
    assert "source_artifacts" not in envelope
    for node in envelope["nodes"]:
        assert set(node) <= {
            "node_id",
            "label",
            "kind",
            "role",
            "summary",
            "anchored_to_focus_session",
            "campaign_scope",
        }
    for attribute in envelope["attributes"]:
        assert "active_contribution_ids" not in attribute
        assert set(attribute) <= {
            "assertion_id",
            "subject_node_id",
            "predicate",
            "label",
            "text_value",
            "campaign_scope",
        }


def test_ordinary_miss_is_empty_not_unavailable(tmp_path: Path) -> None:
    _initialize(tmp_path)
    envelope = resolve_agent_world_graph_query_context(
        _nested(),
        outer_text="What should I remember about zz-pr008b-absent-7f4c9d?",
        outer_campaign_id=CAMPAIGN_ID,
        root=tmp_path,
    )
    assert envelope["status"] == "empty"
    assert envelope["matched_node_ids"] == []
    assert envelope["revision_id"]
    assert "world_graph_unavailable" not in envelope["warning_codes"]
    assert "graph_context_empty" in envelope["warning_codes"]


def test_world_graph_unavailable_is_nonfatal(tmp_path: Path) -> None:
    envelope = resolve_agent_world_graph_query_context(
        _nested(),
        outer_text="Tripod?",
        outer_campaign_id=CAMPAIGN_ID,
        root=tmp_path,
    )
    assert envelope["status"] == "unavailable"
    assert envelope["revision_id"] is None
    assert "world_graph_unavailable" in envelope["warning_codes"]


def test_outer_packet_campaign_may_differ_from_graph_lens(tmp_path: Path) -> None:
    """Plan packet campaign (outer) is independent of nested graph-lens campaign."""
    _initialize(tmp_path)
    envelope = resolve_agent_world_graph_query_context(
        _nested(campaign_id=CAMPAIGN_ID),
        outer_text="Tripod?",
        outer_campaign_id="longmont-c1",
        root=tmp_path,
    )
    assert envelope["status"] in {"ready", "empty"}
    assert envelope["campaign_id"] == CAMPAIGN_ID


def test_historical_pin_reports_is_head_false(tmp_path: Path) -> None:
    _initialize(tmp_path)
    head, first_revision, _store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    first_revision_id = head.head_revision_id

    # Publish a second head by retracting nothing material — use a no-op re-open
    # and pin to the recorded first revision after a second projection confirms head.
    first_projection = project_world_graph(
        WorldGraphProjectionRequest(
            schema=PROJECTION_REQUEST_SCHEMA,
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            revision_pin=first_revision_id,
            query_text="Tripod Null-Calf",
        ),
        root=tmp_path,
    )
    assert first_projection.snapshot.revision_id == first_revision_id

    envelope = resolve_agent_world_graph_query_context(
        _nested(revision_pin=first_revision_id),
        outer_text="Tripod Null-Calf",
        outer_campaign_id=CAMPAIGN_ID,
        root=tmp_path,
    )
    assert envelope["revision_id"] == first_revision_id
    assert envelope["head_revision_id"] == first_revision_id
    assert envelope["is_head"] is True  # only one revision exists yet

    # Force a second revision by publishing an empty contribution merge is out of
    # scope; instead simulate via project_fn returning a non-head snapshot.
    def _fake_project(request: WorldGraphProjectionRequest, *, root: Path | None = None) -> Any:
        projection = project_world_graph(request, root=root)
        # Clone with is_head forced false while retaining exact pin.
        data = projection.model_dump(mode="python")
        data["snapshot"]["is_head"] = False
        data["snapshot"]["head_revision_id"] = "rev:fake-newer-head"
        from graph_memory.projection.world_projection import WorldGraphProjection

        return WorldGraphProjection.model_validate(data)

    envelope2 = resolve_agent_world_graph_query_context(
        _nested(revision_pin=first_revision_id),
        outer_text="Tripod Null-Calf",
        outer_campaign_id=CAMPAIGN_ID,
        root=tmp_path,
        project_fn=_fake_project,
    )
    assert envelope2["revision_id"] == first_revision_id
    assert envelope2["is_head"] is False
    assert envelope2["head_revision_id"] == "rev:fake-newer-head"


def test_prompt_renderer_is_deterministic_and_non_citation(tmp_path: Path) -> None:
    _initialize(tmp_path)
    envelope = resolve_agent_world_graph_query_context(
        _nested(),
        outer_text="Tripod Null-Calf",
        outer_campaign_id=CAMPAIGN_ID,
        root=tmp_path,
    )
    block_a = render_world_graph_prompt_block(envelope)
    block_b = render_world_graph_prompt_block(envelope)
    assert block_a == block_b
    assert "not source quotations" in block_a
    assert "must not be cited with corpus evidence IDs" in block_a
    assert TRIPOD_ID in block_a


def test_fatal_projection_errors_propagate() -> None:
    def _boom(
        request: WorldGraphProjectionRequest,
        *,
        root: Path | None = None,
    ) -> Any:
        raise WorldGraphProjectionServiceError(
            "pin missing",
            code="revision_not_found",
            status_code=404,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="revision_not_found",
                    message="pin missing",
                    severity="error",
                )
            ],
        )

    with pytest.raises(AgentWorldGraphQueryContextError) as exc_info:
        resolve_agent_world_graph_query_context(
            _nested(revision_pin="rev:does-not-exist"),
            outer_text="Tripod?",
            outer_campaign_id=CAMPAIGN_ID,
            project_fn=_boom,
        )
    assert exc_info.value.code == "revision_not_found"
    assert exc_info.value.status_code == 404


def test_campaign_scope_rejects_mismatched_focus_campaign() -> None:
    nested = AgentWorldGraphQueryContextRequest.model_validate(
        {
            "schema": "dmb_agent_world_graph_query_context_request_v1",
            "world_id": WORLD_ID,
            "campaign_id": CAMPAIGN_ID,
            "scope_mode": "campaign",
            "focus": {
                "kind": "session",
                "session_id": FOCUS_SESSION_ID,
                "campaign_id": "longmont-c1",
            },
            "admissibility": "gm",
            "revision_pin": None,
        }
    )
    with pytest.raises(AgentWorldGraphQueryContextError) as exc_info:
        build_projection_request(nested, query_text="Tripod?")
    assert exc_info.value.code == "invalid_request"
    assert "focus.campaign_id" in str(exc_info.value)


def test_campaign_scope_qualifies_focus_with_lens_campaign() -> None:
    nested = AgentWorldGraphQueryContextRequest.model_validate(
        {
            "schema": "dmb_agent_world_graph_query_context_request_v1",
            "world_id": WORLD_ID,
            "campaign_id": CAMPAIGN_ID,
            "scope_mode": "campaign",
            "focus": {"kind": "session", "session_id": FOCUS_SESSION_ID},
            "admissibility": "gm",
            "revision_pin": None,
        }
    )
    request = build_projection_request(nested, query_text="Tripod?")
    assert request.focus.campaign_id == CAMPAIGN_ID


def test_adapt_empty_query_context_is_empty_status(tmp_path: Path) -> None:
    _initialize(tmp_path)
    projection = project_world_graph(
        WorldGraphProjectionRequest(
            schema=PROJECTION_REQUEST_SCHEMA,
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            focus=WorldGraphProjectionFocus(kind="session", session_id=FOCUS_SESSION_ID),
            query_text="zz-pr008b-absent-7f4c9d",
        ),
        root=tmp_path,
    )
    envelope = adapt_projection_to_agent_envelope(
        projection,
        query_text="zz-pr008b-absent-7f4c9d",
    )
    assert envelope["status"] == "empty"
    assert envelope["matched_node_ids"] == []
