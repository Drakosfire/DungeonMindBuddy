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
    assert profile.enable_session_relationship_sweep is False
    assert profile.enable_automatic_identity_consolidation is False


def test_rendered_worldbuilding_edge_prompt_omits_recap_sweep_and_requires_schema() -> None:
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        render_category_pass_prompts,
    )
    from src.graph_memory.extraction.category_candidate_graph_schema import (
        category_pass_text_format_for_spec,
        schema_for_pass_spec,
    )
    from src.graph_memory.party_context import PartyContext

    profile = get_extraction_profile(
        WORLDBUILDING_PROFILE_ID, WORLDBUILDING_PROFILE_VERSION
    )
    party_ctx = PartyContext(
        campaign_id="longmont-c2",
        session="",
        party_names=(),
        members=(),
        warnings=(),
    )
    prompts = render_category_pass_prompts(
        [
            {
                "source_span_ref_id": "span:1",
                "source_unit_id": "paragraph:001",
                "line_start": 1,
                "line_end": 1,
                "text": "Commander Vell commands Shepherd's Flock.",
            }
        ],
        party_ctx=party_ctx,
        profile=profile,
    )
    edge_prompt = prompts["edge_pass.md"]
    assert "durable" in edge_prompt.lower()
    assert "predicate_family" in edge_prompt
    assert "session-sized" not in edge_prompt
    assert "Relationship extraction sweep" not in edge_prompt
    assert "organized refugee groups" not in edge_prompt
    assert "evacuation pressure" not in edge_prompt
    assert "learned weaknesses" not in edge_prompt
    assert "waves, groups, encounters" not in edge_prompt
    # Profile-owned task instruction remains present.
    assert "automatic identity merges" in edge_prompt.lower()

    schema = schema_for_pass_spec(profile.edge_pass)
    required = schema["properties"]["observation_edges"]["items"]["required"]
    assert "predicate_family" in required
    assert "relationship_type" in required
    text_format = category_pass_text_format_for_spec(profile.edge_pass)
    assert text_format["format"]["type"] == "json_schema"
    assert text_format["format"]["strict"] is True
    assert "predicate_family" in text_format["format"]["schema"]["properties"][
        "observation_edges"
    ]["items"]["required"]


def test_worldbuilding_consolidation_preserves_cross_class_label_collisions() -> None:
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        consolidate_category_outputs,
    )

    profile = get_extraction_profile(
        WORLDBUILDING_PROFILE_ID, WORLDBUILDING_PROFILE_VERSION
    )
    evidence = [{"source_span_ref_id": "span:1", "anchor_quotes": ["Greyfen"]}]
    consolidated = consolidate_category_outputs(
        {
            "location_pass": {
                "observation_nodes": [
                    {
                        "node_id": "loc:greyfen",
                        "label": "Greyfen",
                        "node_type": "location",
                        "description": "Settlement.",
                        "importance": "high",
                        "evidence_refs": evidence,
                    }
                ]
            },
            "collective_pass": {
                "observation_nodes": [
                    {
                        "node_id": "org:greyfen",
                        "label": "Greyfen",
                        "node_type": "organization",
                        "description": "Town council.",
                        "importance": "medium",
                        "evidence_refs": evidence,
                    }
                ]
            },
            "actor_pass": {"observation_nodes": []},
            "edge_pass": {"observation_edges": []},
        },
        campaign_id="longmont-c2",
        session=None,
        profile=profile,
    )
    labels = [(n["node_id"], n["node_type"], n["label"]) for n in consolidated["nodes"]]
    assert ("loc:greyfen", "location", "Greyfen") in labels
    assert ("org:greyfen", "organization", "Greyfen") in labels
    assert consolidated["consolidation_diagnostics"]["automatic_identity_consolidation"] is False
    assert consolidated["consolidation_diagnostics"]["cross_class_merged_nodes"] == []
    assert consolidated["consolidation_diagnostics"]["merged_nodes"] == []


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
