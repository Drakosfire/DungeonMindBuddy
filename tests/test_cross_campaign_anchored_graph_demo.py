"""Deterministic contract tests for cross-campaign world-scope graph demo."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.services.agent_world_graph_query_context import (
    AgentWorldGraphQueryContextRequest,
    build_projection_request,
)
from apps.live_control_server.services.hermes_graph_agent_contract import (
    HermesGraphAgentTurnRequest,
    deserialize_hermes_graph_agent_turn_request,
    serialize_hermes_graph_agent_turn_request,
)
from apps.live_control_server.services.hermes_graph_query import (
    HermesGraphQueryRequestError,
    _api_focus_to_host_focus,
    validate_hermes_query_inputs,
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
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
)

# Reuse the C2 init fixture constants from kernel world-projection tests.
from tests.test_graph_kernel_world_projection import (
    BUNDLE_PATH,
    CAMPAIGN_ID,
    FOCUS_SESSION_ID,
    TRIPOD_ID,
    WORLD_ID,
    _initialize,
    _request,
    loaded_bundle,
)

C1_CAMPAIGN_ID = "longmont-c1"


def test_campaign_scope_isolates_foreign_campaign_objects(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(campaign_id=C1_CAMPAIGN_ID, scope_mode="campaign"),
    )
    node_ids = {node.node_id for node in projection.nodes}
    assert TRIPOD_ID not in node_ids
    assert "party:questionable-company" not in node_ids
    assert "location:mirathorn" in node_ids


def test_world_scope_surfaces_c2_objects_from_c1_anchor(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(campaign_id=C1_CAMPAIGN_ID, scope_mode="world"),
    )
    assert projection.snapshot.scope_mode == "world"
    assert projection.snapshot.campaign_id == C1_CAMPAIGN_ID
    node_ids = {node.node_id for node in projection.nodes}
    assert TRIPOD_ID in node_ids
    tripod = next(node for node in projection.nodes if node.node_id == TRIPOD_ID)
    assert tripod.campaign_scope == CAMPAIGN_ID


def test_qualified_session_focus_does_not_anchor_foreign_campaign_evidence(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    c1_focus = kernel.project_world_graph(
        tmp_path,
        _request(
            campaign_id=C1_CAMPAIGN_ID,
            scope_mode="world",
            focus_kind="session",
            session_id=FOCUS_SESSION_ID,
            focus_campaign_id=C1_CAMPAIGN_ID,
        ),
    )
    assert c1_focus.snapshot.focus.campaign_id == C1_CAMPAIGN_ID
    tripod_c1 = next(node for node in c1_focus.nodes if node.node_id == TRIPOD_ID)
    assert tripod_c1.anchored_to_focus_session is False

    c2_focus = kernel.project_world_graph(
        tmp_path,
        _request(
            campaign_id=CAMPAIGN_ID,
            scope_mode="world",
            focus_kind="session",
            session_id=FOCUS_SESSION_ID,
            focus_campaign_id=CAMPAIGN_ID,
        ),
    )
    assert c2_focus.snapshot.focus.campaign_id == CAMPAIGN_ID
    assert c2_focus.snapshot.scope_mode == "world"


def test_agent_request_builder_world_vs_campaign_scope() -> None:
    world_nested = AgentWorldGraphQueryContextRequest.model_validate(
        {
            "schema": "dmb_agent_world_graph_query_context_request_v1",
            "world_id": WORLD_ID,
            "campaign_id": C1_CAMPAIGN_ID,
            "scope_mode": "world",
            "focus": {
                "kind": "session",
                "session_id": "session-3",
                "campaign_id": C1_CAMPAIGN_ID,
            },
            "admissibility": "gm",
        }
    )
    world_request = build_projection_request(world_nested, query_text="Mirathorn?")
    assert world_request.schema_ == PROJECTION_REQUEST_SCHEMA
    assert world_request.scope_mode == "world"
    assert world_request.campaign_id == C1_CAMPAIGN_ID
    assert world_request.focus == WorldGraphProjectionFocus(
        kind="session",
        session_id="session-3",
        campaign_id=C1_CAMPAIGN_ID,
    )

    campaign_nested = AgentWorldGraphQueryContextRequest.model_validate(
        {
            **world_nested.model_dump(by_alias=True),
            "scope_mode": "campaign",
        }
    )
    campaign_request = build_projection_request(campaign_nested, query_text="Mirathorn?")
    assert campaign_request.scope_mode == "campaign"


@pytest.mark.parametrize(
    "api_focus",
    [
        None,
        {"kind": "session", "session_id": "session-3", "campaign_id": C1_CAMPAIGN_ID},
    ],
)
def test_hermes_turn_request_focus_campaign_id_round_trip(
    api_focus: dict[str, str] | None,
) -> None:
    focus = _api_focus_to_host_focus(api_focus)
    request = HermesGraphAgentTurnRequest(
        question="q",
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus=focus,
        admissibility="gm",
        revision_pin="rev:1",
    )
    wire = serialize_hermes_graph_agent_turn_request(request)
    restored = deserialize_hermes_graph_agent_turn_request(wire)
    assert restored.focus == focus
    assert "campaignId" in (restored.focus or {})


def test_validate_hermes_query_inputs_campaign_vs_world() -> None:
    with pytest.raises(HermesGraphQueryRequestError) as campaign_mismatch:
        validate_hermes_query_inputs(
            world_graph_context=SimpleNamespace(
                campaign_id=C1_CAMPAIGN_ID,
                scope_mode="campaign",
            ),
            request_manifest_path=None,
            hermes_session_id=None,
            outer_campaign_id=CAMPAIGN_ID,
        )
    assert campaign_mismatch.value.code == "campaign_scope_mismatch"

    validate_hermes_query_inputs(
        world_graph_context=SimpleNamespace(
            campaign_id=C1_CAMPAIGN_ID,
            scope_mode="world",
        ),
        request_manifest_path=None,
        hermes_session_id=None,
        outer_campaign_id=CAMPAIGN_ID,
    )


# Plan UI request builders live in TypeScript (`planGraphContextRequest.ts`).
# UI proof is covered by vitest:
#   apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.test.ts
#   apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx
