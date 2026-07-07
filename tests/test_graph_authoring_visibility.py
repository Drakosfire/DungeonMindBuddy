"""Tests for authored graph audience visibility filtering (A8)."""

from __future__ import annotations

import pytest

from apps.live_control_server.models.graph_authoring_overlay import (
    GraphVisibilityPolicy,
    create_empty_authored_graph_overlay,
)
from apps.live_control_server.services.graph_authoring_overlay_projection import (
    apply_authored_overlay_to_graph_review_projection,
    authored_object_node_id,
)
from apps.live_control_server.services.graph_authoring_visibility import (
    GraphAudience,
    assertion_visible_to_audience,
    filter_authored_assertions_for_audience,
    filter_authored_overlay_for_audience,
    normalize_visibility_policy,
    projection_adjacency_visible_to_audience,
    projection_node_visible_to_audience,
    visibility_policy_visible_to_audience,
)
from graph_memory.projection.focus_overlay import GraphFocusOverlay
from graph_memory.projection.recap_projection import RecapGraphProjection
from tests.test_graph_authoring_overlay_models import (
    CAMPAIGN_ID,
    STAMP,
    link_existing_assertion,
    object_assertion,
    relationship_assertion,
)

GM = GraphAudience(audience_kind="gm")
TABLE = GraphAudience(audience_kind="table")
PLAYER = GraphAudience(audience_kind="player", player_id="player-1")
OTHER_PLAYER = GraphAudience(audience_kind="player", player_id="player-2")
CHARACTER = GraphAudience(audience_kind="character", character_id="char-1")
OTHER_CHARACTER = GraphAudience(audience_kind="character", character_id="char-2")


def _policy(
    visibility: str,
    *,
    reveal_state: str = "unrevealed",
    visible_to_player_ids: list[str] | None = None,
    visible_to_character_ids: list[str] | None = None,
) -> GraphVisibilityPolicy:
    return GraphVisibilityPolicy(
        visibility=visibility,  # type: ignore[arg-type]
        reveal_state=reveal_state,  # type: ignore[arg-type]
        visible_to_player_ids=visible_to_player_ids or [],
        visible_to_character_ids=visible_to_character_ids or [],
    )


@pytest.mark.parametrize(
    "visibility",
    [
        "gm_private",
        "table_known",
        "player_visible",
        "character_specific",
        "hidden_until_revealed",
    ],
)
def test_gm_sees_all_visibility_values(visibility: str) -> None:
    policy = _policy(visibility, reveal_state="unrevealed")
    assert visibility_policy_visible_to_audience(policy, GM) is True


@pytest.mark.parametrize(
    "visibility",
    ["table_known", "player_visible"],
)
def test_table_sees_table_known_and_player_visible(visibility: str) -> None:
    assert visibility_policy_visible_to_audience(_policy(visibility), TABLE) is True


@pytest.mark.parametrize(
    "visibility",
    ["gm_private", "character_specific"],
)
def test_table_excludes_gm_private_and_character_specific(visibility: str) -> None:
    assert visibility_policy_visible_to_audience(_policy(visibility), TABLE) is False


def test_table_excludes_unrevealed_hidden_until_revealed() -> None:
    policy = _policy("hidden_until_revealed", reveal_state="unrevealed")
    assert visibility_policy_visible_to_audience(policy, TABLE) is False


@pytest.mark.parametrize(
    "visibility",
    ["table_known", "player_visible"],
)
def test_player_sees_table_known_and_player_visible(visibility: str) -> None:
    assert visibility_policy_visible_to_audience(_policy(visibility), PLAYER) is True


def test_player_excludes_gm_private() -> None:
    assert visibility_policy_visible_to_audience(_policy("gm_private"), PLAYER) is False


def test_player_excludes_unrevealed_hidden() -> None:
    policy = _policy("hidden_until_revealed", reveal_state="partial")
    assert visibility_policy_visible_to_audience(policy, PLAYER) is False


def test_player_sees_matching_character_specific_via_player_ids() -> None:
    policy = _policy(
        "character_specific",
        visible_to_player_ids=["player-1"],
    )
    assert visibility_policy_visible_to_audience(policy, PLAYER) is True


def test_player_excludes_nonmatching_character_specific() -> None:
    policy = _policy(
        "character_specific",
        visible_to_player_ids=["player-1"],
    )
    assert visibility_policy_visible_to_audience(policy, OTHER_PLAYER) is False


@pytest.mark.parametrize(
    "visibility",
    ["table_known", "player_visible"],
)
def test_character_sees_table_known_and_player_visible(visibility: str) -> None:
    assert visibility_policy_visible_to_audience(_policy(visibility), CHARACTER) is True


def test_character_sees_matching_character_specific() -> None:
    policy = _policy(
        "character_specific",
        visible_to_character_ids=["char-1"],
    )
    assert visibility_policy_visible_to_audience(policy, CHARACTER) is True


def test_character_excludes_nonmatching_character_specific() -> None:
    policy = _policy(
        "character_specific",
        visible_to_character_ids=["char-1"],
    )
    assert visibility_policy_visible_to_audience(policy, OTHER_CHARACTER) is False


def test_character_excludes_gm_private() -> None:
    assert visibility_policy_visible_to_audience(_policy("gm_private"), CHARACTER) is False


