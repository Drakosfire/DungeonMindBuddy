"""Unit tests for Hermes canvas block proposal (propose-only, no durable write)."""

from __future__ import annotations

from apps.live_control_server.services.canvas_block_proposal import (
    CANVAS_BLOCK_PROPOSAL_SCHEMA,
    PROPOSE_CANVAS_BLOCK_TOOL_NAME,
    execute_propose_canvas_block,
)
from apps.live_control_server.services.hermes_graph_interaction_tools import (
    ORDERED_MODEL_VISIBLE_TOOL_NAMES,
    hermes_model_visible_tool_definitions,
)
from graph_memory.hermes_graph_plugin import (
    HermesCanvasWorkObject,
    HermesGraphScope,
    apply_capability_policy_to_arguments,
    default_graph_only_capability_policy,
    reset_active_capability_policy,
    reset_active_canvas_work_object,
    set_active_capability_policy,
    set_active_canvas_work_object,
)


def test_propose_canvas_block_is_model_visible_in_order() -> None:
    names = [item["function"]["name"] for item in hermes_model_visible_tool_definitions()]
    assert PROPOSE_CANVAS_BLOCK_TOOL_NAME in names
    assert names == list(ORDERED_MODEL_VISIBLE_TOOL_NAMES)


def test_execute_propose_canvas_block_builds_preview() -> None:
    result = execute_propose_canvas_block(
        {
            "documentId": "doc-1",
            "surfaceId": "plan",
            "expectedContentSha256": "abc123",
            "op": "insert_callout",
            "kind": "gm-note",
            "body": "Precious metal leaves on odd branches.",
            "locator": {"afterHeading": "Area 5: The Grotesque Tree"},
            "provenanceRefs": ["location:grotesque-tree-site"],
        }
    )
    assert result["schema"] == CANVAS_BLOCK_PROPOSAL_SCHEMA
    assert result["kind"] == "gm-note"
    assert "precious metal leaves" in result["body"].lower()
    assert result["previewMarkdown"].startswith("> [!GM-NOTE]")
    assert result["documentId"] == "doc-1"
    assert result["expectedContentSha256"] == "abc123"


def test_execute_propose_requires_document() -> None:
    result = execute_propose_canvas_block(
        {
            "op": "insert_callout",
            "kind": "gm-note",
            "body": "Leaves.",
            "locator": {"afterHeading": "Area 5"},
        }
    )
    assert result["schema"] == "dmb_canvas_block_proposal_error_v1"
    assert result["code"] == "canvas_work_object_missing"


def test_capability_policy_injects_canvas_and_allows_write() -> None:
    scope = HermesGraphScope(
        world_id="world_eldyrwild",
        campaign_id="of-conks-cons",
        focus={"kind": "none"},
        admissibility="gm",
        revision_pin="rev_1",
    )
    policy = default_graph_only_capability_policy(scope)
    rule = policy.rule_for(PROPOSE_CANVAS_BLOCK_TOOL_NAME)
    assert rule is not None
    assert rule.allowed_effects == frozenset({"write"})

    policy_token = set_active_capability_policy(policy)
    canvas_token = set_active_canvas_work_object(
        HermesCanvasWorkObject(
            document_id="doc-plan-1",
            surface_id="plan",
            expected_content_sha256="deadbeef",
        )
    )
    try:
        denied_read = apply_capability_policy_to_arguments(
            PROPOSE_CANVAS_BLOCK_TOOL_NAME,
            {"op": "insert_callout", "kind": "gm-note", "body": "x", "locator": {"afterHeading": "H"}},
            effect="read",
        )
        assert denied_read[0] is None
        assert denied_read[1] is not None

        payload, denied = apply_capability_policy_to_arguments(
            PROPOSE_CANVAS_BLOCK_TOOL_NAME,
            {
                "documentId": "forged",
                "op": "insert_callout",
                "kind": "gm-note",
                "body": "Metal leaves.",
                "locator": {"afterHeading": "Area 5"},
            },
            effect="write",
        )
        assert denied is None
        assert payload is not None
        assert payload["documentId"] == "doc-plan-1"
        assert payload["surfaceId"] == "plan"
        assert payload["expectedContentSha256"] == "deadbeef"
    finally:
        reset_active_canvas_work_object(canvas_token)
        reset_active_capability_policy(policy_token)
