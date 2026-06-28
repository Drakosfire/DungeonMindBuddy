from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from apps.live_control_server.services.union_supergraph_projection_adapter import (
    TWO_SESSION_PREVIEW_SOURCE,
    build_plan_union_supergraph_projection,
    build_plan_union_supergraph_projection_payload,
)
from graph_memory.projection import RecapGraphProjection
from graph_memory.union_supergraph.load import DEFAULT_FIXTURE_PATH


def test_adapter_builds_projection_for_session_23() -> None:
    projection = build_plan_union_supergraph_projection(session_id="session-23")

    assert isinstance(projection, RecapGraphProjection)
    assert projection.session_id == "session-23"
    assert projection.campaign_id == "longmont-c2"
    assert projection.graph_id == "longmont-c2:union-supergraph"


def test_adapter_projection_contains_global_pc_caelynn() -> None:
    projection = build_plan_union_supergraph_projection(session_id="session-23")

    caelynn = projection.node_views["pc_caelynn"]
    assert caelynn.node_id == "pc_caelynn"
    assert caelynn.label == "Caelynn"
    assert caelynn.kind == "pc"
    assert caelynn.role == "pc"
    assert caelynn.anchored_to_focus_session is True


def test_adapter_projection_preserves_focus_and_non_focus_evidence() -> None:
    projection = build_plan_union_supergraph_projection(session_id="session-23")

    caelynn = projection.node_views["pc_caelynn"]
    badges = {badge.evidence_ref_id: badge for badge in caelynn.evidence_badges}

    assert (
        badges["evidence:session-23:caelynn:recap-mention"].is_focus_session_evidence
        is True
    )
    assert badges["evidence:session-23:caelynn:recap-mention"].source_domain == "recap"
    assert (
        badges[
            "evidence:worldbuilding:caelynn:character-note"
        ].is_focus_session_evidence
        is False
    )
    assert (
        badges["evidence:worldbuilding:caelynn:character-note"].source_domain
        == "worldbuilding"
    )


def test_adapter_projection_preserves_focus_and_non_focus_adjacency() -> None:
    projection = build_plan_union_supergraph_projection(session_id="session-23")

    caelynn = projection.node_views["pc_caelynn"]
    candidates = {candidate.node_id: candidate for candidate in caelynn.adjacency}

    session_event = candidates["event_session_23_mireward_gate"]
    assert session_event.anchored_to_focus_session is True
    assert session_event.predicate == "participated_in"

    mirathorn = candidates["loc_mirathorn"]
    assert mirathorn.anchored_to_focus_session is False
    assert mirathorn.source_domains == ["worldbuilding"]


def test_adapter_payload_is_json_safe_dict() -> None:
    payload = build_plan_union_supergraph_projection_payload(session_id="session-23")

    assert isinstance(payload, dict)
    assert payload["session_id"] == "session-23"
    assert payload["node_views"]["pc_caelynn"]["node_id"] == "pc_caelynn"
    json.dumps(payload)
    assert _is_json_safe(payload)


def test_adapter_accepts_explicit_store_path() -> None:
    projection = build_plan_union_supergraph_projection(
        session_id="session-23",
        store_path=DEFAULT_FIXTURE_PATH,
    )

    assert projection.node_views["pc_caelynn"].node_id == "pc_caelynn"


def test_adapter_builds_two_session_preview_source() -> None:
    projection = build_plan_union_supergraph_projection(
        session_id="session-23",
        preview_source=TWO_SESSION_PREVIEW_SOURCE,
    )
    lysandro = projection.node_views["character_lysandro"]

    assert projection.graph_id == "longmont-c2:preview-union-supergraph"
    assert projection.markdown
    assert "[Lysandro](dmb-node:character_lysandro)" in projection.markdown
    assert lysandro.anchored_to_focus_session is True
    assert lysandro.suggested_expansions
    assert lysandro.suggested_expansions[0].rank == 1
    assert any(
        badge.evidence_ref_id.startswith("evidence:session-22:")
        and not badge.is_focus_session_evidence
        for badge in lysandro.evidence_badges
    )
    assert any(
        badge.evidence_ref_id.startswith("evidence:session-23:")
        and badge.is_focus_session_evidence
        for badge in lysandro.evidence_badges
    )


def test_adapter_preview_payload_is_json_safe() -> None:
    payload = build_plan_union_supergraph_projection_payload(
        session_id="session-23",
        preview_source=TWO_SESSION_PREVIEW_SOURCE,
    )

    assert payload["node_views"]["character_lysandro"]["anchored_to_focus_session"] is True
    assert _is_json_safe(payload)


def test_adapter_raises_for_missing_store_path(tmp_path: Path) -> None:
    missing_store_path = tmp_path / "missing-union-supergraph.json"

    with pytest.raises(FileNotFoundError):
        build_plan_union_supergraph_projection(
            session_id="session-23",
            store_path=missing_store_path,
        )


def _is_json_safe(value: Any) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list):
        return all(_is_json_safe(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_safe(item)
            for key, item in value.items()
        )
    return False
