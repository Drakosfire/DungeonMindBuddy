"""Committed benchmark lexicon seed JSON (equivalences + shadow legacy stopwords)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.sentence_routing_retrieval_falsification.token_resolver_shadow import (
    BenchmarkLexiconSeeds,
    build_campaign_lexicon,
    clear_benchmark_lexicon_seeds_cache,
    default_benchmark_lexicon_seeds_path,
    get_benchmark_lexicon_seeds,
    load_benchmark_lexicon_seeds,
)


def test_default_benchmark_lexicon_seeds_path_points_at_committed_file() -> None:
    p = default_benchmark_lexicon_seeds_path()
    assert p.is_file(), f"missing committed seeds: {p}"


def test_load_benchmark_lexicon_seeds_validates_schema() -> None:
    p = default_benchmark_lexicon_seeds_path()
    seeds = load_benchmark_lexicon_seeds(p)
    assert isinstance(seeds, BenchmarkLexiconSeeds)
    assert "captain" in seeds.equivalences
    assert "lysandra" in seeds.equivalences["captain"]
    assert "longmont" in seeds.legacy_route_stopwords_for_shadow_diff
    assert seeds.source_path == str(p.resolve())


def test_get_benchmark_lexicon_seeds_is_memoized() -> None:
    clear_benchmark_lexicon_seeds_cache()
    a = get_benchmark_lexicon_seeds()
    b = get_benchmark_lexicon_seeds()
    assert a is b
    clear_benchmark_lexicon_seeds_cache()


def test_load_custom_seeds_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "custom_seeds.json"
    path.write_text(
        json.dumps(
            {
                "schema": "dmb_benchmark_lexicon_seeds_v1",
                "version": 1,
                "equivalences": {"alpha": ["beta"]},
                "legacy_route_stopwords_for_shadow_diff": ["gamma"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    seeds = load_benchmark_lexicon_seeds(path)
    assert seeds.equivalences == {"alpha": ["beta"]}
    assert seeds.legacy_route_stopwords_for_shadow_diff == frozenset({"gamma"})


def test_load_benchmark_lexicon_seeds_rejects_bad_schema(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"schema": "wrong", "version": 1}', encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected seeds schema"):
        load_benchmark_lexicon_seeds(path)


def test_build_campaign_lexicon_provenance_includes_seed_file() -> None:
    """Lexicon ``built_from`` must cite the committed seed artifact (liftability)."""
    _repo = Path(__file__).resolve().parents[1]
    fixture = (
        _repo
        / "corpus"
        / "eldyrwild-markdown"
        / "Longmont Campaign"
        / "Campaign 1"
        / "Session Recaps"
        / "_session_memory"
        / "Session 01 - Stonebridge and Glowkindle Rats.records_meta.jsonl"
    )
    assert fixture.is_file(), f"missing fixture: {fixture}"
    lines = fixture.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    lex = build_campaign_lexicon(
        breadcrumb_artifact_text="",
        records=records,
        campaign_id="longmont-c1",
    )
    kinds = [entry.get("kind") for entry in lex.to_json_dict().get("built_from", [])]
    assert "benchmark_lexicon_seeds" in kinds
    seed_paths = [
        entry.get("path")
        for entry in lex.to_json_dict().get("built_from", [])
        if entry.get("kind") == "benchmark_lexicon_seeds"
    ]
    assert seed_paths
    assert Path(seed_paths[0]).name == "benchmark_lexicon_seeds_v1.json"
