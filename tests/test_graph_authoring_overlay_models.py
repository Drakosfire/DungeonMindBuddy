"""Tests for authored graph overlay Pydantic contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphLinkExistingAssertion,
    AuthoredGraphObjectAssertion,
    AuthoredGraphObjectRef,
    AuthoredGraphOverlay,
    AuthoredGraphRelationshipAssertion,
    GraphAuthoringSourceAnchor,
    GraphVisibilityPolicy,
    build_source_anchor_from_payload,
    create_empty_authored_graph_overlay,
    default_graph_authoring_provenance,
    hash_text,
    normalize_selected_text,
)

STAMP = "2026-07-06T12:00:00Z"
CAMPAIGN_ID = "longmont-c1"


def provenance(**overrides):
    kwargs = {"created_at": STAMP}
    kwargs.update(overrides)
    return default_graph_authoring_provenance(**kwargs)


def object_ref(**overrides):
    data = {
        "ref_kind": "existing_graph_node",
        "node_id": "pc_bonogo",
        "label": "Bonogo",
        "kind": "pc",
    }
    data.update(overrides)
    return AuthoredGraphObjectRef.model_validate(data)


def object_assertion(**overrides) -> AuthoredGraphObjectAssertion:
    data = {
        "assertion_id": "assert-object-1",
        "assertion_kind": "object",
        "operation": "create",
        "campaign_id": CAMPAIGN_ID,
        "session_id": "session-1",
        "provenance": provenance().model_dump(),
        "object_ref": object_ref().model_dump(),
        "aliases": ["gang"],
        "summary": "Questionable company of mercenaries",
    }
    data.update(overrides)
    return AuthoredGraphObjectAssertion.model_validate(data)


def link_existing_assertion(**overrides) -> AuthoredGraphLinkExistingAssertion:
    data = {
        "assertion_id": "assert-link-1",
        "assertion_kind": "link_existing",
        "operation": "alias",
        "campaign_id": CAMPAIGN_ID,
        "session_id": "session-1",
        "provenance": provenance().model_dump(),
        "selected_text": "gang",
        "normalized_selected_text": "gang",
        "existing_object_ref": object_ref(label="Questionable Company").model_dump(),
    }
    data.update(overrides)
    return AuthoredGraphLinkExistingAssertion.model_validate(data)


def relationship_assertion(**overrides) -> AuthoredGraphRelationshipAssertion:
    data = {
        "assertion_id": "assert-rel-1",
        "assertion_kind": "relationship",
        "operation": "create",
        "campaign_id": CAMPAIGN_ID,
        "session_id": "session-1",
        "provenance": provenance().model_dump(),
        "source_object_ref": object_ref(label="Questionable Company").model_dump(),
        "target_object_ref": object_ref(node_id="pc_bonogo", label="Bonogo").model_dump(),
        "relationship_type": "has_member",
        "direction": "directed",
    }
    data.update(overrides)
    return AuthoredGraphRelationshipAssertion.model_validate(data)


def test_builds_object_assertion() -> None:
    assertion = object_assertion()
    assert assertion.assertion_kind == "object"
    assert assertion.object_ref.label == "Bonogo"
    assert assertion.aliases == ["gang"]


def test_builds_link_existing_assertion() -> None:
    assertion = link_existing_assertion()
    assert assertion.assertion_kind == "link_existing"
    assert assertion.selected_text == "gang"
    assert assertion.existing_object_ref.label == "Questionable Company"


def test_builds_relationship_assertion() -> None:
    assertion = relationship_assertion()
    assert assertion.assertion_kind == "relationship"
    assert assertion.relationship_type == "has_member"
    assert assertion.source_object_ref.label == "Questionable Company"


def test_builds_overlay_document_with_all_three() -> None:
    overlay = AuthoredGraphOverlay(
        campaign_id=CAMPAIGN_ID,
        overlay_id=f"overlay-{CAMPAIGN_ID}",
        created_at=STAMP,
        updated_at=STAMP,
        assertions=[
            object_assertion(),
            link_existing_assertion(),
            relationship_assertion(),
        ],
    )
    assert len(overlay.assertions) == 3
    kinds = {item.assertion_kind for item in overlay.assertions}
    assert kinds == {"object", "link_existing", "relationship"}


@pytest.mark.parametrize(
    "label",
    ["", "   "],
)
def test_rejects_blank_object_ref_label(label: str) -> None:
    with pytest.raises(ValidationError):
        object_ref(label=label, ref_kind="manual_ref")


def test_rejects_blank_existing_node_ref_label() -> None:
    with pytest.raises(ValidationError):
        object_ref(label="  \t  ", node_id="pc_bonogo")


def test_accepts_valid_object_ref() -> None:
    ref = object_ref(label="Bonogo")
    assert ref.label == "Bonogo"


def test_table_known_and_player_visible_are_distinct() -> None:
    table_known = GraphVisibilityPolicy(visibility="table_known")
    player_visible = GraphVisibilityPolicy(visibility="player_visible")
    assert table_known.visibility == "table_known"
    assert player_visible.visibility == "player_visible"


def test_defaults_visibility_reveal_include_gold_and_status() -> None:
    assertion = object_assertion()
    assert assertion.visibility.visibility == "gm_private"
    assert assertion.visibility.reveal_state == "unrevealed"
    assert assertion.include_in_gold_eval is False
    assert assertion.status == "authored"
    assert "evaluation_gold" not in assertion.graph_scope


def test_source_anchor_supports_redundant_fields_without_tiptap() -> None:
    anchor = GraphAuthoringSourceAnchor(
        anchor_kind="text_span",
        selected_text="gang",
        normalized_selected_text="gang",
        surrounding_text_before="the ",
        surrounding_text_after=" of mercenaries",
        paragraph_ordinal=3,
        selected_text_sha256=hash_text("gang"),
        context_sha256=hash_text("the \ngang\n of mercenaries"),
    )
    assert anchor.tiptap_from is None
    assert anchor.tiptap_to is None
    assert anchor.paragraph_ordinal == 3


def test_source_anchor_allows_optional_tiptap_positions() -> None:
    anchor = GraphAuthoringSourceAnchor(
        anchor_kind="text_span",
        selected_text="gang",
        normalized_selected_text="gang",
        tiptap_from=120,
        tiptap_to=124,
    )
    assert anchor.tiptap_from == 120


def test_normalize_selected_text_collapses_whitespace() -> None:
    assert normalize_selected_text("  gang   of\nmercenaries ") == "gang of mercenaries"


def test_hash_text_is_deterministic() -> None:
    assert hash_text("gang") == hash_text("gang")
    assert hash_text("gang") != hash_text("Gang")


def test_build_source_anchor_from_payload_populates_hashes() -> None:
    anchor = build_source_anchor_from_payload(
        {
            "selectionKind": "text_span",
            "selectedText": "gang",
            "surroundingTextBefore": "the ",
            "surroundingTextAfter": " marched",
            "paragraphOrdinal": 2,
            "tiptapFrom": 10,
            "tiptapTo": 14,
        }
    )
    assert anchor.normalized_selected_text == "gang"
    assert anchor.selected_text_sha256 == hash_text("gang")
    assert anchor.context_sha256 is not None
    assert anchor.tiptap_from == 10


def test_create_empty_overlay_has_safe_defaults() -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP)
    assert overlay.schema_version == "dmb.authored_graph_overlay.v1"
    assert overlay.assertions == []
    assert overlay.overlay_id == f"overlay-{CAMPAIGN_ID}"
