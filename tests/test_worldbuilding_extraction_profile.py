"""Unit tests for the bounded Shepherd's Flock worldbuilding profile."""

from __future__ import annotations

import pytest

from src.graph_memory.extraction.extraction_profile import (
    InadmissibleExtractionProfileError,
    UnknownExtractionProfileError,
    get_extraction_profile,
    require_admitted_profile,
)
from src.graph_memory.extraction.worldbuilding_extraction_profile import (
    EXCLUDED_NODE_TYPES,
    INCLUDED_NODE_TYPES,
    WORLDBUILDING_PROFILE_ID,
    WORLDBUILDING_PROFILE_VERSION,
    validate_worldbuilding_candidate_bounds,
)


def test_profile_registers_exact_id_and_version() -> None:
    profile = get_extraction_profile(
        WORLDBUILDING_PROFILE_ID, WORLDBUILDING_PROFILE_VERSION
    )
    assert profile.qualified_id == f"{WORLDBUILDING_PROFILE_ID}@{WORLDBUILDING_PROFILE_VERSION}"
    assert profile.allow_null_session is True
    assert profile.beat_pass is None
    assert profile.enable_encounter_job_pass is False
    assert {p.pass_id for p in profile.node_passes} == {
        "actor_pass",
        "location_pass",
        "collective_pass",
    }
    assert profile.edge_pass.pass_id == "edge_pass"
    assert "candidate_graph" in profile.schema_ids
    assert profile.vocabulary_policy["mode"] == "bounded_worldbuilding"
    assert profile.post_extraction_validation_policy["auto_promotion"] is False


def test_profile_owns_worldbuilding_instructions_not_recap_beats() -> None:
    profile = get_extraction_profile(
        WORLDBUILDING_PROFILE_ID, WORLDBUILDING_PROFILE_VERSION
    )
    assert "named npcs" in profile.node_passes[0].instruction.lower()
    assert "durable" in profile.edge_pass.instruction.lower()
    assert profile.default_semantic_state["canon_state"] == "worldbuilding_draft"
    assert all(p.pass_id != "beat_pass" for p in profile.node_passes)
    assert profile.beat_pass is None


def test_admits_worldbuilding_null_session_and_rejects_fabricated_session() -> None:
    profile = require_admitted_profile(
        profile_id=WORLDBUILDING_PROFILE_ID,
        profile_version=WORLDBUILDING_PROFILE_VERSION,
        source_domain="worldbuilding",
        document_class="lore",
        session_id=None,
    )
    assert profile.profile_id == WORLDBUILDING_PROFILE_ID

    with pytest.raises(InadmissibleExtractionProfileError):
        require_admitted_profile(
            profile_id=WORLDBUILDING_PROFILE_ID,
            profile_version=WORLDBUILDING_PROFILE_VERSION,
            source_domain="worldbuilding",
            document_class="lore",
            session_id="session-22",
        )

    with pytest.raises(InadmissibleExtractionProfileError):
        require_admitted_profile(
            profile_id=WORLDBUILDING_PROFILE_ID,
            profile_version=WORLDBUILDING_PROFILE_VERSION,
            source_domain="recap",
            document_class="lore",
            session_id=None,
        )


def test_unknown_profile_version_fails_closed() -> None:
    with pytest.raises(UnknownExtractionProfileError):
        get_extraction_profile(WORLDBUILDING_PROFILE_ID, "9.9")


def test_category_bounds_accept_included_and_reject_excluded() -> None:
    assert "character" in INCLUDED_NODE_TYPES
    assert "faction" in INCLUDED_NODE_TYPES
    assert "institution" not in INCLUDED_NODE_TYPES
    assert "item" in EXCLUDED_NODE_TYPES
    ok = {
        "session_id": None,
        "nodes": [
            {
                "node_id": "npc:vell",
                "node_type": "character",
                "evidence_refs": [{"source_span_ref_id": "span:1"}],
            }
        ],
        "edges": [],
        "beats": [],
    }
    assert validate_worldbuilding_candidate_bounds(ok) == []

    bad = {
        "session_id": "session-1",
        "nodes": [
            {
                "node_id": "item:rations",
                "node_type": "item",
                "evidence_refs": [],
            },
            {
                "node_id": "landmark:ridge",
                "node_type": "landmark",
                "evidence_refs": [{"source_span_ref_id": "span:1"}],
            },
        ],
        "edges": [{"edge_id": "e1", "from_node_id": "a"}],
        "beats": [{"beat_id": "b1"}],
    }
    errors = validate_worldbuilding_candidate_bounds(bad)
    assert any("session_id" in e for e in errors)
    assert any("excluded type" in e for e in errors)
    assert any("undeclared type" in e for e in errors)
    assert any("missing evidence_refs" in e for e in errors)
    assert any("exact endpoints" in e for e in errors)
    assert any("beats" in e for e in errors)
