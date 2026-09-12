import json

import pytest
from pydantic import ValidationError

from extraction_lab.pair_experiment_manifest import load_pair_experiment_manifest


SHA = "a" * 40


def _write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _repo(tmp_path):
    repo = tmp_path / "repo"
    corpus = repo / "corpus"
    corpus.mkdir(parents=True)
    (corpus / "one.md").write_text("# One\n", encoding="utf-8")
    (corpus / "two.md").write_text("# Two\n", encoding="utf-8")
    _write_json(repo / "entity.json", [])
    _write_json(repo / "fact.json", [])
    return repo


def _payload(**overrides):
    payload = {
        "schema": "dmb_extraction_pair_experiment_v1",
        "experiment_id": "pair",
        "repository_sha": SHA,
        "surface": "core_extraction",
        "corpus_root": "corpus",
        "sources": ["one.md"],
        "entity_anchors": "entity.json",
        "fact_anchors": "fact.json",
        "execution": {"mode": "realtime", "cache_policy": "isolated", "repetitions": 1},
        "variants": {"baseline": {"batch_size": 5}, "candidate": {"batch_size": 4}},
    }
    payload.update(overrides)
    return payload


def test_manifest_normalizes_exact_bounded_sources(tmp_path) -> None:
    repo = _repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    _write_json(manifest, _payload(sources=["one.md", "two.md"]))
    pair = load_pair_experiment_manifest(manifest, repo_root=repo)
    assert pair.source_locators == ("one.md", "two.md")
    assert pair.manifest.variants.baseline.batch_size == 5


@pytest.mark.parametrize(
    "sources",
    [[], ["one.md", "one.md"], ["one.md", "two.md", "three.md", "four.md"]],
)
def test_manifest_rejects_empty_duplicate_or_four_source_cohort(
    tmp_path, sources
) -> None:
    repo = _repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    _write_json(manifest, _payload(sources=sources))
    with pytest.raises((ValidationError, ValueError)):
        load_pair_experiment_manifest(manifest, repo_root=repo)


@pytest.mark.parametrize(
    "source", ["../outside.md", "missing.md", "one.txt", "_dungeonbuddy/managed.md"]
)
def test_manifest_rejects_outside_missing_non_markdown_or_managed_source(
    tmp_path, source
) -> None:
    repo = _repo(tmp_path)
    (tmp_path / "outside.md").write_text("outside\n", encoding="utf-8")
    (repo / "corpus" / "one.txt").write_text("text\n", encoding="utf-8")
    managed = repo / "corpus" / "_dungeonbuddy"
    managed.mkdir()
    (managed / "managed.md").write_text("managed\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    _write_json(manifest, _payload(sources=[source]))
    with pytest.raises(ValueError):
        load_pair_experiment_manifest(manifest, repo_root=repo)


def test_manifest_rejects_unknown_variant_fields_and_unbounded_execution(
    tmp_path,
) -> None:
    repo = _repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    payload = _payload()
    payload["variants"]["candidate"]["model"] = "not-allowed"
    payload["execution"]["repetitions"] = 2
    _write_json(manifest, payload)
    with pytest.raises(ValidationError):
        load_pair_experiment_manifest(manifest, repo_root=repo)


def test_manifest_rejects_gold_outside_repository(tmp_path) -> None:
    repo = _repo(tmp_path)
    outside = tmp_path / "outside-entity.json"
    _write_json(outside, [])
    manifest = tmp_path / "manifest.json"
    _write_json(manifest, _payload(entity_anchors="../outside-entity.json"))
    with pytest.raises(ValueError, match="inside"):
        load_pair_experiment_manifest(manifest, repo_root=repo)
