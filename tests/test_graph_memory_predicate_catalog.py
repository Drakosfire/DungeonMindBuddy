"""Tests for the runtime predicate catalogue."""

from __future__ import annotations

from src.graph_memory import identity_resolution as ir
from src.graph_memory.predicate_catalog import (
    V1_EXACT_PREDICATES,
    catalog_cross_check_issues,
    edge_predicate_family,
    exact_predicate_ids,
    predicate_family_for_type,
    predicate_family_ids,
    predicates_by_family,
    prompt_markdown,
    validate_edge_predicate,
)


def test_catalog_matches_identity_resolution_map():
    assert V1_EXACT_PREDICATES == ir.PREDICATE_FAMILY


def test_every_exact_predicate_uses_a_known_family():
    assert catalog_cross_check_issues() == []


def test_predicate_family_for_type_uses_catalog_or_rel_prefix():
    assert predicate_family_for_type("parent_of") == "kinship"
    assert predicate_family_for_type("recognizes") == "rel:recognizes"


def test_exact_predicate_ids_are_sorted_and_non_empty():
    ids = exact_predicate_ids()
    assert ids == tuple(sorted(ids))
    assert "parent_of" in ids
    assert "associated_with" in ids


def test_predicates_by_family_groups_catalog():
    grouped = predicates_by_family()
    assert "kinship" in grouped
    assert "parent_of" in grouped["kinship"]
    assert "child_of" in grouped["kinship"]


def test_predicate_family_ids_include_kinship():
    assert "kinship" in predicate_family_ids()


def test_validate_edge_predicate_detects_unknown_and_mismatch():
    assert validate_edge_predicate("recognizes", "kinship") == ["unknown_relationship_type"]
    assert validate_edge_predicate("parent_of", "social_relation") == ["relationship_family_mismatch"]
    assert validate_edge_predicate("parent_of", "kinship") == []


def test_edge_predicate_family_prefers_explicit_field():
    edge = {
        "relationship_type": "works_with",
        "predicate_family": "membership",
    }
    assert edge_predicate_family(edge) == "membership"


def test_prompt_markdown_lists_controlled_catalog():
    md = prompt_markdown()
    assert "Controlled edge predicates" in md
    assert "`parent_of`" in md
    assert "Do not invent verbs" in md
    assert "**kinship**" in md


def test_session_23_gold_predicates_are_in_catalog():
    # Idea 2: the v1 catalog must be a superset of the relationship verbs the
    # Session 23 gold fixture uses, otherwise the strict edge-pass enum makes
    # those gold edges impossible to emit (a self-inflicted recall ceiling).
    assert predicate_family_for_type("leads") == "authority"
    assert predicate_family_for_type("threatens") == "threat_relation"
    assert predicate_family_for_type("displaced_from") == "routing"
    ids = exact_predicate_ids()
    for verb in ("leads", "threatens", "displaced_from"):
        assert verb in ids
    # Widened families must still resolve in the runtime catalogue.
    assert catalog_cross_check_issues() == []


def test_protects_adopts_existing_directed_threat_response_family():
    assert V1_EXACT_PREDICATES["protects"] == "threat_relation"
    assert validate_edge_predicate("protects", "threat_relation") == []
    assert "protects" in predicates_by_family()["threat_relation"]
    assert "`protects`" in prompt_markdown()
    assert "threat_relation" not in ir.SYMMETRIC_FAMILIES
    assert catalog_cross_check_issues() == []


def test_prompt_and_schema_generation_do_not_read_eval_files(monkeypatch):
    import importlib
    from pathlib import Path

    from src.graph_memory import predicate_catalog
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        render_category_pass_prompts,
    )
    from src.graph_memory.extraction.category_candidate_graph_schema import (
        category_edge_pass_json_schema,
    )

    original_open = Path.open

    def reject_eval_read(path, *args, **kwargs):
        if "evals" in path.parts:
            raise FileNotFoundError("eval fixtures are absent from production")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_eval_read)
    # A warm registry cache must not conceal the production packaging failure.
    importlib.reload(predicate_catalog)
    prompts = render_category_pass_prompts([
        {"source_span_ref_id": "span-1", "line_start": 1, "line_end": 1,
         "text": "The party arrived at the village."},
    ])
    assert len(prompts) == 7
    assert "Controlled edge predicates" in prompts["edge_pass.md"]
    schema = category_edge_pass_json_schema()
    family_enum = schema["properties"]["observation_edges"]["items"]["properties"]["predicate_family"]["enum"]
    assert len(family_enum) == 18
    assert {"citation", "source_derivation", "temporal_sequence", "visibility"} <= set(family_enum)
    assert predicate_catalog.validate_edge_predicate("parent_of", "kinship") == []
    assert predicate_catalog.validate_edge_predicate("parent_of", "citation") == ["relationship_family_mismatch"]
    assert predicate_catalog.validate_edge_predicate("parent_of", "not_a_family") == ["unknown_predicate_family"]


def test_recap_meaning_guidance_covers_exact_catalogue_without_changing_common_prompt():
    from src.graph_memory.predicate_catalog import (
        RECAP_PREDICATE_MEANINGS, recap_predicate_meaning_guidance,
    )

    assert set(RECAP_PREDICATE_MEANINGS) == set(exact_predicate_ids())
    guidance = recap_predicate_meaning_guidance()
    assert "subject → predicate → object" in guidance
    for predicate, meaning in RECAP_PREDICATE_MEANINGS.items():
        assert f"- `{predicate}`: {meaning}" in guidance
        assert meaning not in prompt_markdown()


def test_recap_predicate_roles_preserve_distinctions_and_ambiguous_source_scope():
    from src.graph_memory.predicate_catalog import RECAP_PREDICATE_MEANINGS as meanings

    assert "possessed item does not possess its holder" in meanings["possesses"]
    assert "a visit" in meanings["attacks"]
    assert "traveling with someone" in meanings["travels_to"]
    assert "communications" in meanings["controls_comms_with"]
    assert "mission or mission-directing actor" in meanings["mission_focus"]
    assert "not that object is missing" in meanings["missing_contact"]
    assert "device changing hands alone" in meanings["replaced_contact"]