@pytest.mark.parametrize(
    "reveal_state",
    ["unrevealed", "partial"],
)
def test_hidden_until_revealed_not_visible_to_non_gm_until_revealed(
    reveal_state: str,
) -> None:
    policy = _policy("hidden_until_revealed", reveal_state=reveal_state)
    assert visibility_policy_visible_to_audience(policy, TABLE) is False
    assert visibility_policy_visible_to_audience(policy, PLAYER) is False
    assert visibility_policy_visible_to_audience(policy, CHARACTER) is False


def test_hidden_until_revealed_visible_to_non_gm_when_revealed() -> None:
    policy = _policy("hidden_until_revealed", reveal_state="revealed")
    assert visibility_policy_visible_to_audience(policy, TABLE) is True
    assert visibility_policy_visible_to_audience(policy, PLAYER) is True
    assert visibility_policy_visible_to_audience(policy, CHARACTER) is True


def test_missing_policy_defaults_private_for_non_gm() -> None:
    assert visibility_policy_visible_to_audience(None, GM) is True
    assert visibility_policy_visible_to_audience(None, TABLE) is False
    assert visibility_policy_visible_to_audience(None, PLAYER) is False
    assert visibility_policy_visible_to_audience(None, CHARACTER) is False


def test_normalize_visibility_policy_defaults_to_gm_private() -> None:
    policy = normalize_visibility_policy(None)
    assert policy.visibility == "gm_private"


def test_filter_authored_assertions_preserves_only_visible_assertions() -> None:
    private = object_assertion(
        assertion_id="assert-private",
        visibility=_policy("gm_private").model_dump(),
    )
    table_known = object_assertion(
        assertion_id="assert-table",
        visibility=_policy("table_known").model_dump(),
    )
    filtered = filter_authored_assertions_for_audience([private, table_known], TABLE)
    assert [item.assertion_id for item in filtered] == ["assert-table"]


def test_filter_authored_overlay_preserves_metadata_and_does_not_mutate_original() -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                object_assertion(
                    assertion_id="assert-private",
                    visibility=_policy("gm_private").model_dump(),
                ),
                object_assertion(
                    assertion_id="assert-table",
                    visibility=_policy("table_known").model_dump(),
                ),
            ]
        }
    )
    original_assertion_count = len(overlay.assertions)
    filtered = filter_authored_overlay_for_audience(overlay, TABLE)
    assert len(overlay.assertions) == original_assertion_count
    assert filtered.campaign_id == overlay.campaign_id
    assert filtered.overlay_id == overlay.overlay_id
    assert [item.assertion_id for item in filtered.assertions] == ["assert-table"]


@pytest.mark.parametrize(
    "builder",
    [link_existing_assertion, relationship_assertion],
)
def test_assertion_visibility_applies_to_link_existing_and_relationship(
    builder,
) -> None:
    visible = builder(
        assertion_id="assert-visible",
        visibility=_policy("table_known").model_dump(),
    )
    hidden = builder(
        assertion_id="assert-hidden",
        visibility=_policy("gm_private").model_dump(),
    )
    assert assertion_visible_to_audience(visible, TABLE) is True
    assert assertion_visible_to_audience(hidden, TABLE) is False


def test_projection_node_helper_treats_missing_visibility_as_private() -> None:
    assert projection_node_visible_to_audience({"label": "Bonogo"}, GM) is True
    assert projection_node_visible_to_audience({"label": "Bonogo"}, TABLE) is False


def test_projection_adjacency_helper_respects_visibility() -> None:
    adjacency = {"visibility": "table_known"}
    assert projection_adjacency_visible_to_audience(adjacency, TABLE) is True
    assert projection_adjacency_visible_to_audience(adjacency, PLAYER) is True
    assert projection_adjacency_visible_to_audience({"visibility": "gm_private"}, TABLE) is False


def _empty_projection() -> RecapGraphProjection:
    return RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-1",
        graph_id="graph-1",
        markdown="# Recap",
        focus=GraphFocusOverlay(focus_session_id="session-1"),
        node_views={},
        mentions=[],
        source_spans=[],
    )


def test_gm_projection_includes_gm_private_and_table_known_authored_nodes() -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                object_assertion(
                    assertion_id="assert-private",
                    visibility=_policy("gm_private").model_dump(),
                ),
                object_assertion(
                    assertion_id="assert-table",
                    visibility=_policy("table_known").model_dump(),
                ),
            ]
        }
    )
    enriched, _ = apply_authored_overlay_to_graph_review_projection(
        _empty_projection(),
        overlay,
        audience=GM,
    )
    assert authored_object_node_id("assert-private") in enriched.node_views
    assert authored_object_node_id("assert-table") in enriched.node_views


def test_table_filtered_projection_excludes_gm_private_authored_node() -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                object_assertion(
                    assertion_id="assert-private",
                    visibility=_policy("gm_private").model_dump(),
                ),
                object_assertion(
                    assertion_id="assert-table",
                    visibility=_policy("table_known").model_dump(),
                ),
            ]
        }
    )
    enriched, summary = apply_authored_overlay_to_graph_review_projection(
        _empty_projection(),
        overlay,
        audience=TABLE,
    )
    assert authored_object_node_id("assert-private") not in enriched.node_views
    assert authored_object_node_id("assert-table") in enriched.node_views
    assert summary.assertion_count == 1


def test_projection_without_audience_preserves_gm_like_behavior() -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                object_assertion(
                    assertion_id="assert-private",
                    visibility=_policy("gm_private").model_dump(),
                )
            ]
        }
    )
    enriched, _ = apply_authored_overlay_to_graph_review_projection(
        _empty_projection(),
        overlay,
    )
    assert authored_object_node_id("assert-private") in enriched.node_views
