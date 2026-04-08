"""Tests for src/agent/retriever.py — question-aware entity retrieval."""

from __future__ import annotations

import pytest

from src.agent.retriever import (
    EntityIndex,
    _expand_via_relationships,
    _expand_via_shared_evidence,
    _is_noise_fact,
    _tokenize,
    build_entity_summary,
    filter_projection,
    retrieve_relevant_entities,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_entity(
    entity_id: str,
    display_name: str,
    entity_class: str = "actor",
    aliases: list[str] | None = None,
    subtype_facets: list[str] | None = None,
) -> dict:
    return {
        "entity_id": entity_id,
        "display_name": display_name,
        "entity_class": entity_class,
        "aliases": aliases or [],
        "subtype_facets": subtype_facets or [],
        "entity_tags": [],
    }


def _make_projected_entity(
    attributes: dict[str, dict] | None = None,
) -> dict:
    return {"attributes": attributes or {}}


def _make_attr(
    value_label: str,
    evidence_ids: list[str] | None = None,
) -> dict:
    return {
        "selected_fact_id": "fact_1",
        "value_label": value_label,
        "value_normalized": None,
        "all_value_labels": [value_label],
        "source_layer": "world",
        "source_campaign_id": None,
        "source_class": "seed_reference",
        "source_truth_state": "CANON",
        "fact_ids": ["fact_1"],
        "provenance_evidence_ids": evidence_ids or [],
        "conflict_ids": [],
    }


ENTITIES = [
    _make_entity("ent_mirathorn", "Mirathorn", "place",
                 aliases=["City", "city of Mirathorn"],
                 subtype_facets=["settlement"]),
    _make_entity("ent_elara", "Elara Swiftwind", "actor",
                 aliases=["Elara", "Lady Swiftwind"]),
    _make_entity("ent_shepherds_flock", "Shepherd's Flock", "group",
                 aliases=["The Shepherds", "Flock"]),
    _make_entity("ent_barin", "Barin Stonefist", "actor",
                 aliases=["Barin"]),
    _make_entity("ent_ancient_crystal", "Ancient Crystal", "object"),
]

PROJECTION = {
    "campaign_id": None,
    "entities": {
        "ent_mirathorn": _make_projected_entity({
            "geography": _make_attr(
                "Nestled between Stormspire Peaks and Lake Mirathorn",
                evidence_ids=["evid_1", "evid_2"],
            ),
            "economy": _make_attr(
                "Major trade hub with diverse industries",
                evidence_ids=["evid_1"],
            ),
            "defenses": _make_attr(
                "Stone walls being refortified after the cultist battle",
                evidence_ids=["evid_3"],
            ),
            "relationship_tags": _make_attr(
                "Elara Swiftwind leads the city council; Barin Stonefist sits on council",
                evidence_ids=["evid_1"],
            ),
            "source_comments": _make_attr("Mentioned in evidence unit"),
            "unresolved_questions": _make_attr("Not mentioned in the provided text"),
        }),
        "ent_elara": _make_projected_entity({
            "role": _make_attr(
                "Leader of Mirathorn, presides over the city council",
                evidence_ids=["evid_1", "evid_4"],
            ),
            "goals": _make_attr(
                "Ensure Mirathorn's prosperity and safety after the cult crisis",
                evidence_ids=["evid_4"],
            ),
            "relationship_tags": _make_attr(
                "Allied with Barin Stonefist; distrusts the Wizard's College",
                evidence_ids=["evid_4"],
            ),
        }),
        "ent_shepherds_flock": _make_projected_entity({
            "role": _make_attr(
                "Corrupted cult that attempted to summon an Abyssal Flesh Kaiju",
                evidence_ids=["evid_5"],
            ),
            "operational_status": _make_attr(
                "Defeated, remnants scattered",
                evidence_ids=["evid_5"],
            ),
        }),
        "ent_barin": _make_projected_entity({
            "role": _make_attr(
                "Council member in Mirathorn, dwarven blacksmith",
                evidence_ids=["evid_1", "evid_6"],
            ),
            "history": _make_attr(
                "Veteran of the cult battle beneath the city",
                evidence_ids=["evid_6"],
            ),
        }),
        "ent_ancient_crystal": _make_projected_entity({
            "history": _make_attr(
                "Artifact from the first settlers, powers the city's teleportation circle",
                evidence_ids=["evid_7"],
            ),
        }),
    },
    "conflicts": [],
    "metrics": {"open_conflicts": 0, "resolved_conflicts": 0, "projected_entities": 5},
}


# ---------------------------------------------------------------------------
# _tokenize
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_basic(self):
        tokens = _tokenize("What are the defenses of Mirathorn?")
        assert "mirathorn" in tokens
        assert "defenses" in tokens
        assert "the" not in tokens
        assert "are" not in tokens

    def test_empty(self):
        assert _tokenize("") == set()

    def test_short_words_excluded(self):
        tokens = _tokenize("go to it")
        assert len(tokens) == 0


# ---------------------------------------------------------------------------
# _is_noise_fact
# ---------------------------------------------------------------------------

class TestIsNoiseFact:
    def test_noise_attribute(self):
        assert _is_noise_fact("source_comments", "Some text")
        assert _is_noise_fact("unresolved_questions", "Some question")

    def test_noise_label(self):
        assert _is_noise_fact("history", "Not mentioned in evidence text")
        assert _is_noise_fact("role", "No direct assertion in provided text")
        assert _is_noise_fact("atmosphere", "Mentioned in evidence unit")

    def test_empty_label(self):
        assert _is_noise_fact("history", "")
        assert _is_noise_fact("history", "   ")

    def test_short_label(self):
        assert _is_noise_fact("species", "yes")

    def test_valid_fact(self):
        assert not _is_noise_fact("geography", "Located between mountains and a lake")
        assert not _is_noise_fact("role", "Leader of the city council")


# ---------------------------------------------------------------------------
# build_entity_summary
# ---------------------------------------------------------------------------

class TestBuildEntitySummary:
    def test_includes_name_and_class(self):
        summary = build_entity_summary(ENTITIES[0], PROJECTION["entities"]["ent_mirathorn"])
        assert "Mirathorn" in summary
        assert "place" in summary

    def test_includes_facets(self):
        summary = build_entity_summary(ENTITIES[0], PROJECTION["entities"]["ent_mirathorn"])
        assert "settlement" in summary

    def test_includes_fact_labels(self):
        summary = build_entity_summary(ENTITIES[0], PROJECTION["entities"]["ent_mirathorn"])
        assert "trade hub" in summary
        assert "Stormspire Peaks" in summary

    def test_excludes_noise(self):
        summary = build_entity_summary(ENTITIES[0], PROJECTION["entities"]["ent_mirathorn"])
        assert "Mentioned in evidence unit" not in summary
        assert "Not mentioned in the provided text" not in summary

    def test_includes_aliases(self):
        summary = build_entity_summary(ENTITIES[0], PROJECTION["entities"]["ent_mirathorn"])
        assert "city of Mirathorn" in summary

    def test_truncates_long_labels(self):
        long_label = "x" * 500
        entity_data = _make_projected_entity({"history": _make_attr(long_label)})
        summary = build_entity_summary(ENTITIES[0], entity_data)
        assert "..." in summary
        assert len(summary) < 500


# ---------------------------------------------------------------------------
# EntityIndex
# ---------------------------------------------------------------------------

class TestEntityIndex:
    @pytest.fixture()
    def index(self):
        idx = EntityIndex()
        idx.build(PROJECTION, ENTITIES)
        return idx

    def test_build_size(self, index):
        assert index.size == 5

    def test_search_by_name_exact(self, index):
        scores = index.search_by_name("Tell me about Mirathorn")
        assert "ent_mirathorn" in scores
        assert scores["ent_mirathorn"] > 0

    def test_search_by_name_alias(self, index):
        scores = index.search_by_name("Who is Lady Swiftwind?")
        assert "ent_elara" in scores

    def test_search_by_name_no_match(self, index):
        scores = index.search_by_name("Tell me about dragons")
        assert len(scores) == 0

    def test_search_by_keyword(self, index):
        results = index.search_by_keyword("defenses walls fortified")
        entity_ids = [eid for eid, _ in results]
        assert "ent_mirathorn" in entity_ids

    def test_search_by_keyword_cult(self, index):
        results = index.search_by_keyword("cult summoning ritual kaiju")
        entity_ids = [eid for eid, _ in results]
        assert "ent_shepherds_flock" in entity_ids

    def test_search_by_keyword_empty(self, index):
        results = index.search_by_keyword("the is a")
        assert len(results) == 0

    def test_search_by_keyword_returns_sorted(self, index):
        results = index.search_by_keyword("council leader Mirathorn")
        if len(results) >= 2:
            scores = [s for _, s in results]
            assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Graph expansion
# ---------------------------------------------------------------------------

class TestGraphExpansion:
    @pytest.fixture()
    def index(self):
        idx = EntityIndex()
        idx.build(PROJECTION, ENTITIES)
        return idx

    def test_expand_via_relationships(self, index):
        seed = {"ent_mirathorn"}
        expanded = _expand_via_relationships(seed, PROJECTION, index)
        assert "ent_elara" in expanded or "ent_barin" in expanded

    def test_expand_via_shared_evidence(self):
        seed = {"ent_mirathorn"}
        expanded = _expand_via_shared_evidence(seed, PROJECTION)
        # ent_elara and ent_barin share evid_1 with ent_mirathorn
        assert "ent_elara" in expanded or "ent_barin" in expanded

    def test_expand_no_seed(self, index):
        expanded = _expand_via_relationships(set(), PROJECTION, index)
        assert len(expanded) == 0

    def test_expand_shared_evidence_capped(self):
        expanded = _expand_via_shared_evidence(
            {"ent_mirathorn"}, PROJECTION, max_expansion=1
        )
        assert len(expanded) <= 1


# ---------------------------------------------------------------------------
# filter_projection
# ---------------------------------------------------------------------------

class TestFilterProjection:
    def test_filters_to_subset(self):
        filtered = filter_projection(PROJECTION, {"ent_mirathorn", "ent_elara"})
        assert len(filtered["entities"]) == 2
        assert "ent_mirathorn" in filtered["entities"]
        assert "ent_elara" in filtered["entities"]
        assert "ent_shepherds_flock" not in filtered["entities"]

    def test_metrics_updated(self):
        filtered = filter_projection(PROJECTION, {"ent_mirathorn"})
        assert filtered["metrics"]["projected_entities"] == 1
        assert filtered["metrics"]["retrieval_filtered"] is True
        assert filtered["metrics"]["pre_filter_count"] == 5

    def test_empty_filter(self):
        filtered = filter_projection(PROJECTION, set())
        assert len(filtered["entities"]) == 0

    def test_preserves_other_fields(self):
        filtered = filter_projection(PROJECTION, {"ent_mirathorn"})
        assert filtered["campaign_id"] == PROJECTION["campaign_id"]
        assert "conflicts" in filtered


# ---------------------------------------------------------------------------
# retrieve_relevant_entities (integration)
# ---------------------------------------------------------------------------

class TestRetrieveRelevantEntities:
    def test_name_match_retrieval(self):
        ranked, index = retrieve_relevant_entities(
            "Tell me about Mirathorn",
            PROJECTION,
            ENTITIES,
            expand_relationships=False,
            expand_evidence=False,
        )
        entity_ids = [eid for eid, _ in ranked]
        assert "ent_mirathorn" in entity_ids

    def test_keyword_retrieval(self):
        ranked, _ = retrieve_relevant_entities(
            "What happened during the cult summoning?",
            PROJECTION,
            ENTITIES,
            expand_relationships=False,
            expand_evidence=False,
        )
        entity_ids = [eid for eid, _ in ranked]
        assert "ent_shepherds_flock" in entity_ids

    def test_with_expansion(self):
        ranked, _ = retrieve_relevant_entities(
            "Tell me about Mirathorn",
            PROJECTION,
            ENTITIES,
            expand_relationships=True,
            expand_evidence=True,
        )
        entity_ids = [eid for eid, _ in ranked]
        assert "ent_mirathorn" in entity_ids
        # Expansion should pull in related entities
        assert len(entity_ids) > 1

    def test_returns_index_for_caching(self):
        _, index = retrieve_relevant_entities(
            "test question",
            PROJECTION,
            ENTITIES,
        )
        assert index.size == 5
        # Reuse index
        ranked2, _ = retrieve_relevant_entities(
            "Who is Elara?",
            PROJECTION,
            ENTITIES,
            index=index,
        )
        entity_ids = [eid for eid, _ in ranked2]
        assert "ent_elara" in entity_ids

    def test_scores_sorted_descending(self):
        ranked, _ = retrieve_relevant_entities(
            "Mirathorn council leader defenses",
            PROJECTION,
            ENTITIES,
        )
        scores = [s for _, s in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_top_k_limits_before_expansion(self):
        ranked, _ = retrieve_relevant_entities(
            "everything about everyone",
            PROJECTION,
            ENTITIES,
            top_k=2,
            expand_relationships=False,
            expand_evidence=False,
        )
        assert len(ranked) <= 2

    def test_no_results_for_unrelated(self):
        ranked, _ = retrieve_relevant_entities(
            "quantum physics spacetime continuum",
            PROJECTION,
            ENTITIES,
            expand_relationships=False,
            expand_evidence=False,
        )
        assert len(ranked) == 0
