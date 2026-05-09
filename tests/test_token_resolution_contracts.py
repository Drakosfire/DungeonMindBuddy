"""Contract tests for ``src.token_resolution`` data classes and builder.

These tests pin the artifact schema and serialization invariants. The package
is intended to be lifted into its own project, so the tests act as the public
contract surface.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.token_resolution import (
    LEXICON_SCHEMA_V1,
    LEXICON_VERSION,
    RESOLVED_TOKENS_SCHEMA_V1,
    ConflictRow,
    HubAliasSpec,
    LexiconArtifact,
    LexiconBuildSource,
    ProvenanceRow,
    ResolvedTokens,
    ScenarioOverrides,
    default_generic_defaults,
)
from src.token_resolution.build_lexicon import (
    assemble_lexicon,
    load_lexicon_artifact,
    write_lexicon_artifact,
)


def test_default_generic_defaults_has_no_setting_specific_tokens() -> None:
    """Defaults must be corpus-agnostic; adding world/campaign names is a regression."""
    defaults = default_generic_defaults()
    forbidden = {"longmont", "elderwyld", "mirathorn", "lysandra", "tealeaf"}
    assert forbidden.isdisjoint(defaults.structural_route_stopwords)
    assert forbidden.isdisjoint(defaults.expansion_token_stopwords)
    assert forbidden.isdisjoint(defaults.query_signal_stopwords)
    assert defaults.base_equivalences == {}


def test_default_generic_defaults_includes_basic_structural_words() -> None:
    """Generic structural words like 'session', 'npcs', 'pcs' belong in defaults."""
    defaults = default_generic_defaults()
    expected_structural = {"session", "sessions", "npcs", "pcs", "parties", "locations"}
    assert expected_structural.issubset(defaults.structural_route_stopwords)


def test_lexicon_artifact_to_json_dict_is_deterministic() -> None:
    """Same inputs → byte-identical JSON, regardless of dict insertion order."""
    a = LexiconArtifact(
        campaign_id="longmont-c1",
        corpus_fingerprint="fp123",
        built_from=(
            LexiconBuildSource(kind="breadcrumb_frontmatter", path="recap.md", fingerprint="abc"),
        ),
        equivalences={"Lysandra": ["captain", "Captain Lysandra"], "magma_spider": ["spider"]},
        route_tokens={"NPCs/lysandra": ["lysandra", "captain"]},
        derived_route_stopwords=["longmont", "elderwyld"],
        protected_tokens=["lysandra", "magma_spider"],
        source_refs={"lysandra": ["recap.md:42"]},
    )
    b = LexiconArtifact(
        campaign_id="longmont-c1",
        corpus_fingerprint="fp123",
        built_from=(
            LexiconBuildSource(kind="breadcrumb_frontmatter", path="recap.md", fingerprint="abc"),
        ),
        equivalences={"magma_spider": ["spider"], "Lysandra": ["Captain Lysandra", "captain"]},
        route_tokens={"NPCs/lysandra": ["captain", "lysandra"]},
        derived_route_stopwords=["elderwyld", "longmont"],
        protected_tokens=["magma_spider", "lysandra"],
        source_refs={"lysandra": ["recap.md:42"]},
    )
    assert json.dumps(a.to_json_dict(), sort_keys=True) == json.dumps(b.to_json_dict(), sort_keys=True)


def test_lexicon_artifact_round_trip_via_json_dict() -> None:
    """to_json_dict → from_json_dict preserves the artifact (modulo normalization)."""
    artifact = LexiconArtifact(
        campaign_id="longmont-c1",
        corpus_fingerprint="fp123",
        equivalences={"lysandra": ["captain"]},
        route_tokens={"npcs/lysandra": ["captain"]},
        derived_route_stopwords=["longmont"],
        protected_tokens=["lysandra"],
        source_refs={"lysandra": ["recap.md:1"]},
    )
    payload = artifact.to_json_dict()
    rebuilt = LexiconArtifact.from_json_dict(payload)
    assert rebuilt.to_json_dict() == payload
    assert rebuilt.schema == LEXICON_SCHEMA_V1
    assert rebuilt.version == LEXICON_VERSION


def test_lexicon_artifact_rejects_unknown_schema() -> None:
    with pytest.raises(ValueError, match="Unsupported lexicon schema"):
        LexiconArtifact.from_json_dict({"schema": "wrong_schema_v0", "version": LEXICON_VERSION})


def test_lexicon_artifact_rejects_unknown_version() -> None:
    with pytest.raises(ValueError, match="Unsupported lexicon version"):
        LexiconArtifact.from_json_dict({"schema": LEXICON_SCHEMA_V1, "version": 99})


def test_assemble_lexicon_merges_hub_alias_specs() -> None:
    """Hub aliases are seeded by slug; extra equivalences extend (don't replace)."""
    artifact = assemble_lexicon(
        campaign_id="longmont-c1",
        corpus_fingerprint="fp",
        hub_aliases=[
            HubAliasSpec(
                slug="captain_lysandra_ironveil",
                subject_class="NPC",
                aliases=["Captain Lysandra", "Lysandra", "Ironveil"],
                source_ref="NPCs/captain_lysandra_ironveil/README.md",
            )
        ],
        extra_equivalences={"captain_lysandra_ironveil": ["captain"]},
        route_tokens={"NPCs/captain_lysandra_ironveil": ["lysandra"]},
        derived_route_stopwords=["longmont"],
        protected_tokens=["captain_lysandra_ironveil"],
        source_refs={"captain_lysandra_ironveil": ["README.md"]},
    )
    payload = artifact.to_json_dict()
    aliases = payload["equivalences"]["captain_lysandra_ironveil"]
    assert "captain lysandra" in aliases
    assert "lysandra" in aliases
    assert "ironveil" in aliases
    assert "captain" in aliases
    assert payload["derived_route_stopwords"] == ["longmont"]
    assert payload["protected_tokens"] == ["captain_lysandra_ironveil"]


def test_write_and_load_lexicon_artifact_round_trip(tmp_path: Path) -> None:
    artifact = assemble_lexicon(
        campaign_id="c1",
        corpus_fingerprint="fp",
        hub_aliases=[HubAliasSpec(slug="x", subject_class="NPC", aliases=["X"], source_ref="r")],
    )
    out_path = tmp_path / "campaign-c1.json"
    written = write_lexicon_artifact(artifact, out_path)
    assert written == out_path
    raw = out_path.read_text(encoding="utf-8")
    assert raw.endswith("\n"), "deterministic artifact should end with a newline"
    rebuilt = load_lexicon_artifact(out_path)
    assert rebuilt.to_json_dict() == artifact.to_json_dict()


def test_scenario_overrides_normalize_and_serialize() -> None:
    overrides = ScenarioOverrides(
        semantic_equivalences={"foo": ["FOO_alias", "foo_alias"]},
        force_include_tokens=["BAR", "bar"],
        force_exclude_tokens=["baz"],
        extra_route_stopwords=["LONGMONT"],
        source_ref="gold/scenario-1.json",
    )
    payload = overrides.to_json_dict()
    assert payload["semantic_equivalences"]["foo"] == ["foo_alias"]
    assert payload["force_include_tokens"] == ["bar"]
    assert payload["force_exclude_tokens"] == ["baz"]
    assert payload["extra_route_stopwords"] == ["longmont"]
    assert payload["source_ref"] == "gold/scenario-1.json"


def test_resolved_tokens_serialization_is_stable() -> None:
    resolved = ResolvedTokens(
        campaign_id="longmont-c1",
        resolved_for_query="What did Grishna tell the party?",
        query_tokens=["grishna", "tell", "party"],
        expanded_terms=["captain", "boulder"],
        effective_equivalences={"grishna": ["the brewer"]},
        effective_route_stopwords=["longmont"],
        provenance_rows=[
            ProvenanceRow(token="captain", layer="lexicon", source_ref="lex.json", action="include"),
            ProvenanceRow(token="longmont", layer="lexicon", source_ref="lex.json", action="exclude"),
        ],
        conflict_rows=[
            ConflictRow(
                token="captain",
                winning_layer="scenario",
                shadowed_layer="lexicon",
                winning_source_ref="gold/q1.json",
                shadowed_source_ref="lex.json",
                note="scenario specifies broader alias list",
            )
        ],
    )
    payload = resolved.to_json_dict()
    assert payload["schema"] == RESOLVED_TOKENS_SCHEMA_V1
    assert payload["query_tokens"] == ["grishna", "party", "tell"]
    assert payload["expanded_terms"] == ["boulder", "captain"]
    assert payload["provenance_rows"][0]["layer"] == "lexicon"
    assert payload["conflict_rows"][0]["winning_layer"] == "scenario"


def test_resolved_tokens_round_trip_via_json() -> None:
    """Serialization should be byte-stable across runs (sort_keys-friendly)."""
    resolved = ResolvedTokens(
        campaign_id="c1",
        resolved_for_query="q",
        query_tokens=["b", "a"],
        expanded_terms=["d", "c"],
    )
    payload_a = json.dumps(resolved.to_json_dict(), sort_keys=True)
    payload_b = json.dumps(resolved.to_json_dict(), sort_keys=True)
    assert payload_a == payload_b
