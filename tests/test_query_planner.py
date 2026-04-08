"""Tests for src/agent/query_planner.py — LLM-guided entity triage."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.agent.query_planner import (
    QueryPlan,
    _normalize_attribute,
    _parse_plan_response,
    build_entity_roster,
)


# ---------------------------------------------------------------------------
# Fixtures — reuse projection shape from test_retriever.py
# ---------------------------------------------------------------------------

def _make_attr(value_label: str) -> dict:
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
        "provenance_evidence_ids": [],
        "conflict_ids": [],
    }


ENTITIES = [
    {"entity_id": "ent_mirathorn", "display_name": "Mirathorn", "entity_class": "place",
     "aliases": [], "subtype_facets": ["settlement"]},
    {"entity_id": "ent_elara", "display_name": "Elara Swiftwind", "entity_class": "actor",
     "aliases": ["Elara"]},
    {"entity_id": "ent_flock", "display_name": "Shepherd's Flock", "entity_class": "group",
     "aliases": []},
    {"entity_id": "ent_barin", "display_name": "Barin Stonefist", "entity_class": "actor",
     "aliases": []},
]

PROJECTION = {
    "entities": {
        "ent_mirathorn": {"attributes": {
            "geography": _make_attr("Between Stormspire Peaks and Lake Mirathorn"),
            "economy": _make_attr("Major trade hub"),
            "defenses": _make_attr("Stone walls being refortified"),
            "source_comments": _make_attr("Mentioned in evidence unit"),
        }},
        "ent_elara": {"attributes": {
            "role": _make_attr("Leader of Mirathorn"),
            "goals": _make_attr("Ensure prosperity"),
        }},
        "ent_flock": {"attributes": {
            "role": _make_attr("Corrupted cult"),
            "operational_status": _make_attr("Defeated"),
        }},
        "ent_barin": {"attributes": {
            "role": _make_attr("Council member, dwarven blacksmith"),
        }},
    },
}

RANKED = [
    ("ent_mirathorn", 1.5),
    ("ent_elara", 1.2),
    ("ent_flock", 0.8),
    ("ent_barin", 0.5),
]

CANDIDATE_IDS = {"ent_mirathorn", "ent_elara", "ent_flock", "ent_barin"}


# ---------------------------------------------------------------------------
# build_entity_roster
# ---------------------------------------------------------------------------

class TestBuildEntityRoster:
    def test_produces_lines_for_each_entity(self):
        roster = build_entity_roster(RANKED, PROJECTION, ENTITIES)
        lines = roster.strip().split("\n")
        assert len(lines) == 4

    def test_includes_entity_id_in_brackets(self):
        roster = build_entity_roster(RANKED, PROJECTION, ENTITIES)
        assert "[ent_mirathorn]" in roster
        assert "[ent_elara]" in roster

    def test_includes_display_name(self):
        roster = build_entity_roster(RANKED, PROJECTION, ENTITIES)
        assert "Mirathorn" in roster
        assert "Elara Swiftwind" in roster

    def test_includes_entity_class(self):
        roster = build_entity_roster(RANKED, PROJECTION, ENTITIES)
        assert "(place)" in roster
        assert "(actor)" in roster

    def test_excludes_noise_attributes(self):
        roster = build_entity_roster(RANKED, PROJECTION, ENTITIES)
        assert "source_comments" not in roster
        assert "Mentioned in evidence unit" not in roster

    def test_includes_real_attributes(self):
        roster = build_entity_roster(RANKED, PROJECTION, ENTITIES)
        assert "geography:" in roster or "economy:" in roster
        assert "trade hub" in roster

    def test_respects_max_attrs(self):
        roster = build_entity_roster(
            RANKED, PROJECTION, ENTITIES, max_attrs_per_entity=1
        )
        mirathorn_line = [line for line in roster.split("\n") if "ent_mirathorn" in line][0]
        assert mirathorn_line.count(":") <= 3  # id:, name(class):, one attr:

    def test_truncates_long_labels(self):
        proj = {
            "entities": {
                "ent_mirathorn": {"attributes": {
                    "history": _make_attr("x" * 200),
                }}
            }
        }
        roster = build_entity_roster(
            [("ent_mirathorn", 1.0)], proj, ENTITIES, max_label_chars=50
        )
        assert "..." in roster


# ---------------------------------------------------------------------------
# _parse_plan_response
# ---------------------------------------------------------------------------

class TestParsePlanResponse:
    def test_parses_valid_json(self):
        raw = json.dumps({
            "selected_entity_ids": ["ent_mirathorn", "ent_elara"],
            "relevant_attributes": ["role", "goals"],
            "reasoning": "test",
        })
        plan = _parse_plan_response(raw, CANDIDATE_IDS)
        assert plan.selected_entity_ids == ["ent_mirathorn", "ent_elara"]
        assert plan.relevant_attributes == ["role", "goals"]
        assert plan.reasoning == "test"

    def test_filters_invalid_entity_ids(self):
        raw = json.dumps({
            "selected_entity_ids": ["ent_mirathorn", "ent_nonexistent", "ent_barin"],
            "reasoning": "test",
        })
        plan = _parse_plan_response(raw, CANDIDATE_IDS)
        assert plan.selected_entity_ids == ["ent_mirathorn", "ent_barin"]
        assert "ent_nonexistent" not in plan.selected_entity_ids

    def test_handles_missing_attributes(self):
        raw = json.dumps({
            "selected_entity_ids": ["ent_mirathorn"],
            "reasoning": "test",
        })
        plan = _parse_plan_response(raw, CANDIDATE_IDS)
        assert plan.relevant_attributes is None

    def test_handles_empty_attributes_list(self):
        raw = json.dumps({
            "selected_entity_ids": ["ent_mirathorn"],
            "relevant_attributes": [],
            "reasoning": "test",
        })
        plan = _parse_plan_response(raw, CANDIDATE_IDS)
        assert plan.relevant_attributes is None

    def test_handles_markdown_wrapped_json(self):
        raw = "```json\n" + json.dumps({
            "selected_entity_ids": ["ent_elara"],
            "reasoning": "test",
        }) + "\n```"
        plan = _parse_plan_response(raw, CANDIDATE_IDS)
        assert plan.selected_entity_ids == ["ent_elara"]

    def test_raises_on_garbage(self):
        with pytest.raises(Exception):
            _parse_plan_response("not json at all {{{", CANDIDATE_IDS)

    def test_empty_selected_ids(self):
        raw = json.dumps({
            "selected_entity_ids": [],
            "reasoning": "nothing relevant",
        })
        plan = _parse_plan_response(raw, CANDIDATE_IDS)
        assert plan.selected_entity_ids == []

    def test_normalizes_attribute_typos(self):
        raw = json.dumps({
            "selected_entity_ids": ["ent_mirathorn"],
            "relevant_attributes": ["portray_notes", "status"],
        })
        plan = _parse_plan_response(raw, CANDIDATE_IDS)
        assert plan.relevant_attributes == ["portrayal_notes", "operational_status"]

    def test_drops_unknown_attributes(self):
        raw = json.dumps({
            "selected_entity_ids": ["ent_mirathorn"],
            "relevant_attributes": ["totally_unknown_attribute"],
        })
        plan = _parse_plan_response(raw, CANDIDATE_IDS)
        assert plan.relevant_attributes is None


class TestNormalizeAttribute:
    def test_exact(self):
        assert _normalize_attribute("defenses") == "defenses"

    def test_alias(self):
        assert _normalize_attribute("portray_notes") == "portrayal_notes"

    def test_fuzzy(self):
        assert _normalize_attribute("physical_condtion") == "physical_condition"


# ---------------------------------------------------------------------------
# filter_projection with attribute_filter (from retriever.py)
# ---------------------------------------------------------------------------

class TestFilterProjectionWithAttributes:
    def test_attribute_filter_narrows_attributes(self):
        from src.agent.retriever import filter_projection

        filtered = filter_projection(
            PROJECTION,
            {"ent_mirathorn"},
            attribute_filter=["defenses"],
        )
        attrs = filtered["entities"]["ent_mirathorn"]["attributes"]
        assert "defenses" in attrs
        assert "geography" not in attrs
        assert "economy" not in attrs

    def test_attribute_filter_none_keeps_all(self):
        from src.agent.retriever import filter_projection

        filtered = filter_projection(PROJECTION, {"ent_mirathorn"})
        attrs = filtered["entities"]["ent_mirathorn"]["attributes"]
        assert len(attrs) == 4  # geography, economy, defenses, source_comments

    def test_attribute_filter_in_metrics(self):
        from src.agent.retriever import filter_projection

        filtered = filter_projection(
            PROJECTION,
            {"ent_mirathorn"},
            attribute_filter=["defenses", "role"],
        )
        assert filtered["metrics"]["attribute_filter"] == ["defenses", "role"]


# ---------------------------------------------------------------------------
# QueryPlan dataclass
# ---------------------------------------------------------------------------

class TestQueryPlan:
    def test_defaults(self):
        plan = QueryPlan(selected_entity_ids=["ent_a"])
        assert plan.fallback is False
        assert plan.relevant_attributes is None
        assert plan.reasoning == ""
        assert plan.duration_ms == 0

    def test_fallback_flag(self):
        plan = QueryPlan(
            selected_entity_ids=["ent_a"],
            fallback=True,
            reasoning="no_api_key",
        )
        assert plan.fallback is True


# ---------------------------------------------------------------------------
# plan_query_async (mocked LLM)
# ---------------------------------------------------------------------------

class TestPlanQuery:
    def test_returns_plan_from_mock_llm(self):
        from src.agent.query_planner import plan_query

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "selected_entity_ids": ["ent_mirathorn", "ent_elara"],
            "relevant_attributes": ["role", "defenses"],
            "reasoning": "question about city defenses and leader",
        })

        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=mock_response)

        plan = plan_query(
            "What are Mirathorn's defenses?",
            "roster text",
            CANDIDATE_IDS,
            openai_client=mock_client,
        )

        assert "ent_mirathorn" in plan.selected_entity_ids
        assert "ent_elara" in plan.selected_entity_ids
        assert plan.relevant_attributes == ["role", "defenses"]
        assert not plan.fallback

    def test_falls_back_on_api_error(self):
        from src.agent.query_planner import plan_query

        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(
            side_effect=RuntimeError("API error")
        )

        plan = plan_query(
            "test question",
            "roster",
            CANDIDATE_IDS,
            openai_client=mock_client,
        )

        assert plan.fallback is True
        assert set(plan.selected_entity_ids) == CANDIDATE_IDS

    def test_falls_back_on_no_api_key(self):
        from src.agent.query_planner import plan_query

        with patch("src.agent.query_planner._load_api_key", return_value=None):
            plan = plan_query(
                "test",
                "roster",
                CANDIDATE_IDS,
            )

        assert plan.fallback is True
        assert plan.reasoning == "no_api_key"

    def test_falls_back_on_empty_selection(self):
        from src.agent.query_planner import plan_query

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "selected_entity_ids": [],
            "reasoning": "nothing matched",
        })

        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=mock_response)

        plan = plan_query(
            "test",
            "roster",
            CANDIDATE_IDS,
            openai_client=mock_client,
        )

        assert plan.fallback is True
        assert set(plan.selected_entity_ids) == CANDIDATE_IDS
