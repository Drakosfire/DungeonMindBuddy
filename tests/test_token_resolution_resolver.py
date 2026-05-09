"""Resolver + explain-diff tests (Packet C)."""

from __future__ import annotations

import json

import pytest

from src.token_resolution import (
    HubAliasSpec,
    LexiconArtifact,
    ScenarioOverrides,
    default_generic_defaults,
)
from src.token_resolution.explain import (
    diff_alias_maps,
    diff_token_sets,
    shadow_mode_diff,
)
from src.token_resolution.resolver import resolve_for_query


def _lexicon() -> LexiconArtifact:
    return LexiconArtifact(
        campaign_id="longmont-c1",
        equivalences={
            "captain_lysandra_ironveil": ["captain", "lysandra", "ironveil"],
            "magma_spider": ["magma", "spider"],
        },
        derived_route_stopwords=["longmont"],
        protected_tokens=["lysandra", "magma", "spider"],
    )


def test_resolve_for_query_includes_default_query_tokens() -> None:
    resolved = resolve_for_query(
        "What did Grishna tell the party about finding the brewery?",
        scenario_overrides=ScenarioOverrides(),
        hub_aliases=(),
        lexicon=_lexicon(),
        defaults=default_generic_defaults(),
    )
    assert "grishna" in resolved.query_tokens
    assert "brewery" in resolved.query_tokens
    assert "what" not in resolved.query_tokens
    assert "the" not in resolved.query_tokens


def test_resolve_for_query_emits_route_stopwords_from_each_layer() -> None:
    scenario = ScenarioOverrides(
        extra_route_stopwords=["beta"],
        source_ref="gold/q.json",
    )
    resolved = resolve_for_query(
        "anything",
        scenario_overrides=scenario,
        hub_aliases=(),
        lexicon=_lexicon(),
        defaults=default_generic_defaults(),
    )
    stopwords = set(resolved.effective_route_stopwords)
    assert "session" in stopwords
    assert "longmont" in stopwords
    assert "beta" in stopwords


def test_resolver_force_include_shadows_lower_layer_stopword() -> None:
    scenario = ScenarioOverrides(
        force_include_tokens=["longmont"],
        source_ref="gold/q.json",
    )
    resolved = resolve_for_query(
        "anything",
        scenario_overrides=scenario,
        lexicon=_lexicon(),
        defaults=default_generic_defaults(),
    )
    assert "longmont" not in resolved.effective_route_stopwords
    shadow_rows = [
        row for row in resolved.provenance_rows if row.action == "shadow"
    ]
    assert any(row.token == "longmont" for row in shadow_rows)


def test_resolver_force_exclude_records_conflict_against_lexicon() -> None:
    scenario = ScenarioOverrides(
        force_exclude_tokens=["captain_lysandra_ironveil"],
        source_ref="gold/q.json",
    )
    resolved = resolve_for_query(
        "anything",
        scenario_overrides=scenario,
        lexicon=_lexicon(),
        defaults=default_generic_defaults(),
    )
    assert "captain_lysandra_ironveil" not in resolved.effective_equivalences
    assert any(c.token == "captain_lysandra_ironveil" for c in resolved.conflict_rows)


def test_resolver_unions_aliases_with_higher_layer_winning() -> None:
    scenario = ScenarioOverrides(
        semantic_equivalences={
            "captain_lysandra_ironveil": ["the captain"],
        },
        source_ref="gold/q.json",
    )
    resolved = resolve_for_query(
        "Tell me about the captain.",
        scenario_overrides=scenario,
        hub_aliases=(),
        lexicon=_lexicon(),
        defaults=default_generic_defaults(),
    )
    aliases = set(resolved.effective_equivalences["captain_lysandra_ironveil"])
    assert {"captain", "the captain", "lysandra", "ironveil"}.issubset(aliases)
    conflicts = {(c.token, c.winning_layer, c.shadowed_layer) for c in resolved.conflict_rows}
    assert ("captain_lysandra_ironveil", "scenario", "lexicon") in conflicts


def test_resolver_hub_aliases_layer_between_scenario_and_lexicon() -> None:
    hub = HubAliasSpec(
        slug="captain_lysandra_ironveil",
        subject_class="NPC",
        aliases=["the ironveil captain"],
        source_ref="hub/README.md",
    )
    resolved = resolve_for_query(
        "lysandra",
        hub_aliases=(hub,),
        lexicon=_lexicon(),
        defaults=default_generic_defaults(),
    )
    aliases = resolved.effective_equivalences["captain_lysandra_ironveil"]
    assert "the ironveil captain" in aliases
    assert "captain" in aliases
    assert "lysandra" in aliases


def test_resolver_expanded_terms_include_aliases_for_query_tokens() -> None:
    resolved = resolve_for_query(
        "Where is captain on session 5?",
        lexicon=_lexicon(),
        defaults=default_generic_defaults(),
    )
    assert "lysandra" in resolved.expanded_terms or "ironveil" in resolved.expanded_terms


def test_resolver_output_is_json_round_trip_stable() -> None:
    resolved = resolve_for_query(
        "captain",
        lexicon=_lexicon(),
        defaults=default_generic_defaults(),
    )
    one = json.dumps(resolved.to_json_dict(), sort_keys=True)
    two = json.dumps(resolved.to_json_dict(), sort_keys=True)
    assert one == two


def test_diff_token_sets_returns_symmetric_partition() -> None:
    diff = diff_token_sets(legacy=["a", "B", "c"], resolver=["a", "d"])
    assert diff == {
        "only_in_legacy": ["b", "c"],
        "only_in_resolver": ["d"],
        "in_both": ["a"],
    }


def test_diff_alias_maps_reports_extension_and_drops() -> None:
    legacy = {"x": ["one"], "y": ["two"]}
    resolver_map = {"x": ["one", "extra"], "z": ["new"]}
    diff = diff_alias_maps(legacy, resolver_map)
    assert diff["canonicals_only_in_legacy"] == {"y": ["two"]}
    assert diff["canonicals_only_in_resolver"] == {"z": ["new"]}
    assert diff["aliases_added_in_resolver"] == {"x": ["extra"]}
    assert diff["aliases_dropped_in_resolver"] == {}


def test_shadow_mode_diff_packages_full_payload() -> None:
    resolved = resolve_for_query(
        "Tell me about the captain.",
        scenario_overrides=ScenarioOverrides(
            semantic_equivalences={"captain_lysandra_ironveil": ["the captain"]},
            source_ref="gold/q.json",
        ),
        lexicon=_lexicon(),
        defaults=default_generic_defaults(),
    )
    diff = shadow_mode_diff(
        legacy_route_stopwords={"longmont", "elderwyld", "session"},
        legacy_equivalences={"captain": ["lysandra"]},
        legacy_query_tokens=["captain", "ancient_legacy_only"],
        legacy_expanded_terms=["lysandra"],
        resolver_result=resolved,
    )
    assert diff["schema"] == "dmb_token_resolver_shadow_v1"
    assert "elderwyld" in diff["route_stopwords_diff"]["only_in_legacy"]
    assert "captain_lysandra_ironveil" in diff["equivalences_diff"]["canonicals_only_in_resolver"]
    assert diff["conflict_count"] >= 1
    assert "ancient_legacy_only" in diff["query_tokens_diff"]["only_in_legacy"]
