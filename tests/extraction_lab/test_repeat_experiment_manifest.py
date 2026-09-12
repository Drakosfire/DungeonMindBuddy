import json

import pytest
from pydantic import ValidationError

from extraction_lab.repeat_experiment_manifest import load_repeat_experiment_manifest


SHA = "a" * 40


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture(tmp_path, **repeat_changes):
    repo = tmp_path / "repo"
    (repo / "corpus").mkdir(parents=True)
    (repo / "corpus" / "one.md").write_text("one", encoding="utf-8")
    _write(repo / "entity.json", [])
    _write(repo / "fact.json", [])
    _write(repo / "MODEL_POLICY.json", {"models": {}, "actions": {}})
    pair = tmp_path / "pair.json"
    _write(pair, {
        "schema": "dmb_extraction_pair_experiment_v1", "experiment_id": "pair",
        "repository_sha": SHA, "surface": "core_extraction", "corpus_root": "corpus",
        "sources": ["one.md"], "entity_anchors": "entity.json", "fact_anchors": "fact.json",
        "execution": {"mode": "realtime", "cache_policy": "isolated", "repetitions": 1},
        "variants": {"baseline": {"batch_size": 5}, "candidate": {"batch_size": 4}},
    })
    repeat = {"schema": "dmb_extraction_repeat_experiment_v1", "experiment_id": "repeat", "pair_manifest": "pair.json", "repetitions": 3}
    repeat.update(repeat_changes)
    path = tmp_path / "repeat.json"
    _write(path, repeat)
    return repo, path


def test_loads_strict_two_or_three_repetition_wrapper(tmp_path):
    repo, path = _fixture(tmp_path)
    result = load_repeat_experiment_manifest(path, repo_root=repo)
    assert result.manifest.repetitions == 3
    assert result.pair.manifest.experiment_id == "pair"
    assert len(result.pair_manifest_sha256) == 64


@pytest.mark.parametrize("value", [1, 4, True])
def test_rejects_repetitions_outside_contract(tmp_path, value):
    repo, path = _fixture(tmp_path, repetitions=value)
    with pytest.raises(ValidationError):
        load_repeat_experiment_manifest(path, repo_root=repo)


def test_rejects_unknown_fields_and_missing_pair(tmp_path):
    repo, path = _fixture(tmp_path, surprise=True)
    with pytest.raises(ValidationError):
        load_repeat_experiment_manifest(path, repo_root=repo)
    repo, path = _fixture(tmp_path / "missing", pair_manifest="absent.json")
    with pytest.raises(ValueError, match="does not exist"):
        load_repeat_experiment_manifest(path, repo_root=repo)
