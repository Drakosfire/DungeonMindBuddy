"""Audience-aware visibility filtering for authored graph overlay assertions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphAssertion,
    AuthoredGraphOverlay,
    GraphVisibility,
    GraphVisibilityPolicy,
)

GraphAudienceKind = Literal["gm", "table", "player", "character"]

_GM_PRIVATE_POLICY = GraphVisibilityPolicy(visibility="gm_private")


class GraphAudience(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audience_kind: GraphAudienceKind
    player_id: str | None = None
    character_id: str | None = None


def normalize_visibility_policy(
    policy: GraphVisibilityPolicy | None,
) -> GraphVisibilityPolicy:
    """Missing or absent policy defaults to GM-private."""
    if policy is None:
        return _GM_PRIVATE_POLICY.model_copy(deep=True)
    return policy


def visibility_policy_from_projection_fields(
    *,
    visibility: str | None = None,
    reveal_state: str | None = None,
    visible_to_player_ids: list[str] | None = None,
    visible_to_character_ids: list[str] | None = None,
) -> GraphVisibilityPolicy:
    """Build a visibility policy from projection node/adjacency extras."""
    normalized_visibility = _normalize_projection_visibility(visibility)
    normalized_reveal = _normalize_projection_reveal_state(reveal_state)
    return GraphVisibilityPolicy(
        visibility=normalized_visibility,
        reveal_state=normalized_reveal,
        visible_to_player_ids=list(visible_to_player_ids or ()),
        visible_to_character_ids=list(visible_to_character_ids or ()),
    )


def _normalize_projection_visibility(value: str | None) -> GraphVisibility:
    allowed: tuple[GraphVisibility, ...] = (
        "gm_private",
        "player_visible",
        "table_known",
        "character_specific",
        "hidden_until_revealed",
    )
    if value in allowed:
        return value  # type: ignore[return-value]
    return "gm_private"


def _normalize_projection_reveal_state(
    value: str | None,
) -> Literal["unrevealed", "partial", "revealed"]:
    if value in ("unrevealed", "partial", "revealed"):
        return value
    return "unrevealed"


def visibility_policy_visible_to_audience(
    policy: GraphVisibilityPolicy | None,
    audience: GraphAudience,
) -> bool:
    """Return whether an assertion visibility policy is visible to the audience."""
    normalized = normalize_visibility_policy(policy)

    if audience.audience_kind == "gm":
        return True

    visibility = normalized.visibility
    if visibility == "hidden_until_revealed":
        return normalized.reveal_state == "revealed"

    if visibility == "gm_private":
        return False

    if audience.audience_kind == "table":
        return visibility in ("table_known", "player_visible")

    if audience.audience_kind == "player":
        if visibility in ("table_known", "player_visible"):
            return True
        if visibility == "character_specific":
            return bool(
                audience.player_id
                and audience.player_id in normalized.visible_to_player_ids
            )
        return False

    if audience.audience_kind == "character":
        if visibility in ("table_known", "player_visible"):
            return True
        if visibility == "character_specific":
            return bool(
                audience.character_id
                and audience.character_id in normalized.visible_to_character_ids
            )
        return False

    return False


def assertion_visible_to_audience(
    assertion: AuthoredGraphAssertion,
    audience: GraphAudience,
) -> bool:
    """Return whether an authored assertion is visible to the audience."""
    return visibility_policy_visible_to_audience(assertion.visibility, audience)


def filter_authored_assertions_for_audience(
    assertions: list[AuthoredGraphAssertion],
    audience: GraphAudience,
) -> list[AuthoredGraphAssertion]:
    """Return assertions visible to the audience without mutating the input list."""
    return [
        assertion
        for assertion in assertions
        if assertion_visible_to_audience(assertion, audience)
    ]


def filter_authored_overlay_for_audience(
    overlay: AuthoredGraphOverlay,
    audience: GraphAudience,
) -> AuthoredGraphOverlay:
    """Return a copy of the overlay with assertions filtered for the audience."""
    filtered_assertions = filter_authored_assertions_for_audience(
        overlay.assertions,
        audience,
    )
    return overlay.model_copy(update={"assertions": filtered_assertions})


def _projection_field(raw: object, name: str) -> Any:
    if isinstance(raw, dict):
        return raw.get(name)
    return getattr(raw, name, None)


def projection_node_visible_to_audience(
    raw_node_view: object,
    audience: GraphAudience,
) -> bool:
    """Return whether a projection node view is visible to the audience."""
    policy = visibility_policy_from_projection_fields(
        visibility=_projection_field(raw_node_view, "visibility"),
        reveal_state=_projection_field(raw_node_view, "reveal_state"),
        visible_to_player_ids=_projection_field(raw_node_view, "visible_to_player_ids"),
        visible_to_character_ids=_projection_field(raw_node_view, "visible_to_character_ids"),
    )
    return visibility_policy_visible_to_audience(policy, audience)


def projection_adjacency_visible_to_audience(
    raw_edge_or_adjacency: object,
    audience: GraphAudience,
) -> bool:
    """Return whether a projection adjacency payload is visible to the audience."""
    policy = visibility_policy_from_projection_fields(
        visibility=_projection_field(raw_edge_or_adjacency, "visibility"),
        reveal_state=_projection_field(raw_edge_or_adjacency, "revealed_state")
        or _projection_field(raw_edge_or_adjacency, "reveal_state"),
        visible_to_player_ids=_projection_field(raw_edge_or_adjacency, "visible_to_player_ids"),
        visible_to_character_ids=_projection_field(
            raw_edge_or_adjacency,
            "visible_to_character_ids",
        ),
    )
    return visibility_policy_visible_to_audience(policy, audience)
